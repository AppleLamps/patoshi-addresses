"""Phase 5 co-spend census: one BigQuery query, reusing the immutable Phase 2 cache machinery.

    python scripts/phase5_bigquery.py census             # dry run only: validates the SQL, prints bytes and cost
    python scripts/phase5_bigquery.py census --execute   # dry run, then the billed query, capped at --max-tb
    python scripts/phase5_bigquery.py census --semijoin  # same output without the whole-table window, if BigQuery
                                                         # reports exceeded resources (may bill two input scans)

Authentication is gcloud application-default credentials, as in Phase 2. Set GCLOUD to the gcloud executable when
it is not at the Phase 2 Windows path, and BQ_PROJECT to bill a different project. Where gcloud is unavailable, set
GOOGLE_APPLICATION_CREDENTIALS to a service-account JSON key file; it is read in place and never copied.
"""
import argparse, base64, json, os, time, urllib.parse, urllib.request
from pathlib import Path
import phase2_bigquery as bq

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase5'
USD_PER_TIB = 6.25   # BigQuery on-demand list price; the first 1 TiB each month is free
SCOPE = 'https://www.googleapis.com/auth/bigquery'


def service_account_token(path):
    """OAuth access token from a service-account key via the signed-JWT grant (RFC 7523)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    key = json.loads(Path(path).read_text(encoding='utf8'))
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b'=')
    now = int(time.time())
    claims = {'iss': key['client_email'], 'scope': SCOPE, 'aud': key['token_uri'], 'iat': now, 'exp': now + 3600}
    unsigned = b64(json.dumps({'alg': 'RS256', 'typ': 'JWT'}).encode()) + b'.' + b64(json.dumps(claims).encode())
    signer = serialization.load_pem_private_key(key['private_key'].encode(), password=None)
    jwt = unsigned + b'.' + b64(signer.sign(unsigned, padding.PKCS1v15(), hashes.SHA256()))
    body = urllib.parse.urlencode({'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer', 'assertion': jwt.decode()})
    with urllib.request.urlopen(urllib.request.Request(key['token_uri'], data=body.encode()), timeout=60) as r:
        return json.loads(r.read())['access_token']


class ServiceAccountBigQuery(bq.BigQuery):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def auth(self):
        if self.token is None or time.monotonic() - self.token_time > 2400:
            self.token = service_account_token(self.path)
            self.token_time = time.monotonic()
        return self.token


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('action', choices=['census'])
    ap.add_argument('--execute', action='store_true', help='run the billed query after the dry run')
    ap.add_argument('--semijoin', action='store_true', help='use the fallback SQL with identical output')
    ap.add_argument('--max-tb', type=float, default=2.0, help='maximumBytesBilled, in TB (default 2)')
    a = ap.parse_args()
    bq.OUT = OUT
    bq.GCLOUD = os.environ.get('GCLOUD', bq.GCLOUD)
    bq.PROJECT = os.environ.get('BQ_PROJECT', bq.PROJECT)
    sql = (OUT / ('sql/cospend_census_semijoin.sql' if a.semijoin else 'sql/cospend_census.sql')).read_text(encoding='utf8')
    cap = int(a.max_tb * 1e12)
    sa = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    client = ServiceAccountBigQuery(sa) if sa else bq.BigQuery()
    dry = client.query('cospend_census', sql, dry=True, max_bytes=cap)
    est = dry.get('totalBytesProcessed')
    if est is not None and not dry.get('local_cache_reused'):
        est = int(est)
        print(json.dumps({'estimated_tb': round(est / 1e12, 3), 'estimated_usd_after_free_tier': round(est / 2**40 * USD_PER_TIB, 2),
                          'cap_tb': a.max_tb}))
        if est > cap:
            raise SystemExit(f'Estimate exceeds --max-tb {a.max_tb}; raise the cap deliberately if you accept the cost')
    if not a.execute:
        print('Dry run only. Re-run with --execute to run the query.')
        return
    rows = client.query('cospend_census', sql, dry=False, max_bytes=cap)
    kinds = {}
    for r in rows:
        kinds[r['row_kind']] = kinds.get(r['row_kind'], 0) + 1
    print(json.dumps({'rows': len(rows), 'by_kind': kinds}))
    print('Next: python scripts/phase5_offline.py census manifest')


if __name__ == '__main__':
    main()
