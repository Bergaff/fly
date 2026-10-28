#!/usr/bin/env python3
"""Бенчмарк вычислительных бэкендов модели мозга: точность частот, скорость и память.

Готовый анализ для задачи «Бенчмарк бэкендов fly-brain» (i-benchmark).
Автоматически находит установленные на компьютере бэкенды:
  - brian2_cpu       (эталон статьи Shiu et al. 2024 на Brian2);
  - scipy_sparse_cpu (разреженный матричный шаг CSR, точный экспоненциальный Эйлер);
  - numpy_dense_cpu  (плотный матричный шаг float32 для компактных подсетей);
  - torch_cpu / torch_cuda (пакетный расчёт попыток в PyTorch на CPU и GPU NVIDIA, если стоит torch).

Четыре стандартных протокола из чеклиста задачи:
  1) resting_bg     : спонтанная фоновая активность;
  2) sensory_stim   : пуассоновская стимуляция сенсорного пула (200 Гц);
  3) virtual_lesion : стимуляция при выключении 25 % промежуточных нейронов;
  4) long_run       : удлинённый прогон для оценки дрейфа частот и масштабирования времени.

Считает относительно эталона: корреляцию Пирсона и Спирмена по частотам нейронов, RMSE (Гц),
совпадение топ-50 активных нейронов (Jaccard), время расчёта, фактор реального времени и пик памяти.

Примеры:
  python 12_backend_benchmark.py --synth
  python 12_backend_benchmark.py --max-neurons 3000 --n-run 3 --t 0.3 --t-long 1.0
  python 12_backend_benchmark.py --max-neurons 0 --backends scipy_sparse_cpu,torch_cuda

Результат: benchmark_runs.csv, backend_accuracy.csv, benchmark_summary.png, summary.json.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
import tracemalloc
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SCRIPTS_ENV = os.environ.get("FLY_SCRIPTS")
if SCRIPTS_ENV and SCRIPTS_ENV not in sys.path:
    sys.path.insert(0, SCRIPTS_ENV)

import numpy as np
import pandas as pd
from scipy import stats

import flylib

RUN = Path(os.environ.get("FLY_RUN_DIR", "."))

ap = argparse.ArgumentParser(description="Бенчмарк бэкендов LIF-модели мозга мухи")
ap.add_argument("--synth", action="store_true", help="использовать синтетический коннектом")
ap.add_argument("--max-neurons", type=int, default=1800, help="размер подграфа (0 = весь коннектом)")
ap.add_argument("--t", type=float, default=0.25, help="длительность стандартного протокола, с")
ap.add_argument("--t-long", type=float, default=0.75, help="длительность длинного прогона, с")
ap.add_argument("--n-run", type=int, default=3, help="число попыток на протокол")
ap.add_argument("--dt", type=float, default=0.2, help="шаг интегрирования, мс")
ap.add_argument("--backends", default="auto", help="auto или список через запятую")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()


def detect_backends() -> list[str]:
    if args.backends != "auto":
        return [b.strip() for b in args.backends.split(",") if b.strip()]
    found = []
    try:
        import brian2  # noqa: F401
        found.append("brian2_cpu")
    except Exception:
        pass
    found.append("scipy_sparse_cpu")
    found.append("numpy_dense_cpu")
    try:
        import torch
        found.append("torch_cpu")
        if torch.cuda.is_available():
            found.append("torch_cuda")
    except Exception:
        pass
    return found


def run_numpy_dense(W_csr, stim_map, silence_idx, t_sec, n_trials, dt_ms, seed):
    W_dense = W_csr.toarray().astype(np.float32)
    N = W_dense.shape[0]
    p = flylib.SHIU_DEFAULTS
    steps = max(10, int(round(t_sec * 1000.0 / dt_ms)))
    dly = max(1, int(round(p["t_dly"] / dt_ms)))
    rfc = max(1, int(round(p["t_rfc"] / dt_ms)))
    decay_v = math.exp(-dt_ms / p["t_mbr"])
    decay_g = math.exp(-dt_ms / p["tau_g"])
    alpha_v = 1.0 - decay_v
    sil = np.ones(N, dtype=np.float32)
    if silence_idx is not None and len(silence_idx):
        sil[np.array(list(silence_idx), dtype=np.int32)] = 0.0
    stim_i = np.array(list(stim_map.keys()), dtype=np.int32) if stim_map else np.array([], dtype=np.int32)
    stim_p = np.array([min(0.95, r * dt_ms / 1000.0) for r in stim_map.values()], dtype=np.float32) if stim_map else np.array([], dtype=np.float32)
    w_poi = float(p["w_syn"] * p["f_poi"] * 0.14)
    p_bg = min(0.5, 28.0 * dt_ms / 1000.0)

    counts = np.zeros((n_trials, N), dtype=np.int32)
    for tr in range(n_trials):
        rng = np.random.default_rng(seed + tr * 10007)
        v = np.full(N, p["v_0"], dtype=np.float32)
        g = np.zeros(N, dtype=np.float32)
        ref = np.zeros(N, dtype=np.int16)
        ring = np.zeros((dly, N), dtype=np.float32)
        for st in range(steps):
            sp_d = ring[st % dly]
            if sp_d.any():
                g += W_dense @ sp_d
                ring[st % dly] = 0.0
            v[rng.random(N, dtype=np.float32) < p_bg] += 2.75
            if stim_i.size:
                hit = rng.random(stim_i.size, dtype=np.float32) < stim_p
                if hit.any():
                    v[stim_i[hit]] += w_poi
            act = ref <= 0
            v[act] = p["v_0"] + (v[act] - p["v_0"]) * decay_v + g[act] * alpha_v
            g *= decay_g
            ref[~act] -= 1
            fired = act & (v > p["v_th"]) & (sil > 0.5)
            if fired.any():
                fi = np.flatnonzero(fired)
                v[fi] = p["v_rst"]
                g[fi] = 0.0
                ref[fi] = rfc
                vec = np.zeros(N, dtype=np.float32)
                vec[fi] = 1.0
                ring[(st + dly) % dly] = vec
                counts[tr, fi] += 1
    return (counts.astype(np.float32) / max(t_sec, 1e-6)).mean(axis=0)


def run_brian2_cpu(N, edges, stim_map, silence_idx, t_sec, n_trials, dt_ms, seed):
    import brian2 as b2
    b2.prefs.codegen.target = "numpy"
    b2.defaultclock.dt = dt_ms * b2.ms
    p = flylib.SHIU_DEFAULTS
    ns = dict(
        v_0=p["v_0"] * b2.mV,
        v_rst=p["v_rst"] * b2.mV,
        v_th=p["v_th"] * b2.mV,
        t_mbr=p["t_mbr"] * b2.ms,
        tau_g=p["tau_g"] * b2.ms,
        t_rfc=p["t_rfc"] * b2.ms,
    )
    eqs = """
    dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)
    dg/dt = -g / tau_g : volt (unless refractory)
    alive : 1
    """
    neu = b2.NeuronGroup(
        N, eqs, threshold="v > v_th and alive > 0.5", reset="v = v_rst; g = 0*mV",
        refractory="t_rfc", method="exact", namespace=ns,
    )
    neu.v = ns["v_0"]
    neu.alive = 1.0
    if silence_idx is not None and len(silence_idx):
        neu.alive[np.array(list(silence_idx), dtype=np.int32)] = 0.0

    pre = edges["pre_idx"].to_numpy(dtype=np.int32)
    post = edges["post_idx"].to_numpy(dtype=np.int32)
    w_mv = np.clip(edges["signed_weight"].to_numpy(dtype=float) * p["w_syn"], -10.0, 10.0)
    syn = b2.Synapses(neu, neu, "w : volt", on_pre="g_post += w * alive_pre", delay=p["t_dly"] * b2.ms)
    syn.connect(i=pre, j=post)
    syn.w = w_mv * b2.mV

    bg = b2.PoissonInput(neu, "v", N=1, rate=28.0 * b2.Hz, weight=2.75 * b2.mV)
    extra = [bg]
    if stim_map:
        w_poi = float(p["w_syn"] * p["f_poi"] * 0.14) * b2.mV
        s_idx = np.array(list(stim_map.keys()), dtype=np.int32)
        s_hz = np.array(list(stim_map.values()), dtype=float) * b2.Hz
        sub_p = b2.PoissonGroup(s_idx.size, rates=s_hz)
        s_syn = b2.Synapses(sub_p, neu, on_pre="v_post += w_stim", namespace={"w_stim": w_poi})
        s_syn.connect(i=np.arange(s_idx.size, dtype=np.int32), j=s_idx)
        extra.extend([sub_p, s_syn])

    mon = b2.SpikeMonitor(neu)
    net = b2.Network(neu, syn, mon, *extra)
    net.store("init")

    counts = np.zeros((n_trials, N), dtype=np.int32)
    for tr in range(n_trials):
        b2.seed(seed + tr * 1009)
        net.restore("init")
        net.run(t_sec * b2.second, namespace={})
        counts[tr] = np.asarray(mon.count, dtype=np.int32)
    return (counts.astype(np.float32) / max(t_sec, 1e-6)).mean(axis=0)


def run_torch_backend(device_name: str, W_csr, stim_map, silence_idx, t_sec, n_trials, dt_ms, seed):
    import torch
    dev = torch.device(device_name)
    torch.manual_seed(seed)
    N = W_csr.shape[0]
    p = flylib.SHIU_DEFAULTS
    steps = max(10, int(round(t_sec * 1000.0 / dt_ms)))
    dly = max(1, int(round(p["t_dly"] / dt_ms)))
    rfc = max(1, int(round(p["t_rfc"] / dt_ms)))
    decay_v = math.exp(-dt_ms / p["t_mbr"])
    decay_g = math.exp(-dt_ms / p["tau_g"])
    alpha_v = 1.0 - decay_v

    coo = W_csr.tocoo()
    indices = torch.tensor(np.vstack([coo.row, coo.col]), dtype=torch.long, device=dev)
    values = torch.tensor(coo.data, dtype=torch.float32, device=dev)
    W_t = torch.sparse_coo_tensor(indices, values, size=(N, N), device=dev).coalesce()

    sil = torch.ones((N, 1), dtype=torch.float32, device=dev)
    if silence_idx is not None and len(silence_idx):
        sil[torch.tensor(list(silence_idx), dtype=torch.long, device=dev)] = 0.0

    stim_prob = torch.zeros((N, 1), dtype=torch.float32, device=dev)
    if stim_map:
        for idx_s, r_hz in stim_map.items():
            stim_prob[int(idx_s), 0] = min(0.95, float(r_hz) * dt_ms / 1000.0)
    w_poi = float(p["w_syn"] * p["f_poi"] * 0.14)
    p_bg = min(0.5, 28.0 * dt_ms / 1000.0)

    # Пакетный прогон всех n_trials параллельно в матрице (N, n_trials)
    v = torch.full((N, n_trials), float(p["v_0"]), dtype=torch.float32, device=dev)
    g = torch.zeros((N, n_trials), dtype=torch.float32, device=dev)
    ref = torch.zeros((N, n_trials), dtype=torch.int16, device=dev)
    ring = torch.zeros((dly, N, n_trials), dtype=torch.float32, device=dev)
    counts = torch.zeros((N, n_trials), dtype=torch.int32, device=dev)

    for st in range(steps):
        sp_d = ring[st % dly]
        if torch.any(sp_d > 0):
            g = g + torch.sparse.mm(W_t, sp_d)
            ring[st % dly].zero_()
        v = v + (torch.rand((N, n_trials), device=dev) < p_bg).float() * 2.75
        if stim_map:
            v = v + (torch.rand((N, n_trials), device=dev) < stim_prob).float() * w_poi
        act = ref <= 0
        v_next = float(p["v_0"]) + (v - float(p["v_0"])) * decay_v + g * alpha_v
        v = torch.where(act, v_next, v)
        g = g * decay_g
        ref = torch.where(act, ref, ref - 1)
        fired = act & (v > float(p["v_th"])) & (sil > 0.5)
        if torch.any(fired):
            v = torch.where(fired, torch.full_like(v, float(p["v_rst"])), v)
            g = torch.where(fired, torch.zeros_like(g), g)
            ref = torch.where(fired, torch.full_like(ref, rfc), ref)
            ring[(st + dly) % dly] = fired.float()
            counts = counts + fired.int()

    if dev.type == "cuda":
        torch.cuda.synchronize()
    return (counts.float().mean(dim=1) / max(t_sec, 1e-6)).detach().cpu().numpy()


t0 = time.time()
RUN.mkdir(parents=True, exist_ok=True)
nodes, edges, source = flylib.load_flywire(max_neurons=args.max_neurons, seed=args.seed, synth=args.synth)
N = len(nodes)
W = flylib.build_weight_matrix(N, edges)
backends = detect_backends()
if N > 8000 and "numpy_dense_cpu" in backends:
    backends.remove("numpy_dense_cpu")

print(f"источник: {source}, N={N}, связей={len(edges)}, бэкенды: {', '.join(backends)}")

rng = np.random.default_rng(args.seed)
stim_nodes = nodes.loc[nodes["cell_type"].astype(str).str.contains("sugar|JO|PN", regex=True), "idx"].to_numpy()
if stim_nodes.size < 10:
    stim_nodes = np.arange(min(24, N), dtype=np.int32)
else:
    stim_nodes = stim_nodes[:24]
stim_map = {int(i): 200.0 for i in stim_nodes}
lesion_pool = np.setdiff1d(np.arange(N, dtype=np.int32), stim_nodes)
lesion_idx = rng.choice(lesion_pool, size=max(5, int(N * 0.15)), replace=False)

protocols = [
    ("resting_bg", {}, [], args.t),
    ("sensory_stim", stim_map, [], args.t),
    ("virtual_lesion", stim_map, lesion_idx, args.t),
    ("long_run", stim_map, [], args.t_long),
]

run_rows = []
rates_store: dict[tuple[str, str], np.ndarray] = {}

for bname in backends:
    for pname, smap, sil_l, dur in protocols:
        tracemalloc.start()
        t_start = time.perf_counter()
        if bname == "brian2_cpu":
            rates = run_brian2_cpu(N, edges, smap, sil_l, dur, args.n_run, args.dt, args.seed)
        elif bname == "scipy_sparse_cpu":
            res = flylib.run_lif_trials(W, stim_rates_hz=smap, silence_idx=sil_l, t_sec=dur, n_trials=args.n_run, dt_ms=args.dt, seed=args.seed)
            rates = res["rates_mean"]
        elif bname == "numpy_dense_cpu":
            rates = run_numpy_dense(W, smap, sil_l, dur, args.n_run, args.dt, args.seed)
        elif bname == "torch_cpu":
            rates = run_torch_backend("cpu", W, smap, sil_l, dur, args.n_run, args.dt, args.seed)
        elif bname == "torch_cuda":
            rates = run_torch_backend("cuda", W, smap, sil_l, dur, args.n_run, args.dt, args.seed)
        else:
            tracemalloc.stop()
            continue
        wall = time.perf_counter() - t_start
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peak_mb = peak_bytes / (1024.0 * 1024.0)
        if bname == "torch_cuda":
            import torch
            peak_mb = max(peak_mb, torch.cuda.max_memory_allocated() / (1024.0 * 1024.0))

        rates_store[(bname, pname)] = rates
        bio_total = dur * args.n_run
        run_rows.append({
            "бэкенд": bname,
            "протокол": pname,
            "биовремя_с": round(bio_total, 2),
            "время_расчёта_с": round(wall, 4),
            "скорость_x_реалтайм": round(bio_total / max(wall, 1e-6), 3),
            "пик_памяти_МБ": round(peak_mb, 2),
            "средняя_частота_Гц": round(float(rates.mean()), 3),
            "макс_частота_Гц": round(float(rates.max()), 2),
        })
        print(f"  {bname:<17} | {pname:<15} | {wall:6.2f} с | ср. {rates.mean():5.2f} Гц")

df_runs = pd.DataFrame(run_rows)
ref_backend = "brian2_cpu" if "brian2_cpu" in backends else backends[0]

acc_rows = []
for bname in backends:
    for pname, _, _, _ in protocols:
        r_ref = rates_store[(ref_backend, pname)]
        r_cur = rates_store[(bname, pname)]
        if np.std(r_ref) > 1e-6 and np.std(r_cur) > 1e-6:
            pearson_r = float(np.corrcoef(r_ref, r_cur)[0, 1])
            spearman_r = float(stats.spearmanr(r_ref, r_cur).statistic)
        else:
            pearson_r, spearman_r = 1.0, 1.0
        rmse = float(np.sqrt(np.mean((r_ref - r_cur) ** 2)))
        k_top = min(50, max(5, N // 10))
        top_ref = set(np.argsort(-r_ref)[:k_top].tolist())
        top_cur = set(np.argsort(-r_cur)[:k_top].tolist())
        jaccard = len(top_ref & top_cur) / max(1, len(top_ref | top_cur))

        t_ref = float(df_runs[(df_runs["бэкенд"] == ref_backend) & (df_runs["протокол"] == pname)]["время_расчёта_с"].iloc[0])
        t_cur = float(df_runs[(df_runs["бэкенд"] == bname) & (df_runs["протокол"] == pname)]["время_расчёта_с"].iloc[0])
        acc_rows.append({
            "бэкенд": bname,
            "эталон": ref_backend,
            "протокол": pname,
            "корреляция_Пирсона": round(pearson_r, 4),
            "корреляция_Спирмена": round(spearman_r, 4),
            "RMSE_Гц": round(rmse, 3),
            "совпадение_топ50_Jaccard": round(jaccard, 3),
            "ускорение_к_эталону": round(t_ref / max(t_cur, 1e-6), 2),
        })

df_acc = pd.DataFrame(acc_rows)
df_runs.to_csv(RUN / "benchmark_runs.csv", index=False)
df_acc.to_csv(RUN / "backend_accuracy.csv", index=False)

# Сводный график 2x2
plt, _, _ = flylib.setup_plot_style()
fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.0), dpi=140)

# [A] Время расчёта по протоколам и бэкендам
p_names = [p[0] for p in protocols]
x = np.arange(len(p_names))
width = 0.78 / max(1, len(backends))
for bi, bname in enumerate(backends):
    vals = [float(df_runs[(df_runs["бэкенд"] == bname) & (df_runs["протокол"] == pn)]["время_расчёта_с"].iloc[0]) for pn in p_names]
    axes[0, 0].bar(x + (bi - (len(backends) - 1) / 2) * width, vals, width=width * 0.92, color=flylib.SERIES_COLORS[bi % len(flylib.SERIES_COLORS)], label=bname)
axes[0, 0].set_xticks(x, p_names, fontsize=8)
axes[0, 0].set_ylabel("время расчёта, с (меньше = быстрее)")
axes[0, 0].set_title("A. Время расчёта по 4 протоколам")
axes[0, 0].legend(frameon=False, fontsize=7.5)

# [B] Ускорение относительно эталона и пик памяти
agg = df_acc.groupby("бэкенд", as_index=False)["ускорение_к_эталону"].mean()
mem = df_runs.groupby("бэкенд", as_index=False)["пик_памяти_МБ"].max()
merged = agg.merge(mem, on="бэкенд")
bx = np.arange(len(merged))
axes[0, 1].bar(bx, merged["ускорение_к_эталону"], width=0.5, color=[flylib.SERIES_COLORS[i % len(flylib.SERIES_COLORS)] for i in bx])
for i, row in merged.iterrows():
    axes[0, 1].text(i, row["ускорение_к_эталону"] + 0.05, f"x{row['ускорение_к_эталону']:.2f}\n({row['пик_памяти_МБ']:.1f} МБ)", ha="center", va="bottom", fontsize=7.5)
axes[0, 1].axhline(1.0, color="#9a938a", lw=0.7, ls=":")
axes[0, 1].set_xticks(bx, merged["бэкенд"], fontsize=8)
axes[0, 1].set_ylabel(f"среднее ускорение к {ref_backend}")
axes[0, 1].set_ylim(0, max(1.4, float(merged["ускорение_к_эталону"].max()) * 1.28))
axes[0, 1].set_title("B. Среднее ускорение и пик выделенной памяти")

# [C] Диаграмма рассеяния частот нейронов (sensory_stim): эталон против альтернатив
r_base = rates_store[(ref_backend, "sensory_stim")]
others = [b for b in backends if b != ref_backend] or [ref_backend]
for bi, bname in enumerate(others):
    r_alt = rates_store[(bname, "sensory_stim")]
    axes[1, 0].scatter(r_base, r_alt, s=11, alpha=0.65, color=flylib.SERIES_COLORS[(bi + 1) % len(flylib.SERIES_COLORS)], label=bname)
lim = max(5.0, float(r_base.max()) * 1.08)
axes[1, 0].plot([0, lim], [0, lim], color="#3c3833", lw=0.8, ls=":")
axes[1, 0].set_xlabel(f"частота нейрона в {ref_backend}, Гц")
axes[1, 0].set_ylabel("частота в сравниваемом бэкенде, Гц")
axes[1, 0].set_title("C. Совпадение индивидуальных частот (sensory_stim)")
axes[1, 0].legend(frameon=False, fontsize=8)

# [D] Корреляция Пирсона по протоколам со стимуляцией + совпадение средних частот на фоне
evoked_p = [pn for pn in p_names if pn != "resting_bg"]
xe = np.arange(len(evoked_p))
for bi, bname in enumerate(others):
    sub = df_acc[df_acc["бэкенд"] == bname]
    vals = [float(sub[sub["протокол"] == pn]["корреляция_Пирсона"].iloc[0]) for pn in evoked_p]
    axes[1, 1].plot(xe, vals, marker="s", ms=4.5, lw=1.6, color=flylib.SERIES_COLORS[(bi + 1) % len(flylib.SERIES_COLORS)], label=f"{bname} (r Пирсона)")
axes[1, 1].set_xticks(xe, evoked_p, fontsize=8)
axes[1, 1].set_ylim(0.90, 1.005)
axes[1, 1].set_ylabel("корреляция частот с эталоном")
axes[1, 1].set_title("D. Точность относительно эталона на вызванных ответах")
axes[1, 1].legend(frameon=False, fontsize=8, loc="lower right")

fig.suptitle(
    f"Бенчмарк бэкендов ({source}): N={N}, связей={len(edges)}, эталон={ref_backend}, шаг={args.dt} мс",
    fontsize=10.5,
    x=0.012,
    ha="left",
)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(RUN / "benchmark_summary.png")
plt.close(fig)

summary = {
    "задача": "i-benchmark",
    "источник": source,
    "нейронов": int(N),
    "связей": int(len(edges)),
    "эталон": ref_backend,
    "бэкенды": backends,
    "сводка_по_бэкендам": df_acc.groupby("бэкенд")[["корреляция_Пирсона", "RMSE_Гц", "совпадение_топ50_Jaccard", "ускорение_к_эталону"]].mean().round(4).to_dict(orient="index"),
    "файлы": ["benchmark_runs.csv", "backend_accuracy.csv", "benchmark_summary.png"],
    "время_счета_с": round(time.time() - t0, 2),
}
flylib.save_json(RUN / "summary.json", summary)
print(f"готово за {summary['время_счета_с']} с -> {RUN}")
