"""Сверка пробного MN9-контроля с неизменённым model.py авторов на v630.

По умолчанию только проверка файлов; --simulate явно запускает один повтор.
Не выполняет лезию и не воспроизводит всю Figure 1.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

SOURCE = 'https://github.com/philshiu/Drosophila_brain_model/blob/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960/model.py'
AUTHOR_MODEL_SHA256 = 'fc45837d7122c6ce2a7f3f2f23c515992e4b232aadb919efabb72337fac88e4e'
EXPECTED = {'connections': '8b4d9531bc0acbda7c2074ae577e6ac9e2fca166',
            'neurons': 'be745f0ce054308df21accc5c4b3883aa38498f9'}
LEFT = ['720575940620589838','720575940631147148','720575940608305161','720575940629388135','720575940630968335','720575940606801282','720575940617398502','720575940616167218','720575940620296641','720575940627961104']
MN9 = {'left': '720575940660219265', 'right': '720575940645521262'}


def get_file(key, ext):
    value = os.environ.get(key, '').strip()
    if not value:
        raise ValueError(f'{key} не выбран в «Данные и окружение».')
    f = Path(value)
    if not f.is_file() or not f.name.lower().endswith(ext):
        raise ValueError(f'{key}: нужен доступный файл {ext}: {f}')
    return f


def fingerprint(path):
    before = path.stat()
    sha = hashlib.sha256()
    git = hashlib.sha1(f'blob {before.st_size}\0'.encode())
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(2 * 1024 * 1024), b''):
            sha.update(block); git.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError(f'Файл изменился во время чтения: {path}')
    return {'path': str(path), 'bytes': before.st_size, 'mtime_ns': before.st_mtime_ns,
            'sha256': sha.hexdigest(), 'git_blob_sha1': git.hexdigest()}


def load_author(path):
    signature = fingerprint(path)
    if signature['sha256'] != AUTHOR_MODEL_SHA256:
        raise ValueError('Файл 26_shiu_author_model.py отличается от закреплённого model.py авторов.')
    spec = importlib.util.spec_from_file_location('shiu_original_model', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, signature


def simulate(author, comp, conn, lookup, args):
    import brian2 as b2
    b2.start_scope()
    b2.prefs.codegen.target = 'numpy'
    b2.defaultclock.dt = 0.1 * b2.ms
    params = dict(author.default_params)
    params['r_poi'] = args.frequency_hz * b2.Hz
    # Неизменённые функции create_model и poi из model.py. Как в run_trial,
    # после создания модели собираем Network без лезий и запускаем на 1 сек.
    print('Авторский model.py создаёт полный граф и монитор всех спайков...', flush=True)
    neu, syn, monitor = author.create_model(comp, conn, params)
    targets = [lookup[x] for x in LEFT]
    pois, neu = author.poi(neu, targets, [], params)
    syn = author.silence([], syn)
    net = b2.Network(neu, syn, monitor, *pois)
    b2.seed(args.seed)
    print('Выполняется один контроль без лезий...', flush=True)
    start = time.time()
    net.run(duration=1000*b2.ms, namespace={})
    elapsed = time.time() - start
    result = {'seed': args.seed, 'left_mn9_rate_hz': int(monitor.count[lookup[MN9['left']]]),
              'right_mn9_rate_hz': int(monitor.count[lookup[MN9['right']]]),
              'stimulus_rates_hz': [int(monitor.count[i]) for i in targets],
              'duration_ms': 1000, 'dt_ms': 0.1, 'wall_seconds': round(elapsed, 3),
              'brian2': b2.__version__, 'backend': 'numpy'}
    # Спайковые времена монитором записаны, как в авторском коде, но файл для
    # них не создаётся: сравниваем только нужные числа MN9 и sugar GRN.
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulate', action='store_true')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--frequency-hz', type=float, default=100.0)
    args = parser.parse_args()
    dest = os.environ.get('FLY_RUN_DIR', '').strip()
    if not dest:
        print('FLY_RUN_DIR не задан. Запустите из приложения.', file=sys.stderr)
        return 2
    out = Path(dest); out.mkdir(parents=True, exist_ok=True)
    report = {'status': 'pending', 'mode': 'simulation' if args.simulate else 'preflight',
              'scope': 'Сверка одного пробного запуска с функциями авторского model.py, без лезий.',
              'args': vars(args), 'author_source': SOURCE, 'files': [],
              'caveats': [
                  'Авторские функции create_model, poi и silence не изменены. Сеть собирается отдельно для установки seed, backend и извлечения чисел спайков.',
                  '10 левых sugar GRN из авторского ноутбука. Различие стороны между статьёй и ноутбуком остаётся открытым.',
                  'Один повтор не характеризует изменчивость и не является проверкой полного воспроизведения Figure 1.',
                  'Спайковые времена записываются в память авторским монитором, но не сохраняются в файл.']}
    try:
        if not 0 <= args.seed <= 2**32-1 or not math.isfinite(args.frequency_hz) or not 0 < args.frequency_hz <= 200:
            raise ValueError('Укажите допустимый seed и частоту (0, 200] Гц.')
        conn = get_file('FLY_SHIU_CONNECTIONS', '.parquet')
        comp = get_file('FLY_SHIU_NEURONS', '.csv')
        print('Проверяем контрольные суммы авторских файлов...', flush=True)
        hashes = {'connections': fingerprint(conn), 'neurons': fingerprint(comp)}
        report['inputs'] = hashes
        report['author_git_blob_matches_reference'] = {k: hashes[k]['git_blob_sha1'] == v for k, v in EXPECTED.items()}
        if not all(report['author_git_blob_matches_reference'].values()):
            raise ValueError('Данные не совпадают с закреплёнными авторскими файлами v630.')
        model = Path(__file__).parent / '26_shiu_author_model.py'
        author, model_info = load_author(model)
        report['author_model'] = model_info
        with comp.open('r', encoding='utf-8-sig', newline='') as file:
            rows = csv.reader(file)
            header = next(rows)
            ids = [row[0].strip() for row in rows if row]
        if not header or not ids or len(set(ids)) != len(ids) or not all(x.isdigit() and int(x) > 0 for x in ids):
            raise ValueError('Авторский список нейронов имеет некорректные или повторные ID.')
        lookup = {value: index for index, value in enumerate(ids)}
        missing = [x for x in LEFT + list(MN9.values()) if x not in lookup]
        if missing:
            raise ValueError('Нет необходимых ID: ' + ', '.join(missing))
        for key, f in [('connections', conn), ('neurons', comp)]:
            stat = f.stat(); info = hashes[key]
            if (stat.st_size, stat.st_mtime_ns) != (info['bytes'], info['mtime_ns']):
                raise ValueError(f'Файл изменился во время чтения: {f}')
        report['data_check'] = {'neurons': len(ids), 'stimulation_ids': LEFT, 'mn9_ids': MN9}
        if args.simulate:
            result = simulate(author, comp, conn, lookup, args)
            report['result'] = result
            report['status'] = 'ok'; report['files'] = ['report.txt']
            (out / 'report.txt').write_text(
                'Сверка с оригинальными функциями model.py\n'
                f"Левая сторона, {args.frequency_hz} Гц, seed {args.seed}, 1 секунда.\n"
                f"MN9 слева: {result['left_mn9_rate_hz']} Гц; справа: {result['right_mn9_rate_hz']} Гц.\n"
                'Без лезий. Сравните с контрольным запуском 25_shiu_v630_control.py при тех же параметрах.\n', encoding='utf-8')
        else:
            report['status'] = 'preflight_complete'
        code = 0
    except Exception as exc:
        report['status'] = 'error'; report['error'] = f'{type(exc).__name__}: {exc}'
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        code = 1
    with (out / 'summary.json').open('w', encoding='utf-8') as file:
        json.dump(report, file, ensure_ascii=False, indent=2, allow_nan=False)
    print(f'Сверка авторского кода: {report["status"]}. Отчёт: {out / "summary.json"}', flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
