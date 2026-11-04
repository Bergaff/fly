#!/usr/bin/env python3
"""Follow-up kinematic stimulus controls for the two-flies toy observer."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
import numpy as np
import mujoco
from PIL import Image

BASE = Path(__file__).resolve().parent / '38_two_flies_observation.py'
EXPECTED = '2f7d4ed860abe2cd97aec19ce93012d608501fa85acbfd6ae7aec9b46d673290'
CONDITIONS = (
    dict(name='wing_stationary', kind='wing_static', frequency_hz=0., phase_deg=0., control=None),
    dict(name='object_stationary', kind='object_static', frequency_hz=0., phase_deg=0., control=None),
    dict(name='wing_2hz_0deg', kind='wing', frequency_hz=2., phase_deg=0., control='wing_stationary'),
    dict(name='wing_3hz_0deg', kind='wing', frequency_hz=3., phase_deg=0., control='wing_stationary'),
    dict(name='wing_3hz_90deg', kind='wing', frequency_hz=3., phase_deg=90., control='wing_stationary'),
    dict(name='wing_4hz_0deg', kind='wing', frequency_hz=4., phase_deg=0., control='wing_stationary'),
    dict(name='object_3hz_0deg', kind='object', frequency_hz=3., phase_deg=0., control='object_stationary'),
)
ACTIVE = tuple(c for c in CONDITIONS if c['control'])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_engine():
    if sha(BASE) != EXPECTED:
        raise ValueError('Исходный скрипт 38 не соответствует закреплённой версии.')
    spec = importlib.util.spec_from_file_location('visual_observer_engine', BASE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stats(times, ids, frequency, phase_offset):
    counts = np.bincount(ids, minlength=32)
    phase = np.remainder(2 * np.pi * frequency * times + phase_offset, 2 * np.pi)
    z = np.bincount(ids, weights=np.cos(phase), minlength=32) + 1j * np.bincount(ids, weights=np.sin(phase), minlength=32)
    strength = np.divide(np.abs(z), counts, out=np.zeros(32), where=counts > 0)
    direction = np.where((counts > 0) & (strength > 1e-12), np.remainder(np.angle(z), 2 * np.pi), np.nan)
    bin_ids = np.minimum((phase * 8 / (2 * np.pi)).astype(int), 7)
    bins = np.bincount(ids * 8 + bin_ids, minlength=256).reshape(32, 8)
    return counts, strength, direction, bins


def save_csv(path, columns, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(columns)
        w.writerows(rows)


def run(output, duration=2., fps=50, seed=0, width=96, height=64):
    if not (0 < duration <= 10 and fps in (20, 25, 50)):
        raise ValueError('Продолжительность: (0, 10] секунд; FPS: 20, 25 или 50.')
    count = round(duration * fps)
    if count < 2 or abs(count / fps - duration) > 1e-9 or abs(round(duration * 1000) / 1000 - duration) > 1e-9:
        raise ValueError('Продолжительность должна содержать целое число кадров и миллисекунд.')
    if width <= 0 or height <= 0 or width % 4 or height % 4:
        raise ValueError('Размеры изображения должны быть положительны и кратны 4.')
    engine = load_engine()
    obj_xml = '<body name="distractor" mocap="true" pos="3 0 0.55"><geom name="distractor_geom" type="ellipsoid" size="0.25 0.25 0.25" rgba="0.22 0.22 0.20 1"/></body>'
    xml_object = engine.XML.replace('</worldbody></mujoco>', obj_xml + '</worldbody></mujoco>')
    if xml_object == engine.XML:
        raise ValueError('Не удалось подготовить отдельную сцену постороннего объекта.')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    dest = output / ('visual_controls_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8])
    dest.mkdir()
    metadata = dict(status='running', created_utc=datetime.now(timezone.utc).isoformat(), duration_s=duration, fps=fps, sample_times_s='k / fps', seed=seed,
        integration_dt_ms=1, visual_shape=[2, height, width, 3], eye_fov_deg=65,
        wing_amplitude_rad=0.65, object_center_xyz=[3., 0., 0.55], object_y_amplitude=0.65,
        object_size=[0.25, 0.25, 0.25], object_appearance='dark ellipsoid', object_motion='y=0.65*sin(2*pi*f*t+phase), x=3, z=0.55',
        source_sha256=sha(Path(__file__)), engine_sha256=EXPECTED, engine_file=str(BASE.resolve()),
        python=platform.python_version(), versions={p: importlib.metadata.version(p) for p in ('numpy', 'mujoco', 'brian2', 'pillow')},
        conditions=list(CONDITIONS), model='identical toy LIF engine, two kinematic flies, ray-cast RGB; extra ellipsoid only in object scenes',
        limitations='Not a connectome or a biological eye. Distractor differs in shape, position, extent and motion statistics; matching is not enforced. Frequencies are not biological wingbeat rates. No learning or observer motor action. No biological replicates.')
    (dest / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    (dest / 'scene_wings.xml').write_text(engine.XML, encoding='utf-8')
    (dest / 'scene_object.xml').write_text(xml_object, encoding='utf-8')
    save_csv(dest / 'neuron_map.csv', ['neuron_id', 'eye', 'tile_row', 'tile_col', 'model'], ((i, 'left' if i < 16 else 'right', i % 16 // 4, i % 4, 'toy_LIF_motion') for i in range(32)))
    cams = [engine.camera([.85, y, .46], [4, 0, .55], width, height) for y in (.13, -.13)]
    data_by_condition = {}
    for cond in CONDITIONS:
        name, kind, freq = cond['name'], cond['kind'], cond['frequency_hz']
        phase_offset = math.radians(cond['phase_deg'])
        has_object = kind.startswith('object')
        model = mujoco.MjModel.from_xml_string(xml_object if has_object else engine.XML)
        data = mujoco.MjData(model)
        left = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, 'left_hinge')]
        right = model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, 'right_hinge')]
        frames, scene = [], []
        static = kind.endswith('_static')
        for k in range(count):
            t = k / fps
            signal = math.sin(2 * math.pi * freq * t + phase_offset)
            angle = 0.65 * signal if kind == 'wing' else 0.
            data.qpos[left], data.qpos[right] = angle, -angle
            y = 0.65 * signal if kind == 'object' else 0.
            if has_object:
                data.mocap_pos[0] = [3., y, .55]
            mujoco.mj_forward(model, data)
            if static and k:
                frame = frames[0].copy()
            else:
                frame = np.stack([engine.render(model, data, cam, True) for cam in cams])
            frames.append(frame)
            scene.append((k, t, float(data.qpos[left]), float(data.qpos[right]), int(has_object), 3. if has_object else '', y if has_object else '', .55 if has_object else ''))
        frames = np.stack(frames)
        features = engine.features(frames)
        ts, ids, drives = engine.simulate(features, 1 / fps, seed)
        sub = dest / name
        sub.mkdir()
        np.savez_compressed(sub / 'vision.npz', scene_eyes=frames, neural_input=frames, input_source_frame=np.arange(count))
        save_csv(sub / 'scene.csv', ['frame', 'time_s', 'left_wing_rad', 'right_wing_rad', 'object_present', 'object_x', 'object_y', 'object_z'], scene)
        save_csv(sub / 'visual_input.csv', ['frame', 'time_s', 'neuron_id', 'motion_abs_diff', 'drive'], ((k, k / fps, i, float(features[k, i]), float(drives[k, i])) for k in range(count) for i in range(32)))
        save_csv(sub / 'spikes.csv', ['time_s', 'neuron_id'], ((float(t), int(i)) for t, i in zip(ts, ids)))
        ims = [Image.fromarray(np.concatenate((frame[0], frame[1]), axis=1)) for frame in frames]
        ims[0].save(sub / 'observer_input.gif', save_all=True, append_images=ims[1:], duration=round(1000 / fps), loop=0, optimize=False)
        summary = dict(condition=name, frames=count, spikes=len(ts), mean_motion=float(features.mean()), mean_motion_by_neuron=features.mean(axis=0).tolist(), condition_parameters=cond)
        (sub / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
        data_by_condition[name] = dict(times=ts, ids=ids, features=features, summary=summary)
        print(f'{name}: {len(ts)} спайков; средняя разность яркости {features.mean():.6f}', flush=True)
    for name in ('wing_stationary', 'object_stationary'):
        if np.any(data_by_condition[name]['features']):
            raise ValueError(f'Неподвижный контроль {name} содержит изменения изображения.')
    for cond in ACTIVE:
        if not np.any(data_by_condition[cond['name']]['features']):
            raise ValueError(f"Стимул {cond['name']} не вызвал изменений изображения. Результат оставлен со статусом running.")
    overall, neurons, bins_rows = [], [], []
    for cond in ACTIVE:
        name, control = cond['name'], cond['control']
        active, static = data_by_condition[name], data_by_condition[control]
        f, offset = cond['frequency_hz'], math.radians(cond['phase_deg'])
        acount, strength, direction, abins = stats(active['times'], active['ids'], f, offset)
        bcount, _, _, bbins = stats(static['times'], static['ids'], f, offset)
        overall.append((name, control, cond['kind'], f, cond['phase_deg'], len(active['times']), len(static['times']), float(active['features'].mean()), float(static['features'].mean())))
        ticks = np.arange(round(duration * 1000)) / 1000
        phase_ticks = np.remainder(2 * np.pi * f * ticks + offset, 2 * np.pi)
        exposure = np.bincount(np.minimum((phase_ticks * 8 / (2 * np.pi)).astype(int), 7), minlength=8) / 1000
        for i in range(32):
            neurons.append((name, control, f, cond['phase_deg'], i, 'left' if i < 16 else 'right', i % 16 // 4, i % 4, int(acount[i]), int(bcount[i]), int(acount[i] - bcount[i]), float(active['features'][:, i].mean()), float(static['features'][:, i].mean()), float(strength[i]), float(np.degrees(direction[i])) if np.isfinite(direction[i]) else ''))
            for k in range(8):
                bins_rows.append((name, control, i, k, k * 45, (k + 1) * 45, float(exposure[k]), int(abins[i,k]), int(bbins[i,k]), float(abins[i,k] / exposure[k]) if exposure[k] else '', float(bbins[i,k] / exposure[k]) if exposure[k] else ''))
    save_csv(dest / 'conditions_summary.csv', ['condition', 'control', 'stimulus_kind', 'frequency_hz', 'initial_phase_deg', 'spikes', 'control_spikes', 'mean_motion_abs_diff', 'control_mean_motion_abs_diff'], overall)
    save_csv(dest / 'neuron_comparison.csv', ['condition', 'control', 'frequency_hz', 'initial_phase_deg', 'neuron_id', 'eye', 'tile_row', 'tile_col', 'spikes', 'control_spikes', 'spike_difference', 'mean_motion_abs_diff', 'control_mean_motion_abs_diff', 'vector_strength', 'mean_phase_deg'], neurons)
    save_csv(dest / 'phase_bins.csv', ['condition', 'control', 'neuron_id', 'bin', 'phase_start_deg', 'phase_end_deg', 'exposure_s', 'spikes', 'control_spikes', 'rate_hz', 'control_rate_hz'], bins_rows)
    text = '''СЕРИЯ: ДВИЖЕНИЕ КРЫЛА И ПОСТОРОННИЙ ОБЪЕКТ\n\nВ wing_* перед неподвижным наблюдателем находятся неподвижные корпуса; только крылья демонстратора синусоидально вращаются. В object_* у тех же двух тел крылья неподвижны, а отдельный тёмный эллипсоид перемещается в поперечном направлении. Для каждого вида сцены есть свой неподвижный контроль. Частоты 2, 3, 4 Гц и начальная фаза 90 градусов являются параметрами модели, не частотами настоящей мухи. Во всех условиях начальные состояния 32 LIF одинаковы.\n\nconditions_summary.csv показывает среднюю разность изображения и общий счёт. neuron_comparison.csv даёт для каждого ID число спайков, разницу с соответствующим контролем, средний зрительный вход и фазовую привязку. phase_bins.csv содержит пары со своим контролем: фаза это фаза заданной синусоиды движения, включая начальный сдвиг; у контроля фаза условна. Частота на фазу учитывает время в интервале по шагам 1 мс. Фазы средней активности могут быть ненадёжны при низкой силе привязки. Файлы каждого условия: спайки, RGB-кадры, зрительный вход, положение объектов, а также GIF наблюдателя.\n\nОбъект и крыло не уравнены по размеру на изображении, положению, контрасту, траектории, окклюзии или величине/распределению движения. Поэтому различие откликов не доказывает избирательность к крылу; сравните визуальный вход каждого нейрона. Заданный сдвиг фазы меняет и стартовое положение; переходный участок и начальная фаза нейронов могут влиять на итог. Условия не являются независимыми животными или повторениями. Статистический тест не выполнялся.\n\nМодель использует условные камеры, искусственные LIF и абсолютную разность изображений. Действие наблюдателя, обучение, настоящая биология и зеркальные нейроны не моделируются. Изображения и сцена обновляются только по кадрам; шаг сети 1 мс не равен временному разрешению зрительного стимула. Это исследовательский тест прототипа, не биологический вывод.\n'''
    (dest / 'report.txt').write_text(text, encoding='utf-8-sig')
    metadata['status'] = 'completed'
    metadata['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (dest / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    print('RESULT_DIR=' + str(dest.resolve()), flush=True)
    return dest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', default='workspace/runs/ideas/i-observational/visual-controls')
    p.add_argument('--duration', type=float, default=2.)
    p.add_argument('--fps', type=int, default=50)
    p.add_argument('--seed', type=int, default=0)
    args = p.parse_args()
    run(args.output, args.duration, args.fps, args.seed)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ОШИБКА: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
