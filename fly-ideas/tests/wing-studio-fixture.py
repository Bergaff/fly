import importlib.util,json,math,sys,tempfile
from pathlib import Path
import numpy as np
import mujoco
root=Path(__file__).resolve().parents[1]; path=root/'experiments/templates/50_two_flies_wing_studio_pilot.py'
spec=importlib.util.spec_from_file_location('wing_studio',path); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
traj={'schema':'fly-wings-trajectory-v1','fps':25,'duration_s':.52,'keyframes':[{'t':0,'angles_deg':[0,10,0,0,0,0]},{'t':.24,'angles_deg':[30,0,0,-10,20,0]},{'t':.52,'angles_deg':[0,0,0,0,0,0]}]}
with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp);source=tmp/'input.json';source.write_text(json.dumps(traj)); before=source.read_bytes()
    times,y=m.sample(traj);assert len(times)==14 and np.isclose(times[-1],.52) and np.isclose(y[6,0],math.pi/6)
    for mutation in [dict(traj,duration_s=.51),dict(traj,fps=20),dict(traj,keyframes=[traj['keyframes'][0],traj['keyframes'][0]])]:
        try:m.validate(mutation);raise AssertionError('Invalid trajectory accepted')
        except ValueError:pass
    engine=m.load('fixture_engine',m.HERE/'38_two_flies_observation.py',m.ENGINE_SHA); scene=m.Scene(engine)
    # Each hinge has its own coordinate, and changing only one changes its wing orientation.
    assert len(set(scene.joints))==6
    m0=scene.render(np.zeros((1,6))); images=[]
    for i in range(6):
        angles=np.zeros((1,6));angles[0,i]=.4; images.append(scene.render(angles));
        assert not np.array_equal(m0,images[-1]),f'axis {i} did not change images'
    a=m.run(source,tmp/'runs',4,2);result=json.loads((a/'playback.json').read_text());meta=json.loads((a/'metadata.json').read_text());assert source.read_bytes()==before
    assert not (a/'INCOMPLETE.txt').exists() and meta['status']=='completed' and len(result['samples'])==14
    assert result['samples'][0]['prediction_deg'] is None and result['samples'][1]['prediction_deg'] is None
    pred=np.array([x['prediction_deg'] for x in result['samples'][2:]])*np.pi/180
    np.testing.assert_allclose(m.metrics(y[2:],pred)['rmse_rad'],result['user_metrics']['new']['rmse_rad'])
    np.testing.assert_allclose([x['teacher_deg'] for x in result['samples']],y*180/np.pi)
    # Independent user input never enters fit: changing only user file yields identical model.
    other=dict(traj,keyframes=[dict(k,angles_deg=[-v for v in k['angles_deg']]) for k in traj['keyframes']]);source.write_text(json.dumps(other));b=m.run(source,tmp/'runs',4,2)
    with np.load(a/'model_six_axes.npz') as x,np.load(b/'model_six_axes.npz') as z:
        for key in x.files:np.testing.assert_array_equal(x[key],z[key])
    assert (a/'trajectory.json').read_bytes()==before
    assert all(result['samples'][i]['prediction_deg'] is not None for i in range(2,len(times)))
print('wing studio fixture passed')
