#!/usr/bin/env python3
"""Independent arithmetic checks for the user-pasted full series 64 summary."""
from __future__ import annotations
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'experiments/reports/wing-context-invariant-replication-user-summary-transcribed.json'
def close(a,b,tol=1e-12):assert math.isclose(a,b,rel_tol=0,abs_tol=tol),(a,b)
def main():
 d=json.loads(PATH.read_text(encoding='utf8'));a=d['aggregate'];rows=d['holdouts']
 assert d['status']=='completed' and d['protocol']['models_frozen'] is True
 assert len(rows)==a['holdouts']==5 and sum(x['frames'] for x in rows)==a['frames']==245
 assert [x['holdout_index'] for x in rows]==[1,2,3,4,5]
 for row in rows:
  c=row['control'];i=row['context_invariant'];close(c['rmse_rad']**2*c['frames'],c['sse_rad2']);close(i['rmse_rad']**2*i['frames'],i['sse_rad2'])
  close(i['rmse_rad']-c['rmse_rad'],row['paired_rmse_difference_rad']);close(i['mae_rad']-c['mae_rad'],row['paired_mae_difference_rad'])
 close(sum(x['paired_rmse_difference_rad'] for x in rows)/5,a['primary_mean_paired_rmse_difference_rad'])
 close(sum(x['paired_mae_difference_rad'] for x in rows)/5,a['mean_paired_mae_difference_rad'])
 assert sum(x['paired_rmse_difference_rad']<0 for x in rows)==a['holdouts_rmse_better']==3
 assert sum(x['paired_rmse_difference_rad']>0 for x in rows)==a['holdouts_rmse_worse']==2
 for model in ('control','context_invariant'):
  pooled=a[f'{model}_pooled'];close(sum(x[model]['sse_rad2'] for x in rows),pooled['sse_rad2']);close(math.sqrt(pooled['sse_rad2']/245),pooled['rmse_rad'])
  close(sum(x[model]['mae_rad']*49 for x in rows)/245,pooled['mae_rad']);close(sum(x[model]['mean_error_rad']*49 for x in rows)/245,pooled['mean_error_rad'])
  assert sum(x[model]['opposite_sign_frames'] for x in rows)==pooled['opposite_sign_frames']
 c=a['control_pooled'];i=a['context_invariant_pooled'];close(100*(i['rmse_rad']/c['rmse_rad']-1),a['pooled_rmse_change_percent'])
 close(100*(i['mae_rad']/c['mae_rad']-1),9.227579558746157);close(100*(abs(i['mean_error_rad'])/abs(c['mean_error_rad'])-1),-52.137521401341004)
 assert (c['opposite_sign_frames'],i['opposite_sign_frames'])==(52,75)
 print('series 64 user result fixture passed')
if __name__=='__main__':main()
