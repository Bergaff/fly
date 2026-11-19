"""Проверка и пробный контроль sugar GRN -> MN9 на авторских данных Shiu v630.

Без аргументов выполняется только проверка файлов; --simulate запускает один
или несколько пробных повторов. Никакой Princeton CSV не загружается.
Это контроль модели, не лезия и не доказанное воспроизведение Figure 1.
"""
# Portions adapted from Drosophila_brain_model/model.py (MIT License).
# Copyright (c) 2023 Philip Shiu and Nico Spiller
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import argparse
import csv
import gc
import hashlib
import json
import math
import os
import statistics
import sys
import time
import traceback
from pathlib import Path

SOURCE = 'https://github.com/philshiu/Drosophila_brain_model/tree/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960'
# Git blob SHA-1 закреплённого коммита, не произвольный файл с таким же именем.
EXPECTED = {'connections': '8b4d9531bc0acbda7c2074ae577e6ac9e2fca166',
            'neurons': 'be745f0ce054308df21accc5c4b3883aa38498f9'}
LEFT = ['720575940620589838','720575940631147148','720575940608305161','720575940629388135','720575940630968335','720575940606801282','720575940617398502','720575940616167218','720575940620296641','720575940627961104']
RIGHT = ['720575940624963786','720575940630233916','720575940637568838','720575940638202345','720575940617000768','720575940630797113','720575940632889389','720575940621754367','720575940621502051','720575940640649691','720575940639332736','720575940616885538','720575940639198653','720575940620900446','720575940617937543','720575940632425919','720575940633143833','720575940612670570','720575940628853239','720575940629176663','720575940611875570']
MN9 = {'left': '720575940660219265', 'right': '720575940645521262'}
COLUMNS = ['Presynaptic_ID', 'Postsynaptic_ID', 'Presynaptic_Index', 'Postsynaptic_Index', 'Connectivity', 'Excitatory', 'Excitatory x Connectivity']


def args_parse():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--simulate', action='store_true', help='После проверки выполнить пробный контроль без лезий')
    p.add_argument('--side', choices=['left', 'right'], default='left')
    p.add_argument('--frequency-hz', type=float, default=100.0)
    p.add_argument('--n-trials', type=int, default=1, help='Пробные повторы, от 1 до 5')
    p.add_argument('--seed', type=int, default=0)
    return p.parse_args()


def input_file(env, extension):
    name = os.environ.get(env, '').strip()
    if not name:
        raise ValueError(f'{env} не выбран в «Данные и окружение».')
    path = Path(name)
    if not path.is_file() or not path.name.lower().endswith(extension):
        raise ValueError(f'{env}: нужен доступный файл {extension}: {path}')
    return path


def fingerprint(path):
    before = path.stat()
    sha = hashlib.sha256()
    git = hashlib.sha1(f'blob {before.st_size}\0'.encode())
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(2 * 1024 * 1024), b''):
            sha.update(chunk); git.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f'Файл изменился во время чтения: {path}')
    return {'path': str(path), 'bytes': before.st_size, 'mtime_ns': before.st_mtime_ns,
            'sha256': sha.hexdigest(), 'git_blob_sha1': git.hexdigest()}


