#!/usr/bin/env python3
"""Directed one- and two-edge paths in the pinned author v630 model graph.

Reads the linked Shiu files only; never modifies them or opens study databases.
No simulation, activity inference, or path-strength claim.
"""
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import sys
import traceback
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

SOURCE = 720575940623211725
TARGETS = {'left': 720575940660219265, 'right': 720575940645521262}
EXPECTED = {'connections': '8b4d9531bc0acbda7c2074ae577e6ac9e2fca166',
            'neurons': 'be745f0ce054308df21accc5c4b3883aa38498f9'}
COLUMNS = ['Presynaptic_ID', 'Postsynaptic_ID', 'Presynaptic_Index', 'Postsynaptic_Index', 'Connectivity', 'Excitatory', 'Excitatory x Connectivity']


def fingerprint(path):
    before = path.stat()
    git = hashlib.sha1(f'blob {before.st_size}\0'.encode()); sha = hashlib.sha256()
    with path.open('rb') as f:
        while chunk := f.read(2 * 1024 * 1024):
            git.update(chunk); sha.update(chunk)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f'Файл изменился при чтении: {path}')
    return {'path': str(path.resolve()), 'bytes': before.st_size, 'mtime_ns': before.st_mtime_ns,
            'git_blob_sha1': git.hexdigest(), 'sha256': sha.hexdigest()}


def ensure_unchanged(path, fp):
    st = path.stat()
    if (st.st_size, st.st_mtime_ns) != (fp['bytes'], fp['mtime_ns']):
        raise ValueError(f'Файл изменился во время анализа: {path}')


def ids_from_csv(path):
    ids = []
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            raise ValueError('Пустой CSV нейронов')
        for row in reader:
            text = row[0].strip() if row else ''
            if not text.isascii() or not text.isdigit() or int(text) <= 0:
                raise ValueError('Некорректный ID в CSV нейронов')
            ids.append(int(text))
    if len(set(ids)) != len(ids) or not ids:
        raise ValueError('Пустой список или дубликаты ID нейронов')
    if any(x not in ids for x in [SOURCE, *TARGETS.values()]):
        raise ValueError('Клетка ранга 62 или MN9 отсутствует в списке')
    return np.asarray(ids, dtype=np.int64)


def add_edge(edges, pre, post, count, sign):
    key = (int(pre), int(post))
    count, sign = int(count), int(sign)
    if key in edges:
        if edges[key][1] != sign:
            raise ValueError(f'Противоречивые знаки повторённой пары {key}')
        edges[key][0] += count
        edges[key][2] += 1
    else:
        edges[key] = [count, sign, 1]


def collect(conn, ids):
    table = pq.ParquetFile(conn)
    if any(name not in table.schema_arrow.names or not pa.types.is_integer(table.schema_arrow.field(name).type) for name in COLUMNS):
        raise ValueError('Таблица не содержит необходимых целочисленных колонок')
    outgoing, incoming = {}, {}
    nrows = 0
    for batch in table.iter_batches(batch_size=250_000, columns=COLUMNS, use_threads=False):
        if any(col.null_count for col in batch.columns):
            raise ValueError('Пропущенные значения в связях')
        c = {name: batch.column(name).to_numpy(zero_copy_only=False) for name in COLUMNS}
        i, j = c[COLUMNS[2]], c[COLUMNS[3]]
        n, sign, weighted = c[COLUMNS[4]], c[COLUMNS[5]], c[COLUMNS[6]]
        if (np.any(i < 0) or np.any(j < 0) or np.any(i >= len(ids)) or np.any(j >= len(ids))
            or np.any(c[COLUMNS[0]] != ids[i]) or np.any(c[COLUMNS[1]] != ids[j])
            or np.any(n <= 0) or np.any((sign != 1) & (sign != -1)) or np.any(weighted != n * sign)):
            raise ValueError('Некорректные индексы, ID, количество или знак связи')
        pre, post = c[COLUMNS[0]], c[COLUMNS[1]]
        for k in np.flatnonzero(pre == SOURCE):
            add_edge(outgoing, pre[k], post[k], n[k], sign[k])
        for k in np.flatnonzero(np.isin(post, list(TARGETS.values()))):
            add_edge(incoming, pre[k], post[k], n[k], sign[k])
        nrows += batch.num_rows
    if nrows != table.metadata.num_rows or not nrows:
        raise ValueError('Неполное чтение таблицы связей')
    return outgoing, incoming, nrows


def path_rows(outgoing, incoming, targets=TARGETS, source=SOURCE):
    direct, indirect = [], []
    for side, target in targets.items():
        edge = outgoing.get((source, target))
        if edge:
            direct.append([side, str(source), str(target), *edge])
        for (pre, middle), first in outgoing.items():
            if pre != source or middle in (source, target):
                continue  # simple paths only; no self loops as intermediates
            second = incoming.get((middle, target))
            if second:
                indirect.append([side, str(source), str(middle), str(target), *first, *second])
    indirect.sort(key=lambda row: (row[0], -min(row[4], row[7]), -row[4], -row[7], int(row[2])))
    return direct, indirect


def write_csv(path, header, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f); writer.writerow(header); writer.writerows(rows)


