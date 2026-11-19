#!/usr/bin/env python3
"""Phase and frame-permutation analysis for an existing two-flies pilot run."""
from __future__ import annotations
import argparse
import csv
import hashlib
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

BASE = Path(__file__).resolve().parent / '38_two_flies_observation.py'
EXPECTED = '2f7d4ed860abe2cd97aec19ce93012d608501fa85acbfd6ae7aec9b46d673290'
BINS = 8


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_engine():
    require(sha(BASE) == EXPECTED, 'Локальный скрипт 38 не соответствует версии исходного эксперимента.')
    spec = importlib.util.spec_from_file_location('two_flies_original', BASE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_spikes(path, duration):
    with path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    t = np.array([float(r['time_s']) for r in rows], dtype=float)
    ids = np.array([int(r['neuron_id']) for r in rows], dtype=int)
    require(np.all(np.isfinite(t)) and np.all((0 <= t) & (t < duration)) and np.all((0 <= ids) & (ids < 32)), f'Некорректные спайки: {path}')
    order = np.lexsort((ids, t))
    return t[order], ids[order]


def same_spikes(a, b):
    x = np.lexsort((b[1], b[0]))
    return len(a[0]) == len(b[0]) and np.array_equal(a[1], b[1][x]) and np.allclose(a[0], b[0][x], rtol=0, atol=1e-9)


def phase_stats(times, ids, frequency):
    """Resultant vector and 8-bin event counts for absolute sinusoidal clock phase."""
    phase = np.remainder(2 * np.pi * frequency * times, 2 * np.pi)
    bins = np.minimum((phase * BINS / (2 * np.pi)).astype(int), BINS - 1)
    counts = np.bincount(ids, minlength=32)
    summed = np.bincount(ids, weights=np.cos(phase), minlength=32) + 1j * np.bincount(ids, weights=np.sin(phase), minlength=32)
    strength = np.divide(np.abs(summed), counts, out=np.zeros(32), where=counts > 0)
    direction = np.where((counts > 0) & (strength > 1e-12), np.remainder(np.angle(summed), 2 * np.pi), np.nan)
    by_bin = np.bincount(ids * BINS + bins, minlength=32 * BINS).reshape(32, BINS)
    return counts, strength, direction, by_bin


def save_csv(path, header, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def analyse(run, n=100, random_seed=20261104):
    run = Path(run).resolve()
    require(1 <= n <= 10000, 'Число перемешиваний должно быть от 1 до 10000.')
    required = ['metadata.json', 'neuron_map.csv', 'moving/vision.npz', 'moving/scene.csv', 'moving/spikes.csv', 'stationary/spikes.csv', 'occluded/spikes.csv']
    for name in required:
        require((run / name).is_file(), f'Нет файла {name}. Выберите папку полного запуска, не папку moving.')
    hashes = {name: sha(run / name) for name in required}
    metadata = json.loads((run / 'metadata.json').read_text(encoding='utf-8-sig'))
    require(metadata.get('status') == 'completed', 'Запуск не завершён: status должен быть completed.')
    require(metadata.get('source_sha256') == EXPECTED, 'Этот анализ поддерживает только исходную версию скрипта 38 с известной SHA-256.')
    fps, duration, freq, amp, seed = int(metadata['fps']), float(metadata['duration_s']), float(metadata['wing_hz']), float(metadata['wing_amplitude_rad']), int(metadata['seed'])
    require(fps in (10, 20, 25, 50) and 0 < duration <= 10 and freq > 0 and amp > 0 and metadata.get('integration_dt_ms') == 1, 'Неподдерживаемые параметры исходного запуска.')
    frames_count = round(duration * fps)
    require(frames_count >= 2 and abs(frames_count / fps - duration) < 1e-9, 'Продолжительность не соответствует числу кадров.')
    with (run / 'moving/scene.csv').open(encoding='utf-8-sig', newline='') as f:
        scene = list(csv.DictReader(f))
    require(len(scene) == frames_count, 'Число строк scene.csv не совпадает с параметрами.')
    for k, row in enumerate(scene):
        expected = amp * math.sin(2 * math.pi * freq * k / fps)
        require(int(row['frame']) == k and abs(float(row['time_s']) - k / fps) < 1e-9 and abs(float(row['left_wing_rad']) - expected) < 1e-8 and abs(float(row['right_wing_rad']) + expected) < 1e-8, 'scene.csv не соответствует ожидаемой синусоиде и времени кадров.')
    with (run / 'neuron_map.csv').open(encoding='utf-8-sig', newline='') as f:
        mapping = list(csv.DictReader(f))
    require(len(mapping) == 32 and all(int(row['neuron_id']) == i and row['eye'] == ('left' if i < 16 else 'right') and int(row['tile_row']) == i % 16 // 4 and int(row['tile_col']) == i % 4 for i, row in enumerate(mapping)), 'Неожиданная карта нейронов.')
    with np.load(run / 'moving/vision.npz', allow_pickle=False) as data:
        frames = data['neural_input'].copy()
        require(np.array_equal(data['scene_eyes'], frames) and np.array_equal(data['input_source_frame'], np.arange(frames_count)), 'moving/vision.npz не содержит исходный порядок изображений.')
    require(frames.dtype == np.uint8 and frames.ndim == 5 and frames.shape[:2] == (frames_count, 2) and frames.shape[-1] == 3 and frames.shape[2] % 4 == 0 and frames.shape[3] % 4 == 0, 'Неподдерживаемая форма кадров.')
    engine = load_engine()
    observed = {c: read_spikes(run / c / 'spikes.csv', duration) for c in ('moving', 'stationary', 'occluded')}
    print('Проверка полного воспроизведения сохранённых спайков...', flush=True)
    replay = engine.simulate(engine.features(frames), 1 / fps, seed)
    require(same_spikes(observed['moving'], replay), 'Времена moving не воспроизвелись полностью. Сравнение остановлено: проверьте версии среды и целостность файлов.')
    replay_zero = engine.simulate(np.zeros((frames_count, 32)), 1 / fps, seed)
    for c in ('stationary', 'occluded'):
        require(same_spikes(observed[c], replay_zero), f'Времена {c} не соответствуют фоновому воспроизведению. Сравнение остановлено.')
    require(all(sha(run / name) == digest for name, digest in hashes.items()), 'Входные файлы изменились во время проверки.')

    # Only create output after validations. mkdir with a unique name never replaces data.
    dest = run / ('phase_analysis_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8])
    dest.mkdir()
    result_meta = dict(status='running', created_utc=datetime.now(timezone.utc).isoformat(), input_directory=str(run), input_sha256=hashes, original_script_sha256=EXPECTED, analysis_script_sha256=sha(Path(__file__)), python=platform.python_version(), numpy=np.__version__, brian2=engine.b.__version__, seed_initial_neurons=seed, shuffle_rng_seed=random_seed, permutations=n, phase_formula='(2*pi*wing_hz*time_s) mod 2*pi', phase_reference='nominal continuous sinusoidal clock; visual frames and scene held between sample times', bins=BINS, statistic='mean resultant vector length across all spikes of each neuron', replay_match='moving, stationary and occluded event times and IDs match to 1e-9 s')
    (dest / 'analysis_metadata.json').write_text(json.dumps(result_meta, ensure_ascii=False, indent=2), encoding='utf-8')
    statistics = {c: phase_stats(*obs, freq) for c, obs in observed.items()}
    rng = np.random.default_rng(random_seed)
    shuffle_strength = np.empty((n, 32))
    shuffle_counts = np.empty((n, 32), dtype=int)
    # Events and frame indices are retained, so the analysis remains auditable.
    with (dest / 'shuffle_spikes.csv').open('w', encoding='utf-8-sig', newline='') as sf, (dest / 'shuffle_permutations.csv').open('w', encoding='utf-8-sig', newline='') as pf:
        sw, pw = csv.writer(sf), csv.writer(pf)
        sw.writerow(['trial', 'time_s', 'neuron_id'])
        pw.writerow(['trial', 'output_frame', 'source_frame'])
        for j in range(n):
            perm = rng.permutation(frames_count)
            pw.writerows((j + 1, k, int(source)) for k, source in enumerate(perm))
            ts, ids, _ = engine.simulate(engine.features(frames[perm]), 1 / fps, seed)
            sw.writerows((j + 1, float(t), int(i)) for t, i in zip(ts, ids))
            counts, strength, _, _ = phase_stats(ts, ids, freq)
            shuffle_counts[j], shuffle_strength[j] = counts, strength
            if (j + 1) % 10 == 0 or j + 1 == n:
                print(f'Перемешивания: {j + 1}/{n}', flush=True)
    mcount, mr, mphase, _ = statistics['moving']
    save_csv(dest / 'neuron_summary.csv', ['neuron_id', 'eye', 'tile_row', 'tile_col', 'moving_spikes', 'stationary_spikes', 'occluded_spikes', 'moving_vector_strength', 'moving_mean_phase_deg', 'shuffle_strength_median', 'shuffle_strength_min', 'shuffle_strength_max', 'shuffles_strength_ge_moving', 'shuffles_n', 'shuffle_spikes_median'],
        ((i, mapping[i]['eye'], mapping[i]['tile_row'], mapping[i]['tile_col'], int(mcount[i]), int(statistics['stationary'][0][i]), int(statistics['occluded'][0][i]), float(mr[i]), float(np.degrees(mphase[i])) if np.isfinite(mphase[i]) else '', float(np.median(shuffle_strength[:, i])), float(shuffle_strength[:, i].min()), float(shuffle_strength[:, i].max()), int(np.sum(shuffle_strength[:, i] >= mr[i] - 1e-12)), n, float(np.median(shuffle_counts[:, i]))) for i in range(32)))
    save_csv(dest / 'shuffle_neurons.csv', ['trial', 'neuron_id', 'spikes', 'vector_strength'], ((j + 1, i, int(shuffle_counts[j, i]), float(shuffle_strength[j, i])) for j in range(n) for i in range(32)))
    # Exposure on the 1 ms Brian2 clock; appropriate also for incomplete cycles.
    ticks = np.arange(round(duration * 1000)) / 1000
    exposure = np.bincount(np.minimum((np.remainder(2 * np.pi * freq * ticks, 2 * np.pi) * BINS / (2 * np.pi)).astype(int), BINS - 1), minlength=BINS) / 1000
    save_csv(dest / 'phase_bins.csv', ['condition', 'neuron_id', 'bin', 'phase_start_deg', 'phase_end_deg', 'spikes', 'exposure_s', 'rate_hz'], ((c, i, k, k * 360 / BINS, (k + 1) * 360 / BINS, int(stats[3][i, k]), float(exposure[k]), float(stats[3][i, k] / exposure[k]) if exposure[k] else '') for c, stats in statistics.items() for i in range(32) for k in range(BINS)))
    text = f'''АНАЛИЗ ФАЗЫ ВЗМАХА И ПЕРЕМЕШИВАНИЙ\n\nИсточник: {run}\nЧисло перемешиваний: {n}; seed перемешиваний: {random_seed}.\nПроверка: все времена и ID спайков moving, stationary и occluded воспроизведены с точностью 1 нс. Исходные файлы не изменялись.\n\nФаза = (360 × частота крыла × время спайка) по модулю 360 градусов. 0 градусов соответствует прохождению левого крыла через нулевой угол при движении к положительному углу. Это фаза непрерывной заданной синусоиды; сцена и картинка обновляются только на кадрах {fps} Гц, а не непрерывно. Значения на графиках не следует воспринимать как реальную миллисекундную точность зрительного стимула.\n\nДля каждого нейрона vector_strength от 0 до 1: насколько фазы спайков сосредоточены в одном направлении. При отсутствии спайков записан 0, направление отсутствует; сравнение без спайков не информативно. При практически нулевой силе направление оставлено пустым. Средняя фаза может быть неустойчивой при малой силе. phase_bins.csv даёт число спайков и частоту в восьми фазовых интервалах с учётом времени в каждом интервале на сетке 1 мс. stationary и occluded используют ту же условную временную фазу, хотя их зрительный вход не меняется.\n\nКаждый shuffle независимо перемешивает исходные кадры moving; временная ось сравнения остаётся прежней, начальные состояния нейронов те же, что в исходном запуске. shuffle_spikes.csv содержит все новые спайки, shuffle_permutations.csv соответствия кадров. shuffles_strength_ge_moving показывает, сколько перестановок дало такую же или большую силу фазы. Это описательное сравнение, не подтверждённый p-value: исходный порядок и искусственно перемешанные кадры не обязаны быть взаимозаменяемы; перемешивание меняет и разности яркости. 32 нейрона рассматриваются одновременно, поправка на множественность не проводилась.\n\nНабор данных представляет один детерминированный игрушечный эксперимент. Сеть напрямую реагирует на изменение яркости, фоновые фазы заданы искусственно. Нет независимых животных, биологически проверенных нейронов, действия наблюдателя, обучения или проверки зеркальности. Дополнительные пермутации не являются независимыми биологическими повторами.\n'''
    (dest / 'report.txt').write_text(text, encoding='utf-8-sig')
    require(all(sha(run / name) == digest for name, digest in hashes.items()), 'Входные файлы изменились во время анализа; результаты не помечены завершёнными.')
    result_meta['status'] = 'completed'
    result_meta['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (dest / 'analysis_metadata.json').write_text(json.dumps(result_meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print('RESULT_DIR=' + str(dest), flush=True)
    return dest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', help='Папка исходного запуска с metadata.json')
    p.add_argument('--choose', action='store_true', help='Открыть выбор папки')
    p.add_argument('--permutations', type=int, default=100)
    p.add_argument('--shuffle-seed', type=int, default=20261104)
    args = p.parse_args()
    run = args.run
    if args.choose:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
        run = filedialog.askdirectory(title='Выберите папку запуска двух мух с metadata.json', initialdir=str(Path('workspace/runs/ideas/i-observational/two-flies').resolve()))
        root.destroy()
        if not run:
            print('Выбор отменён, исходные файлы не изменены.'); return
    if not run:
        p.error('Укажите --run или --choose')
    dest = analyse(run, args.permutations, args.shuffle_seed)
    if args.choose and os.name == 'nt':
        os.startfile(str(dest))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ОШИБКА: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
