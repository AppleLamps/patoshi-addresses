"""Resumable, throttled Esplora collector. Standard library only; read-only HTTP.

Successful cache entries are immutable, including historical outspend observations.
Every HTTP response/error is retained in SQLite. Run --mode controls before full.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import os
from pathlib import Path
import random
import sqlite3
import struct
import threading
import time
import traceback
import urllib.error
import urllib.request
import zlib
from datetime import datetime, timezone
from decimal import Decimal

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis/phase2"
PIN = "33a74d805c95c368636c4a7334e3cff80d8624fd4b0182bde84eca9e4749465f"
CONTROLS = {2817: 5201000000, 19863: 5014000000, 23079: 5012000000, 28507: 5022000000}
HOSTS = ("https://mempool.space/api", "https://blockstream.info/api")


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def dh(b):
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()


def atomic_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def inputs():
    heights = [int(s) for s in (ROOT / "analysis/provenance/lopp_patoshi_heights.txt").read_text().splitlines()]
    assert sha(("".join(f"{h}\n" for h in heights)).encode()) == PIN
    with (ROOT / "patoshi_pubkeys_COMPLETE.csv").open(newline="") as f:
        rows = {int(r["Block Height"]): r for r in csv.DictReader(f)}
    assert sorted(rows) == heights and len(heights) == 21953
    return heights, rows


def compact(n):
    if n < 253:
        return bytes([n])
    return (b"\xfd" + struct.pack("<H", n)) if n <= 65535 else b"\xfe" + struct.pack("<I", n)


def txid_from_json(tx):
    """Serialize non-witness transaction; coinbase prevout is consensus constant."""
    b = struct.pack("<I", tx["version"] & 0xffffffff) + compact(len(tx["vin"]))
    for v in tx["vin"]:
        cb = v.get("is_coinbase", False)
        prev = bytes(32) if cb else bytes.fromhex(v["txid"])[::-1]
        index = 0xffffffff if cb else v["vout"]
        script = bytes.fromhex(v["scriptsig"])
        b += prev + struct.pack("<I", index) + compact(len(script)) + script + struct.pack("<I", v["sequence"])
    b += compact(len(tx["vout"]))
    for v in tx["vout"]:
        script = bytes.fromhex(v["scriptpubkey"])
        b += struct.pack("<Q", v["value"]) + compact(len(script)) + script
    b += struct.pack("<I", tx["locktime"])
    return dh(b)[::-1].hex()


def check_header(h):
    raw = struct.pack("<I", h["version"] & 0xffffffff)
    raw += bytes.fromhex(h.get("previousblockhash", "00" * 32))[::-1]
    raw += bytes.fromhex(h["merkle_root"])[::-1]
    raw += struct.pack("<III", h["timestamp"], h["bits"], h["nonce"])
    assert dh(raw)[::-1].hex() == h["id"], "header hash mismatch"
    bits = h["bits"]
    target = (bits & 0x7fffff) * 256 ** ((bits >> 24) - 3)
    assert int(h["id"], 16) <= target, "proof of work fails"
    return raw.hex()


def merkle_root(txids):
    layer = [bytes.fromhex(t)[::-1] for t in txids]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [dh(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0][::-1].hex()


def extra_nonce(script):
    """Parse pushes, preserving ambiguity. Early client's second push is candidate EN."""
    b, i, pushes = bytes.fromhex(script), 0, []
    try:
        while i < len(b):
            op = b[i]
            i += 1
            if op <= 75:
                n = op
            elif op in (76, 77, 78):
                size = {76: 1, 77: 2, 78: 4}[op]
                if i + size > len(b):
                    raise ValueError("truncated length")
                n = int.from_bytes(b[i:i + size], "little")
                i += size
            elif 81 <= op <= 96:
                pushes.append(bytes([op - 80]))
                continue
            else:
                raise ValueError(f"non-push opcode {op}")
            if i + n > len(b):
                raise ValueError("truncated push")
            pushes.append(b[i:i + n])
            i += n
        if len(pushes) != 2 or len(pushes[1]) > 8:
            return {"extra_nonce": None, "pushes": [p.hex() for p in pushes], "parse_status": "not_two_early_client_pushes"}
        p = pushes[1]
        value = int.from_bytes(p, "little")
        if p and p[-1] & 128:
            value = -(value & ~(128 << (8 * (len(p) - 1))))
        return {"extra_nonce": value, "pushes": [p.hex() for p in pushes], "parse_status": "two_push_candidate"}
    except ValueError as e:
        return {"extra_nonce": None, "parse_status": str(e)}


