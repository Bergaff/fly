"""Comparison and overlap sampling on local synthetic examples, not user data."""
import csv
import importlib.util
import json
import tempfile
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('eval56',root/'experiments/templates/56_user_wing_evaluation.py')
stim=load('stim53',root/'experiments/templates/53_long_user_wing_stimuli.py')
base=load('base51',root/'experiments/templates/51_two_flies_user_trajectory_learning.py')
studio=base.load('studio_eval',base.HERE/'50_two_flies_wing_studio_pilot.py',base.STUDIO_SHA)
pilot=studio.load('pilot_eval',base.HERE/'47_two_flies_imitation_learning.py',base.PILOT_SHA)
engine=studio.load('engine_eval',base.HERE/'38_two_flies_observation.py',base.ENGINE_SHA)
examples=root/'experiments/examples/wing-user-training';tp=[examples/'train-a.json',examples/'train-b.json'];ep=[examples/'test-a.json']
train,test=stim.prepare_split(tp,ep);source_before={p:p.read_bytes() for p in tp+ep}
with tempfile.TemporaryDirectory() as td:
    tmp=Path(td);folder=base.run(tp,ep,tmp/'runs');old,digest=m.load_series51_model(folder)
    meta=json.loads((folder/'metadata.json').read_text());assert digest==meta['model_sha256']
    # Train a separate candidate from originals and four labelled variations.
    scene=studio.Scene(engine);stats=base.empty_stats()
    for ident in range(6):
        spec,deg=stim.accepted_candidate(train,{test[0]['motion_sha256']},ident)
        images=scene.render(deg*np.pi/180,distance=spec['distance'],offset=spec['side_offset'])
        base.update_stats(stats,pilot.history(images),deg[2:]*np.pi/180)
    mean,scale,intercept,weights=base.fit(stats);new={'mean':mean,'scale':scale,'intercept':intercept,'weights':weights}
    test_angles=test[0]['angles_deg']*np.pi/180
    with np.load(folder/'test_001'/'observer_vision.npz',allow_pickle=False) as z:images=z['eye_rgb'].copy()
    np.testing.assert_array_equal(m.feature_history(images),pilot.history(images))
    outputs=m.compare_models(images,test_angles,old,new)
    assert outputs['metrics']['old']['rmse_rad']==meta['holdout_metrics']['new']['rmse_rad']
    with (folder/'test_001'/'user_predictions.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    for i,axis in enumerate(base.CHANNELS):
        np.testing.assert_allclose(outputs['predictions']['old'][:,i],[float(r[f'predicted_{axis}_rad']) for r in rows],atol=1e-12)
        assert abs(outputs['metrics']['old']['axis_rmse_rad'][axis]-meta['holdout_metrics']['axis_new'][axis]['rmse_rad'])<1e-14
    print('LOCAL developer-only RMSE old / new / zero / mean:',*[f"{outputs['metrics'][k]['rmse_rad']:.9f}" for k in ('old','new','zero','training_mean')])
    expected=float(np.sqrt(np.mean((outputs['predictions']['new']-test_angles[2:])**2)))
    assert abs(expected-outputs['metrics']['new']['rmse_rad'])<1e-14
    assert abs(outputs['metrics']['zero']['rmse_rad']-meta['holdout_metrics']['zero']['rmse_rad'])<1e-14
    altered=test_angles.copy();altered[2:]+=.1
    modified=m.compare_models(images,altered,old,new)
    np.testing.assert_array_equal(outputs['predictions']['old'],modified['predictions']['old'])
    np.testing.assert_array_equal(outputs['predictions']['new'],modified['predictions']['new'])
    assert outputs['metrics']['old']['rmse_rad']!=modified['metrics']['old']['rmse_rad']
    # Output clipping is applied to each model, independently of labels.
    clipped={**new,'weights':np.zeros_like(weights),'intercept':np.full(6,2.)}
    assert np.all(m.predict(clipped,m.feature_history(images))==np.pi/3)
    # Sampling is disclosed: a candidate can match a test exactly but be absent from a small sample.
    records=[]
    for ident in range(8):
        spec,deg=stim.candidate(train,ident)
        records.append({'id':ident,'status':'accepted','spec':spec,'motion_sha256':spec['sampled_motion_sha256']})
    _,held_angles=stim.candidate(train,7);held={'id':2,'times':train[1]['times'].copy(),'angles_deg':held_angles}
    small=m.overlap_sample(stim,train,[held],records,cap=2)
    assert small['audited_count']==2 and small['accepted_total']==8 and not small['is_exhaustive'] and small['sample_ids']==[0,1]
    full=m.overlap_sample(stim,train,[held],records,cap=8)
    assert full['audited_count']==8 and full['is_exhaustive'] and np.all(full['tests'][0]['nearest_rms_deg']==0)
    assert np.max(small['tests'][0]['nearest_rms_deg'])>0
    # Check exact distances against the reference audit for the first two originals.
    direct=stim.assess_history_overlap(train,[held])[0]
    np.testing.assert_allclose(small['tests'][0]['nearest_rms_deg'],direct['nearest_rms_deg'],atol=1e-14)
    bad=[dict(r) for r in records];bad[0]['motion_sha256']='0'*64
    try:m.overlap_sample(stim,train,[held],bad,cap=8);raise AssertionError('corrupted log accepted')
    except ValueError as e:assert 'Журнал' in str(e)
    original=(folder/'model_six_axes.npz').read_bytes();(folder/'model_six_axes.npz').write_bytes(original+b'wrong')
    try:m.load_series51_model(folder);raise AssertionError('corrupted baseline accepted')
    except ValueError as e:assert 'SHA' in str(e)
    (folder/'model_six_axes.npz').write_bytes(original);(folder/'INCOMPLETE.txt').write_text('incomplete')
    try:m.load_series51_model(folder);raise AssertionError('incomplete baseline accepted')
    except ValueError:pass
assert all(p.read_bytes()==content for p,content in source_before.items())
print('Independent same-frame old/new comparison and bounded training-overlap sampling verified.')
