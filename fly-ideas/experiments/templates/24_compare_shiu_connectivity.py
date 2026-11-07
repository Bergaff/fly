"""Сравнение подключённой таблицы Princeton с авторскими таблицами Shiu v630.

Сопоставляет только точно одинаковые ID, не применяет непроверенные переименования.
Не изменяет входные файлы, не запускает модель и не проверяет её воспроизведение.
Для больших таблиц нужны время и свободное место для временных файлов.
"""
import csv
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

EXPECTED = {'author_connections': '8b4d9531bc0acbda7c2074ae577e6ac9e2fca166',
            'author_neurons': 'be745f0ce054308df21accc5c4b3883aa38498f9'}
SOURCE = 'https://github.com/philshiu/Drosophila_brain_model/tree/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960'


def required(var, extensions):
    value = os.environ.get(var, '').strip()
    if not value:
        raise ValueError(f'{var} не выбран в разделе «Данные и окружение».')
    file = Path(value)
    if not file.is_file():
        raise ValueError(f'{var}: файл недоступен: {file}')
    if not file.name.lower().endswith(extensions):
        raise ValueError(f'{var}: неподдерживаемый формат файла; нужен {" или ".join(extensions)}.')
    return file


def fingerprint(file):
    stat = file.stat()
    sha = hashlib.sha256()
    git = hashlib.sha1(f'blob {stat.st_size}\0'.encode())
    with file.open('rb') as stream:
        for chunk in iter(lambda: stream.read(2 * 1024 * 1024), b''):
            sha.update(chunk); git.update(chunk)
    after = file.stat()
    if (stat.st_size, stat.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f'Файл изменился во время чтения: {file}')
    return {'path': str(file), 'bytes': stat.st_size, 'mtime_ns': stat.st_mtime_ns,
            'sha256': sha.hexdigest(), 'git_blob_sha1': git.hexdigest()}


def scalar(db, sql, params=None):
    return db.execute(sql, params or []).fetchone()[0]


def plot_results(output, data, sample, verified):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                         'figure.facecolor': '#eeeae2', 'axes.facecolor': '#eeeae2',
                         'axes.edgecolor': '#716c62', 'text.color': '#383831',
                         'axes.labelcolor': '#383831', 'xtick.color': '#383831', 'ytick.color': '#383831'})
    f, ax = plt.subplots(figsize=(7, 4.5))
    labels = ['Только авторская', 'Общие', 'Только выбранная']
    values = [data['author_only_pairs'], data['common_pairs'], data['princeton_only_pairs']]
    bars = ax.bar(labels, values, color=['#697b87', '#777e5a', '#a17851'], width=0.6)
    for bar, value in zip(bars, values):
        ax.annotate(f'{value:,}'.replace(',', ' '), (bar.get_x()+bar.get_width()/2, value), xytext=(0, 4), textcoords='offset points', ha='center', fontsize=9)
    ax.set_ylabel('направленные пары нейронов'); ax.set_title('Связность на общем наборе точных ID')
    ax.set_ylim(0, max(values + [1]) * 1.15); f.tight_layout(); f.savefig(output / 'pairs.png', dpi=140); plt.close(f)
    f, ax = plt.subplots(figsize=(6, 5))
    if sample:
        a = [r[0] for r in sample]; p = [r[1] for r in sample]
        ax.scatter(a, p, s=5, alpha=0.24, color='#465f6b', linewidths=0)
        ax.set_xscale('log'); ax.set_yscale('log')
        maximum = max(max(a), max(p), 1)
        ax.plot([1, maximum], [1, maximum], color='#8b7058', linewidth=0.8)
    else:
        ax.text(0.5, 0.5, 'Нет общих пар для графика', ha='center', va='center', transform=ax.transAxes)
    ax.set_xlabel('Синапсы: Shiu v630' if verified else 'Синапсы: авторская таблица (версия не подтверждена)'); ax.set_ylabel('Синапсы: выбранная таблица')
    ax.set_title(f'Веса общих пар, показано {len(sample)} из {data["common_pairs"]}')
    f.tight_layout(); f.savefig(output / 'weights.png', dpi=140); plt.close(f)


