#!/usr/bin/env python3
"""Протокол обучения на реальных KC, MBON и PPL1 из FlyWire v783.

Что делает:
  берёт подписи типов клеток и связи FlyWire, выбирает грибовидное тело
  (KC, MBON, PPL1, PAM), собирает схему «запах → KC → MBON» с двумя компартментами
  MBON и дофаминовой модуляцией, прогоняет протокол: обучение, угасание, отдых,
  повторное обучение.

Логика двух компартментов (Aso et al. 2014, Hige et al. 2015):
  путь через компартмент «приближение» тянет муху к запаху, путь через компартмент
  «избегание» отталкивает. Удар (PPL1) угнетает KC → MBON_приближение, поэтому запах
  начинает пугать; награда (PAM) угнетает KC → MBON_избегание, поэтому запах начинает
  привлекать. Показатель избегания = относительный отклик пути избегания минус отклик
  пути приближения, посчитанный по коду того же запаха: 0 у наивной мухи,
  больше нуля после обучения с ударом, меньше нуля после награды.

Пассивная релаксация:
  веса постепенно возвращаются к базовым с постоянной --tau, поэтому память слабеет
  без «перезаписи» (режим угасания по умолчанию). Режим newtrace дополнительно
  подкрепляет противоположный след, как при настоящем угасании.

Примеры:
  python 09_mb_circuit_v783.py --synth --n-pair 8                 # проверка без данных
  python 09_mb_circuit_v783.py --n-pair 10 --extinction 20        # на скачанных v783
  python 09_mb_circuit_v783.py --extinction-mode newtrace --appetitive 6
  python 09_mb_circuit_v783.py --lr 0.25 --tau 400 --seed 3       # другие параметры

Результат: mb_protocol.csv, mb_curves.png, summary.json.
Данные: FLY_DATA (2025_Completeness_783.csv, 2025_Connectivity_783.parquet), результат: FLY_RUN_DIR.
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

RUN = Path(os.environ.get("FLY_RUN_DIR", "."))
DATA = Path(os.environ.get("FLY_DATA", "workspace/data"))
COLORS = {"приближение": "#3f4a5a", "избегание": "#8a4b4b", "индекс": "#7d5a3c"}

ap = argparse.ArgumentParser(description="Протокол обучения на клетках MB из FlyWire v783")
ap.add_argument("--synth", action="store_true", help="синтетические клетки вместо данных")
ap.add_argument("--cells", default="", help="файл с типами клеток (по умолчанию 2025_Completeness_783.csv)")
ap.add_argument("--edges", default="", help="файл связей (по умолчанию 2025_Connectivity_783.parquet)")
ap.add_argument("--n-pair", type=int, default=8, help="проб обучения (запах + удар)")
ap.add_argument("--extinction", type=int, default=12, help="проб угасания (запах без удара)")
ap.add_argument("--extinction-mode", choices=["relax", "newtrace"], default="relax",
                help="relax: только пассивная релаксация, newtrace: ещё и противоположный след")
ap.add_argument("--appetitive", type=int, default=0, help="проб обучения с наградой в конце протокола")
ap.add_argument("--rest", type=int, default=250, help="шагов отдыха для пассивной релаксации")
ap.add_argument("--relearn", type=int, default=4, help="пробы повторного обучения после отдыха")
ap.add_argument("--lr", type=float, default=0.18, help="скорость обучения")
ap.add_argument("--lr-reward", type=float, default=None, help="скорость обучения с наградой (по умолчанию = --lr)")
ap.add_argument("--tau", type=float, default=120.0, help="время пассивной релаксации весов, шагов")
ap.add_argument("--kc-sparsity", type=float, default=0.06, help="доля KC в коде запаха")
ap.add_argument("--n-odors", type=int, default=1, help="сколько разных запахов вести в протоколе")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

for m in ("pandas", "numpy"):
    try:
        __import__(m)
    except ImportError:
        sys.exit(f"Нет пакета {m}. conda env create -f environment.yml или pip install pandas numpy matplotlib")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

PATTERNS = {"KC": r"^KC", "MBON": r"^MBON", "PPL1": r"^PPL1", "PAM": r"^PAM", "PN": r"^PN"}


def synth_cells():
    rows, n = [], 0
    for kind, count in (("PN", 300), ("KCg-m", 2000), ("KCab-c", 500), ("MBON01", 6), ("MBON11", 6),
                        ("PPL1-01", 12), ("PAM-01", 10)):
        for _ in range(count):
            rows.append({"root_id": 1000000 + n, "cell_type": kind})
            n += 1
    cells = pd.DataFrame(rows)
    rng = np.random.default_rng(0)
    kcs = cells[cells.cell_type.str.startswith("KC")].root_id.to_numpy()
    mbon = cells[cells.cell_type.str.startswith("MBON")].root_id.to_numpy()
    ppl1 = cells[cells.cell_type.str.startswith("PPL1")].root_id.to_numpy()
    pam = cells[cells.cell_type.str.startswith("PAM")].root_id.to_numpy()
    pre = np.concatenate([rng.choice(kcs, 20000), rng.choice(ppl1, 4000), rng.choice(pam, 4000)])
    post = np.concatenate([rng.choice(mbon, 20000), rng.choice(mbon, 4000), rng.choice(kcs, 4000)])
    return cells, pd.DataFrame({"pre": pre, "post": post, "weight": rng.integers(1, 8, pre.size) + 0.0})


def load_real():
    cells_path = Path(args.cells) if args.cells else DATA / "2025_Completeness_783.csv"
    edges_path = Path(args.edges) if args.edges else DATA / "2025_Connectivity_783.parquet"
    if not (cells_path.exists() and edges_path.exists()):
        return None
    cells = pd.read_csv(cells_path, index_col=0).reset_index()
    cells = cells.rename(columns={cells.columns[0]: "root_id"})
    type_col = next((c for c in cells.columns if c.lower() in ("type", "cell_type", "celltype", "class")), None)
    if type_col is None:
        return None
    cells = cells.rename(columns={type_col: "cell_type"})[["root_id", "cell_type"]].dropna()
    edges = pd.read_parquet(edges_path)
    low = {c.lower(): c for c in edges.columns}
    pre = low.get("pre") or low.get("pre_root_id") or low.get("pre_pt_root_id")
    post = low.get("post") or low.get("post_root_id") or low.get("post_pt_root_id")
    w = low.get("weight") or low.get("syn_count") or low.get("count")
    if not (pre and post):
        return None
    edges = edges[[pre, post] + ([w] if w else [])].rename(columns={pre: "pre", post: "post"})
    edges["weight"] = edges[w].astype(float) if w else 1.0
    return cells, edges[["pre", "post", "weight"]]


t0 = time.time()
if args.synth:
    cells, edges = synth_cells()
    source = "синтетика"
else:
    got = load_real()
    if got is None:
        print("Нет файлов v783 (Completeness и Connectivity скачиваются во вкладке «Мозг»). Считаю на синтетике.")
        cells, edges = synth_cells()
        source = "синтетика (не нашлось данных v783)"
    else:
        cells, edges = got
        source = "FlyWire v783"

groups = {}
for name, pat in PATTERNS.items():
    groups[name] = cells[cells.cell_type.astype(str).str.match(pat)].root_id.astype("int64").to_numpy()
kc, mbon = groups["KC"], groups["MBON"]
dan = np.concatenate([groups["PPL1"], groups["PAM"]]) if groups["PPL1"].size or groups["PAM"].size else np.array([], dtype=np.int64)
if kc.size < 20 or mbon.size < 2:
    sys.exit(f"Слишком мало клеток для схемы: KC {kc.size}, MBON {mbon.size}. Проверь подписи типов.")
print(f"источник {source}: KC {kc.size}, MBON {mbon.size}, дофаминовые {dan.size}, PN {groups['PN'].size}")

sub = edges[edges.pre.isin(set(kc.tolist())) & edges.post.isin(set(mbon.tolist()))]
if len(sub) == 0:
    sys.exit("В таблице связей нет рёбер KC → MBON. Проверь, что связи и подписи из одного коннектома.")
print(f"рёбер KC → MBON: {len(sub)}")

rng = np.random.default_rng(args.seed)
n_active = max(1, int(kc.size * args.kc_sparsity))
odor_kc = {i: rng.choice(kc, n_active, replace=False) for i in range(args.n_odors)}

mbon_ids = np.array(sorted(set(mbon.tolist())))
half = max(1, len(mbon_ids) // 2)
comp_app = set(mbon_ids[:half].tolist())                       # компартмент приближения: угнетает удар
comp_avo = set(mbon_ids[half:].tolist()) if len(mbon_ids) > half else set(mbon_ids[:1].tolist())
row_of = {int(b): i for i, b in enumerate(mbon_ids)}
kc_col = {int(k): i for i, k in enumerate(kc)}

src_col = np.array([kc_col.get(int(p), -1) for p in sub.pre.to_numpy()])
dst_row = np.array([row_of.get(int(p), -1) for p in sub.post.to_numpy()])
keep = (src_col >= 0) & (dst_row >= 0)
src_col, dst_row = src_col[keep], dst_row[keep]
w_link = np.log1p(sub.weight.to_numpy(dtype=float))[keep]
mask_app = np.isin(mbon_ids[dst_row], list(comp_app))

W = np.zeros((kc.size, len(mbon_ids)))
np.add.at(W, (src_col, dst_row), w_link)
W_base = W.copy()
print(f"компартменты: приближение {len(comp_app)} MBON, избегание {len(comp_avo)} MBON, "
      f"связей в матрице {int((W > 0).sum())}")

app_cols = np.isin(mbon_ids, list(comp_app))
avo_cols = ~app_cols
base_app = max(W_base[:, app_cols].sum(), 1e-9)
base_avo = max(W_base[:, avo_cols].sum(), 1e-9)


def odor_vector(odor):
    v = np.zeros(kc.size)
    v[np.isin(kc, odor_kc[odor])] = 1.0
    return v


def avoidance_index(odor):
    """0 у наивной мухи, больше нуля при избегании, меньше нуля при привлекательности.

    Считается по тому же запаху: сравнивается отклик путей на его код KC
    до и после протокола, поэтому индекс не смешивается другими запахами."""
    v = odor_vector(odor)
    drive, base = v @ W, v @ W_base
    app = drive[app_cols].sum() / max(base[app_cols].sum(), 1e-9)
    avo = drive[avo_cols].sum() / max(base[avo_cols].sum(), 1e-9)
    return float(avo - app)


def pair(odor, kind, lr):
    """Проба с подкреплением: удар угнетает путь приближения, награда путь избегания."""
    global W
    v = odor_vector(odor)
    cols = app_cols if kind == "shock" else avo_cols
    W *= (1.0 - lr * np.outer(v, cols.astype(float)))


def relax(steps, odor=None, newtrace=False):
    """Пассивная релаксация весов к базовым; при newtrace ещё и слабый противоположный след."""
    global W
    if steps <= 0:
        return
    # точное решение dx/dt = (база − x)/tau за steps шагов: за tau уходит 63% памяти
    rate = 1.0 - math.exp(-steps / max(1.0, args.tau))
    W += (W_base - W) * rate
    if newtrace and odor is not None:
        v = odor_vector(odor)
        W *= (1.0 - 0.25 * args.lr * np.outer(v, app_cols.astype(float)))


rows = []
for odor in range(args.n_odors):
    step = 0

    def note(phase, before, after, extra=None):
        global step
        row = {"запах": odor, "фаза": phase, "шаг": step, "индекс_до": before, "индекс_после": after}
        if extra:
            row.update(extra)
        rows.append(row)
        step += 1

    note("старт", avoidance_index(odor), avoidance_index(odor))
    for _ in range(args.n_pair):                      # обучение: запах + удар
        before = avoidance_index(odor)
        pair(odor, "shock", args.lr)
        note("обучение", before, avoidance_index(odor))
    for _ in range(args.extinction):                  # угасание: запах без подкрепления
        before = avoidance_index(odor)
        relax(1, odor, newtrace=(args.extinction_mode == "newtrace"))
        note("угасание", before, avoidance_index(odor))
    relax(args.rest, odor, newtrace=(args.extinction_mode == "newtrace"))
    note("отдых", avoidance_index(odor), avoidance_index(odor), {"шагов_отдыха": args.rest})
    lr_reward = args.lr if args.lr_reward is None else args.lr_reward
    for _ in range(args.appetitive):                  # награда: запах + сахар
        before = avoidance_index(odor)
        pair(odor, "reward", lr_reward)
        note("награда", before, avoidance_index(odor))
    for _ in range(args.relearn):                     # повторное обучение после отдыха
        before = avoidance_index(odor)
        pair(odor, "shock", args.lr)
        note("повторное обучение", before, avoidance_index(odor))

proto = pd.DataFrame(rows)
proto["проба"] = np.arange(len(proto))
proto.to_csv(RUN / "mb_protocol.csv", index=False)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#9a938a", "axes.labelcolor": "#3c3833",
                     "text.color": "#3c3833", "xtick.color": "#6b655e", "ytick.color": "#6b655e",
                     "figure.facecolor": "#f6f3ee", "axes.facecolor": "#f6f3ee"})
fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), dpi=130)
for odor in range(args.n_odors):
    sub_p = proto[proto["запах"] == odor]
    ax[0].plot(sub_p["проба"], sub_p["индекс_после"], lw=1.5,
               color=list(COLORS.values())[odor % 3], label=f"запах {odor + 1}")
phases = proto.groupby("фаза", sort=False)["проба"].min()
for phase, x in phases.items():
    ax[0].axvline(x, color="#9a938a", lw=0.6, ls=":")
    if phase not in ("старт",):
        ax[0].text(x + 0.6, ax[0].get_ylim()[1], phase, fontsize=7, rotation=90, va="top", color="#6b655e")
ax[0].axhline(0, color="#3c3833", lw=0.7)
ax[0].set_title("показатель избегания по пробам")
ax[0].set_xlabel("номер пробы")
ax[0].set_ylabel("индекс: больше нуля = избегание")
ax[0].legend(frameon=False, fontsize=8, loc="best")
ax[0].spines[["top", "right"]].set_visible(False)

labels = ["KC → MBON\nприближение", "KC → MBON\nизбегание"]
now = [W[:, app_cols].sum() / base_app, W[:, avo_cols].sum() / base_avo]
base = [W_base[:, app_cols].sum() / base_app, W_base[:, avo_cols].sum() / base_avo]
x = np.arange(2)
ax[1].bar(x - 0.18, base, width=0.34, color="#c9c2b8", label="до протокола")
ax[1].bar(x + 0.18, now, width=0.34, color=[COLORS["приближение"], COLORS["избегание"]], label="после протокола")
ax[1].set_xticks(x, labels)
ax[1].set_ylabel("вес относительно базы")
ax[1].set_ylim(0, 1.15)
ax[1].set_title("что изменилось в двух путях")
ax[1].legend(frameon=False, fontsize=8)
ax[1].spines[["top", "right"]].set_visible(False)
fig.suptitle(f"Грибовидное тело: {source}, KC {kc.size}, MBON {mbon.size}, "
             f"обучение {args.n_pair}, угасание {args.extinction} ({args.extinction_mode}), отдых {args.rest}",
             fontsize=10, x=0.012, ha="left")
fig.tight_layout(rect=[0, 0, 1, 0.93])
fig.savefig(RUN / "mb_curves.png")
plt.close(fig)

last = proto.iloc[-1]
summary = {
    "источник": source, "KC": int(kc.size), "MBON": int(mbon.size), "дофаминовые": int(dan.size),
    "компартменты": {"приближение": int(len(comp_app)), "избегание": int(len(comp_avo))},
    "связей_KC_MBON": int(len(sub)),
    "параметры": {"lr": args.lr, "tau": args.tau, "разреженность_KC": args.kc_sparsity,
                  "проб_обучения": args.n_pair, "проб_угасания": args.extinction,
                  "режим_угасания": args.extinction_mode, "шагов_отдыха": args.rest,
                  "проб_награды": args.appetitive},
    "индекс_по_фазам": {ph: float(proto[proto.фаза == ph]["индекс_после"].iloc[-1])
                        for ph in proto["фаза"].unique()},
    "веса_относительно_базы": {"приближение": float(now[0]), "избегание": float(now[1])},
    "последний_индекс": float(last["индекс_после"]),
    "файлы": [f for f in ("mb_protocol.csv", "mb_curves.png") if (RUN / f).exists()],
    "время_счета_с": round(time.time() - t0, 1),
}
(RUN / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))

by_phase = summary["индекс_по_фазам"]
print("индекс избегания по фазам: " + ", ".join(f"{k} {v:.3f}" for k, v in by_phase.items()))
print(f"кривая: {RUN / 'mb_protocol.csv'}")
print(f"сводка: {RUN / 'summary.json'}")
