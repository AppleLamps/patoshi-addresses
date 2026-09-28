"""Offline public corpus intersection and exact-script funding audit."""
import csv,json,hashlib,re,tarfile,collections
from decimal import Decimal
from pathlib import Path
from phase3_offline import read,save,table,ROOT,OUT,P2
ALPH='123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
def h160(b):return hashlib.new('ripemd160',hashlib.sha256(b).digest()).digest()
def b58(version,payload):
 b=bytes([version])+payload;b+=hashlib.sha256(hashlib.sha256(b).digest()).digest()[:4];n=int.from_bytes(b,'big');s=''
 while n:n,r=divmod(n,58);s=ALPH[r]+s
 return '1'*(len(b)-len(b.lstrip(b'\0')))+s
def bech32(h):
 chars='qpzry9x8gf2tvdw0s3jn54khce6mua7l';acc=0;bits=0;data=[0]
 for b in h:
  acc=(acc<<8)|b;bits+=8
  while bits>=5:bits-=5;data.append((acc>>bits)&31)
 if bits:data.append((acc<<(5-bits))&31)
 v=[3,3,0,2,3]+data+[0]*6;chk=1
 for n in v:
  top=chk>>25;chk=((chk&0x1ffffff)<<5)^n
  for i,g in enumerate([0x3b6a57b2,0x26508e6d,0x1ea119fa,0x3d4233dd,0x2a1462b3]):
   if (top>>i)&1:chk^=g
 chk^=1
 return 'bc1'+''.join(chars[n] for n in data+[(chk>>5*(5-i))&31 for i in range(6)])
def corpus():
 rows=read(ROOT/'patoshi_p2pkh_addresses.csv');targets={}
 for r in rows:
  key=bytes.fromhex(r['pubkey_uncompressed']);comp=bytes([2+(key[-1]&1)])+key[1:33]
  assert b58(0,h160(key))==r['p2pkh_address']
  for enc,k in [('uncompressed',key),('compressed',comp)]:
   hh=h160(k);targets[b58(0,hh)]=(int(r['block_height']),enc,'p2pkh')
   if enc=='compressed':
    targets[bech32(hh)]=(int(r['block_height']),enc,'p2wpkh');targets[b58(5,h160(b'\0\x14'+hh))]=(int(r['block_height']),enc,'p2sh_p2wpkh')
 files=[];hits=[];unique=set()
 with tarfile.open(OUT/'cache/milksad-data.tar.gz') as tar:
  for m in tar.getmembers():
   # Address lists only: do not read, export, or reconstruct corpus private keys.
   if not m.isfile() or 'bitcoin' not in m.name.lower() or not any(w in m.name.lower() for w in ['addresses','_addr_']):continue
   raw=tar.extractfile(m).read();addresses=set(re.findall(r'(?<![A-Za-z0-9])(?:[13][1-9A-HJ-NP-Za-km-z]{25,34}|bc1[ac-hj-np-z02-9]{11,87})(?![A-Za-z0-9])',raw.decode('utf8')))
   matches=addresses&targets.keys();unique.update(addresses)
   files.append({'path':m.name,'sha256':hashlib.sha256(raw).hexdigest(),'unique_addresses':len(addresses),'matches':len(matches)})
   hits.extend({'height':targets[a][0],'encoding':targets[a][1],'type':targets[a][2],'address':a,'source_file':m.name} for a in matches)
 save('published_corpus_screen.json',{'source_commit':'81d1eb74585403e0042f9d507089ee4660a18502','files':len(files),'unique_corpus_addresses':len(unique),'target_encodings':len(targets),'hits':hits,'scope':'Published address lists, not exhaustive vulnerable PRNG spaces; four encodings per target point; modern flaws do not imply historical use.'});table('corpus_files.csv',files)
def pushes(script):
 b=bytes.fromhex(script);i=0;ps=[]
 while i<len(b):
  op=b[i];i+=1
  if op<=75:n=op
  elif op in (76,77,78):
   w={76:1,77:2,78:4}[op];n=int.from_bytes(b[i:i+w],'little');i+=w
  else:return []
  if i+n>len(b):return []
  ps.append(b[i:i+n]);i+=n
 return ps
def funding():
 rs=read(OUT/'results/funded_keyhashes.csv');targets={r['hash160']:r for r in read(ROOT/'patoshi_p2pkh_addresses.csv')};agg={};collision=[];unknown=[];revealed=0;pubkeys=set()
 for r in rs:
  hh=r['script_hex'][6:-4];target=targets[hh];r['target_height']=target['block_height'];r['address']=target['p2pkh_address']
  row=agg.setdefault(hh,{'target_height':int(target['block_height']),'address':r['address'],'outputs':0,'unspent_outputs':0,'received_sats':0,'unspent_sats':0})
  row['outputs']+=1;row['received_sats']+=int(Decimal(r['value_sats']))
  if not r['spending_txid']:row['unspent_outputs']+=1;row['unspent_sats']+=int(Decimal(r['value_sats']));continue
  ps=pushes(r['spending_scriptsig']);key=ps[-1] if ps else b''
  if len(key) in (33,65) and h160(key).hex()==hh:
   revealed+=1;pubkeys.add(key.hex())
   if key.hex()!=target['pubkey_uncompressed']:collision.append(r)
  else:unknown.append(r)
 totals={'historical_outputs':len(rs),'matching_hashes':len(agg),'unspent_outputs':sum(r['unspent_outputs'] for r in agg.values()),'unspent_hashes':sum(r['unspent_outputs']>0 for r in agg.values()),'unspent_sats':sum(r['unspent_sats'] for r in agg.values()),'spent_outputs_with_pubkey_checked':revealed,'distinct_revealed_pubkeys':len(pubkeys),'different_pubkey_same_hash_hits':len(collision),'unparsed_spent_outputs':len(unknown),'internal_hash160_duplicates':21953-len(targets),'watermark':968902}
 save('funding_summary.json',totals);table('funding_by_keyhash.csv',sorted(agg.values(),key=lambda r:r['unspent_sats'],reverse=True));save('collision_candidates.json',collision);save('unparsed_funding_spends.json',unknown)
 base=read(P2/'spend_status_all.csv');unspent=[r for r in base if r['dataset_status']=='no_spend_found_in_dataset'];btc=Decimal(sum(int(r['value_sats']) for r in unspent))/10**8;quote=json.loads((OUT/'cache/coinbase_spot.json').read_text());price=Decimal(quote['data']['amount'])
 save('quantum_exposure.json',{'watermark':968902,'original_unspent_outputs':len(unspent),'original_unspent_btc':str(btc),'btc_usd':str(price),'quote_receipt':json.loads((OUT/'cache/coinbase_spot.json.metadata.json').read_text()),'original_unspent_usd':str(btc*price),'additional_p2pkh_unspent_outputs':totals['unspent_outputs'],'additional_p2pkh_unspent_btc':str(Decimal(totals['unspent_sats'])/10**8),'interpretation':'Conditional exposure to sufficiently capable fault-tolerant Shor attack; not evidence of a currently practical attack. Balance is at historical dataset watermark, quote is at receipt time.'})
if __name__=='__main__':corpus();funding()
