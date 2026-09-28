"""Fetch the public key of every coinbase at heights 0 to 54,619 for revised_list.csv.

    python scripts/phase8_pubkeys.py            # dry run only: validates the SQL, prints bytes
    python scripts/phase8_pubkeys.py --execute  # billed query (about 15 MB processed), cached under analysis/phase8/results

Authentication is as in scripts/phase5_bigquery.py (gcloud, or GOOGLE_APPLICATION_CREDENTIALS).
"""
import argparse, json, os
from pathlib import Path
import phase2_bigquery as bq
from phase5_bigquery import ServiceAccountBigQuery

OUT = Path(__file__).resolve().parents[1] / 'analysis/phase8'


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--max-gb', type=float, default=50.0)
    a = ap.parse_args()
    bq.OUT = OUT
    bq.GCLOUD = os.environ.get('GCLOUD', bq.GCLOUD)
    bq.PROJECT = os.environ.get('BQ_PROJECT', bq.PROJECT)
    sql = (OUT / 'sql/coinbase_pubkeys.sql').read_text(encoding='utf8')
    cap = int(a.max_gb * 1e9)
    sa = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    client = ServiceAccountBigQuery(sa) if sa else bq.BigQuery()
    dry = client.query('coinbase_pubkeys', sql, dry=True, max_bytes=cap)
    est = dry.get('totalBytesProcessed')
    if est is not None and int(est) > cap:
        raise SystemExit(f'Estimate {int(est) / 1e9:.1f} GB exceeds --max-gb {a.max_gb}')
    if a.execute:
        rows = client.query('coinbase_pubkeys', sql, dry=False, max_bytes=cap)
        print(json.dumps({'rows': len(rows)}))


if __name__ == '__main__':
    main()
