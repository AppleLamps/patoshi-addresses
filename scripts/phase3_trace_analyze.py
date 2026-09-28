"""Reconstruct cached transactions and trace explicit outpoint edges, with bounded depth."""
import json,collections,graphlib
from decimal import Decimal,getcontext
from phase3_offline import read,save,table,ROOT,OUT,P2
from phase2_collect import txid_from_json
getcontext().prec=50
def main():
 tx=json.loads((OUT/'trace_seed_transactions.json').read_text());depth={k:0 for k in tx}
 for d in range(1,4):
  p=OUT/f'results/trace_transactions_{d}.csv'
  if not p.exists():continue
  for r in read(p):
   ins=json.loads(r['inputs_json']);outs=json.loads(r['outputs_json'])
   tx[r['txid']]={'txid':r['txid'],'version':int(r['version']),'locktime':int(r['lock_time']),'status':{'block_height':int(r['height'])},'vin':[{'txid':i['spent_transaction_hash'],'vout':int(i['spent_output_index']),'scriptsig':i['script_hex'],'sequence':int(i['sequence']),'prevout':{'value':int(Decimal(str(i['value'])))}} for i in sorted(ins,key=lambda i:i['index'])],'vout':[{'scriptpubkey':o['script_hex'],'value':int(Decimal(str(o['value']))),'addresses':o.get('addresses',[])} for o in sorted(outs,key=lambda o:o['index'])]};depth[r['txid']]=d
 for t in tx.values():assert txid_from_json(t)==t['txid'],'Cached transaction reconstruction failed'
 sources={(r['coinbase_txid'],0):Decimal(r['value_sats']) for r in read(P2/'results/confirmed_spends.csv')}
 edges=[];spent={};queried=set();snap=[]
 for d in range(1,4):
  p=OUT/f'results/trace_edges_{d}.csv'
  if p.exists():
   rs=read(p);edges.extend(rs)
   for r in rs:spent[(r['parent_txid'],int(r['parent_vout']))]=r
 queried.update(k for k,v in depth.items() if v<3)
 # A frontier output may already be consumed inside another fetched branch.
 # Recognize those explicit inputs before counting terminals; otherwise convergence
 # within the final generation would double-count proportional value.
 for child,t in tx.items():
  for index,i in enumerate(t['vin']):
   op=(i['txid'],i['vout'])
   if i['txid'] in tx and op not in spent:
    spent[op]={'parent_txid':op[0],'parent_vout':str(op[1]),'spending_txid':child,'spending_vin':str(index),'spending_height':str(t['status']['block_height']),'spending_time':''}
    edges.append(spent[op])
 taint=dict(sources);fees=Decimal(0);outputs=[]
 order=graphlib.TopologicalSorter({k:{i['txid'] for i in t['vin'] if i['txid'] in tx} for k,t in tx.items()}).static_order()
 for k in order:
  t=tx[k]
  incoming=sum((taint.get((i['txid'],i['vout']),Decimal(0)) for i in t['vin']),Decimal(0));iv=sum(i['prevout']['value'] for i in t['vin']);ov=sum(o['value'] for o in t['vout']);assert iv>=ov
  frac=incoming/iv if iv else Decimal(0);fees+=(iv-ov)*frac
  for j,o in enumerate(t['vout']):
   v=Decimal(o['value'])*frac;taint[(k,j)]=v;s=spent.get((k,j))
   status='spent_to_fetched_transaction' if s else ('no_reference_to_watermark' if k in queried else 'frontier_not_queried')
   outputs.append({'txid':k,'vout':j,'height':t['status']['block_height'],'depth_after_first_spend':depth[k],'value_sats':o['value'],'proportional_listed_sats':str(v),'status':status,'spending_txid':s['spending_txid'] if s else '', 'script':o['scriptpubkey']})
 terminal=sum((Decimal(r['proportional_listed_sats']) for r in outputs if r['status']!='spent_to_fetched_transaction'),Decimal(0))
 # Seeds can have downstream edges pointing at another seed. Each source injected once.
 assert abs(terminal+fees-Decimal(1550)*10**8)<Decimal('.001'),str((terminal,fees))
 table('trace_outputs.csv',outputs);table('trace_edges.csv',edges)
 summary={'first_spend_transactions':20,'all_reconstructed_transactions':len(tx),'input_edges_returned':len(edges),'unique_spent_outpoints':len(spent),'depths':dict(collections.Counter(depth.values())),'proportional_fee_sats':str(fees),'terminal_proportional_sats':str(terminal),'terminal_statuses':{s:{'outputs':sum(r['status']==s for r in outputs),'proportional_sats':str(sum((Decimal(r['proportional_listed_sats']) for r in outputs if r['status']==s),Decimal(0)))} for s in ['no_reference_to_watermark','frontier_not_queried']},'assumption':'Illustrative proportional allocation across all outputs and fees; provenance of individual satoshis and ownership are NOT established. No change-address or common-input identity inference. Frontier spend status unknown.'}
 save('trace_summary.json',summary)
 may=[];maytx=set()
 for root in ['499d0f5d452891ebe18a8c23cc0a554459a0ba3341ef021f3fae15926a977ffd','028ad2c836163295e4723a49dd418ee8fb55a14613b1186675f01124b60fb763']:
  front={root};seen={root}
  for generation in range(1,4):
   nxt=set()
   for r in edges:
    if r['parent_txid'] in front:
     child=tx[r['spending_txid']];parent=tx[r['parent_txid']];out=parent['vout'][int(r['parent_vout'])]
     may.append({**r,'root':root,'generation':generation,'edge_value_sats':out['value'],'child_inputs':len(child['vin']),'child_outputs':len(child['vout']),'child_total_in_sats':sum(i['prevout']['value'] for i in child['vin']),'child_output_summary':json.dumps([{'vout':i,'value':o['value'],'script':o['scriptpubkey']} for i,o in enumerate(child['vout'])])});nxt.add(r['spending_txid']);maytx.add(r['spending_txid'])
   front=nxt-seen;seen.update(nxt)
 table('may2010_paths.csv',may)
 save('trace_live_targets.json',sorted(maytx))
if __name__=='__main__':main()
