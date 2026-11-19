#!/usr/bin/env python3
"""Independent aggregate verifier for the uploaded or persisted series88 result."""
from __future__ import annotations
import hashlib,json,math,statistics,sys
from pathlib import Path
EXPECTED_SHA='94fac84c12fb0049aada2dd5b04ac84da30d63808e6d0a45cd09d0c731780feb'
ROOT=Path(__file__).resolve().parents[1];EXTRACT=ROOT/'experiments/reports/actuator-bridge-prototype-user-summary-extract.json'
def load(path):
 raw=Path(path).read_bytes();d=json.loads(raw)
 if Path(path).resolve()!=EXTRACT.resolve() and hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA:raise AssertionError('Unexpected uploaded summary SHA.')
 return d
def verify(d):
 if d.get('schema')=='actuator-bridge-prototype-user-extract-v1':records=d['records'];reported=d['reported_primary'];protocol=d['protocol'];source_pass=d['source84z_passed']
 else:
  records=[]
  for x in d['tests']:
   a=x['actuator'];records.append({'id':x['id'],'replicate':x['replicate'],'action':x['action'],'corner_id':x['corner_id'],'motion_sha256':x['motion_sha256'],'state_coefficients':a['state_coefficients'],'target_policy_sha256':a['target_policy_sha256'],'teacher_access_during_rollout':a['teacher_access_during_rollout'],'rgb_access_during_rollout':a['rgb_access_during_rollout'],'framewise_observer_buffer_access_during_rollout':a['framewise_observer_buffer_access_during_rollout'],'state_unchanged_during_delay':x['state_unchanged_during_delay'],'state_sha256_before_delay':x['state_sha256_before_delay'],'state_sha256_after_delay':x['state_sha256_after_delay'],'closed_loop':a['closed_loop'],'open_loop':a['open_loop'],'truth_rmse_rad':a['truth_rmse_rad']})
  reported=d['primary'];protocol=d['protocol'];source_pass=d['source84z_primary']['passed']
 assert source_pass and protocol['mode']=='full' and protocol['training_allowed'] is False
 assert protocol['script_sha256']=='888778dd5771f740e142747f0bad2eb1cadff8147bf01c6b2fe480c6952daa30'
 assert protocol['runner87_sha256']=='105f0c26e0b9fd5e0fa9a6060af48fe4fa900da09ff5e906116da1d12d7caa54'
 assert protocol['series87_extract_sha256']=='f30a118a72e450cbe76024c74ff32764b8f545f41b3ecc6b3957f9fd0a6faf6f'
 assert protocol['selected_model_sha256']=='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0'
 assert [x['id'] for x in protocol['motions']]==list(range(537,567)) and protocol['geometry_corners']==16
 assert len(records)==480 and len({(x['id'],x['corner_id']) for x in records})==480
 assert {x['id'] for x in records}==set(range(537,567)) and {x['corner_id'] for x in records}==set(range(1,17))
 assert all(x['state_coefficients']==72 and x['state_unchanged_during_delay'] and x['state_sha256_before_delay']==x['state_sha256_after_delay'] for x in records)
 assert len({x['target_policy_sha256'] for x in records})==480
 assert all(not x[k] for x in records for k in ('teacher_access_during_rollout','rgb_access_during_rollout','framewise_observer_buffer_access_during_rollout'))
 c=[x['closed_loop'] for x in records];o=[x['open_loop'] for x in records];n=len(records);required=math.ceil(.9*n)
 recomputed={'cases':n,'finite_passed':all(x['nan_count']==0 for x in c),'joint_limits_passed':all(x['limit_violations']==0 for x in c),'support_stability_passed':all(x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30 for x in c),'bounded_torque_energy_passed':all(x['max_abs_torque']<=.35+1e-12 and x['energy_abs_work']<=4. for x in c),'closed_loop_tracking_rmse_rad':statistics.mean(x['tracking_rmse_rad'] for x in c),'open_loop_tracking_rmse_rad':statistics.mean(x['tracking_rmse_rad'] for x in o),'closed_loop_better_wins':sum(x['tracking_rmse_rad']<y['tracking_rmse_rad'] for x,y in zip(c,o)),'completed_bouts':sum(x['completion_ratio']>=.65 for x in c),'required_cases':required}
 recomputed['passed']=recomputed['finite_passed'] and recomputed['joint_limits_passed'] and recomputed['support_stability_passed'] and recomputed['bounded_torque_energy_passed'] and recomputed['closed_loop_tracking_rmse_rad']<=.12 and recomputed['closed_loop_tracking_rmse_rad']<.80*recomputed['open_loop_tracking_rmse_rad'] and recomputed['closed_loop_better_wins']>=required and recomputed['completed_bouts']>=required
 assert recomputed==reported
 by_action={}
 for action in ('foreleg_rubbing','head_directed_grooming','reach_withdraw'):
  rr=[x for x in records if x['action']==action];cc=[x['closed_loop'] for x in rr];oo=[x['open_loop'] for x in rr];by_action[action]={'cases':len(rr),'closed_rmse':statistics.mean(x['tracking_rmse_rad'] for x in cc),'open_rmse':statistics.mean(x['tracking_rmse_rad'] for x in oo),'wins':sum(x['tracking_rmse_rad']<y['tracking_rmse_rad'] for x,y in zip(cc,oo)),'completed':sum(x['completion_ratio']>=.65 for x in cc),'truth_rmse':statistics.mean(x['truth_rmse_rad'] for x in rr)}
 return recomputed,by_action
if __name__=='__main__':
 result,actions=verify(load(sys.argv[1] if len(sys.argv)>1 else EXTRACT));print('Series88 primary independently recomputed from 480 exported case metrics:',result['passed']);print(json.dumps(actions,ensure_ascii=False,sort_keys=True))
