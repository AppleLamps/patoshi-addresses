"""Targeted confirmation only; bulk data remains BigQuery. Immutable local receipts."""
import csv,json,sqlite3,zlib,random
from decimal import Decimal
from pathlib import Path
import phase2_collect as chain
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase3';chain.OUT=OUT
csv.field_size_limit(50_000_000)
def read(p):
 with p.open(newline='',encoding='utf8') as f:return list(csv.DictReader(f))
def main():
 store=chain.Store(2);old=sqlite3.connect('file:'+str(ROOT/'analysis/phase2_bigquery/cache/chain.sqlite3')+'?mode=ro',uri=True)
 def fetch(h,path):
  hit=old.execute('SELECT body_zlib,id,fetched_at,host FROM responses WHERE height=? AND endpoint=? AND status=200 ORDER BY id LIMIT 1',(h,path)).fetchone()
  if hit:return json.loads(zlib.decompress(hit[0])),{'phase2_response_id':hit[1],'observed_at':hit[2],'host':hit[3]}
  return store.fetch(h,path)
 targets=set(json.loads((OUT/'trace_live_targets.json').read_text()));fund=read(OUT/'results/funded_keyhashes.csv')
 chosen=sorted(fund,key=lambda r:int(Decimal(r['value_sats'])),reverse=True)[:5]+random.Random(3305).sample(fund,10)+[r for r in fund if r['spending_txid']]
 targets.update(r['txid'] for r in chosen);targets.update(r['spending_txid'] for r in chosen if r['spending_txid'])
 alltx={r['txid']:r for d in range(1,4) for r in read(OUT/f'results/trace_transactions_{d}.csv')};receipts=[]
 for txid in sorted(targets):
  record={'kind':'transaction','txid':txid,'confirmed':False}
  try:
   h=int(alltx[txid]['height']) if txid in alltx else next((int(r['height']) for r in chosen if r['txid']==txid),492919)
   t,receipt=fetch(h,'/tx/'+txid);assert chain.txid_from_json(t)==txid
   if txid in alltx:
    expected=alltx[txid];assert t['status']['block_height']==int(expected['height'])
    outputs=json.loads(expected['outputs_json']);assert len(outputs)==len(t['vout'])
    for o in outputs:
     live=t['vout'][int(o['index'])];assert live['scriptpubkey']==o['script_hex'] and live['value']==int(Decimal(str(o['value'])))
   for r in chosen:
    if r['txid']==txid:
     v=t['vout'][int(r['vout'])];assert v['scriptpubkey']==r['script_hex'] and v['value']==int(Decimal(r['value_sats']))
    if r['spending_txid']==txid:assert any(i['txid']==r['txid'] and i['vout']==int(r['vout']) for i in t['vin'])
   record.update(confirmed=True,height=t['status']['block_height'],receipt=receipt)
  except Exception as e:record['error']=str(e)
  receipts.append(record);print(json.dumps(record),flush=True)
 for r in chosen:
  h=int(r['height']);record={'kind':'funding_outpoint','txid':r['txid'],'vout':int(r['vout']),'confirmed':False}
  try:
   spends,receipt=fetch(h,'/tx/'+r['txid']+'/outspends');s=spends[int(r['vout'])]
   if r['spending_txid']:assert s['spent'] and s['txid']==r['spending_txid']
   else:assert not s['spent'] or s.get('status',{}).get('block_height',968903)>968902
   record.update(confirmed=True,live_spent=s['spent'],receipt=receipt)
  except Exception as e:record['error']=str(e)
  receipts.append(record);print(json.dumps(record),flush=True)
 headers={int(r['height']):r for r in read(ROOT/'analysis/phase2_bigquery/results/headers.csv')}
 # Reset observations, neighboring evidence for 37808, and endpoint anchors.
 hs={1755,1756,1757,1767,1768,1770,46771,46776,46781,20342,20442,21308,21467,37738,37804,37808,37809,49797,49867,49957,49973}
 events=read(OUT/'reset_events.csv');robust=[r for r in events if r['moderate']=='True']
 for r in random.Random(3306).sample(robust,5):hs.update([int(r['left_height']),int(r['right_height'])])
 for h in sorted(hs):
  r=headers[h];record={'kind':'header_and_coinbase','height':h,'confirmed':False}
  try:
   header,hr=fetch(h,'/block/'+r['block_hash']);chain.check_header(header)
   assert header['nonce']==int(r['nonce'],16)
   txs,tr=fetch(h,'/block/'+r['block_hash']+'/txs/0');assert txs[0]['vin'][0]['scriptsig']==r['coinbase_param'];assert chain.txid_from_json(txs[0])==txs[0]['txid']
   record.update(confirmed=True,header_receipt=hr,coinbase_receipt=tr)
  except Exception as e:record['error']=str(e)
  receipts.append(record);print(json.dumps(record),flush=True)
 chain.atomic_json(OUT/'live_confirmations.json',receipts);store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)');store.db.close();old.close()
if __name__=='__main__':main()
