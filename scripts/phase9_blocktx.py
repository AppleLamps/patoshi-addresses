"""Fetch transaction lists for multi-transaction early blocks (Phase 9, gap 2).

    python scripts/phase9_blocktx.py            # dry run only
    python scripts/phase9_blocktx.py --execute  # billed query (tens of MB), cached under analysis/phase9_nonce_clock/results

Authentication as in scripts/phase5_bigquery.py (gcloud, or GOOGLE_APPLICATION_CREDENTIALS).
"""
import argparse, csv, json, os
from pathlib import Path
import phase2_bigquery as bq
from phase5_bigquery import ServiceAccountBigQuery

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase9_nonce_clock'


def heights():
    with (ROOT / 'analysis/phase2_bigquery/results/headers.csv').open(newline='') as f:
        return [int(r['height']) for r in csv.DictReader(f) if int(r['height']) <= 54_619 and int(r['transaction_count']) >= 3]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--max-gb', type=float, default=1.0)
    a = ap.parse_args()
    bq.OUT = OUT
    bq.GCLOUD = os.environ.get('GCLOUD', bq.GCLOUD)
    bq.PROJECT = os.environ.get('BQ_PROJECT', bq.PROJECT)
    sql = (OUT / 'sql/block_transactions.sql').read_text(encoding='utf8')
    params = bq.heights_parameter(heights())
    cap = int(a.max_gb * 1e9)
    sa = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    client = ServiceAccountBigQuery(sa) if sa else bq.BigQuery()
    dry = client.query('block_transactions', sql, params, dry=True, max_bytes=cap)
    est = dry.get('totalBytesProcessed')
    if est is not None and int(est) > cap:
        raise SystemExit(f'Estimate {int(est) / 1e9:.2f} GB exceeds --max-gb {a.max_gb}')
    if a.execute:
        rows = client.query('block_transactions', sql, params, dry=False, max_bytes=cap)
        print(json.dumps({'rows': len(rows)}))


if __name__ == '__main__':
    main()
