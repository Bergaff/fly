import csv,hashlib,importlib.util,json,math,tempfile
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[1];path=root/'experiments/templates/51_two_flies_user_trajectory_learning.py'
spec=importlib.util.spec_from_file_location('user_wing',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
studio=m.load('fixture_studio',m.HERE/'50_two_flies_wing_studio_pilot.py',m.STUDIO_SHA)
pilot=studio.load('fixture_visual',m.HERE/'47_two_flies_imitation_learning.py',m.PILOT_SHA)

def trajectory(v):return {'schema':'fly-wings-trajectory-v1','fps':25,'duration_s':.52,'keyframes':[{'t':0,'angles_deg':[0,0,0,0,0,0]},{'t':.24,'angles_deg':[v,5,-5,-v,3,2]},{'t':.52,'angles_deg':[0,0,0,0,0,0]}]}
with tempfile.TemporaryDirectory() as td:
    tmp=Path(td);paths=[]
    for i in range(4):
        p=tmp/f'{i}.json';p.write_text(json.dumps(trajectory(10+8*i)),encoding='utf8');paths.append(p)
    before=[p.read_bytes() for p in paths]
    dupe=tmp/'duplicate.json';dupe.write_text(json.dumps(trajectory(10),indent=4),encoding='utf8')
    try:m.run(paths[:2],[dupe],tmp/'not-created');raise AssertionError('Обучающая траектория попала в проверку')
    except ValueError as e:assert 'Совпадают движения' in str(e)
    assert not (tmp/'not-created').exists()
    # Adding a collinear keyframe must not bypass duplicate detection.
    obj=trajectory(10);obj['keyframes'].insert(1,{'t':.12,'angles_deg':[5,2.5,-2.5,-5,1.5,1]})
    dupe.write_text(json.dumps(obj),encoding='utf8')
    try:m.prepare_inputs(paths[:2],[dupe],studio);raise AssertionError('Дубликат проскользнул')
    except ValueError as e:assert 'Совпадают движения' in str(e)
    try:m.prepare_inputs(paths[:1],paths[2:3],studio);raise AssertionError('Не хватает примеров')
    except ValueError:pass
    # Online statistics must equal direct ridge fit, including six channels.
    rng=np.random.default_rng(5);x=rng.normal(size=(40,m.DIM));y=rng.normal(size=(40,6));st=m.empty_stats()
    m.update_stats(st,x[:13],y[:13]);m.update_stats(st,x[13:],y[13:]);mu,scale,intercept,weights=m.fit(st)
    z=(x-x.mean(0))/x.std(0);direct=np.linalg.solve(z.T@z/len(z)+np.eye(m.DIM),z.T@(y-y.mean(0))/len(z))
    np.testing.assert_allclose(mu,x.mean(0),atol=1e-14);np.testing.assert_allclose(scale,x.std(0),atol=1e-14);np.testing.assert_allclose(weights,direct,atol=1e-12)
    a=m.run(paths[:2],[paths[2]],tmp/'out'); b=m.run(paths[:2],[paths[3]],tmp/'out'); c=m.run([paths[0],paths[3]],[paths[2]],tmp/'out')
    assert [p.read_bytes() for p in paths]==before
    assert not (a/'INCOMPLETE.txt').exists() and json.loads((a/'metadata.json').read_text())['status']=='completed'
    with np.load(a/'model_six_axes.npz') as first,np.load(b/'model_six_axes.npz') as second:
        for key in first.files:np.testing.assert_array_equal(first[key],second[key])
        model={k:first[k].copy() for k in first.files}
    with np.load(c/'model_six_axes.npz') as altered:
        assert not np.array_equal(model['weights'],altered['weights'])
    meta=json.loads((a/'metadata.json').read_text());manifest=json.loads((a/'input_manifest.json').read_text());assert (meta['train_sequences'],meta['test_sequences'])==(2,1)
    for item in manifest['inputs']:
        assert hashlib.sha256((a/item['copy']).read_bytes()).hexdigest()==item['source_sha256']
    folder=a/'test_001';result=json.loads((folder/'playback.json').read_text());assert result['holdout_label']=='Все проверочные траектории пользователя'
    assert result['samples'][0]['prediction_deg'] is None and result['samples'][1]['prediction_deg'] is None
    with np.load(folder/'observer_vision.npz') as vision,np.load(folder/'model_inputs.npz') as inputs:
        frames=vision['eye_rgb'];np.testing.assert_array_equal(pilot.visual_vectors(frames),inputs['frame_luminance']);np.testing.assert_array_equal(pilot.history(frames),inputs['raw_history']);np.testing.assert_array_equal((inputs['raw_history']-model['mean'])/model['scale'],inputs['normalized_history'])
        p=np.clip(inputs['normalized_history']@model['weights']+model['intercept'],-math.pi/3,math.pi/3)
        np.testing.assert_allclose([s['prediction_deg'] for s in result['samples'][2:]],p*180/math.pi,atol=1e-12)
        with Image.open(folder/'observer_vision.gif') as img:
            assert img.size==(384,128)
            # GIF is only an enlarged, palette-converted display of the source frame.
            shown=np.array(img.convert('RGB'))[::4,::4]; original=np.concatenate([frames[0,0],frames[0,1]],axis=1)
            assert np.mean(np.abs(shown.astype(int)-original.astype(int)))<4
        with Image.open(folder/'observer_model_input.gif') as img:
            shown=np.array(img.convert('L'))[::16,::16];original=np.rint(inputs['frame_luminance'][0].reshape(2,8,12).transpose(1,0,2).reshape(8,24)*255).astype('uint8')
            np.testing.assert_array_equal(shown,original)
    print('user wing fixture passed')
