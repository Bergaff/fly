"""Small actual two-eye training exercise with an interruption and reload."""
import hashlib
import importlib.util
import tempfile
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
mod=load('stimuli',root/'experiments/templates/53_long_user_wing_stimuli.py')
ck=load('checkpoint',root/'experiments/templates/54_user_wing_checkpoint.py')
base=load('base51',root/'experiments/templates/51_two_flies_user_trajectory_learning.py')
studio=base.load('cp_studio',base.HERE/'50_two_flies_wing_studio_pilot.py',base.STUDIO_SHA)
pilot=studio.load('cp_visual',base.HERE/'47_two_flies_imitation_learning.py',base.PILOT_SHA)
engine=studio.load('cp_engine',base.HERE/'38_two_flies_observation.py',base.ENGINE_SHA)
examples=root/'experiments/examples/wing-user-training'
train,test=mod.prepare_split([examples/'train-a.json',examples/'train-b.json'],[examples/'test-a.json'])
scene=studio.Scene(engine);held={x['motion_sha256'] for x in test};stats=ck.empty_stats()
input_bytes={name:(examples/name).read_bytes() for name in ('train-a.json','train-b.json','test-a.json')}
protocol={'schema':'local-scene-fixture','source_sha256':{name:ck.sha(data) for name,data in input_bytes.items()}}
with tempfile.TemporaryDirectory() as td:
    db=Path(td)/'checkpoint.sqlite3';ck.create(db,protocol,input_bytes)
    for ident in range(4):
        spec,angles=mod.accepted_candidate(train,held,ident)
        rgb=scene.render(angles*np.pi/180,distance=spec['distance'],offset=spec['side_offset'])
        x=pilot.history(rgb);y=angles[2:]*np.pi/180;base.update_stats(stats,x,y)
        rec={'id':ident,'status':'accepted','frames':len(y),'motion_sha256':spec['sampled_motion_sha256'],
             'rgb_sha256':hashlib.sha256(rgb.tobytes()).hexdigest(),'spec':spec}
        ck.commit_batch(db,protocol,ident,[rec],stats,ident+1)
        if ident==1:
            # Discard in-memory accumulators and recover only committed state.
            reloaded=ck.open_verified(db,protocol);assert reloaded['next_id']==2
            stats=reloaded['stats']
    recovered=ck.open_verified(db,protocol);assert recovered['next_id']==4 and recovered['stats']['n']==196
    # Replay all deterministic training examples independently to check the recovered fit.
    direct=base.empty_stats()
    for ident in range(4):
        spec,angles=mod.accepted_candidate(train,held,ident);rgb=scene.render(angles*np.pi/180,distance=spec['distance'],offset=spec['side_offset'])
        base.update_stats(direct,pilot.history(rgb),angles[2:]*np.pi/180)
    for a,b in zip(base.fit(direct),base.fit(recovered['stats'])):np.testing.assert_allclose(a,b,atol=1e-12)
    test_y=test[0]['angles_deg']*np.pi/180;features=pilot.history(scene.render(test_y))
    mean,scale,intercept,weights=base.fit(recovered['stats']);pred=np.clip((features-mean)/scale@weights+intercept,-np.pi/3,np.pi/3)
    assert np.isfinite(pred).all() and pred.shape==(49,6)
    print('Saved, reopened and checked real two-eye frame statistics; test RMSE',float(np.sqrt(np.mean((pred-test_y[2:])**2))))
