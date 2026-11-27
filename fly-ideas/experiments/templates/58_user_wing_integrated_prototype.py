#!/usr/bin/env python3
"""Developer-only integrated short study, limited to 2–8 candidates.

Exercises the frozen 51 baseline, separate tests, transactional training,
process restart, a pause request between batches, and paired evaluation.
Not a 4–8 hour runner or a BAT.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import csv
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import multiprocessing
import os
from pathlib import Path
import platform
import sqlite3
import sys
import time
import uuid
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
import numpy as np

HERE = Path(__file__).resolve().parent
PIN = {
    '55_user_wing_resume_prototype.py': '81e491eb489c46b4729440763ebb2f1590b532bc31fd438917206cdfabd8148e',
    '56_user_wing_evaluation.py': 'b4378b1ed9b63a5ebf863915dd67fbdc1a9252bd34691a9fdc255a8002bd84f5',
    '57_user_wing_preflight.py': '9395171ff29f134ddfe1c9afa84049b817f9658d203253edfd08a645556f0b2e',
}
AXES = ('left_x', 'left_y', 'left_z', 'right_x', 'right_y', 'right_z')


def sha(raw): return hashlib.sha256(raw).hexdigest()
def file_sha(path): return sha(Path(path).read_bytes())


def load(filename, name):
    p = HERE / filename
    if file_sha(p) != PIN[filename]: raise ValueError(f'Закреплённый файл {filename} изменился.')
    spec = importlib.util.spec_from_file_location(name, p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dependencies():
    proto = load('55_user_wing_resume_prototype.py', 'integrated_proto')
    ev = load('56_user_wing_evaluation.py', 'integrated_eval')
    pre = load('57_user_wing_preflight.py', 'integrated_preflight')
    stim, ck, base, large = proto.modules()
    return proto, ev, pre, stim, ck, base, large


def make_protocol(sources_sha, labels, limit, proto):
    return {'schema': 'user-wing-integrated-prototype-v1', 'mode': 'developer-only',
            'limit': limit, 'workers': 2, 'batch': 2,
            'script_sha256': file_sha(__file__), 'dependencies': {**proto.PIN, **PIN},
            'python': platform.python_version(),
            'versions': {p: importlib.metadata.version(p) for p in ('numpy', 'mujoco', 'brian2', 'pillow')},
            'source_sha256': sources_sha, 'labels': labels}


WORKER = None

def worker_init(train, hold):
    global WORKER
    WORKER = load('55_user_wing_resume_prototype.py', 'integrated_worker_proto')
    WORKER.worker_init(train, hold)


def worker_generate(ident): return WORKER.generate(ident)


def start(folder, previous, fresh, limit, max_batches=None):
    if type(limit) is not int or not 2 <= limit <= 8:
        raise ValueError('Прототип ограничен 2–8 кандидатами.')
    if max_batches is not None and (type(max_batches) is not int or not 1 <= max_batches <= 4):
        raise ValueError('Прототип допускает 1–4 партии за вызов.')
    proto, ev, pre, stim, ck, base, large = dependencies()
    snapshot = pre.prepare(previous, fresh)
    proto.split_from_sources(snapshot['sources'], stim)
    protocol = make_protocol(snapshot['source_sha256'], snapshot['labels'], limit, proto)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=False)
    ck.create(folder / 'integrated.sqlite3', protocol, snapshot['sources'])
    process(folder, max_batches)


def check_pins(proto, saved):
    if file_sha(__file__) != saved['script_sha256']: raise ValueError('Прототип изменился; запись остановлена.')
    for name, expected in {**proto.PIN, **PIN}.items():
        if file_sha(HERE / name) != expected: raise ValueError(f'Зависимость {name} изменилась; запись остановлена.')


def read_model(raw, ev):
    with np.load(io.BytesIO(raw), allow_pickle=False) as data:
        return ev.checked_model({key: data[key] for key in data.files})


def records_for_audit(dbpath):
    with sqlite3.connect(Path(dbpath).resolve().as_uri() + '?mode=ro', uri=True) as db:
        rows = db.execute('SELECT id,status,spec,motion_sha256 FROM candidates ORDER BY id').fetchall()
    return [{'id': i, 'status': status, 'spec': json.loads(spec), 'motion_sha256': motion} for i, status, spec, motion in rows]


def save_json(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def evaluate(folder, state, saved, proto, ev, stim, base):
    """Publish result directory only after complete evaluation.

    Previous incomplete attempt directories are retained. If result already
    exists, refuse to overwrite or declare it valid without verification.
    """
    folder = Path(folder)
    output = folder / 'result'
    if output.exists():
        raise ValueError('Результат уже существует; он не перезаписывается.')
    if state['stats']['n'] < 2: raise ValueError('Недостаточно принятых кадров обучения.')
    train, tests = proto.split_from_sources(state['sources'], stim)
    labels = {item['copy']: item for item in saved['labels']}
    old = read_model(state['sources']['baseline_model.npz'], ev)
    mean, scale, intercept, weights = base.fit(state['stats'])
    new = ev.checked_model({'mean': mean, 'scale': scale, 'intercept': intercept, 'weights': weights})
    studio = proto.load('integrated_studio', '50_two_flies_wing_studio_pilot.py')
    engine = proto.load('integrated_engine', '38_two_flies_observation.py')
    scene = studio.Scene(engine)
    records = records_for_audit(folder / 'integrated.sqlite3')
    audit = ev.overlap_sample(stim, train, tests, records, cap=128)
    temp = folder / ('evaluation_incomplete_' + uuid.uuid4().hex)
    temp.mkdir()
    np.savez_compressed(temp / 'model_new.npz', **new)
    summary = []
    for item, overlap in zip(tests, audit['tests']):
        ident = item['id']; label = labels[f'test_{ident:03d}.json']
        truth = item['angles_deg'] * np.pi / 180
        images = scene.render(truth)
        compared = ev.compare_models(images, truth, old, new)
        testdir = temp / f'test_{ident:03d}'
        testdir.mkdir()
        with (testdir / 'predictions.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['time_s'] + [f'teacher_{a}_rad' for a in AXES] +
                            [f'{model}_{a}_rad' for model in ('old','new','zero','training_mean') for a in AXES])
            for k, t in enumerate(item['times'][2:]):
                writer.writerow([float(t), *map(float, compared['teacher_rad'][k]),
                                 *(float(v) for name in ('old','new','zero','training_mean') for v in compared['predictions'][name][k])])
        result = {'test_id': ident, 'role': label['role'], 'frames': len(truth)-2,
                  'metrics': compared['metrics'],
                  'overlap_under_0_001_deg': overlap['under_0_001_deg'],
                  'overlap_under_1_deg': overlap['under_1_deg'], 'overlap_under_5_deg': overlap['under_5_deg']}
        summary.append(result)
        save_json(testdir / 'metrics.json', result)
    summary_data = {'status': 'developer_fixture_completed', 'test_only': True,
                    'candidates': state['next_id'], 'training_frames': state['stats']['n'],
                    'active_seconds_to_last_batch': state['elapsed'],
                    'baseline_model_sha256': sha(state['sources']['baseline_model.npz']),
                    'new_model_sha256': file_sha(temp / 'model_new.npz'),
                    'audit': {'accepted_total': audit['accepted_total'], 'audited_count': audit['audited_count'],
                              'is_exhaustive': audit['is_exhaustive'], 'sample_ids': audit['sample_ids']},
                    'tests': summary,
                    'limitations': ['Техническая короткая проба, не серия 4–8 часов.',
                                    'Прежняя проверка является регрессионной; новая выбрана пользователем.',
                                    'Точное совпадение полных движений исключается, близкие фрагменты возможны.',
                                    'Аудит сравнивает углы, не зрительные входы; неполная выборка может пропустить совпадение.',
                                    'Кинематические мухи и искусственные камеры, supervised ridge; не доказательство зеркальных нейронов.']}
    save_json(temp / 'summary.json', summary_data)
    check_pins(proto, saved)
    # Same filesystem rename, while holding the run lock. Never replace a result.
    if output.exists(): raise ValueError('Результат уже существует.')
    temp.rename(output)
    return summary_data


def process(folder, max_batches=None):
    if max_batches is not None and (type(max_batches) is not int or not 1 <= max_batches <= 4):
        raise ValueError('Прототип допускает 1–4 партии за вызов.')
    proto, ev, pre, stim, ck, base, large = dependencies()
    folder = Path(folder).resolve(); dbpath = folder / 'integrated.sqlite3'
    if not dbpath.is_file(): raise ValueError('Нет базы интеграционного прототипа.')
    large.job_guard()
    with large.RunLock(folder):
        with sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True) as db:
            record = db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()
        if not record: raise ValueError('Нет протокола.')
        saved = json.loads(record[0]); limit = saved.get('limit')
        if type(limit) is not int or not 2 <= limit <= 8: raise ValueError('Неверный лимит прототипа.')
        expected = make_protocol(saved.get('source_sha256'), saved.get('labels'), limit, proto)
        state = ck.open_verified(dbpath, expected)
        train, tests = proto.split_from_sources(state['sources'], stim)
        hold = {x['motion_sha256'] for x in tests}
        done = state['next_id']; stats = state['stats']; elapsed = state['elapsed']; batches = 0
        if done > limit: raise ValueError('Позиция выше лимита.')
        if (folder / 'result').exists():
            print('Результат уже существует, повторная запись запрещена.', flush=True)
            return
        start_time = time.monotonic()
        if done < limit:
            with concurrent.futures.ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context('spawn'),
                                                        initializer=worker_init, initargs=(train,hold)) as pool:
                while done < limit and (max_batches is None or batches < max_batches):
                    pause = folder / 'pause.request'
                    if pause.exists():
                        # No work is in flight here; every earlier batch is committed.
                        # If removal fails, do not silently ignore the pause.
                        try: pause.unlink()
                        except OSError as exc: print(f'Не удалось убрать запрос паузы: {exc}', flush=True)
                        print('ПРОТОТИП НА ПАУЗЕ: последняя партия сохранена.', flush=True)
                        return
                    ids = list(range(done, min(done+2, limit)))
                    generated = list(pool.map(worker_generate, ids)); records = []
                    for ident, (rec, x, y) in zip(ids, generated):
                        expected_spec, _ = stim.candidate(train, ident)
                        if rec['id'] != ident or rec['spec'] != expected_spec or rec['motion_sha256'] != expected_spec['sampled_motion_sha256']:
                            raise ValueError('Кандидат не соответствует плану.')
                        rejected = rec['motion_sha256'] in hold
                        if rejected != (rec['status'] == 'rejected'): raise ValueError('Ошибка блокировки проверочного движения.')
                        if not rejected:
                            if x is None or y is None or x.shape != (rec['frames'],576) or y.shape != (rec['frames'],6):
                                raise ValueError('Неверный размер партии.')
                            base.update_stats(stats, x, y)
                        elif x is not None or y is not None: raise ValueError('Отклонённый кандидат передал кадры.')
                        records.append(rec)
                    check_pins(proto, saved)
                    ck.commit_batch(dbpath, saved, done, records, stats, elapsed + time.monotonic()-start_time)
                    done += len(ids); batches += 1
                    print(f'Короткий прототип: сохранено {done}/{limit}', flush=True)
        if done < limit:
            print('ПРОТОТИП ОСТАНОВЛЕН: можно продолжить только сохранённые входы.', flush=True)
            return
        # Reload committed state, never evaluate uncommitted in-memory values.
        state = ck.open_verified(dbpath, saved)
        result = evaluate(folder, state, saved, proto, ev, stim, base)
        print(json.dumps(result, ensure_ascii=False), flush=True)


def request_pause(folder):
    proto, ev, pre, stim, ck, base, large = dependencies()
    folder = Path(folder).resolve(); dbpath = folder / 'integrated.sqlite3'
    if not dbpath.is_file(): raise ValueError('Нет базы прототипа.')
    try:
        with large.RunLock(folder): pass
    except ValueError:
        pass
    else:
        raise ValueError('Прототип не запущен, запрос паузы не записан.')
    with sqlite3.connect(dbpath.as_uri()+'?mode=ro', uri=True, timeout=30) as db:
        rec = db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()
        row = db.execute('SELECT next_id FROM state WHERE id=1').fetchone()
    if not rec or not row: raise ValueError('Нет состояния прототипа.')
    saved = json.loads(rec[0])
    if saved.get('mode') != 'developer-only' or row[0] >= saved.get('limit', 0):
        raise ValueError('Обучение уже закончилось; пауза доступна только во время обучения.')
    try:
        with (folder/'pause.request').open('x', encoding='utf-8') as f: f.write('pause\n')
    except FileExistsError:
        print('Запрос паузы уже записан.', flush=True); return
    print('Запрос паузы записан; если обучение ещё идёт, текущая партия будет сохранена.', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True); g.add_argument('--new'); g.add_argument('--resume'); g.add_argument('--pause')
    p.add_argument('--previous'); p.add_argument('--fresh', nargs='+'); p.add_argument('--limit', type=int, default=6); p.add_argument('--batches', type=int)
    a = p.parse_args()
    if a.new:
        if not a.previous or not a.fresh: p.error('Нужны --previous и --fresh.')
        start(a.new, a.previous, a.fresh, a.limit, a.batches)
    elif a.pause:
        if a.previous or a.fresh or a.batches is not None: p.error('Для паузы нужна только папка прототипа.')
        request_pause(a.pause)
    else:
        if a.previous or a.fresh: p.error('При продолжении используются сохранённые входы.')
        process(a.resume, a.batches)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    try: main()
    except Exception as exc:
        print(f'ОШИБКА КОРОТКОГО ПРОТОТИПА: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