class Store:
    def __init__(self, rate):
        (OUT / "cache").mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.rate_lock = threading.Lock()
        self.next_request = 0
        self.pause_until = 0
        self.interval = 1 / rate
        self.db = sqlite3.connect(OUT / "cache/chain.sqlite3", check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS responses (
          id INTEGER PRIMARY KEY, height INTEGER NOT NULL, endpoint TEXT NOT NULL,
          host TEXT NOT NULL, attempt INTEGER NOT NULL, fetched_at TEXT NOT NULL,
          status INTEGER NOT NULL, headers TEXT NOT NULL, sha256 TEXT NOT NULL,
          body_zlib BLOB NOT NULL, error TEXT,
          UNIQUE(height, endpoint, host, attempt));
        CREATE INDEX IF NOT EXISTS response_lookup ON responses(height, endpoint, status);
        CREATE TABLE IF NOT EXISTS results (
          kind TEXT NOT NULL, height INTEGER NOT NULL, data TEXT NOT NULL,
          PRIMARY KEY(kind,height));
        CREATE TABLE IF NOT EXISTS failures (
          stage TEXT NOT NULL, height INTEGER NOT NULL, at TEXT NOT NULL, error TEXT NOT NULL,
          PRIMARY KEY(stage,height));
        CREATE TABLE IF NOT EXISTS request_payloads (
          height INTEGER NOT NULL, endpoint TEXT NOT NULL, body_json BLOB NOT NULL,
          PRIMARY KEY(height,endpoint));
        """)
        self.db.commit()

    def get(self, kind, h):
        with self.lock:
            row = self.db.execute("SELECT data FROM results WHERE kind=? AND height=?", (kind, h)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, kind, h, value):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO results VALUES(?,?,?)", (kind, h, json.dumps(value, sort_keys=True)))

    def failure(self, stage, h, error):
        with self.lock, self.db:
            self.db.execute("INSERT OR REPLACE INTO failures VALUES(?,?,?,?)", (stage, h, now(), str(error)))

    def throttle(self):
        with self.rate_lock:
            wait = max(self.next_request, self.pause_until) - time.monotonic()
            while wait > 0:
                time.sleep(min(wait, 30))
                wait = max(self.next_request, self.pause_until) - time.monotonic()
            self.next_request = time.monotonic() + self.interval

    def fetch(self, h, endpoint, as_json=True, hosts=HOSTS, max_attempts=3, request_body=None):
        url_path, payload = endpoint, None
        if request_body is not None:
            # The only POST permitted here is a read-only script-history lookup.
            assert endpoint.split('?')[0] == '/scripthashes/txs'
            payload = json.dumps(request_body, separators=(',', ':')).encode()
            endpoint = 'POST ' + endpoint + ' body-sha256=' + sha(payload)
            with self.lock, self.db:
                self.db.execute('INSERT OR IGNORE INTO request_payloads VALUES(?,?,?)', (h, endpoint, payload))
        with self.lock:
            hit = self.db.execute("SELECT body_zlib,id,fetched_at,host FROM responses WHERE height=? AND endpoint=? AND status=200 ORDER BY id LIMIT 1", (h, endpoint)).fetchone()
        if hit:
            body = zlib.decompress(hit[0])
            return (json.loads(body) if as_json else body.decode().strip()), {"response_id": hit[1], "observed_at": hit[2], "host": hit[3]}
        for host in hosts:
            with self.lock:
                used = self.db.execute("SELECT COALESCE(MAX(attempt),0) FROM responses WHERE height=? AND endpoint=? AND host=?", (h, endpoint, host)).fetchone()[0]
            for attempt in range(used + 1, max_attempts + 1):
                self.throttle()
                status, headers, body, err = 0, {}, b"", None
                stamp = now()
                try:
                    req = urllib.request.Request(host + url_path, data=payload, headers={"User-Agent": "patoshi-chain-verification/1.0", "Accept": "application/json,text/plain", "Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=45) as response:
                        status, headers, body = response.status, dict(response.headers), response.read()
                except urllib.error.HTTPError as e:
                    status, headers, body, err = e.code, dict(e.headers), e.read(), str(e)
                except Exception as e:
                    err = f"{type(e).__name__}: {e}"
                with self.lock, self.db:
                    cur = self.db.execute("INSERT INTO responses(height,endpoint,host,attempt,fetched_at,status,headers,sha256,body_zlib,error) VALUES(?,?,?,?,?,?,?,?,?,?)", (h, endpoint, host, attempt, stamp, status, json.dumps(headers), sha(body), zlib.compress(body), err))
                    rid = cur.lastrowid
                if status == 200:
                    return (json.loads(body) if as_json else body.decode().strip()), {"response_id": rid, "observed_at": stamp, "host": host}
                if status == 429:
                    try:
                        delay = float(next((v for k, v in headers.items() if k.lower() == "retry-after"), 60))
                    except ValueError:
                        delay = 60
                    with self.rate_lock:
                        self.pause_until = max(self.pause_until, time.monotonic() + max(delay, 30 * 2 ** (attempt - 1)))
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)
        raise RuntimeError(f"Cached failure: all attempts exhausted for height {h} {endpoint}; no successful response")


def coinbase(s, h, row=None):
    cached = s.get("coinbase", h)
    if cached:
        return cached
    header = s.get("header", h)
    if header:
        blockhash, hash_ref = header["id"], header["response"]
    else:
        blockhash, hash_ref = s.fetch(h, f"/block-height/{h}", False)
    assert len(blockhash) == 64 and int(blockhash, 16) >= 0
    txs, tx_ref = s.fetch(h, f"/block/{blockhash}/txs/0")
    return record_coinbase(s, h, txs, blockhash, hash_ref, tx_ref, row)


def record_coinbase(s, h, txs, blockhash, hash_ref, tx_ref, row=None):
    tx = txs[0]
    assert len(tx["vin"]) == 1 and tx["vin"][0]["is_coinbase"], "first transaction not coinbase"
    assert tx["status"]["confirmed"] and tx["status"]["block_height"] == h and tx["status"]["block_hash"] == blockhash
    assert txid_from_json(tx) == tx["txid"], "reconstructed txid differs"
    out = tx["vout"][0]
    script = out["scriptpubkey"].lower()
    key = script[2:-2] if len(script) == 134 and script.startswith("4104") and script.endswith("ac") else None
    result = {"height": h, "block_hash": blockhash, "txid": tx["txid"], "output_index": 0,
              "scriptpubkey": script, "chain_pubkey": key, "value_sats": out["value"],
              "output_count": len(tx["vout"]), "coinbase_total_sats": sum(v["value"] for v in tx["vout"]),
              "scriptsig": tx["vin"][0]["scriptsig"], "sequence": tx["vin"][0]["sequence"],
              "txid_reconstructed": True, "page_txids": [t["txid"] for t in txs],
              "hash_response": hash_ref, "tx_response": tx_ref, **extra_nonce(tx["vin"][0]["scriptsig"])}
    if row is not None:
        expected = row["Address/Pubkey"].lower()
        expected_sats = int(Decimal(row["Amount (BTC)"]) * 100000000)
        result.update(csv_pubkey=expected, csv_value_sats=expected_sats,
                      pubkey_match=script == "41" + expected + "ac", amount_match=out["value"] == expected_sats)
    s.put("coinbase", h, result)
    return result


def spend(s, h):
    if s.get("spend", h):
        return
    cb = s.get("coinbase", h)
    if not cb:
        raise ValueError("coinbase unavailable")
    outs, ref = s.fetch(h, f"/tx/{cb['txid']}/outspends")
    record_spend(s, h, outs, ref)


def record_spend(s, h, outs, ref):
    cb = s.get("coinbase", h)
    assert len(outs) == cb["output_count"] and type(outs[0]["spent"]) is bool
    value = {"height": h, "coinbase_txid": cb["txid"], "value_sats": cb["value_sats"], "output_index": 0, **outs[0], "response": ref}
    # Independently reconstruct a reported spender and verify its actual input.
    if outs[0]["spent"]:
        tx, spender_ref = s.fetch(h, f"/tx/{outs[0]['txid']}")
        assert txid_from_json(tx) == outs[0]["txid"]
        vin = tx["vin"][outs[0]["vin"]]
        assert vin["txid"] == cb["txid"] and vin["vout"] == 0
        value.update(coinbase_txid=cb["txid"], spending_txid=outs[0]["txid"], spending_input_verified=True, spender_response=spender_ref)
    s.put("spend", h, value)


def bulk_coinbases(s, hs, rows):
    if all(s.get("coinbase", h) for h in hs):
        return
    scripts = ["41" + rows[h]["Address/Pubkey"].lower() + "ac" for h in hs]
    script_hashes = [sha(bytes.fromhex(script)) for script in scripts]
    # Keep stable batch membership across resumes; a partial batch reuses its response.
    try:
        txs, ref = s.fetch(hs[0], "/scripthashes/txs", hosts=HOSTS[:1], request_body=script_hashes)
        assert isinstance(txs, list)
        for tx in txs:
            status = tx.get("status", {})
            h = status.get("block_height")
            if h not in hs or s.get("coinbase", h):
                continue
            if not tx.get("vin") or not tx["vin"][0].get("is_coinbase"):
                continue
            header = s.get("header", h)
            if not header:
                continue
            # This is a candidate transaction; inclusion is independently verified below.
            try:
                record_coinbase(s, h, [tx], header["id"], header["response"], ref, rows[h])
            except Exception as e:
                s.failure("bulk_candidate", h, str(e))
    except Exception as e:
        print(json.dumps({"bulk_coinbase_fallback": hs[0], "reason": str(e)}), flush=True)
    # No completeness assumption about script-history pagination. Every absent candidate
    # is fetched directly by block hash, which detects missing/wrong CSV keys.
    for h in hs:
        if not s.get("coinbase", h):
            coinbase(s, h, rows[h])
        inclusion(s, h)


def bulk_spends(s, hs):
    if all(s.get("spend", h) for h in hs):
        return
    cbs = [s.get("coinbase", h) for h in hs]
    if not all(cbs):
        for h, cb in zip(hs, cbs):
            if cb:
                spend(s, h)
        return
    endpoint = "/txs/outspends?txids=" + ",".join(cb["txid"] for cb in cbs)
    try:
        values, ref = s.fetch(hs[0], endpoint, hosts=HOSTS[:1])
        assert len(values) == len(hs), "bulk outspend count mismatch"
        for i, (h, outs) in enumerate(zip(hs, values)):
            if not s.get("spend", h):
                record_spend(s, h, outs, {**ref, "batch_index": i})
    except Exception as e:
        print(json.dumps({"bulk_spend_fallback": hs[0], "reason": str(e)}), flush=True)
        for h in hs:
            spend(s, h)


def headers(s, end):
    if all(s.get("header", h) for h in range(max(0, end - 9), end + 1)):
        return
    blocks, ref = s.fetch(end, f"/blocks/{end}")
    expected = list(range(end, max(-1, end - 10), -1))
    assert [b["height"] for b in blocks] == expected, "unexpected header batch"
    for b in blocks:
        b["header_hex"] = check_header(b)
        b["response"] = ref
        s.put("header", b["height"], b)


def inclusion(s, h):
    if s.get("inclusion", h):
        return
    cb, header = s.get("coinbase", h), s.get("header", h)
    assert cb and header, "coinbase/header missing"
    assert cb["block_hash"] == header["id"], "height/hash disagreement"
    txids = cb["page_txids"]
    result = {"height": h, "verified": True}
    if len(txids) == header["tx_count"]:
        assert merkle_root(txids) == header["merkle_root"], "Merkle root mismatch"
        result["method"] = "complete_page_merkle_tree"
    else:
        proof, ref = s.fetch(h, f"/tx/{cb['txid']}/merkle-proof")
        assert proof["block_height"] == h and proof["pos"] == 0
        value, pos = bytes.fromhex(cb["txid"])[::-1], proof["pos"]
        for sibling in proof["merkle"]:
            sibling = bytes.fromhex(sibling)[::-1]
            value = dh((sibling + value) if pos & 1 else (value + sibling))
            pos >>= 1
        assert value[::-1].hex() == header["merkle_root"], "Merkle proof mismatch"
        result.update(method="merkle_branch", response=ref)
    s.put("inclusion", h, result)


def selection(heights):
    path = OUT / "selection.json"
    if path.exists():
        data = json.loads(path.read_text())
        assert data["pinned_height_sha256"] == PIN
        return data
    present = set(heights)
    rng = random.Random(20260927)
    # Equal 60-per-1000-height-bin sampling, without replacement, excludes listed.
    controls = []
    for start in range(0, 50000, 1000):
        candidates = [h for h in range(max(3, start), min(49974, start + 1000)) if h not in present]
        controls.extend(rng.sample(candidates, 60))
    gaps = sorted(((b - a - 1, a + 1, b - 1) for a, b in zip(heights, heights[1:]) if b - a > 1), reverse=True)[:10]
    boundary = {0, 1, 2, *range(49974, 50274), *range(54016, 54617)}
    for _, a, b in gaps:
        boundary.update(range(a, b + 1))
    data = {"pinned_height_sha256": PIN, "seed": 20260927, "control_method": "60 uniformly sampled unlisted heights without replacement per 1000-height bin; partial edge bins clipped to 3..49973", "controls": sorted(controls), "boundary": sorted(boundary), "largest_ten_gaps": gaps, "maximum_header_height": 54619}
    atomic_json(path, data)
    return data


def progress(s, phase, done, total, started, errors=0):
    with s.lock:
        counts = dict(s.db.execute("SELECT kind,COUNT(*) FROM results GROUP BY kind"))
        responses = s.db.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        failures = s.db.execute("SELECT COUNT(*) FROM failures").fetchone()[0]
    obj = {"updated_at": now(), "pid": os.getpid(), "phase": phase, "done": done, "total": total, "phase_errors": errors, "elapsed_seconds": round(time.monotonic() - started, 1), "result_counts": counts, "cached_responses": responses, "failure_records": failures}
    atomic_json(OUT / "progress.json", obj)
    print(json.dumps(obj), flush=True)


def batch(s, phase, values, fn, workers, started):
    errors = 0
    progress(s, phase, 0, len(values), started)
    for start in range(0, len(values), 32):
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(fn, h): h for h in values[start:start + 32]}
            for future in concurrent.futures.as_completed(futures):
                h = futures[future]
                try:
                    future.result()
                    with s.lock, s.db:
                        s.db.execute("DELETE FROM failures WHERE stage=? AND height=?", (phase, h))
                except Exception as e:
                    errors += 1
                    s.failure(phase, h, f"{type(e).__name__}: {e}")
                    print(json.dumps({"at": now(), "phase": phase, "height": h, "error": str(e)}), flush=True)
        progress(s, phase, min(start + 32, len(values)), len(values), started, errors)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["controls", "full"], required=True)
    p.add_argument("--rate", type=float, default=2.0)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--transport", choices=["bulk", "individual"], default="bulk")
    args = p.parse_args()
    assert 0 < args.rate <= 3 and 1 <= args.workers <= 4
    OUT.mkdir(parents=True, exist_ok=True)
    # OS-held lock releases on crash, unlike a stale PID-only sentinel.
    lockfile = (OUT / "cache.lock").open("a+b")
    lockfile.seek(0)
    lockfile.write(b"0")
    lockfile.flush()
    lockfile.seek(0)
    if os.name == "nt":
        import msvcrt
        msvcrt.locking(lockfile.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
    started = time.monotonic()
    heights, rows = inputs()
    s = Store(args.rate)
    controls = []
    for h, expected in CONTROLS.items():
        cb = coinbase(s, h, rows[h])
        assert cb["value_sats"] == expected and cb["coinbase_total_sats"] == expected, f"CONTROL FAILED {h}: amount"
        assert cb["pubkey_match"] and cb["amount_match"], f"CONTROL FAILED {h}: CSV"
        headers(s, (h // 10) * 10 + 9)
        inclusion(s, h)
        controls.append({"height": h, "expected_sats": expected, "chain_sats": cb["value_sats"], "pubkey_match": cb["pubkey_match"], "txid": cb["txid"], "block_hash": cb["block_hash"], "inclusion_verified": True})
        progress(s, "controls", len(controls), 4, started)
    atomic_json(OUT / "controls.json", {"passed": True, "completed_at": now(), "controls": controls})
    if args.mode == "controls":
        return
    sample = selection(heights)
    if args.transport == "bulk":
        # Header preparation eliminates per-height hash requests and anchors bulk candidates.
        batch(s, "headers", list(range(9, sample["maximum_header_height"] + 1, 10)), lambda h: headers(s, h), args.workers, started)
        groups = [heights[i:i + 25] for i in range(0, len(heights), 25)]
        batch(s, "pubkeys_bulk", list(range(len(groups))), lambda i: bulk_coinbases(s, groups[i], rows), args.workers, started)
        spend_groups = [heights[i:i + 50] for i in range(0, len(heights), 50)]
        batch(s, "spends_bulk", list(range(len(spend_groups))), lambda i: bulk_spends(s, spend_groups[i]), args.workers, started)
    else:
        batch(s, "pubkeys", heights, lambda h: coinbase(s, h, rows[h]), args.workers, started)
        batch(s, "spends", heights, lambda h: spend(s, h), args.workers, started)
        batch(s, "headers", list(range(9, sample["maximum_header_height"] + 1, 10)), lambda h: headers(s, h), args.workers, started)
    batch(s, "listed_inclusion", heights, lambda h: inclusion(s, h), args.workers, started)
    batch(s, "classifier_controls", sample["controls"], lambda h: coinbase(s, h), args.workers, started)
    batch(s, "boundary", sample["boundary"], lambda h: coinbase(s, h), args.workers, started)
    batch(s, "sample_inclusion", sorted(set(sample["controls"] + sample["boundary"])), lambda h: inclusion(s, h), args.workers, started)
    # Adjacent-header links across the entire fetched range are checked offline.
    previous = None
    for h in range(sample["maximum_header_height"] + 1):
        header = s.get("header", h)
        if header and previous:
            if header["previousblockhash"] != previous["id"]:
                s.failure("header_link", h, "adjacent header hash mismatch")
        previous = header
    progress(s, "collection_finished", len(heights), len(heights), started)
    s.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    s.db.close()
    print("Collection finished. Run phase2_analyze.py; missing data remain explicitly unknown.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
