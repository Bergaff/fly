"""Verify exact pasted series 61 summary against earlier series 59 artifacts."""
import csv,json,math
from pathlib import Path
root=Path(__file__).resolve().parents[1]
summary=json.loads((root/'experiments/reports/long-user-wing-context-intervention-user-summary-transcribed.json').read_text(encoding='utf-8'))
prior=json.loads((root/'experiments/reports/long-user-wing-user-summary-transcribed.json').read_text(encoding='utf-8'))
assert summary['schema']=='wing-context-intervention-v1'
assert summary['source_test_id']==2 and summary['source_role']=='new_test'
assert summary['target_axis']=='right_x' and summary['segment_s']==[1.44,1.6]
assert summary['active_training_seconds']==28800.937000000005
assert summary['baseline_model_sha256']==prior['baseline_model_sha256']
assert summary['new_model_sha256']==prior['new_model_sha256']
rows={x['condition']:x for x in summary['conditions']}
assert len(rows)==12 and all(x['old']['frames']==x['new']['frames']==5 for x in rows.values())
# Independently recompute the untouched baseline from the original uploaded CSV.
with (root/'experiments/reports/long-user-wing-user-test-002-predictions.csv').open(encoding='utf-8-sig',newline='') as f:
    source=[x for x in csv.DictReader(f) if 1.44-1e-12<=float(x['time_s'])<=1.6+1e-12]
truth=[float(x['teacher_right_x_rad']) for x in source]
for model in ('old','new'):
    pred=[float(x[f'{model}_right_x_rad']) for x in source]
    err=[a-b for a,b in zip(pred,truth)]
    got=rows['baseline'][model]
    assert abs((sum(x*x for x in err)/len(err))**.5-got['rmse_rad'])<1e-15
    assert abs(sum(map(abs,err))/len(err)-got['mae_rad'])<1e-15
    assert abs(sum(pred)/len(pred)-got['mean_prediction_rad'])<1e-15
truth_mean=sum(truth)/len(truth)
assert abs(truth_mean*180/math.pi-18.56)<1e-12
only=rows['only_right_x']
assert abs((only['old']['mean_prediction_rad']-truth_mean)*180/math.pi+9.83014808055)<1e-10
assert abs((only['new']['mean_prediction_rad']-truth_mean)*180/math.pi+11.9320863683)<1e-10
assert max((x for x in rows.values() if x['changed_axis']),key=lambda x:abs(x['new']['mean_delta_from_baseline_rad']))['condition']=='right_y_plus_10deg'
print('exact context summary and baseline provenance passed')