def validate_inputs(conn, neurons, store_arrays):
    """Полная проверка индексов и весов по частям; ID только int64, без float."""
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq
    frame = pd.read_csv(neurons, usecols=[0], dtype='string', encoding='utf-8-sig')
    ids = frame.iloc[:, 0].str.strip()
    if ids.empty or ids.isna().any() or not ids.str.fullmatch(r'[1-9][0-9]*').all() or ids.duplicated().any():
        raise ValueError('Авторский список должен содержать уникальные положительные ID в первом столбце.')
    try:
        id_list = [str(v) for v in ids.tolist()]
        numbers = np.asarray([int(v) for v in id_list], dtype=np.int64)
    except (OverflowError, ValueError) as exc:
        raise ValueError('ID авторского списка должны помещаться в int64.') from exc
    lookup = {v: i for i, v in enumerate(id_list)}
    missing = [x for x in LEFT + RIGHT + list(MN9.values()) if x not in lookup]
    if missing:
        raise ValueError('Авторские ID GRN или MN9 отсутствуют в списке: ' + ', '.join(missing))
    table = pq.ParquetFile(conn)
    schema = table.schema_arrow
    if any(name not in schema.names or not pa.types.is_integer(schema.field(name).type) for name in COLUMNS):
        raise ValueError('Авторский Parquet не содержит требуемые целочисленные столбцы ID, индексов и весов.')
    count = table.metadata.num_rows
    if count == 0 or len(numbers) > np.iinfo(np.int32).max:
        raise ValueError('Авторская таблица пуста или содержит слишком много нейронов.')
    if store_arrays:
        pre = np.empty(count, dtype=np.int32); post = np.empty(count, dtype=np.int32); weights = np.empty(count, dtype=np.int32)
    else:
        pre = post = weights = None
    checked = 0
    for batch in table.iter_batches(batch_size=500_000, columns=COLUMNS):
        if any(col.null_count for col in batch.columns):
            raise ValueError('В авторских связях обнаружены пропущенные значения.')
        cols = {name: batch.column(name).to_numpy(zero_copy_only=False) for name in COLUMNS}
        i, j = cols['Presynaptic_Index'], cols['Postsynaptic_Index']
        n, sign, w = cols['Connectivity'], cols['Excitatory'], cols['Excitatory x Connectivity']
        if (np.any(i < 0) or np.any(j < 0) or np.any(i >= len(numbers)) or np.any(j >= len(numbers))
            or np.any(cols['Presynaptic_ID'] != numbers[i]) or np.any(cols['Postsynaptic_ID'] != numbers[j])
            or np.any(n <= 0) or np.any(n > np.iinfo(np.int32).max)
            or np.any((sign != 1) & (sign != -1)) or np.any(w != sign * n)):
            raise ValueError('Авторский Parquet не соответствует индексам списка или имеет некорректные веса.')
        if store_arrays:
            end = checked + batch.num_rows
            pre[checked:end] = i; post[checked:end] = j; weights[checked:end] = w
        checked += batch.num_rows
    if checked != count:
        raise ValueError('Не удалось проверить все строки связей.')
    return {'ids': id_list, 'lookup': lookup, 'rows': count, 'pre': pre, 'post': post, 'weights': weights}


def simulate_one(data, side, frequency_hz, seed):
    """Уравнения и веса по model.py авторов; хранит только число спайков, не их времена."""
    import brian2 as b2
    b2.start_scope()
    b2.prefs.codegen.target = 'numpy'
    b2.defaultclock.dt = 0.1 * b2.ms
    params = {'v_0': -52*b2.mV, 'v_rst': -52*b2.mV, 'v_th': -45*b2.mV,
              't_mbr': 20*b2.ms, 'tau': 5*b2.ms, 't_rfc': 2.2*b2.ms}
    eqs = 'dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)\ndg/dt = -g / tau : volt (unless refractory)\nrfc : second'
    neu = b2.NeuronGroup(len(data['ids']), eqs, method='linear', threshold='v > v_th',
                          reset='v = v_rst; g = 0*mV', refractory='rfc', namespace=params)
    neu.v = params['v_0']; neu.g = 0; neu.rfc = params['t_rfc']
    syn = b2.Synapses(neu, neu, 'w : volt', on_pre='g += w', delay=1.8*b2.ms)
    syn.connect(i=data['pre'], j=data['post'])
    syn.w = data['weights'] * 0.275*b2.mV
    ids = LEFT if side == 'left' else RIGHT
    targets = [data['lookup'][v] for v in ids]
    pois = []
    for index in targets:
        neu[index].rfc = 0*b2.ms
        pois.append(b2.PoissonInput(neu[index], 'v', N=1, rate=frequency_hz*b2.Hz, weight=0.275*250*b2.mV))
    monitor = b2.SpikeMonitor(neu, record=False)
    network = b2.Network(neu, syn, monitor, *pois)
    b2.seed(seed)
    start = time.time()
    network.run(1000*b2.ms, namespace={})
    seconds = time.time() - start
    # count records every neuron, but only MN9 and stimulation counts leave this function.
    result = {'seed': seed, 'left_mn9_rate_hz': int(monitor.count[data['lookup'][MN9['left']]]),
              'right_mn9_rate_hz': int(monitor.count[data['lookup'][MN9['right']]]),
              'stimulus_rates_hz': [int(monitor.count[i]) for i in targets], 'wall_seconds': round(seconds, 3)}
    del network, monitor, pois, syn, neu
    gc.collect()
    return result


