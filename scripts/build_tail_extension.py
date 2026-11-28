"""Build the site extension from saved outpoint and Merkle proof receipts."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from audit_tail_outpoints import ROOT, P, H, K, C, eligible, dsha, hv, tx
from phase2_collect import extra_nonce

DOCS = ROOT / "docs"
ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def derive_address(pubkey):
    h = hashlib.new("ripemd160", hashlib.sha256(pubkey).digest()).digest()
    payload = b"\0" + h
    encoded = payload + dsha(payload)[:4]
    n, s = int.from_bytes(encoded, "big"), ""
    while n:
        n, digit = divmod(n, 58)
        s = ALPHABET[digit] + s
    return "1" * (len(encoded) - len(encoded.lstrip(b"\0"))) + s, h.hex()


def verify_receipt(h, r):
    b, k = H[h], K[h]
    proof = r["merkle"]
    predicted, txid, value = tx(h)
    raw = bytes.fromhex(r["coinbase_hex"])
    if (r["coinbase_txid"] != txid or dsha(raw)[::-1].hex() != txid
            or not raw.endswith(predicted[-81:]) or r["value_sats"] != value
            or C[h]["coinbase_txid"] != txid or int(C[h]["value_sats"]) != value):
        raise ValueError(f"Coinbase verification failed at {h}")
    leaf = hv(txid)
    for sibling in proof["merkle"]:
        leaf = dsha(leaf + hv(sibling))
    if proof["block_height"] != h or proof["pos"] != 0 or leaf != hv(b["merkle_root"]):
        raise ValueError(f"Merkle verification failed at {h}")
    if r["block_hash"] != b["block_hash"] or r["outspend"]["spent"] is not False:
        raise ValueError(f"Blocked or spent output at {h}")
    return bytes.fromhex(k["output_script"][2:-2])


def build(receipt_path, tip_height, base_manifest=None):
    meta_path = DOCS / "data.json"
    manifest = json.loads((base_manifest or meta_path).read_text())
    meta = manifest["meta"]
    previous_extension = meta.get("tail_additions_count", 0)
    if previous_extension:
        raise ValueError("Rebuild against the pre-extension curation manifest, not an already extended copy")
    records, seen = [], set()
    with open(receipt_path, newline="", encoding="utf-8") as f:
        receipts = list(csv.DictReader(f))
    for flat in sorted(receipts, key=lambda r: int(r["height"])):
        h = int(flat["height"])
        if h not in eligible or h in seen or h in manifest["excluded_heights"]:
            raise ValueError(f"Unexpected tail height {h}")
        seen.add(h)
        row = dict(flat, value_sats=int(flat["value_sats"]), merkle=json.loads(flat["merkle"]),
                   outspend=json.loads(flat["outspend"]))
        pubkey = verify_receipt(h, row)
        addr, hash160 = derive_address(pubkey)
        b, p = H[h], P[h]
        records.append([h, addr, pubkey.hex(), hash160, row["coinbase_txid"], row["block_hash"],
                        row["value_sats"], row["value_sats"], 0, None, None, None,
                        b["timestamp"].removesuffix("+00"), int(b["nonce"], 16),
                        extra_nonce(b["coinbase_param"])["extra_nonce"], "tail_high_confidence",
                        float(p["posterior_m10"]), int(b["transaction_count"] == "1"), "Phase 10 robust",
                        "Counter track, nonce band and nonce clock agree. Merkle proof verified; output 0 unspent at "
                        + row["checked_utc"] + "."])
    if not records:
        raise ValueError("No verified tail records")
    if len({r[1] for r in records}) != len(records):
        raise ValueError("Duplicate extension addresses")
    sat = sum(r[6] for r in records)
    meta.update(count=meta["count"]+len(records), tail_additions_count=len(records),
                last_height=records[-1][0], total_original_sats=meta["total_original_sats"]+sat,
                total_balance_sats=meta["total_balance_sats"]+sat,
                unspent_count=meta["unspent_count"]+len(records),
                tail_spend_checked_utc=max(r["checked_utc"] for r in receipts),
                tail_tip_height_observed=tip_height)
    manifest["tail_file"] = "tail_additions.json"
    (DOCS / "tail_additions.json").write_text(
        '{"records":[\n'+",\n".join(json.dumps(r,separators=(",",":")) for r in records)+'\n]}\n')
    meta_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("receipt_csv")
    ap.add_argument("tip_height", type=int)
    ap.add_argument("--base-manifest", type=Path)
    a = ap.parse_args()
    build(a.receipt_csv, a.tip_height, a.base_manifest)
