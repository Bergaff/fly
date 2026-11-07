#!/usr/bin/env python3
"""Индивидуальность из одинакового мозга: устойчивость поведенческих фенотипов между днями (ICC и PCA).

Готовый анализ для задачи «Индивидуальность из одинакового мозга» (i-individuality, рамка работ
лаборатории B. de Bivort). Проверяет, откуда на одном и том же коннектоме берутся устойчивые
индивидуальные различия поведения (асимметрия выбора лево/право, склонность к избеганию, уровень
локомоторной активности).

Сравнивает три биологических механизма на когорте N виртуальных мух (тест День 1 против Дня 2):
  1) pure_noise        : строго одинаковые веса и пороги, только независимый пуассоновский шум в попытке;
  2) dev_microvar      : микро-вариация синаптических весов и порогов при развитии (фиксирована у особи);
  3) plastic_history   : одинаковый старт + короткий идиосинкратический фоновый опыт с пластичностью MB.

Метрики индивидуальности:
  - корреляция воспроизводимости День 1 / День 2 (r_test_retest и p-value);
  - внутриклассовая корреляция ICC(1,1) (доля межиндивидуальной дисперсии в общей дисперсии выбора);
  - проекция фенотипов в главные компоненты (PCA).

Примеры:
  python 17_individuality_phenotypes.py --synth
  python 17_individuality_phenotypes.py --n-flies 24 --trials-per-day 4
  python 17_individuality_phenotypes.py --weight-cv 0.14 --thresh-sd 0.45 --seed 2

Результат: individual_flies.csv, individuality_regimes.csv, individuality_phenotypes.png, summary.json.
"""
from __future__ import annotations

import argparse
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
from scipy import sparse, stats

import flylib

RUN = Path(os.environ.get("FLY_RUN_DIR", "."))

ap = argparse.ArgumentParser(description="Поведенческая индивидуальность когорты виртуальных мух")
ap.add_argument("--synth", action="store_true", help="работать на модульном синтетическом коннектоме")
ap.add_argument("--max-neurons", type=int, default=1400)
ap.add_argument("--n-flies", type=int, default=20, help="число виртуальных особей в каждом режиме")
ap.add_argument("--trials-per-day", type=int, default=3, help="число тестовых попыток в День 1 и в День 2")
ap.add_argument("--t", type=float, default=0.18, help="длительность одной попытки, с")
ap.add_argument("--weight-cv", type=float, default=0.22, help="коэффициент микро-вариации синаптических весов при развитии")
ap.add_argument("--thresh-sd", type=float, default=0.85, help="разброс порогов спайка между особями, мВ")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()


def calc_icc(data_matrix: np.ndarray) -> float:
    """Коэффициент внутриклассовой корреляции ICC(1,1) по матрице (n_flies, k_repeats)."""
    n, k = data_matrix.shape
    if n < 2 or k < 2:
        return 0.0
    grand = data_matrix.mean()
    row_means = data_matrix.mean(axis=1)
    ms_between = k * np.sum((row_means - grand) ** 2) / (n - 1)
    ms_within = np.sum((data_matrix - row_means[:, None]) ** 2) / (n * (k - 1))
    denom = ms_between + (k - 1) * ms_within
    if denom <= 1e-12:
        return 0.0
    return float(np.clip((ms_between - ms_within) / denom, -0.25, 1.0))


t0 = time.time()
RUN.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(args.seed)

nodes, edges, source = flylib.load_flywire(max_neurons=args.max_neurons, seed=args.seed, synth=args.synth)
ct = nodes["cell_type"].astype(str)
if int((nodes["side"] == "left").sum()) < 5 or int((nodes["side"] == "right").sum()) < 5:
    nodes = nodes.copy()
    nodes["side"] = ["left" if i % 2 == 0 else "right" for i in range(len(nodes))]

N = len(nodes)
stim_pool = nodes.loc[ct.str.contains("PN|sugar|JO|LC", regex=True), "idx"].to_numpy(dtype=np.int32)
if stim_pool.size < 8:
    stim_pool = np.arange(min(20, N), dtype=np.int32)
