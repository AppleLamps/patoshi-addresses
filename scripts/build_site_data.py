"""Build docs/addresses.json, the data file behind the docs/ website.

Each row is [block_height, address, amount_btc, mined_unix, spent, source],
where spent is 1 for a spent coinbase output and 0 otherwise, and source is
0 for the original 21,953-block list and 1 for the confirmed additions.
"""
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read(path):
    with open(ROOT / path, newline="") as f:
        return list(csv.DictReader(f))


def main():
    times = {}
    for r in read("analysis/phase8/revised_list.csv"):
        t = datetime.strptime(r["time_utc"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        times[int(r["height"])] = int(t.timestamp())

    spent = {int(r["height"]) for r in read("analysis/phase2_bigquery/spend_status_all.csv")
             if r["dataset_status"] == "spent"}

    rows = []
    for r in read("patoshi_p2pkh_addresses.csv"):
        h = int(r["block_height"])
        rows.append([h, r["p2pkh_address"], float(r["amount_btc"]), times[h], int(h in spent), 0])
    for r in read("patoshi_additions_confirmed.csv"):
        h = int(r["block_height"])
        rows.append([h, r["p2pkh_address"], float(r["amount_btc"]), times[h], int(r["spent"] == "True"), 1])
    rows.sort()

    out = {
        "spend_watermark": "block 968,902 (2026-09-27) for the original list; 2026-10-11 for additions",
        "columns": ["height", "address", "amount", "mined", "spent", "source"],
        "rows": rows,
    }
    (ROOT / "docs" / "addresses.json").write_text(json.dumps(out, separators=(",", ":")))
    print(len(rows), "rows", sum(r[2] for r in rows), "BTC", sum(r[4] for r in rows), "spent")


if __name__ == "__main__":
    main()
