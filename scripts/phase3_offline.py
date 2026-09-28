"""Offline analytical screens; public-key comparisons only, no spending operations."""
import bisect, collections, csv, hashlib, json, math, sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal
import numpy as np
csv.field_size_limit(50_000_000)
from phase2_collect import extra_nonce
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'analysis/phase3'; P2=ROOT/'analysis/phase2_bigquery'
def offline(event,args):
 if event.startswith('socket.'): raise RuntimeError('Offline analysis forbids sockets')
sys.addaudithook(offline)
def read(p):
 with p.open(newline='',encoding='utf8') as f:return list(csv.DictReader(f))
def save(name,x):
 OUT.mkdir(parents=True,exist_ok=True)
 (OUT/name).write_text(json.dumps(x,indent=2)+'\n',encoding='utf8',newline='\n')
def table(name,rows,fields=None):
 with (OUT/name).open('w',newline='',encoding='utf8') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def stats(x):
 a=np.array(x,float)
 return {'n':len(a),'min':float(a.min()),'median':float(np.median(a)),'mean':float(a.mean()),'p25':float(np.quantile(a,.25)),'p75':float(np.quantile(a,.75)),'max':float(a.max())} if len(a) else {'n':0}
def ts(s):return int(datetime.fromisoformat(s).timestamp())
def stamp(t):return datetime.fromtimestamp(int(t),timezone.utc).isoformat()
def holm(tests):
 prev=0
 for i,r in enumerate(sorted(tests,key=lambda r:r['p'])):
  prev=max(prev,min(1,(len(tests)-i)*r['p']));r['holm_p']=prev
def load():
 listed=read(P2/'results/pubkeys.csv'); listed.sort(key=lambda r:int(r['height']))
 headers={int(r['height']):r for r in read(P2/'results/headers.csv')}
 for h,r in headers.items():
  r['h']=h;r['t']=ts(r['timestamp']);r['en']=extra_nonce(r['coinbase_param']).get('extra_nonce');r['n']=int(r['nonce'],16)
 return listed,headers
def keys(listed):
 out=OUT/'weak_key_screen.json'
 if out.exists():return
 p=2**256-2**32-977;n=0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
 gx=0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798;gy=0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
 targets={int(r['output_script'][4:68],16):(int(r['height']),int(r['output_script'][68:132],16)) for r in listed}
 hits=[];x,y=gx,gy;limit=2**20
 for k in range(1,limit+1):
  if x in targets:
   h,ty=targets[x]
   if ty==y or ty==p-y:hits.append({'height':h,'class':'small_positive_scalar' if ty==y else 'near_curve_order_scalar'})
  if k==limit:break
  slope=((3*x*x)*pow(2*y,-1,p) if x==gx else (y-gy)*pow(x-gx,-1,p))%p
  nx=(slope*slope-x-gx)%p;y=(slope*(x-nx)-y)%p;x=nx
 from cryptography.hazmat.primitives.asymmetric import ec
 assert ec.derive_private_key(limit,ec.SECP256K1()).public_key().public_numbers().x==x
 structured=set([2**k for k in range(256)]+[n-2**k for k in range(256)])
 structured.update(int.from_bytes(bytes([b])*32,'big') for b in range(1,256))
 structured={k for k in structured if 0<k<n}
 for k in structured:
  q=ec.derive_private_key(k,ec.SECP256K1()).public_key().public_numbers()
  if q.x in targets and targets[q.x][1]==q.y:hits.append({'height':targets[q.x][0],'class':'structured_scalar'})
 save('weak_key_screen.json',{'pubkeys':len(listed),'small_positive_range':[1,limit],'near_order_count':limit,'structured_classes':'powers of two, order minus powers of two, repeated-byte scalars','structured_count':len(structured),'hits':hits,'debian_status':'NOT EXHAUSTIVELY TESTED: no applicable complete secp256k1 corpus acquired; date/version is not encoded in a public key'})