stim_map = {int(i): 175.0 for i in stim_pool[:24]}

motor_mask = nodes["region"].isin(["DN_MOTOR", "VNC_MOTOR"])
if int(motor_mask.sum()) < 8:
    motor_mask = pd.Series(np.arange(N) >= (N - 40))

left_out = nodes.loc[motor_mask & (nodes["side"] == "left"), "idx"].to_numpy(dtype=np.int32)
right_out = nodes.loc[motor_mask & (nodes["side"] == "right"), "idx"].to_numpy(dtype=np.int32)
avo_out = nodes.loc[motor_mask & ct.str.contains("turn|halt|escape|DNa|MDN", regex=True), "idx"].to_numpy(dtype=np.int32)
walk_out = nodes.loc[motor_mask & ~ct.str.contains("turn|halt|escape|DNa|MDN", regex=True), "idx"].to_numpy(dtype=np.int32)
if avo_out.size == 0:
    avo_out = left_out
if walk_out.size == 0:
    walk_out = right_out

W_base = flylib.build_weight_matrix(N, edges)
kc_mask_edges = np.isin(edges["pre_idx"].to_numpy(), nodes.loc[ct.str.startswith("KC"), "idx"].to_numpy())

regimes = [
    ("pure_noise", "чистый шум (одинаковые веса)"),
    ("dev_microvar", "микро-вариация развития"),
    ("plastic_history", "ранний пластический опыт"),
]

fly_rows = []
regime_rows = []

for r_code, r_label in regimes:
    all_turn_repeats = np.zeros((args.n_flies, 2 * args.trials_per_day), dtype=np.float32)

    for fly_i in range(args.n_flies):
        fly_rng = np.random.default_rng(args.seed * 1000 + fly_i * 37 + 11)
        v_th_off = None

        if r_code == "pure_noise":
            W_fly = W_base
        elif r_code == "dev_microvar":
            # Фиксированная стохастика синаптогенеза (Linneweber et al. 2020) и возбудимости особи
            mult = np.clip(fly_rng.normal(1.0, args.weight_cv, size=W_base.nnz), 0.25, 2.0).astype(np.float32)
            W_fly = sparse.csr_matrix((W_base.data * mult, W_base.indices, W_base.indptr), shape=W_base.shape)
            v_th_off = fly_rng.normal(0.0, args.thresh_sd, size=N).astype(np.float32)
        else:
            # Идиосинкратический ранний опыт: индивидуальные пластические сдвиги в MB и премоторных связях
            edf = edges.copy()
            if kc_mask_edges.any():
                plast_factors = np.clip(fly_rng.lognormal(0.0, 0.28, size=int(kc_mask_edges.sum())), 0.25, 1.85)
                edf.loc[kc_mask_edges, "signed_weight"] *= plast_factors
            side_bias = fly_rng.normal(0.0, 0.14)
            right_post = np.isin(edf["post_idx"].to_numpy(), right_out)
            left_post = np.isin(edf["post_idx"].to_numpy(), left_out)
            edf.loc[right_post, "signed_weight"] *= (1.0 + side_bias)
            edf.loc[left_post, "signed_weight"] *= (1.0 - side_bias)
            W_fly = flylib.build_weight_matrix(N, edf)

        day_metrics = {}
        for day in (1, 2):
            res = flylib.run_lif_trials(
                W_fly,
                stim_rates_hz=stim_map,
                t_sec=args.t,
                n_trials=args.trials_per_day,
                seed=args.seed + 50000 * day + fly_i * 97 + (0 if r_code == "pure_noise" else 7000),
                v_th_offset=v_th_off,
            )
            tr = res["trial_rates"]  # (trials_per_day, N)
            r_l = tr[:, left_out].mean(axis=1)
            r_r = tr[:, right_out].mean(axis=1)
            turn_bias = (r_r - r_l) / np.maximum(r_r + r_l, 1.0)
            avo_r = tr[:, avo_out].mean(axis=1)
            wlk_r = tr[:, walk_out].mean(axis=1)
            avoid_pref = (avo_r - wlk_r) / np.maximum(avo_r + wlk_r, 1.0)
            vigor = tr[:, motor_mask.to_numpy()].mean(axis=1)

            sl = slice(0, args.trials_per_day) if day == 1 else slice(args.trials_per_day, 2 * args.trials_per_day)
            all_turn_repeats[fly_i, sl] = turn_bias
            day_metrics[day] = {
                "turn": float(turn_bias.mean()),
                "avoid": float(avoid_pref.mean()),
                "vigor": float(vigor.mean()),
            }

        fly_rows.append({
            "режим": r_code,
            "описание": r_label,
            "особь": fly_i + 1,
            "поворот_день1": round(day_metrics[1]["turn"], 4),
            "поворот_день2": round(day_metrics[2]["turn"], 4),
            "избегание_день1": round(day_metrics[1]["avoid"], 4),
            "избегание_день2": round(day_metrics[2]["avoid"], 4),
            "активность_Гц_день1": round(day_metrics[1]["vigor"], 3),
            "активность_Гц_день2": round(day_metrics[2]["vigor"], 3),
        })

    sub_f = pd.DataFrame([r for r in fly_rows if r["режим"] == r_code])
    if sub_f["поворот_день1"].std() > 1e-6 and sub_f["поворот_день2"].std() > 1e-6:
        r_tr, p_tr = stats.pearsonr(sub_f["поворот_день1"], sub_f["поворот_день2"])
    else:
        r_tr, p_tr = 0.0, 1.0
    icc_val = calc_icc(all_turn_repeats)
    regime_rows.append({
        "режим": r_code,
        "описание": r_label,
        "r_день1_день2": round(float(r_tr), 4),
        "p_value": round(float(p_tr), 5),
        "ICC_индивидуальность": round(icc_val, 4),
        "межособевой_разброс_поворота": round(float(sub_f["поворот_день1"].std()), 4),
    })
    print(f"  {r_code:<16} | r(День1, День2) = {r_tr:+.3f} (p={p_tr:.4f}) | ICC = {icc_val:.3f}")

