"""Техническая проверка Brian2 на подвыборке вручную подключённых CSV-таблиц.

Это НЕ воспроизведение модели Shiu или опубликованных рисунков. Вес, параметры,
стимуляция и знаки синапсов здесь условные. Результат не является биологическим
выводом. Входные таблицы не изменяются, синтетические данные не подставляются.
"""
import argparse
import csv
import json
import math
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

CHUNK_SIZE = 300_000


def parse_args():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--n-neurons", type=int, default=2000)
    p.add_argument("--duration-ms", type=float, default=200.0)
    p.add_argument("--dt-ms", type=float, default=0.1)
    p.add_argument("--stim-frac", type=float, default=0.05)
    p.add_argument("--stim-amp-pa", type=float, default=250.0)
    p.add_argument("--v-th-mv", type=float, default=-50.0)
    p.add_argument("--v-reset-mv", type=float, default=-65.0)
    p.add_argument("--tau-m-ms", type=float, default=20.0)
    p.add_argument("--tau-syn-ms", type=float, default=5.0,
                   help="Условная постоянная затухания синаптического тока, мс.")
    p.add_argument("--t-refract-ms", type=float, default=2.0)
    p.add_argument("--r-mohm", type=float, default=100.0)
    p.add_argument("--w-scale", type=float, default=1.0)
    return p.parse_args()


def validate_args(args):
    if args.seed < 0 or args.n_neurons < 1:
        raise ValueError("seed должен быть неотрицательным, n-neurons не менее 1.")
    for name in ("duration_ms", "dt_ms", "tau_m_ms", "tau_syn_ms", "r_mohm"):
        value = getattr(args, name)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} должен быть конечным положительным числом.")
    for name in ("stim_frac", "stim_amp_pa", "v_th_mv", "v_reset_mv", "t_refract_ms", "w_scale"):
        if not math.isfinite(getattr(args, name)):
            raise ValueError(f"{name} должен быть конечным числом.")
    if not 0 <= args.stim_frac <= 1 or args.t_refract_ms < 0 or args.w_scale < 0:
        raise ValueError("stim-frac должен быть от 0 до 1; t-refract-ms и w-scale неотрицательны.")
    if args.v_reset_mv >= args.v_th_mv:
        raise ValueError("v-reset-mv должен быть меньше v-th-mv.")
    if args.dt_ms >= min(args.tau_m_ms, args.tau_syn_ms):
        raise ValueError("dt-ms должен быть меньше постоянных времени мембраны и синапса.")
    steps = args.duration_ms / args.dt_ms
    if abs(steps - round(steps)) > 1e-7:
        raise ValueError("duration-ms должен быть кратен dt-ms.")


def input_path(name, required=True):
    value = os.environ.get(name, "").strip()
    if not value:
        if required:
            raise FileNotFoundError(f"{name} не выбран в разделе «Данные и окружение».")
        return None
    result = Path(value)
    if required and not result.is_file():
        raise FileNotFoundError(f"Файл {name} недоступен: {result}")
    if required and not result.name.lower().endswith((".csv", ".csv.gz")):
        raise ValueError(f"{name}: этот тест поддерживает только CSV и CSV.GZ.")
    return result


def chunks(file, columns, dtypes):
    try:
        yield from pd.read_csv(file, usecols=columns, dtype=dtypes, chunksize=CHUNK_SIZE,
                               compression="infer", encoding="utf-8-sig")
    except ValueError as e:
        raise ValueError(f"Не удалось прочитать {file.name}, нужны колонки {', '.join(columns)}: {e}") from e


def check_ids(column, name):
    if column.isna().any() or not column.str.fullmatch(r"[1-9][0-9]*").all():
        raise ValueError(f"{name}: ID должны быть положительными целыми числами без пропусков.")


def choose_neurons(connections, n, seed):
    ids = set()
    for chunk in chunks(connections, ["pre_root_id", "post_root_id"],
                        {"pre_root_id": "string", "post_root_id": "string"}):
        for col in ("pre_root_id", "post_root_id"):
            check_ids(chunk[col], col)
            ids.update(chunk[col].unique().tolist())
    if not ids:
        raise ValueError("В таблице связей нет нейронов.")
    # Сортируем как целые числа, но сами идентификаторы оставляем строками.
    ordered = sorted(ids, key=int)
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(ordered), size=min(n, len(ordered)), replace=False)
    return sorted((ordered[int(i)] for i in indices), key=int), len(ordered)


