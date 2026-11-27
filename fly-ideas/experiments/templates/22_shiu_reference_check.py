"""Сверка входных таблиц с ID из авторского ноутбука Shiu et al.

Никаких симуляций не запускает. Совпадение ID само по себе не доказывает
соответствие версий коннектома и не является воспроизведением статьи.
"""
import json
import os
import sys
from pathlib import Path

import pandas as pd

# Авторский figures.ipynb, commit 91bdd1e7dcf193f3e7ca5a8933497fcef63b7960:
# Figure 1D: правые sugar GRNs, Extended Data/S1D в ноутбуке: левые sugar GRNs;
# Figure 2: MN9 слева и справа. Там же конфигурация исходных файлов версии 630.
RIGHT_SUGAR = [
    "720575940624963786", "720575940630233916", "720575940637568838", "720575940638202345", "720575940617000768",
    "720575940630797113", "720575940632889389", "720575940621754367", "720575940621502051", "720575940640649691",
    "720575940639332736", "720575940616885538", "720575940639198653", "720575940620900446", "720575940617937543",
    "720575940632425919", "720575940633143833", "720575940612670570", "720575940628853239", "720575940629176663",
    "720575940611875570",
]
LEFT_SUGAR = [
    "720575940620589838", "720575940631147148", "720575940608305161", "720575940629388135", "720575940630968335",
    "720575940606801282", "720575940617398502", "720575940616167218", "720575940620296641", "720575940627961104",
]
MN9 = {"left": "720575940660219265", "right": "720575940645521262"}
TARGETS = set(RIGHT_SUGAR + LEFT_SUGAR + list(MN9.values()))
SOURCE = "https://github.com/philshiu/Drosophila_brain_model/blob/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960/figures.ipynb"
CHUNK = 200_000


def table_batches(file, columns=None):
    name = file.name.lower()
    if name.endswith('.parquet'):
        import pyarrow.parquet as pq
        parquet = pq.ParquetFile(file)
        names = parquet.schema_arrow.names
        if columns is None:
            return names
        return (batch.to_pandas().astype('string') for batch in parquet.iter_batches(columns=columns, batch_size=CHUNK))
    if not name.endswith(('.csv', '.csv.gz', '.tsv', '.tsv.gz')):
        raise ValueError('Поддерживаются CSV, CSV.GZ, TSV, TSV.GZ и Parquet.')
    sep = '\t' if name.endswith(('.tsv', '.tsv.gz')) else ','
    if columns is None:
        return list(pd.read_csv(file, sep=sep, nrows=0, encoding='utf-8-sig').columns)
    return pd.read_csv(file, sep=sep, usecols=columns, dtype='string', chunksize=CHUNK, encoding='utf-8-sig')


def pick(columns, names):
    mapping = {str(c).strip().lower(): c for c in columns}
    return next((mapping[x] for x in names if x in mapping), None)


