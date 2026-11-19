"""Small real render and LIF run: controls, accounting, provenance, isolation."""
import csv
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('visual_controls', root / 'experiments/templates/41_two_flies_visual_controls.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()}

with tempfile.TemporaryDirectory() as tmp:
    original = Path(tmp) / 'previous_user_run'
    original.mkdir()
    (original / 'important.csv').write_text('user,data\n1,2\n')
    before = hashes(original)
    out = m.run(tmp, duration=.4, fps=20, seed=42, width=48, height=32)
    original_summary = (out / 'neuron_comparison.csv').read_bytes()
    meta = json.loads((out / 'metadata.json').read_text(encoding='utf-8'))
    assert meta['status'] == 'completed' and meta['engine_sha256'] == m.EXPECTED
    assert len(meta['conditions']) == 7
    assert len(rows(out / 'conditions_summary.csv')) == 5
    comparison = rows(out / 'neuron_comparison.csv')
    phase = rows(out / 'phase_bins.csv')
    assert len(comparison) == 5 * 32 and len(phase) == 5 * 32 * 8
    for condition in m.CONDITIONS:
        p = out / condition['name']
        with np.load(p / 'vision.npz', allow_pickle=False) as data:
            images = data['neural_input'].copy()
            assert images.shape == (8, 2, 32, 48, 3)
            assert np.array_equal(images, data['scene_eyes'])
            assert np.array_equal(data['input_source_frame'], np.arange(8))
        visual = rows(p / 'visual_input.csv')
        computed = m.load_engine().features(images)
        assert np.allclose(np.array([float(r['motion_abs_diff']) for r in visual]).reshape(8, 32), computed)
        scene = rows(p / 'scene.csv')
        sp = rows(p / 'spikes.csv')
        assert len(scene) == 8 and all(0 <= float(r['time_s']) < .4 and 0 <= int(r['neuron_id']) < 32 for r in sp)
        if condition['kind'].endswith('_static'):
            assert not np.any(computed)
        elif condition['kind'] == 'object':
            assert np.any(computed) and all(float(r['left_wing_rad']) == 0 and r['object_present'] == '1' for r in scene)
        else:
            assert np.any(computed) and all(r['object_present'] == '0' for r in scene)
        for r in comparison:
            if r['condition'] == condition['name']:
                nid = int(r['neuron_id'])
                assert int(r['spikes']) == sum(int(x['neuron_id']) == nid for x in sp)
                b = [x for x in phase if x['condition'] == condition['name'] and int(x['neuron_id']) == nid]
                assert sum(int(x['spikes']) for x in b) == int(r['spikes'])
                assert sum(int(x['control_spikes']) for x in b) == int(r['control_spikes'])
                assert abs(sum(float(x['exposure_s']) for x in b) - .4) < 1e-10
    with np.load(out / 'object_stationary/vision.npz') as obj, np.load(out / 'object_3hz_0deg/vision.npz') as mov, np.load(out / 'wing_stationary/vision.npz') as no_obj:
        assert np.array_equal(obj['neural_input'][0], mov['neural_input'][0])
        assert not np.array_equal(obj['neural_input'][0], no_obj['neural_input'][0])
        assert not np.array_equal(mov['neural_input'][0], mov['neural_input'][1])
    scene_90 = rows(out / 'wing_3hz_90deg/scene.csv')
    assert abs(float(scene_90[0]['left_wing_rad']) - .65) < 1e-10
    next_out = m.run(tmp, duration=.4, fps=20, seed=42, width=48, height=32)
    assert out != next_out and original_summary == (next_out / 'neuron_comparison.csv').read_bytes()
    assert hashes(original) == before and (out / 'neuron_comparison.csv').read_bytes() == original_summary
    before_dirs = sorted(Path(tmp).iterdir())
    try:
        m.run(tmp, duration=.41, fps=20)
    except ValueError:
        pass
    else:
        raise AssertionError('Invalid duration accepted')
    assert sorted(Path(tmp).iterdir()) == before_dirs
print('Visual control fixture passed')
