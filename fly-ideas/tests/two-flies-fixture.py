"""Light end-to-end checks, using the separate two-flies environment."""
import csv
import importlib.util
import json
import tempfile
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('two_flies', root / 'experiments/templates/38_two_flies_observation.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

with tempfile.TemporaryDirectory() as tmp:
    first = m.run(tmp, .4, 20, 42, 48, 32)
    second = m.run(tmp, .4, 20, 42, 48, 32)
    assert first != second
    assert json.loads((first / 'metadata.json').read_text())['status'] == 'completed'
    for cond in m.CONDITIONS:
        a = np.load(first / cond / 'vision.npz')
        b = np.load(second / cond / 'vision.npz')
        assert a['scene_eyes'].shape == (8, 2, 32, 48, 3)
        for key in a.files:
            assert np.array_equal(a[key], b[key]), (cond, key)
        assert (first / cond / 'spikes.csv').read_bytes() == (second / cond / 'spikes.csv').read_bytes()
        rows = list(csv.DictReader((first / cond / 'visual_input.csv').open(encoding='utf-8')))
        motion = m.features(a['neural_input'])
        assert len(rows) == 8 * 32
        assert np.allclose([float(r['motion_abs_diff']) for r in rows], motion.ravel())
        assert float(rows[0]['time_s']) == 0
        assert (first / cond / 'scene.gif').stat().st_size > 0
    moving = np.load(first / 'moving/vision.npz')
    static = np.load(first / 'stationary/vision.npz')
    occluded = np.load(first / 'occluded/vision.npz')
    shuffled = np.load(first / 'shuffled/vision.npz')
    assert np.array_equal(moving['scene_eyes'], occluded['scene_eyes'])
    assert np.array_equal(moving['scene_eyes'], shuffled['scene_eyes'])
    assert np.all(occluded['neural_input'] == 128)
    assert np.array_equal(shuffled['neural_input'], moving['scene_eyes'][shuffled['input_source_frame']])
    assert np.array_equal(static['scene_eyes'][0], static['scene_eyes'][1])
    assert m.features(moving['neural_input']).sum() > 0
    assert m.features(static['neural_input']).sum() == 0
    assert (first / 'stationary/spikes.csv').read_bytes() == (first / 'occluded/spikes.csv').read_bytes()
    assert (first / 'moving/spikes.csv').read_bytes() != (first / 'stationary/spikes.csv').read_bytes()
    assert 'time_s,neuron_id' in (first / 'moving/spikes.csv').read_text()
    assert all(0 <= float(r['time_s']) < .4 and 0 <= int(r['neuron_id']) < 32
               for r in csv.DictReader((first / 'moving/spikes.csv').open()))
    try:
        m.run(tmp, .41, 20, 42)
    except ValueError:
        pass
    else:
        raise AssertionError('fractional frame duration accepted')
print('Two-flies fixture passed')