def periodicity(listed,perms=1999):
 b=np.array([list(bytes.fromhex(r['output_script'][2:-2]))[1:] for r in listed],float)
 hashes=np.array([list(hashlib.new('ripemd160',hashlib.sha256(bytes.fromhex(r['output_script'][2:-2])).digest()).digest()) for r in listed],float)
 features=np.column_stack((b[:,0],b[:,32],hashes[:,0]));tests=[];rng=np.random.default_rng(3301)
 phase=np.arange(len(b))%100;counts=np.bincount(phase)
 def phase_stat(z):
  return sum(float(np.var(np.bincount(phase,weights=z[:,j])/counts)) for j in range(z.shape[1]))
 obs=phase_stat(features);ex=0
 for _ in range(perms):ex+=phase_stat(features[rng.permutation(len(b))])>=obs
 tests.append({'test':'100-position phase means, X/Y/hash160 leading bytes','statistic':obs,'p':(ex+1)/(perms+1)})
 for j,name in enumerate(['X','Y','hash160']):
  for lag in [1,99,100,101]:
   a=features[:,j];v=float(np.corrcoef(a[:-lag],a[lag:])[0,1]);ex=0
   for _ in range(perms):
    q=rng.permutation(a);ex+=abs(np.corrcoef(q[:-lag],q[lag:])[0,1])>=abs(v)
   tests.append({'test':f'{name} leading byte lag {lag}','statistic':v,'p':(ex+1)/(perms+1)})
 holm(tests);save('key_order_tests.json',{'permutations':perms,'seed':3301,'tests':tests,'limitation':'Block order is not necessarily key generation order; keypool not introduced until October 2010. No on-chain refill boundaries exist.'})
