"""Искусственная сеть только для тестирования, не результат пользователя."""
import importlib.util
import json
import os
from pathlib import Path
import sys

import brian2 as b2
import pandas as pd

root = Path(__file__).resolve().parents[1]
tmp = Path(sys.argv[1])

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

mod = load('v630_control', root / 'experiments/templates/25_shiu_v630_control.py')
author = load('author', root / 'tests/fixtures/shiu-reference/model.py')
ids = sorted(set(mod.LEFT + mod.RIGHT + list(mod.MN9.values())), key=int)
index = {value: i for i, value in enumerate(ids)}
comp = tmp / 'authors.csv'; conn = tmp / 'authors.parquet'
pd.DataFrame({'Completed': [True]*len(ids)}, index=[int(v) for v in ids]).to_csv(comp)
# Несколько возбуждающих и тормозящих рёбер, с прямым входом в оба MN9.
rows = [(index[x], index[mod.MN9['left']], 30, 1) for x in mod.LEFT]
rows += [(index[x], index[mod.MN9['right']], 25, 1) for x in mod.LEFT]
rows += [(index[ids[0]], index[ids[-1]], 2, -1)]
df = pd.DataFrame([{'Presynaptic_ID': int(ids[i]), 'Postsynaptic_ID': int(ids[j]),
                    'Presynaptic_Index': i, 'Postsynaptic_Index': j, 'Connectivity': n,
                    'Excitatory': sign, 'Excitatory x Connectivity': sign*n}
                   for i,j,n,sign in rows])
df.to_parquet(conn, index=False)
# Разрешение искусственных файлов только внутри теста, в приложении ожидаются официальные SHA.
mod.EXPECTED = {'connections': mod.fingerprint(conn)['git_blob_sha1'], 'neurons': mod.fingerprint(comp)['git_blob_sha1']}
original = dict(mod.EXPECTED)

def run(*args):
    out = tmp / f'run-{len(list(tmp.glob("run-*")))}'; out.mkdir()
    os.environ.update(FLY_RUN_DIR=str(out), FLY_SHIU_CONNECTIONS=str(conn), FLY_SHIU_NEURONS=str(comp))
    sys.argv = ['control', *args]
    status = mod.main()
    return status, json.loads((out / 'summary.json').read_text(encoding='utf-8')), out

code, report, out = run()
assert code == 0 and report['status'] == 'preflight_complete'
assert report['data_check']['neurons'] == len(ids) and report['data_check']['connection_rows'] == len(rows)
assert not (out/'mn9_v630_trials.csv').exists()
code, report, out = run('--simulate', '--n-trials', '2', '--seed', '5')
assert code == 0 and report['status'] == 'ok' and len(report['result']['trials']) == 2
assert (out/'mn9_v630_trials.csv').exists() and (out/'report.txt').exists()
for n, trial in enumerate(report['result']['trials']):
    # Сверка ядра с неизменённым авторским model.py для обоих MN9 и каждого GRN.
    b2.start_scope(); b2.defaultclock.dt = 0.1*b2.ms; b2.prefs.codegen.target = 'numpy'
    params = dict(author.default_params); params['r_poi'] = 100*b2.Hz
    neu, syn, mon = author.create_model(comp, conn, params)
    stim = [index[rid] for rid in mod.LEFT]
    pois, neu = author.poi(neu, stim, [], params)
    net = b2.Network(neu, syn, mon, *pois)
    b2.seed(5+n); net.run(1000*b2.ms, namespace={})
    assert trial['left_mn9_rate_hz'] == int(mon.count[index[mod.MN9['left']]])
    assert trial['right_mn9_rate_hz'] == int(mon.count[index[mod.MN9['right']]])
    assert trial['stimulus_rates_hz'] == [int(mon.count[i]) for i in stim]
    del net, mon, pois, syn, neu
# Точное соответствие авторскому файлу обязательно, ошибок молча не скрываем.
mod.EXPECTED['connections'] = 'wrong'
code, report, _ = run('--simulate')
assert code == 1 and report['status'] == 'error' and 'не совпадают' in report['error']
mod.EXPECTED = original
# Повреждённые индексы выявляются до симуляции даже после изменения тестовой контрольной суммы.
df.loc[0, 'Presynaptic_Index'] = (int(df.loc[0, 'Presynaptic_Index'])+1) % len(ids)
df.to_parquet(conn, index=False)
mod.EXPECTED['connections'] = mod.fingerprint(conn)['git_blob_sha1']
code, report, _ = run()
assert code == 1 and report['status'] == 'error' and 'не соответствует' in report['error']
# Не подменять невыбранные данные синтетикой.
os.environ['FLY_SHIU_CONNECTIONS'] = ''
assert mod.main() == 1
print('ok')
