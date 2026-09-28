"""Bounded BigQuery collection, reusing immutable Phase 2 cache machinery."""
import argparse,csv,json,sqlite3,zlib
from pathlib import Path
import phase2_bigquery as bq
csv.field_size_limit(50_000_000)
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase3';bq.OUT=OUT
def read(p):
 with p.open(newline='',encoding='utf8') as f:return list(csv.DictReader(f))
def strings(name,values):return {'name':name,'parameterType':{'type':'ARRAY','arrayType':{'type':'STRING'}},'parameterValue':{'arrayValues':[{'value':x} for x in sorted(set(values))]}}
def scalar(name,x):return {'name':name,'parameterType':{'type':'STRING'},'parameterValue':{'value':x}}
def query(name,sql,params):
 c=bq.BigQuery();c.query(name,sql,params,dry=True,max_bytes=3_000_000_000_000)
 return c.query(name,sql,params,dry=False,max_bytes=3_000_000_000_000)
def seeds():
 p=OUT/'trace_seed_transactions.json'
 if p.exists():return json.loads(p.read_text())
 db=sqlite3.connect('file:'+str(ROOT/'analysis/phase2_bigquery/cache/chain.sqlite3')+'?mode=ro',uri=True)
 needed={r['spending_txid'] for r in read(ROOT/'analysis/phase2_bigquery/results/spends.csv')};tx={}
 for endpoint,body in db.execute('SELECT endpoint,body_zlib FROM responses WHERE status=200'):
  if endpoint.startswith('/tx/') and not endpoint.endswith('/outspends'):
   r=json.loads(zlib.decompress(body))
   if r.get('txid') in needed:tx[r['txid']]=r
 assert set(tx)==needed
 p.write_text(json.dumps(tx,indent=2)+'\n',encoding='utf8',newline='\n');return tx
def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['funding','trace']);a=ap.parse_args();OUT.mkdir(exist_ok=True)
 if a.action=='funding':
  rs=read(ROOT/'patoshi_p2pkh_addresses.csv');scripts=['76a914'+r['hash160']+'88ac' for r in rs]
  query('funded_keyhashes',(OUT/'sql/funded_keyhashes.sql').read_text(),[strings('scripts',scripts)]);return
 frontier=set(seeds());seen=set(frontier)
 # Three generations AFTER the first spend. Every branch included, no change heuristics.
 for depth in range(1,4):
  if not frontier:break
  if len(frontier)>5000:raise RuntimeError('Branching exceeded 5000 transactions; report frontier instead of silently pruning')
  edges=query(f'trace_edges_{depth}',(OUT/'sql/trace_edges.sql').read_text(),[strings('txids',frontier)])
  targets=sorted({r['spending_txid'] for r in edges}-seen)
  if not targets:break
  start=min(r['spending_time'] for r in edges);end=max(r['spending_time'] for r in edges)
  rows=query(f'trace_transactions_{depth}',(OUT/'sql/trace_transactions.sql').read_text(),[strings('txids',targets),scalar('start',start),scalar('end',end)])
  assert {r['txid'] for r in rows}==set(targets),'missing traced transaction'
  seen.update(targets);frontier=set(targets)
 (OUT/'trace_frontier.json').write_text(json.dumps({'maximum_generations_after_first_spend':3,'unqueried_frontier':sorted(frontier),'unique_transactions':len(seen)},indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
