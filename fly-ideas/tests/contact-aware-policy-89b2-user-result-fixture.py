#!/usr/bin/env python3
"""Independent aggregate verifier for uploaded or persisted series89B2 result."""
from __future__ import annotations
import hashlib,json,math,statistics,sys
from pathlib import Path
EXPECTED_SHA='6e3f9c224087bb2915034bf3017703a63afd8f2ad6e67966009a37faae2bb00b'
ROOT=Path(__file__).resolve().parents[1];EXTRACT=ROOT/'experiments/reports/contact-aware-policy-89b2-user-summary-extract.json'
def load(path):
 raw=Path(path).read_bytes();d=json.loads(raw)
 if Path(path).resolve()!=EXTRACT.resolve() and hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA:raise AssertionError('Unexpected uploaded summary SHA.')
 return d
def verify(d):
 if d.get('schema')=='contact-aware-policy-user-extract-v1':records=d['records'];reported=d['reported_primary'];protocol=d['protocol'];source=d['source84z_passed']
 else:records=d['tests'];reported=d['primary'];protocol=d['protocol'];source=d['source84z_primary']['passed']
 assert source and protocol['mode']=='full' and protocol['source84z_training_allowed'] is False and protocol['development_training_allowed'] is True and protocol['final_used_for_fit'] is False
 assert protocol['script_sha256']=='ec46c681834c4dc13c30d66f07616546809c2f3b29242e134b7f0a004d95f1a3'
 assert protocol['runner89b_sha256']=='99e0ccd01e9ae0ba27d61c4391e6cdff675793c8b10cbea41a4237a5b398a920'
 assert protocol['series89b_nogo_extract_sha256']=='ad8405c5bab7511bafaa0c0fbfee44cfa3c357cdcabdb70cca8e196a01ab75e8'
 motions=protocol['motions'];assert [x['id'] for x in motions]==list(range(639,675));assert all(x['role']=='development' for x in motions[:18]) and all(x['role']=='final' for x in motions[18:])
 assert [x['corner_id'] for x in protocol['development_views']]==list(range(401,409)) and [x['corner_id'] for x in protocol['final_views']]==list(range(421,433))
 assert len(records)==216 and len({(x['id'],x['corner_id']) for x in records})==216 and {x['id'] for x in records}==set(range(657,675)) and {x['corner_id'] for x in records}==set(range(421,433))
 assert all(x['state_coefficients']==72 and x['state_unchanged_during_delay'] and x['state_sha256_before_delay']==x['state_sha256_after_delay'] for x in records) and len({x['state_sha256'] for x in records})==216
 trials=[t for r in records for t in r['trials']];assert len(trials)==648 and all(set(t['controls'])==set(protocol['controls']) for t in trials);required=math.ceil(.9*len(trials));candidate=[t['controls']['candidate'] for t in trials];safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=.35+1e-12 and x['energy_abs_work']<=4 and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30
 safety=sum(safe(x) for x in candidate);recovered=sum(x['recovered'] for x in candidate);completed=sum(x['completion_ratio']>=.65 for x in candidate);an=('uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');cn=('angle_only',)+an;aw={n:sum(t['controls']['candidate']['angle_rmse_truth']<t['controls'][n]['angle_rmse_truth'] for t in trials) for n in an};cw={n:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][n]['contact_mae_truth'] for t in trials) for n in cn};means={n:{k:statistics.mean(t['controls'][n][k] for t in trials) for k in ('angle_rmse_truth','contact_mae_truth')} for n in protocol['controls']};angle=all(aw[n]>=required for n in an) and means['candidate']['angle_rmse_truth']<=1.05*means['angle_only']['angle_rmse_truth'];contact=cw['angle_only']>=required and sum(cw[n]>=required for n in cn)>=4;recomputed={'final_visual_cases':len(records),'final_trials':len(trials),'required_trials':required,'candidate_safety_passed':safety,'candidate_recovered':recovered,'candidate_completed':completed,'candidate_angle_wins':aw,'candidate_contact_wins':cw,'means':means,'angle_gate_passed':angle,'contact_gate_passed':contact,'passed':safety==len(trials) and recovered>=required and completed>=required and angle and contact}
 for key,value in recomputed.items():
  if key!='means':assert value==reported[key],key
 for name,metrics in means.items():
  for key,value in metrics.items():assert abs(value-reported['means'][name][key])<1e-15,(name,key)
 return recomputed
if __name__=='__main__':
 result=verify(load(sys.argv[1] if len(sys.argv)>1 else EXTRACT));print('Series89B2 primary independently recomputed:',result['passed'],'contact:',json.dumps(result['candidate_contact_wins'],sort_keys=True))
