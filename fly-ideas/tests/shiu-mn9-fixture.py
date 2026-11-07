"""Небольшие искусственные данные ТОЛЬКО для автоматического теста, не анализ FlyWire."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import brian2 as b2
import numpy as np
import pandas as pd

root = Path(__file__).resolve().parents[1]
script = root / 'experiments/templates/23_shiu_mn9_adapted.py'
ref = root / 'tests/fixtures/shiu-reference/model.py'
tmp = Path(sys.argv[1])

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

mod = load('adapted', script)
author = load('author', ref)
# Искусственный граф содержит все IDs для тестирования ветвления; данные не реальные.
ids = sorted({mod.CANDIDATES.get(v, v) for v in mod.LEFT + mod.RIGHT + list(mod.MN9.values())}, key=int)
nt = {rid: 'ach' for rid in ids}
nt[ids[-1]] = 'da'
rows = [(rid, ids[(i+1) % len(ids)], 2) for i, rid in enumerate(ids)]
rows += [(mod.CANDIDATES.get(rid, rid), mod.MN9['left'], 25) for rid in mod.LEFT]
conn = tmp / 'connections.csv'
ntfile = tmp / 'neurons.csv'
pd.DataFrame(rows, columns=['pre_root_id','post_root_id','syn_count']).to_csv(conn, index=False)
pd.DataFrame(list(nt.items()), columns=['root_id', 'nt_type']).to_csv(ntfile, index=False)

def run(*args):
    runpath = tmp / f'run-{len(list(tmp.glob("run-*")))}'
    runpath.mkdir()
    env = dict(os.environ, FLY_RUN_DIR=str(runpath), FLY_CONNECTOME=str(conn), FLY_NEUROTRANSMITTERS=str(ntfile))
    proc = subprocess.run([sys.executable, str(script), *args], env=env, text=True, capture_output=True, timeout=45)
    return proc, json.loads((runpath / 'summary.json').read_text(encoding='utf8')), runpath

p, out, _ = run()
assert p.returncode == 0 and out['status'] == 'preflight_complete', (p.stderr, out)
assert out['candidate_mapping_required']
for original, candidate in mod.CANDIDATES.items():
    assert out['reference_id_check'][original]['selected_if_accepted'] == candidate
    assert out['reference_id_check'][original]['status'] == 'candidate_present_unverified'
assert out['data_check']['excluded_rows'] > 0
p, out, _ = run('--simulate')
assert p.returncode == 1 and out['status'] == 'blocked' and 'accept-candidate-map' in out['blockers'][0]
p, out, _ = run('--simulate', '--accept-candidate-map')
assert p.returncode == 1 and out['status'] == 'blocked' and 'accept-exclusions' in out['blockers'][0]
p, out, runpath = run('--simulate', '--accept-candidate-map', '--accept-exclusions', '--n-trials', '2', '--seed', '7')
assert p.returncode == 0 and out['status'] == 'ok', (p.stdout, p.stderr, out)
assert len(out['result']['trials']) == 2 and (runpath / 'mn9_trials.csv').exists()
assert out['result']['trials'][0]['left_mn9_rate_hz'] > 0
# Проверяем повторяемость seed и сравниваем с неизменённым авторским ядром.
scan = mod.scan_connections(conn, nt)
_, mapping = mod.resolve_ids(scan, nt)
args = SimpleNamespace(side='left', frequency_hz=100.0, n_trials=1, seed=7)
ours = mod.run_simulation(conn, scan, nt, mapping, args, tmp)
index = {rid: i for i, rid in enumerate(ids)}
author_edges = [(index[pre], index[post], n * mod.type_sign(nt[pre])) for pre, post, n in rows if mod.type_sign(nt[pre])]
comp = tmp / 'comp.csv'
pd.DataFrame({'Completed': [True]*len(ids)}, index=[int(rid) for rid in ids]).to_csv(comp)
author_frame = pd.DataFrame(author_edges, columns=['Presynaptic_Index','Postsynaptic_Index','Excitatory x Connectivity'])
old_read = author.pd.read_parquet
author.pd.read_parquet = lambda _: author_frame
try:
    b2.start_scope(); b2.defaultclock.dt = 0.1 * b2.ms; b2.prefs.codegen.target = 'numpy'
    params = dict(author.default_params); params['r_poi'] = 100 * b2.Hz
    neu, syn, monitor = author.create_model(comp, 'not-used.parquet', params)
    targets = [index[mapping[rid]] for rid in mod.LEFT]
    pois, neu = author.poi(neu, targets, [], params)
    net = b2.Network(neu, syn, monitor, *pois)
    b2.seed(7); net.run(1000*b2.ms, namespace={})
    assert int(monitor.count[index[mapping[mod.MN9['left']]]]) == ours['trials'][0]['left_mn9_rate_hz']
    assert int(monitor.count[index[mapping[mod.MN9['right']]]]) == ours['trials'][0]['right_mn9_rate_hz']
    assert out['result']['trials'][0]['left_mn9_rate_hz'] == ours['trials'][0]['left_mn9_rate_hz']
finally:
    author.pd.read_parquet = old_read

# Наличие старого и предполагаемого нового ID одновременно нельзя разрешать молча.
old = next(iter(mod.CANDIDATES))
pd.DataFrame(rows + [(old, ids[0], 1)], columns=['pre_root_id','post_root_id','syn_count']).to_csv(conn, index=False)
pd.DataFrame(list(nt.items()) + [(old, 'ach')], columns=['root_id', 'nt_type']).to_csv(ntfile, index=False)
p, blocked, _ = run('--simulate', '--accept-candidate-map', '--accept-exclusions')
assert p.returncode == 1 and blocked['status'] == 'blocked'
assert blocked['reference_id_check'][old]['status'] == 'ambiguous_both_present'
# Неполные входы не подменяются синтетикой.
ntfile.unlink()
p, out, _ = run()
assert p.returncode == 1 and out['status'] == 'error' and 'FLY_NEUROTRANSMITTERS' in out['error']
print('ok')