def sessions(listed,headers,perms=4999):
 hs=np.array([int(r['height']) for r in listed]);en=np.array([headers[int(h)]['en'] for h in hs]);times=np.array([headers[int(h)]['t'] for h in hs])
 raw=np.flatnonzero(np.diff(en)<0)+1;events=[]
 for i in raw:
  sustained=i>=5 and i+5<=len(en) and bool(np.all(np.diff(en[i-5:i])>=0)) and bool(np.all(np.diff(en[i:i+5])>=0))
  events.append({'left_height':int(hs[i-1]),'right_height':int(hs[i]),'utc':stamp(times[i]),'before':int(en[i-1]),'reset_to':int(en[i]),'observation_gap_seconds':int(times[i]-times[i-1]),'sustained_5':sustained,'conservative':bool(sustained and en[i-1]>=1000 and en[i]<=100 and en[i]<=.1*en[i-1]),'moderate':bool(sustained and en[i-1]>=100 and en[i]<=100 and en[i]<=.2*en[i-1])})
 table('reset_events.csv',events);groups={'all_decreases':raw,'moderate':np.array([np.searchsorted(hs,r['right_height']) for r in events if r['moderate']]),'conservative':np.array([np.searchsorted(hs,r['right_height']) for r in events if r['conservative']])}
 tests=[];summ={};hist=[];rng=np.random.default_rng(3302);strata=[np.flatnonzero(hs//1000==k) for k in range(50)]
 for name,ids in groups.items():
  ids=ids.astype(int);labels=np.zeros(len(hs),bool);labels[ids]=True;dt=np.diff(times[ids])/86400
  summ[name]={'events':len(ids),'inter_event_days':stats(dt),'intervals_4_to_6_days':int(np.sum((dt>=4)&(dt<=6))),'reset_to':stats(en[ids]),'observation_bracket_seconds':stats(times[ids]-times[ids-1]),'intervals_are':'first observed low-counter block to next such observation; not measured downtime'}
  for unit,cats,size in [('hour',times//3600%24,24),('weekday',(times//86400+3)%7,7)]:
   expected=np.zeros(size)
   for ix in strata:
    if len(ix):expected+=np.bincount(cats[ix],minlength=size)*labels[ix].mean()
   obs=np.bincount(cats[labels],minlength=size);stat=float(np.sum((obs-expected)**2/np.maximum(expected,1e-9)));ex=0
   for _ in range(perms):
    perm=labels.copy()
    for ix in strata:
     if len(ix):perm[ix]=np.roll(labels[ix],int(rng.integers(len(ix))))
    po=np.bincount(cats[perm],minlength=size);ex+=float(np.sum((po-expected)**2/np.maximum(expected,1e-9)))>=stat-1e-12
   tests.append({'test':f'{name}_{unit}','events':len(ids),'statistic':stat,'p':(ex+1)/(perms+1)})
   hist.extend({'group':name,'unit':unit,'bin':k,'count':int(obs[k]),'expected':float(expected[k])} for k in range(size))
 holm(tests);summ['tests']=tests;summ['permutations']=perms;summ['seed']=3302
 gaps=np.diff(times)/86400;summ['actual_observation_gaps_4_to_6_days']=[{'left':int(hs[i]),'right':int(hs[i+1]),'days':float(gaps[i])} for i in np.flatnonzero((gaps>=4)&(gaps<=6))]
 save('session_summary.json',summ);table('reset_time_distributions.csv',hist)
 # Descriptive monotone runs, NOT claimed miner sessions.
 cuts=[0,*raw.tolist(),len(hs)];runs=[]
 for a,b in zip(cuts,cuts[1:]):
  runs.append({'first_height':int(hs[a]),'last_height':int(hs[b-1]),'blocks':b-a,'hours':float((times[b-1]-times[a])/3600),'start_en':int(en[a]),'end_en':int(en[b-1])})
 table('monotone_runs.csv',runs)
def archaeology(listed,headers):
 rows=[];shape=collections.Counter();anomalies=[]
 for r in listed:
  h=int(r['height']);s=r['input_script'];parsed=extra_nonce(s);push=parsed.get('pushes',[])
  expected_bits=int(headers[h]['bits'],16);first=int.from_bytes(bytes.fromhex(push[0]),'little') if push else None
  e=parsed['extra_nonce'];raw=bytes.fromhex(push[1]);v=int.from_bytes(raw,'little')
  minimal=not(raw and raw[-1]&127==0 and (len(raw)==1 or not raw[-2]&128))
  canonical=f'{len(bytes.fromhex(push[0])):02x}'+push[0]+f'{len(raw):02x}'+push[1]
  ok=len(push)==2 and first==expected_bits and minimal and s==canonical and e>=0
  shape[(len(bytes.fromhex(s)),len(raw),first==expected_bits,minimal)]+=1
  if not ok:anomalies.append({'height':h,'script':s,'pushes':push,'en':e,'bits_match':first==expected_bits,'minimal_script_number':minimal})
  rows.append({'height':h,'script':s,'extra_nonce':e,'first_push_matches_bits':first==expected_bits,'number_minimal':minimal,'only_two_direct_pushes':s==canonical})
 table('coinbase_encoding.csv',rows)
 save('coinbase_archaeology.json',{'count':len(rows),'anomalies':anomalies,'shapes':[{'script_bytes':k[0],'counter_bytes':k[1],'bits_match':k[2],'number_minimal':k[3],'count':v} for k,v in shape.items()],'message_test':'Parse entire script; require exactly difficulty and minimally encoded nonnegative counter. Incidental printable counter bytes are not messages.'})
def boundary(listed,headers):
 hs=[int(r['height']) for r in listed];chosen=[49829,49845,49870,49875,49878,49880,49905,49918,49919,49933,37808]
 literature={int(r['height']):r for r in read(OUT/'cache/bitquery_dataset.csv')}
 rows=[];neighbors=[]
 for h in chosen+list(range(49974,50274)):
  i=bisect.bisect_left(hs,h);near=[x for x in hs[max(0,i-12):i+13] if x!=h];hr=headers[h]
  slopes=[(headers[b]['en']-headers[a]['en'])/((headers[b]['t']-headers[a]['t'])/3600) for ai,a in enumerate(near) for b in near[ai+1:] if headers[b]['t']>headers[a]['t']]
  slope=float(np.median(slopes));intercept=float(np.median([headers[x]['en']-slope*(headers[x]['t']-hr['t'])/3600 for x in near]));res=hr['en']-intercept
  fitres=[headers[x]['en']-intercept-slope*(headers[x]['t']-hr['t'])/3600 for x in near]
  inner=int.from_bytes(hr['n'].to_bytes(4,'little'),'big');lit=literature.get(h,{})
  left=hs[i-1] if i else None;ri=i+1 if i<len(hs) and hs[i]==h else i;right=hs[ri] if ri<len(hs) else None
  row={'height':h,'utc':stamp(hr['t']),'en':hr['en'],'nonce':hr['n'],'nonce_lsb':hr['n']&255,'inner_nonce':inner,'tight_nonce':inner<163840000 or 327680000<=inner<983040000,'left_listed':left,'right_listed':right,'time_bracketed':bool(left and right and headers[left]['t']<hr['t']<headers[right]['t']),'time_slope_en_per_hour':slope,'predicted_en':intercept,'residual_en':res,'neighbor_median_abs_residual':float(np.median(np.abs(fitres))),'neighbors':len(near),'literature_patoshi':lit.get('patoshi'),'literature_tier':lit.get('tier'),'literature_residual':lit.get('resid'),'literature_line_id':lit.get('line_id')}
  row['nearest_time_prediction']='';row['nearest_time_residual']=''
  if row['time_bracketed'] and headers[right]['en']>=headers[left]['en']:
   pred=headers[left]['en']+(headers[right]['en']-headers[left]['en'])*(hr['t']-headers[left]['t'])/(headers[right]['t']-headers[left]['t'])
   row['nearest_time_prediction']=pred;row['nearest_time_residual']=hr['en']-pred
  # Clip neighborhood at counter decreases to avoid fitting across reset boundaries.
  lo=max(0,i-1);hi=min(len(hs)-1,ri)
  while lo>0 and headers[hs[lo]]['en']>=headers[hs[lo-1]]['en'] and i-lo<20:lo-=1
  while hi+1<len(hs) and headers[hs[hi+1]]['en']>=headers[hs[hi]]['en'] and hi-i<20:hi+=1
  segment=[x for x in hs[lo:hi+1] if x!=h]
  segslopes=[(headers[b]['en']-headers[a]['en'])/((headers[b]['t']-headers[a]['t'])/3600) for ai,a in enumerate(segment) for b in segment[ai+1:] if headers[b]['t']>headers[a]['t']]
  row['segment_neighbors']=len(segment);row['segment_first']=segment[0];row['segment_last']=segment[-1]
  row['segment_slope']='';row['segment_residual']=''
  if segslopes:
   ss=float(np.median(segslopes));sp=float(np.median([headers[x]['en']-ss*(headers[x]['t']-hr['t'])/3600 for x in segment]));row['segment_slope']=ss;row['segment_residual']=hr['en']-sp
  row['segment_supported']=bool(len(segment)>=10 and row['time_bracketed'])
  rows.append(row)
  if h in chosen:
   neighbors.extend({'target':h,'height':x,'utc':stamp(headers[x]['t']),'en':headers[x]['en'],'nonce':headers[x]['n'],'listed':True} for x in near)
 table('boundary_deep_dive.csv',rows);table('boundary_neighbors.csv',neighbors)
 # Evidence triage only: original flag confidence is not calibrated.
 flags=read(P2/'classifier_flags.csv');flags.sort(key=lambda r:float(r['scaled_residual'] or -1),reverse=True);triage=[]
 for r in flags[:50]:
  h=int(r['height']);a=int(r['anchor_left']);b=int(r['anchor_right']);j=bisect.bisect_left(hs,a);end=bisect.bisect_right(hs,b);seq=hs[j:end]
  drops=sum(headers[y]['en']<headers[x]['en'] for x,y in zip(seq,seq[1:]));lit=literature.get(h,{})
  triage.append({'height':h,'en':headers[h]['en'],'left_anchor':a,'left_en':headers[a]['en'],'right_anchor':b,'right_en':headers[b]['en'],'scaled_residual':r['scaled_residual'],'intervening_decreases':drops,'literature_patoshi':lit.get('patoshi'),'literature_tier':lit.get('tier'),'disposition':'interpolation crosses counter decrease; unsupported for exclusion' if drops else 'unresolved local fit outlier; no attribution decision'})
 table('top50_flag_triage.csv',triage)
def main():
 OUT.mkdir(parents=True,exist_ok=True);listed,headers=load()
 for name,func in [('weak_keys',lambda:keys(listed)),('key_order',lambda:periodicity(listed)),('sessions',lambda:sessions(listed,headers)),('boundary',lambda:boundary(listed,headers)),('archaeology',lambda:archaeology(listed,headers))]:
  if len(sys.argv)>1 and sys.argv[1]!=name:continue
  print('START',name,flush=True);func();print('DONE',name,flush=True)
if __name__=='__main__':main()
