"""Поэтапный адаптированный тест sugar GRN -> MN9 на подключённых CSV.

По умолчанию только проверяет входы. Для отдельного пробного расчёта нужны
--simulate --accept-candidate-map --accept-exclusions (см. отчёт и README).
Это НЕ точное воспроизведение статьи и НЕ подготовка авторского коннектома.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE = 'https://github.com/philshiu/Drosophila_brain_model/blob/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960/'
MAPPING_SOURCE = 'https://github.com/arniByte/flyswamp/blob/53fb1f5d500d710d6a5580be64ec1351f770bf37/validation/reference/shiu_neuron_sets_783.json'
RIGHT = ['720575940624963786','720575940630233916','720575940637568838','720575940638202345','720575940617000768','720575940630797113','720575940632889389','720575940621754367','720575940621502051','720575940640649691','720575940639332736','720575940616885538','720575940639198653','720575940620900446','720575940617937543','720575940632425919','720575940633143833','720575940612670570','720575940628853239','720575940629176663','720575940611875570']
LEFT = ['720575940620589838','720575940631147148','720575940608305161','720575940629388135','720575940630968335','720575940606801282','720575940617398502','720575940616167218','720575940620296641','720575940627961104']
MN9 = {'left': '720575940660219265', 'right': '720575940645521262'}
# Не авторская таблица: гипотезы на основе схожести связей, требующие проверки.
CANDIDATES = {'720575940620900446': '720575940639259967', '720575940627961104': '720575940630882039', '720575940645521262': '720575940618238523'}
TARGETS = set(LEFT + RIGHT + list(MN9.values()) + list(CANDIDATES.values()))
CHUNK = 200_000


def arguments():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--simulate', action='store_true', help='Запустить адаптированную модель после проверки')
    p.add_argument('--accept-candidate-map', action='store_true', help='Явно принять гипотетические соответствия ID')
    p.add_argument('--accept-exclusions', action='store_true', help='Явно разрешить исключение связей с неиспользуемыми типами медиаторов')
    p.add_argument('--side', choices=['left', 'right'], default='left', help='Сторона по обозначениям в авторском ноутбуке')
    p.add_argument('--frequency-hz', type=float, default=100.0)
    p.add_argument('--n-trials', type=int, default=1)
    p.add_argument('--seed', type=int, default=0)
    return p.parse_args()


def file_for(var):
    value = os.environ.get(var, '').strip()
    if not value:
        raise ValueError(f'{var} не выбран в «Данные и окружение».')
    path = Path(value)
    if not path.is_file():
        raise ValueError(f'{var}: файл недоступен: {path}')
    if not path.name.lower().endswith(('.csv', '.csv.gz')):
        raise ValueError(f'{var}: нужны CSV или CSV.GZ.')
    return path


def checked_id(series, name):
    valid = series.notna() & series.str.fullmatch(r'[1-9][0-9]*', na=False)
    if not valid.all():
        raise ValueError(f'{name}: ID должны быть положительными целыми числами без пропусков.')


def read_nt(path):
    df = pd.read_csv(path, usecols=['root_id', 'nt_type'], dtype='string', encoding='utf-8-sig')
    df['root_id'] = df['root_id'].str.strip()
    checked_id(df['root_id'], 'root_id')
    if df['root_id'].duplicated().any():
        raise ValueError('В таблице медиаторов есть повторяющиеся root_id; неоднозначный источник.')
    df['nt_type'] = df['nt_type'].fillna('').str.strip().str.lower()
    return dict(zip(df['root_id'].tolist(), df['nt_type'].tolist()))


def type_sign(nt):
    # Явное приближение для этих таблиц, не вывод о действии в живом мозге.
    if nt in ('ach', 'acetylcholine', 'cholinergic'):
        return 1
    if nt in ('gaba', 'gabaergic', 'glut', 'glutamate', 'glutamatergic'):
        return -1
    return 0


def scan_connections(path, nt):
    presence = {x: {'pre_rows': 0, 'post_rows': 0} for x in sorted(TARGETS)}
    neurons = set(nt)
    by_type = {}
    total = 0
    for chunk in pd.read_csv(path, usecols=['pre_root_id', 'post_root_id', 'syn_count'], dtype={'pre_root_id': 'string', 'post_root_id': 'string'}, chunksize=CHUNK, encoding='utf-8-sig'):
        pre, post = chunk['pre_root_id'].str.strip(), chunk['post_root_id'].str.strip()
        checked_id(pre, 'pre_root_id'); checked_id(post, 'post_root_id')
        weights = pd.to_numeric(chunk['syn_count'], errors='raise').to_numpy(dtype=float)
        if not np.isfinite(weights).all() or (weights <= 0).any() or not np.equal(weights, np.floor(weights)).all():
            raise ValueError('syn_count должен содержать положительные целые числа.')
        total += len(chunk)
        neurons.update(pre.unique().tolist()); neurons.update(post.unique().tolist())
        for col, field in ((pre, 'pre_rows'), (post, 'post_rows')):
            for rid, count in col[col.isin(TARGETS)].value_counts().items():
                presence[str(rid)][field] += int(count)
        types = pre.map(nt).fillna('').astype(str)
        for typ, count in types.value_counts().items():
            key = typ or '(нет данных)'
            by_type[key] = by_type.get(key, 0) + int(count)
    if not total:
        raise ValueError('Таблица связей пуста.')
    return {'rows': total, 'neurons': neurons, 'presence': presence, 'by_type': by_type}


def resolve_ids(scan, nt):
    presence = scan['presence']
    def seen(rid):
        return presence[rid]['pre_rows'] + presence[rid]['post_rows'] > 0
    info, resolved = {}, {}
    for old in LEFT + RIGHT + list(MN9.values()):
        candidate = CANDIDATES.get(old)
        old_ok = seen(old) and old in nt
        candidate_ok = bool(candidate and seen(candidate) and candidate in nt)
        if old_ok and candidate_ok:
            chosen, state = None, 'ambiguous_both_present'
        elif old_ok:
            chosen, state = old, 'same_id_present'
        elif candidate_ok:
            chosen, state = candidate, 'candidate_present_unverified'
        else:
            chosen, state = None, 'missing'
        info[old] = {'original_in_connections': seen(old), 'original_in_nt': old in nt,
                     'candidate': candidate, 'candidate_in_connections': seen(candidate) if candidate else None,
                     'candidate_in_nt': candidate in nt if candidate else None, 'selected_if_accepted': chosen, 'status': state}
        resolved[old] = chosen
    return info, resolved


def run_simulation(conn, scan, nt, mapping, args, output):
    import brian2 as b2
    ids = sorted(scan['neurons'], key=int)
    index = {rid: i for i, rid in enumerate(ids)}
    left, right = index[mapping[MN9['left']]], index[mapping[MN9['right']]]
    targets = [index[mapping[rid]] for rid in (LEFT if args.side == 'left' else RIGHT)]
    chunks_pre, chunks_post, chunks_weight = [], [], []
    excluded = 0
    for chunk in pd.read_csv(conn, usecols=['pre_root_id', 'post_root_id', 'syn_count'], dtype={'pre_root_id': 'string', 'post_root_id': 'string'}, chunksize=CHUNK, encoding='utf-8-sig'):
        pre_ids, post_ids = chunk['pre_root_id'].str.strip(), chunk['post_root_id'].str.strip()
        signs = np.array([type_sign(str(v)) for v in pre_ids.map(nt).fillna('').tolist()], dtype=np.int8)
        selected = signs != 0
        excluded += int((~selected).sum())
        if selected.any():
            chunks_pre.append(pre_ids[selected].map(index).to_numpy(dtype=np.int32))
            chunks_post.append(post_ids[selected].map(index).to_numpy(dtype=np.int32))
            chunks_weight.append(pd.to_numeric(chunk.loc[selected, 'syn_count'], errors='raise').to_numpy(dtype=float) * signs[selected])
    if not chunks_pre:
        raise ValueError('Нет связей с поддерживаемым типом медиатора.')
    pre, post, weights = np.concatenate(chunks_pre), np.concatenate(chunks_post), np.concatenate(chunks_weight)
    del chunks_pre, chunks_post, chunks_weight
    # Синапсы по разным neuropil сохраняются отдельными строками, линейные вклады складываются.
    b2.prefs.codegen.target = 'numpy'
    b2.start_scope()
    b2.defaultclock.dt = 0.1 * b2.ms
    params = {'v_0': -52*b2.mV, 'v_rst': -52*b2.mV, 'v_th': -45*b2.mV, 't_mbr': 20*b2.ms, 'tau': 5*b2.ms, 't_rfc': 2.2*b2.ms}
    eqs = 'dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)\ndg/dt = -g / tau : volt (unless refractory)\nrfc : second'
    neurons = b2.NeuronGroup(len(ids), eqs, method='linear', threshold='v > v_th', reset='v = v_rst; g = 0*mV', refractory='rfc', namespace=params)
    neurons.v = params['v_0']; neurons.g = 0; neurons.rfc = params['t_rfc']
    syn = b2.Synapses(neurons, neurons, 'w : volt', on_pre='g += w', delay=1.8*b2.ms)
    syn.connect(i=pre, j=post)
    syn.w = weights * 0.275*b2.mV
    pois = []
    for i in targets:
        neurons[i].rfc = 0*b2.ms
        pois.append(b2.PoissonInput(neurons[i], 'v', N=1, rate=args.frequency_hz*b2.Hz, weight=0.275*250*b2.mV))
    # Считаем только MN9; авторская модель сохраняет спайки всех активных нейронов.
    monitor = b2.SpikeMonitor(neurons, record=False)
    net = b2.Network(neurons, syn, monitor, *pois)
    if args.n_trials > 1: net.store('initial')
    rows = []
    for trial in range(args.n_trials):
        if args.n_trials > 1: net.restore('initial')
        b2.seed(args.seed + trial)
        print(f'Расчёт: повтор {trial + 1}/{args.n_trials}, 1 секунда модельного времени...', flush=True)
        start = time.time()
        net.run(1000*b2.ms, namespace={})
        rows.append({'trial': trial + 1, 'seed': args.seed + trial, 'left_mn9_id': ids[left], 'right_mn9_id': ids[right],
                     'left_mn9_rate_hz': int(monitor.count[left]), 'right_mn9_rate_hz': int(monitor.count[right]),
                     'wall_seconds': round(time.time() - start, 3)})
    csv = output / 'mn9_trials.csv'
    pd.DataFrame(rows).to_csv(csv, index=False)
    return {'neurons': len(ids), 'used_connection_rows': int(len(weights)), 'excluded_connection_rows': excluded,
            'stimulation_ids': [ids[i] for i in targets], 'trials': rows, 'file': csv.name,
            'brian2': b2.__version__, 'dt_ms': 0.1, 'duration_ms': 1000}


def main():
    args = arguments()
    run_dir = os.environ.get('FLY_RUN_DIR', '').strip()
    if not run_dir:
        print('FLY_RUN_DIR не задан. Запустите из приложения.', file=sys.stderr)
        return 2
    out = Path(run_dir); out.mkdir(parents=True, exist_ok=True)
    report = {'status': 'pending', 'mode': 'adapted_simulation' if args.simulate else 'preflight', 'args': vars(args),
              'scope': 'Адаптация для CSV Princeton, не точное воспроизведение статьи.', 'author_source': SOURCE,
              'candidate_mapping_source': MAPPING_SOURCE, 'caveats': [
                  'Идентичность кандидатов и версия данных не подтверждены; стороны названы по авторскому ноутбуку.',
                  'Данные Princeton не приравниваются к авторской связности v630 или v783; количественное сравнение с авторскими таблицами не выполнялось.',
                  'ACH условно возбуждающий, GABA и GLUT условно тормозящие; прочие типы исключаются. Это не полная авторская обработка и не биологическое доказательство.',
                  'Повторы, частота и выбор стороны нужно сверить с протоколом конкретной панели; результат не является верифицированной Figure 1c.'], 'files': []}
    try:
        if not 0 <= args.seed <= 2**32 - max(args.n_trials, 1) or not 1 <= args.n_trials <= 30 or not np.isfinite(args.frequency_hz) or not 0 < args.frequency_hz <= 200:
            raise ValueError('Укажите seed, 1–30 повторов и частоту в диапазоне (0, 200] Гц.')
        conn, nt_file = file_for('FLY_CONNECTOME'), file_for('FLY_NEUROTRANSMITTERS')
        before = {str(f): {'bytes': f.stat().st_size, 'mtime_ns': f.stat().st_mtime_ns} for f in (conn, nt_file)}
        report['inputs'] = before
        print('Читаем медиаторы и полную таблицу связей, это может занять время...', flush=True)
        nt = read_nt(nt_file)
        scan = scan_connections(conn, nt)
        for f in (conn, nt_file):
            if before[str(f)] != {'bytes': f.stat().st_size, 'mtime_ns': f.stat().st_mtime_ns}:
                raise ValueError(f'Файл изменился во время чтения: {f}')
        mapping, resolved = resolve_ids(scan, nt)
        report['reference_id_check'] = mapping
        report['data_check'] = {'connection_rows': scan['rows'], 'neuron_ids_union': len(scan['neurons']), 'rows_by_presynaptic_nt': scan['by_type'],
                                'excluded_rows': sum(v for k, v in scan['by_type'].items() if not type_sign(k))}
        blockers = [f'{old}: {v["status"]}' for old, v in mapping.items() if v['selected_if_accepted'] is None]
        if len({x for x in resolved.values() if x}) != sum(x is not None for x in resolved.values()):
            blockers.append('Несколько авторских ID ведут к одному ID: нужна ручная проверка.')
        report['blockers'] = blockers
        report['candidate_mapping_required'] = any(v['status'] == 'candidate_present_unverified' for v in mapping.values())
        if blockers:
            report['status'] = 'blocked'
        elif not args.simulate:
            report['status'] = 'preflight_complete'
        elif report['candidate_mapping_required'] and not args.accept_candidate_map:
            report['status'] = 'blocked'
            report['blockers'].append('Нужно явно принять непроверенные соответствия ID флагом --accept-candidate-map.')
        elif report['data_check']['excluded_rows'] and not args.accept_exclusions:
            report['status'] = 'blocked'
            report['blockers'].append('Нужно явно принять исключения связей флагом --accept-exclusions.')
        else:
            report['result'] = run_simulation(conn, scan, nt, resolved, args, out)
            for f in (conn, nt_file):
                if before[str(f)] != {'bytes': f.stat().st_size, 'mtime_ns': f.stat().st_mtime_ns}:
                    raise ValueError(f'Файл изменился во время расчёта: {f}')
            report['files'].append('mn9_trials.csv')
            report['status'] = 'ok'
    except Exception as exc:
        report['status'] = 'error'
        report['error'] = f'{type(exc).__name__}: {exc}'
    with (out / 'summary.json').open('w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, allow_nan=False)
    print(f"Статус: {report['status']}. Отчёт: {out / 'summary.json'}", flush=True)
    if report.get('blockers'): print('Препятствия:', '; '.join(report['blockers']), flush=True)
    if report.get('error'): print(report['error'], file=sys.stderr, flush=True)
    return 0 if report['status'] in ('ok', 'preflight_complete') else 1


if __name__ == '__main__':
    sys.exit(main())
