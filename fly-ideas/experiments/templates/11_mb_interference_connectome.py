#!/usr/bin/env python3
"""Интерференция, перегрузка памяти и четыре пробы вспоминания на контуре грибовидных тел.

Готовый анализ для задачи «Переучить, забить память, вспомнить первое: интерференция и восстановление в MB»
(i-interference). Переносит когнитивный протокол Bouton 2004 и Felsenberg et al. 2018 со схемной модели
на реальные клетки PN -> KC -> MBON коннектома (FlyWire v783 или MaleCNS v1.0, с синтетическим режимом).

Пять фаз протокола:
  1) обучение запаху A с наказанием (PPL1) -> снимок синапсов W1;
  2) переучивание (угасание как параллельный след, реверс с наградой или конкурирующий запах B) -> снимок W2;
  3) загрузка памяти N случайными ассоциациями при разреженности APL -> снимок W3;
  4) четыре независимые пробы возврата первой памяти из W3:
     - спонтанное восстановление (асимметричный распад свежего следа угасания быстрее первичного следа);
     - reinstatement (одиночный безусловный удар в контексте без запаха);
     - renewal ABA (обучение в контексте C1, угасание в C2, проверка возврата в C1);
     - savings (число проб повторного обучения до 75 % критерия против наивной сети);
  5) синаптическая декомпозиция W1, W2, W3 на ансамбле KC запаха A: стирание против маскировки.

Примеры:
  python 11_mb_interference_connectome.py --synth
  python 11_mb_interference_connectome.py --relearn extinction --n-junk 50 --sparsity 0.05
  python 11_mb_interference_connectome.py --relearn reversal --n-junk 80 --seed 2

Результат: interference_protocol.csv, recovery_probes.csv, synaptic_traces.csv, interference_connectome.png, summary.json.
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

ap = argparse.ArgumentParser(description="Интерференция и возврат памяти в контуре MB коннектома")
ap.add_argument("--synth", action="store_true", help="работать на синтетическом контуре")
ap.add_argument("--connectome", choices=["flywire", "malecns"], default="flywire")
ap.add_argument("--relearn", choices=["extinction", "reversal", "competitor", "none"], default="extinction")
ap.add_argument("--n-train", type=int, default=6, help="проб первичного обучения A + удар")
ap.add_argument("--n-relearn", type=int, default=8, help="проб переучивания")
ap.add_argument("--n-junk", type=int, default=45, help="число интерферирующих запахов")
ap.add_argument("--sparsity", type=float, default=0.05, help="доля активных KC под торможением APL")
ap.add_argument("--lr", type=float, default=0.22, help="скорость синаптической депрессии KC->MBON")
ap.add_argument("--tau-acq", type=float, default=480.0, help="постоянная распада консолидированного следа страха")
ap.add_argument("--tau-ext", type=float, default=95.0, help="постоянная распада лабильного следа угасания")
ap.add_argument("--wait", type=int, default=160, help="интервал ожидания для спонтанного восстановления")
ap.add_argument("--context-frac", type=float, default=0.18, help="вклад контекстного входа в отбор KC (для ABA renewal)")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

t0 = time.time()
RUN.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(args.seed)

loader = flylib.load_malecns if args.connectome == "malecns" else flylib.load_flywire
nodes, edges, source = loader(seed=args.seed, synth=args.synth)

ct = nodes["cell_type"].astype(str)
pn_idx = nodes.loc[ct.str.contains(r"^PN|Or67|Or56", regex=True), "idx"].to_numpy(dtype=np.int32)
kc_idx = nodes.loc[ct.str.startswith("KC"), "idx"].to_numpy(dtype=np.int32)
mbon_idx = nodes.loc[ct.str.startswith("MBON"), "idx"].to_numpy(dtype=np.int32)
ppl1_idx = nodes.loc[ct.str.startswith("PPL1"), "idx"].to_numpy(dtype=np.int32)
pam_idx = nodes.loc[ct.str.contains(r"^PAM|aSP13", regex=True), "idx"].to_numpy(dtype=np.int32)

# Если в скачанном FlyWire v783 ещё нет таблицы аннотаций типов, синтезируем подконтур MB
if kc_idx.size < 30 or mbon_idx.size < 2:
    print("В таблице нет размеченных KC/MBON (скачай аннотации Schlegel 2024 во вкладке «Данные»), строю модельный MB.")
    nodes, edges, source = flylib.build_synthetic_connectome(seed=args.seed, male=(args.connectome == "malecns"))
    ct = nodes["cell_type"].astype(str)
    pn_idx = nodes.loc[ct.str.contains(r"^PN|Or67", regex=True), "idx"].to_numpy(dtype=np.int32)
    kc_idx = nodes.loc[ct.str.startswith("KC"), "idx"].to_numpy(dtype=np.int32)
    mbon_idx = nodes.loc[ct.str.startswith("MBON"), "idx"].to_numpy(dtype=np.int32)
    ppl1_idx = nodes.loc[ct.str.startswith("PPL1"), "idx"].to_numpy(dtype=np.int32)
    pam_idx = nodes.loc[ct.str.contains(r"^PAM|aSP13", regex=True), "idx"].to_numpy(dtype=np.int32)

N_PN = max(60, pn_idx.size)
N_KC = kc_idx.size
N_MBON = mbon_idx.size

# Матрица PN -> KC из коннектома (или разреженная когерентная проекция по числу коготков KC ~7)
kc_map = {int(v): i for i, v in enumerate(kc_idx)}
pn_map = {int(v): i for i, v in enumerate(pn_idx)}
sub_pk = edges[edges["pre_idx"].isin(pn_idx) & edges["post_idx"].isin(kc_idx)]
if len(sub_pk) >= N_KC:
    W_pn_kc = np.zeros((N_PN, N_KC), dtype=np.float32)
    for p_i, k_i, w_v in zip(sub_pk["pre_idx"], sub_pk["post_idx"], sub_pk["syn_count"]):
        W_pn_kc[pn_map[int(p_i)], kc_map[int(k_i)]] += math.log1p(float(w_v))
else:
    W_pn_kc = (rng.random((N_PN, N_KC)) < (7.0 / N_PN)).astype(np.float32)

# Матрица KC -> MBON из реальных весов коннектома + разделение MBON на приближение и избегание по входам PPL1/PAM
mbon_map = {int(v): i for i, v in enumerate(mbon_idx)}
W_base = np.zeros((N_KC, N_MBON), dtype=np.float32)
sub_km = edges[edges["pre_idx"].isin(kc_idx) & edges["post_idx"].isin(mbon_idx)]
for k_i, m_i, w_v in zip(sub_km["pre_idx"], sub_km["post_idx"], sub_km["syn_count"]):
    W_base[kc_map[int(k_i)], mbon_map[int(m_i)]] += math.log1p(abs(float(w_v)))
if (W_base > 0).sum() == 0:
    W_base = (rng.random((N_KC, N_MBON)) < 0.35).astype(np.float32)

ppl1_in = np.zeros(N_MBON, dtype=np.float32)
pam_in = np.zeros(N_MBON, dtype=np.float32)
for p_i, m_i, w_v in zip(edges["pre_idx"], edges["post_idx"], edges["syn_count"]):
    mi = mbon_map.get(int(m_i), -1)
    if mi >= 0:
        if int(p_i) in set(ppl1_idx.tolist()):
            ppl1_in[mi] += abs(float(w_v))
        elif int(p_i) in set(pam_idx.tolist()):
            pam_in[mi] += abs(float(w_v))

mbon_types = [str(t) for t in nodes.loc[nodes["idx"].isin(mbon_idx), "cell_type"].tolist()]
if any("app" in t for t in mbon_types) and any("avo" in t for t in mbon_types):
    app_cols = np.array(["app" in t for t in mbon_types], dtype=bool)
elif (ppl1_in.sum() > 0) and (pam_in.sum() > 0) and not np.all(ppl1_in >= pam_in):
    app_cols = ppl1_in >= pam_in
else:
    app_cols = np.arange(N_MBON) < (N_MBON // 2)
avo_cols = ~app_cols
if not avo_cols.any():
    avo_cols[-1] = True
    app_cols[-1] = False

print(
    f"контур MB ({source}): PN={N_PN}, KC={N_KC}, MBON={N_MBON} "
    f"(приближение {int(app_cols.sum())}, избегание {int(avo_cols.sum())}), связей KC->MBON={int((W_base > 0).sum())}"
)


def make_odor(seed_id: int) -> np.ndarray:
    r = np.random.default_rng(seed_id)
    v = np.zeros(N_PN, dtype=np.float32)
    active = r.choice(N_PN, size=max(4, int(N_PN * 0.12)), replace=False)
    v[active] = 1.0
    return v


def make_context(seed_id: int) -> np.ndarray:
    r = np.random.default_rng(seed_id)
    c = np.zeros(N_KC, dtype=np.float32)
    c[r.choice(N_KC, size=max(6, int(N_KC * 0.15)), replace=False)] = 1.0
    return c


def kc_response(odor_vec: np.ndarray, ctx_vec: np.ndarray, sparsity: float) -> np.ndarray:
    k_act = max(2, int(round(N_KC * sparsity)))
    drive = odor_vec @ W_pn_kc
    if drive.max() > 0:
        drive = drive / (drive.max() + 1e-9)
    total = (1.0 - args.context_frac) * drive + args.context_frac * ctx_vec
    top = np.argpartition(total, -k_act)[-k_act:]
    out = np.zeros(N_KC, dtype=np.float32)
    out[top] = 1.0
    return out


def avoidance(W: np.ndarray, k_vec: np.ndarray) -> float:
    """Показатель избегания: >0 избегание запаха, <0 влечение, 0 нейтрально."""
    resp = k_vec @ W
    base = k_vec @ W_base
    r_app = float(resp[app_cols].sum() / max(float(base[app_cols].sum()), 1e-6))
    r_avo = float(resp[avo_cols].sum() / max(float(base[avo_cols].sum()), 1e-6))
    return float(r_avo - r_app)


def depress(W: np.ndarray, k_vec: np.ndarray, cols_mask: np.ndarray, lr: float, hetero_ltp: float = 0.0) -> np.ndarray:
    """Дофаминовая депрессия целевого компартмента + гетеросинаптический откат антагониста (Cohn et al. 2015)."""
    out = W.copy()
    factor = 1.0 - lr * k_vec[:, None] * cols_mask[None, :].astype(np.float32)
    out = out * factor
    if hetero_ltp > 0.0:
        opp = (~cols_mask)[None, :].astype(np.float32)
        out = out + hetero_ltp * lr * k_vec[:, None] * opp * (W_base - out)
    return np.clip(out, 0.02 * W_base, W_base)


odor_A = make_odor(1001 + args.seed * 100)
odor_B = make_odor(1002 + args.seed * 100)
ctx_1 = make_context(2001 + args.seed * 100)
ctx_2 = make_context(2002 + args.seed * 100)

kA_c1 = kc_response(odor_A, ctx_1, args.sparsity)
kA_c2 = kc_response(odor_A, ctx_2, args.sparsity)
kB_c1 = kc_response(odor_B, ctx_1, args.sparsity)

W = W_base.copy()
W0 = W.copy()
traj = []
step_no = 0


def record(phase: str, ctx_name: str, W_cur: np.ndarray):
    global step_no
    traj.append({
        "шаг": step_no,
        "фаза": phase,
        "контекст_теста": ctx_name,
        "избегание_A_C1": round(avoidance(W_cur, kA_c1), 4),
        "избегание_A_C2": round(avoidance(W_cur, kA_c2), 4),
        "избегание_B_C1": round(avoidance(W_cur, kB_c1), 4),
    })
    step_no += 1


record("наивная", "C1", W)

# Фаза 1: обучение A + удар в контексте C1
for _ in range(args.n_train):
    W = depress(W, kA_c1, app_cols, args.lr)
    record("обучение", "C1", W)
W1 = W.copy()

# Фаза 2: переучивание (угасание в контексте C2 для честной проверки ABA renewal)
relearn_ctx = kA_c2 if args.relearn == "extinction" else kA_c1
for _ in range(args.n_relearn):
    if args.relearn == "extinction":
        # По Felsenberg et al. 2018: угасание строит параллельную депрессию в избегающем компартменте
        W = depress(W, relearn_ctx, avo_cols, 0.68 * args.lr)
    elif args.relearn == "reversal":
        W = depress(W, kA_c1, avo_cols, args.lr)
    elif args.relearn == "competitor":
        W = depress(W, kB_c1, app_cols, args.lr)
        W = depress(W, kA_c1, avo_cols, 0.22 * args.lr)
    record("переучивание", "C2" if args.relearn == "extinction" else "C1", W)
W2 = W.copy()

# Фаза 3: заполнение памяти случайными запахами
junk_hit_counts = np.zeros(N_KC, dtype=np.int32)
for j in range(args.n_junk):
    oj = make_odor(5000 + args.seed * 500 + j)
    kj = kc_response(oj, ctx_1 if j % 2 == 0 else ctx_2, args.sparsity)
    junk_hit_counts += (kj > 0).astype(np.int32)
    us_cols = app_cols if (j % 2 == 0) else avo_cols
    # Небольшой гомеостатический возврат при интенсивной перезаписи + новая ассоциация
    W = W + 0.008 * (W_base - W)
    W = depress(W, kj, us_cols, 0.55 * args.lr)
    if (j + 1) % max(1, args.n_junk // 8) == 0 or j == args.n_junk - 1:
        record("интерференция", "C2", W)
W3 = W.copy()

# Фаза 4: четыре независимые пробы возврата первого следа из W3
base_test_vec = kA_c2 if args.relearn == "extinction" else kA_c1
after_junk_val = avoidance(W3, base_test_vec)
after_learn_val = avoidance(W1, kA_c1)

# 4a. Спонтанное восстановление: лабильный след в avo распадается с tau_ext, консолидированный в app с tau_acq
W_sr = W3.copy()
r_acq = 1.0 - math.exp(-args.wait / max(1.0, args.tau_acq))
r_ext = 1.0 - math.exp(-args.wait / max(1.0, args.tau_ext))
W_sr[:, app_cols] += (W_base[:, app_cols] - W_sr[:, app_cols]) * r_acq
W_sr[:, avo_cols] += (W_base[:, avo_cols] - W_sr[:, avo_cols]) * r_ext
sr_val = avoidance(W_sr, base_test_vec)

# 4b. Reinstatement: одиночный удар без запаха активирует контекстный пул C1 + PPL1
k_ctx_only = (ctx_1 > 0).astype(np.float32)
W_ri = depress(W3, k_ctx_only, app_cols, 0.75 * args.lr)
ri_val = avoidance(W_ri, kA_c1)

# 4c. Renewal (ABA): возврат из контекста угасания C2 обратно в контекст обучения C1
rn_c2 = avoidance(W3, kA_c2)
rn_c1 = avoidance(W3, kA_c1)

# 4d. Savings: число проб A + удар до 70 % от уровня W1 из W3 против наивной W0 (с учётом гетеросинаптического растормаживания PPL1)
criterion = 0.70 * after_learn_val
W_sav = W3.copy()
trials_relearn = 0
while avoidance(W_sav, kA_c1) < criterion and trials_relearn < 25:
    W_sav = depress(W_sav, kA_c1, app_cols, args.lr, hetero_ltp=0.85)
    trials_relearn += 1

W_naive = W0.copy()
trials_naive = 0
while avoidance(W_naive, kA_c1) < criterion and trials_naive < 25:
    W_naive = depress(W_naive, kA_c1, app_cols, args.lr, hetero_ltp=0.85)
    trials_naive += 1
savings_pct = round(100.0 * (trials_naive - trials_relearn) / max(1, trials_naive), 1)

probes_df = pd.DataFrame([
    {"проба": "после обучения (W1)", "индекс_избегания": round(after_learn_val, 4)},
    {"проба": "после переучивания (W2)", "индекс_избегания": round(avoidance(W2, base_test_vec), 4)},
    {"проба": "после мусорных запахов (W3)", "индекс_избегания": round(after_junk_val, 4)},
    {"проба": "спонтанное восстановление", "индекс_избегания": round(sr_val, 4)},
    {"проба": "reinstatement (удар без запаха)", "индекс_избегания": round(ri_val, 4)},
    {"проба": "renewal ABA (возврат в C1)", "индекс_избегания": round(rn_c1, 4)},
])

# Фаза 5: синаптический разбор W1, W2, W3 на ансамбле KC запаха A
kc_mask_A = kA_c1 > 0
base_app_A = max(float(W_base[kc_mask_A][:, app_cols].sum()), 1e-6)
base_avo_A = max(float(W_base[kc_mask_A][:, avo_cols].sum()), 1e-6)

syn_rows = []
for snap_name, snap_W in (("W0_наивная", W0), ("W1_обучение", W1), ("W2_переучивание", W2), ("W3_интерференция", W3), ("W4_спонтанное", W_sr)):
    dep_app = 1.0 - float(snap_W[kc_mask_A][:, app_cols].sum()) / base_app_A
    dep_avo = 1.0 - float(snap_W[kc_mask_A][:, avo_cols].sum()) / base_avo_A
    syn_rows.append({
        "снимок": snap_name,
        "первичный_след_депрессия_app": round(dep_app, 4),
        "параллельный_след_депрессия_avo": round(dep_avo, 4),
        "разность_путей": round(dep_app - dep_avo, 4),
    })
df_syn = pd.DataFrame(syn_rows)

dW1 = (W_base - W1).ravel()
dW3 = (W_base - W3).ravel()
cos_w1_w3 = float(np.dot(dW1, dW3) / max(np.linalg.norm(dW1) * np.linalg.norm(dW3), 1e-9))
primary_w1 = syn_rows[1]["первичный_след_депрессия_app"]
primary_w3 = syn_rows[3]["первичный_след_депрессия_app"]
masking_w3 = syn_rows[3]["параллельный_след_депрессия_avo"]
retention_primary = primary_w3 / max(primary_w1, 1e-6)
junk_overlap = float((junk_hit_counts[kc_mask_A] > 0).mean())

if retention_primary >= 0.6 and masking_w3 >= 0.25:
    verdict = "маскировка: первичный след в KC->MBON_app сохранён, но перекрыт параллельной депрессией KC->MBON_avo"
elif retention_primary < 0.45:
    verdict = "частичное стирание: перезапись ансамбля KC снизила первичный след"
else:
    verdict = "след сохранён и доминирует над конкурирующими ассоциациями"

# Дополнительная развёртка ёмкости по числу мусорных запахов при 3 уровнях разреженности APL
junk_grid = [0, 15, 30, 60, 100]
sparsity_levels = [0.02, 0.05, 0.12]
cap_curves: dict[float, list[float]] = {}
for sp in sparsity_levels:
    vals = []
    kA_sp = kc_response(odor_A, ctx_1, sp)
    for nj in junk_grid:
        Wt = depress(W_base, kA_sp, app_cols, args.lr * 2.2)
        for j in range(nj):
            kj = kc_response(make_odor(8000 + j), ctx_1, sp)
            Wt = Wt + 0.008 * (W_base - Wt)
            Wt = depress(Wt, kj, app_cols if j % 2 == 0 else avo_cols, 0.55 * args.lr)
        vals.append(avoidance(Wt, kA_sp))
    cap_curves[sp] = vals

df_traj = pd.DataFrame(traj)
df_traj.to_csv(RUN / "interference_protocol.csv", index=False)
probes_df.to_csv(RUN / "recovery_probes.csv", index=False)
df_syn.to_csv(RUN / "synaptic_traces.csv", index=False)

# График 2x2
plt, _, _ = flylib.setup_plot_style()
fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.0), dpi=140)

# [A] Траектория по фазам в C1 и C2
axes[0, 0].plot(df_traj["шаг"], df_traj["избегание_A_C1"], lw=1.6, color=flylib.PALETTE["brick"], label="запах A (контекст обучения C1)")
axes[0, 0].plot(df_traj["шаг"], df_traj["избегание_A_C2"], lw=1.4, ls="--", color=flylib.PALETTE["steel"], label="запах A (контекст угасания C2)")
axes[0, 0].plot(df_traj["шаг"], df_traj["избегание_B_C1"], lw=1.1, color=flylib.PALETTE["olive"], label="контрольный запах B")
for ph, grp in df_traj.groupby("фаза", sort=False):
    x0 = int(grp["шаг"].iloc[0])
    if x0 > 0:
        axes[0, 0].axvline(x0, color="#9a938a", lw=0.6, ls=":")
        axes[0, 0].text(x0 + 0.25, 0.96, ph, transform=axes[0, 0].get_xaxis_transform(), fontsize=7.5, rotation=90, va="top", color="#6b655e")
axes[0, 0].axhline(0, color="#3c3833", lw=0.6)
axes[0, 0].set_xlabel("шаг протокола")
axes[0, 0].set_ylabel("индекс избегания")
axes[0, 0].set_title(f"A. Ход протокола ({args.relearn}, мусорных запахов {args.n_junk})")
axes[0, 0].legend(frameon=False, fontsize=7.5, loc="best")

# [B] Четыре пробы возврата памяти
y_pos = np.arange(len(probes_df))
bar_colors = [
    flylib.PALETTE["brick"],
    flylib.PALETTE["stone"],
    flylib.PALETTE["slate"],
    flylib.PALETTE["ochre"],
    flylib.PALETTE["olive"],
    flylib.PALETTE["steel"],
]
axes[0, 1].barh(y_pos, probes_df["индекс_избегания"], color=bar_colors, height=0.62)
axes[0, 1].set_yticks(y_pos, probes_df["проба"], fontsize=8)
axes[0, 1].invert_yaxis()
axes[0, 1].axvline(0, color="#3c3833", lw=0.6)
axes[0, 1].set_xlabel("индекс избегания запаха A")
axes[0, 1].set_title(f"B. Возврат первой памяти (savings: {trials_relearn} проб против {trials_naive}, выигрыш {savings_pct}%)")

# [C] Синаптическая декомпозиция: первичный след против маскирующего
x_s = np.arange(len(df_syn))
axes[1, 0].bar(x_s - 0.17, df_syn["первичный_след_депрессия_app"], width=0.32, color=flylib.PALETTE["brick"], label="первичный след (депрессия KC->app)")
axes[1, 0].bar(x_s + 0.17, df_syn["параллельный_след_депрессия_avo"], width=0.32, color=flylib.PALETTE["steel"], label="параллельный след (депрессия KC->avo)")
axes[1, 0].set_xticks(x_s, [s.replace("_", "\n") for s in df_syn["снимок"]], fontsize=7.5)
axes[1, 0].set_ylabel("доля депрессии весов ансамбля A")
axes[1, 0].set_ylim(0, 1.05)
axes[1, 0].set_title("C. Синапсы ансамбля A: стирание или маскировка")
axes[1, 0].legend(frameon=False, fontsize=7.5, loc="best")

# [D] Ёмкость кода при разной силе торможения APL
for idx_c, (sp, vals) in enumerate(cap_curves.items()):
    axes[1, 1].plot(
        junk_grid,
        vals,
        marker="o",
        ms=4,
        lw=1.6,
        color=flylib.SERIES_COLORS[idx_c],
        label=f"разреженность KC {int(sp * 100)} %",
    )
axes[1, 1].axhline(0, color="#3c3833", lw=0.6)
axes[1, 1].set_xlabel("число случайных интерферирующих ассоциаций")
axes[1, 1].set_ylabel("остаточное избегание A")
axes[1, 1].set_title("D. Ёмкость памяти MB и роль разреженности APL")
axes[1, 1].legend(frameon=False, fontsize=8, loc="best")

fig.suptitle(
    f"Интерференция в MB ({source}): KC={N_KC}, MBON={N_MBON}, сохранность 1-го следа={retention_primary:.2f}",
    fontsize=10.5,
    x=0.012,
    ha="left",
)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(RUN / "interference_connectome.png")
plt.close(fig)

summary = {
    "задача": "i-interference",
    "источник": source,
    "KC": int(N_KC),
    "MBON": int(N_MBON),
    "args": vars(args),
    "пробы_возврата": {
        "после_обучения_W1": round(after_learn_val, 4),
        "после_мусора_W3": round(after_junk_val, 4),
        "спонтанное_восстановление": round(sr_val, 4),
        "reinstatement": round(ri_val, 4),
        "renewal_ABA_C1": round(rn_c1, 4),
        "renewal_в_C2": round(rn_c2, 4),
        "savings_проб_переучивание": int(trials_relearn),
        "savings_проб_наивная": int(trials_naive),
        "savings_выигрыш_проц": savings_pct,
    },
    "синаптический_разбор": {
        "сохранность_первичного_следа": round(retention_primary, 4),
        "сила_маскирующего_следа": round(masking_w3, 4),
        "перекрытие_ансамбля_A_с_мусором": round(junk_overlap, 4),
        "косинус_dW1_dW3": round(cos_w1_w3, 4),
        "вывод": verdict,
    },
    "файлы": ["interference_protocol.csv", "recovery_probes.csv", "synaptic_traces.csv", "interference_connectome.png"],
    "время_счета_с": round(time.time() - t0, 2),
}
flylib.save_json(RUN / "summary.json", summary)
print("вывод:", verdict)
print(f"готово за {summary['время_счета_с']} с -> {RUN}")