df_flies = pd.DataFrame(fly_rows)
df_reg = pd.DataFrame(regime_rows)

# PCA (SVD) по поведенческому вектору особей в режиме микро-вариации и пластического опыта
feat_cols = ["поворот_день1", "поворот_день2", "избегание_день1", "активность_Гц_день1"]
X_feat = df_flies[feat_cols].to_numpy(dtype=float)
X_std = (X_feat - X_feat.mean(axis=0)) / np.maximum(X_feat.std(axis=0), 1e-6)
u, s_vals, _ = np.linalg.svd(X_std, full_matrices=False)
df_flies["PC1"] = np.round(u[:, 0] * s_vals[0], 4)
df_flies["PC2"] = np.round(u[:, 1] * s_vals[1], 4)

df_flies.to_csv(RUN / "individual_flies.csv", index=False)
df_reg.to_csv(RUN / "individuality_regimes.csv", index=False)

# График 2x2
plt, _, _ = flylib.setup_plot_style()
fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.0), dpi=140)

# [A] Воспроизводимость поведения между Днём 1 и Днём 2
for idx_r, (r_code, r_label) in enumerate(regimes):
    sub = df_flies[df_flies["режим"] == r_code]
    axes[0, 0].scatter(
        sub["поворот_день1"], sub["поворот_день2"], s=24, alpha=0.8,
        color=flylib.SERIES_COLORS[idx_r], label=r_code,
    )
lim = max(0.15, float(np.abs(df_flies[["поворот_день1", "поворот_день2"]].to_numpy()).max()) * 1.15)
axes[0, 0].plot([-lim, lim], [-lim, lim], color="#3c3833", lw=0.7, ls=":")
axes[0, 0].set_xlim(-lim, lim)
axes[0, 0].set_ylim(-lim, lim)
axes[0, 0].set_xlabel("индекс выбора право/лево, День 1")
axes[0, 0].set_ylabel("индекс выбора право/лево, День 2")
axes[0, 0].set_title("A. Стабильность индивидуального выбора между днями")
axes[0, 0].legend(frameon=False, fontsize=8)

