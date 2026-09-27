"""Offline verification and statistics from cached BigQuery results."""
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3

import phase2_collect as chain
import phase2_analyze as analysis

OUT = chain.ROOT / "analysis/phase2_bigquery"
analysis.OUT = OUT


def read(name):
    with (OUT / "results" / (name + ".csv")).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def timestamp(value):
    return int(datetime.fromisoformat(value.replace(" ", "T")).timestamp())


def main():
    heights, original = chain.inputs()
    selected = json.loads((chain.ROOT / "analysis/phase2/selection.json").read_text())
    headers = {}
    for row in read("headers"):
        h = int(row["height"])
        header = {"height": h, "id": row["block_hash"], "version": int(row["version"]), "merkle_root": row["merkle_root"], "timestamp": timestamp(row["timestamp"]), "nonce": int(row["nonce"], 16), "bits": int(row["bits"], 16), "tx_count": int(row["transaction_count"]), "previousblockhash": headers[h-1]["id"] if h else "00"*32}
        header["header_hex"] = chain.check_header(header)
        headers[h] = header
    assert list(headers) == list(range(54620)), "incomplete or duplicate header coverage"
    listed = read("pubkeys")
    context = read("context")
    assert len(listed) == 21953 and sorted(int(r["height"]) for r in listed) == heights
    assert sorted(int(r["height"]) for r in context) == sorted(set(selected["controls"] + selected["boundary"]))
    cbs = {}
    verification = []
    failures = []
    for row in listed + context:
        h = int(row["height"])
        header = headers[h]
        outputs = json.loads(row["all_outputs_json"])
        outputs.sort(key=lambda o: o["index"])
        assert [o["index"] for o in outputs] == list(range(len(outputs)))
        tx = {"version": int(row["tx_version"]), "locktime": int(row["lock_time"]), "vin": [{"is_coinbase": True, "scriptsig": row["input_script"], "sequence": int(row["input_sequence"])}], "vout": [{"scriptpubkey": o["script_hex"], "value": int(Decimal(str(o["value"])))} for o in outputs]}
        assert int(row["input_count"]) == 1 and int(row["output_count"]) == len(outputs)
        assert row["output_script"] == tx["vout"][0]["scriptpubkey"]
        assert int(Decimal(row["output_value_raw"])) == tx["vout"][0]["value"]
        assert chain.txid_from_json(tx) == row["coinbase_txid"], f"txid serialization disagreement {h}"
        assert row["block_hash"] == header["id"]
        assert int(row["nonce"], 16) == header["nonce"] and row["merkle_root"] == header["merkle_root"]
        single_tx_proven = header["tx_count"] == 1 and row["coinbase_txid"] == header["merkle_root"]
        if header["tx_count"] == 1:
            assert single_tx_proven, f"single-transaction Merkle root mismatch {h}"
        parsed = chain.extra_nonce(row["input_script"])
        cbs[h] = {"height": h, "txid": row["coinbase_txid"], "scriptsig": row["input_script"], "sequence": int(row["input_sequence"]), **parsed}
        if h not in original:
            continue
        csv_key = original[h]["Address/Pubkey"].lower()
        script = row["output_script"].lower()
        value = int(Decimal(row["output_value_raw"]))
        record = {"height": h, "coinbase_txid": row["coinbase_txid"], "csv_pubkey": csv_key, "chain_script": script, "chain_pubkey": script[2:-2] if script.startswith("4104") and script.endswith("ac") and len(script) == 134 else "", "pubkey_match": script == "41"+csv_key+"ac", "value_sats": value, "amount_match": value == int(Decimal(original[h]["Amount (BTC)"]) * 100000000), "txid_reconstructed": True, "single_tx_inclusion_proven": single_tx_proven, "block_hash": row["block_hash"]}
        verification.append(record)
    controls = []
    for h, value in chain.CONTROLS.items():
        record = next(r for r in verification if r["height"] == h)
        assert record["value_sats"] == value and record["pubkey_match"] and record["amount_match"]
        controls.append(record)
    analysis.csv_out("verification.csv", verification, list(verification[0]))
    analysis.csv_out("pubkey_mismatches.csv", [r for r in verification if not r["pubkey_match"]], list(verification[0]))
    analysis.csv_out("amount_mismatches.csv", [r for r in verification if not r["amount_match"]], list(verification[0]))
    chain.atomic_json(OUT / "controls.json", controls)
    hits = read("spends")
    confirmations = json.loads((OUT / "live_spend_confirmations.json").read_text())
    confirmed = {int(r["coinbase_height"]): r for r in confirmations if r["live_confirmed"]}
    hit_by_height = {int(r["coinbase_height"]): r for r in hits}
    assert len(hits) == len(hit_by_height), "duplicate spend references require review"
    statuses = []
    for record in verification:
        h = record["height"]
        hit = hit_by_height.get(h)
        statuses.append({"height": h, "coinbase_txid": record["coinbase_txid"], "output_index": 0, "value_sats": record["value_sats"], "dataset_status": "spent" if hit else "no_spend_found_in_dataset", "live_confirmed_spend": h in confirmed, "spending_txid": hit["spending_txid"] if hit else "", "spending_height": hit["spending_height"] if hit else "", "spending_timestamp": hit["spending_timestamp"] if hit else "", "observed_at": confirmed[h]["observed_at"] if h in confirmed else ""})
    analysis.csv_out("spend_status_all.csv", statuses, list(statuses[0]))
    classifier = analysis.classifier(heights, cbs, headers, selected)
    temporal = analysis.temporal(heights, headers, 1999)
    # Match available prior live control anchors without any network calls.
    anchors = []
    original_cache = chain.ROOT / "analysis/phase2/cache/chain.sqlite3"
    if original_cache.exists():
        db = sqlite3.connect(original_cache.as_uri()+"?mode=ro", uri=True)
        for h in chain.CONTROLS:
            live = json.loads(db.execute("SELECT data FROM results WHERE kind='header' AND height=?", (h,)).fetchone()[0])
            assert live["header_hex"] == headers[h]["header_hex"]
            anchors.append(h)
        db.close()
    snapshot = read("snapshot")[0]
    summary = {"generated_at": chain.now(), "pinned_height_sha256": chain.PIN, "source": "BigQuery crypto_bitcoin with live confirmation of every spend hit", "snapshot": {"query_at": datetime.fromtimestamp(float(snapshot["query_snapshot_at"]), timezone.utc).isoformat(), "maximum_block_height": int(snapshot["maximum_block_height"]), "maximum_block_timestamp": datetime.fromtimestamp(float(snapshot["maximum_block_timestamp"]), timezone.utc).isoformat(), "blocks_available": int(snapshot["blocks_available"])}, "counts": {"listed": len(verification), "pubkey_matches": sum(r["pubkey_match"] for r in verification), "amount_matches": sum(r["amount_match"] for r in verification), "listed_single_tx_inclusions_proven": sum(r["single_tx_inclusion_proven"] for r in verification), "coinbase_txids_reconstructed_including_context": len(cbs), "linked_headers_hash_and_pow_validated": len(headers), "live_control_header_anchors": anchors, "spend_hits": len(hits), "live_confirmed_spends": len(confirmed), "no_spend_found_in_dataset": len(heights)-len(hit_by_height), "spent_satoshis": sum(r["value_sats"] for r in verification if r["height"] in confirmed), "total_coinbase_satoshis": sum(r["value_sats"] for r in verification)}, "classifier": classifier, "temporal": temporal}
    summary["table_watermarks"] = read("watermarks")
    candidate_file = OUT / "live_candidate_confirmations.json"
    if candidate_file.exists():
        candidates = json.loads(candidate_file.read_text())
        summary["live_candidate_confirmations"] = {"checked": len(candidates), "confirmed": sum(r["confirmed"] for r in candidates)}
    chain.atomic_json(OUT / "summary.json", summary)
    # The anomaly API cache is separate from the abandoned general collector.
    api_cache = OUT / "cache/chain.sqlite3"
    if api_cache.exists():
        db = sqlite3.connect(api_cache.as_uri()+"?mode=ro", uri=True)
        chain.atomic_json(OUT / "api_cache_manifest.json", analysis.manifest(db))
        db.close()
    # Every query result, request and response is locally fingerprinted.
    manifest = []
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.suffix != ".log" and path.name not in ("manifest.json", "chain.sqlite3-shm", "chain.sqlite3-wal"):
            manifest.append({"path": str(path.relative_to(ROOT)).replace('\\','/'), "bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    chain.atomic_json(OUT / "manifest.json", {"generated_at": chain.now(), "files": manifest})
    print(json.dumps(summary, indent=2))


ROOT = chain.ROOT
if __name__ == "__main__":
    main()
