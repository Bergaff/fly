"""End-to-end motor bridge on a small image fixture, no fabricated biological claim."""
import csv
import hashlib
import importlib.util
import json
import math
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[1]
def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,root/'experiments/templates'/filename)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
source=load('source41','41_two_flies_visual_controls.py')
bridge=load('bridge42','42_two_flies_motor_bridge.py')
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def hashes(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()}

with tempfile.TemporaryDirectory() as tmp:
    data=source.run(tmp,2,50,0,48,32)
    before=hashes(data)
    out=bridge.run(data,make_video=True,video_fps=10,video_width=80,video_height=48)
    metadata=json.loads((out/'metadata.json').read_text(encoding='utf8'))
    assert metadata['status']=='completed' and metadata['motor_frequency_hz']==2.0
    assert metadata['input_sha256']['metadata.json']==before['metadata.json']
    assert all(hashlib.sha256((data/f).read_bytes()).hexdigest()==h for f,h in before.items())
    sums={r['condition']:r for r in read(out/'conditions_summary.csv')}
    assert set(sums)=={'wings','stationary','occluded','shuffled','object','object_stationary','wings_readout_disabled'}
    assert float(sums['wings']['programmed_amplitude_rad'])>0
    for c in ('stationary','occluded','object_stationary','wings_readout_disabled'):
        assert float(sums[c]['programmed_amplitude_rad']) == 0
    assert (out/'wings/observation_spikes.csv').read_bytes()==(out/'wings_readout_disabled/observation_spikes.csv').read_bytes()
    assert sums['wings']['raw_score']==sums['wings_readout_disabled']['raw_score']
    for name,row in sums.items():
        events=read(out/name/'observation_spikes.csv')
        weights=read(out/name/'neuron_weights.csv')
        timeline=read(out/name/'motor_timeline.csv')
        assert len(weights)==32 and len(timeline)==250 and len(events)==int(row['observation_spikes'])
        assert [r['stage'] for r in timeline]==['before']*50+['observe']*100+['after']*100
        assert all(float(r['observer_left_wing_rad'])==0 for r in timeline[:150])
        for i,w in enumerate(weights):
            count=sum(int(r['neuron_id'])==i for r in events)
            assert int(w['spikes'])==count
            assert abs(float(w['weight'])-max(count/2-12.5,0)/20)<1e-12
        amp=float(row['programmed_amplitude_rad'])
        for entry in timeline[150:]:
            a=float(entry['observer_left_wing_rad']);t=float(entry['time_s'])
            assert abs(a-amp*math.sin(2*math.pi*2*(t-3)))<1e-12
            assert abs(a+float(entry['observer_right_wing_rad']))<1e-12
        assert (out/name/'movement.png').stat().st_size>0
        with Image.open(out/name/'scene.gif') as im:
            total=0
            for k in range(im.n_frames):
                im.seek(k);total+=im.info.get('duration',0)
            assert total==5000,(name,total)
    with np.load(out/'occluded/neural_input.npz') as a:
        assert np.all(a['neural_input']==128)
    with np.load(out/'shuffled/neural_input.npz') as a, np.load(data/'wing_3hz_0deg/vision.npz') as b:
        order=a['input_source_frame'];assert sorted(order.tolist())==list(range(100))
        assert np.array_equal(a['neural_input'],b['neural_input'][order])
    # Inputs are validated before creating a new result folder.
    spike=data/'wing_3hz_0deg/spikes.csv'
    spike.write_bytes(spike.read_bytes()+b'0.001,0\n')
    existing=set(data.glob('motor_bridge_*'))
    try:bridge.run(data,make_video=False)
    except ValueError as e:assert 'Не воспроизвелись спайки' in str(e)
    else:raise AssertionError('corrupt source accepted')
    assert set(data.glob('motor_bridge_*'))==existing
print('Two-flies motor bridge fixture passed')
