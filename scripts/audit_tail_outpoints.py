"""Recheck high-confidence post-cutoff coinbase outpoints: python scripts/audit_tail_outpoints.py OUTPUT_DIR."""
import csv, json, datetime, pathlib, hashlib, struct, urllib.request, urllib.error, concurrent.futures, threading, time, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
def csvat(p): return {int(r['height']):r for r in csv.DictReader((ROOT/p).open())}
P=csvat('analysis/phase10_clock_model/posterior_m10.csv'); C=csvat('analysis/phase5/census_blocks.csv'); H=csvat('analysis/phase2_bigquery/results/headers.csv'); K=csvat('analysis/phase8/results/coinbase_pubkeys.csv')
def dsha(b): return hashlib.sha256(hashlib.sha256(b).digest()).digest()
def hv(s): return bytes.fromhex(s)[::-1]
eligible={h for h,p in P.items() if h>49973 and p['tier_m10']=='added_robust' and float(p['posterior'])>=.9 and p['track_fit']=='True' and p['clock_inconsistent']=='True' and p['band']=='True' and p['co_spend_label'] in ('unclustered','patoshi') and p['spent']=='False'}
assert len(eligible)==273, len(eligible)
lock=threading.Lock(); last=0
BASE='https://mempool.space/api/'
def get(path, decode=True):
 global last
 for attempt in range(2):
  with lock:
   time.sleep(max(0,last+.32-time.monotonic())); last=time.monotonic()
  try:
   with urllib.request.urlopen(urllib.request.Request(BASE+path,headers={'Cache-Control':'no-cache','User-Agent':'Patoshi public outpoint audit'}),timeout=12) as r:
    v=r.read()
    return json.loads(v) if decode else v.decode().strip()
  except urllib.error.HTTPError as e:
   if e.code==429:
    with lock: last=time.monotonic()+max(30,int(e.headers.get('Retry-After','30') or '30'))
   elif e.code not in (502,503,504): raise
   if attempt: raise
  except (TimeoutError,urllib.error.URLError):
   if attempt:raise
def tx(h):
 k=K[h]; cs=bytes.fromhex(H[h]['coinbase_param']); sc=bytes.fromhex(k['output_script']); value=int(k['value_raw'])
 assert len(cs)<253 and len(sc)==67 and sc[:2]==b'A\x04' and sc[-1:]==b'\xac' and k['output_index']=='0'
 txid=k['coinbase_txid']
 pred=struct.pack('<I',1)+b'\x01'+bytes(32)+b'\xff'*4+bytes([len(cs)])+cs+b'\xff'*4+b'\x01'+struct.pack('<Q',value)+bytes([len(sc)])+sc+bytes(4)
 return pred, txid, value
def audit(h):
 k=K[h]; b=H[h]; pred,txid,value=tx(h); assert C[h]['coinbase_txid']==txid and int(C[h]['value_sats'])==value and C[h]['spent']=='False'
 if dsha(pred)[::-1].hex()!=txid:
  raw=bytes.fromhex(get('tx/'+txid+'/hex',False))
  assert dsha(raw)[::-1].hex()==txid and raw.endswith(pred[-(1+8+1+67+4):]), (h,'canonical reward transaction mismatch')
 else: raw=pred
 leaf=hv(txid)
 if b['transaction_count']=='1': proof={'block_height':h,'merkle':[],'pos':0}
 else: proof=get('tx/'+txid+'/merkle-proof')
 assert proof['block_height']==h and proof['pos']==0
 for sibling in proof['merkle']: leaf=dsha(leaf+hv(sibling))
 assert leaf==hv(b['merkle_root']), (h,'merkle proof mismatch')
 parent=H[h-1]['block_hash']; t=int(datetime.datetime.fromisoformat(b['timestamp']).timestamp())
 header=struct.pack('<I',int(b['version']))+hv(parent)+leaf+struct.pack('<III',t,int(b['bits'],16),int(b['nonce'],16))
 assert dsha(header)[::-1].hex()==b['block_hash'], (h,'header mismatch')
 response=get('tx/'+txid+'/outspend/0')
 assert type(response.get('spent')) is bool
 return {'height':h,'coinbase_txid':txid,'value_sats':value,'block_hash':b['block_hash'],'coinbase_hex':raw.hex(),'merkle':proof,'outspend':response,'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
def main():
 O=pathlib.Path(sys.argv[1]); O.mkdir(parents=True,exist_ok=True)
 tip_start=int(get('blocks/tip/height',False))
 print('start',len(eligible),tip_start,flush=True)
 result=[]; errors={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex, (O/'receipts.jsonl').open('w') as fd:
  jobs={ex.submit(audit,h):h for h in sorted(eligible)}
  for i,f in enumerate(concurrent.futures.as_completed(jobs),1):
   h=jobs[f]
   try:
    row=f.result(); result.append(row); fd.write(json.dumps(row)+'\n');fd.flush()
   except Exception as e: errors[h]=repr(e);print('error',h,repr(e),flush=True)
   if i%50==0:print(i,len(result),len(errors),flush=True)
 meta={'start_candidates':len(eligible),'matched':len(result),'errors':errors,'spent':sum(r['outspend']['spent'] for r in result),'sum_sats':sum(r['value_sats'] for r in result),'tip_height_start':tip_start,'tip_height_end':int(get('blocks/tip/height',False))}
 (O/'receipt_summary.json').write_text(json.dumps(meta,indent=2)+'\n');print(meta,flush=True)

if __name__=='__main__':
 main()
