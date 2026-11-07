"""Проверка двух выбранных лезий на семи дополнительных частотах v630.

Исходные 90 повторов при 50 Гц читаются из снимков. Новая база отдельная,
каждый повтор фиксируется транзакцией. Запуск только по явному frequency-run.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sqlite3
import statistics
import sys
import time
import traceback
import uuid

PILOT_SHA = '857c8428d7daee57304cffe35daa6330c0a18a70c6ca631df9b569c8f0731fc0'
TARGETS = ['720575940622695448', '720575940623211725']
FREQUENCIES = [60, 70, 80, 90, 100, 110, 120]
SEEDS = list(range(30))
MODE = 'shiu-two-lesions-frequencies-v1'


def load_pilot():
    path = Path(__file__).parent / '33_shiu_individuality_pilot.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest() != PILOT_SHA:
        raise ValueError('Код проверки источника изменён; запуск остановлен.')
    spec = importlib.util.spec_from_file_location('frequency_source_pilot', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def code_hash():
    return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def source_50(pilot, shared, view, selected_module, study, manifest, out):
    if any(t not in manifest['selected'] for t in TARGETS) or len(set(TARGETS)) != 2:
        raise ValueError('В выбранном наборе нет обеих заранее выбранных клеток.')
    source = study / shared.SELECTED_DIR / 'selected_lesions.sqlite3'
    control_source = study / shared.CONTROL_DIR / 'lesions.sqlite3'
    if any(p.is_symlink() or not p.is_file() for p in (source, control_source)):
        raise ValueError('Исходные базы 50 Гц отсутствуют или являются ссылками.')
    with shared.lock(study):
        view.snapshot(control_source, out / 'controls_50_snapshot.sqlite3')
        view.snapshot(source, out / 'selected_lesions.sqlite3')
    meta, controls = view.read_checked(out / 'controls_50_snapshot.sqlite3')
    if meta != manifest['source_protocol'] or len(controls) != 30 or {(r[0], r[1], r[2]) for r in controls} != {(50, '', s) for s in SEEDS}:
        raise ValueError('Нужны 30 проверенных контролей 50 Гц этого набора.')
    top = view.read_top(study / shared.TOP_DIR, meta)
    base = view.reference().load_top().base_module()
    selected, pairs = selected_module.selection(meta, base)
    if selected != manifest['selected'] or pairs != manifest['pairs']:
        raise ValueError('Выборка не совпадает с манифестом.')
    protocol = shared.selected_protocol(selected_module, view, meta, selected, pairs)
    verify = out / 'verify_selected'
    verify.mkdir()
    checked = selected_module.open_selected(verify, protocol, out)
    try:
        keys = ['control'] + ['single:' + t for t in TARGETS]
        rows = checked.execute('SELECT condition,seed,left_count,right_count,wall_seconds,origin,digest FROM trials ORDER BY condition,seed').fetchall()
        baseline = [r for r in rows if r[0] in keys]
    finally:
        checked.close()
    if len(baseline) != 90 or {(r[0], r[1]) for r in baseline} != {(k, s) for k in keys for s in SEEDS}:
        raise ValueError('Нужны все 90 проверенных повторов контроля и двух лезий при 50 Гц.')
    orig = {r[2]: (r[3], r[4]) for r in controls}
    if any((r[2], r[3]) != orig[r[1]] for r in baseline if r[0] == 'control'):
        raise ValueError('Контроли в двух базах 50 Гц не совпадают.')
    return meta, baseline, top


def make_protocol(pilot, study, meta, baseline):
    return {'kind': MODE, 'study_id': study.name, 'source_protocol': meta,
            'source_50_rows_sha256': pilot.stable_hash(baseline), 'script_sha256': code_hash(),
            'targets': TARGETS, 'frequencies_new_hz': FREQUENCIES, 'source_frequency_hz': 50,
            'seeds': SEEDS, 'duration_ms': 1000, 'dt_ms': 0.1,
            'selection': 'Клетки выбраны после просмотра результатов при 50 Гц; новые частоты являются исследовательской проверкой.',
            'comparison': 'Средняя частота левого MN9 и отношение к среднему контролю на той же частоте. Правый MN9 описательно.',
            'caveat': 'Одинаковые seed не гарантируют совпадение входных спайков. Лезия обнуляет исходящие веса.'}


def data_dir(shared_root, study_id, create):
    root = Path(shared_root).parent / 'shiu-v630-frequency-check'
    if create:
        root.mkdir(exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Папка проверки частот отсутствует или является ссылкой.')
    folder = root / study_id
    if create:
        folder.mkdir(exist_ok=True)
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError('Проверка частот ещё не начата или папка является ссылкой.')
    return folder


def row_hash(pilot, f, target, seed, left, right, seconds):
    return pilot.stable_hash([f, target, seed, left, right, float(seconds).hex()])


def open_db(pilot, folder, protocol, create):
    path = folder / 'frequencies.sqlite3'
    if path.is_symlink():
        raise ValueError('База проверки не должна быть ссылкой.')
    exists = path.is_file()
    if not exists and not create:
        raise ValueError('Проверка частот ещё не начата.')
    db = sqlite3.connect(path, timeout=30)
    db.execute('PRAGMA synchronous=FULL')
    try:
        if not exists:
            db.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE trials(frequency INTEGER NOT NULL,target TEXT NOT NULL,seed INTEGER NOT NULL,left_count INTEGER NOT NULL,right_count INTEGER NOT NULL,wall_seconds REAL NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(frequency,target,seed));')
            db.execute('INSERT INTO metadata VALUES(?,?)', ('protocol', json.dumps(protocol, ensure_ascii=False, sort_keys=True)))
            db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('База проверки повреждена.')
        records = db.execute('SELECT value FROM metadata WHERE key=?', ('protocol',)).fetchall()
        if len(records) != 1 or json.loads(records[0][0]) != protocol:
            raise ValueError('Источник или протокол изменился; продолжение остановлено.')
        rows = db.execute('SELECT frequency,target,seed,left_count,right_count,wall_seconds,digest FROM trials').fetchall()
        seen = set()
        for f, target, seed, left, right, seconds, digest in rows:
            key = (f, target, seed)
            if (key in seen or f not in FREQUENCIES or target not in ['', *TARGETS] or seed not in SEEDS or
                type(left) is not int or type(right) is not int or not 0 <= left <= 10000 or not 0 <= right <= 10000 or
                not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or seconds < 0 or
                digest != row_hash(pilot, f, target, seed, left, right, seconds)):
                raise ValueError('Некорректный повтор в базе проверки частот.')
            seen.add(key)
        return db
    except Exception:
        db.close()
        raise


def backup(folder, db, count):
    directory = folder / 'backups'
    directory.mkdir(exist_ok=True)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('Папка резервных снимков не должна быть ссылкой.')
    path = directory / f'frequency_{count:04d}_{time.strftime("%Y%m%d_%H%M%S")}_{uuid.uuid4().hex[:6]}.sqlite3'
    with path.open('xb'):
        pass
    try:
        with sqlite3.connect(path, timeout=30) as dest:
            db.backup(dest)
    except Exception:
        path.unlink(missing_ok=True)
        raise


def report(pilot, view, out, protocol, baseline, rows, status, top):
    all_rows = [(50, '' if key == 'control' else key.split(':', 1)[1], seed, left, right, seconds, 'source_50')
                for key, seed, left, right, seconds, _origin, _digest in baseline]
    all_rows += [(f, t, s, l, r, sec, 'new') for f, t, s, l, r, sec, _ in rows]
    all_rows.sort(key=lambda r: (r[0], r[1], r[2]))
    fields = ['frequency_hz', 'target', 'seed', 'left_count', 'right_count', 'wall_seconds', 'origin']
    pilot.write_csv(out / 'frequency_trials.csv', fields, [dict(zip(fields, r)) for r in all_rows])
    groups = {(f, t): [r for r in all_rows if r[0] == f and r[1] == t] for f in [50, *FREQUENCIES] for t in ['', *TARGETS]}
    summary = []
    for f in [50, *FREQUENCIES]:
        ctrl = groups[(f, '')]
        c = statistics.mean(r[3] for r in ctrl) if len(ctrl) == 30 else None
        for target in ['', *TARGETS]:
            values = groups[(f, target)]
            left = statistics.mean(r[3] for r in values) if values else None
            right = statistics.mean(r[4] for r in values) if values else None
            complete = len(values) == 30
            ratio = left / c if target and complete and c not in (None, 0) else None
            summary.append({'frequency_hz': f, 'target': target or 'control', 'rank_200hz': top[target]['rank'] if target else '',
                            'trials': len(values), 'expected': 30, 'complete': complete,
                            'left_mean_hz': left if left is not None else '', 'left_sd_hz': statistics.stdev(r[3] for r in values) if len(values) > 1 else '',
                            'right_mean_hz': right if right is not None else '', 'right_sd_hz': statistics.stdev(r[4] for r in values) if len(values) > 1 else '',
                            'control_complete': len(ctrl) == 30, 'left_ratio_to_control': ratio if ratio is not None else '',
                            'left_le_80_percent': ('yes' if ratio <= 0.8 else 'no') if ratio is not None else 'undefined'})
    pilot.write_csv(out / 'frequency_conditions.csv', list(summary[0]), summary)
    complete = len(rows) == 630
    lines = ['ПРОВЕРКА ДВУХ ЛЕЗИЙ НА ДРУГИХ ЧАСТОТАХ',
             f'Состояние: {status}; новые повторы {len(rows)}/630; исходные 50 Гц: 90/90.',
             'Две клетки выбраны после просмотра 50 Гц; проверка дополнительных частот исследовательская.',
             '21 правый GRN, 1 с, dt 0,1 мс. На каждой частоте: 30 контролей и по 30 повторов каждой лезии.',
             'Отношение считается только для полных 30 контролей и 30 лезий на одной частоте.',
             '', 'Гц | условие | повторов | левый MN9, Гц | правый MN9, Гц | % контроля слева']
    for item in summary:
        fmt = lambda x: '-' if x == '' else f'{x:.2f}'
        ratio = '-' if item['left_ratio_to_control'] == '' else f"{100 * item['left_ratio_to_control']:.1f}%"
        lines.append(f"{item['frequency_hz']} | {item['target']} | {item['trials']}/30 | {fmt(item['left_mean_hz'])} | {fmt(item['right_mean_hz'])} | {ratio}")
    lines.extend(['', 'Порог 80% описывает отношение средних на одной частоте, это не тест значимости.',
                  'Неполные условия не следует сравнивать; общий вывод по частотам возможен только после завершения всех условий.',
                  'Один коннектом, модельные повторы не животные; одинаковый seed не гарантирует совпадение входных спайков.',
                  'Клетки выбраны post hoc по 50 Гц; это не полное воспроизведение классификации Shiu.'])
    (out / 'report.txt').write_text('\n'.join(lines) + '\n', encoding='utf8')
    view.atomic_json(out / 'frozen_plan.json', protocol)
    files = ['report.txt', 'frozen_plan.json', 'frequency_conditions.csv', 'frequency_trials.csv', 'controls_50_snapshot.sqlite3', 'selected_lesions.sqlite3']
    if (out / 'frequencies_snapshot.sqlite3').is_file():
        files.append('frequencies_snapshot.sqlite3')
    view.atomic_json(out / 'summary.json', {'status': status, 'mode': MODE, 'study_id': protocol['study_id'],
        'baseline_50_trials': len(baseline), 'new_completed': len(rows), 'new_planned': 630,
        'all_frequencies_complete': complete, 'files': files})
    print('\n'.join(lines), flush=True)


def execute(pilot, shared, view, module, study, manifest, out, stage):
    meta, baseline, top = source_50(pilot, shared, view, module, study, manifest, out)
    protocol = make_protocol(pilot, study, meta, baseline)
    if stage == 'frequency-plan':
        report(pilot, view, out, protocol, baseline, [], 'plan_ready', top)
        return
    folder = data_dir(os.environ['FLY_SHIU_SHARED_ROOT'], study.name, stage == 'frequency-run')
    with shared.lock(folder):
        db = open_db(pilot, folder, protocol, stage == 'frequency-run')
        try:
            if stage == 'frequency-run':
                have = {(f, t, s) for f, t, s in db.execute('SELECT frequency,target,seed FROM trials')}
                print(f'Отдельная база {folder}; сохранено новых {len(have)}/630.', flush=True)
                stop = out / 'stop.request'
                if len(have) < 630 and not stop.exists():
                    pilot.check_memory()
                    lesion, base, data = module.validate_simulation(meta, study / shared.TOP_DIR)
                    for frequency in FREQUENCIES:
                        for target in ['', *TARGETS]:
                            for seed in SEEDS:
                                if stop.exists():
                                    break
                                if (frequency, target, seed) in have:
                                    continue
                                pilot.check_memory()
                                print(f'{frequency} Гц, {target or "контроль"}, seed {seed}: новый повтор {len(have)+1}/630.', flush=True)
                                left, right, seconds = lesion.trial(base, data, frequency, seed, target)
                                digest = row_hash(pilot, frequency, target, seed, left, right, seconds)
                                db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)', (frequency, target, seed, left, right, seconds, digest))
                                db.commit()
                                have.add((frequency, target, seed))
                                view.atomic_json(out / 'progress.json', {'new_completed': len(have), 'new_total': 630, 'frequency_hz': frequency, 'target': target, 'seed': seed})
                                if len(have) % 30 == 0:
                                    backup(folder, db, len(have))
                            if stop.exists():
                                break
                        if stop.exists():
                            break
                backup(folder, db, len(have))
            rows = db.execute('SELECT frequency,target,seed,left_count,right_count,wall_seconds,digest FROM trials ORDER BY frequency,target,seed').fetchall()
            with sqlite3.connect(out / 'frequencies_snapshot.sqlite3') as copy:
                db.backup(copy)
            status = 'complete' if len(rows) == 630 else 'stopped' if stage == 'frequency-run' and (out / 'stop.request').exists() else 'partial'
            report(pilot, view, out, protocol, baseline, rows, status, top)
        finally:
            db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['frequency-plan', 'frequency-run', 'frequency-review'], required=True)
    parser.add_argument('--study', required=True)
    args = parser.parse_args()
    out = Path(os.environ['FLY_RUN_DIR'])
    out.mkdir(parents=True, exist_ok=True)
    try:
        pilot = load_pilot()
        shared = pilot.load_shared()
        module, view = shared.modules()
        study = shared.study_path(os.environ['FLY_SHIU_SHARED_ROOT'], args.study)
        manifest = shared.read_manifest(study)
        execute(pilot, shared, view, module, study, manifest, out, args.stage)
        return 0
    except Exception as exc:
        out.joinpath('summary.json').write_text(json.dumps({'status': 'error', 'mode': args.stage, 'error': f'{type(exc).__name__}: {exc}', 'files': ['progress.json'] if (out / 'progress.json').exists() else []}, ensure_ascii=False, indent=2), encoding='utf8')
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        return 1

if __name__ == '__main__':
    sys.exit(main())
