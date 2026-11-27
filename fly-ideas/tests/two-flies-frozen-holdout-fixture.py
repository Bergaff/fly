import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

root=Path(__file__).resolve().parents[1]
script=root/'experiments/templates/48_two_flies_frozen_holdout.py'
spec=importlib.util.spec_from_file_location('holdout',script)
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
m=h.load_pilot()


def readcsv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def fails(fn, fragment):
    try:fn()
    except ValueError as e:assert fragment in str(e),str(e)
    else:raise AssertionError('expected error')

plan=h.fixed_plan();assert len(plan)==64 and len(set(plan))==64
train,oldtest=m.plan()
assert {s[1] for s in plan}.isdisjoint({s[0] for s in train+oldtest})
assert {s[2] for s in plan}.isdisjoint({s[1] for s in train+oldtest})
assert {s[4] for s in plan}.isdisjoint({s[2] for s in train+oldtest})
assert {s[3] for s in plan} == {3.6,4.4} and {s[5] for s in plan} == {0.45,0.8}
assert math.isclose(h.HARMONIC_MAX,(7/6)*math.sqrt(7/12),rel_tol=0,abs_tol=1e-15)
assert max(abs((np.sin(np.linspace(0,2*np.pi,10000))+.25*np.sin(3*np.linspace(0,2*np.pi,10000)))/h.HARMONIC_MAX)) <= 1.000001
for s in plan: assert len(h.angles(s,m)) == 50 and np.max(np.abs(h.angles(s,m))) <= s[5]+1e-12

with tempfile.TemporaryDirectory() as temp:
    temp=Path(temp);training=m.run(temp/'training');model=training/'model.npz';meta=training/'metadata.json'
    original_model=digest(model);original_meta=digest(meta)
    # Must not train at all, including while calculating the test metrics.
    def no_fit(*args,**kwargs):raise AssertionError('fit was called during holdout')
    m.fit=no_fit;h.load_pilot=lambda:m
    out=h.evaluate(model,temp/'results')
    assert digest(model)==original_model and digest(meta)==original_meta
    assert digest(out/'frozen_model.npz')==original_model and digest(out/'source_metadata.json')==original_meta
    md=json.loads((out/'metadata.json').read_text(encoding='utf8'))
    assert md['status']=='completed' and md['count']==64 and md['scored_frames_per_sequence']==48
    assert md['source_model_sha256']==original_model and md['source_metadata_sha256']==original_meta
    assert md['protocol_sha256']==digest(h.PROTOCOL) and not (out/'INCOMPLETE.txt').exists()
    table=readcsv(out/'sequence_metrics.csv');rows=readcsv(out/'predictions.csv');groups=readcsv(out/'breakdown.csv')
    assert len(table)==64*6 and len(rows)==64*48 and len(groups)==8*6
    for cond,field in [('trained','trained_angle_rad'),('untrained','untrained_angle_rad'),('zero','zero_angle_rad'),('occluded','occluded_angle_rad'),('shuffled','shuffled_angle_rad'),('clip_floor','clip_floor_angle_rad')]:
        actual=math.sqrt(sum((float(r[field])-float(r['teacher_angle_rad']))**2 for r in rows)/len(rows))
        assert abs(actual-md['scores'][cond]['rmse_rad'])<1e-12
    assert sum(md['sequences_vs_zero'].values())==64
    with np.load(out/'visual_sequences.npz',allow_pickle=False) as data, np.load(out/'frozen_model.npz',allow_pickle=False) as z:
        assert data['images'].shape==(64,50,2,32,48,3) and data['teacher_angle'].shape==(64,50)
        pred=m.predict(data['images'][0],z['mean'],z['scale'],float(z['intercept']),z['weights'])
        assert np.allclose(pred,[float(r['trained_angle_rad']) for r in rows[:48]])
        assert np.allclose(data['teacher_angle'][0,2:],[float(r['teacher_angle_rad']) for r in rows[:48]])
        for row in rows:
            y=float(row['teacher_angle_rad']);assert abs(float(row['clip_floor_angle_rad'])-np.clip(y,-.65,.65))<1e-12
    assert (out/'comparison.gif').is_file() and (out/'comparison.png').is_file()
    assert 'не обучались повторно' in (out/'ИТОГ.txt').read_text(encoding='utf-8-sig')
    # Incomplete inputs and wrong metadata are rejected before creating output.
    (training/'INCOMPLETE.txt').write_text('interrupted')
    fails(lambda:h.load_model(model,m),'INCOMPLETE')
    (training/'INCOMPLETE.txt').unlink()
    metadata=json.loads(meta.read_text(encoding='utf8'));metadata['mode']='smoke';meta.write_text(json.dumps(metadata),encoding='utf8')
    fails(lambda:h.load_model(model,m),'основного пилота')
    meta.write_text(json.dumps({**metadata,'mode':'full_pilot','history_frames':5}),encoding='utf8')
    fails(lambda:h.load_model(model,m),'history_frames')
    # Failure on rendering leaves the new folder explicitly incomplete.
    meta.write_text((out/'source_metadata.json').read_text(encoding='utf8'),encoding='utf8')
    old=h.Scene.sequence
    def broken(*args):raise RuntimeError('injected error')
    h.Scene.sequence=broken
    try:
        try:h.evaluate(model,temp/'broken')
        except RuntimeError:pass
        else:raise AssertionError('expected failure')
        bad=list((temp/'broken').iterdir());assert len(bad)==1 and (bad[0]/'INCOMPLETE.txt').exists()
    finally:h.Scene.sequence=old
    proc=subprocess.run([sys.executable,str(script),'--model',str(temp/'missing/model.npz'),'--output',str(temp/'no-result')],capture_output=True,text=True,timeout=30)
    assert proc.returncode!=0 and not (temp/'no-result').exists()
print('frozen holdout fixture: OK')
