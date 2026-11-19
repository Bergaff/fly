#!/usr/bin/env python3
"""Supervised image-to-wing-angle imitation in a kinematic two-fly toy scene.

Visual input only at inference; labels are demonstrator angles used for fitting
and evaluation, not unsupervised observational learning or a biological model.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import sys
import uuid

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
import numpy as np
import mujoco
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ENGINE_HASH = '2f7d4ed860abe2cd97aec19ce93012d608501fa85acbfd6ae7aec9b46d673290'
FPS = 25
FRAMES = 50
WIDTH, HEIGHT = 48, 32
HISTORY = 3
AMPLITUDE = 0.65
RIDGE = 1.0
SEED = 20261107


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def engine_load():
    path = HERE / '38_two_flies_observation.py'
    if sha(path) != ENGINE_HASH:
        raise ValueError('Файл модели 38 отличается от закреплённого. Ничего не запущено.')
    spec = importlib.util.spec_from_file_location('imitation_scene_engine', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def plan(smoke=False):
    train = [(f, phase, off) for f in (1.0, 2.0, 4.0) for phase in (0, 90, 180, 270) for off in (-0.4, 0.0, 0.4)]
    test = [(f, phase, 0.2) for f in (1.5, 3.5) for phase in (45, 135, 225, 315)]
    if smoke:
        train = [(1.0, 0, 0.0), (2.0, 90, -0.4)]
        test = [(1.5, 45, 0.2)]
    if set(train) & set(test):
        raise ValueError('Обучающая и проверочная последовательности пересекаются.')
    if set(x[0] for x in train) & set(x[0] for x in test) or set(x[1] for x in train) & set(x[1] for x in test) or set(x[2] for x in train) & set(x[2] for x in test):
        raise ValueError('Отложенные частоты, фазы и смещения должны быть новыми.')
    return train, test


class Scene:
    def __init__(self, engine):
        self.engine = engine
        self.model = mujoco.MjModel.from_xml_string(engine.XML)
        self.data = mujoco.MjData(self.model)
        self.body = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, 'demonstrator')
        self.left = self.model.jnt_qposadr[mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, 'left_hinge')]
        self.right = self.model.jnt_qposadr[mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, 'right_hinge')]
        self.cams = [engine.camera([.85, y, .46], [4, 0, .55], WIDTH, HEIGHT) for y in (.13, -.13)]
        self.cache = {}

    def eyes(self, angle, offset):
        # Near-identical periodic poses share a render; rounding is at most 1e-12 rad.
        key = (offset, round(float(angle), 12))
        if key not in self.cache:
            self.model.body_pos[self.body] = [4.0, offset, .4]
            self.data.qpos[self.left] = angle; self.data.qpos[self.right] = -angle
            mujoco.mj_forward(self.model, self.data)
            self.cache[key] = np.stack([self.engine.render(self.model, self.data, cam, True) for cam in self.cams])
        return self.cache[key]

    def sequence(self, spec):
        freq, phase, offset = spec
        times = np.arange(FRAMES, dtype=float) / FPS
        target = AMPLITUDE * np.sin(2 * np.pi * freq * times + np.deg2rad(phase))
        images = np.stack([self.eyes(a, offset) for a in target])
        return images, target


def visual_vectors(images):
    # Mean luminance in 4x4-pixel blocks. Unlike the previous 32 LIF motion
    # features, these retain coarse spatial appearance, not LIF spikes.
    lum = images.astype(np.float64).mean(axis=-1) / 255.0
    n, eyes, h, w = lum.shape
    return lum.reshape(n, eyes, h//4, 4, w//4, 4).mean(axis=(3, 5)).reshape(n, -1)


def history(images):
    vectors = visual_vectors(images)
    return np.concatenate([vectors[HISTORY-1-i:len(vectors)-i] for i in range(HISTORY)], axis=1)


def fit(train_x, train_y):
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    scale[scale < 1e-6] = 1.0
    z = (train_x - mean) / scale
    # Centre target separately; L2 ridge and normalisation use only training data.
    intercept = float(train_y.mean())
    weights = np.linalg.solve(z.T @ z / len(z) + RIDGE * np.eye(z.shape[1]), z.T @ (train_y - intercept) / len(z))
    init = np.random.default_rng(SEED).normal(0, 0.03 / np.sqrt(z.shape[1]), z.shape[1])
    return mean, scale, intercept, weights, init


def predict(images, mean, scale, intercept, weights):
    z = (history(images) - mean) / scale
    return np.clip(z @ weights + intercept, -AMPLITUDE, AMPLITUDE)


def metrics(target, prediction):
    d = prediction - target
    rmse = float(np.sqrt(np.mean(d*d))); mae = float(np.mean(np.abs(d)))
    corr = None
    if np.std(target) > 1e-12 and np.std(prediction) > 1e-12:
        corr = float(np.corrcoef(target, prediction)[0, 1])
    return {'rmse_rad': rmse, 'mae_rad': mae, 'correlation': corr}


def csv_write(path, header, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f); writer.writerow(header); writer.writerows(rows)


def preview(engine, target, predicted, spec, path):
    xml = engine.XML
    for side, y in [('left', '0.75'), ('right', '-0.75')]:
        original = f'<geom name="observer_{side}_wing" type="ellipsoid" pos="-0.1 {y} 0.20" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/>'
        replacement = f'<body name="observer_{side}_joint_body" pos="-0.1 {y} 0.20"><joint name="observer_{side}_hinge" type="hinge" axis="1 0 0"/><geom name="observer_{side}_wing" type="ellipsoid" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/></body>'
        if original not in xml: raise ValueError('Не удалось собрать визуализацию наблюдателя.')
        xml = xml.replace(original, replacement)
    model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
    model.body_pos[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, 'demonstrator')] = [4.0, spec[2], .4]
    def jid(name): return model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)]
    dl, dr, ol, or_ = [jid(x) for x in ('left_hinge', 'right_hinge', 'observer_left_hinge', 'observer_right_hinge')]
    cam = engine.camera([6, -9, 5], [2, 0, .4], 240, 160, 55)
    images = []
    for a, p in zip(target, predicted):
        data.qpos[dl], data.qpos[dr], data.qpos[ol], data.qpos[or_] = a, -a, p, -p
        mujoco.mj_forward(model, data)
        im = Image.fromarray(engine.render(model, data, cam))
        draw = ImageDraw.Draw(im); draw.rectangle((0, 0, 239, 17), fill=(220, 220, 210))
        draw.text((3, 3), 'OBSERVER LEFT / TEACHER RIGHT', fill=(20, 20, 20))
        images.append(im)
    images[0].save(path, save_all=True, append_images=images[1:], duration=round(1000/FPS), loop=0, optimize=False)


def plot_sequence(target, predicted, path):
    image = Image.new('RGB', (900, 320), (239, 238, 229))
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = 50, 45, 870, 275
    draw.line((left, top, left, bottom, right, bottom), fill=(50, 50, 45), width=1)
    draw.line((left, (top+bottom)//2, right, (top+bottom)//2), fill=(170, 170, 160), width=1)
    def line(values, color):
        points = [(left + i*(right-left)/(len(values)-1), top + (AMPLITUDE-float(v))*(bottom-top)/(2*AMPLITUDE)) for i,v in enumerate(values)]
        draw.line(points, fill=color, width=2)
    line(target, (38, 73, 102)); line(predicted, (174, 74, 42))
    draw.text((50, 14), 'TEACHER (BLUE)  /  OBSERVER (RED)  /  FIRST TEST SEQUENCE', fill=(30,30,30))
    draw.text((6, top-5), '+0.65', fill=(30,30,30)); draw.text((11, bottom-5), '-0.65', fill=(30,30,30))
    draw.text((left, 292), 'time: observation (s)     angle: radians', fill=(30,30,30))
    image.save(path)


def lower_priority():
    try:
        if os.name == 'nt':
            import ctypes
            kernel = ctypes.windll.kernel32
            kernel.GetCurrentProcess.restype = ctypes.c_void_p
            kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            if not kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x00004000):
                print('Не удалось снизить приоритет процесса.', flush=True)
        elif hasattr(os, 'nice'):
            os.nice(10)
    except OSError:
        print('Не удалось снизить приоритет процесса.', flush=True)


def run(root, smoke=False):
    engine = engine_load()
    train_specs, test_specs = plan(smoke)
    root = Path(root).resolve(); root.mkdir(parents=True, exist_ok=True)
    out = root / ('imitation_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8])
    out.mkdir(); (out/'INCOMPLETE.txt').write_text('Эксперимент выполняется или прерван. Результаты не завершены.\n', encoding='utf-8')
    scene = Scene(engine)
    sequences = []
    for split, specs in [('train', train_specs), ('test', test_specs)]:
        for spec in specs:
            print(f'Кадры: {split}, {spec[0]} Гц, фаза {spec[1]}, смещение {spec[2]}', flush=True)
            images, target = scene.sequence(spec)
            sequences.append((split, spec, images, target))
    np.savez_compressed(out/'visual_sequences.npz', images=np.stack([x for _, _, x, _ in sequences]), teacher_angle=np.stack([y for _, _, _, y in sequences]))
    train_x = np.concatenate([history(x) for split, _, x, _ in sequences if split == 'train'])
    train_y = np.concatenate([y[HISTORY-1:] for split, _, _, y in sequences if split == 'train'])
    mean, scale, intercept, weights, init = fit(train_x, train_y)
    np.savez_compressed(out/'model.npz', mean=mean, scale=scale, intercept=intercept, weights=weights, initial_weights=init)
    split_rows, records, summary_rows = [], [], []
    aggregate = {k: [[], []] for k in ('trained', 'untrained', 'constant_zero', 'occluded', 'shuffled')}
    preview_data = None
    for seq_id, (split, spec, images, target) in enumerate(sequences):
        freq, phase, offset = spec
        split_rows.append((seq_id, split, freq, phase, 4.0, offset, FRAMES))
        if split != 'test': continue
        y = target[HISTORY-1:]
        rng = np.random.default_rng(SEED + seq_id)
        shuffle_idx = rng.permutation(FRAMES)
        # Shuffle whole images, so the tested control breaks temporal stimulus structure.
        preds = {'trained': predict(images, mean, scale, intercept, weights),
                 'untrained': predict(images, mean, scale, 0.0, init),
                 'constant_zero': np.zeros_like(y),
                 'occluded': predict(np.full_like(images, 128), mean, scale, intercept, weights),
                 'shuffled': predict(images[shuffle_idx], mean, scale, intercept, weights)}
        for name, pred in preds.items():
            score = metrics(y, pred); aggregate[name][0].extend(y.tolist()); aggregate[name][1].extend(pred.tolist())
            summary_rows.append((seq_id, freq, phase, offset, name, len(y), score['rmse_rad'], score['mae_rad'], score['correlation']))
        for k in range(HISTORY-1, FRAMES):
            i = k - (HISTORY-1)
            records.append((seq_id, freq, phase, offset, k, k/FPS, target[k], *(preds[name][i] for name in ('trained', 'untrained', 'constant_zero', 'occluded', 'shuffled'))))
        if preview_data is None:
            preview_data = (y.copy(), preds['trained'].copy(), spec)
    csv_write(out/'split.csv', ['sequence_id','split','frequency_hz','phase_deg','distance','offset','frames'], split_rows)
    csv_write(out/'test_metrics.csv', ['sequence_id','frequency_hz','phase_deg','offset','condition','frames','rmse_rad','mae_rad','correlation'], summary_rows)
    csv_write(out/'test_predictions.csv', ['sequence_id','frequency_hz','phase_deg','offset','frame','time_s','teacher_angle_rad','trained_angle_rad','untrained_angle_rad','zero_angle_rad','occluded_angle_rad','shuffled_angle_rad'], records)
    scores = {name: metrics(np.asarray(target), np.asarray(pred)) for name, (target, pred) in aggregate.items()}
    if preview_data:
        preview(engine, *preview_data, out/'comparison.gif')
        plot_sequence(preview_data[0], preview_data[1], out/'comparison.png')
    metadata = {'status':'completed', 'mode':'smoke' if smoke else 'full_pilot', 'created_utc':datetime.now(timezone.utc).isoformat(), 'script_sha256':sha(__file__), 'engine_sha256':ENGINE_HASH,
                'python':platform.python_version(), 'versions':{p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')}, 'seed':SEED, 'fps':FPS, 'frames_per_sequence':FRAMES, 'history_frames':HISTORY, 'frame_shape':[2,HEIGHT,WIDTH,3], 'cache_pose_rounding_decimal_places':12, 'train_sequences':len(train_specs), 'test_sequences':len(test_specs), 'train_samples':len(train_y), 'test_samples':len(records), 'ridge':RIDGE, 'amplitude_rad':AMPLITUDE, 'distance':4.0, 'scores':scores,
                'method':'Supervised ridge regression from three past/current coarse grayscale images of two eyes to demonstrator angle. Teacher angles are training labels, never predictor inputs. Two observer wings receive the same predicted magnitude with opposite signs.',
                'limitations':['Kinematic wing position, no musculoskeletal dynamics or closed-loop body.', 'Labels from demonstrator angles: supervised imitation, not self-discovered action or label-free learning.', 'No LIF spikes, no biological connectome, no evidence of mirror neurons.', 'Holdout frequencies, phases and offsets are disjoint, but video and motion are deterministic synthetic sine waves of a fixed amplitude and distance; individual poses can repeat.', 'This is an exploratory engineering pilot: the plan was revised after inspecting an earlier local run, so it is not a blind confirmatory holdout.', 'Predictions are simultaneous with observation; the model does not generate action after the visual input ends.', 'Shuffled control disrupts temporal pairing; occlusion is out-of-distribution constant gray; neither is a matched moving-object control.', 'Global scores pool correlated frames, not independent animals; no statistical significance claimed.']}
    (out/'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    lines = ['ОБУЧЕНИЕ ПО НАБЛЮДЕНИЮ: ПРОБА ДВУХ МУХ', f'Режим: {"ТЕСТОВЫЙ МАЛЫЙ НАБОР" if smoke else "основной пилот"}', f'Обучающих последовательностей: {len(train_specs)}; новых проверочных: {len(test_specs)}.', 'Частоты, фазы и смещения проверочных последовательностей отсутствуют в обучающем наборе.', 'Вход модели: только последние три изображения двух глаз. Обучающие метки: угол крыльев первой мухи.', 'Команда второй мухе: предсказанный угол. Это кинематическая сцена, а не обучение физической мухи.', '', 'Оценка на новых последовательностях, RMSE в радианах (меньше лучше):']
    for name, label in [('trained','После обучения'), ('untrained','До обучения (случайные веса)'), ('constant_zero','Постоянный нулевой угол'), ('occluded','После обучения, серый вход'), ('shuffled','После обучения, перемешанные кадры')]:
        v=scores[name]; lines.append(f'{label}: {v["rmse_rad"]:.6f}; MAE {v["mae_rad"]:.6f}; корреляция {v["correlation"] if v["correlation"] is not None else "не определена"}')
    lines.extend(['', 'Обучение выполнено по явным эталонным углам, поэтому это не самостоятельное обучение без подсказки.', 'Данные детерминированы, движение синусоидальное; кадры не являются независимыми биологическими повторами.', 'Пилотный план скорректирован после просмотра предыдущей локальной пробы. Это не слепая подтверждающая проверка.', 'Модель выдаёт команды при просмотре, не воспроизводит движение самостоятельно после окончания видео.', 'Серый вход может быть вне распределения обучения; эти контроли не заменяют уравненный движущийся объект.', 'При ухудшении относительно простого нулевого прогноза обучение нельзя считать успешным.', 'comparison.gif и comparison.png показывают одну заранее выбранную проверочную последовательность, не средний результат.', 'test_metrics.csv содержит оценки по последовательностям, test_predictions.csv покадровые данные; split.csv список условий.', 'model.npz сохраняет веса, visual_sequences.npz кадры и эталонные углы; metadata.json параметры, версии и ограничения.', 'Это не доказательство зеркальных нейронов, моторной физики или обучения живой мухи.'])
    (out/'ИТОГ.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8-sig')
    (out/'INCOMPLETE.txt').unlink()
    print('\n'.join(lines)); print('\nРезультаты:', out, flush=True)
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='workspace/runs/ideas/i-observational/imitation-learning')
    parser.add_argument('--smoke', action='store_true', help=argparse.SUPPRESS)
    args=parser.parse_args()
    lower_priority()
    result=run(args.output, args.smoke)
    if os.name == 'nt':
        try: os.startfile(str(result))
        except OSError as exc: print('Не удалось открыть папку автоматически:', exc)


if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ОШИБКА: {type(exc).__name__}: {exc}\nСтарые исследования не изменены. Папка с INCOMPLETE.txt не является готовым результатом.', file=sys.stderr, flush=True)
        sys.exit(1)
