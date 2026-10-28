#!/usr/bin/env python3
"""Виртуальные лезии: карта необходимости областей мозга, доза-эффект и парные выключения.

Готовый анализ для задачи «Виртуальные лезии: карта необходимости областей мозга» (i-lesions).
Прогоняет три сенсомоторных преобразования по мотивам Shiu et al. 2024:
  1) питание: вкусовые sugar_GRNs -> мотонейроны хоботка MN9;
  2) груминг: механосенсорные JO -> нисходящие нейроны чистки антенн aDN1;
  3) побег: зрительные looming-нейроны LC4 -> гигантское волокно GF и MDN.

Для каждой промежуточной области мозга (GNG_SEZ, AVLP_WED, MB, CX, LH, AL):
  - считает полное выключение (100 %) и строит матрицу необходимости «область x поведение»;
  - снимает кривую доза-эффект (0, 25, 50, 75, 100 % случайно заглушенных интернейронов области);
  - проверяет парные лезии областей и считает индекс эпистаза e_ij = y_ij - y_i * y_j
    (отрицательный = взаимная подстраховка и обходной путь, положительный = общий последовательный тракт).

Примеры:
  python 10_virtual_lesions.py --synth
  python 10_virtual_lesions.py --max-neurons 4000 --n-run 4 --t 0.4
  python 10_virtual_lesions.py --doses 0,0.25,0.5,0.75,1.0 --seed 1

Результат: lesion_matrix.csv, dose_response.csv, double_lesions.csv, lesions_overview.png, summary.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from itertools import combinations
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

ap = argparse.ArgumentParser(description="Виртуальные лезии областей мозга дрозофилы")
ap.add_argument("--synth", action="store_true", help="работать на модульном синтетическом коннектоме")
ap.add_argument("--max-neurons", type=int, default=3500, help="ограничить размер сети для быстрого обхода лезий (0 = весь мозг)")
ap.add_argument("--regions", default="GNG_SEZ,AVLP_WED,OPTIC,MB,CX,LH", help="список областей для выключения")
ap.add_argument("--doses", default="0.0,0.25,0.5,0.75,1.0", help="доли заглушаемых клеток области")
ap.add_argument("--t", type=float, default=0.35, help="длительность одной попытки, с")
ap.add_argument("--n-run", type=int, default=3, help="число попыток на условие")
ap.add_argument("--stim-rate", type=float, default=200.0, help="частота пуассоновской стимуляции входов, Гц")
ap.add_argument("--no-double", action="store_true", help="пропустить матрицу парных лезий")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()


def pick_group(nodes: pd.DataFrame, names: list[str], fallback_region: str, top_k: int = 12, as_input: bool = True) -> np.ndarray:
    mask = nodes["cell_type"].isin(names)
    if not mask.any():
        for nm in names:
            mask |= nodes["cell_type"].astype(str).str.contains(nm, case=False, na=False)
    if mask.any():
        return nodes.loc[mask, "idx"].to_numpy(dtype=np.int32)
    reg = nodes[nodes["region"] == fallback_region]
    if len(reg) == 0:
        reg = nodes
    idxs = reg["idx"].to_numpy(dtype=np.int32)
    return idxs[:top_k] if as_input else idxs[-top_k:]


t0 = time.time()
RUN.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(args.seed)

nodes, edges, source = flylib.load_flywire(max_neurons=args.max_neurons, seed=args.seed, synth=args.synth)
W = flylib.build_weight_matrix(len(nodes), edges)
print(f"источник: {source}, нейронов: {len(nodes)}, связей: {len(edges)}")

tasks = [
    {
        "id": "feeding",
        "label": "питание (sugar->MN9)",
        "stim": pick_group(nodes, ["sugar_GRNs", "sugar_GRN"], "GNG_SEZ", 16, True),
        "readout": pick_group(nodes, ["MN9_feeding", "MN9_feed"], "VNC_MOTOR", 6, False),
    },
    {
        "id": "grooming",
        "label": "груминг (JO->aDN1)",
        "stim": pick_group(nodes, ["JO_auditory", "JO"], "AVLP_WED", 16, True),
        "readout": pick_group(nodes, ["aDN1_grooming", "aDN1_groom"], "DN_MOTOR", 6, False),
    },
    {
        "id": "escape",
        "label": "побег (LC4->GF/MDN)",
        "stim": pick_group(nodes, ["LC4_looming", "LC_VPN"], "OPTIC", 16, True),
        "readout": pick_group(nodes, ["MDN_escape", "GF_escape", "MDN_GF_escape"], "DN_MOTOR", 8, False),
    },
]

protected = set()
for tk in tasks:
    protected.update(int(x) for x in tk["stim"])
    protected.update(int(x) for x in tk["readout"])

regions = [r.strip() for r in args.regions.split(",") if r.strip()]
region_pools: dict[str, np.ndarray] = {}
for reg in regions:
    cand = nodes.loc[nodes["region"] == reg, "idx"].to_numpy(dtype=np.int32)
    cand = np.array([x for x in cand if int(x) not in protected], dtype=np.int32)
    if cand.size > 0:
        region_pools[reg] = cand
regions = list(region_pools.keys())
print("области для лезий:", ", ".join(f"{r} ({region_pools[r].size})" for r in regions))

doses = [float(x) for x in args.doses.split(",") if x.strip()]

# 1. Эталон без лезий для каждой поведенческой задачи
baselines = {}
rest_run = flylib.run_lif_trials(W, t_sec=args.t, n_trials=args.n_run, seed=args.seed)
rest_rates = rest_run["rates_mean"]

for tk in tasks:
    stim_map = {int(i): args.stim_rate for i in tk["stim"]}
    res = flylib.run_lif_trials(W, stim_rates_hz=stim_map, t_sec=args.t, n_trials=args.n_run, seed=args.seed + 100)
    ro = tk["readout"]
    evoked = float(max(0.1, res["rates_mean"][ro].mean() - rest_rates[ro].mean()))
    baselines[tk["id"]] = {
        "raw_hz": float(res["rates_mean"][ro].mean()),
        "rest_hz": float(rest_rates[ro].mean()),
        "evoked_hz": evoked,
        "psth": res["psth_hz"][:, ro].mean(axis=1),
        "bins_s": res["bin_centers_s"],
    }
    print(f"эталон {tk['label']}: ответ {baselines[tk['id']]['raw_hz']:.1f} Гц (прирост +{evoked:.1f} Гц над фоном)")

# 2. Матрица полных лезий и кривые доза-эффект
matrix_rows = []
dose_rows = []
psth_examples = {}

for reg in regions:
    pool = region_pools[reg]
    for tk in tasks:
        stim_map = {int(i): args.stim_rate for i in tk["stim"]}
        ro = tk["readout"]
        base_ev = baselines[tk["id"]]["evoked_hz"]
        base_rest = baselines[tk["id"]]["rest_hz"]

        for d in doses:
            if d <= 0.0:
                sil = np.array([], dtype=np.int32)
            elif d >= 1.0:
                sil = pool
            else:
                k = max(1, int(round(pool.size * d)))
                sil = rng.choice(pool, size=k, replace=False)

            res = flylib.run_lif_trials(
                W, stim_rates_hz=stim_map, silence_idx=sil, t_sec=args.t, n_trials=args.n_run, seed=args.seed + 300
            )
            trial_ro = res["trial_rates"][:, ro].mean(axis=1) - base_rest
            ev = float(np.maximum(0.0, trial_ro).mean())
            ev_sd = float(trial_ro.std())
            retention = float(np.clip(ev / base_ev, 0.0, 1.35))
            necessity = float(np.clip(1.0 - retention, -0.35, 1.0))

            dose_rows.append({
                "область": reg,
                "задача": tk["id"],
                "поведение": tk["label"],
                "доза": d,
                "заглушено_клеток": int(sil.size),
                "ответ_Гц": round(float(res["rates_mean"][ro].mean()), 2),
                "прирост_Гц": round(ev, 2),
                "разброс_Гц": round(ev_sd, 2),
                "сохранность_ответа": round(retention, 3),
                "необходимость": round(necessity, 3),
            })

            if abs(d - 0.5) < 1e-6 and tk["id"] == "feeding" and reg == regions[0]:
                psth_examples["50%"] = res["psth_hz"][:, ro].mean(axis=1)
            if abs(d - 1.0) < 1e-6:
                if tk["id"] == "feeding" and reg == regions[0]:
                    psth_examples["100%"] = res["psth_hz"][:, ro].mean(axis=1)
                matrix_rows.append({
                    "область": reg,
                    "задача": tk["id"],
                    "поведение": tk["label"],
                    "клеток_в_области": int(pool.size),
                    "эталон_прирост_Гц": round(base_ev, 2),
                    "после_лезии_прирост_Гц": round(ev, 2),
                    "сохранность_ответа": round(retention, 3),
                    "необходимость": round(necessity, 3),
                })

df_mat = pd.DataFrame(matrix_rows)
df_dose = pd.DataFrame(dose_rows)
df_mat.to_csv(RUN / "lesion_matrix.csv", index=False)
df_dose.to_csv(RUN / "dose_response.csv", index=False)

# 3. Парные лезии (ищем задачу с параллельными путями, где одиночные лезии не обнуляют ответ целиком)
double_rows = []
epistasis_grid = np.zeros((len(regions), len(regions)))
best_double_task = tasks[-1]  # побег (LC4 -> OPTIC / AVLP_WED -> GF/MDN) имеет два параллельных плеча
if not args.no_double and len(regions) >= 2:
    tk0 = best_double_task
    stim0 = {int(i): args.stim_rate for i in tk0["stim"]}
    ro0 = tk0["readout"]
    base_ev0 = baselines[tk0["id"]]["evoked_hz"]
    base_rest0 = baselines[tk0["id"]]["rest_hz"]
    single_ret = {
        r["область"]: r["сохранность_ответа"]
        for r in matrix_rows
        if r["задача"] == tk0["id"]
    }
    for i, r1 in enumerate(regions):
        epistasis_grid[i, i] = 0.0
        for j, r2 in enumerate(regions):
            if j <= i:
                continue
            sil_pair = np.union1d(region_pools[r1], region_pools[r2])
            res_p = flylib.run_lif_trials(
                W, stim_rates_hz=stim0, silence_idx=sil_pair, t_sec=args.t, n_trials=max(2, args.n_run - 1), seed=args.seed + 700
            )
            ev_p = float(max(0.0, res_p["rates_mean"][ro0].mean() - base_rest0))
            y12 = float(np.clip(ev_p / base_ev0, 0.0, 1.35))
            y1, y2 = single_ret[r1], single_ret[r2]
            expected = y1 * y2
            epi = y12 - expected
            epistasis_grid[i, j] = epi
            epistasis_grid[j, i] = epi
            if epi < -0.08:
                regime = "избыточность (параллельный обход)"
            elif epi > 0.08:
                regime = "общий последовательный тракт"
            else:
                regime = "независимый вклад"
            double_rows.append({
                "область_1": r1,
                "область_2": r2,
                "сохранность_1": round(y1, 3),
                "сохранность_2": round(y2, 3),
                "сохранность_пары": round(y12, 3),
                "ожидание_независимое": round(expected, 3),
                "индекс_эпистаза": round(epi, 3),
                "режим": regime,
            })

df_dbl = pd.DataFrame(double_rows)
if len(df_dbl):
    df_dbl.to_csv(RUN / "double_lesions.csv", index=False)

# 4. Сводная фигура 2x2
plt, seq_cmap, div_cmap = flylib.setup_plot_style()
fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.2), dpi=140)

# [A] Тепловая карта необходимости (область x поведение)
piv = df_mat.pivot(index="область", columns="поведение", values="необходимость").reindex(index=regions)
im0 = axes[0, 0].imshow(piv.to_numpy(), cmap=seq_cmap, vmin=0.0, vmax=1.0, aspect="auto")
axes[0, 0].set_xticks(range(len(piv.columns)), piv.columns, rotation=14, ha="right", fontsize=8)
axes[0, 0].set_yticks(range(len(piv.index)), piv.index, fontsize=8.5)
for r_i in range(piv.shape[0]):
    for c_i in range(piv.shape[1]):
        val = piv.iloc[r_i, c_i]
        color = "#f6f3ee" if val > 0.58 else "#3c3833"
        axes[0, 0].text(c_i, r_i, f"{val:.2f}", ha="center", va="center", fontsize=8, color=color)
axes[0, 0].set_title("A. Карта необходимости областей (падение ответа при 100 % лезии)")
fig.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.03)

# [B] Кривые доза-эффект для ключевых пар область-поведение
top_pairs = df_mat.sort_values("необходимость", ascending=False).head(4)
for idx_row, (_, row) in enumerate(top_pairs.iterrows()):
    sub = df_dose[(df_dose["область"] == row["область"]) & (df_dose["задача"] == row["задача"])].sort_values("доза")
    axes[0, 1].plot(
        sub["доза"] * 100.0,
        sub["сохранность_ответа"],
        marker="s",
        ms=4,
        lw=1.6,
        color=flylib.SERIES_COLORS[idx_row % len(flylib.SERIES_COLORS)],
        label=f"{row['область']} : {row['задача']}",
    )
axes[0, 1].axhline(0.5, color="#9a938a", lw=0.7, ls=":")
axes[0, 1].set_xlabel("доля выключенных клеток области, %")
axes[0, 1].set_ylabel("относительный моторный ответ")
axes[0, 1].set_ylim(-0.03, 1.15)
axes[0, 1].set_title("B. Доза-эффект частичных выключений")
axes[0, 1].legend(frameon=False, fontsize=7.5, loc="best")

# [C] Парные лезии: индекс эпистаза
im2 = axes[1, 0].imshow(epistasis_grid, cmap=div_cmap, vmin=-0.35, vmax=0.35, aspect="auto")
axes[1, 0].set_xticks(range(len(regions)), regions, rotation=20, ha="right", fontsize=8)
axes[1, 0].set_yticks(range(len(regions)), regions, fontsize=8)
for r_i in range(len(regions)):
    for c_i in range(len(regions)):
        if r_i != c_i:
            axes[1, 0].text(c_i, r_i, f"{epistasis_grid[r_i, c_i]:+.2f}", ha="center", va="center", fontsize=7.5)
axes[1, 0].set_title(f"C. Парные лезии ({best_double_task['id']}): эпистаз (<0 резерв, >0 общий путь)")
fig.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.03)

# [D] Временной ход ответа мотонейронов при лезии ведущей области
t_bins = baselines["feeding"]["bins_s"] * 1000.0
axes[1, 1].plot(t_bins, baselines["feeding"]["psth"], lw=1.6, color=flylib.PALETTE["steel"], label="интактная сеть")
if "50%" in psth_examples:
    axes[1, 1].plot(t_bins, psth_examples["50%"], lw=1.4, color=flylib.PALETTE["ochre"], label=f"{regions[0]} лезия 50 %")
if "100%" in psth_examples:
    axes[1, 1].plot(t_bins, psth_examples["100%"], lw=1.4, color=flylib.PALETTE["brick"], label=f"{regions[0]} лезия 100 %")
axes[1, 1].set_xlabel("время от начала стимуляции, мс")
axes[1, 1].set_ylabel("частота MN9, Гц")
axes[1, 1].set_title(f"D. Временной профиль ответа MN9 ({regions[0]})")
axes[1, 1].legend(frameon=False, fontsize=8, loc="best")

fig.suptitle(
    f"Виртуальные лезии: {source}, N={len(nodes)}, попыток={args.n_run}, t={args.t} с",
    fontsize=10.5,
    x=0.012,
    ha="left",
)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(RUN / "lesions_overview.png")
plt.close(fig)

critical = (
    df_mat.sort_values("необходимость", ascending=False)
    .groupby("задача", as_index=False)
    .first()[["поведение", "область", "необходимость", "сохранность_ответа"]]
    .to_dict(orient="records")
)
files_out = [f for f in ("lesion_matrix.csv", "dose_response.csv", "double_lesions.csv", "lesions_overview.png") if (RUN / f).exists()]
summary = {
    "задача": "i-lesions",
    "источник": source,
    "нейронов": int(len(nodes)),
    "связей": int(len(edges)),
    "args": vars(args),
    "ведущие_области_по_задачам": critical,
    "парных_лезий_проверено": int(len(df_dbl)),
    "файлы": files_out,
    "время_счета_с": round(time.time() - t0, 2),
}
flylib.save_json(RUN / "summary.json", summary)
print("ведущие области:", json.dumps(critical, ensure_ascii=False) if "json" in globals() else critical)
print(f"готово за {summary['время_счета_с']} с -> {RUN}")
