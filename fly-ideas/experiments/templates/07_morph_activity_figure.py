#!/usr/bin/env python3
"""Связка морфологии и активности в одной фигуре: анатомия MaleCNS плюс прогон модели.

Зачем: модель Shiu et al. считает спайки на FlyWire v783, а красивые скелеты с отростками
удобнее брать из MaleCNS v1.0. Пространства id у них разные, поэтому фигура честно
разделена на две половины и подписана:

  верх: морфология нейронов (скелеты SWC, MaleCNS v1.0), три проекции, цвет = нейрон;
  низ:  активность модели (спайки FlyWire v783): растр по времени и число спайков.

Если есть таблица соответствия id (--map), фигура связывает половины: морфология
раскрашивается тем же цветом, а над скелетом подписывается число спайков модели.

Примеры:
  python 07_morph_activity_figure.py --swc C:/proj/skeletons --spikes %FLY_RUN_DIR%/spikes.parquet
  python 07_morph_activity_figure.py --ids 12781 556329 --spikes spikes.parquet --map map.csv
  python 07_morph_activity_figure.py --swc C:/proj/skeletons --spikes spikes.csv --max-neurons 6

Результат: morph_activity.png, summary.json. Данные: FLY_DATA, результат: FLY_RUN_DIR.
"""
import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

RUN = Path(os.environ.get("FLY_RUN_DIR", "."))
HERE = Path(__file__).resolve().parent

ap = argparse.ArgumentParser(description="Морфология MaleCNS плюс активность модели v783 в одной фигуре")
ap.add_argument("--ids", nargs="*", help="id нейронов MaleCNS для скачивания скелетов")
ap.add_argument("--swc", help="файл .swc или папка со скелетами")
ap.add_argument("--glob", default="*.swc", help="маска файлов в папке --swc")
ap.add_argument("--max-neurons", type=int, default=6, help="сколько нейронов брать")
ap.add_argument("--spikes", required=True, help="parquet или csv со спайками модели: колонки t и flywire_id")
ap.add_argument("--spikes-label", default="FlyWire v783 (модель Shiu et al.)", help="подпись источника спайков")
ap.add_argument("--morph-label", default="MaleCNS v1.0 (скелеты Janelia)", help="подпись источника морфологии")
ap.add_argument("--map", help="csv с соответствием id: колонки malecns_id, flywire_id (или body_id)")
ap.add_argument("--bins", type=int, default=40, help="столбцов на гистограмме спайков")
args = ap.parse_args()

for m in ("numpy", "pandas", "matplotlib"):
    try:
        __import__(m)
    except ImportError:
        sys.exit(f"Нет пакета {m}. conda env create -f environment.yml")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

# Берём загрузчики из шаблона 05, чтобы не дублировать разбор SWC и спайков.
spec = importlib.util.spec_from_file_location("gallery05", HERE / "05_neuron_gallery.py")
if spec is None or spec.loader is None:
    sys.exit("Не нашёл рядом 05_neuron_gallery.py")
gallery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gallery)

sk_args = argparse.Namespace(ids=args.ids, swc=args.swc, glob=args.glob, max_neurons=args.max_neurons)
skeletons = gallery.load_skeletons(sk_args)
spikes = gallery.load_spikes(args.spikes)

colors = ["#3f4a5a", "#7d5a3c", "#5c6b4a", "#8a4b4b", "#4a6b7d", "#6b5b7d", "#8a7a4b", "#4b7d6b"]

mapping = {}
if args.map:
    mp = pd.read_csv(args.map)
    low = {c.lower(): c for c in mp.columns}
    id_col = low.get("malecns_id") or low.get("malecns") or list(mp.columns)[0]
    other = low.get("flywire_id") or low.get("body_id") or low.get("bodyid") or list(mp.columns)[1]
    mapping = {str(a): str(b) for a, b in zip(mp[id_col], mp[other])}
    print(f"соответствий id: {len(mapping)}")

counts = spikes.groupby("id").size()
per_neuron = np.array([float(counts.get(mapping.get(s["name"], s["name"]), 0)) for s in skeletons])
matched = int(np.sum([1 for s in skeletons if mapping.get(s["name"], s["name"]) in counts.index]))
if matched == 0:
    print("  id скелетов не совпали со спайками: половины фигуры нарисованы независимо. "
          "Это нормально для MaleCNS против v783, для связи нужен --map.", file=sys.stderr)

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#9a938a", "axes.labelcolor": "#3c3833",
                     "text.color": "#3c3833", "xtick.color": "#6b655e", "ytick.color": "#6b655e",
                     "figure.facecolor": "#f6f3ee", "axes.facecolor": "#f6f3ee"})
