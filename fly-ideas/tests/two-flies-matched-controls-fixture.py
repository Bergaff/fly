"""Checks visual invariants, event records, real execution and source preservation."""
import csv
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

root=Path(__file__).resolve().parents[1]
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,root/'experiments/templates'/file)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def read(file):
    with file.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def hashes(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()}
source=load('source41','41_two_flies_visual_controls.py')
control=load('controls43','43_two_flies_matched_controls.py')

# Test frame-by-frame invariants independently on nontrivial synthetic RGB.
rng=np.random.default_rng(345);frames=rng.integers(0,256,(8,2,12,16,3),dtype=np.uint8)
for tilewise in (True,False):
    transformed=control.scramble(frames,tilewise)
    assert np.array_equal(transformed,control.scramble(frames,tilewise))
    assert np.all(control.rgb_hist_matches(frames,transformed))
    assert np.array_equal(control.motion_sums(frames),control.motion_sums(transformed))
    assert not np.array_equal(frames,transformed)
    if tilewise:
        for r in range(4):
            for c in range(4):
                assert np.array_equal(control.motion_sums(frames[:,:,r*3:(r+1)*3,c*4:(c+1)*4]),control.motion_sums(transformed[:,:,r*3:(r+1)*3,c*4:(c+1)*4]))
with tempfile.TemporaryDirectory() as temp:
    original=source.run(temp,2,50,0,48,32);before=hashes(original)
    out=control.run(original,make_gif=True)
    m=json.loads((out/'metadata.json').read_text(encoding='utf8'))
    assert m['status']=='completed' and m['feature_max_abs_difference_tile_scramble']<=1e-6
    assert all(hashlib.sha256((original/f).read_bytes()).hexdigest()==digest for f,digest in before.items())
    sums={r['condition']:r for r in read(out/'conditions_summary.csv')}
    assert set(sums)=={'wings','stationary','reverse','tile_scramble','global_scramble','object_unmatched'}
    assert sums['wings']['spikes']==sums['tile_scramble']['spikes']
    assert (out/'wings/spikes.csv').read_bytes()==(out/'tile_scramble/spikes.csv').read_bytes()
    neurons=read(out/'neuron_comparison.csv');assert len(neurons)==6*32
    with np.load(original/'wing_3hz_0deg/vision.npz') as f:original_frames=f['neural_input'].copy()
    for name,row in sums.items():
        sub=out/name;events=read(sub/'spikes.csv');visual=read(sub/'visual_input.csv');compare=[n for n in neurons if n['condition']==name]
        assert len(events)==int(row['spikes']) and len(visual)==100*32
        for n in compare: assert int(n['spikes'])==sum(int(x['neuron_id'])==int(n['neuron_id']) for x in events)
        with np.load(sub/'neural_input.npz') as f:
            if name=='reverse':assert np.array_equal(f['neural_input'],original_frames[::-1]) and np.array_equal(f['source_frame'],np.arange(99,-1,-1))
            if name=='tile_scramble':assert np.array_equal(f['neural_input'],control.scramble(original_frames,True))
        with Image.open(sub/'observer_input.gif') as im:
            total=0
            for k in range(im.n_frames):im.seek(k);total+=im.info.get('duration',0)
            assert total==2000
    metrics=read(out/'image_matching.csv');assert len(metrics)==6*100*2
    for row in metrics:
        if row['condition'] in ('wings','reverse','tile_scramble','global_scramble'):
            assert row['same_rgb_histogram']=='1'
            assert row['abs_luminance_diff_sum_x3']==row['wings_abs_luminance_diff_sum_x3']
    # Damaged source must fail before allocating an output directory.
    f=original/'wing_3hz_0deg/spikes.csv';f.write_bytes(f.read_bytes()+b'0.001,0\n')
    previous=set(original.glob('matched_controls_*'))
    try:control.run(original,False)
    except ValueError as e:assert 'Не воспроизвелись спайки' in str(e)
    else:raise AssertionError('Corrupt input accepted')
    assert set(original.glob('matched_controls_*'))==previous
print('Matched visual controls fixture passed')