def subset_connections(file, chosen):
    selected = set(chosen)
    frames = []
    for chunk in chunks(file, ["pre_root_id", "post_root_id", "syn_count"],
                        {"pre_root_id": "string", "post_root_id": "string"}):
        mask = chunk["pre_root_id"].isin(selected) & chunk["post_root_id"].isin(selected)
        if mask.any():
            frames.append(chunk.loc[mask].copy())
    if not frames:
        return pd.DataFrame(columns=["pre_root_id", "post_root_id", "syn_count"])
    sub = pd.concat(frames, ignore_index=True)
    try:
        weights = pd.to_numeric(sub["syn_count"], errors="raise").to_numpy(dtype=float)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Некорректный syn_count в выбранных связях: {e}") from e
    if not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError("В выбранных связях syn_count должен быть конечным положительным числом.")
    sub["syn_count"] = weights
    return sub


def transmitter_map(file, chosen):
    selected = set(chosen)
    mapping = {}
    for chunk in chunks(file, ["root_id", "nt_type"], {"root_id": "string", "nt_type": "string"}):
        match = chunk[chunk["root_id"].isin(selected)]
        for root_id, nt in zip(match["root_id"], match["nt_type"]):
            value = "" if pd.isna(nt) else str(nt).strip().lower()
            if root_id in mapping and mapping[root_id] != value:
                raise ValueError(f"Для нейрона {root_id} в таблице указаны разные nt_type.")
            mapping[root_id] = value
    return mapping


def signed_type(value):
    # Даже эти два класса здесь только техническое приближение.
    if value in ("gaba", "gabaergic"):
        return -1.0
    if value in ("ach", "acetylcholine", "cholinergic"):
        return 1.0
    # Глутамат и другие медиаторы не получают выдуманный знак.
    return 0.0


def simulate(args, sub, chosen, nt_map):
    import brian2 as b2

    b2.prefs.codegen.target = "numpy"
    b2.start_scope()
    b2.defaultclock.dt = args.dt_ms * b2.ms
    n = len(chosen)
    labels = sub["pre_root_id"].map(nt_map).fillna("")
    signs = np.asarray([signed_type(str(value)) for value in labels], dtype=float)
    keep = signs != 0
    ignored = int((~keep).sum())
    ignored_types = labels.loc[~keep].replace("", "(нет данных)").value_counts().to_dict()
    kept = sub.loc[keep].copy()
    idx = {rid: i for i, rid in enumerate(chosen)}
    pre = np.array([idx[value] for value in kept["pre_root_id"]], dtype=int)
    post = np.array([idx[value] for value in kept["post_root_id"]], dtype=int)
    syn_count = kept["syn_count"].to_numpy(dtype=float)
    w = syn_count / syn_count.mean() * signs[keep] * args.w_scale if len(syn_count) else np.array([])

    eqs = """
    dv/dt = (-(v - EL) + R*(I_ext + I_syn)) / tau : volt (unless refractory)
    dI_syn/dt = -I_syn / tau_syn : amp
    I_ext : amp
    """
    params = {"EL": args.v_reset_mv * b2.mV, "R": args.r_mohm * b2.Mohm,
              "tau": args.tau_m_ms * b2.ms, "tau_syn": args.tau_syn_ms * b2.ms,
              "v_th": args.v_th_mv * b2.mV, "v_reset": args.v_reset_mv * b2.mV}
    neurons = b2.NeuronGroup(n, eqs, threshold="v > v_th", reset="v = v_reset",
                             refractory=args.t_refract_ms * b2.ms, method="euler",
                             name="neurons", namespace=params)
    neurons.v = params["v_reset"]
    neurons.I_syn = 0 * b2.pA
    rng = np.random.default_rng(args.seed + 1)
    n_stim = min(n, int(round(args.stim_frac * n)))
    stim_idx = rng.choice(n, size=n_stim, replace=False)
    current = np.zeros(n)
    current[stim_idx] = args.stim_amp_pa
    neurons.I_ext = current * b2.pA

    synapses = None
    if len(w):
        synapses = b2.Synapses(neurons, neurons, model="w_syn : 1",
                               on_pre="I_syn_post += w_syn * pA", name="synapses")
        synapses.connect(i=pre, j=post)
        synapses.w_syn = w
    spikes = b2.SpikeMonitor(neurons)
    net = b2.Network(neurons, spikes)
    if synapses is not None:
        net.add(synapses)
    start = time.perf_counter()
    net.run(args.duration_ms * b2.ms, namespace={})
    wall = time.perf_counter() - start
    spike_i = np.asarray(spikes.i, dtype=int)
    spike_t = np.asarray(spikes.t / b2.ms, dtype=float)
    counts = np.bincount(spike_i, minlength=n)
    rates = counts / (args.duration_ms / 1000.0)
    metrics = {
        "n_neurons": n, "candidate_edges": int(len(sub)), "used_edges": int(len(w)),
        "ignored_edges_unknown_sign": ignored, "ignored_types": {str(k): int(v) for k, v in ignored_types.items()},
        "n_stimulated": n_stim, "total_spikes": int(len(spike_i)),
        "mean_rate_hz": float(rates.mean()), "median_rate_hz": float(np.median(rates)),
        "max_rate_hz": float(rates.max()), "frac_silent": float((rates == 0).mean()),
        "wall_seconds": wall, "effective_dt_ms": float(b2.defaultclock.dt / b2.ms),
        "spike_neurons": spike_i[:5000].tolist(), "spike_times_ms": spike_t[:5000].tolist(),
        "spikes_in_summary_truncated": len(spike_i) > 5000,
    }
    return metrics, spike_i, spike_t, rates


