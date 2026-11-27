#!/usr/bin/env python3
"""Independent arithmetic checks of the user-pasted full series 63 summary."""
from __future__ import annotations
import json,math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'experiments/reports/long-wing-context-invariant-user-summary-transcribed.json'

def close(a,b,tol=1e-12):assert math.isclose(a,b,rel_tol=0,abs_tol=tol),(a,b)

def main():
 data=json.loads(PATH.read_text(encoding='utf-8'))
 assert data['status']=='completed' and data['schema']=='wing-context-invariant-result-v1'
 p=data['protocol'];assert p['mode']=='full' and p['replacement_count']==data['replacements_completed']==30046
 assert data['training_frames_each_model']==p['source_training_frames']==2944606
 assert p['primary_metric']=='right_x RMSE on every scored holdout frame'
 assert data['control_model_sha256']=='f2ef4321e3438ac719e2148da3dc6821fb95abc43d537095728c05be214716ad'
 assert data['primary']==data['tests'][0] and data['primary']['role']=='preregistered_holdout'
 assert [x['role'] for x in data['tests']]==['preregistered_holdout','diagnostic_regression','diagnostic_regression']

 for test in data['tests']:
  right=test['right_x'];c=right['control'];i=right['context_invariant']
  close(100*(i['rmse_rad']/c['rmse_rad']-1),right['rmse_change_percent'])
  for model in ('control','context_invariant'):
   total=right[model];bins=test['fixed_amplitude_bins'][model]
   assert sum(x['metrics']['frames'] for x in bins)==total['frames']==49
   close(math.sqrt(sum(x['metrics']['frames']*x['metrics']['rmse_rad']**2 for x in bins)/49),total['rmse_rad'])
   close(sum(x['metrics']['frames']*x['metrics']['mae_rad'] for x in bins)/49,total['mae_rad'])
   close(sum(x['metrics']['frames']*x['metrics']['mean_error_rad'] for x in bins)/49,total['mean_error_rad'])
   assert sum(x['metrics']['opposite_sign_frames'] for x in bins)==total['opposite_sign_frames']

 primary=data['primary'];c=primary['right_x']['control'];i=primary['right_x']['context_invariant']
 close(c['rmse_rad']**2*49,5.6794939033360095)
 close(i['rmse_rad']**2*49,5.701459025286673)
 close(100*(i['mae_rad']/c['mae_rad']-1),7.21027791875275)
 close(100*(abs(i['mean_error_rad'])/abs(c['mean_error_rad'])-1),-88.66340450638464)
 assert (c['opposite_sign_frames'],i['opposite_sign_frames'])==(8,11)
 middle_c=primary['fixed_amplitude_bins']['control'][1]['metrics'];middle_i=primary['fixed_amplitude_bins']['context_invariant'][1]['metrics']
 close(100*(middle_i['rmse_rad']/middle_c['rmse_rad']-1),56.217556599358986)
 high_c=primary['fixed_amplitude_bins']['control'][2]['metrics'];high_i=primary['fixed_amplitude_bins']['context_invariant'][2]['metrics']
 close(100*(high_i['rmse_rad']/high_c['rmse_rad']-1),-6.0036449903519635)
 print('series 63 user result fixture passed')

if __name__=='__main__':main()