def main():
    args = args_parse()
    run = os.environ.get('FLY_RUN_DIR', '').strip()
    if not run:
        print('FLY_RUN_DIR не задан. Запустите из приложения.', file=sys.stderr)
        return 2
    output = Path(run); output.mkdir(parents=True, exist_ok=True)
    report = {'status': 'pending', 'mode': 'simulation' if args.simulate else 'preflight', 'args': vars(args),
              'scope': 'Пробный контроль на исходных авторских файлах v630; без лезий, не верифицированная Figure 1.',
              'author_source': SOURCE, 'files': [], 'caveats': [
                  'Никакие кандидатные ID не применяются. Используются исходные ID в авторском списке.',
                  'По умолчанию активируются 10 левых sugar GRN из авторского ноутбука; в опубликованном тексте и ноутбуке есть различие по стороне протокола. Не выдавать пробу за готовую панель статьи.',
                  'Односекундные повторы с указанными seed не являются биологическими повторностями. Оригинальный код сохраняет время всех спайков, здесь сохраняются только числа MN9 и стимулированных GRN.',
                  'Это отдельная реализация уравнений model.py. В сбросе опущено локальное присваивание w=0 из оригинала; на малой искусственной сети спайки MN9 и стимуляции совпали с авторским ядром. Полная эквивалентность не доказана.',
                  'Сравнение с адаптацией Princeton не доказывает идентичности нейронов или эквивалентности протоколов; требуется отдельный анализ.']}
    try:
        if not 1 <= args.n_trials <= 5 or not 0 <= args.seed <= 2**32 - args.n_trials or not math.isfinite(args.frequency_hz) or not 0 < args.frequency_hz <= 200:
            raise ValueError('Допустимы 1–5 повторов, частота (0, 200] Гц и корректный seed.')
        conn = input_file('FLY_SHIU_CONNECTIONS', '.parquet')
        neurons = input_file('FLY_SHIU_NEURONS', '.csv')
        print('Проверяем контрольные суммы авторских файлов...', flush=True)
        hashes = {'connections': fingerprint(conn), 'neurons': fingerprint(neurons)}
        report['inputs'] = hashes
        report['author_git_blob_matches_reference'] = {key: hashes[key]['git_blob_sha1'] == expected for key, expected in EXPECTED.items()}
        if not all(report['author_git_blob_matches_reference'].values()):
            raise ValueError('Авторские файлы не совпадают с закреплёнными файлами v630. Скачайте оригиналы по ссылкам в программе.')
        print('Проверяем индексы, ID и веса авторских связей...', flush=True)
        data = validate_inputs(conn, neurons, args.simulate)
        for key, file in [('connections', conn), ('neurons', neurons)]:
            st = file.stat()
            if (st.st_size, st.st_mtime_ns) != (hashes[key]['bytes'], hashes[key]['mtime_ns']):
                raise ValueError(f'Авторский файл изменился при проверке: {file}')
        report['data_check'] = {'neurons': len(data['ids']), 'connection_rows': data['rows'],
                                'stimulation_ids': LEFT if args.side == 'left' else RIGHT, 'mn9_ids': MN9}
        if args.simulate:
            import brian2 as b2
            trials = []
            for n in range(args.n_trials):
                print(f'Запускаем контроль v630: повтор {n+1}/{args.n_trials}, 1 секунда модельного времени...', flush=True)
                result = simulate_one(data, args.side, args.frequency_hz, args.seed + n)
                result['trial'] = n + 1
                trials.append(result)
            with (output / 'mn9_v630_trials.csv').open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=['trial', 'seed', 'left_mn9_rate_hz', 'right_mn9_rate_hz', 'wall_seconds'])
                writer.writeheader()
                writer.writerows({key: value for key, value in row.items() if key != 'stimulus_rates_hz'} for row in trials)
            report['status'] = 'ok'
            left_rates = [row['left_mn9_rate_hz'] for row in trials]
            right_rates = [row['right_mn9_rate_hz'] for row in trials]
            report['result'] = {'trials': trials, 'duration_ms': 1000, 'dt_ms': 0.1, 'brian2': b2.__version__,
                                'left_mean_hz': statistics.mean(left_rates), 'right_mean_hz': statistics.mean(right_rates),
                                'left_sd_hz': statistics.stdev(left_rates) if len(left_rates) > 1 else None,
                                'right_sd_hz': statistics.stdev(right_rates) if len(right_rates) > 1 else None,
                                'backend': 'numpy', 'weight_mV_per_synapse': 0.275, 'delay_ms': 1.8}
            report['files'] = ['mn9_v630_trials.csv', 'report.txt']
            lines = ['Пробный контроль на авторской связности Shiu v630',
                     f'Сторона сахарных GRN: {args.side}; заданная частота: {args.frequency_hz} Гц.',
                     'Исходные ID, без замен и без лезий.', '']
            for row in trials:
                lines.append(f"Повтор {row['trial']}, seed {row['seed']}: MN9 слева {row['left_mn9_rate_hz']} Гц, справа {row['right_mn9_rate_hz']} Гц; время {row['wall_seconds']} с.")
            lines += ['', 'Пробные повторы не являются верифицированной панелью статьи. Подробности и фактические частоты стимулированных GRN в summary.json.']
            (output / 'report.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        else:
            report['status'] = 'preflight_complete'
        code = 0
    except Exception as exc:
        report['status'] = 'error'; report['error'] = f'{type(exc).__name__}: {exc}'
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        code = 1
    with (output / 'summary.json').open('w', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f'Контроль v630: {report["status"]}. Отчёт: {output / "summary.json"}', flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
