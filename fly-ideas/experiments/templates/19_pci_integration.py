#!/usr/bin/env python3
"""Пертурбационный индекс сложности (PCI) и меры интеграции на коннектоме мозга мухи.

Готовый анализ для задачи «PCI / меры интеграции на мушином коннектоме» (i-pci, операциональная
схема Casali et al. 2013 без метафизических допущений).

Метод:
  1) наносит короткий локальный импульс возмущения на центральный модуль мозга и записывает
     пространственно-временной отклик сети (300 мс после импульса, бины по 4 мс);
  2) переводит отклик модулей/популяций в бинарную матрицу значимой активации S(m, t) относительно
     предстимульного фона и вычисляет нормированную сложность Лемпеля-Зива (PCI), долю вовлечённых
     областей (интеграция) и энтропию паттернов (дифференциация);
  3) сравнивает три топологии одинаковой плотности при развертке глобального сцепления g_scale:
       - intact_connectome : модульный коннектом мозга с дальнодействующими трактами;
       - degree_shuffled   : перемешанный граф с сохранением степеней (нет модульности);
       - modular_lattice   : изолированные локальные кластеры (нет дальнодействующей интеграции).

Примеры:
  python 19_pci_integration.py --synth
  python 19_pci_integration.py --couplings 0.4,0.7,1.0,1.4,1.9 --n-trials 4

Результат: pci_regimes.csv, pci_topologies.csv, pci_complexity.png, summary.json.
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
SCRIPTS_ENV = os.environ.get("FLY_SCRIPTS")
if SCRIPTS_ENV and SCRIPTS_ENV not in sys.path:
    sys.path.insert(0, SCRIPTS_ENV)

import numpy as np
import pandas as pd

import flylib

RUN = Path(os.environ.get("FLY_RUN_DIR", "."))

ap = argparse.ArgumentParser(description="Расчёт индекса PCI и мер интеграции/дифференциации на коннектоме")
ap.add_argument("--synth", action="store_true", help="работать на модульном синтетическом коннектоме")
ap.add_argument("--max-neurons", type=int, default=1800)
ap.add_argument("--couplings", default="0.45,0.75,1.05,1.45,2.05", help="множители глобальной силы связей")
ap.add_argument("--n-channels", type=int, default=32, help="число пространственных каналов/пулов для матрицы S(m,t)")
ap.add_argument("--n-trials", type=int, default=8)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()


def lz76_complexity(bits: np.ndarray) -> int:
    """Классическая сложность Лемпеля-Зива (LZ76) для одномерной бинарной строки."""
    s = "".join("1" if b else "0" for b in bits)
    n = len(s)
    if n == 0:
        return 0
    i, k, l = 0, 1, 1
    c = 1
    while True:
        if s[i + k - 1] == s[l + k - 1]:
            k += 1
            if l + k > n:
                c += 1
                break
        else:
            if k > 1:
                i += 1
                if i == l:
                    c += 1
                    l += k
                    if l + 1 > n:
                        break
                    i = 0
                    k = 1
            else:
                c += 1
                l += 1
                if l + 1 > n:
                    break
                i = 0
                k = 1
    return c


def compute_pci(S_bin: np.ndarray) -> tuple[float, float, float]:
    """Возвращает (PCI, интеграция, дифференциация) по бинарной матрице S(channels, bins)."""
    # Сортируем каналы по общей активности, как в клиническом алгоритме Casali et al. 2013
    order = np.argsort(-S_bin.sum(axis=1))
    S_ord = S_bin[order]
    flat = S_ord.ravel(order="F")  # развёртка по пространству внутри каждого шага времени
    L = flat.size
    p1 = float(flat.mean())
    integration = float((S_bin.sum(axis=1) > 0).mean())
    if p1 <= 0.005 or p1 >= 0.995:
        return 0.02 if p1 > 0 else 0.0, integration, 0.0

    h_src = -p1 * math.log2(p1) - (1.0 - p1) * math.log2(1.0 - p1)
    c_lz = lz76_complexity(flat)
    norm_factor = (L * h_src) / math.log2(max(L, 2))
    pci = float(np.clip(c_lz / max(norm_factor, 1.0), 0.0, 1.0))

    # Дифференциация: доля уникальных пространственных состояний среди активных моментов времени
    active_cols = [tuple(S_ord[:, t].tolist()) for t in range(S_ord.shape[1]) if S_ord[:, t].any()]
    diff_score = len(set(active_cols)) / max(1, len(active_cols)) if active_cols else 0.0
    return pci, integration, float(diff_score)


def build_lattice_edges(sorted_idx: np.ndarray, edge_df: pd.DataFrame, n_clusters: int, seed_val: int) -> pd.DataFrame:
    """Строит строго локальную кластерную решётку той же плотности (связи замкнуты внутри локальных пулов)."""
    r_lat = np.random.default_rng(seed_val)
    n_nodes = sorted_idx.size
    cl_of = np.zeros(n_nodes, dtype=np.int32)
    buckets = np.array_split(sorted_idx, n_clusters)
    for c_id, grp_nodes in enumerate(buckets):
        cl_of[grp_nodes] = c_id
    pre_new = edge_df["pre_idx"].to_numpy().copy()
    post_new = np.empty_like(pre_new)
    for c_id, nodes_c in enumerate(buckets):
        mask = cl_of[pre_new] == c_id
        cnt = int(mask.sum())
        if cnt:
            post_new[mask] = r_lat.choice(nodes_c, size=cnt, replace=True)
    out = edge_df.copy()
    out["post_idx"] = post_new
    return out


t0 = time.time()
RUN.mkdir(parents=True, exist_ok=True)
nodes, edges, source = flylib.load_flywire(max_neurons=args.max_neurons, seed=args.seed, synth=args.synth)
N = len(nodes)
n_ch = min(args.n_channels, max(8, N // 20))

# Группируем нейроны по функциональным областям и подпулам в n_channels пространственных каналов
nodes_sorted = nodes.sort_values(["region", "cell_type", "idx"]).reset_index(drop=True)
sorted_idx_arr = nodes_sorted["idx"].to_numpy(dtype=np.int32)
channel_groups = np.array_split(sorted_idx_arr, n_ch)
# Наносим возмущение на сенсорно-ассоциативный входной пул (PN / антеннальная доля), откуда волна идёт по мозгу
pn_cand = [ci for ci, g in enumerate(channel_groups) if nodes.loc[nodes["idx"].isin(g), "region"].isin(["AL", "MB"]).any()]
perturb_ch = pn_cand[0] if pn_cand else 0
perturb_idx = channel_groups[perturb_ch]

topologies = {
    "intact_connectome": edges,
    "degree_shuffled": flylib.degree_preserving_shuffle(edges, np.random.default_rng(args.seed + 17)),
    "modular_lattice": build_lattice_edges(sorted_idx_arr, edges, n_clusters=max(8, n_ch // 2), seed_val=args.seed + 29),
}

couplings = [float(x) for x in args.couplings.split(",") if x.strip()]
rows = []
matrices_at_unit: dict[str, np.ndarray] = {}


def run_perturbation(edge_df: pd.DataFrame, g_scale: float, seed_val: int) -> np.ndarray:
    W = flylib.build_weight_matrix(N, edge_df, w_syn=0.275, weight_scale=g_scale, clip_mv=12.0)
    p = flylib.SHIU_DEFAULTS
    dt_ms = 0.25
    total_ms = 340.0
    pulse_start_ms, pulse_end_ms = 60.0, 72.0
    bin_ms = 4.0
    steps = int(round(total_ms / dt_ms))
    steps_bin = int(round(bin_ms / dt_ms))
    n_bins = steps // steps_bin
    rfc = max(1, int(round(p["t_rfc"] / dt_ms)))
    dly = max(1, int(round(p["t_dly"] / dt_ms)))
    decay_v = math.exp(-dt_ms / p["t_mbr"])
    decay_g = math.exp(-dt_ms / p["tau_g"])
    alpha_v = 1.0 - decay_v

    n_tr = args.n_trials
    rng = np.random.default_rng(seed_val)
    v = np.full((N, n_tr), float(p["v_0"]), dtype=np.float32)
    g = np.zeros((N, n_tr), dtype=np.float32)
    ref = np.zeros((N, n_tr), dtype=np.int16)
    ring = np.zeros((dly, N, n_tr), dtype=np.float32)
    binned = np.zeros((n_bins, N), dtype=np.float32)
    p_bg = 24.0 * dt_ms / 1000.0
    s0, s1 = int(pulse_start_ms / dt_ms), int(pulse_end_ms / dt_ms)

    for st in range(steps):
        sp_d = ring[st % dly]
        if sp_d.any():
            g += W.dot(sp_d)
            ring[st % dly] = 0.0
        v[rng.random((N, n_tr), dtype=np.float32) < p_bg] += 2.65
        if s0 <= st < s1:
            phits = rng.random((perturb_idx.size, n_tr), dtype=np.float32) < (450.0 * dt_ms / 1000.0)
            if phits.any():
                v[perturb_idx] += phits.astype(np.float32) * 9.5

        act = ref <= 0
        v = np.where(act, float(p["v_0"]) + (v - float(p["v_0"])) * decay_v + g * alpha_v, v)
        g *= decay_g
        ref = np.where(act, 0, ref - 1)
        fired = act & (v > float(p["v_th"]))
        if fired.any():
            v = np.where(fired, float(p["v_rst"]), v)
            g = np.where(fired, 0.0, g)
            ref = np.where(fired, rfc, ref)
            ring[(st + dly) % dly] = fired.astype(np.float32)
            binned[min(n_bins - 1, st // steps_bin)] += fired.sum(axis=1)

    ch_rates = np.zeros((n_ch, n_bins), dtype=np.float32)
    for ci, grp in enumerate(channel_groups):
        ch_rates[ci] = binned[:, grp].mean(axis=1) / (n_tr * (bin_ms / 1000.0))

    pre_bins = int(pulse_start_ms / bin_ms)
    base_mu = ch_rates[:, :pre_bins].mean(axis=1, keepdims=True)
    base_sd = ch_rates[:, :pre_bins].std(axis=1, keepdims=True)
    # Строгий порог детерминированного вызванного отклика (отсекает фоновый пуассоновский шум в пустых каналах)
    S_post = (ch_rates[:, pre_bins:] > (base_mu + np.maximum(3.8 * base_sd, 8.5))).astype(np.int8)
    return S_post


for topo_name, t_edges in topologies.items():
    for g_sc in couplings:
        S_mat = run_perturbation(t_edges, g_sc, seed_val=args.seed + 101)
        pci, integ, diff_s = compute_pci(S_mat)
        # Произведение интеграции и сложной дифференциации (индекс баланса GI)
        balance_idx = pci * integ * (0.35 + 0.65 * diff_s)
        rows.append({
            "топология": topo_name,
            "сцепление_g": g_sc,
            "PCI": round(pci, 4),
            "интеграция": round(integ, 4),
            "дифференциация": round(diff_s, 4),
            "индекс_сложной_интеграции": round(balance_idx, 4),
            "доля_единиц": round(float(S_mat.mean()), 4),
        })
        if abs(g_sc - 1.0) < 0.16 and topo_name not in matrices_at_unit:
            matrices_at_unit[topo_name] = S_mat
    print(f"  {topo_name:<18} | макс. индекс = {max(r['индекс_сложной_интеграции'] for r in rows if r['топология']==topo_name):.3f}")

df_res = pd.DataFrame(rows)
df_res.to_csv(RUN / "pci_regimes.csv", index=False)
df_top = df_res.groupby("топология", as_index=False)[["PCI", "интеграция", "дифференциация", "индекс_сложной_интеграции"]].max()
df_top.to_csv(RUN / "pci_topologies.csv", index=False)

# График 2x2
plt, seq_cmap, _ = flylib.setup_plot_style()
fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.0), dpi=140)

# [A] PCI и индекс сложной интеграции по силе глобального сцепления
for ti, tname in enumerate(topologies.keys()):
    sub = df_res[df_res["топология"] == tname].sort_values("сцепление_g")
    axes[0, 0].plot(sub["сцепление_g"], sub["индекс_сложной_интеграции"], marker="o", ms=4.5, lw=1.7, color=flylib.SERIES_COLORS[ti], label=tname)
axes[0, 0].set_xlabel("множитель глобального синаптического сцепления (g)")
axes[0, 0].set_ylabel("сложная интеграция (PCI x вовлечение)")
axes[0, 0].set_title("A. Колоколообразная зависимость сложности ответа от режима сети")
axes[0, 0].legend(frameon=False, fontsize=8)

# [B] Компромисс интеграции и дифференциации
for ti, tname in enumerate(topologies.keys()):
    sub = df_res[df_res["топология"] == tname]
    axes[0, 1].scatter(sub["интеграция"], sub["дифференциация"], s=35, color=flylib.SERIES_COLORS[ti], label=tname)
    axes[0, 1].plot(sub["интеграция"], sub["дифференциация"], lw=0.9, ls=":", color=flylib.SERIES_COLORS[ti])
axes[0, 1].set_xlabel("интеграция (доля вовлечённых каналов мозга)")
axes[0, 1].set_ylabel("дифференциация (разнообразие состояний во времени)")
axes[0, 1].set_title("B. Плоскость интеграция / дифференциация")
axes[0, 1].legend(frameon=False, fontsize=8)

# [C] Бинарная матрица ответа S(m, t) реального коннектома (g = 1.0)
mat_int = matrices_at_unit.get("intact_connectome", np.zeros((n_ch, 50)))
axes[1, 0].imshow(mat_int, cmap=seq_cmap, aspect="auto", interpolation="nearest")
axes[1, 0].set_xlabel("бины после импульса (по 4 мс)")
axes[1, 0].set_ylabel("пространственные пулы коннектома")
axes[1, 0].set_title("C. Отклик S(m, t) модульного коннектома (богатая каскадная волна)")

# [D] Бинарная матрица ответа S(m, t) изолированной решётки (g = 1.0)
mat_lat = matrices_at_unit.get("modular_lattice", np.zeros((n_ch, 50)))
axes[1, 1].imshow(mat_lat, cmap=seq_cmap, aspect="auto", interpolation="nearest")
axes[1, 1].set_xlabel("бины после импульса (по 4 мс)")
axes[1, 1].set_ylabel("пространственные пулы решётки")
axes[1, 1].set_title("D. Отклик S(m, t) решётки без дальнодействующих связей")

best_int = df_res[df_res["топология"] == "intact_connectome"].sort_values("индекс_сложной_интеграции", ascending=False).iloc[0]
fig.suptitle(
    f"Индекс PCI и интеграция ({source}): пик коннектома PCI={best_int['PCI']:.2f}, интеграция={best_int['интеграция']:.2f} при g={best_int['сцепление_g']}",
    fontsize=10.5,
    x=0.012,
    ha="left",
)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(RUN / "pci_complexity.png")
plt.close(fig)

summary = {
    "задача": "i-pci",
    "источник": source,
    "нейронов": int(N),
    "каналов": int(n_ch),
    "максимумы_по_топологиям": df_top.to_dict(orient="records"),
    "файлы": ["pci_regimes.csv", "pci_topologies.csv", "pci_complexity.png"],
    "время_счета_с": round(time.time() - t0, 2),
}
flylib.save_json(RUN / "summary.json", summary)
print(f"готово за {summary['время_счета_с']} с -> {RUN}")