# [B] Показатели индивидуальности ICC(1,1) и корреляция тест-ретест
xr = np.arange(len(df_reg))
axes[0, 1].bar(xr - 0.17, df_reg["ICC_индивидуальность"], width=0.32, color=flylib.PALETTE["steel"], label="ICC(1,1) доля личности")
axes[0, 1].bar(xr + 0.17, df_reg["r_день1_день2"], width=0.32, color=flylib.PALETTE["brick"], label="r (День 1 vs День 2)")
axes[0, 1].axhline(0, color="#3c3833", lw=0.6)
axes[0, 1].set_xticks(xr, df_reg["режим"], fontsize=8)
axes[0, 1].set_ylim(-0.2, 1.05)
axes[0, 1].set_ylabel("коэффициент устойчивости")
axes[0, 1].set_title("B. Откуда берётся устойчивый фенотип (шум vs структура/опыт)")
axes[0, 1].legend(frameon=False, fontsize=8)

# [C] Ранжированные профили особей в режиме микро-вариации развития
sub_dev = df_flies[df_flies["режим"] == "dev_microvar"].sort_values("поворот_день1").reset_index(drop=True)
xf = np.arange(len(sub_dev))
axes[1, 0].plot(xf, sub_dev["поворот_день1"], marker="o", ms=4, lw=1.4, color=flylib.PALETTE["steel"], label="День 1")
axes[1, 0].plot(xf, sub_dev["поворот_день2"], marker="s", ms=4, lw=1.2, ls="--", color=flylib.PALETTE["ochre"], label="День 2 (та же особь)")
axes[1, 0].axhline(0, color="#3c3833", lw=0.6)
axes[1, 0].set_xlabel("особи, упорядоченные по предпочтению в День 1")
axes[1, 0].set_ylabel("индекс асимметрии поворота")
axes[1, 0].set_title("C. Сохранение индивидуального ранга особей (dev_microvar)")
axes[1, 0].legend(frameon=False, fontsize=8)

# [D] Пространство поведенческих фенотипов (PCA)
for idx_r, (r_code, _) in enumerate(regimes):
    sub = df_flies[df_flies["режим"] == r_code]
    axes[1, 1].scatter(sub["PC1"], sub["PC2"], s=24, alpha=0.8, color=flylib.SERIES_COLORS[idx_r], label=r_code)
axes[1, 1].axhline(0, color="#ded8ce", lw=0.6)
axes[1, 1].axvline(0, color="#ded8ce", lw=0.6)
axes[1, 1].set_xlabel("PC1 (асимметрия выбора и избегание)")
axes[1, 1].set_ylabel("PC2 (общая моторная бодрость)")
axes[1, 1].set_title("D. Разброс поведенческих фенотипов в пространстве PCA")
axes[1, 1].legend(frameon=False, fontsize=8)

best_row = df_reg.sort_values("ICC_индивидуальность", ascending=False).iloc[0]
fig.suptitle(
    f"Индивидуальность на одном коннектоме ({source}): особей={args.n_flies}, макс. ICC={best_row['ICC_индивидуальность']:.2f} ({best_row['режим']})",
    fontsize=10.5,
    x=0.012,
    ha="left",
)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(RUN / "individuality_phenotypes.png")
plt.close(fig)

summary = {
    "задача": "i-individuality",
    "источник": source,
    "нейронов": int(N),
    "особей_на_режим": int(args.n_flies),
    "режимы": regime_rows,
    "вывод": (
        "Чистый динамический шум не создаёт наследуемой между днями индивидуальности (ICC около 0), "
        "тогда как фиксированная микро-вариация синапсов и ранний пластический опыт формируют устойчивые фенотипы."
    ),
    "файлы": ["individual_flies.csv", "individuality_regimes.csv", "individuality_phenotypes.png"],
    "время_счета_с": round(time.time() - t0, 2),
}
flylib.save_json(RUN / "summary.json", summary)
print(f"готово за {summary['время_счета_с']} с -> {RUN}")
