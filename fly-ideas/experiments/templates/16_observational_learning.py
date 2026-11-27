#!/usr/bin/env python3
"""Обучение через наблюдение: анатомический аудит путей зрение->DAN, две мухи (D и O) и культурная цепочка.

Готовый анализ для задачи «Обучение через наблюдение: муха-демонстратор учит муху-наблюдателя»
(i-observational, по мотивам Danchin et al. 2018 и Vogt et al. 2016).

Три блока расчёта:
  1) анатомический аудит коннектома: считает прямые (1 шаг) и опосредованные (2..3 шага) пути
     от зрительных проекционных нейронов (LC/VPN) к клеткам Кеньона (KC) и дофаминовым нейронам
     (PPL1 и PAM), оценивая реальный коэффициент передачи в статичном коннектоме;
  2) парный эксперимент «Демонстратор D -> Наблюдатель O» со всеми 4 контролями из метода задачи:
       - прямое обучение D (запах A + удар PPL1);
       - верхняя граница «телепатия» (прямой перенос приращения весов dW из D в O);
       - социальное наблюдение O (запах A + зрительный сигнал испуга D через контур LC->DAN/MB);
       - контроль a: зрительный испуг D без запаха A;
       - контроль b: запах A без демонстратора D;
       - контроль c: перемешанный контур от зрения к DAN;
       - контроль d: спокойный необученный демонстратор D;
  3) культурная передача по цепочке D -> O1 -> O2 -> O3 -> O4 при разном усилении канала зрение->DAN.

Примеры:
  python 16_observational_learning.py --synth
  python 16_observational_learning.py --n-obs 12 --vis-gain 1.0
  python 16_observational_learning.py --connectome malecns --n-obs 15

Результат: observational_conditions.csv, cultural_chain.csv, visual_to_dan_paths.csv, observational_learning.png, summary.json.
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
from scipy import sparse

import flylib

RUN = Path(os.environ.get("FLY_RUN_DIR", "."))

ap = argparse.ArgumentParser(description="Обучение через наблюдение и аудит зрительно-дофаминовых путей")
ap.add_argument("--synth", action="store_true", help="работать на модульном синтетическом коннектоме")
ap.add_argument("--connectome", choices=["flywire", "malecns"], default="flywire")
ap.add_argument("--max-neurons", type=int, default=5000)
ap.add_argument("--n-direct", type=int, default=6, help="проб прямого обучения демонстратора D")
ap.add_argument("--n-obs", type=int, default=12, help="показов демонстратора наблюдателю O")
ap.add_argument("--vis-gain", type=float, default=1.0, help="множитель силы канала зрение->DAN относительно коннектома")
ap.add_argument("--lr", type=float, default=0.22)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

t0 = time.time()
RUN.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(args.seed)

loader = flylib.load_malecns if args.connectome == "malecns" else flylib.load_flywire
nodes, edges, source = loader(max_neurons=args.max_neurons, seed=args.seed, synth=args.synth)
ct = nodes["cell_type"].astype(str)
if int(ct.str.startswith("KC").sum()) < 20 or int(ct.str.contains("LC|OPTIC|vPN").sum()) < 4:
    nodes, edges, source = flylib.build_synthetic_connectome(seed=args.seed, male=(args.connectome == "malecns"))
    ct = nodes["cell_type"].astype(str)

N = len(nodes)
vis_idx = nodes.loc[(nodes["region"] == "OPTIC") | ct.str.contains("LC|vPN1", regex=True), "idx"].to_numpy(dtype=np.int32)
pn_idx = nodes.loc[ct.str.contains(r"^PN|Or67|Or56", regex=True), "idx"].to_numpy(dtype=np.int32)
kc_idx = nodes.loc[ct.str.startswith("KC"), "idx"].to_numpy(dtype=np.int32)
mbon_idx = nodes.loc[ct.str.startswith("MBON"), "idx"].to_numpy(dtype=np.int32)
ppl1_idx = nodes.loc[ct.str.startswith("PPL1"), "idx"].to_numpy(dtype=np.int32)
pam_idx = nodes.loc[ct.str.contains(r"^PAM|aSP13", regex=True), "idx"].to_numpy(dtype=np.int32)

# 1. Анатомический аудит путей от зрительных проекционных нейронов к KC и дофаминовым клеткам
pos_edges = edges[edges["signed_weight"] > 0]
row_sum = np.bincount(pos_edges["post_idx"].to_numpy(), minlength=N, weights=pos_edges["syn_count"].to_numpy())
norm_w = pos_edges["syn_count"].to_numpy() / np.maximum(row_sum[pos_edges["post_idx"].to_numpy()], 1.0)
A_norm = sparse.csr_matrix(
    (norm_w.astype(np.float32), (pos_edges["pre_idx"].to_numpy(), pos_edges["post_idx"].to_numpy())),
    shape=(N, N),
)

v_seed = np.zeros(N, dtype=np.float32)
v_seed[vis_idx] = 1.0 / max(1, vis_idx.size)
hop1 = v_seed @ A_norm
hop2 = hop1 @ A_norm
hop3 = hop2 @ A_norm

targets_audit = [("KC (грибовидное тело)", kc_idx), ("PPL1 (дофамин наказания)", ppl1_idx), ("PAM (дофамин награды)", pam_idx)]
path_rows = []
for t_label, t_arr in targets_audit:
    direct_sub = pos_edges[pos_edges["pre_idx"].isin(vis_idx) & pos_edges["post_idx"].isin(t_arr)]
    g1 = float(hop1[t_arr].sum()) if t_arr.size else 0.0
    g2 = float(hop2[t_arr].sum()) if t_arr.size else 0.0
    g3 = float(hop3[t_arr].sum()) if t_arr.size else 0.0
    path_rows.append({
        "цель": t_label,
        "прямых_рёбер_1шаг": int(len(direct_sub)),
        "прямых_синапсов_1шаг": round(float(direct_sub["syn_count"].sum()), 1),
        "передача_1шаг": round(g1, 5),
        "передача_2шага": round(g2, 5),
        "передача_3шага": round(g3, 5),
        "суммарный_коэффициент_1_3": round(g1 + 0.6 * g2 + 0.35 * g3, 5),
    })
df_paths = pd.DataFrame(path_rows)
df_paths.to_csv(RUN / "visual_to_dan_paths.csv", index=False)

anat_ppl1_gain = float(df_paths.loc[df_paths["цель"].str.startswith("PPL1"), "суммарный_коэффициент_1_3"].iloc[0])
anat_kc_gain = float(df_paths.loc[df_paths["цель"].str.startswith("KC"), "суммарный_коэффициент_1_3"].iloc[0])
# Нормируем анатомический коэффициент в долю от прямого безусловного удара (обычно 0.16..0.32)
eff_social_us = float(np.clip((anat_ppl1_gain * 1.55 + 0.04) * args.vis_gain, 0.03, 0.75))
print(
    f"аудит путей LC/VPN -> PPL1 ({source}): прямых рёбер={df_paths.iloc[1]['прямых_рёбер_1шаг']}, "
    f"суммарная передача={anat_ppl1_gain:.4f}, учительский сигнал наблюдения={eff_social_us:.3f} от прямого удара"
)

# 2. Сборка двух одинаковых контуров MB (Демонстратор D и Наблюдатель O)
N_KC = kc_idx.size
mbon_types = [str(t) for t in nodes.loc[nodes["idx"].isin(mbon_idx), "cell_type"].tolist()]
if any("app" in t for t in mbon_types) and any("avo" in t for t in mbon_types):
    app_cols = np.array(["app" in t for t in mbon_types], dtype=bool)
else:
    app_cols = np.arange(mbon_idx.size) < max(1, mbon_idx.size // 2)
avo_cols = ~app_cols

kc_pos = {int(k): i for i, k in enumerate(kc_idx)}
mb_pos = {int(m): i for i, m in enumerate(mbon_idx)}
W0 = np.zeros((N_KC, mbon_idx.size), dtype=np.float32)
sub_km = edges[edges["pre_idx"].isin(kc_idx) & edges["post_idx"].isin(mbon_idx)]
for pr, po, sc in zip(sub_km["pre_idx"], sub_km["post_idx"], sub_km["syn_count"]):
    W0[kc_pos[int(pr)], mb_pos[int(po)]] += math.log1p(float(sc))
if (W0 > 0).sum() == 0:
    W0 = (rng.random((N_KC, mbon_idx.size)) < 0.32).astype(np.float32)

k_act = max(4, int(round(N_KC * 0.06)))
kc_odor_A = np.zeros(N_KC, dtype=np.float32)
kc_odor_A[rng.choice(N_KC, size=k_act, replace=False)] = 1.0

kc_odor_B = np.zeros(N_KC, dtype=np.float32)
kc_odor_B[rng.choice(N_KC, size=k_act, replace=False)] = 1.0

# Зрительный вход в MB по каналу Vogt et al. 2016 активирует небольшую подгруппу KC наблюдателя
kc_vis_startle = np.zeros(N_KC, dtype=np.float32)
kc_vis_startle[rng.choice(N_KC, size=max(2, int(round(k_act * 0.35))), replace=False)] = 0.65


def avoid_score(W: np.ndarray, k_vec: np.ndarray) -> float:
    r = k_vec @ W
    b = k_vec @ W0
    app = float(r[app_cols].sum() / max(float(b[app_cols].sum()), 1e-6))
    avo = float(r[avo_cols].sum() / max(float(b[avo_cols].sum()), 1e-6))
    return float(avo - app)


def step_learn(W: np.ndarray, k_vec: np.ndarray, da_strength: float) -> np.ndarray:
    if da_strength <= 0.0:
        return W.copy()
    factor = 1.0 - np.clip(args.lr * da_strength, 0.0, 0.85) * k_vec[:, None] * app_cols[None, :].astype(np.float32)
    return np.clip(W * factor, 0.04 * W0, W0)


# Обучаем демонстратора D напрямую
W_D = W0.copy()
curve_direct = [avoid_score(W_D, kc_odor_A)]
for _ in range(args.n_direct):
    W_D = step_learn(W_D, kc_odor_A, da_strength=1.0)
    curve_direct.append(avoid_score(W_D, kc_odor_A))
behav_D = avoid_score(W_D, kc_odor_A)  # выраженность отскока демонстратора D (0..1)

# Верхняя граница («телепатия»): перенос дельты весов D -> O
W_tele = np.clip(W0 - (W0 - W_D), 0.04 * W0, W0)

# Настоящее наблюдение O: запах A + зрительный отскок D -> слабый сигнал PPL1
W_obs = W0.copy()
curve_obs = [avoid_score(W_obs, kc_odor_A)]
combined_kc = np.clip(kc_odor_A + 0.25 * kc_vis_startle, 0.0, 1.0)
for _ in range(args.n_obs):
    da_obs = eff_social_us * max(0.0, behav_D)
    W_obs = step_learn(W_obs, combined_kc, da_strength=da_obs)
    curve_obs.append(avoid_score(W_obs, kc_odor_A))

# Контроль a: O видит испуг D, но запаха A нет
W_ctrl_a = W0.copy()
for _ in range(args.n_obs):
    W_ctrl_a = step_learn(W_ctrl_a, kc_vis_startle, da_strength=eff_social_us * behav_D)

# Контроль b: O нюхает запах A один, без демонстратора D
W_ctrl_b = W0.copy()
for _ in range(args.n_obs):
    W_ctrl_b = step_learn(W_ctrl_b, kc_odor_A, da_strength=0.0)

# Контроль c: перемешанный зрительно-дофаминовый контур (случайный разброс по всем DAN, нет фокуса на PPL1)
shuf_edges = flylib.degree_preserving_shuffle(pos_edges, np.random.default_rng(args.seed + 313))
rs_s = np.bincount(shuf_edges["post_idx"].to_numpy(), minlength=N, weights=shuf_edges["syn_count"].to_numpy())
nw_s = shuf_edges["syn_count"].to_numpy() / np.maximum(rs_s[shuf_edges["post_idx"].to_numpy()], 1.0)
A_shuf = sparse.csr_matrix((nw_s.astype(np.float32), (shuf_edges["pre_idx"].to_numpy(), shuf_edges["post_idx"].to_numpy())), shape=(N, N))
h1_s = v_seed @ A_shuf
h2_s = h1_s @ A_shuf
# В перемешанном графе сигнал приходит одинаково на PPL1 и антагонист PAM, взаимно гася знак валентности
net_shuf_valence = max(0.0, float(h1_s[ppl1_idx].sum() + 0.6 * h2_s[ppl1_idx].sum()) - float(h1_s[pam_idx].sum() + 0.6 * h2_s[pam_idx].sum()))
W_ctrl_c = W0.copy()
for _ in range(args.n_obs):
    W_ctrl_c = step_learn(W_ctrl_c, combined_kc, da_strength=net_shuf_valence * 8.0 * behav_D)

# Контроль d: демонстратор D наивный и спокойный (behav_D = 0)
W_ctrl_d = W0.copy()
for _ in range(args.n_obs):
    W_ctrl_d = step_learn(W_ctrl_d, kc_odor_A, da_strength=0.02)

cond_df = pd.DataFrame([
    {"условие": "прямое обучение D", "избегание_A": round(behav_D, 4), "избегание_B": round(avoid_score(W_D, kc_odor_B), 4)},
    {"условие": "телепатия (верхняя граница)", "избегание_A": round(avoid_score(W_tele, kc_odor_A), 4), "избегание_B": round(avoid_score(W_tele, kc_odor_B), 4)},
    {"условие": "наблюдатель O (запах + D)", "избегание_A": round(avoid_score(W_obs, kc_odor_A), 4), "избегание_B": round(avoid_score(W_obs, kc_odor_B), 4)},
    {"условие": "контроль a: D без запаха", "избегание_A": round(avoid_score(W_ctrl_a, kc_odor_A), 4), "избегание_B": round(avoid_score(W_ctrl_a, kc_odor_B), 4)},
    {"условие": "контроль b: запах без D", "избегание_A": round(avoid_score(W_ctrl_b, kc_odor_A), 4), "избегание_B": round(avoid_score(W_ctrl_b, kc_odor_B), 4)},
    {"условие": "контроль c: shuffled зрение->DAN", "избегание_A": round(avoid_score(W_ctrl_c, kc_odor_A), 4), "избегание_B": round(avoid_score(W_ctrl_c, kc_odor_B), 4)},
    {"условие": "контроль d: спокойный D", "избегание_A": round(avoid_score(W_ctrl_d, kc_odor_A), 4), "избегание_B": round(avoid_score(W_ctrl_d, kc_odor_B), 4)},
])
cond_df.to_csv(RUN / "observational_conditions.csv", index=False)

# 3. Цепочка культурной передачи D -> O1 -> O2 -> O3 -> O4 при разном усилении канала зрение->DAN
chain_rows = []
for gain_label, gain_mult in (("слабый (x0.5)", 0.5), ("коннектом (x1.0)", 1.0), ("усиленный (x2.2)", 2.2)):
    cur_behav = behav_D
    chain_rows.append({"режим_связи": gain_label, "поколение": 0, "агент": "D", "избегание_A": round(cur_behav, 4)})
    for gen in range(1, 5):
        W_g = W0.copy()
        da_g = float(np.clip(eff_social_us * gain_mult, 0.02, 0.95)) * max(0.0, cur_behav)
        for _ in range(args.n_obs):
            W_g = step_learn(W_g, combined_kc, da_strength=da_g)
        cur_behav = avoid_score(W_g, kc_odor_A)
        chain_rows.append({"режим_связи": gain_label, "поколение": gen, "агент": f"O{gen}", "избегание_A": round(cur_behav, 4)})

df_chain = pd.DataFrame(chain_rows)
df_chain.to_csv(RUN / "cultural_chain.csv", index=False)

# График 2x2
plt, _, _ = flylib.setup_plot_style()
fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.0), dpi=140)

# [A] Сравнение наблюдателя с прямым обучением, телепатией и 4 контролями
yc = np.arange(len(cond_df))
c_bars = [
    flylib.PALETTE["brick"],
    flylib.PALETTE["umber"],
    flylib.PALETTE["steel"],
    flylib.PALETTE["stone"],
    flylib.PALETTE["stone"],
    flylib.PALETTE["slate"],
    flylib.PALETTE["stone"],
]
axes[0, 0].barh(yc, cond_df["избегание_A"], height=0.6, color=c_bars)
axes[0, 0].set_yticks(yc, cond_df["условие"], fontsize=8)
axes[0, 0].invert_yaxis()
axes[0, 0].axvline(0, color="#3c3833", lw=0.6)
axes[0, 0].set_xlabel("индекс избегания запаха A")
axes[0, 0].set_title("A. Наблюдатель против прямого обучения и 4 контролей")

# [B] Скорость обучения: прямое (D) против социального наблюдения (O)
axes[0, 1].plot(range(len(curve_direct)), curve_direct, marker="o", ms=4, lw=1.7, color=flylib.PALETTE["brick"], label="прямое обучение D (запах + удар)")
axes[0, 1].plot(range(len(curve_obs)), curve_obs, marker="s", ms=4, lw=1.7, color=flylib.PALETTE["steel"], label="наблюдатель O (запах + вид D)")
axes[0, 1].set_xlabel("число проб / показов")
axes[0, 1].set_ylabel("индекс избегания A")
axes[0, 1].set_title("B. Динамика накопления ассоциации у D и O")
axes[0, 1].legend(frameon=False, fontsize=8)

# [C] Культурная цепочка D -> O1 -> O2 -> O3 -> O4
for gi, (g_lbl, grp) in enumerate(df_chain.groupby("режим_связи", sort=False)):
    axes[1, 0].plot(grp["поколение"], grp["избегание_A"], marker="o", ms=4.5, lw=1.6, color=flylib.SERIES_COLORS[gi], label=g_lbl)
axes[1, 0].set_xticks([0, 1, 2, 3, 4], ["D", "O1", "O2", "O3", "O4"])
axes[1, 0].set_xlabel("звено социальной передачи")
axes[1, 0].set_ylabel("индекс избегания A")
axes[1, 0].set_title("C. Устойчивость культурной традиции по поколениям")
axes[1, 0].legend(frameon=False, fontsize=8)

# [D] Анатомический аудит путей LC/VPN -> KC / PPL1 / PAM по числу шагов
xp = np.arange(len(df_paths))
axes[1, 1].bar(xp - 0.22, df_paths["передача_1шаг"], width=0.21, color=flylib.PALETTE["brick"], label="1 шаг (прямые)")
axes[1, 1].bar(xp, df_paths["передача_2шага"], width=0.21, color=flylib.PALETTE["ochre"], label="2 шага")
axes[1, 1].bar(xp + 0.22, df_paths["передача_3шага"], width=0.21, color=flylib.PALETTE["steel"], label="3 шага")
axes[1, 1].set_xticks(xp, [c.split(" ")[0] for c in df_paths["цель"]], fontsize=8.5)
axes[1, 1].set_ylabel("нормированный коэффициент передачи")
axes[1, 1].set_title("D. Анатомические пути от зрения (LC/VPN) к MB и DAN")
axes[1, 1].legend(frameon=False, fontsize=8)

obs_val = float(cond_df.loc[cond_df["условие"].str.startswith("наблюдатель"), "избегание_A"].iloc[0])
fig.suptitle(
    f"Обучение через наблюдение ({source}): D={behav_D:.2f}, O={obs_val:.2f} ({obs_val / max(behav_D, 1e-6) * 100:.0f}% от прямого)",
    fontsize=10.5,
    x=0.012,
    ha="left",
)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(RUN / "observational_learning.png")
plt.close(fig)

summary = {
    "задача": "i-observational",
    "источник": source,
    "избегание_демонстратора_D": round(behav_D, 4),
    "избегание_наблюдателя_O": round(obs_val, 4),
    "доля_от_прямого_обучения": round(obs_val / max(behav_D, 1e-6), 4),
    "контроли": dict(zip(cond_df["условие"].iloc[3:], cond_df["избегание_A"].iloc[3:])),
    "анатомическая_передача_LC_PPL1": round(anat_ppl1_gain, 5),
    "анатомическая_передача_LC_KC": round(anat_kc_gain, 5),
    "затухание_к_O4_коннектом": float(df_chain[(df_chain["режим_связи"] == "коннектом (x1.0)") & (df_chain["агент"] == "O4")]["избегание_A"].iloc[0]),
    "файлы": ["observational_conditions.csv", "cultural_chain.csv", "visual_to_dan_paths.csv", "observational_learning.png"],
    "время_счета_с": round(time.time() - t0, 2),
}
flylib.save_json(RUN / "summary.json", summary)
print(f"наблюдатель O = {obs_val:.3f} ({obs_val / max(behav_D, 1e-6) * 100:.1f}% от D), готово за {summary['время_счета_с']} с -> {RUN}")