def scan(role, env_name):
    value = os.environ.get(env_name, '').strip()
    if not value:
        return {'status': 'not_selected', 'message': f'{env_name} не выбран.'}
    file = Path(value)
    result = {'status': 'error', 'path': str(file)}
    try:
        if not file.is_file():
            raise FileNotFoundError('Файл недоступен.')
        stat = file.stat()
        result.update(size_bytes=stat.st_size, modified_unix=stat.st_mtime)
        columns = table_batches(file)
        result['columns'] = columns
        if role == 'connections':
            pre = pick(columns, ['pre_root_id', 'pre_pt_root_id', 'pre', 'bodyid_pre'])
            post = pick(columns, ['post_root_id', 'post_pt_root_id', 'post', 'bodyid_post'])
            if not pre or not post or pre == post:
                raise ValueError('Не найдены колонки ID до и после синапса; таблица в другом формате.')
            chosen = [pre, post]
            result.update(pre_column=pre, post_column=post)
            counts = {rid: {'pre_rows': 0, 'post_rows': 0} for rid in sorted(TARGETS)}
            total = 0
            for chunk in table_batches(file, chosen):
                total += len(chunk)
                for col, key in ((pre, 'pre_rows'), (post, 'post_rows')):
                    vals = chunk[col].str.strip()
                    for rid, count in vals[vals.isin(TARGETS)].value_counts().items():
                        counts[str(rid)][key] += int(count)
            result.update(rows_scanned=total, id_counts=counts)
        else:
            id_col = pick(columns, ['root_id', 'flywire_id', 'body_id', 'bodyid'])
            if not id_col:
                raise ValueError('Не найдена колонка root_id или flywire_id.')
            counts = {rid: 0 for rid in sorted(TARGETS)}
            total = 0
            for chunk in table_batches(file, [id_col]):
                total += len(chunk)
                vals = chunk[id_col].str.strip()
                for rid, count in vals[vals.isin(TARGETS)].value_counts().items():
                    counts[str(rid)] += int(count)
            result.update(id_column=id_col, rows_scanned=total, id_counts=counts)
        if file.stat().st_size != stat.st_size or file.stat().st_mtime != stat.st_mtime:
            raise RuntimeError('Файл изменился во время чтения; повторите проверку.')
        result['status'] = 'ok'
    except Exception as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
    return result


def main():
    run = os.environ.get('FLY_RUN_DIR', '').strip()
    if not run:
        print('FLY_RUN_DIR не задан. Запустите скрипт из приложения.', file=sys.stderr)
        return 2
    run_dir = Path(run)
    run_dir.mkdir(parents=True, exist_ok=True)
    report = {
        'status': 'pending',
        'scope': 'Только сверка строковых ID. Симуляция и проверка Figure 1c не выполняются.',
        'reference': {'url': SOURCE, 'commit': '91bdd1e7dcf193f3e7ca5a8933497fcef63b7960',
                      'note': 'ID из ноутбука, настроенного на v630; это не установление их соответствия другому релизу.'},
        'reference_ids': {'sugar_right_figure_1d': RIGHT_SUGAR, 'sugar_left_supplement': LEFT_SUGAR, 'mn9_figure_2': MN9},
        'caveats': [
            'Наличие одинаковых ID не доказывает идентичность клеток, версии или связности.',
            'Отсутствие ID в таблице связей означает только отсутствие в её строках, а не отсутствие нейрона.',
            'Описание сторон в опубликованной Figure 1c необходимо отдельно сверить с протоколом и исходными результатами.',
            'Авторская модель использует свои подготовленные таблицы; эта проверка не преобразует их и не проверяет эквивалентность.',
        ],
        'tables': {},
    }
    for role, env in [('connections', 'FLY_CONNECTOME'), ('annotations', 'FLY_ANNOTATIONS'),
                      ('cell_types', 'FLY_CELL_TYPES'), ('neurotransmitters', 'FLY_NEUROTRANSMITTERS')]:
        print(f'Проверка {role}: {env}...', flush=True)
        report['tables'][role] = scan(role, env)
    connections = report['tables']['connections']
    if connections['status'] == 'ok':
        counts = connections['id_counts']
        found = lambda rid: counts[rid]['pre_rows'] > 0 or counts[rid]['post_rows'] > 0
        report['matches_in_connections'] = {
            'sugar_right': {'found': sum(found(rid) for rid in RIGHT_SUGAR), 'total': len(RIGHT_SUGAR)},
            'sugar_left': {'found': sum(found(rid) for rid in LEFT_SUGAR), 'total': len(LEFT_SUGAR)},
            'mn9_left': found(MN9['left']), 'mn9_right': found(MN9['right']),
        }
        print(f"Совпадения в связях: {report['matches_in_connections']}", flush=True)
        report['status'] = 'ok'
    else:
        report['status'] = 'blocked'
    out = run_dir / 'summary.json'
    with out.open('w', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f'Отчёт: {out}\nСтатус: {report["status"]}. Это не запуск модели.')
    return 0 if report['status'] == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
