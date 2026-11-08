"""Fast, local tests for a proposed long study's stimuli; no long study is run."""
import importlib.util
import json
import tempfile
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('wing_long_stimuli',root/'experiments/templates/53_long_user_wing_stimuli.py')
old=load('wing_user_51',root/'experiments/templates/51_two_flies_user_trajectory_learning.py')
studio=old.load('studio50_for_long',old.HERE/'50_two_flies_wing_studio_pilot.py',old.STUDIO_SHA)
with tempfile.TemporaryDirectory() as td:
    p=Path(td);files=[]
    def obj(amp,duration=2):
        return {'schema':'fly-wings-trajectory-v1','fps':25,'duration_s':duration,'keyframes':[{'t':0,'angles_deg':[0,0,0,0,0,0]},{'t':duration/2,'angles_deg':[amp,-amp,amp/2,-amp/3,0,amp/4]},{'t':duration,'angles_deg':[0,0,0,0,0,0]}]}
    for i,amp in enumerate((24,36,12,60)):
        path=p/f'{i}.json';path.write_text(json.dumps(obj(amp)),encoding='utf8');files.append(path)
    orig=[x.read_bytes() for x in files]
    train,test=m.prepare_split(files[:2],files[2:3]); hashes={test[0]['motion_sha256']}
    oldtrain,oldtest=old.prepare_inputs(files[:2],files[2:3],studio)
    assert [s['motion_sha256'] for s in train+test]==[s['sampled_motion_sha256'] for s in oldtrain+oldtest]
    for i in range(200):
        a,y=m.candidate(train,i);b,y2=m.candidate(train,i)
        assert a==b;np.testing.assert_array_equal(y,y2)
        assert y.shape==(51,6) and np.isfinite(y).all() and np.max(np.abs(y))<=60
        assert a['source_train_id']==i%2+1 and 3.7<=a['distance']<=4.3 and abs(a['side_offset'])<=.3
        assert m.accepted_candidate(train,hashes,i) is not None
    np.testing.assert_array_equal(m.candidate(train,0)[1],train[0]['angles_deg'])
    np.testing.assert_array_equal(m.candidate(train,1)[1],train[1]['angles_deg'])
    spec,y=m.candidate(train,12)
    assert m.accepted_candidate(train,{spec['sampled_motion_sha256']},12) is None
    with_other_heldout=m.candidate(train,12);assert with_other_heldout[0]==spec;np.testing.assert_array_equal(with_other_heldout[1],y)
    copied=p/'same.json';copied.write_text(json.dumps(obj(24),indent=3),encoding='utf8')
    try:m.prepare_split(files[:2],[copied]);raise AssertionError('Duplicate crossed split')
    except ValueError as e:assert 'Совпадает' in str(e)
    for bad in [obj(float('nan')),dict(obj(5),duration_s=2.01),dict(obj(5),fps=50),obj(61)]:
        try:m.sample_trajectory(bad);raise AssertionError('Invalid input accepted')
        except ValueError:pass
    assert [x.read_bytes() for x in files]==orig
print('Long user-wing stimulus design fixture passed; this is not a long runner.')
