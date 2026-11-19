"""Short technical check of candidate generation, actual eyes and 6-axis ridge.

Not a multi-hour study and not user data.
"""
import importlib.util
import time
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('wing_long_stimuli',root/'experiments/templates/53_long_user_wing_stimuli.py')
base=load('wing_user_51',root/'experiments/templates/51_two_flies_user_trajectory_learning.py')
studio=base.load('long_pilot_studio',base.HERE/'50_two_flies_wing_studio_pilot.py',base.STUDIO_SHA)
pilot=studio.load('long_pilot_visual',base.HERE/'47_two_flies_imitation_learning.py',base.PILOT_SHA)
engine=studio.load('long_pilot_engine',base.HERE/'38_two_flies_observation.py',base.ENGINE_SHA)
examples=root/'experiments/examples/wing-user-training'
train,test=m.prepare_split([examples/'train-a.json',examples/'train-b.json'],[examples/'test-a.json'])
scene=studio.Scene(engine);stats=base.empty_stats();all_x=[];all_y=[];hold={test[0]['motion_sha256']}
start=time.monotonic()
for ident in range(6):
    result=m.accepted_candidate(train,hold,ident);assert result is not None
    spec,deg=result;images=scene.render(deg*np.pi/180,distance=spec['distance'],offset=spec['side_offset']);x=pilot.history(images);y=deg[2:]*np.pi/180
    base.update_stats(stats,x,y);all_x.append(x);all_y.append(y)
    if ident==1:
        baseline=base.fit(stats)
    if ident>=2:assert spec['distance']!=4.0 and spec['source_train_id'] in (1,2)
mean,scale,intercept,weights=base.fit(stats)
x=np.concatenate(all_x);y=np.concatenate(all_y);z=(x-x.mean(0))/np.where(x.std(0)<1e-6,1,x.std(0))
direct=np.linalg.solve(z.T@z/len(z)+np.eye(base.DIM),z.T@(y-y.mean(0))/len(y))
np.testing.assert_allclose(weights,direct,atol=2e-10);np.testing.assert_allclose(intercept,y.mean(0),atol=1e-13)
test_y=test[0]['angles_deg']*np.pi/180;test_x=pilot.history(scene.render(test_y));pred=np.clip((test_x-mean)/scale@weights+intercept,-np.pi/3,np.pi/3)
mu0,sc0,b0,w0=baseline;pred0=np.clip((test_x-mu0)/sc0@w0+b0,-np.pi/3,np.pi/3)
score=lambda p:float(np.sqrt(np.mean((p-test_y[2:])**2)))
print(f'developer-only, candidate motions 6, train frames {stats["n"]}, test frames {len(test_y)-2}')
print(f'RMSE: baseline={score(pred0):.9f} candidate={score(pred):.9f} zero={score(np.zeros_like(pred)):.9f}')
print(f'total_seconds={time.monotonic()-start:.3f}; includes training, direct-fit check and test; not a benchmark')
assert np.isfinite(pred).all()
