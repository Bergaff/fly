"""Preflight tests use generated baseline 51 and artificial trajectories only."""
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
base = load('old51', root / 'experiments/templates/51_two_flies_user_trajectory_learning.py')
pre = load('pre57', root / 'experiments/templates/57_user_wing_preflight.py')
examples = root / 'experiments/examples/wing-user-training'
train = [examples / 'train-a.json', examples / 'train-b.json']
test = examples / 'test-a.json'
source_bytes = {p: p.read_bytes() for p in train + [test]}

def rejected(fn, part):
    try:
        fn()
    except (ValueError, FileNotFoundError) as exc:
        assert part in str(exc), (part, str(exc))
    else:
        raise AssertionError('invalid input accepted')

with tempfile.TemporaryDirectory() as d:
    tmp = Path(d)
    folder = base.run(train, [test], tmp / 'runs')
    before = {p.relative_to(folder): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    fresh = tmp / 'fresh.json'
    obj = json.loads(test.read_text(encoding='utf-8'))
    obj['keyframes'][0]['angles_deg'][0] += 1
    fresh.write_text(json.dumps(obj), encoding='utf-8')
    snapshot = pre.prepare(folder, [fresh])
    assert [x['role'] for x in snapshot['labels']] == ['train', 'train', 'regression', 'new_test']
    assert set(snapshot['sources']) == {'baseline_metadata.json', 'baseline_manifest.json', 'baseline_model.npz',
                                        'train_001.json', 'train_002.json', 'test_001.json', 'test_002.json'}
    assert snapshot['sources']['test_002.json'] == fresh.read_bytes()
    assert snapshot['baseline_model_sha256'] == hashlib.sha256((folder/'model_six_axes.npz').read_bytes()).hexdigest()
    assert snapshot['source_sha256'] == {k: hashlib.sha256(v).hexdigest() for k, v in sorted(snapshot['sources'].items())}
    rejected(lambda: pre.prepare(folder, [test]), 'совпадает')
    rejected(lambda: pre.prepare(folder, [train[0]]), 'совпадает')
    rejected(lambda: pre.prepare(folder, [fresh, fresh]), 'совпадает')
    rejected(lambda: pre.prepare(folder, []), '1 до 19')
    # All integrity checks are read-only; restore only files within this temporary test.
    copied = folder / 'input/train_001.json'
    original = copied.read_bytes()
    copied.write_bytes(original + b' ')
    rejected(lambda: pre.prepare(folder, [fresh]), 'манифест')
    copied.write_bytes(original)
    mf = folder / 'input_manifest.json'
    original = mf.read_bytes()
    mf.write_bytes(original + b' ')
    rejected(lambda: pre.prepare(folder, [fresh]), 'манифест')
    mf.write_bytes(original)
    old_model = folder/'model_six_axes.npz'
    original = old_model.read_bytes()
    old_model.write_bytes(original + b'bad')
    rejected(lambda: pre.prepare(folder, [fresh]), 'SHA')
    old_model.write_bytes(original)
    (folder / 'INCOMPLETE.txt').write_text('incomplete')
    rejected(lambda: pre.prepare(folder, [fresh]), 'завершённая')
    (folder / 'INCOMPLETE.txt').unlink()
    assert {p.relative_to(folder): p.read_bytes() for p in folder.rglob('*') if p.is_file()} == before
assert all(p.read_bytes() == raw for p, raw in source_bytes.items())
print('Frozen input roles, baseline integrity, duplicate rejection and read-only behavior verified.')
