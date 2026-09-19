#!/usr/bin/env python3
"""Прогон LIF-модели (Shiu et al.) на Brian2: стимуляция, спайки, отклик сети.

Что делает:
  читает связи (таблица pre, post, weight) для FlyWire v783 или MaleCNS,
  собирает сеть LIF в Brian2 с параметрами из статьи (порог, мембранная постоянная,
  вес синапса, частота фонового пуассоновского входа), подстраивает фоновый вес под
  целевую частоту разрядов, включает или заглушает заданные нейроны, прогоняет
  несколько попыток и сохраняет спайки в формате fly-brain (t, trial, flywire_id, exp_name).

Примеры:
  # проверить без данных, на синтетической сети
  python 06_brian2_shiu.py --synth --n 2000 --t 0.5 --n-run 2

  # реальный коннектом (таблица связей скачивается во вкладке «Мозг»)
  python 06_brian2_shiu.py --edges %FLY_DATA%/2025_Connectivity_783.parquet --stim 720575940624963786 --t 1 --n-run 5

  # связи MaleCNS (получаются шаблоном 08_malecns_loader.py)
  python 06_brian2_shiu.py --edges %FLY_DATA%/malecns_edgelist.parquet

Результат: spikes.parquet, rates_top.csv, raster.png, summary.json.
Данные: FLY_DATA, результат: FLY_RUN_DIR.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

RUN = Path(os.environ.get("FLY_RUN_DIR", "."))
DATA = Path(os.environ.get("FLY_DATA", "workspace/data"))

# Параметры по умолчанию повторяют default_params из кода статьи Shiu et al.
# (code/paper-phil-drosophila/model.py в репозитории fly-brain). Значения можно
# перекрыть файлом --params-json, чтобы не расходиться с оригиналом.
DEFAULTS = dict(
    v_rest=-52.0,      # мВ, потенциал покоя
    v_reset=-52.0,     # мВ, после спайка
    v_th=-45.0,        # мВ, порог
    t_mbr=20.0,        # мс, мембранная постоянная
    t_syn=5.0,         # мс, постоянная синаптического тока
    refractory=2.0,    # мс, рефрактерность
    delay=1.0,         # мс, задержка синапса
    w_syn=0.275,       # мВ на одну связь
    r_poi=150.0,       # Гц, фоновая пуассоновская стимуляция каждого нейрона
    t_run=1000.0,      # мс, длительность попытки
)

COLORS = ["#3f4a5a", "#7d5a3c", "#5c6b4a", "#8a4b4b", "#4a6b7d"]

ap = argparse.ArgumentParser()
ap.add_argument("--edges", type=str, default="", help="parquet/csv со связями: pre, post, weight")
ap.add_argument("--synth", action="store_true", help="синтетическая сеть вместо данных")
ap.add_argument("--n", type=int, default=2000, help="размер синтетической сети")
ap.add_argument("--max-neurons", type=int, default=0, help="обрезать реальную сеть до N нейронов (0 = целиком)")
ap.add_argument("--stim", type=str, default="", help="id нейронов для стимуляции, через запятую")
ap.add_argument("--silence", type=str, default="", help="id нейронов, которые заглушить, через запятую")
ap.add_argument("--stim-random", type=int, default=0, help="стимулировать N случайных нейронов (для проверок)")
ap.add_argument("--t", type=float, default=1.0, help="секунд биовремени на попытку")
ap.add_argument("--n-run", type=int, default=3, help="попыток на условие")
ap.add_argument("--rate", type=float, default=None, help="перекрыть r_poi (Гц)")
ap.add_argument("--stim-rate", type=float, default=None, help="частота входа в стимулируемые нейроны (Гц)")
ap.add_argument("--w-syn", type=float, default=None, help="перекрыть вес синапса (мВ)")
ap.add_argument("--weight-scale", type=float, default=1.0, help="множитель веса связи")
ap.add_argument("--max-weight", type=float, default=6.0, help="потолок веса одной связи, мВ")
ap.add_argument("--target-rate", type=float, default=2.0, help="Гц, целевая частота фона (калибровка)")
ap.add_argument("--no-calibrate", action="store_true", help="не подстраивать фоновый вес")
ap.add_argument("--w-bg", type=float, default=None, help="вес фонового входа (мВ), если калибровка не нужна")
ap.add_argument("--params-json", type=str, default="", help="файл с параметрами модели")
ap.add_argument("--exp", type=str, default="baseline,stim", help="условия через запятую: baseline и (или) stim")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--no-plot", action="store_true")
args = ap.parse_args()

params = dict(DEFAULTS)
if args.params_json and Path(args.params_json).exists():
    params.update({k: v for k, v in json.loads(Path(args.params_json).read_text()).items() if k in DEFAULTS})
if args.rate is not None:
    params["r_poi"] = float(args.rate)
if args.w_syn is not None:
    params["w_syn"] = float(args.w_syn)
stim_rate = args.stim_rate if args.stim_rate is not None else max(params["r_poi"] * 3.0, 400.0)

for m in ("pandas", "brian2", "numpy"):
    try:
        __import__(m)
    except ImportError:
        sys.exit(f"Нет пакета {m}. conda env create -f environment.yml  (для brian2 нужен numpy<2)")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from brian2 import (Hz, Network, NeuronGroup, PoissonGroup, SpikeMonitor, StateMonitor,  # noqa: E402
                    Synapses, defaultclock, mV, ms, seed as b2seed)

EXPS = [e.strip() for e in args.exp.split(",") if e.strip()] or ["stim"]


def load_edges():
    """Возвращает (pre, post, weight, источник)."""
    path = Path(args.edges) if args.edges else None
    if path is None:
        for cand in (DATA / "malecns_edgelist.parquet", DATA / "2025_Connectivity_783.parquet"):
            if cand.exists() and cand.stat().st_size > 1000:
                path = cand
                break
    if path is not None and path.exists():
        df = pd.read_parquet(path) if path.suffix != ".csv" else pd.read_csv(path)
        cols = {c.lower(): c for c in df.columns}
        pre = cols.get("pre") or cols.get("pre_root_id") or cols.get("pre_pt_root_id") or cols.get("bodyid_pre")
        post = cols.get("post") or cols.get("post_root_id") or cols.get("post_pt_root_id") or cols.get("bodyid_post")
        wcol = cols.get("weight") or cols.get("syn_count") or cols.get("count") or cols.get("n_synapses")
        if not (pre and post):
            sys.exit(f"В {path.name} не нашёл колонок pre/post. Есть: {list(df.columns)[:12]}")
        w = df[wcol].astype(float).to_numpy() if wcol else np.ones(len(df))
        return df[pre].to_numpy(), df[post].to_numpy(), w, path.name
    if not args.synth:
        print("Связей нет, беру синтетическую сеть (--synth).")
    rng = np.random.default_rng(args.seed)
    n = max(50, args.n)
    pre = rng.integers(0, n, n * 12)
    post = rng.integers(0, n, n * 12)
    keep = pre != post
    pre, post = pre[keep], post[keep]
    w = rng.integers(1, 6, pre.size).astype(float)
    return pre, post, w, "синтетика"


pre, post, weight, source = load_edges()
ids = np.union1d(pre, post).astype(np.int64)

if args.max_neurons and ids.size > args.max_neurons:
    deg = pd.Series(np.concatenate([pre, post])).value_counts()
    keep_ids = [int(x) for x in deg.index[: args.max_neurons]]
    # Берём связи отобранных узлов целиком: иначе в разреженном графе можно потерять все рёбра.
    mask = np.isin(pre, keep_ids)
    if not mask.any():
        mask = np.isin(post, keep_ids)
    pre, post, weight = pre[mask], post[mask], weight[mask]
    ids = np.union1d(pre, post).astype(np.int64)
    if args.stim and not np.isin(np.array([int(v) for v in args.stim.replace(" ", "").split(",") if v]),
                                 ids).any():
        print("  замечание: заданные --stim не попали в обрезанную сеть, подними --max-neurons")
    print(f"сеть обрезана: {ids.size} нейронов, {pre.size} связей (узлы отобраны по степени, лимит {args.max_neurons})")

index = {int(v): i for i, v in enumerate(ids)}
N = ids.size
if N < 2:
    sys.exit("В таблице связей меньше двух нейронов.")
print(f"сеть: {N} нейронов, {pre.size} связей, источник {source}")

src = np.array([index[int(v)] for v in pre], dtype=np.int32)
dst = np.array([index[int(v)] for v in post], dtype=np.int32)
w_mv = np.clip(weight * params["w_syn"] * args.weight_scale, 0.0, args.max_weight)


def parse_ids(text):
    out = []
    for part in text.replace(" ", "").split(","):
        if part:
            out.append(index.get(int(part)))
    return [i for i in out if i is not None]


stim_idx = parse_ids(args.stim)
if not stim_idx and args.stim_random:
    stim_idx = sorted(np.random.default_rng(args.seed).choice(N, min(args.stim_random, N), replace=False).tolist())
silence_idx = parse_ids(args.silence)
if args.stim and not stim_idx:
    sys.exit("Ни один из --stim не встречается в таблице связей. Проверь, что id из того же коннектома.")

defaultclock.dt = 0.1 * ms
NS = dict(v_rest=params["v_rest"] * mV, v_th=params["v_th"] * mV, v_reset=params["v_reset"] * mV,
          t_mbr=params["t_mbr"] * ms, t_syn=params["t_syn"] * ms, refr=params["refractory"] * ms)
EQS = """
dv/dt = (v_rest - v + i_syn) / t_mbr : volt (unless refractory)
di_syn/dt = -i_syn / t_syn : volt
"""


def build(poi_rates, w_bg_mv, record_state=False):
    E = NeuronGroup(N, EQS, threshold="v > v_th", reset="v = v_reset", refractory="refr",
                    method="exact", name="E", namespace=NS)
    E.v = NS["v_reset"]
    S = Synapses(E, E, "w : volt", on_pre="i_syn_post += w", name="S", method="exact")
    S.connect(i=src, j=dst)
    S.w = w_mv * mV
    S.delay = params["delay"] * ms
    POI = PoissonGroup(N, rates=poi_rates * Hz, name="POI")
    B = Synapses(POI, E, "w : volt", on_pre="i_syn_post += w", name="B", method="exact")
    B.connect(j="i")
    B.w = w_bg_mv * mV
    mon, drive = SpikeMonitor(E, name="mon"), SpikeMonitor(POI, name="drive")
    items = [E, S, POI, B, mon, drive]
    st = None
    if record_state:
        st = StateMonitor(E, "v", record=list(range(min(4, N))), name="st")
        items.append(st)
    return Network(*items), mon, st


def simulate(poi_rates, w_bg_mv, dur_ms, record_state=False):
    """Одна попытка. Возвращает (спайки DataFrame, трассы мембраны или None)."""
    net, mon, st = build(poi_rates, w_bg_mv, record_state)
    net.run(dur_ms * ms, report=None)
    df = pd.DataFrame({"t": np.asarray(mon.t / ms, dtype=float),
                       "flywire_id": ids[mon.i] if len(mon.i) else np.array([], dtype=np.int64)})
    tr = np.asarray(st.v[:] / mV, dtype=float) if st is not None else None
    return df, tr


def trial_rates(exp):
    r = np.full(N, float(params["r_poi"]))
    if exp == "stim":
        for i in stim_idx:
            r[i] = stim_rate
    for i in silence_idx:
        r[i] = 0.0
    return r


# Калибровка фонового входа: в статье вес подбирается под спонтанную активность,
# здесь он ищется по целевой частоте разрядов (иначе при w = w_syn сеть молчит).
def background_rate(w_bg_mv, dur_ms=200.0):
    detect = np.full(N, float(params["r_poi"]))
    d, _ = simulate(detect, w_bg_mv, dur_ms)
    return len(d) / (N * dur_ms / 1000.0)


w_bg = float(args.w_bg) if args.w_bg is not None else params["w_syn"]
calib = None
if not args.no_calibrate and args.w_bg is None and not silence_idx:
    b2seed(args.seed)
    measured, lo, hi = {}, 0.0, None
    for cand in (0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0):
        measured[cand] = background_rate(cand)
        if measured[cand] >= args.target_rate:
            hi = cand
            break
        lo = cand
    if hi is not None and lo > 0:  # уточняем вилку в несколько шагов
        for _ in range(4):
            mid = float(np.sqrt(lo * hi))
            measured[mid] = background_rate(mid)
            if measured[mid] >= args.target_rate:
                hi = mid
            else:
                lo = mid
    w_bg = min(measured, key=lambda k: abs(measured[k] - args.target_rate))
    calib = {"целевая_Гц": args.target_rate, "подобранный_вес_мВ": w_bg,
             "частота_Гц": round(measured[w_bg], 3),
             "проверено_весов": len(measured)}
    print(f"калибровка фона: вес {w_bg:.3g} мВ даёт {measured[w_bg]:.2f} Гц (цель {args.target_rate})")

t_run = args.t * 1000.0
rows, per_exp, traces, t0 = [], {}, {}, time.time()

for exp in EXPS:
    for trial in range(args.n_run):
        b2seed(args.seed + trial + (1000 if exp == "stim" else 0))
        df, tr = simulate(trial_rates(exp), w_bg, t_run, record_state=(not args.no_plot and trial == 0))
        df["trial"] = trial
        df["exp_name"] = exp
        rows.append(df)
        per_exp.setdefault(exp, []).append(int(len(df)))
        if tr is not None:
            traces[exp] = tr
        print(f"{exp}, попытка {trial + 1}/{args.n_run}: спайков {len(df)}")

spikes = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
    columns=["t", "flywire_id", "trial", "exp_name"])
if len(spikes) == 0:
    print("Нейроны не разрядились. Подними --target-rate или --w-syn (и посмотри параметры в paper_model.py).")
spikes["t_global"] = spikes["t"] + spikes["trial"] * t_run
spikes = spikes[["t", "trial", "flywire_id", "exp_name", "t_global"]]
spikes.to_parquet(RUN / "spikes.parquet", index=False)

counts = spikes.groupby("flywire_id").size().sort_values(ascending=False)
n_edge = max(1, len(EXPS) * args.n_run)
rates_top = pd.DataFrame({"flywire_id": counts.index.astype(np.int64), "spikes": counts.to_numpy(),
                          "rate_hz": counts.to_numpy() / n_edge / (t_run / 1000.0)})
rates_top.to_csv(RUN / "rates_top.csv", index=False)

mean_rate = {k: float(np.mean(v) / (t_run / 1000.0) / N) for k, v in per_exp.items()}
stim_rate_measured = None
if stim_idx and len(spikes):
    sub = spikes[(spikes.exp_name == "stim") & (spikes.flywire_id.isin(ids[stim_idx]))]
    stim_rate_measured = float(len(sub) / args.n_run / (t_run / 1000.0) / max(1, len(stim_idx)))

if not args.no_plot and len(spikes):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#9a938a", "axes.labelcolor": "#3c3833",
                         "text.color": "#3c3833", "xtick.color": "#6b655e", "ytick.color": "#6b655e",
                         "axes.titlesize": 10, "figure.facecolor": "#f6f3ee", "axes.facecolor": "#f6f3ee"})
    exps = list(per_exp)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.2), dpi=130, gridspec_kw={"width_ratios": [2, 1]})
    for k, exp in enumerate(exps):
        sub = spikes[spikes.exp_name == exp]
        if len(sub):
            rank = sub["flywire_id"].rank(method="dense").astype(int)
            ax[0].plot(sub["t_global"].to_numpy(), rank.to_numpy(), ".", markersize=1.4,
                       color=COLORS[k % len(COLORS)], label=f"{exp} ({int(np.mean(per_exp[exp]))} спайков)")
    if stim_idx and len(spikes):
        hot = spikes[spikes.flywire_id.isin(ids[stim_idx])]
        if len(hot):
            ax[0].plot(hot["t_global"].to_numpy(), hot["flywire_id"].rank(method="dense").astype(int).to_numpy(),
                       ".", markersize=2.6, color="#8a4b4b", label="стимулируемые нейроны")
    ax[0].set_title("спайки по времени, условия наложены")
    ax[0].set_xlabel("время, мс (попытки подряд)")
    ax[0].set_ylabel("нейрон, ранк активности")
    ax[0].legend(loc="upper left", fontsize=8, framealpha=0.92, facecolor="#f6f3ee", edgecolor="none")
    ax[0].spines[["top", "right"]].set_visible(False)
    for k, exp in enumerate(exps):
        if exp in traces:
            for j in range(traces[exp].shape[0]):
                ax[1].plot(np.arange(traces[exp].shape[1]) * 0.1, traces[exp][j], lw=0.8,
                           color=COLORS[k % len(COLORS)])
    ax[1].axhline(params["v_th"], color="#8a4b4b", lw=0.8, ls="--")
    ax[1].set_title("мембрана первых нейронов, порог пунктиром")
    ax[1].set_xlabel("время, мс")
    ax[1].set_ylabel("мВ")
    ax[1].spines[["top", "right"]].set_visible(False)
    fig.suptitle(f"LIF Shiu et al. на Brian2: {source}, {N} нейронов, {args.n_run} попыток на условие",
                 fontsize=10, x=0.012, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(RUN / "raster.png")
    plt.close(fig)

summary = {
    "source": source, "нейронов": int(N), "связей": int(pre.size), "попыток": args.n_run,
    "условия": EXPS, "стимуляция": [int(ids[i]) for i in stim_idx], "заглушено": [int(ids[i]) for i in silence_idx],
    "спайков": {k: int(sum(v)) for k, v in per_exp.items()},
    "средняя_частота_Гц": mean_rate, "частота_стимулируемых_Гц": stim_rate_measured,
    "калибровка_фона": calib, "параметры": params, "стим_частота_Гц": stim_rate,
    "длительность_мс": t_run, "вес_связи_мВ": [float(w_mv.min()), float(w_mv.max())],
    "файлы": [f for f in ("spikes.parquet", "rates_top.csv", "raster.png") if (RUN / f).exists()],
    "время_счета_с": round(time.time() - t0, 1),
}
if "baseline" in mean_rate and "stim" in mean_rate:
    summary["отклик"] = {"фон_Гц": mean_rate["baseline"], "стимуляция_Гц": mean_rate["stim"],
                         "отношение": (mean_rate["stim"] / mean_rate["baseline"]) if mean_rate["baseline"] else None}
(RUN / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))

print(f"спайков всего: {len(spikes)}, время счета {summary['время_счета_с']} с")
print(f"спайки: {RUN / 'spikes.parquet'}")
print(f"сводка: {RUN / 'summary.json'}")
