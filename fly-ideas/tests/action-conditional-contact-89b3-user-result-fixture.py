#!/usr/bin/env python3
"""Independent aggregate verifier for uploaded or persisted series89B3 result."""
from __future__ import annotations
import hashlib,json,math,statistics,sys
from pathlib import Path
EXPECTED_SHA='dd16e35af84f5fe40d5319a9cc2720637639d51f7ac1c442af06cfd632bcccfb'
ROOT=Path(__file__).resolve().parents[1];EXTRACT=ROOT/'experiments/reports/action-conditional-contact-89b3-user-summary-extract.json'
def load(path):
 raw=Path(path).read_bytes();d=json.loads(raw)
 if Path(path).resolve()!=EXTRACT.resolve() and hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA:raise AssertionError('Unexpected uploaded summary SHA.')
 return d
def verify(d):
 if d.get('schema')=='action-conditional-contact-user-extract-v1':records=d['records'];reported=d['reported_primary'];protocol=d['protocol'];source=d['source84z_passed']
 else:records=d['tests'];reported=d['primary'];protocol=d['protocol'];source=d['source84z_primary']['passed']
 assert source and protocol['mode']=='full' and protocol['source84z_training_allowed'] is False and protocol['development_training_allowed'] is True and protocol['final_used_for_fit'] is False
 assert protocol['script_sha256']=='b6252829d81ea92c106554f8413cae6b842868c06f69b18fdcd99e5d512ef259'
 assert protocol['runner89b2_sha256']=='ec46c681834c4dc13c30d66f07616546809c2f3b29242e134b7f0a004d95f1a3'
 assert protocol['series89b2_nogo_extract_sha256']=='fc3de1d5264a08249d4cdb4a1db88b14d239737c6dc9b6fcb3e3a35d23122621'
 motions=protocol['motions'];assert [x['id'] for x in motions]==list(range(675,711));assert all(x['role']=='development' for x in motions[:18]) and all(x['role']=='final' for x in motions[18:])
 assert len(records)==216 and len({(x['id'],x['corner_id']) for x in records})==216 and {x['id'] for x in records}==set(range(693,711)) and {x['corner_id'] for x in records}==set(range(521,533))
 assert all(x['state_coefficients']==72 and x['state_unchanged_during_delay'] and x['state_sha256_before_delay']==x['state_sha256_after_delay'] for x in records) and len({x['state_sha256'] for x in records})==216
 trials=[t for r in records for t in r['trials']];assert len(trials)==648 and all(set(t['controls'])==set(protocol['controls']) for t in trials);required=math.ceil(.9*len(trials));identity_required=math.ceil(.9*len(records));identity=sum(r['predicted_action']==r['action'] for r in records);candidate=[t['controls']['candidate'] for t in trials];safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=.35+1e-12 and x['energy_abs_work']<=4 and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30
 safety=sum(safe(x) for x in candidate);recovered=sum(x['recovered'] for x in candidate);completed=sum(x['completion_ratio']>=.65 for x in candidate);an=('uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');cn=('angle_only','common_contact')+an;aw={n:sum(t['controls']['candidate']['angle_rmse_truth']<t['controls'][n]['angle_rmse_truth'] for t in trials) for n in an};cw={n:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][n]['contact_mae_truth'] for t in trials) for n in cn};means={n:{k:statistics.mean(t['controls'][n][k] for t in trials) for k in ('angle_rmse_truth','contact_mae_truth')} for n in protocol['controls']};angle=all(aw[n]>=required for n in an) and means['candidate']['angle_rmse_truth']<=1.05*means['angle_only']['angle_rmse_truth'];contact=cw['angle_only']>=required and cw['common_contact']>=required and sum(cw[n]>=required for n in cn)>=5;recomputed={'final_visual_cases':len(records),'final_trials':len(trials),'required_trials':required,'identity_correct':identity,'identity_required':identity_required,'candidate_safety_passed':safety,'candidate_recovered':recovered,'candidate_completed':completed,'candidate_angle_wins':aw,'candidate_contact_wins':cw,'means':means,'angle_gate_passed':angle,'contact_gate_passed':contact,'passed':identity>=identity_required and safety==len(trials) and recovered>=required and completed>=required and angle and contact}
 for key,value in recomputed.items():
  if key!='means':assert value==reported[key],key
 for name,metrics in means.items():
  for key,value in metrics.items():assert abs(value-reported['means'][name][key])<1e-15,(name,key)
 return recomputed
if __name__=='__main__':
 r=verify(load(sys.argv[1] if len(sys.argv)>1 else EXTRACT));print('Series89B3 primary independently recomputed:',r['passed'],'identity',r['identity_correct'],'contact',json.dumps(r['candidate_contact_wins'],sort_keys=True))
