#!/usr/bin/env python3
"""Independently recompute all strict gates in a full user series84AA summary."""
import hashlib,json,math,sys
from pathlib import Path
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
SOURCES=('source84v','source84s','source84r')
EXPECTED_SHA='93daa4e4dc360b2b741ee7ff8cac6934d58d293c3aedc82bdc914184e71c468b'
MODEL_SHA='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0'
HOLDOUTS={441:'a5d3a6a5da0335a70e7128a8ec82281b5a9bff55277e5a8d5a2c6b26973e2c29',442:'8771bddd7ea53ddbbd84fb46853de1e5b89b2e7d3fce8bf42cf868b5915923b0',443:'f0f1d89a9f23fb1dd309a8927792ff6c9af751c56e1c52ff5a58c19727ae564f',444:'c843826f18aa372e3498e6adfd1086b3639319111d07db058cde4c44302c871a',445:'8b7186e227409139959d6cd50ebfc493725f5edbbb204485141696dd1363c0d5',446:'0c22872db9d868bf3a144b99cc387ec27b29b3028d194e76b9d80772257d43e2',447:'328662c5a40679fbcb652ed0961bf6dea7203937b4d8179e0fd86b1e7413c3bb',448:'4bc89f29790ca695efd51ce81155857da2d75cf7c51885a5487f47d79571bd5d',449:'3a10f2982bbe1f1e539b731e67f84788b0e304be979f030d6480d6aa3e90bbdf',450:'6e3b7697a6630ea0b14cd54abb5fa0d86353497b1070ce03846381e80ced7c32'}
def pooled(rows,key,axis=None):
 n=sum(r['frames'] for r in rows)
 return math.sqrt(sum(r['frames']*(r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad'])**2 for r in rows)/n)
def decision(rows):
 axes={};n=len(rows)
 for axis in AXES:
  c=pooled(rows,'candidate',axis);z=pooled(rows,'zero',axis);values={k:pooled(rows,k,axis) for k in SOURCES};wz=sum(r['candidate']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in rows);wins={k:sum(r['candidate']['axis_rmse_rad'][axis]<r[k]['axis_rmse_rad'][axis] for r in rows) for k in SOURCES};ok=c<z and wz>=.70*n and (all(c<values[k] and wins[k]>=.60*n for k in SOURCES) if axis=='right_distal' else all(c<=1.05*values[k] for k in SOURCES));axes[axis]={'candidate':c,**values,'zero':z,'wins_vs_zero':wz,**{'wins_vs_'+k:wins[k] for k in SOURCES},'cases':n,'passed':ok}
 combined={k:pooled(rows,k) for k in ('candidate',*SOURCES,'zero')};total=sum(r['frames'] for r in rows)
 for name in ('shuffled','static','closed'):combined[name]=math.sqrt(sum(r['frames']*r['controls'][name]['rmse_rad']**2 for r in rows)/total)
 def safeguard(field,values):
  out=[]
  for value in values:
   rr=[r for r in rows if r['view'][field]==value];aa={}
   for axis in AXES:
    c=pooled(rr,'candidate',axis);z=pooled(rr,'zero',axis);w=sum(r['candidate']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in rr);aa[axis]={'candidate':c,'zero':z,'wins':w,'cases':len(rr),'passed':c<z and w>=.70*len(rr)}
   out.append({'value':value,'axes':aa,'passed':all(x['passed'] for x in aa.values())})
  return out
 body=safeguard('body_x',(3.82,4.18));camera=safeguard('camera_z',(.36,.56));low=[r for r in rows if r['view']['body_x']==3.82]
 lr={'candidate':pooled(low,'candidate','right_distal'),**{k:pooled(low,k,'right_distal') for k in SOURCES},'zero':pooled(low,'zero','right_distal'),'wins_vs_zero':sum(r['candidate']['axis_rmse_rad']['right_distal']<r['zero']['axis_rmse_rad']['right_distal'] for r in low),**{'wins_vs_'+k:sum(r['candidate']['axis_rmse_rad']['right_distal']<r[k]['axis_rmse_rad']['right_distal'] for r in low) for k in SOURCES},'cases':len(low),'required_vs_zero':math.ceil(.75*len(low)),'required_vs_each_source':math.ceil(.60*len(low))}
 lr['passed']=lr['candidate']<min(lr[k] for k in (*SOURCES,'zero')) and lr['wins_vs_zero']>=lr['required_vs_zero'] and all(lr['wins_vs_'+k]>=lr['required_vs_each_source'] for k in SOURCES);body[0]['axes']['right_distal']['passed']&=lr['passed'];body[0]['passed']=all(x['passed'] for x in body[0]['axes'].values())
 corners=[]
 for cid in range(1,17):
  rr=[r for r in rows if r['corner_id']==cid];aa={}
  for axis in AXES:
   c=pooled(rr,'candidate',axis);z=pooled(rr,'zero',axis);w=sum(r['candidate']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in rr);aa[axis]={'candidate':c,'zero':z,'wins':w,'cases':len(rr),'passed':c<z and w>=7}
  corners.append({'corner_id':cid,'view':rr[0]['view'],'axes':aa,'passed':all(x['passed'] for x in aa.values())})
 out={'axes':axes,'combined':combined,'body_x_safeguards':body,'camera_z_safeguards':camera,'corner_results':corners,'corners_passed':sum(x['passed'] for x in corners),'corners_required':12,'lower_x_right_distal_comparator':lr};out['passed']=all(x['passed'] for x in axes.values()) and combined['candidate']<min(combined[k] for k in (*SOURCES,'zero','shuffled','static','closed')) and all(x['passed'] for x in body+camera) and out['corners_passed']>=12;return out
def same(a,b,path='primary'):
 if isinstance(a,dict):
  assert set(a)==set(b),(path,set(a)^set(b))
  for k in a:same(a[k],b[k],path+'.'+k)
 elif isinstance(a,list):
  assert len(a)==len(b),(path,len(a),len(b))
  for i,(x,y) in enumerate(zip(a,b)):same(x,y,f'{path}[{i}]')
 elif isinstance(a,float):assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),(path,a,b)
 else:assert a==b,(path,a,b)
def verify(path):
 raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==EXPECTED_SHA
 d=json.loads(raw);p=d['protocol'];rows=d['tests'];assert d['schema']=='frozen-multivariant-replication-result-v1' and d['status']=='completed';assert p['mode']=='full' and p['runner84z_sha256']=='fa4040d7271f2c98021042054ebe60767ad092de81d610a60815738be9f57a6b' and p['script_sha256']=='846bf4b56e7d6d221a8a5a35eb02675f16bde570ea7e7b7a8e2d822f4c33e879';assert p['selected_model_sha256']==MODEL_SHA and p['selected_variant']=='ridge_0175' and p['right_distal_ridge']==.175 and p['new_weight']==1.;assert p['motion_seed']==8436 and p['geometry_corners']==16 and not p['training_allowed'] and not p['development_selection_allowed'];assert {x['id']:x['motion_sha256'] for x in p['holdouts']}==HOLDOUTS
 assert len(rows)==160 and {(r['test_id'],r['corner_id']) for r in rows}=={(i,c) for i in range(441,451) for c in range(1,17)}
 for r in rows:
  assert r['frames']==49 and r['state_coefficients']==72 and r['delay_s']==.5 and r['state_unchanged_during_delay'] and r['state_sha256_before_delay']==r['state_sha256_after_delay'];assert r['diagnostics']['unique_rgb_frames']>1 and r['diagnostics']['changed_rgb_values']>0 and r['diagnostics']['candidate_feature_max_std']>0
  for key in ('candidate',*SOURCES,'zero'):
   m=r[key];assert set(m['axis_rmse_rad'])==set(AXES) and all(math.isfinite(x) and x>=0 for x in [m['rmse_rad'],*m['axis_rmse_rad'].values()])
 recomputed=decision(rows);same(recomputed,d['primary']);assert recomputed['passed'] and recomputed['corners_passed']==16
 a=d['audit'];assert a['accepted_total']==16384 and a['audited_count']==128 and not a['is_exhaustive'] and len(a['tests'])==10
 print('Series84AA independently recomputed: all strict frozen-replication gates pass; replication go.')
def verify_extract():
 path=Path(__file__).resolve().parents[1]/'experiments/reports/frozen-multivariant-replication-user-summary-extract.json';d=json.loads(path.read_text(encoding='utf8'));assert d['source_file_sha256']==EXPECTED_SHA and d['status']=='completed';p=d['primary'];assert p['passed'] and all(x['passed'] for x in p['axes'].values());assert p['corners_passed']==16>=p['corners_required']==12;lr=p['lower_x_right_distal_comparator'];assert lr['passed'] and (lr['wins_vs_zero'],lr['wins_vs_source84v'],lr['wins_vs_source84s'],lr['wins_vs_source84r'])==(68,73,64,67);x=d['derived'];assert x['test_records']==x['state_unchanged_cases']==x['state_sha_match_cases']==160;assert x['candidate_case_wins']=={'zero':160,'source84v':136,'source84s':151,'source84r':157,'shuffled':160,'static':160,'closed':159};assert x['overlap_totals']=={'under_0_001_deg':0,'under_1_deg':0,'under_5_deg':94};assert d['audit']['accepted_total']==16384 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive'];print('Persisted series84AA extract matches the independently recomputed replication go.')
if __name__=='__main__':verify(sys.argv[1]) if len(sys.argv)>1 else verify_extract()
