"""Confirm only specific classifier/boundary anomalies, using cached live responses."""
import csv
import json
from decimal import Decimal
import phase2_collect as chain

OUT = chain.ROOT / "analysis/phase2_bigquery"
chain.OUT = OUT


def main():
    with (OUT / "classifier_blocks.csv").open(newline="") as f:
        flags = list(csv.DictReader(f))
    selected = {int(r["height"]) for r in flags if (r["group"] == "listed" and r["inner_range_pass"] == "False") or (r["group"] != "listed" and r.get("combined_fit") == "True")}
    selected.update([21308, 21467])  # Check endpoints of the longest time gap.
    cb = {}
    for name in ("pubkeys", "context"):
        with (OUT / f"results/{name}.csv").open(newline="") as f:
            cb.update({int(r["height"]): r for r in csv.DictReader(f)})
    store = chain.Store(2)
    records = []
    for h in sorted(selected):
        bq = cb[h]
        record = {"height": h, "confirmed": False}
        try:
            header, hr = store.fetch(h, f"/block/{bq['block_hash']}")
            chain.check_header(header)
            txs, tr = store.fetch(h, f"/block/{bq['block_hash']}/txs/0")
            tx = txs[0]
            assert tx["vin"][0]["is_coinbase"]
            assert chain.txid_from_json(tx) == bq["coinbase_txid"]
            assert tx["vin"][0]["scriptsig"] == bq["input_script"]
            assert tx["vout"][0]["scriptpubkey"] == bq["output_script"]
            assert tx["vout"][0]["value"] == int(Decimal(bq["output_value_raw"]))
            assert header["nonce"] == int(bq["nonce"], 16)
            if len(txs) == header["tx_count"]:
                assert chain.merkle_root([t["txid"] for t in txs]) == header["merkle_root"]
            record.update(confirmed=True, block_hash=header["id"], nonce=header["nonce"], timestamp=header["timestamp"], scriptsig=tx["vin"][0]["scriptsig"], txid=tx["txid"], header_response=hr, coinbase_response=tr)
        except Exception as e:
            record["error"] = str(e)
        records.append(record)
        print(json.dumps({"height": h, "confirmed": record["confirmed"]}), flush=True)
    chain.atomic_json(OUT / "live_candidate_confirmations.json", records)
    store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    store.db.close()


if __name__ == "__main__":
    main()
