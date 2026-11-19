import json,math
from pathlib import Path
root=Path(__file__).parents[1]
p=root/'experiments/reports/five-hour-wing-observation-user-summary-extract.json'
d=json.loads(p.read_text())
assert d['status']=='completed' and d['active_training_seconds']==18000.5
assert d['accepted_candidates']==40516 and d['training_frames']==1985284
assert len(d['tests'])==6 and [x['movement'] for x in d['tests'][1:]]==[71,72,73,74,75]
new=d['tests'][1:];a=d['derived_new_holdout_aggregate'];names=('old','new','zero','training_mean')
for name in names:
 value=math.sqrt(sum(x['rmse_rad'][name]**2 for x in new)/5)
 assert math.isclose(value,a['pooled_rmse_rad'][name],rel_tol=0,abs_tol=1e-15)
assert a['wins']=={
 'new_better_than_old':sum(x['rmse_rad']['new']<x['rmse_rad']['old'] for x in new),
 'new_better_than_zero':sum(x['rmse_rad']['new']<x['rmse_rad']['zero'] for x in new),
 'new_better_than_training_mean':sum(x['rmse_rad']['new']<x['rmse_rad']['training_mean'] for x in new),
 'holdouts':5}
assert math.isclose(a['new_minus_old_rmse_rad'],a['pooled_rmse_rad']['new']-a['pooled_rmse_rad']['old'],abs_tol=1e-15)
assert math.isclose(a['new_minus_zero_rmse_rad'],a['pooled_rmse_rad']['new']-a['pooled_rmse_rad']['zero'],abs_tol=1e-15)
assert a['pooled_rmse_rad']['new']<a['pooled_rmse_rad']['old']
assert a['pooled_rmse_rad']['new']>a['pooled_rmse_rad']['zero']
print('five-hour user result fixture: OK')
