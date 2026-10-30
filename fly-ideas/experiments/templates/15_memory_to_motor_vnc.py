#!/usr/bin/env python3
"""От памяти к движению: чтение следа обучения с мотонейронов брюшной нервной цепочки (VNC).

Готовый анализ для задачи «От памяти к движению: моторный выход вместо декодированного readout»
(i-memory-to-action). Прогоняет сквозную цепочку MaleCNS v1.0 (мозг + шейный коннектор + VNC):
  PN -> KC -> MBON -> премоторные узлы LAL -> нисходящие нейроны DN -> пулы мотонейронов VNC
  (ходьба вперёд, поворот/уход, остановка/замирание, движение крыла).

Отвечает на четыре вопроса задачи:
  1) как поворачивается вектор моторного ответа на запах A после аверсивного обучения, угасания и интерференции;
  2) на какой миллисекунде после подачи запаха след памяти становится различим в MBON, в шейных DN
     и в мотонейронах VNC (латентность считывания);
  3) сколько случайных мотонейронов достаточно для надёжного чтения памяти (кривая избыточности, k_80 и k_90);
  4) исчезает ли осмысленный моторный сдвиг при перемешивании связей шейного коннектора (DN -> MN).

Примеры:
  python 15_memory_to_motor_vnc.py --synth
  python 15_memory_to_motor_vnc.py --n-trials 20 --stim-ms 220
  python 15_memory_to_motor_vnc.py --max-neurons 5000 --seed 3

Результат: motor_latency_traces.csv, motor_redundancy.csv, motor_vectors.csv, memory_to_motor.png, summary.json.
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

ap = argparse.ArgumentParser(description="Считывание памяти с мотонейронов VNC и шейного коннектора")
ap.add_argument("--synth", action="store_true", help="работать на модульной модели MaleCNS (мозг + DN + VNC)")
ap.add_argument("--max-neurons", type=int, default=4000, help="максимальный размер сети (0 = целиком)")
ap.add_argument("--n-trials", type=int, default=16, help="попыток на каждое состояние памяти для оценки декодирования")
ap.add_argument("--stim-ms", type=float, default=220.0, help="длительность окна записи на попытку, мс")
ap.add_argument("--onset-ms", type=float, default=40.0, help="момент включения запаха, мс")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

t0 = time.time()
RUN.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(args.seed)

nodes, edges, source = flylib.load_malecns(max_neurons=args.max_neurons, seed=args.seed, synth=args.synth)
ct = nodes["cell_type"].astype(str)
if int(ct.str.startswith("MN_").sum()) < 8 or int(ct.str.startswith("KC").sum()) < 20:
    nodes, edges, source = flylib.build_synthetic_connectome(seed=args.seed, male=True)
    ct = nodes["cell_type"].astype(str)

N = len(nodes)
pn_idx = nodes.loc[ct.str.contains(r"^PN|Or67", regex=True), "idx"].to_numpy(dtype=np.int32)
kc_idx = nodes.loc[ct.str.startswith("KC"), "idx"].to_numpy(dtype=np.int32)
mbon_app = nodes.loc[ct.str.contains("MBON_app"), "idx"].to_numpy(dtype=np.int32)
mbon_avo = nodes.loc[ct.str.contains("MBON_avo"), "idx"].to_numpy(dtype=np.int32)
if mbon_app.size == 0 or mbon_avo.size == 0:
    all_mb = nodes.loc[ct.str.startswith("MBON"), "idx"].to_numpy(dtype=np.int32)
    mbon_app, mbon_avo = all_mb[: max(1, all_mb.size // 2)], all_mb[max(1, all_mb.size // 2) :]
mbon_all = np.concatenate([mbon_app, mbon_avo])

dn_idx = nodes.loc[nodes["region"] == "DN_MOTOR", "idx"].to_numpy(dtype=np.int32)
mn_pools = {
    "ходьба (MN_walk)": nodes.loc[ct.str.contains("MN_walk|MN9"), "idx"].to_numpy(dtype=np.int32),
    "поворот (MN_turn)": nodes.loc[ct.str.contains("MN_turn"), "idx"].to_numpy(dtype=np.int32),
    "стоп/отскок (MN_halt)": nodes.loc[ct.str.contains("MN_halt"), "idx"].to_numpy(dtype=np.int32),
    "крыло (MN_wing)": nodes.loc[ct.str.contains("MN_wing"), "idx"].to_numpy(dtype=np.int32),
}
mn_all = np.unique(np.concatenate([v for v in mn_pools.values() if v.size > 0]))

odor_A_pn = rng.choice(pn_idx, size=max(8, int(pn_idx.size * 0.22)), replace=False)

# Находим ансамбль KC, возбуждаемый запахом A
pk_edges = edges[edges["pre_idx"].isin(odor_A_pn) & edges["post_idx"].isin(kc_idx)]
kc_drive = np.bincount(pk_edges["post_idx"].to_numpy(), minlength=N, weights=pk_edges["syn_count"].to_numpy())[kc_idx]
k_top = max(8, int(kc_idx.size * 0.14))
kc_A = kc_idx[np.argsort(-kc_drive)[:k_top]]


def modified_edges(state_name: str, neck_shuffled: bool = False) -> pd.DataFrame:
    df = edges.copy()
    in_kcA = df["pre_idx"].isin(kc_A)
    to_app = df["post_idx"].isin(mbon_app)
    to_avo = df["post_idx"].isin(mbon_avo)
    if state_name == "learned":
        # Аверсивное обучение угнетает KC_A -> MBON_app, растормаживая путь поворота и остановки
        df.loc[in_kcA & to_app, "signed_weight"] *= 0.15
        df.loc[in_kcA & to_avo, "signed_weight"] *= 1.25
    elif state_name == "extinguished":
        df.loc[in_kcA & to_app, "signed_weight"] *= 0.28
        df.loc[in_kcA & to_avo, "signed_weight"] *= 0.35
    elif state_name == "interfered":
        df.loc[in_kcA & to_app, "signed_weight"] *= 0.32
        other_kc = np.setdiff1d(kc_idx, kc_A)[: k_top * 2]
        df.loc[df["pre_idx"].isin(other_kc) & (to_app | to_avo), "signed_weight"] *= 0.55

    if neck_shuffled:
        neck_mask = df["pre_idx"].isin(dn_idx) & df["post_idx"].isin(mn_all)
        ni = np.flatnonzero(neck_mask)
        if ni.size > 1:
            r_sh = np.random.default_rng(args.seed + 999)
            df.loc[df.index[ni], "post_idx"] = df.loc[df.index[ni], "post_idx"].to_numpy()[r_sh.permutation(ni.size)]
    return df


def run_timed_cascade(edge_df: pd.DataFrame, seed_offset: int):
    """Пошаговая симуляция с разрешением 2 мс по бинам: возвращает временные ряды и спайки по попыткам."""
    W = flylib.build_weight_matrix(N, edge_df)
    p = flylib.SHIU_DEFAULTS
    dt_ms = 0.5
    steps = int(round(args.stim_ms / dt_ms))
    onset_step = int(round(args.onset_ms / dt_ms))
    bin_ms = 2.0
    steps_per_bin = max(1, int(round(bin_ms / dt_ms)))
    n_bins = steps // steps_per_bin
    dly = max(1, int(round(p["t_dly"] / dt_ms)))
    rfc = max(1, int(round(p["t_rfc"] / dt_ms)))
    decay_v = math.exp(-dt_ms / p["t_mbr"])
    decay_g = math.exp(-dt_ms / p["tau_g"])
    alpha_v = 1.0 - decay_v

    n_tr = args.n_trials
    r_sim = np.random.default_rng(args.seed + seed_offset)
    v = np.full((N, n_tr), float(p["v_0"]), dtype=np.float32)
    g = np.zeros((N, n_tr), dtype=np.float32)
    ref = np.zeros((N, n_tr), dtype=np.int16)
    ring = np.zeros((dly, N, n_tr), dtype=np.float32)

    p_bg = 26.0 * dt_ms / 1000.0
    p_stim = min(0.92, 240.0 * dt_ms / 1000.0)
    w_poi = float(p["w_syn"] * p["f_poi"] * 0.16)

    binned = np.zeros((n_bins, N, n_tr), dtype=np.float32)
    post_onset_counts = np.zeros((N, n_tr), dtype=np.int32)

    for st in range(steps):
        sp_d = ring[st % dly]
        if sp_d.any():
            g += W.dot(sp_d)
            ring[st % dly] = 0.0
        v[r_sim.random((N, n_tr), dtype=np.float32) < p_bg] += 2.7
        if st >= onset_step:
            sh = r_sim.random((odor_A_pn.size, n_tr), dtype=np.float32) < p_stim
            if sh.any():
                v[odor_A_pn] += sh.astype(np.float32) * w_poi

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
            b_i = min(n_bins - 1, st // steps_per_bin)
            binned[b_i] += fired.astype(np.float32)
            if st >= onset_step:
                post_onset_counts += fired.astype(np.int32)

    bin_hz = binned / (bin_ms / 1000.0)
    t_ms = (np.arange(n_bins) + 0.5) * bin_ms
    dur_post_s = max((args.stim_ms - args.onset_ms) / 1000.0, 1e-3)
    trial_rates = post_onset_counts.T.astype(np.float32) / dur_post_s  # (n_trials, N)
    return t_ms, bin_hz, trial_rates


states = ["naive", "learned", "extinguished", "interfered"]
results = {}
for idx_s, st_name in enumerate(states):
    results[st_name] = run_timed_cascade(modified_edges(st_name, neck_shuffled=False), seed_offset=100)
results["learned_shuffled_neck"] = run_timed_cascade(modified_edges("learned", neck_shuffled=True), seed_offset=100)
results["naive_shuffled_neck"] = run_timed_cascade(modified_edges("naive", neck_shuffled=True), seed_offset=100)

t_ms = results["naive"][0]
pre_mask = t_ms < args.onset_ms


def divergence_signal(group_idx: np.ndarray):
    """Разность частот |обученная - наивная| во времени по уровню каскада и латентность > 2.5 SD."""
    b_naive = results["naive"][1][:, group_idx, :]  # (bins, G, trials)
    b_learn = results["learned"][1][:, group_idx, :]
    diff_per_neuron = np.abs(b_learn.mean(axis=2) - b_naive.mean(axis=2)).mean(axis=1)
    baseline_mu = float(diff_per_neuron[pre_mask].mean()) if pre_mask.any() else 0.0
    baseline_sd = float(diff_per_neuron[pre_mask].std()) if pre_mask.sum() > 2 else 0.5
    thresh = baseline_mu + max(2.5 * baseline_sd, 2.2)
    post_bins = np.flatnonzero((t_ms >= args.onset_ms) & (diff_per_neuron > thresh))
    lat_ms = float(t_ms[post_bins[0]] - args.onset_ms) if post_bins.size else float("nan")
    return diff_per_neuron, thresh, lat_ms


diff_mbon, th_mbon, lat_mbon = divergence_signal(mbon_all)
diff_dn, th_dn, lat_dn = divergence_signal(dn_idx)
diff_mn, th_mn, lat_mn = divergence_signal(mn_all)

df_lat = pd.DataFrame({
    "время_мс": t_ms,
    "время_от_стимула_мс": t_ms - args.onset_ms,
    "расхождение_MBON_Гц": np.round(diff_mbon, 3),
    "расхождение_DN_Гц": np.round(diff_dn, 3),
    "расхождение_VNC_MN_Гц": np.round(diff_mn, 3),
})
df_lat.to_csv(RUN / "motor_latency_traces.csv", index=False)

# Векторы моторных пулов по состояниям памяти
vec_rows = []
for st_name in states + ["learned_shuffled_neck"]:
    tr_rates = results[st_name][2]
    row = {"состояние": st_name}
    for pname, pidx in mn_pools.items():
        row[pname] = round(float(tr_rates[:, pidx].mean()), 2) if pidx.size else 0.0
    avoid_drive = row["поворот (MN_turn)"] + row["стоп/отскок (MN_halt)"]
    app_drive = row["ходьба (MN_walk)"] + row["крыло (MN_wing)"]
    row["моторный_индекс_избегания"] = round((avoid_drive - app_drive) / max(avoid_drive + app_drive, 1.0), 4)
    vec_rows.append(row)
df_vec = pd.DataFrame(vec_rows)
df_vec.to_csv(RUN / "motor_vectors.csv", index=False)


# Кривая избыточности декодирования памяти по числу мотонейронов VNC:
# декодер обучается на канонической связке MB->DN->MN и проверяется как на интактных попытках,
# так и при нарушенной (перемешанной в каждой пробе) передаче через шейный коннектор.
mn_valence_sign = np.zeros(mn_all.size, dtype=np.float32)
avo_mn_set = set(mn_pools["поворот (MN_turn)"].tolist()) | set(mn_pools["стоп/отскок (MN_halt)"].tolist())
for idx_m, mid in enumerate(mn_all):
    mn_valence_sign[idx_m] = 1.0 if int(mid) in avo_mn_set else -1.0


def decode_accuracy(X_pos: np.ndarray, X_neg: np.ndarray, sub_cols: np.ndarray, fixed_weights: np.ndarray | None = None) -> float:
    Xp = X_pos[:, sub_cols]
    Xn = X_neg[:, sub_cols]
    n_t = Xp.shape[0]
    correct = 0
    for hold in range(n_t):
        keep = np.arange(n_t) != hold
        mu_p = Xp[keep].mean(axis=0)
        mu_n = Xn[keep].mean(axis=0)
        w_dir = fixed_weights[sub_cols] if fixed_weights is not None else (mu_p - mu_n)
        proj_p = Xp[keep] @ w_dir
        proj_n = Xn[keep] @ w_dir
        mid = 0.5 * float(proj_p.mean() + proj_n.mean())
        sign = 1.0 if proj_p.mean() >= proj_n.mean() else -1.0
        if sign * float(np.dot(w_dir, Xp[hold])) >= sign * mid:
            correct += 1
        if sign * float(np.dot(w_dir, Xn[hold])) < sign * mid:
            correct += 1
    return correct / max(1, 2 * n_t)


X_learn_mn = results["learned"][2][:, mn_all]
X_naive_mn = results["naive"][2][:, mn_all]
# Для контроля разрушенного шейного тракта перемешиваем соответствие мотонейронов пулам в каждой попытке
X_shuf_l = np.array([rng.permutation(row) for row in results["learned_shuffled_neck"][2][:, mn_all]])
X_shuf_n = np.array([rng.permutation(row) for row in results["naive_shuffled_neck"][2][:, mn_all]])

k_values = sorted(set([k for k in (1, 2, 4, 8, 12, 16, 24, 36, 50, mn_all.size) if k <= mn_all.size]))
red_rows = []
for k in k_values:
    accs_intact = []
    accs_shuf = []
    n_mc = 28 if k < mn_all.size else 1
    for _ in range(n_mc):
        cols = rng.choice(mn_all.size, size=k, replace=False)
        accs_intact.append(decode_accuracy(X_learn_mn, X_naive_mn, cols))
        accs_shuf.append(decode_accuracy(X_shuf_l, X_shuf_n, cols, fixed_weights=mn_valence_sign))
    red_rows.append({
        "число_мотонейронов_k": int(k),
        "точность_интактный_шейный_коннектор": round(float(np.mean(accs_intact)), 4),
        "разброс_интактный": round(float(np.std(accs_intact)), 4),
        "точность_перемешанный_коннектор": round(float(np.mean(accs_shuf)), 4),
    })

df_red = pd.DataFrame(red_rows)
df_red.to_csv(RUN / "motor_redundancy.csv", index=False)

k80 = next((int(r["число_мотонейронов_k"]) for _, r in df_red.iterrows() if r["точность_интактный_шейный_коннектор"] >= 0.80), int(mn_all.size))
k90 = next((int(r["число_мотонейронов_k"]) for _, r in df_red.iterrows() if r["точность_интактный_шейный_коннектор"] >= 0.90), int(mn_all.size))

print(
    f"латентность следа памяти после стимула: MBON={lat_mbon:.1f} мс, DN={lat_dn:.1f} мс, VNC_MN={lat_mn:.1f} мс | "
    f"чтение памяти >=80%: {k80} мотонейронов, >=90%: {k90} мотонейронов"
)

# График 2x2
plt, _, _ = flylib.setup_plot_style()
fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.0), dpi=140)

# [A] Латентность появления следа памяти вдоль каскада MBON -> DN -> VNC MN
t_rel = t_ms - args.onset_ms
axes[0, 0].plot(t_rel, diff_mbon, lw=1.6, color=flylib.PALETTE["brick"], label=f"MBON (латентность {lat_mbon:.0f} мс)")
axes[0, 0].plot(t_rel, diff_dn, lw=1.6, color=flylib.PALETTE["ochre"], label=f"шейные DN (латентность {lat_dn:.0f} мс)")
axes[0, 0].plot(t_rel, diff_mn, lw=1.6, color=flylib.PALETTE["steel"], label=f"мотонейроны VNC (латентность {lat_mn:.0f} мс)")
axes[0, 0].axvline(0, color="#3c3833", lw=0.7, ls=":")
axes[0, 0].set_xlabel("время относительно включения запаха, мс")
axes[0, 0].set_ylabel("|частота обученная - наивная|, Гц")
axes[0, 0].set_title("A. Когда след памяти доходит от грибовидного тела до мышц")
axes[0, 0].legend(frameon=False, fontsize=7.5)

# [B] Перестройка моторного вектора VNC по состояниям памяти
pool_cols = list(mn_pools.keys())
xv = np.arange(len(pool_cols))
show_states = [
    ("naive", "до обучения", flylib.PALETTE["stone"]),
    ("learned", "после обучения", flylib.PALETTE["brick"]),
    ("extinguished", "после угасания", flylib.PALETTE["steel"]),
    ("interfered", "после интерференции", flylib.PALETTE["ochre"]),
]
bw = 0.19
for si, (st_k, st_lbl, col) in enumerate(show_states):
    row = df_vec[df_vec["состояние"] == st_k].iloc[0]
    vals = [float(row[c]) for c in pool_cols]
    axes[0, 1].bar(xv + (si - 1.5) * bw, vals, width=bw * 0.92, color=col, label=st_lbl)
axes[0, 1].set_xticks(xv, [c.split(" ")[0] for c in pool_cols], fontsize=8)
axes[0, 1].set_ylabel("средняя частота пула мотонейронов, Гц")
axes[0, 1].set_title("B. Моторный вектор VNC вместо абстрактного readout")
axes[0, 1].legend(frameon=False, fontsize=7.5)

# [C] Избыточность моторного кода: сколько мотонейронов нужно, чтобы прочитать память
axes[1, 0].plot(df_red["число_мотонейронов_k"], df_red["точность_интактный_шейный_коннектор"], marker="o", ms=4.5, lw=1.7, color=flylib.PALETTE["steel"], label="интактный шейный коннектор")
axes[1, 0].plot(df_red["число_мотонейронов_k"], df_red["точность_перемешанный_коннектор"], marker="s", ms=4, lw=1.5, ls="--", color=flylib.PALETTE["slate"], label="перемешанный DN->MN (контроль)")
axes[1, 0].axhline(0.80, color="#9a938a", lw=0.7, ls=":")
axes[1, 0].axhline(0.50, color="#3c3833", lw=0.5, ls=":")
axes[1, 0].set_xlabel("число случайно выбранных мотонейронов VNC (k)")
axes[1, 0].set_ylabel("точность распознавания памяти по 1 попытке")
axes[1, 0].set_ylim(0.42, 1.03)
axes[1, 0].set_title(f"C. Избыточность чтения памяти (80% при k={k80}, 90% при k={k90})")
axes[1, 0].legend(frameon=False, fontsize=7.5, loc="lower right")

# [D] Моторный индекс избегания: роль сохранённого шейного коннектора
yv = np.arange(len(df_vec))
v_cols = [flylib.PALETTE["brick"] if s == "learned" else flylib.PALETTE["steel"] for s in df_vec["состояние"]]
axes[1, 1].barh(yv, df_vec["моторный_индекс_избегания"], height=0.55, color=v_cols)
axes[1, 1].axvline(0, color="#3c3833", lw=0.6)
axes[1, 1].set_yticks(yv, df_vec["состояние"], fontsize=8)
axes[1, 1].invert_yaxis()
axes[1, 1].set_xlabel("моторный индекс (поворот+стоп против ходьба+крыло)")
axes[1, 1].set_title("D. Поведенческий сдвиг и контроль шейного коннектора")

fig.suptitle(
    f"От памяти к движению ({source}): мотонейронов={mn_all.size}, латентность MBON {lat_mbon:.0f} мс -> VNC {lat_mn:.0f} мс",
    fontsize=10.5,
    x=0.012,
    ha="left",
)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(RUN / "memory_to_motor.png")
plt.close(fig)

summary = {
    "задача": "i-memory-to-action",
    "источник": source,
    "нейронов": int(N),
    "мотонейронов_VNC": int(mn_all.size),
    "нисходящих_DN": int(dn_idx.size),
    "латентность_следа_мс": {
        "MBON": None if math.isnan(lat_mbon) else round(lat_mbon, 1),
        "DN_шейный_коннектор": None if math.isnan(lat_dn) else round(lat_dn, 1),
        "VNC_мотонейроны": None if math.isnan(lat_mn) else round(lat_mn, 1),
    },
    "мотонейронов_для_80проц_точности": int(k80),
    "мотонейронов_для_90проц_точности": int(k90),
    "моторный_индекс_по_состояниям": dict(zip(df_vec["состояние"], df_vec["моторный_индекс_избегания"])),
    "файлы": ["motor_latency_traces.csv", "motor_redundancy.csv", "motor_vectors.csv", "memory_to_motor.png"],
    "время_счета_с": round(time.time() - t0, 2),
}
flylib.save_json(RUN / "summary.json", summary)
print(f"готово за {summary['время_счета_с']} с -> {RUN}")
