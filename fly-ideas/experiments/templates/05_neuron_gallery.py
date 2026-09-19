#!/usr/bin/env python3
"""Галерея нейронов: морфология и распространение сигнала по контуру.

Скачивает скелеты (SWC) из открытого бакета Janelia MaleCNS v1.0 (лицензия CC-BY 4.0),
рисует три проекции (сверху, спереди, сбоку) и, если даны спайки модели, накладывает
активность на анатомию: раскраску по числу спайков, растровую диаграмму и, по желанию,
анимацию распространения активности.

Примеры:
  # 2 нейрона по id из MaleCNS, три проекции
  python 05_neuron_gallery.py --ids 12781 556329

  # свои файлы
  python 05_neuron_gallery.py --swc C:/proj/skeletons --glob '*.swc'

  # активность из прогона модели (spikes.parquet: колонки t, flywire_id)
  python 05_neuron_gallery.py --ids 12781 --spikes %FLY_DATA%/runs/.../spikes.parquet --animate

Входные данные: переменная FLY_DATA (куда складывать скелеты), FLY_RUN_DIR (куда писать результат).
Готовые таблицы: https://male-cns.janelia.org/download/ (feather, читаются pandas/pyarrow).
Интерактивный просмотр: neuroglancer-сцена из вкладки «Мозг» → «Данные и окружение».
"""

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np

BUCKET = "https://storage.googleapis.com/flyem-male-cns/v1.0/segmentation/skeletons-malecns-mirrored/skeletons-swc"
PALETTE = ["#3f5f8a", "#6b7f4a", "#a8792f", "#8a4a3a", "#4a4a4a", "#7a6a8a", "#2f6f6a", "#8a7f5f"]


