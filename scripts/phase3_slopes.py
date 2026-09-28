"""Exploratory multi-track slope classifier. Fit labels are never used as positives.

Fixed design: 2000-height windows, stride 1000, broad nonce filter; RANSAC
1000 pair proposals, slopes .15..12 EN/height, residual <=15, >=50 points.
Hold out h%5==4 and every top-50 Phase 2 flag. No parameter tuning after run.
This classifies signature consistency, not miner identity or ownership.
"""
import bisect,json
import numpy as np
from phase3_offline import load,read,save,table,ROOT,OUT,P2
def main():
 listed,headers=load();labels={int(r['height']) for r in listed}
 top=read(OUT/'top50_flag_triage.csv');exclude={int(r['height']) for r in top}
 rng=np.random.default_rng(3307);lines=[];predictions={};line_id=0
 valid=[h for h,r in headers.items() if h>0 and r['en'] is not None and ((r['n']&255)<=9 or 19<=(r['n']&255)<=58)]
 for start in range(0,54001,1000):
  window=[h for h in valid if start<=h<start+2000];train=[h for h in window if h%5!=4 and h not in exclude]
  xx=np.array(train,float);yy=np.array([headers[h]['en'] for h in train],float)
  for iteration in range(12):
   if len(xx)<50:break
   pairs=rng.integers(0,len(xx),(1000,2));best=None;bestn=0
   for ia,ib in pairs:
    if abs(xx[ia]-xx[ib])<50:continue
    slope=(yy[ib]-yy[ia])/(xx[ib]-xx[ia])
    if not .15<=slope<=12:continue
    intercept=yy[ia]-slope*xx[ia];mask=np.abs(yy-slope*xx-intercept)<=15;n=int(mask.sum())
    if n>bestn:best=(slope,intercept,mask);bestn=n
   if best is None or bestn<50:break
   slope,intercept,mask=best
   # Two ordinary least-square refinements restricted to RANSAC inliers.
   for _ in range(2):
    slope,intercept=np.polyfit(xx[mask],yy[mask],1);mask=np.abs(yy-slope*xx-intercept)<=15
   if mask.sum()<50 or not .15<=slope<=12:break
   line_id+=1;members=sorted(int(x) for x in xx[mask]);line={'line_id':line_id,'window_start':start,'slope':float(slope),'intercept':float(intercept),'members':len(members),'first':members[0],'last':members[-1],'rmse':float(np.sqrt(np.mean((yy[mask]-slope*xx[mask]-intercept)**2)))};lines.append(line)
   for h in window:
    i=bisect.bisect_left(members,h)
    # Bracketing prevents extrapolating a line across an unobserved reset/gap.
    if i==0 or i==len(members):continue
    left,right=members[i-1],members[i]
    if right==h:
     if i+1==len(members):continue
     right=members[i+1]
    if h-left>200 or right-h>200:continue
    residual=headers[h]['en']-(slope*h+intercept)
    fit={'height':h,'en':headers[h]['en'],'line_id':line_id,'window_start':start,'slope':float(slope),'prediction':float(slope*h+intercept),'residual':float(residual),'left_support':left,'right_support':right,'left_en':headers[left]['en'],'right_en':headers[right]['en'],'support_members':len(members),'pass':bool(abs(residual)<=15),'held_out':h%5==4 or h in exclude}
    if h not in predictions or abs(residual)<abs(predictions[h]['residual']):predictions[h]=fit
   xx=xx[~mask];yy=yy[~mask]
 table('slope_lines.csv',lines);table('slope_predictions.csv',list(predictions.values()))
 adjud=[]
 for r in top:
  h=int(r['height']);fit=predictions.get(h)
  adjud.append({**r,'slope_pass':fit['pass'] if fit else False,'slope_line_id':fit['line_id'] if fit else '', 'slope_residual':fit['residual'] if fit else '', 'slope_left_support':fit['left_support'] if fit else '', 'slope_right_support':fit['right_support'] if fit else '', 'slope_support_members':fit['support_members'] if fit else 0,'adjudication':'separately fitted counter track supports retention as a candidate; interpolation flag alone rejected' if fit and fit['pass'] else 'unresolved; no supported track under fixed model, insufficient evidence for exclusion'})
 table('top50_slope_adjudication.csv',adjud)
 controls=set(json.loads((ROOT/'analysis/phase2/selection.json').read_text())['controls']);evaluated={h for h in labels if h%5==4}
 summary={'seed':3307,'windows':55,'lines':len(lines),'tolerance_en':15,'min_members':50,'slope_range':[.15,12],'top50_excluded_from_training':50,'top50_supported':sum(r['slope_pass'] for r in adjud),'held_out_listed':{'total':len(evaluated),'supported':sum(h in predictions for h in evaluated),'pass':sum(h in predictions and predictions[h]['pass'] for h in evaluated)},'unlisted_controls':{'total':len(controls),'pass':sum(h in predictions and predictions[h]['pass'] for h in controls)},'limitations':'Exploratory signature classifier. Controls can be fitting data; their pass rate is not a held-out false-positive estimate. No independent miner truth labels. Overlapping windows can represent one physical track multiple times. Best-of-many-line fit increases acceptance. No threshold tuning after results.'}
 save('slope_summary.json',summary)
if __name__=='__main__':main()
