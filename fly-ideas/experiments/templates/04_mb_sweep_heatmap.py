"""Развёртка игрушечной MB-модели: разреженность × число «мусорных» ассоциаций → тепловая карта «когда память выживает».

Запускает 02_mb_toy_interference.py в сетке параметров (несколько сидов), собирает summary.json
и рисует heatmap.png: цвет = остаточная сила избегания A после переучивания и набивания.
Аргументы: --relearn extinction|reversal|competitor --seeds 3
           --sparsity 0.01,0.02,0.05,0.1,0.2 --junk 0,10,25,50,100,200
Нужны numpy и matplotlib.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RUN = Path(os.environ.get("FLY_RUN_DIR", "."))
HERE = Path(__file__).resolve().parent
TOY = HERE / "02_mb_toy_interference.py"

ap = argparse.ArgumentParser()
ap.add_argument("--relearn", default="extinction", choices=["extinction", "reversal", "competitor", "none"])
ap.add_argument("--seeds", type=int, default=3)
ap.add_argument("--sparsity", default="0.01,0.02,0.05,0.1,0.2")
ap.add_argument("--junk", default="0,10,25,50,100,200")
ap.add_argument("--metric", default="after_junk_A", help="какое поле summary рисовать: after_junk_A | spontaneous_recovery_A | savings_gain")
args = ap.parse_args()

if not TOY.exists():
    sys.exit(f"Не найден {TOY} — развёртка запускает игрушечную модель из той же папки.")

try:
    import numpy as np
except ImportError:
    sys.exit("pip install numpy matplotlib")

sparsities = [float(x) for x in args.sparsity.split(",") if x.strip()]
junks = [int(x) for x in args.junk.split(",") if x.strip()]
total = len(sparsities) * len(junks) * args.seeds
print(f"Сетка {len(sparsities)}×{len(junks)} × {args.seeds} сидов = {total} прогонов, relearn={args.relearn}")

grid = np.full((len(sparsities), len(junks)), np.nan)
grid_sr = np.full_like(grid, np.nan)   # спонтанное восстановление
grid_sv = np.full_like(grid, np.nan)   # savings: наивная − переученная (трайлы), >0 = переученная быстрее
rows = []
done = 0
for i, sp in enumerate(sparsities):
    for j, nj in enumerate(junks):
        vals, srs, svs = [], [], []
        for seed in range(args.seeds):
            with tempfile.TemporaryDirectory() as td:
                env = {**os.environ, "FLY_RUN_DIR": td}
                r = subprocess.run(
                    [sys.executable, str(TOY), "--seed", str(seed), "--sparsity", str(sp), "--n-junk", str(nj), "--relearn", args.relearn],
                    env=env, capture_output=True, text=True,
                )
                if r.returncode != 0:
                    print(r.stderr[-800:])
                    sys.exit("игрушечная модель упала")
                sm = json.loads((Path(td) / "summary.json").read_text(encoding="utf-8"))
            base = abs(sm["after_learn_A"]) or 1e-9
            vals.append(-sm["after_junk_A"] / base)              # доля исходного избегания, что осталась (1 = как после обучения)
            srs.append(-sm["spontaneous_recovery_A"] / base)
            svs.append(sm["savings_trials_naive"] - sm["savings_trials_to_criterion"])
            rows.append({"sparsity": sp, "n_junk": nj, "seed": seed, **{k: sm[k] for k in sm if k != "args"}})
            done += 1
        grid[i, j], grid_sr[i, j], grid_sv[i, j] = np.mean(vals), np.mean(srs), np.mean(svs)
        print(f"  [{done:3d}/{total}] sparsity={sp:<5} junk={nj:<4} остаток={grid[i,j]:+.2f}  спонт.восст={grid_sr[i,j]:+.2f}  savings={grid_sv[i,j]:+.1f}")

(RUN / "grid.json").write_text(json.dumps({"sparsity": sparsities, "n_junk": junks, "residual": grid.tolist(), "spontaneous": grid_sr.tolist(), "savings_gain": grid_sv.tolist(), "rows": rows}, ensure_ascii=False, indent=1), encoding="utf-8")

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("matplotlib нет — heatmap.png не нарисован (pip install matplotlib). grid.json сохранён.")
    sys.exit(0)

sv_lim = max(1.0, float(np.nanmax(np.abs(grid_sv))))
fig, axes = plt.subplots(1, 3, figsize=(15, 4.4), constrained_layout=True)
panels = [
    (grid, "Остаток памяти A после переучивания + набивания\n(1 = как сразу после обучения, 0 = ничего)", "viridis", (0, 1)),
    (grid_sr, "Спонтанное восстановление\n(после «ожидания»)", "viridis", (0, 1)),
    (grid_sv, "Savings: на сколько трайлов быстрее наивной\n(>0 — след помогает, <0 — мешает)", "coolwarm", (-sv_lim, sv_lim)),
]
for ax, (g, title, cmap, (lo, hi)) in zip(axes, panels):
    im = ax.imshow(g, origin="lower", aspect="auto", cmap=cmap, vmin=lo, vmax=hi)
    ax.set_xticks(range(len(junks)), junks)
    ax.set_yticks(range(len(sparsities)), sparsities)
    ax.set_xlabel("«мусорных» ассоциаций")
    ax.set_ylabel("разреженность KC (сила APL)")
    ax.set_title(title, fontsize=10)
    for (yy, xx), v in np.ndenumerate(g):
        if not np.isnan(v):
            ax.text(xx, yy, f"{v:.1f}" if abs(v) < 10 else f"{v:.0f}", ha="center", va="center", fontsize=8, color="white" if cmap == "viridis" and v < (hi - lo) * 0.6 + lo else "black")
    fig.colorbar(im, ax=ax, shrink=0.85)
fig.suptitle(f"Игрушечная MB-модель · переучивание: {args.relearn} · {args.seeds} сидов", fontsize=11)
fig.savefig(RUN / "heatmap.png", dpi=130)
print(f"\nheatmap.png и grid.json → {RUN}")

(RUN / "summary.json").write_text(json.dumps({
    "args": vars(args),
    "residual_min": float(np.nanmin(grid)), "residual_max": float(np.nanmax(grid)),
    "best_survival": {"sparsity": sparsities[int(np.nanargmax(grid) // len(junks))], "n_junk": junks[int(np.nanargmax(grid) % len(junks))]},
    "savings_gain_mean": float(np.nanmean(grid_sv)),
    "figure": "heatmap.png",
}, ensure_ascii=False, indent=2), encoding="utf-8")
