#!/usr/bin/env python3
"""Read-only analysis of a completed series-51 test; no rendering or retraining."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import os
import sys
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '1'
import numpy as np

AXES = ('left_x', 'left_y', 'left_z', 'right_x', 'right_y', 'right_z')
MAX_FILE = 32 * 1024 * 1024
MAX_UNPACKED = 64 * 1024 * 1024


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError(f'Не найден или слишком велик {path.name}.')
    return json.loads(path.read_text(encoding='utf-8-sig'))


def read_npz(path, keys):
    if not path.is_file() or path.stat().st_size > MAX_FILE:
        raise ValueError(f'Не найден или слишком велик {path.name}.')
    with zipfile.ZipFile(path) as z:
        if sum(item.file_size for item in z.infolist()) > MAX_UNPACKED:
            raise ValueError(f'Содержимое {path.name} слишком велико.')
    with np.load(path, allow_pickle=False) as data:
        if set(data.files) != set(keys):
            raise ValueError(f'Неверный состав {path.name}.')
        return {key: np.array(data[key], copy=True) for key in keys}


def motion(path):
    obj = read_json(path)
    if not isinstance(obj, dict) or obj.get('schema') != 'fly-wings-trajectory-v1' or obj.get('fps') != 25:
        raise ValueError(f'Неподходящий формат {path.name}.')
    duration = obj.get('duration_s'); keys = obj.get('keyframes')
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not .5 <= duration <= 10 or abs(duration * 25 - round(duration * 25)) > 1e-7 or not isinstance(keys, list) or not 2 <= len(keys) <= 200:
        raise ValueError(f'Некорректная длительность или число кадров {path.name}.')
    times = []; angles = []
    for item in keys:
        if not isinstance(item, dict) or not isinstance(item.get('angles_deg'), list) or len(item['angles_deg']) != 6:
            raise ValueError(f'Некорректный кадр {path.name}.')
        values = [item.get('t'), *item['angles_deg']]
        if any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in values) or any(abs(x) > 60 for x in values[1:]):
            raise ValueError(f'Некорректные значения {path.name}.')
        times.append(values[0]); angles.append(values[1:])
    if abs(times[0]) > 1e-9 or abs(times[-1] - duration) > 1e-9 or any(b-a < 1e-6 for a,b in zip(times,times[1:])):
        raise ValueError(f'Некорректные моменты {path.name}.')
    t = np.arange(int(round(duration * 25)) + 1, dtype=float) / 25
    angles = np.asarray(angles, dtype=float)
    return t, np.stack([np.interp(t, times, angles[:, i]) for i in range(6)], axis=1)


def read_csv(path):
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError('Не найден или слишком велик user_predictions.csv.')
    header = ['time_s', *[f'teacher_{c}_rad' for c in AXES], *[f'predicted_{c}_rad' for c in AXES]]
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        if next(reader, None) != header:
            raise ValueError('Некорректные столбцы user_predictions.csv.')
        rows = list(reader)
    if not 1 <= len(rows) <= 249 or any(len(row) != 13 for row in rows):
        raise ValueError('Некорректное число строк user_predictions.csv.')
    data = np.array(rows, dtype=float)
    if not np.isfinite(data).all():
        raise ValueError('Неконечные числа в user_predictions.csv.')
    return data


def nearly(actual, expected, label, atol=1e-10):
    if actual.shape != expected.shape or not np.allclose(actual, expected, atol=atol, rtol=0):
        raise ValueError(f'Не совпадают данные: {label}. Возможно, файлы взяты из разных запусков или повреждены')
    return float(np.max(np.abs(actual - expected))) if actual.size else 0.0


def analyze(test_folder):
    folder = Path(test_folder)
    if not folder.is_dir() or len(folder.name) != 8 or not folder.name.startswith('test_') or not folder.name[5:].isdigit() or int(folder.name[5:]) < 1:
        raise ValueError('Выберите user_predictions.csv внутри папки test_001 или другой папки test_NNN.')
    ident = int(folder.name[5:]); run = folder.parent
    meta = read_json(run / 'metadata.json'); manifest = read_json(run / 'input_manifest.json')
    if meta.get('status') != 'completed' or (run / 'INCOMPLETE.txt').exists():
        raise ValueError('Запуск не помечен завершённым либо присутствует INCOMPLETE.txt.')
    if meta.get('fps') != 25 or meta.get('history_frames') != 3 or meta.get('camera_resolution') != [48,32] or manifest.get('schema') != 'wing-user-inputs-v1':
        raise ValueError('Это не поддерживаемый формат завершённой серии 51.')
    model_path = run / 'model_six_axes.npz'; manifest_path = run / 'input_manifest.json'
    if not model_path.is_file() or model_path.stat().st_size > MAX_FILE or sha(model_path) != meta.get('model_sha256') or sha(manifest_path) != meta.get('manifest_sha256'):
        raise ValueError('SHA модели или манифеста не совпадает с metadata.json.')
    entries = manifest.get('inputs')
    if not isinstance(entries, list):raise ValueError('Некорректный манифест входов.')
    matches = [x for x in entries if isinstance(x,dict) and x.get('role') == 'test' and x.get('id') == ident]
    trains = [x for x in entries if isinstance(x,dict) and x.get('role') == 'train']
    if len(matches) != 1 or not 2 <= len(trains) <= 50 or len(trains) != meta.get('train_sequences'):
        raise ValueError('Не найдена проверка или обучающие файлы в манифесте.')
    test_entry = matches[0]
    def verified_motion(entry, role):
        n = entry.get('id')
        if type(n) is not int or n < 1 or n > 50:raise ValueError('Недопустимый номер во входном манифесте.')
        expected = f'input/{role}_{n:03d}.json'
        if entry.get('copy') != expected:raise ValueError('Некорректное расположение копии траектории в манифесте.')
        path = run / 'input' / f'{role}_{n:03d}.json'
        if not path.is_file() or path.stat().st_size > 1024 * 1024 or sha(path) != entry.get('source_sha256'):
            raise ValueError(f'Копия {role}_{n:03d}.json отсутствует или её SHA не совпадает.')
        return motion(path)
    if len({x.get('id') for x in trains}) != len(trains):raise ValueError('Повторный номер обучающей последовательности.')
    t_test, y_deg = verified_motion(test_entry, 'test')
    train = [(entry['id'], *verified_motion(entry, 'train')) for entry in trains]
    model = read_npz(model_path, ('mean','scale','intercept','weights'))
    inputs_path = folder / 'model_inputs.npz'; vision_path = folder / 'observer_vision.npz'
    data = read_npz(inputs_path, ('frame_luminance','raw_history','normalized_history','times_s'))
    vision = read_npz(vision_path, ('eye_rgb','times_s'))
    csv_path = folder / 'user_predictions.csv'; rows = read_csv(csv_path)
    n = len(rows)
    expected_shapes = {'mean':(576,), 'scale':(576,), 'intercept':(6,), 'weights':(576,6)}
    for key,shape in expected_shapes.items():
        if model[key].shape != shape or not np.isfinite(model[key]).all():raise ValueError(f'Некорректный массив модели {key}.')
    if np.any(model['scale'] <= 0):raise ValueError('Некорректный масштаб модели.')
    shapes = {'frame_luminance':(n+2,192),'raw_history':(n,576),'normalized_history':(n,576),'times_s':(n,)}
    for key,shape in shapes.items():
        if data[key].shape != shape or not np.isfinite(data[key]).all():raise ValueError(f'Некорректный массив признаков {key}.')
    images = vision['eye_rgb']
    if images.dtype != np.uint8 or images.shape != (n+2,2,32,48,3) or vision['times_s'].shape != (n+2,):raise ValueError('Некорректный массив RGB.')
    if not np.isfinite(vision['times_s']).all():raise ValueError('Некорректные времена RGB.')
    if hashlib.sha256(images.tobytes()).hexdigest() != test_entry.get('eye_rgb_sha256'):
        raise ValueError('SHA RGB массива не совпадает с манифестом.')
    if hashlib.sha256(np.asarray(data['raw_history'],dtype='<f8').tobytes()).hexdigest() != test_entry.get('history_sha256'):
        raise ValueError('SHA истории не совпадает с манифестом.')
    nearly(vision['times_s'], t_test, 'времена RGB'); nearly(data['times_s'], t_test[2:], 'времена входов'); nearly(rows[:,0], t_test[2:], 'времена CSV')
    nearly(rows[:,1:7], y_deg[2:] * np.pi / 180, 'углы учителя')
    luminance = images.astype(np.float64).mean(axis=-1) / 255.0
    luminance = luminance.reshape(n+2,2,8,4,12,4).mean(axis=(3,5)).reshape(n+2,192)
    delta_lum = nearly(data['frame_luminance'], luminance, 'RGB → блоки', atol=1e-12)
    history = np.concatenate([luminance[2-i:n+2-i] for i in range(3)], axis=1)
    delta_raw = nearly(data['raw_history'], history, 'RGB → история', atol=1e-12)
    z = (history - model['mean']) / model['scale']
    delta_norm = nearly(data['normalized_history'], z, 'нормировка', atol=1e-10)
    unbounded = z @ model['weights'] + model['intercept']
    prediction = np.clip(unbounded, -math.pi/3, math.pi/3)
    delta_pred = nearly(rows[:,7:13], prediction, 'прогноз из признаков и весов', atol=1e-9)
    # Corresponding motion history in degrees: current, previous, previous-previous.
    train_histories = []; train_meta = []
    for train_id, t, y in train:
        for k in range(2, len(t)):
            train_histories.append(np.concatenate([y[k],y[k-1],y[k-2]]));train_meta.append((train_id,float(t[k])))
    train_histories = np.asarray(train_histories)
    if len(train_histories) < 2:raise ValueError('Недостаточно кадров обучения.')
    test_histories = np.stack([np.concatenate([y_deg[k],y_deg[k-1],y_deg[k-2]]) for k in range(2,len(y_deg))])
    # Bound RAM: never materialize a test × train × 18 tensor for 50 trajectories.
    nearest = np.empty(n, dtype=int); min_dist = np.empty(n, dtype=float)
    for i, history_row in enumerate(test_histories):
        distances = np.sqrt(np.mean((train_histories - history_row)**2, axis=1))
        nearest[i] = int(np.argmin(distances)); min_dist[i] = distances[nearest[i]]
    scores = rows[:,7:13] - rows[:,1:7]
    sse = np.sum(scores*scores,axis=1)
    usable = model['scale'] < 0.999999 # raw features are in [0,1]; scale=1 is the zero-variance fallback
    first = z[0]; nonflat = first[usable]
    lines = [
      'ДИАГНОСТИКА ГОТОВОЙ ПРОБЫ 51 (БЕЗ ОБУЧЕНИЯ И НОВОГО ПОКАЗА)',
      f'Проверка: {folder.name}; кадров {n}; обучающих последовательностей {len(train)}.',
      'Сведения содержат контрольные суммы и численные данные, не содержат путей и имён исходных пользовательских файлов.',
      f'SHA256 model_six_axes.npz: {sha(model_path)}', f'SHA256 input_manifest.json: {sha(manifest_path)}',
      f'SHA256 model_inputs.npz: {sha(inputs_path)}', f'SHA256 observer_vision.npz: {sha(vision_path)}', f'SHA256 user_predictions.csv: {sha(csv_path)}',
      'Сверено: модель и манифест с metadata; копии JSON с манифестом; RGB и история с манифестом.',
      f'Максимальная разность RGB→блоки / история / нормировка / прогноз CSV: {delta_lum:.3g} / {delta_raw:.3g} / {delta_norm:.3g} / {delta_pred:.3g}.',
      'Это проверка согласованности файлов, а не независимое доказательство отсутствия похожих движений.',
      '', 'ОШИБКИ',
      f'RMSE на всех кадрах и 6 осях: {np.sqrt(np.mean(scores*scores)):.9f} рад; MAE: {np.mean(np.abs(scores)):.9f} рад.',
      f'В первых {min(4,n)} оценённых кадрах доля суммы квадратов ошибок: {100*float(sse[:4].sum()/sse.sum()) if sse.sum() else 0:.4f}%.',
      '', 'БЛИЗОСТЬ ИЗВЕСТНЫХ УГЛОВ К ОБУЧЕНИЮ',
      'Для каждого кадра: ближайшая из известных обучающих историй по RMS разности 18 углов (6 осей × 3 кадра), в градусах.',
      'Это сравнение эталонных углов, недоступных для вывода модели; не расстояние изображений и не доказательство причины ошибки.',
    ]
    for i in range(min(8,n)):
        train_id, t = train_meta[int(nearest[i])]
        lines.append(f'{rows[i,0]:.2f} с: {min_dist[i]:.5f}°; ближайшая обучающая последовательность {train_id}, момент {t:.2f} с.')
    lines += [f'Среднее расстояние первых {min(4,n)} кадров: {min_dist[:4].mean():.5f}°.',
              (f'Среднее расстояние остальных {n-4} кадров: {min_dist[4:].mean():.5f}°.' if n>4 else 'Остальных кадров нет.'),
              '', 'ПЕРВЫЙ ПРОГНОЗ И РАЗЛОЖЕНИЕ ЛИНЕЙНОЙ МОДЕЛИ',
              f'Время: {rows[0,0]:.2f} с; история: текущий, −0,04 с, −0,08 с.',
              f'Переменных с обычной нормировкой: {int(usable.sum())}; с запасным масштабом 1: {int((~usable).sum())}.',
              (f'На первом кадре среди обычных: max |z|={np.max(np.abs(nonflat)):.5f}; |z|>3: {int(np.sum(np.abs(nonflat)>3))} из {len(nonflat)}; |z|>10: {int(np.sum(np.abs(nonflat)>10))}.' if len(nonflat) else 'Нет переменных с обычной нормировкой.'),
              'Масштаб 1 заменяет почти нулевое стандартное отклонение; показатель |z|>3 описательный, не проверка вероятности.',
              'Вклады (радианы): свободный член + суммы для трёх моментов = выход до ограничения ±60°. Это не причинное вмешательство.']
    for j, axis in enumerate(AXES):
        contributions = first * model['weights'][:,j]
        sums = [contributions[192*k:192*(k+1)].sum() for k in range(3)]
        lines.append(f'{axis}: учитель={rows[0,1+j]*180/math.pi:+.5f}°, прогноз={prediction[0,j]*180/math.pi:+.5f}°, ошибка={(prediction[0,j]-rows[0,1+j])*180/math.pi:+.5f}°;')
        lines.append(f'  свободный={model["intercept"][j]:+.8f}; текущее={sums[0]:+.8f}; -0,04={sums[1]:+.8f}; -0,08={sums[2]:+.8f}; до ограничения={unbounded[0,j]:+.8f}; после={prediction[0,j]:+.8f}.')
        for idx in np.argsort(-np.abs(contributions), kind='stable')[:3]:
            k = int(idx); shift = k // 192; within = k % 192; eye = within // 96; pos = within % 96
            lines.append(f'  признак {k}: история -{shift*0.04:.2f} с, камера {eye+1}, строка {pos//12+1}, столбец {pos%12+1}; z={first[k]:+.6f}; вес={model["weights"][k,j]:+.6f}; вклад={contributions[k]:+.8f} рад.')
    lines += ['', 'ОГРАНИЧЕНИЯ',
       'Один пользовательский тест, выбранный после просмотра. Кадры зависимы. Нельзя доказать обобщение или причину ошибки.',
       'История и признаки синтетических камер, модель линейная, углы учителя заданы явно. Это не биологическое зрение и не доказательство зеркальных нейронов.',
       'Запуск диагностики не обучает модель и не меняет исходные результаты. Если проверка прервана, сообщите текст ошибки.']
    return '\n'.join(lines) + '\n'


def choose():
    import tkinter as tk
    from tkinter import filedialog, messagebox
    root = tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:
        messagebox.showinfo('Выберите результаты', 'Найдите папку завершённого запуска user_wing_learning_..., откройте в ней test_001 и выберите user_predictions.csv. Исходные файлы не будут изменены.', parent=root)
        base = Path('workspace/runs/ideas/i-observational/wing-studio-user-learning').resolve()
        return filedialog.askopenfilename(title='Откройте test_001 и выберите user_predictions.csv', initialdir=str(base) if base.is_dir() else str(Path.cwd()), filetypes=[('Результат CSV','user_predictions.csv')],parent=root)
    finally:root.destroy()


def main():
    p = argparse.ArgumentParser();g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--choose',action='store_true');g.add_argument('--test-folder')
    p.add_argument('--output-root',default='workspace/runs/ideas/i-observational/wing-diagnostics')
    args=p.parse_args()
    if args.choose:
        selected=choose()
        if not selected:print('Выбор отменён; диагностика не запускалась.');return
        if Path(selected).name != 'user_predictions.csv':raise ValueError('Выберите файл user_predictions.csv.')
        folder=Path(selected).parent
    else:folder=Path(args.test_folder)
    text=analyze(folder)
    base=Path(args.output_root);base.mkdir(parents=True,exist_ok=True)
    out=base/('wing_diagnostic_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);out.mkdir()
    report=out/'ОТЧЕТ.txt'
    with report.open('x',encoding='utf-8-sig',newline='\n') as f:f.write(text)
    print('\nГотово. Текстовый отчёт:',report.resolve());print('Отправьте сюда содержимое ОТЧЕТ.txt. Исходные результаты не изменены.')
    if os.name=='nt':
        try:os.startfile(str(report.resolve()))
        except OSError:print('Не удалось открыть отчёт автоматически. Откройте его по пути выше.')

if __name__ == '__main__':
    try:main()
    except Exception as exc:
        print(f'ОШИБКА: {type(exc).__name__}: {exc}. Исходные результаты не изменены.',file=sys.stderr);sys.exit(1)