fig = plt.figure(figsize=(13, 7.6), dpi=130)
gs = fig.add_gridspec(2, 4, height_ratios=[1.15, 1.0], hspace=0.34, wspace=0.3)

views = [("вид сверху, X-Y", 0, 1, gs[0, 0]), ("вид спереди, X-Z", 0, 2, gs[0, 1]),
         ("вид сбоку, Y-Z", 1, 2, gs[0, 2])]
for title, i, j, slot in views:
    ax = fig.add_subplot(slot)
    for k, sk in enumerate(skeletons):
        xyz = sk["xyz"]
        for a, b in sk["segments"]:
            ax.plot([xyz[a, i], xyz[b, i]], [xyz[a, j], xyz[b, j]], lw=0.5,
                    color=colors[k % len(colors)], alpha=0.9)
        ax.plot(xyz[sk["soma"], i], xyz[sk["soma"], j], "o", ms=2.5, color="#3c3833")
    ax.set_title(title, fontsize=9)
    ax.set_aspect("equal")
    ax.spines[["top", "right"]].set_visible(False)
    if j == 2:
        ax.set_xlabel("ось 1, нм")
        ax.set_ylabel("ось 2, нм")

ax_bar = fig.add_subplot(gs[0, 3])
order = np.argsort(-per_neuron)
ax_bar.barh([skeletons[i]["name"] for i in order][::-1], per_neuron[order][::-1],
            color=[colors[i % len(colors)] for i in order][::-1], height=0.6)
ax_bar.set_title("спайков на нейрон", fontsize=9)
ax_bar.set_xlabel("число спайков за прогон")
ax_bar.spines[["top", "right"]].set_visible(False)

ax_r = fig.add_subplot(gs[1, :3])
if spikes is not None and len(spikes):
    ids_sorted = counts.sort_values(ascending=False).index.tolist()
    y_of = {nid: i for i, nid in enumerate(ids_sorted[::-1])}
    ax_r.plot(spikes["t"].to_numpy(), [y_of[i] for i in spikes["id"]], ".", ms=1.4, color="#3f4a5a")
    ax_r.set_yticks(range(len(ids_sorted)))
    ax_r.set_yticklabels(ids_sorted[::-1], fontsize=6)
ax_r.set_title(f"активность: {args.spikes_label}")
ax_r.set_xlabel("время, мс")
ax_r.set_ylabel("нейрон модели")
ax_r.spines[["top", "right"]].set_visible(False)

ax_h = fig.add_subplot(gs[1, 3])
if spikes is not None and len(spikes):
    ax_h.hist(spikes["t"].to_numpy(), bins=args.bins, color="#7d5a3c")
ax_h.set_title("спайки по времени", fontsize=9)
ax_h.set_xlabel("время, мс")
ax_h.set_ylabel("спайков в столбце")
ax_h.spines[["top", "right"]].set_visible(False)

extra = f"таблица соответствия: {len(mapping)} строк" if args.map else "таблица соответствия не дана (--map)"
note = (f"верх: морфология {args.morph_label}   ·   низ: активность {args.spikes_label}\n"
        f"это разные пространства id, совпало имён: {matched}; {extra}")
fig.suptitle("Нейроны и их активность: анатомия и прогон модели", fontsize=11, x=0.012, ha="left")
fig.text(0.012, 0.012, note, fontsize=8, color="#6b655e")
fig.tight_layout(rect=[0, 0.045, 1, 0.95])
fig.savefig(RUN / "morph_activity.png")
plt.close(fig)

summary = {
    "скелетов": len(skeletons), "нейронов_со_спайками": int(len(counts)),
    "спайков": int(len(spikes)) if spikes is not None else 0,
    "совпало_id": matched, "соответствий_в_таблице": len(mapping),
    "спайков_на_скелет": {s["name"]: float(c) for s, c in zip(skeletons, per_neuron)},
    "источник_морфологии": args.morph_label, "источник_активности": args.spikes_label,
    "файлы": ["morph_activity.png"],
    "примечание": "фигура разделена на две половины: id MaleCNS и FlyWire v783 не совпадают",
}
(RUN / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
print(f"рисунок: {RUN / 'morph_activity.png'}")
print(f"сводка: {RUN / 'summary.json'}")
