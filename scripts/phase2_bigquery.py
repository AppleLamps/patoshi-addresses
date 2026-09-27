"""BigQuery REST evidence cache; uses existing gcloud ADC, never explorer scraping."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis/phase2_bigquery"
API = "https://bigquery.googleapis.com/bigquery/v2"
GCLOUD = r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
PROJECT = "gen-lang-client-0469054007"


def stamp():
    return datetime.now(timezone.utc).isoformat()


class BigQuery:
    def __init__(self):
        self.token = None
        self.token_time = 0

    def auth(self):
        if self.token is None or time.monotonic() - self.token_time > 2400:
            result = subprocess.run([GCLOUD, "auth", "application-default", "print-access-token"], capture_output=True, text=True)
            if result.returncode or not result.stdout.strip():
                raise RuntimeError("Application-default authentication unavailable. Stop; no explorer fallback permitted.")
            self.token = result.stdout.strip()
            self.token_time = time.monotonic()
        return self.token

    def request(self, name, path, payload=None):
        cache = OUT / "cache" / (name + ".json")
        cache.parent.mkdir(parents=True, exist_ok=True)
        if cache.exists():
            record = json.loads(cache.read_text(encoding="utf-8"))
            if record["status"] != 200:
                raise RuntimeError(f"Cached BigQuery error {record['status']}: {record['body']}")
            return record["body"]
        body = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(API + path, data=body, headers={"Authorization": "Bearer " + self.auth(), "Content-Type": "application/json"})
        status, raw = 0, b""
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                status, raw = response.status, response.read()
        except urllib.error.HTTPError as e:
            status, raw = e.code, e.read()
        record = {"fetched_at": stamp(), "url": API + path, "method": "POST" if payload is not None else "GET", "request": payload, "status": status, "raw_sha256": hashlib.sha256(raw).hexdigest(), "body": json.loads(raw)}
        cache.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
        if status != 200:
            raise RuntimeError(f"BigQuery HTTP {status}: {record['body']}")
        return record["body"]

    def schema(self):
        prefix = "/projects/bigquery-public-data/datasets/crypto_bitcoin"
        tables = self.request("tables", prefix + "/tables?maxResults=1000")
        names = [t["tableReference"]["tableId"] for t in tables.get("tables", [])]
        print(json.dumps({"tables": names}))
        for name in ("blocks", "transactions", "inputs", "outputs"):
            if name not in names:
                print(json.dumps({"table": name, "exists": False}))
                continue
            table = self.request("schema_" + name, prefix + "/tables/" + name)
            print(json.dumps({"table": name, "lastModifiedTime": table.get("lastModifiedTime"), "numRows": table.get("numRows"), "numBytes": table.get("numBytes"), "timePartitioning": table.get("timePartitioning"), "schema": table["schema"]}))

    def query(self, name, sql, parameters=None, dry=True, max_bytes=100_000_000_000):
        identity = hashlib.sha256(json.dumps({"project": PROJECT, "sql": sql, "parameters": parameters or []}, sort_keys=True).encode()).hexdigest()
        results = OUT / "results"
        result_path = results / (name + ".csv")
        meta_path = results / (name + ".metadata.json")
        if result_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text())
            if meta["query_identity_sha256"] != identity:
                raise RuntimeError(f"Query changed for cached result {name}; use a new result name, never silently refetch")
            assert hashlib.sha256(result_path.read_bytes()).hexdigest() == meta["csv_sha256"], "Cached CSV checksum mismatch"
            print(json.dumps({"query": name, "local_cache_reused": True, "rows": meta["rows"]}))
            if dry:
                return {"totalBytesProcessed": meta.get("totalBytesProcessed"), "local_cache_reused": True}
            with result_path.open(newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        payload = {"query": sql, "useLegacySql": False, "location": "US", "useQueryCache": True,
                   "parameterMode": "NAMED", "queryParameters": parameters or [], "dryRun": dry,
                   "maximumBytesBilled": str(max_bytes), "timeoutMs": 10000, "maxResults": 10000}
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        payload["requestId"] = fingerprint[:36]
        key = ("dry_" if dry else "query_") + name + "_" + fingerprint[:16]
        result = self.request(key, f"/projects/{PROJECT}/queries", payload)
        if dry:
            print(json.dumps({"query": name, "dry_run": True, "estimated_bytes": result.get("totalBytesProcessed"), "errors": result.get("errors")}))
            return result
        job = result.get("jobReference")
        attempt = 0
        while not result.get("jobComplete"):
            time.sleep(2)
            attempt += 1
            result = self.request(key + f"_poll{attempt}", f"/projects/{PROJECT}/queries/{job['jobId']}?location=US&timeoutMs=10000&maxResults=10000")
        if result.get("errors"):
            raise RuntimeError(str(result["errors"]))
        fields = [f["name"] for f in result["schema"]["fields"]]
        raw_rows = result.get("rows", [])
        page = 0
        while result.get("pageToken"):
            page += 1
            token = urllib.parse.quote(result["pageToken"], safe="")
            result = self.request(key + f"_page{page}", f"/projects/{PROJECT}/queries/{job['jobId']}?location=US&maxResults=10000&pageToken={token}")
            raw_rows.extend(result.get("rows", []))
        rows = [dict(zip(fields, [v.get("v") for v in row["f"]])) for row in raw_rows]
        results.mkdir(exist_ok=True)
        with (results / (name + ".csv")).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        meta = {"query_identity_sha256": identity, "csv_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(), "rows": len(rows), "jobReference": job, "totalBytesProcessed": result.get("totalBytesProcessed"), "cached_at": stamp()}
        meta_path.write_text(json.dumps(meta, indent=2)+"\n", encoding="utf-8", newline="\n")
        print(json.dumps({"query": name, "rows": len(rows), "job": job, "totalBytesProcessed": result.get("totalBytesProcessed")}))
        return rows


def heights_parameter(heights):
    return [{"name": "heights", "parameterType": {"type": "ARRAY", "arrayType": {"type": "INT64"}}, "parameterValue": {"arrayValues": [{"value": str(h)} for h in heights]}}]


def spend_parameters():
    with (OUT / "results/pubkeys.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    return [{"name": "outpoints", "parameterType": {"type": "ARRAY", "arrayType": {"type": "STRUCT", "structTypes": [{"name": "height", "type": {"type": "INT64"}}, {"name": "txid", "type": {"type": "STRING"}}]}}, "parameterValue": {"arrayValues": [{"structValues": {"height": {"value": r["height"]}, "txid": {"value": r["coinbase_txid"]}}} for r in rows]}}]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["schema", "smoke-dry", "smoke", "pubkeys", "spends-dry", "spends", "context", "headers", "snapshot", "watermarks"])
    args = parser.parse_args()
    client = BigQuery()
    if args.action == "schema":
        client.schema()
    elif args.action in ("smoke", "smoke-dry", "pubkeys", "context"):
        sql = (OUT / "sql/coinbases.sql").read_text()
        if args.action in ("smoke", "smoke-dry"):
            heights = [1, 3, 4, 264, 2817, 10000, 19863, 23079, 28507, 49973]
            name = "smoke"
        elif args.action == "pubkeys":
            from phase2_collect import inputs
            from decimal import Decimal
            smoke_path = OUT / "results/smoke.csv"
            if not smoke_path.exists():
                raise RuntimeError("Run the 10-block smoke test before the full query")
            with smoke_path.open(newline="") as f:
                smoke_rows = {int(r["height"]): r for r in csv.DictReader(f)}
            assert len(smoke_rows) == 10
            for h, expected in {2817: 5201000000, 19863: 5014000000, 23079: 5012000000, 28507: 5022000000}.items():
                assert Decimal(smoke_rows[h]["output_value_raw"]) == expected, f"Smoke control failed: {h}"
            heights, _ = inputs()
            name = "pubkeys"
            client.query(name, sql, heights_parameter(heights), dry=True)
        else:
            selection = json.loads((ROOT / "analysis/phase2/selection.json").read_text())
            heights = sorted(set(selection["controls"] + selection["boundary"]))
            name = "context"
            client.query(name, sql, heights_parameter(heights), dry=True)
        result = client.query(name, sql, heights_parameter(heights), dry=args.action.endswith("dry"))
        if args.action == "smoke":
            assert len(result) == 10, f"Smoke test: expected 10 coinbases, got {len(result)}"
            control = next(r for r in result if int(r["height"]) == 2817)
            from decimal import Decimal
            assert Decimal(control["output_value_raw"]) == 5201000000, "52.01 BTC control failed"
            print(json.dumps({"control_2817_value_raw": control["output_value_raw"], "control_2817_script": control["output_script"]}))
    elif args.action.startswith("spends"):
        sql = (OUT / "sql/spends.sql").read_text()
        client.query("spends", sql, spend_parameters(), dry=args.action.endswith("dry"), max_bytes=1_000_000_000_000)
    else:
        sql = (OUT / ("sql/" + args.action + ".sql")).read_text()
        client.query(args.action, sql, dry=True)
        client.query(args.action, sql, dry=False)
