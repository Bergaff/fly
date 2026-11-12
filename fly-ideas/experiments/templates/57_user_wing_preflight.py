#!/usr/bin/env python3
"""Read-only input snapshot for a future long user-wing study.

NOT a runner or user-facing launcher. It retrieves the training and regression
inputs from a verified completed series 51 and freezes separate new test files.
The caller must persist the returned bytes atomically before training.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = {
    '53_long_user_wing_stimuli.py': 'c83be62e18636beaf82f343ce25eb8a67e01c1a97f2374b950793a2f19ca4f1b',
    '56_user_wing_evaluation.py': 'b4378b1ed9b63a5ebf863915dd67fbdc1a9252bd34691a9fdc255a8002bd84f5',
}
MAX_JSON = 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load(filename, name):
    path = HERE / filename
    if digest(path.read_bytes()) != PIN[filename]:
        raise ValueError(f'Закреплённый модуль {filename} изменился.')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_limited(path, limit):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError(f'Файл отсутствует или слишком велик: {path.name}.')
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError(f'Файл слишком велик: {path.name}.')
    return raw


def prepare(previous_folder, fresh_test_paths):
    """Return immutable source bytes and role labels; does not create files.

    The old manifest must match its completed metadata; every saved old input
    must match its source and sampled-motion hashes. New tests cannot duplicate
    any old input or each other, including old training motions. Equality is of
    complete sampled motions only, not visual histories or fragments.
    """
    stim = load('53_long_user_wing_stimuli.py', 'preflight_stim')
    ev = load('56_user_wing_evaluation.py', 'preflight_eval')
    folder = Path(previous_folder)
    if not 1 <= len(fresh_test_paths) <= 19:
        raise ValueError('Выберите от 1 до 19 новых проверочных JSON.')
    model, model_hash = ev.load_series51_model(folder)
    del model
    metadata_raw = read_limited(folder / 'metadata.json', MAX_JSON)
    metadata = json.loads(metadata_raw.decode('utf-8-sig'))
    manifest_raw = read_limited(folder / 'input_manifest.json', MAX_JSON)
    if metadata.get('status') != 'completed' or metadata.get('model_sha256') != model_hash or metadata.get('manifest_sha256') != digest(manifest_raw):
        raise ValueError('Метаданные модели и манифест не совпадают.')
    model_raw = read_limited(folder / 'model_six_axes.npz', ev.MAX_ARCHIVE)
    if digest(model_raw) != model_hash:
        raise ValueError('Модель изменилась во время чтения.')
    manifest = json.loads(manifest_raw.decode('utf-8-sig'))
    items = manifest.get('inputs')
    if manifest.get('schema') != 'wing-user-inputs-v1' or not isinstance(items, list):
        raise ValueError('Неверный манифест предыдущей серии.')
    sources = {'baseline_metadata.json': metadata_raw, 'baseline_manifest.json': manifest_raw,
               'baseline_model.npz': model_raw}
    labels = []
    seen = {}
    counts = {'train': 0, 'test': 0}
    for entry in items:
        if not isinstance(entry, dict) or entry.get('role') not in counts:
            raise ValueError('Неверная роль в манифесте.')
        role = entry['role']
        counts[role] += 1
        number = counts[role]
        expected = f'{role}_{number:03d}.json'
        if entry.get('id') != number or entry.get('copy') != f'input/{expected}':
            raise ValueError('Порядок или имя копии в манифесте нарушены.')
        raw = read_limited(folder / 'input' / expected, MAX_JSON)
        _, angles = stim.sample_trajectory(json.loads(raw.decode('utf-8-sig')))
        motion = stim.motion_hash(angles)
        if digest(raw) != entry.get('source_sha256') or motion != entry.get('sampled_motion_sha256'):
            raise ValueError(f'Копия {expected} отличается от манифеста.')
        if motion in seen:
            raise ValueError('В прошлой серии повторяются полные движения.')
        seen[motion] = expected
        sources[expected] = raw
        labels.append({'copy': expected, 'role': 'train' if role == 'train' else 'regression',
                       'source_sha256': digest(raw), 'motion_sha256': motion})
    if not 2 <= counts['train'] <= 50 or not 1 <= counts['test'] <= 20:
        raise ValueError('В старом запуске нужны 2–50 обучающих и 1–20 проверочных JSON.')
    if counts['test'] + len(fresh_test_paths) > 20:
        raise ValueError('Всего допустимо не более 20 проверочных движений.')
    for index, path in enumerate(fresh_test_paths, 1):
        raw = read_limited(path, MAX_JSON)
        _, angles = stim.sample_trajectory(json.loads(raw.decode('utf-8-sig')))
        motion = stim.motion_hash(angles)
        if motion in seen:
            raise ValueError(f'Новое проверочное движение {index} полностью совпадает с {seen[motion]}.')
        name = f'test_{counts["test"] + index:03d}.json'
        seen[motion] = name
        sources[name] = raw
        labels.append({'copy': name, 'role': 'new_test', 'source_sha256': digest(raw),
                       'motion_sha256': motion, 'original_basename': Path(path).name})
    if len(sources) > 80 or sum(map(len, sources.values())) > 64 * 1024 * 1024:
        raise ValueError('Слишком большой набор данных для контрольной точки.')
    return {'sources': sources, 'labels': labels, 'baseline_model_sha256': model_hash,
            'source_sha256': {name: digest(raw) for name, raw in sorted(sources.items())},
            'limitations': ['Only exact whole-motion duplicates are excluded.',
                            'The former test is regression, not new or blind.',
                            'New tests are user-selected and may share similar fragments.']}