def main():
    output = Path(os.environ.get('FLY_RUN_DIR', '')) if os.environ.get('FLY_RUN_DIR') else None
    if output is None:
        raise ValueError('FLY_RUN_DIR не задан; запускайте из приложения')
    output.mkdir(parents=True, exist_ok=True)
    conn = Path(os.environ.get('FLY_SHIU_CONNECTIONS', ''))
    neurons = Path(os.environ.get('FLY_SHIU_NEURONS', ''))
    if not conn.is_file() or not neurons.is_file():
        raise ValueError('Выберите авторские связи и список нейронов Shiu v630 в «Данные и окружение».')
    print('Проверка целостности авторских файлов v630...', flush=True)
    inputs = {'connections': fingerprint(conn), 'neurons': fingerprint(neurons)}
    if any(inputs[k]['git_blob_sha1'] != sha for k, sha in EXPECTED.items()):
        raise ValueError('Авторские файлы не совпадают с закреплённой версией v630; анализ остановлен.')
    ids = ids_from_csv(neurons)
    print('Потоковое чтение связей, без моделирования...', flush=True)
    outgoing, incoming, total = collect(conn, ids)
    ensure_unchanged(conn, inputs['connections']); ensure_unchanged(neurons, inputs['neurons'])
    direct, indirect = path_rows(outgoing, incoming)
    write_csv(output / 'direct_edges.csv', ['side', 'source_id', 'mn9_id', 'connectivity', 'assigned_sign', 'rows'], direct)
    write_csv(output / 'two_step_paths.csv', ['side', 'source_id', 'intermediate_id', 'mn9_id',
              'first_connectivity', 'first_assigned_sign', 'first_rows', 'second_connectivity', 'second_assigned_sign', 'second_rows'], indirect)
    incoming_stats = {}
    for side, target in TARGETS.items():
        edges = [value for (pre, post), value in incoming.items() if post == target]
        edge = incoming.get((SOURCE, target))
        incoming_stats[side] = {'partners': len(edges), 'connectivity_total': sum(x[0] for x in edges),
                                'source_rank_competition': 1 + sum(x[0] > edge[0] for x in edges) if edge else None,
                                'source_ties': sum(x[0] == edge[0] for x in edges) if edge else 0}
    summary = {'status': 'complete', 'source_id': str(SOURCE), 'mn9_ids': {k: str(v) for k, v in TARGETS.items()},
               'input_files': inputs, 'neuron_count': len(ids), 'connection_rows': total,
               'direct': {side: sum(row[0] == side for row in direct) for side in TARGETS},
               'two_step': {side: sum(row[0] == side for row in indirect) for side in TARGETS},
               'source_outgoing_partners': len(outgoing), 'incoming_stats': incoming_stats, 'python': platform.python_version(),
               'numpy': np.__version__, 'pyarrow': pa.__version__,
               'script_sha256': hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
               'limits': ['Only 1- and 2-edge simple directed paths; longer paths excluded.',
                          'Connectivity and sign are author model fields; sign is an assigned model parameter, not validated physiology.',
                          'Path count and connectivity do not imply activity, effect size, or causal mediation.',
                          'Only author v630 graph; no neuronal type or neurotransmitter annotation is inferred.'],
               'files': ['report.txt', 'direct_edges.csv', 'two_step_paths.csv', 'summary.json']}
    lines = ['АНАТОМИЧЕСКИЙ ОБЗОР: КЛЕТКА РАНГА 62 -> MN9',
             f'Исходная клетка: {SOURCE}. Авторская модель v630; проверены хеши обоих файлов.',
             f'Нейронов: {len(ids)}; строк связей: {total}; исходящих партнёров: {len(outgoing)}.',
             '']
    for side, target in TARGETS.items():
        rows = [r for r in indirect if r[0] == side]
        d = [r for r in direct if r[0] == side]
        lines.append(f'{side} MN9 {target}: прямых пар {len(d)}, двухшаговых простых путей {len(rows)}.')
        if d:
            st = incoming_stats[side]
            lines.append(f'  Прямая связь: Connectivity={d[0][3]}, знак модели={d[0][4]}; '
                         f'ранг по размеру {st["source_rank_competition"]} из {st["partners"]} входящих партнёров '
                         f'(одинаковые значения делят ранг).')
        for r in rows[:10]:
            lines.append(f'  {r[2]}: вход от клетки {r[4]} (знак {r[5]:+d}), выход к MN9 {r[7]} (знак {r[8]:+d}).')
    lines += ['', 'Показаны первые 10 по минимальному числу связей на двух рёбрах. Полный список: two_step_paths.csv.',
              'Знак назначен в модели автора. Числа путей и связей не доказывают передачу сигнала или причину эффекта лезии.',
              'Более длинные пути, динамика сети, типы клеток и биологическая валидация здесь не анализируются.']
    (output / 'report.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\n'.join(lines), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        out = os.environ.get('FLY_RUN_DIR')
        if out:
            Path(out).mkdir(parents=True, exist_ok=True)
            (Path(out) / 'summary.json').write_text(json.dumps({'status': 'error', 'error': str(exc)}, ensure_ascii=False, indent=2), encoding='utf-8')
        sys.exit(1)