# ------------------------------------------------------------------ скелеты
def download_swc(body_id: str, dest_dir: Path) -> Path:
    """Тянет один скелет из открытого бакета и кладёт в папку скелетов."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{body_id}.swc"
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    url = f"{BUCKET}/{body_id}.swc"
    print(f"скачиваю {url}")
    tmp = dest.with_suffix(".swc.part")
    with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
    tmp.rename(dest)
    print(f"  готово: {dest} ({dest.stat().st_size / 1024:.0f} КБ)")
    return dest


def read_swc(path: Path):
    """Читает SWC: id, тип, x, y, z, радиус, родитель. Возвращает узлы и сегменты."""
    ids, types, xyz, radius, parents = [], [], [], [], []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            p = line.split()
            if len(p) < 7:
                continue
            try:
                nid, ntype, x, y, z, r, par = int(p[0]), int(p[1]), float(p[2]), float(p[3]), float(p[4]), float(p[5]), int(p[6])
            except ValueError:
                continue
            ids.append(nid)
            types.append(ntype)
            xyz.append((x, y, z))
            radius.append(max(r, 0.0))
            parents.append(par)
    if not xyz:
        raise ValueError(f"в файле нет узлов: {path}")
    xyz = np.array(xyz, dtype=float)
    index = {nid: i for i, nid in enumerate(ids)}
    segments = [(index[par], i) for i, par in enumerate(parents) if par in index]
    soma = next((i for i, t in enumerate(types) if t == 1), int(np.argmax(radius)))
    return {"file": path, "xyz": xyz, "radius": np.array(radius), "segments": segments, "soma": soma}


def load_skeletons(args) -> list[dict]:
    data_dir = Path(os.environ.get("FLY_DATA", ".")) / "skeletons"
    files: list[Path] = []
    if args.swc:
        src = Path(args.swc)
        files = sorted(src.glob(args.glob)) if src.is_dir() else [src]
    for body_id in args.ids or []:
        files.append(download_swc(str(body_id), data_dir))
    if not files:
        raise SystemExit("укажи --ids (id нейронов MaleCNS) или --swc (файл или папка со скелетами)")
    out = []
    for f in files[: args.max_neurons]:
        try:
            sk = read_swc(f)
            sk["name"] = f.stem
            out.append(sk)
        except Exception as e:
            print(f"  пропускаю {f.name}: {e}", file=sys.stderr)
    if not out:
        raise SystemExit("ни одного скелета прочитать не удалось")
    return out


# ------------------------------------------------------------------ спайки
def load_spikes(path: str | None):
    """Читает спайки модели: parquet или csv с колонками t и flywire_id (или body_id)."""
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"нет файла спайков: {p}")
    if p.suffix.lower() in (".parquet", ".pq"):
        import pandas as pd

        df = pd.read_parquet(p)
    else:
        import pandas as pd

        df = pd.read_csv(p)
    col_id = next((c for c in ("flywire_id", "body_id", "bodyId", "id", "neuron") if c in df.columns), None)
    col_t = next((c for c in ("t", "time", "t_ms", "spike_time") if c in df.columns), None)
    if col_id is None or col_t is None:
        raise SystemExit(f"в файле нужны колонки времени и id нейрона, а есть: {list(df.columns)}")
    df = df[[col_t, col_id]].rename(columns={col_t: "t", col_id: "id"})
    df["id"] = df["id"].astype(str)
    print(f"спайков: {len(df)}, нейронов: {df['id'].nunique()}, время от {df['t'].min():.1f} до {df['t'].max():.1f}")
    return df


def activity_by_neuron(spikes, skeletons):
    """Число спайков на каждый нарисованный нейрон. Ноль, если id не совпал."""
    if spikes is None:
        return None
    counts = spikes.groupby("id").size()
    values = np.array([float(counts.get(s["name"], 0)) for s in skeletons])
    if values.sum() == 0:
        print("  внимание: ни один id скелета не найден в файле спайков. Скелеты MaleCNS и нейроны FlyWire v783 "
              "имеют разные пространства id: нужен либо прогон на том же наборе, либо таблица соответствия.", file=sys.stderr)
    return values


# ------------------------------------------------------------------ рисунок
def draw(args) -> dict:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    run_dir = Path(os.environ.get("FLY_RUN_DIR", "."))
    run_dir.mkdir(parents=True, exist_ok=True)

    skeletons = load_skeletons(args)
    spikes = load_spikes(args.spikes)
    activity = activity_by_neuron(spikes, skeletons)

    views = [(0, 1, "вид сверху, X-Y"), (0, 2, "вид спереди, X-Z"), (1, 2, "вид сбоку, Y-Z")]
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.8), facecolor="#f4f2ee")
    for ax, (i, j, title) in zip(axes, views):
        ax.set_facecolor("#f4f2ee")
        for k, sk in enumerate(skeletons):
            xyz = sk["xyz"]
            color = PALETTE[k % len(PALETTE)]
            lw = 0.7
            if activity is not None:
                # чем больше спайков, тем темнее и толще линия, цвет нейрона сохраняется
                norm = 0.0 if activity.max() == 0 else activity[k] / activity.max()
                r, g, b = (int(color[1:][i:i + 2], 16) / 255 for i in (0, 2, 4))
                k_dark = 1.0 - 0.55 * (1.0 - norm)
                color = (r * k_dark, g * k_dark, b * k_dark)
                lw = 0.5 + 1.7 * (1.0 - norm) + 0.3
            for a, b in sk["segments"]:
                ax.plot(xyz[[a, b], i], xyz[[a, b], j], color=color, linewidth=lw, solid_capstyle="round")
            s = sk["soma"]
            ax.plot([xyz[s, i]], [xyz[s, j]], marker="o", markersize=3.2, color=color, markeredgecolor="#f4f2ee", markeredgewidth=0.6)
        ax.set_title(title, fontsize=9, color="#3a352f")
        ax.set_aspect("equal", adjustable="datalim")
        ax.tick_params(labelsize=7, colors="#6b645c")
        for side in ax.spines.values():
            side.set_color("#c9c3ba")
            side.set_linewidth(0.7)
        ax.set_xlabel(f"ось {i}, нм", fontsize=7, color="#6b645c")
        ax.set_ylabel(f"ось {j}, нм", fontsize=7, color="#6b645c")

    title = "нейронов: %d" % len(skeletons)
    if activity is not None:
        title += ", спайков всего: %d" % int(activity.sum())
        if spikes is not None:
            title += ", окно: %.0f-%.0f мс" % (spikes["t"].min(), spikes["t"].max())
    fig.suptitle(title, fontsize=10, color="#3a352f", x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    gallery = run_dir / "neuron_gallery.png"
    fig.savefig(gallery, dpi=190)
    plt.close(fig)
    print(f"рисунок: {gallery}")

    raster_path = None
    if spikes is not None and not args.no_raster:
        fig2, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 4.4), facecolor="#f4f2ee", height_ratios=[2, 1], sharex=True)
        names = [s["name"] for s in skeletons]
        sub = spikes[spikes["id"].isin(names)]
        for k, name in enumerate(names):
            ts = sub.loc[sub["id"] == name, "t"].to_numpy()
            if ts.size:
                ax1.vlines(ts, k - 0.4, k + 0.4, color=PALETTE[k % len(PALETTE)], linewidth=0.8)
        ax1.set_yticks(range(len(names)), labels=names, fontsize=7)
        ax1.set_ylabel("нейрон", fontsize=8, color="#6b645c")
        ax1.set_title("спайки по времени", fontsize=9, color="#3a352f")
        bins = np.linspace(spikes["t"].min(), spikes["t"].max(), 60)
        hist, edges = np.histogram(sub["t"].to_numpy(), bins=bins) if len(sub) else (np.zeros(59), bins)
        ax2.fill_between(edges[:-1], hist, step="post", color="#3f5f8a", alpha=0.55)
        ax2.set_ylabel("спайков", fontsize=8, color="#6b645c")
        ax2.set_xlabel("время, мс", fontsize=8, color="#6b645c")
        for ax in (ax1, ax2):
            ax.set_facecolor("#f4f2ee")
            ax.tick_params(labelsize=7, colors="#6b645c")
            for side in ax.spines.values():
                side.set_color("#c9c3ba")
                side.set_linewidth(0.7)
        fig2.tight_layout()
        raster_path = run_dir / "activity_raster.png"
        fig2.savefig(raster_path, dpi=190)
        plt.close(fig2)
        print(f"растр: {raster_path}")

    gif_path = None
    if args.animate and spikes is not None and len(skeletons) > 1:
        gif_path = animate(args, skeletons, spikes, run_dir)

    matched = None if activity is None else int((activity > 0).sum())
    summary = {
        "script": "05_neuron_gallery",
        "spikes_matched_neurons": matched,
        "args": {
            "ids": args.ids,
            "swc": args.swc,
            "spikes": args.spikes,
            "animate": bool(args.animate),
        },
        "neurons": [
            {
                "name": s["name"],
                "nodes": int(len(s["xyz"])),
                "segments": int(len(s["segments"])),
                "spikes": None if activity is None else int(activity[k]),
                "extent_nm": [float(v) for v in (s["xyz"].max(axis=0) - s["xyz"].min(axis=0))],
            }
            for k, s in enumerate(skeletons)
        ],
        "files": [p.name for p in (gallery, raster_path, gif_path) if p],
        "note": "морфология: MaleCNS v1.0, Janelia, CC-BY 4.0",
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"сводка: {run_dir / 'summary.json'}")
    return summary


def animate(args, skeletons, spikes, run_dir: Path):
    """Кадры активности на анатомии: точки у сом гаснут и вспыхивают по времени."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import PillowWriter

    t0, t1 = float(spikes["t"].min()), float(spikes["t"].max())
    edges = np.linspace(t0, t1, args.frames + 1)
    soma_xyz = np.array([s["xyz"][s["soma"]] for s in skeletons])
    per = np.zeros((len(skeletons), args.frames))
    for k, s in enumerate(skeletons):
        ts = spikes.loc[spikes["id"] == s["name"], "t"].to_numpy()
        per[k], _ = np.histogram(ts, bins=edges) if ts.size else (np.zeros(args.frames), edges)

    fig, ax = plt.subplots(figsize=(6.4, 5.6), facecolor="#f4f2ee")
    gif = run_dir / "activity.gif"

    def frame(f):
        ax.clear()
        ax.set_facecolor("#f4f2ee")
        for k, s in enumerate(skeletons):
            xyz = s["xyz"]
            for a, b in s["segments"]:
                ax.plot(xyz[[a, b], 0], xyz[[a, b], 1], color="#8d857c", linewidth=0.5)
        for k in range(len(skeletons)):
            n = per[k, f]
            ax.scatter([soma_xyz[k, 0]], [soma_xyz[k, 1]], s=12 + 90 * (n > 0), color=PALETTE[k % len(PALETTE)], alpha=0.25 if n == 0 else 0.95, linewidths=0)
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_title(f"активность, {edges[f]:.0f}-{edges[f + 1]:.0f} мс, спайков: {int(per[:, f].sum())}", fontsize=9, color="#3a352f")
        ax.tick_params(labelsize=7, colors="#6b645c")
        for side in ax.spines.values():
            side.set_color("#c9c3ba")
            side.set_linewidth(0.7)

    anim = __import__("matplotlib.animation", fromlist=["FuncAnimation"]).FuncAnimation(fig, frame, frames=args.frames, interval=180)
    anim.save(gif, writer=PillowWriter(fps=6))
    plt.close(fig)
    print(f"анимация: {gif}")
    return gif


def main():
    ap = argparse.ArgumentParser(description="Морфология нейронов и активность на анатомии")
    ap.add_argument("--ids", nargs="*", help="id нейронов MaleCNS, например 12781 или 12781 556329")
    ap.add_argument("--swc", help="файл .swc или папка со скелетами (свои данные)")
    ap.add_argument("--glob", default="*.swc", help="маска файлов в папке --swc")
    ap.add_argument("--max-neurons", type=int, default=8, help="сколько нейронов рисовать")
    ap.add_argument("--spikes", help="parquet или csv со спайками модели: колонки t и flywire_id")
    ap.add_argument("--no-raster", action="store_true", help="не строить растровую диаграмму")
    ap.add_argument("--animate", action="store_true", help="сделать gif с распространением активности")
    ap.add_argument("--frames", type=int, default=48, help="кадров в анимации")
    args = ap.parse_args()
    summary = draw(args)
    print(json.dumps({"нейронов": len(summary["neurons"]), "файлы": summary["files"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
