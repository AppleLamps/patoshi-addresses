"""Cache sources and timestamped price; no wallet operations or secrets persisted."""
import hashlib, json, time, urllib.request, urllib.error
from pathlib import Path
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase3'
SOURCES = {
 'bitquery_dataset.csv': 'https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth/patoshi-audit-dataset.csv',
 'bitquery_methods.md': 'https://www.bitquery.io/investigations/satoshi-nakamoto-net-worth/method-changelog.md',
 'coinbase_spot.json': 'https://api.coinbase.com/v2/prices/BTC-USD/spot',
 'bitcoin001_main.cpp': 'https://raw.githubusercontent.com/blaesus/bitcoin-0.0.1/master/src/main.cpp',
 'badkeys_README.md': 'https://raw.githubusercontent.com/badkeys/badkeys/main/README.md',
 'milksad-data.tar.gz': 'https://git.distrust.co/milksad/data/archive/81d1eb74585403e0042f9d507089ee4660a18502.tar.gz',
}
def fetch(name, url):
 p=OUT/'cache'/name; p.parent.mkdir(parents=True,exist_ok=True)
 meta=p.with_name(p.name+'.metadata.json')
 if meta.exists():
  m=json.loads(meta.read_text());assert p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==m['sha256'],'source cache checksum mismatch'
  return m
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'PatoshiResearch/1.0'}),timeout=60) as r: raw=r.read(); status=r.status
 except urllib.error.HTTPError as e: raw=e.read(); status=e.code
 p.write_bytes(raw)
 m={'url':url,'status':status,'observed_at':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 meta.write_text(json.dumps(m,indent=2)+'\n',encoding='utf8',newline='\n');time.sleep(.5)
 return m
if __name__=='__main__':
 for name,url in SOURCES.items(): print(name,fetch(name,url),flush=True)