def compare(output):
    import duckdb
    import pandas as pd
    inputs = {
        'princeton': required('FLY_CONNECTOME', ('.csv', '.csv.gz')),
        'author_connections': required('FLY_SHIU_CONNECTIONS', ('.parquet',)),
        'author_neurons': required('FLY_SHIU_NEURONS', ('.csv',)),
    }
    optional = os.environ.get('FLY_NEUROTRANSMITTERS', '').strip()
    if optional:
        inputs['neurotransmitters'] = required('FLY_NEUROTRANSMITTERS', ('.csv', '.csv.gz'))
    hashes = {}
    for key, file in inputs.items():
        print(f'Проверяем файл {key}: {file}', flush=True)
        hashes[key] = fingerprint(file)
    exact = {key: hashes[key]['git_blob_sha1'] == expected for key, expected in EXPECTED.items()}
    if not all(exact.values()):
        print('ВНИМАНИЕ: авторские файлы не совпадают с закреплённой версией v630, происхождение не подтверждено.', flush=True)
    scratch = Path(tempfile.mkdtemp(prefix='.compare_tmp-', dir=output))
    db = None
    try:
        db = duckdb.connect()
        db.execute("SET threads = 2")
        db.execute("SET memory_limit = '1GB'")
        # Path is escaped in a SQL string because SET does not accept parameters.
        db.execute("SET temp_directory = '" + str(scratch).replace("'", "''") + "'")
        neurons = pd.read_csv(inputs['author_neurons'], usecols=[0], dtype='string', encoding='utf-8-sig')
        ids = neurons.iloc[:, 0].str.strip()
        if len(ids) == 0 or ids.isna().any() or not ids.str.fullmatch(r'[1-9][0-9]*').all() or ids.duplicated().any():
            raise ValueError('Авторский CSV должен содержать уникальные целочисленные ID нейронов в первой колонке.')
        try:
            ref = pd.DataFrame({'idx': range(len(ids)), 'id': ids.astype('int64')})
        except (ValueError, OverflowError) as exc:
            raise ValueError('ID в авторском списке не помещаются в int64.') from exc
        db.register('ref_input', ref)
        db.execute('CREATE TEMP TABLE reference_ids AS SELECT * FROM ref_input')
        print('Читаем таблицу Princeton...', flush=True)
        db.execute("CREATE TEMP TABLE raw_p AS SELECT pre_root_id, post_root_id, syn_count FROM read_csv(?, header=true, delim=',', all_varchar=true)", [str(inputs['princeton'])])
        rows_p = scalar(db, 'SELECT count(*) FROM raw_p')
        invalid = scalar(db, """SELECT count(*) FROM raw_p WHERE
            NOT coalesce(regexp_full_match(trim(pre_root_id), '[1-9][0-9]*'), false) OR
            NOT coalesce(regexp_full_match(trim(post_root_id), '[1-9][0-9]*'), false) OR
            NOT coalesce(regexp_full_match(trim(syn_count), '[1-9][0-9]*'), false) OR
            try_cast(trim(pre_root_id) AS BIGINT) IS NULL OR try_cast(trim(post_root_id) AS BIGINT) IS NULL OR
            try_cast(trim(syn_count) AS BIGINT) IS NULL""")
        if invalid or not rows_p:
            raise ValueError(f'Princeton: некорректных строк {invalid}, всего {rows_p}; нужны положительные целые ID и syn_count.')
        db.execute('CREATE TEMP TABLE p_raw AS SELECT cast(trim(pre_root_id) AS BIGINT) pre, cast(trim(post_root_id) AS BIGINT) post, cast(trim(syn_count) AS BIGINT) n FROM raw_p')
        db.execute('DROP TABLE raw_p')
        db.execute('CREATE TEMP TABLE p_ids AS SELECT pre AS id FROM p_raw UNION SELECT post AS id FROM p_raw')
        db.execute('CREATE TEMP TABLE common_ids AS SELECT r.id FROM reference_ids r INNER JOIN p_ids p ON r.id=p.id')
        n_p_ids = scalar(db, 'SELECT count(*) FROM p_ids')
        common_ids = scalar(db, 'SELECT count(*) FROM common_ids')
        if not common_ids:
            raise ValueError('В таблицах нет ни одного общего точного ID. Сравнение пар невозможно.')
        print('Проверяем авторскую таблицу и соответствие ID индексам...', flush=True)
        apath = str(inputs['author_connections'])
        # Авторский parquet содержит и ID, и индексы. Индексы обязательно сверяем с порядком CSV.
        invalid_author = scalar(db, '''SELECT count(*) FROM read_parquet(?) a
          LEFT JOIN reference_ids r1 ON a.Presynaptic_Index=r1.idx
          LEFT JOIN reference_ids r2 ON a.Postsynaptic_Index=r2.idx
          WHERE r1.id IS NULL OR r2.id IS NULL OR a.Presynaptic_ID IS DISTINCT FROM r1.id
             OR a.Postsynaptic_ID IS DISTINCT FROM r2.id OR a.Connectivity IS NULL OR a.Connectivity <= 0
             OR a.Excitatory IS NULL OR a.Excitatory NOT IN (-1,1)
             OR a."Excitatory x Connectivity" IS DISTINCT FROM a.Excitatory*a.Connectivity''', [apath])
        if invalid_author:
            raise ValueError(f'Авторский Parquet не соответствует списку нейронов или имеет некорректные веса: {invalid_author} строк.')
        rows_a = scalar(db, 'SELECT count(*) FROM read_parquet(?)', [apath])
        if not rows_a:
            raise ValueError('Авторская таблица связей пуста.')
        print('Объединяем повторные пары и сравниваем направленные связи...', flush=True)
        db.execute('''CREATE TEMP TABLE p AS SELECT x.pre,x.post,sum(x.n) AS n
          FROM p_raw x JOIN common_ids i ON x.pre=i.id JOIN common_ids j ON x.post=j.id GROUP BY x.pre,x.post''')
        p_rows_shared = scalar(db, 'SELECT count(*) FROM p_raw x JOIN common_ids i ON x.pre=i.id JOIN common_ids j ON x.post=j.id')
        db.execute('DROP TABLE p_raw')
        db.execute('''CREATE TEMP TABLE a AS SELECT x.Presynaptic_ID AS pre,x.Postsynaptic_ID AS post,
          sum(x.Connectivity) AS n,sum(x."Excitatory x Connectivity") AS signed_n,count(*) AS source_rows
          FROM read_parquet(?) x JOIN common_ids i ON x.Presynaptic_ID=i.id JOIN common_ids j ON x.Postsynaptic_ID=j.id
          GROUP BY x.Presynaptic_ID,x.Postsynaptic_ID''', [apath])
        author_rows_shared = scalar(db, 'SELECT coalesce(sum(source_rows),0) FROM a')
        a_pairs = scalar(db, 'SELECT count(*) FROM a'); p_pairs = scalar(db, 'SELECT count(*) FROM p')
        db.execute('CREATE TEMP TABLE matched_pairs AS SELECT a.pre,a.post,a.n AS author_n,p.n AS princeton_n,a.signed_n FROM a JOIN p USING(pre,post)')
        common = scalar(db, 'SELECT count(*) FROM matched_pairs')
        union = a_pairs + p_pairs - common
        corr = scalar(db, 'SELECT corr(cast(author_n AS DOUBLE),cast(princeton_n AS DOUBLE)) FROM matched_pairs') if common > 1 else None
        if corr is not None:
            corr = max(-1.0, min(1.0, corr)) if math.isfinite(corr) else None
        metrics = {'author_neurons': len(ids), 'princeton_connected_neurons': n_p_ids, 'same_ids_in_both': common_ids,
                   'author_rows_total': rows_a, 'princeton_rows_total': rows_p,
                   'author_rows_on_same_ids': int(author_rows_shared), 'princeton_rows_on_same_ids': p_rows_shared,
                   'author_pairs': a_pairs, 'princeton_pairs': p_pairs, 'common_pairs': common,
                   'author_only_pairs': a_pairs - common, 'princeton_only_pairs': p_pairs - common,
                   'jaccard_pairs': common / union if union else None,
                   'author_synapses_on_same_ids': int(scalar(db, 'SELECT coalesce(sum(n),0) FROM a')),
                   'princeton_synapses_on_same_ids': int(scalar(db, 'SELECT coalesce(sum(n),0) FROM p')),
                   'equal_weight_common_pairs': scalar(db, 'SELECT count(*) FROM matched_pairs WHERE author_n=princeton_n'),
                   'mean_absolute_weight_difference': scalar(db, 'SELECT avg(abs(author_n-princeton_n)) FROM matched_pairs'),
                   'sum_absolute_weight_difference': int(scalar(db, 'SELECT coalesce(sum(abs(author_n-princeton_n)),0) FROM matched_pairs')),
                   'author_synapses_on_common_pairs': int(scalar(db, 'SELECT coalesce(sum(author_n),0) FROM matched_pairs')),
                   'princeton_synapses_on_common_pairs': int(scalar(db, 'SELECT coalesce(sum(princeton_n),0) FROM matched_pairs')),
                   'weight_pearson_on_common_pairs': corr}
        # Сравнение знаков только при наличии выбранной таблицы нейромедиаторов.
        sign = {'status': 'not_selected'}
        if 'neurotransmitters' in inputs:
            nt = pd.read_csv(inputs['neurotransmitters'], usecols=['root_id','nt_type'], dtype='string', encoding='utf-8-sig')
            nid = nt['root_id'].str.strip()
            if nid.isna().any() or not nid.str.fullmatch(r'[1-9][0-9]*').all() or nid.duplicated().any():
                raise ValueError('В таблице нейромедиаторов некорректные или повторяющиеся root_id.')
            names = nt['nt_type'].fillna('').str.strip().str.lower()
            pos = {'ach','acetylcholine','cholinergic'}; neg = {'gaba','gabaergic','glut','glutamate','glutamatergic'}
            nt_df = pd.DataFrame({'id': nid.astype('int64'), 'sign': [1 if x in pos else -1 if x in neg else 0 for x in names]})
            db.register('nt_input', nt_df)
            result = db.execute('''SELECT count(*),
                count(*) FILTER (WHERE n.sign IS NOT NULL AND n.sign <> 0 AND b.signed_n <> 0),
                count(*) FILTER (WHERE n.sign IS NOT NULL AND n.sign <> 0 AND b.signed_n <> 0 AND sign(b.signed_n)=n.sign),
                count(*) FILTER (WHERE n.sign IS NOT NULL AND n.sign <> 0 AND b.signed_n <> 0 AND sign(b.signed_n)<>n.sign),
                count(*) FILTER (WHERE n.sign IS NULL OR n.sign=0),
                count(*) FILTER (WHERE n.sign IS NOT NULL AND n.sign<>0 AND b.signed_n=0)
                FROM matched_pairs b LEFT JOIN nt_input n ON n.id=b.pre''').fetchone()
            sign = dict(zip(['common_pairs', 'comparable_pairs', 'same_sign', 'different_sign', 'unavailable_or_excluded', 'author_net_zero'], result))
            sign['status'] = 'ok'
            sign['note'] = 'В Princeton знак взят из нейромедиатора пресинаптического нейрона: ACh +, GABA/GLUT −; остальные не сравниваются. Это допущение модели, не доказательство действия синапса.'
        divisor = max(1, common // 10000)
        sample = db.execute('SELECT author_n,princeton_n FROM matched_pairs WHERE hash(pre,post) % ? = 0 LIMIT 20000', [divisor]).fetchall()
        with (output / 'comparison.csv').open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f); w.writerow(['показатель', 'значение'])
            names = {
                'author_neurons': 'Нейроны в авторском списке', 'princeton_connected_neurons': 'ID в связях выбранной таблицы',
                'same_ids_in_both': 'Точно совпавшие ID', 'author_rows_total': 'Строк авторских связей всего',
                'princeton_rows_total': 'Строк выбранных связей всего', 'author_rows_on_same_ids': 'Строк авторских связей на общих ID',
                'princeton_rows_on_same_ids': 'Строк выбранных связей на общих ID', 'author_pairs': 'Авторских направленных пар на общих ID',
                'princeton_pairs': 'Направленных выбранных пар на общих ID', 'common_pairs': 'Общих направленных пар',
                'author_only_pairs': 'Пар только в авторской таблице', 'princeton_only_pairs': 'Пар только в выбранной таблице',
                'jaccard_pairs': 'Индекс Жаккара направленных пар', 'author_synapses_on_same_ids': 'Синапсов авторской таблицы на общих ID',
                'princeton_synapses_on_same_ids': 'Синапсов выбранной таблицы на общих ID',
                'equal_weight_common_pairs': 'Общих пар с одинаковым весом',
                'mean_absolute_weight_difference': 'Средняя абсолютная разница веса общих пар',
                'sum_absolute_weight_difference': 'Сумма абсолютных разниц веса общих пар',
                'author_synapses_on_common_pairs': 'Синапсов авторской таблицы на общих парах',
                'princeton_synapses_on_common_pairs': 'Синапсов выбранной таблицы на общих парах',
                'weight_pearson_on_common_pairs': 'Корреляция весов общих пар Pearson'}
            for k, v in metrics.items(): w.writerow([names[k], v if v is not None else ''])
            if sign['status'] == 'ok':
                for key, label in [('comparable_pairs','Пар со сравнимым знаком'), ('same_sign','Пар с одинаковым знаком'),
                                   ('different_sign','Пар с разным знаком'), ('unavailable_or_excluded','Пар без применимого медиатора'),
                                   ('author_net_zero','Пар с нулевым авторским суммарным знаком')]:
                    w.writerow([label, sign[key]])
        plot_results(output, metrics, sample, all(exact.values()))
        for key, file in inputs.items():
            current = file.stat(); orig = hashes[key]
            if (current.st_size, current.st_mtime_ns) != (orig['bytes'], orig['mtime_ns']):
                raise ValueError(f'Входной файл изменился во время сравнения: {file}')
        warning = 'да' if all(exact.values()) else 'нет, происхождение не подтверждено'
        if sign['status'] == 'ok':
            sign_line = (f"Сравнимых пар по знаку: {sign['comparable_pairs']}; одинаковый знак: {sign['same_sign']}; "
                         f"разный: {sign['different_sign']}; без применимого медиатора: {sign['unavailable_or_excluded']}; "
                         f"нулевой суммарный знак авторской таблицы: {sign['author_net_zero']}.")
            sign_note = sign['note']
        else:
            sign_line = 'Знаки не сравнивались: таблица нейромедиаторов не выбрана.'
            sign_note = ''
        lines = [
            'СРАВНЕНИЕ СВЯЗНОСТИ: выбранная таблица и авторская таблица', '',
            f'Оба авторских файла совпадают с закреплённой версией GitHub: {warning}',
            f'Точно одинаковых ID: {common_ids} из {len(ids)} в авторском списке и {n_p_ids} ID в выбранных связях.',
            f'Строк связей на общих ID: {author_rows_shared} из {rows_a} в авторской таблице; {p_rows_shared} из {rows_p} в выбранной.',
            f'Внутри этого набора: общих направленных пар {common}, только в авторской таблице {a_pairs-common}, только в выбранной таблице {p_pairs-common}.',
            f'Индекс Жаккара для направленных пар на общих ID: {metrics["jaccard_pairs"]}.',
            f'Сумма синапсов по общим парам: авторская таблица {metrics["author_synapses_on_common_pairs"]}, выбранная таблица {metrics["princeton_synapses_on_common_pairs"]}.',
            f'Общих пар с одинаковым весом: {metrics["equal_weight_common_pairs"]}; средняя абсолютная разница веса: {metrics["mean_absolute_weight_difference"]}.',
            sign_line, sign_note, '',
            'Подробные показатели: comparison.csv и summary.json. Графики: pairs.png и weights.png.',
            'Сравниваются только одинаковые ID; кандидаты переименованных ID не применяются. Одинаковый ID сам по себе не доказывает биологическую идентичность.',
            'Происхождение выбранной таблицы связей и эквивалентность правил отбора не подтверждены. Сравнение графов не является воспроизведением модели или статьи.',
            'Вес в выбранной таблице суммируется по областям; корреляция и график весов касаются только общих пар. График показывает выборку.']
        (output / 'report.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return {'status': 'ok', 'scope': 'Сравнение связности по одинаковым ID, не воспроизведение модели или статьи.',
                'source': SOURCE, 'inputs': hashes, 'author_git_blob_matches_reference': exact,
                'metrics': metrics, 'sign_comparison': sign, 'graph_sample_size': len(sample),
                'files': ['report.txt', 'comparison.csv', 'pairs.png', 'weights.png'],
                'caveats': ['Рассматриваются только ID, точно совпавшие в списке авторов и среди концов связей Princeton. Одинаковый ID не доказывает биологическую идентичность.',
                            'Три предлагаемых соответствия изменённых ID не применяются; несовпавшие нейроны и их связи исключены из парного сравнения.',
                            'Происхождение и версия выбранной пользователем таблицы Princeton не проверяются. Строки по областям суммируются по направленной паре. Сравнение знаков и весов не проверяет эквивалентность классификации, правил фильтрации или динамики модели.',
                            'Авторская версия установлена по Git blob SHA-1 только при обоих совпадениях; при несовпадении файл имеет неподтверждённое происхождение.',
                            'Коэффициент корреляции рассчитан только по общим парам, без отсутствующих связей. График весов показывает детерминированную выборку этих пар.']}
    finally:
        if db is not None:
            db.close()
        shutil.rmtree(scratch, ignore_errors=True)


def main():
    run = os.environ.get('FLY_RUN_DIR', '').strip()
    if not run:
        print('FLY_RUN_DIR не задан. Запустите сравнение из приложения.', file=sys.stderr)
        return 2
    output = Path(run); output.mkdir(parents=True, exist_ok=True)
    try:
        report = compare(output)
        code = 0
    except Exception as exc:
        report = {'status': 'error', 'scope': 'Сравнение не завершено; результатов нет.', 'error': f'{type(exc).__name__}: {exc}', 'files': []}
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        code = 1
    with (output / 'summary.json').open('w', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(f'Сравнение: {report["status"]}. Отчёт: {output / "summary.json"}', flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
