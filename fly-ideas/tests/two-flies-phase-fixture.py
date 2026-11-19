"""Reproducibility, audit files, phase arithmetic, and input safety."""
import csv
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

phase = load('phase', root / 'experiments/templates/40_two_flies_phase_analysis.py')
base = phase.load_engine()
counts, strength, direction, bins = phase.phase_stats(np.array([0., .25, .5, .75]), np.array([0, 0, 0, 0]), 1.)
assert counts[0] == 4 and strength[0] < 1e-12 and np.isnan(direction[0])
assert bins[0].tolist() == [1, 0, 1, 0, 1, 0, 1, 0]
counts, strength, direction, _ = phase.phase_stats(np.array([0., 1.]), np.array([0, 0]), 1.)
assert abs(strength[0] - 1) < 1e-12 and np.isclose(direction[0] % (2 * np.pi), 0, atol=1e-12)

with tempfile.TemporaryDirectory() as tmp:
    run = base.run(tmp, .4, 20, 42, 48, 32)
    inputs = [p for p in run.rglob('*') if p.is_file()]
    before = {str(p.relative_to(run)): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    out1 = phase.analyse(run, n=3, random_seed=5)
    out2 = phase.analyse(run, n=3, random_seed=5)
    assert out1 != out2
    for p in inputs:
        assert hashlib.sha256(p.read_bytes()).hexdigest() == before[str(p.relative_to(run))]
    assert json.loads((out1 / 'analysis_metadata.json').read_text())['status'] == 'completed'
    for name in ['neuron_summary.csv', 'phase_bins.csv', 'shuffle_neurons.csv', 'shuffle_permutations.csv', 'shuffle_spikes.csv']:
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes(), name
    def rows(path):
        with path.open(encoding='utf-8-sig', newline='') as f:
            return list(csv.DictReader(f))
    summary = rows(out1 / 'neuron_summary.csv')
    details = rows(out1 / 'shuffle_neurons.csv')
    permutations = rows(out1 / 'shuffle_permutations.csv')
    events = rows(out1 / 'shuffle_spikes.csv')
    binrows = rows(out1 / 'phase_bins.csv')
    assert len(summary) == 32 and len(details) == 3 * 32 and len(permutations) == 3 * 8
    for j in range(1, 4):
        assert sorted(int(r['source_frame']) for r in permutations if int(r['trial']) == j) == list(range(8))
        for i in range(32):
            assert int(details[(j - 1) * 32 + i]['spikes']) == sum(int(r['trial']) == j and int(r['neuron_id']) == i for r in events)
    for condition in ('moving', 'stationary', 'occluded'):
        for i in range(32):
            selected = [r for r in binrows if r['condition'] == condition and int(r['neuron_id']) == i]
            assert sum(int(r['spikes']) for r in selected) == int(summary[i][condition + '_spikes'])
            assert abs(sum(float(r['exposure_s']) for r in selected) - .4) < 1e-12
    spike = run / 'moving/spikes.csv'
    spike.write_bytes(spike.read_bytes() + b'0.001,0\n')
    number_before = len(list(run.glob('phase_analysis_*')))
    try:
        phase.analyse(run, n=2)
    except ValueError as e:
        assert 'не воспроизвелись полностью' in str(e)
    else:
        raise AssertionError('altered moving spike list accepted')
    assert len(list(run.glob('phase_analysis_*'))) == number_before
print('Two-flies phase fixture passed')
