"""Recalculate user-uploaded predictions against user-pasted summaries.

The attached CSV is available; NPZ, RGB, SQLite, and original 51 CSV are not.
Slices and paired comparisons were selected after viewing the data.
"""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORTS=ROOT/'experiments/reports'
CSV=REPORTS/'long-user-wing-user-test-002-predictions.csv'
PREVIOUS=REPORTS/'user-wing-learning-user-predictions-transcribed.csv'
SUMMARY=REPORTS/'long-user-wing-user-summary-transcribed.json'
AXES=('left_x','left_y','left_z','right_x','right_y','right_z')
MODELS=('old','new','zero','training_mean')

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        assert reader.fieldnames and len(reader.fieldnames)==len(set(reader.fieldnames))
        return reader.fieldnames,[{k:float(v) for k,v in row.items()} for row in reader]

def close(a,b,tol=1e-12): assert abs(a-b)<=tol, (a,b)
def error(row,model,axis): return row[f'{model}_{axis}_rad']-row[f'teacher_{axis}_rad']
def sse(rows,model): return sum(error(r,model,a)**2 for r in rows for a in AXES)
def rmse(rows,model): return math.sqrt(sse(rows,model)/(6*len(rows)))
def mae(rows,model): return sum(abs(error(r,model,a)) for r in rows for a in AXES)/(6*len(rows))

assert hashlib.sha256(CSV.read_bytes()).hexdigest()=='a753267f2a4625241b2c7f771a72d0bead8de1d75f2036ce5e972a7af5a49563'
fields,rows=read(CSV);summary=json.loads(SUMMARY.read_text(encoding='utf-8'));t=summary['tests'][1]
assert fields==['time_s']+[f'teacher_{a}_rad' for a in AXES]+[f'{m}_{a}_rad' for m in MODELS for a in AXES]
assert len(rows)==49 and t['test_id']==2 and t['role']=='new_test' and t['frames']==49
for i,r in enumerate(rows):
    assert all(math.isfinite(v) for v in r.values())
    close(r['time_s'],.08+.04*i)
    for a in AXES:
        assert r[f'zero_{a}_rad']==0
        close(r[f'training_mean_{a}_rad'],rows[0][f'training_mean_{a}_rad'])
        assert abs(r[f'teacher_{a}_rad'])<=math.pi/3+1e-12
        for m in ('old','new'): assert abs(r[f'{m}_{a}_rad'])<=math.pi/3+1e-12
for model in MODELS:
    metric=t['metrics'][model]
    close(rmse(rows,model),metric['rmse_rad']);close(mae(rows,model),metric['mae_rad'])
    for axis in AXES:
        errors=[error(r,model,axis) for r in rows]
        close(math.sqrt(sum(x*x for x in errors)/len(errors)),metric['axis_rmse_rad'][axis])
        close(sum(abs(x) for x in errors)/len(errors),metric['axis_mae_rad'][axis])
assert sum(sse([r],'new')<sse([r],'old') for r in rows)==10
assert sum(sse([r],'new')>sse([r],'old') for r in rows)==39
close(sse(rows[:4],'new')/sse(rows,'new'),0.23438870921120925)
close(rmse(rows[:4],'old'),0.458666785,1e-9);close(rmse(rows[:4],'new'),0.367757289,1e-9)
close(rmse(rows[4:],'old'),0.187132019,1e-9);close(rmse(rows[4:],'new'),0.198162215,1e-9)
event=[r for r in rows if 1.44-1e-9<=r['time_s']<=1.60+1e-9]
assert len(event)==5
close(sse(event,'new')/sse(rows,'new'),0.6712499348969925)
close((sse(event,'new')+sse(rows[:4],'new'))/sse(rows,'new'),0.9056386441082019)
worst=max(rows,key=lambda r:abs(error(r,'new','right_x')))
close(worst['time_s'],1.52)
close(error(worst,'new','right_x')*180/math.pi,-82.87615163442709,1e-9)
assert sum(error(r,'new','right_x')**2 for r in rows)/sse(rows,'new')>0.5836

# Comparison uses the earlier user-pasted, manually transcribed test-1 CSV.
# It does not prove equality of camera pixels, model weights, or original files.
assert hashlib.sha256(PREVIOUS.read_bytes()).hexdigest()=='3af3c26e4a07b9926bbad37fba684062e2ce067d34bae5a0bee57dba007fde55'
_,old=read(PREVIOUS);assert len(old)==49
for a,b in zip(rows,old):close(a['time_s'],b['time_s'])
equal=[all(abs(r[f'teacher_{a}_rad']-o[f'teacher_{a}_rad'])<1e-12 for a in AXES) for r,o in zip(rows,old)]
assert sum(equal)==32
histories={i for i in range(2,49) if all(equal[k] for k in (i,i-1,i-2))}
matching_predictions={i for i,(r,o) in enumerate(zip(rows,old)) if all(abs(r[f'old_{a}_rad']-o[f'predicted_{a}_rad'])<1e-12 for a in AXES)}
assert len(histories)==28 and histories==matching_predictions
assert all(abs(r['teacher_left_z_rad']-o['teacher_left_z_rad'])<1e-12 for r,o in zip(rows,old))
i=next(i for i,r in enumerate(rows) if abs(r['time_s']-1.48)<1e-12)
close(rows[i]['teacher_right_x_rad'],old[i]['teacher_right_x_rad'])
close(rows[i]['teacher_right_z_rad'],old[i]['teacher_right_z_rad'])
for a in ('left_x','left_y','right_y'):assert abs(rows[i][f'teacher_{a}_rad']-old[i][f'teacher_{a}_rad'])>1e-12
close(old[i]['predicted_right_x_rad']*180/math.pi,24.37267206131956,1e-9)
close(rows[i]['old_right_x_rad']*180/math.pi,-51.68990846614386,1e-9)
close(rows[i]['new_right_x_rad']*180/math.pi,-55.88479755528775,1e-9)
print('User CSV hash, all 8 aggregate metrics, frame/axis metrics, post-hoc slices and previous-test comparison verified.')
