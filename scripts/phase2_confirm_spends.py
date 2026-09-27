"""Only live-check the spend anomalies found by BigQuery; no exhaustive scraping."""
import csv
import json
from pathlib import Path
from decimal import Decimal
import phase2_collect as chain

OUT = chain.ROOT / "analysis/phase2_bigquery"
chain.OUT = OUT


def main():
    with (OUT / "results/pubkeys.csv").open(newline="") as f:
        pubkeys = {int(r["height"]): r for r in csv.DictReader(f)}
    with (OUT / "results/spends.csv").open(newline="") as f:
        hits = list(csv.DictReader(f))
    store = chain.Store(2)
    confirmed = []
    for hit in hits:
        h = int(hit["coinbase_height"])
        cb = pubkeys[h]
        store.put("coinbase", h, {"txid": cb["coinbase_txid"], "value_sats": int(Decimal(cb["output_value_raw"])), "output_count": int(cb["output_count"]), "source": "results/pubkeys.csv"})
        result = {**hit, "value_sats": cb["output_value_raw"], "live_confirmed": False}
        try:
            chain.spend(store, h)
            live = store.get("spend", h)
            assert live["spent"] and live["spending_input_verified"]
            assert live["spending_txid"] == hit["spending_txid"]
            assert live["vin"] == int(hit["spending_input_index"])
            assert live["status"]["confirmed"] and live["status"]["block_height"] == int(hit["spending_height"])
            result.update(live_confirmed=True, observed_at=live["response"]["observed_at"], provider=live["response"]["host"], outspend_response_id=live["response"]["response_id"], spender_response_id=live["spender_response"]["response_id"])
        except Exception as e:
            result["error"] = str(e)
        confirmed.append(result)
        print(json.dumps({"height": h, "live_confirmed": result["live_confirmed"], "error": result.get("error")}), flush=True)
    chain.atomic_json(OUT / "live_spend_confirmations.json", confirmed)
    fields = list(dict.fromkeys(k for r in confirmed for k in r))
    with (OUT / "results/confirmed_spends.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(confirmed)
    store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    store.db.close()


if __name__ == "__main__":
    main()