def main():
    args = parse_args()
    folder = os.environ.get("FLY_RUN_DIR", "").strip()
    if not folder:
        print("FLY_RUN_DIR не задан: запустите скрипт из приложения.", file=sys.stderr)
        return 2
    run_dir = Path(folder)
    run_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "args": vars(args), "metrics": {}, "files": [], "status": "pending",
        "scope": "Техническая проверка на подвыборке, не воспроизведение модели или рисунков Shiu.",
        "caveats": [
            "Параметры LIF и затухание тока условные, не сверены с моделью Shiu.",
            "GABA и ACh используются как условные отрицательные и положительные знаки, а не доказанные действия отдельных синапсов.",
            "Связи с другими или отсутствующими типами медиатора исключаются; число исключений указано в metrics.",
            "Вес равен syn_count / средний syn_count оставшихся связей, в условных pA; не калиброван.",
            "Таблицы и версия коннектома не проверены как исходные данные Shiu.",
        ],
    }
    try:
        validate_args(args)
        connections = input_path("FLY_CONNECTOME")
        neurotransmitters = input_path("FLY_NEUROTRANSMITTERS")
        summary["data_paths"] = {"connections": str(connections), "neurotransmitters": str(neurotransmitters)}
        before = (connections.stat().st_size, connections.stat().st_mtime_ns)
        chosen, total_ids = choose_neurons(connections, args.n_neurons, args.seed)
        sub = subset_connections(connections, chosen)
        after = (connections.stat().st_size, connections.stat().st_mtime_ns)
        if before != after:
            raise RuntimeError("Таблица связей изменилась во время чтения. Повторите запуск.")
        nt_before = (neurotransmitters.stat().st_size, neurotransmitters.stat().st_mtime_ns)
        nt_map = transmitter_map(neurotransmitters, chosen)
        nt_after = (neurotransmitters.stat().st_size, neurotransmitters.stat().st_mtime_ns)
        if nt_before != nt_after:
            raise RuntimeError("Таблица медиаторов изменилась во время чтения. Повторите запуск.")
        metrics, spike_i, spike_t, rates = simulate(args, sub, chosen, nt_map)
        metrics["available_neuron_ids"] = total_ids
        with (run_dir / "sample_rates.csv").open("w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["sample_index", "source_root_id", "rate_hz"])
            writer.writerows((i, root_id, float(rates[i])) for i, root_id in enumerate(chosen))
        with (run_dir / "spikes.csv").open("w", encoding="utf-8", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(["time_ms", "sample_index", "source_root_id"])
            writer.writerows((float(t), int(i), chosen[int(i)]) for i, t in zip(spike_i, spike_t))
        summary["metrics"] = metrics
        summary["files"] = ["sample_rates.csv", "spikes.csv"]
        summary["status"] = "ok"
        if metrics["used_edges"] == 0:
            summary["caveats"].append("Нет использованных связей: это тест независимых нейронов, а не работы сети.")
    except Exception as e:
        summary["status"] = "error"
        summary["error"] = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Отчёт: {run_dir / 'summary.json'}\nСтатус: {summary['status']}")
    if summary["status"] == "ok":
        m = summary["metrics"]
        print(f"нейронов={m['n_neurons']} связей={m['used_edges']} спайков={m['total_spikes']}")
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
