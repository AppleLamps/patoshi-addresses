"""Offline cache-integrity checks and auditable manifest (no fetches)."""
import csv,hashlib,json,sqlite3,zlib,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 results=[]
 for p in sorted((OUT/'results').glob('*.metadata.json')):
  m=json.loads(p.read_text());c=p.with_name(p.name.replace('.metadata.json','.csv'))
  assert sha(c)==m['csv_sha256'],str(c)
  csv.field_size_limit(50_000_000)
  with c.open(newline='',encoding='utf8') as f:count=sum(1 for _ in csv.DictReader(f))
  assert count==m['rows'];results.append({'name':c.name,'rows':count,'checksum_verified':True,'job':m['jobReference']})
 source_receipts=[]
 for p in sorted((OUT/'cache').glob('*.metadata.json')):
  m=json.loads(p.read_text());raw=p.with_name(p.name.replace('.metadata.json',''))
  assert sha(raw)==m['sha256'];source_receipts.append({'path':str(raw.relative_to(ROOT)).replace('\\','/'),**m})
 api=[];db=sqlite3.connect('file:'+str(OUT/'cache/chain.sqlite3')+'?mode=ro',uri=True)
 for rid,h,path,host,t,status,digest,body in db.execute('SELECT id,height,endpoint,host,fetched_at,status,sha256,body_zlib FROM responses ORDER BY id'):
  assert hashlib.sha256(zlib.decompress(body)).hexdigest()==digest
  api.append({'id':rid,'height':h,'endpoint':path,'host':host,'observed_at':t,'status':status,'sha256':digest})
 db.close()
 (OUT/'api_response_manifest.json').write_text(json.dumps(api,indent=2)+'\n',encoding='utf8',newline='\n')
 checks=json.loads((OUT/'live_confirmations.json').read_text());assert all(r['confirmed'] for r in checks)
 integrity={'query_csvs':results,'source_receipts':source_receipts,'new_api_responses_checked':len(api),'targeted_checks':len(checks),'targeted_checks_successful':sum(r['confirmed'] for r in checks),'method':'Exact cached-byte checksums, query row counts and successful targeted evidence receipts. Transaction reconstruction and model conservation are performed by phase3_trace_analyze.py.'}
 (OUT/'integrity.json').write_text(json.dumps(integrity,indent=2)+'\n',encoding='utf8',newline='\n')
 files=[]
 paths=list(OUT.rglob('*'))+list((ROOT/'.firecrawl').glob('*'))+list((ROOT/'scripts').glob('phase3*.py'))
 for p in sorted(paths):
  if not p.is_file() or p.name=='manifest.json' or p.suffix=='.log' or p.name.endswith(('-wal','-shm')):continue
  rel=str(p.relative_to(ROOT)).replace('\\','/');local='/cache/' in rel or rel.startswith('.firecrawl/')
  files.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p),'local_only':local})
 manifest={'created_at':datetime.now(timezone.utc).isoformat(),'watermark':968902,'files':files,'notes':'Local-only raw/source cache retained on research machine; source URLs and receipts in integrity.json. Committed CSVs reproduce bulk chain analysis. SHA checks compare bytes, not truth or attribution.'}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps({'query_csvs_verified':len(results),'live_checks':len(checks),'api_responses_verified':len(api),'manifest_files':len(files)}))
if __name__=='__main__':main()
