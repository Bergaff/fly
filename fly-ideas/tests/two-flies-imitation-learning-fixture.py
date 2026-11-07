import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

root = Path(__file__).resolve().parents[1]
script = root / 'experiments/templates/47_two_flies_imitation_learning.py'
spec = importlib.util.spec_from_file_location('imitation', script)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def csvrows(path):
    with path.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))


train, test = m.plan()
assert len(train) == 36 and len(test) == 8
assert set(train).isdisjoint(test)
for idx in range(3): assert {s[idx] for s in train}.isdisjoint({s[idx] for s in test})
# A causal feature window cannot depend on future frames.
images = np.zeros((10, 2, m.HEIGHT, m.WIDTH, 3), dtype=np.uint8)
first = m.history(images)
images[8:] = 255
second = m.history(images)
assert np.array_equal(first[:6], second[:6])
assert np.any(first[6:] != second[6:])
# Fit must actually learn from labels, with normalisation computed from X only.
rng = np.random.default_rng(81)
x = rng.normal(size=(100, 8)); y = np.clip(.2*x[:,0] - .1*x[:,1], -.65, .65)
mean, scale, intercept, weights, init = m.fit(x, y)
assert np.allclose(mean, x.mean(axis=0))
assert np.linalg.norm(weights) > 0 and not np.array_equal(weights, init)
assert np.mean(((x-mean)/scale @ weights + intercept-y)**2) < np.mean(y*y)

with tempfile.TemporaryDirectory() as tmp:
    original_hash = hashlib.sha256((root/'experiments/templates/38_two_flies_observation.py').read_bytes()).hexdigest()
    out = m.run(tmp)
    meta = json.loads((out/'metadata.json').read_text(encoding='utf8'))
    assert meta['status'] == 'completed' and meta['mode'] == 'full_pilot'
    assert meta['train_sequences'] == 36 and meta['test_sequences'] == 8
    assert meta['train_samples'] == 36*48 and meta['test_samples'] == 8*48
    assert meta['engine_sha256'] == original_hash == m.ENGINE_HASH
    assert not (out/'INCOMPLETE.txt').exists()
    rows, summary, split = [csvrows(out/f) for f in ('test_predictions.csv','test_metrics.csv','split.csv')]
    assert len(rows) == 384 and len(summary) == 40 and len(split) == 44
    with np.load(out/'visual_sequences.npz', allow_pickle=False) as data, np.load(out/'model.npz', allow_pickle=False) as model:
        assert data['images'].shape == (44, 50, 2, 32, 48, 3)
        assert data['teacher_angle'].shape == (44, 50)
        seq = int(rows[0]['sequence_id']); assert split[seq]['split'] == 'test'
        pred = m.predict(data['images'][seq], model['mean'], model['scale'], float(model['intercept']), model['weights'])
        target = data['teacher_angle'][seq, m.HISTORY-1:]
        assert np.allclose(pred, [float(r['trained_angle_rad']) for r in rows[:48]])
        assert np.allclose(target, [float(r['teacher_angle_rad']) for r in rows[:48]])
    for name, field in [('trained','trained_angle_rad'), ('untrained','untrained_angle_rad'), ('constant_zero','zero_angle_rad'), ('occluded','occluded_angle_rad'), ('shuffled','shuffled_angle_rad')]:
        rmse = math.sqrt(sum((float(r[field]) - float(r['teacher_angle_rad']))**2 for r in rows)/len(rows))
        assert abs(rmse - meta['scores'][name]['rmse_rad']) < 1e-12
    assert (out/'comparison.gif').is_file() and (out/'comparison.png').is_file()
    assert 'обучение' in (out/'ИТОГ.txt').read_text(encoding='utf-8-sig').lower()
    # CLI creates a separate explicitly marked smoke result and does not touch the first run.
    before = hashlib.sha256((out/'metadata.json').read_bytes()).hexdigest()
    run = subprocess.run([sys.executable, str(script), '--output', tmp, '--smoke'], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr
    folders = [p for p in Path(tmp).iterdir() if p.is_dir()]; assert len(folders) == 2
    smoke = next(p for p in folders if p != out)
    assert json.loads((smoke/'metadata.json').read_text(encoding='utf8'))['mode'] == 'smoke'
    assert before == hashlib.sha256((out/'metadata.json').read_bytes()).hexdigest()
print('imitation learning fixture: OK')
