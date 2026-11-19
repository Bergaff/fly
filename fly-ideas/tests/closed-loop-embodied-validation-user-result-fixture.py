#!/usr/bin/env python3
"""Independent aggregate verifier for uploaded or persisted series89 result."""
from __future__ import annotations
import hashlib,json,math,statistics,sys
from pathlib import Path
EXPECTED_SHA='0b44d61b58b374ac95037ba8a853e23b0c48a1b8510a0b0f4c323ebb509d1105'
ROOT=Path(__file__).resolve().parents[1];EXTRACT=ROOT/'experiments/reports/closed-loop-embodied-validation-user-summary-extract.json'
def load(path):
 raw=Path(path).read_bytes();d=json.loads(raw)
 if Path(path).resolve()!=EXTRACT.resolve() and hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA:raise AssertionError('Unexpected uploaded summary SHA.')
 return d
def verify(d):
 if d.get('schema')=='closed-loop-embodied-validation-user-extract-v1':records=d['records'];reported=d['reported_primary'];protocol=d['protocol'];source_pass=d['source84z_passed']
 else:records=d['tests'];reported=d['primary'];protocol=d['protocol'];source_pass=d['source84z_primary']['passed']
 assert source_pass and protocol['mode']=='full' and protocol['training_allowed'] is False
 assert protocol['script_sha256']=='e0412778b2e7e15c7c202241ededfa997bb6e8c0e39d5f3d3084940dc0d7e218'
 assert protocol['runner88_sha256']=='888778dd5771f740e142747f0bad2eb1cadff8147bf01c6b2fe480c6952daa30'
 assert protocol['series88_extract_sha256']=='baa175ce7af1b20e7f37d9e24d3fb804620276b5f4073be6a15bd4a6ddd8e6e1'
 assert protocol['selected_model_sha256']=='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0'
 assert [x['id'] for x in protocol['motions']]==list(range(567,603)) and [x['corner_id'] for x in protocol['novel_views']]==list(range(101,113))
 assert len(records)==432 and len({(x['id'],x['corner_id']) for x in records})==432
 assert {x['id'] for x in records}==set(range(567,603)) and {x['corner_id'] for x in records}==set(range(101,113))
 assert all(x['state_coefficients']==72 and x['state_unchanged_during_delay'] and x['state_sha256_before_delay']==x['state_sha256_after_delay'] for x in records)
 assert len({x['state_sha256'] for x in records})==432
 assert all(not x[k] for x in records for k in ('teacher_access_during_rollout','rgb_access_during_rollout','framewise_observer_buffer_access_during_rollout'))
 trials=[t for r in records for t in r['trials']];assert len(trials)==1296 and all(set(t['controls'])==set(protocol['controls']) for t in trials)
 normal=[t['controls']['normal'] for t in trials];required=math.ceil(.9*len(trials));safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=.35+1e-12 and x['energy_abs_work']<=4. and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30
 safety=sum(safe(x) for x in normal);recovered=sum(x['recovered'] for x in normal);completed=sum(x['completion_ratio']>=.65 for x in normal);names=('zero_state','shuffled_state','open_loop','shared_lesion');wins={name:sum(t['controls']['normal']['angle_rmse_truth']<t['controls'][name]['angle_rmse_truth'] for t in trials) for name in names};contact={name:sum(t['controls']['normal']['contact_mae_truth']<t['controls'][name]['contact_mae_truth'] for t in trials) for name in names};means={name:{'angle_rmse_truth':statistics.mean(t['controls'][name]['angle_rmse_truth'] for t in trials),'contact_mae_truth':statistics.mean(t['controls'][name]['contact_mae_truth'] for t in trials),'energy_abs_work':statistics.mean(t['controls'][name]['energy_abs_work'] for t in trials)} for name in protocol['controls']};angle_gate=all(wins[x]>=required for x in wins);contact_gate=sum(contact[x]>=required for x in contact)>=3;recomputed={'visual_cases':len(records),'embodied_trials':len(trials),'required_trials':required,'normal_safety_passed':safety,'normal_recovered':recovered,'normal_completed':completed,'normal_angle_wins':wins,'normal_contact_wins':contact,'means':means,'angle_gate_passed':angle_gate,'contact_gate_passed':contact_gate,'passed':safety==len(trials) and recovered>=required and completed>=required and angle_gate and contact_gate}
 for key,value in recomputed.items():
  if key!='means':assert value==reported[key],key
 for name,metrics in means.items():
  for key,value in metrics.items():assert abs(value-reported['means'][name][key])<1e-15,(name,key)
 causes={'nan':sum(x['nan_count']!=0 for x in normal),'limits':sum(x['limit_violations']!=0 for x in normal),'torque':sum(x['max_abs_torque']>.35+1e-12 for x in normal),'energy':sum(x['energy_abs_work']>4. for x in normal),'tilt':sum(x['max_tilt_rad']>.25 for x in normal),'body_z':sum(x['minimum_body_z']<.30 for x in normal)}
 return recomputed,causes
if __name__=='__main__':
 result,causes=verify(load(sys.argv[1] if len(sys.argv)>1 else EXTRACT));print('Series89 primary independently recomputed:',result['passed'],'safety causes:',json.dumps(causes,sort_keys=True))
