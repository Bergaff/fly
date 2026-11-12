#!/usr/bin/env python3
"""Обучение в грибовидных телах внутри спайковой сети целого мозга и контроль перемешанного коннектома.

Готовый анализ для задачи «Обучение в грибовидных телах внутри целого мозга» (i-mb-learning).
Встраивает трёхфакторную дофамин-модулируемую пластичность (след пригодности KC x сигнал PPL1)
непосредственно в возвратную спайковую LIF-сеть мозга, сохраняя фоновую реверберацию, обходной
врождённый путь через латеральный рог (LH) и возвратное торможение APL.

Протокол:
  - дифференциальное обучение: запах CS+ (A + наказание PPL1) против контрольного CS- (B без наказания);
  - тест обобщения на запах C (50 % общих входов PN с запахом A) и фаза угасания;
  - три структурных режима на одних и тех же гиперпараметрах:
      1) intact   : реальная структура коннектома с торможением APL;
      2) no_apl   : выключен тормозный нейрон APL (проверка потери разреженности и специфичности);
      3) shuffled : перемешанный коннектом с сохранением степеней и баланса возбуждения/торможения.

Примеры:
  python 13_whole_brain_mb_learning.py --synth
  python 13_whole_brain_mb_learning.py --max-neurons 3000 --n-trials 8 --lr 0.08
  python 13_whole_brain_mb_learning.py --no-shuffled --n-trials 12

Результат: whole_brain_learning.csv, whole_brain_vs_shuffled.csv, whole_brain_mb.png, summary.json.
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

ap = argparse.ArgumentParser(description="Спайковое обучение в MB внутри целого мозга")
ap.add_argument("--synth", action="store_true", help="работать на модульном синтетическом коннектоме")
ap.add_argument("--max-neurons", type=int, default=2500, help="размер сети (0 = весь коннектом)")
ap.add_argument("--n-trials", type=int, default=7, help="парных проб обучения CS+ и CS-")
ap.add_argument("--n-ext", type=int, default=4, help="проб угасания после теста")
ap.add_argument("--trial-sec", type=float, default=0.18, help="длительность одного предъявления запаха, с")
ap.add_argument("--lr", type=float, default=0.09, help="скорость трёхфакторной пластичности KC->MBON")
ap.add_argument("--tau-elig", type=float, default=45.0, help="постоянная следа пригодности KC, мс")
ap.add_argument("--no-shuffled", action="store_true", help="пропустить контроль с перемешанным коннектомом")
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

t0 = time.time()
RUN.mkdir(parents=True, exist_ok=True)

nodes, edges, source = flylib.load_flywire(max_neurons=args.max_neurons, seed=args.seed, synth=args.synth)
ct = nodes["cell_type"].astype(str)
if int(ct.str.startswith("KC").sum()) < 20 or int(ct.str.startswith("MBON").sum()) < 2:
    print("В скачанных таблицах нет разметки KC/MBON, использую полномодульную синтетическую сеть мозга.")
    nodes, edges, source = flylib.build_synthetic_connectome(seed=args.seed, male=False)
    ct = nodes["cell_type"].astype(str)

N = len(nodes)
pn_idx = nodes.loc[ct.str.contains(r"^PN|Or67|Or56", regex=True), "idx"].to_numpy(dtype=np.int32)
kc_idx = nodes.loc[ct.str.startswith("KC"), "idx"].to_numpy(dtype=np.int32)
apl_idx = nodes.loc[ct.str.startswith("APL"), "idx"].to_numpy(dtype=np.int32)
mbon_idx = nodes.loc[ct.str.startswith("MBON"), "idx"].to_numpy(dtype=np.int32)
ppl1_idx = nodes.loc[ct.str.startswith("PPL1"), "idx"].to_numpy(dtype=np.int32)
dn_idx = nodes.loc[nodes["region"].isin(["DN_MOTOR", "VNC_MOTOR"]), "idx"].to_numpy(dtype=np.int32)

mbon_types = [str(t) for t in nodes.loc[nodes["idx"].isin(mbon_idx), "cell_type"].tolist()]
if any("app" in t for t in mbon_types) and any("avo" in t for t in mbon_types):
    mbon_app = mbon_idx[[("app" in t) for t in mbon_types]]
    mbon_avo = mbon_idx[[("avo" in t) for t in mbon_types]]
else:
    half = max(1, mbon_idx.size // 2)
    mbon_app, mbon_avo = mbon_idx[:half], mbon_idx[half:]

rng_od = np.random.default_rng(args.seed + 55)
k_pn = max(6, int(pn_idx.size * 0.16))
odor_A = rng_od.choice(pn_idx, size=k_pn, replace=False)
rem_pn = np.setdiff1d(pn_idx, odor_A)
odor_B = rng_od.choice(rem_pn if rem_pn.size >= k_pn else pn_idx, size=k_pn, replace=False)
odor_C = np.concatenate([odor_A[: k_pn // 2], odor_B[: k_pn - k_pn // 2]])

print(
    f"сеть целого мозга ({source}): всего={N}, PN={pn_idx.size}, KC={kc_idx.size}, "
    f"APL={apl_idx.size}, MBON={mbon_idx.size}, PPL1={ppl1_idx.size}"
)


def run_condition(cond_name: str, edge_df: pd.DataFrame, silence_apl: bool = False):
    """Прогоняет спайковую LIF-сеть всего мозга с пластичной подматрицей KC -> MBON."""
    p = flylib.SHIU_DEFAULTS
    dt_ms = 0.25
    steps = max(20, int(round(args.trial_sec * 1000.0 / dt_ms)))
    rfc_steps = max(1, int(round(p["t_rfc"] / dt_ms)))
    decay_v = math.exp(-dt_ms / p["t_mbr"])
    decay_g = math.exp(-dt_ms / p["tau_g"])
    decay_e = math.exp(-dt_ms / args.tau_elig)
    alpha_v = 1.0 - decay_v

    is_kc = np.isin(edge_df["pre_idx"].to_numpy(), kc_idx)
    is_mbon = np.isin(edge_df["post_idx"].to_numpy(), mbon_idx)
    plastic_mask = is_kc & is_mbon

    fixed_edges = edge_df[~plastic_mask]
    W_fixed = flylib.build_weight_matrix(N, fixed_edges, w_syn=p["w_syn"])

    kc_pos = {int(k): i for i, k in enumerate(kc_idx)}
    mb_pos = {int(m): i for i, m in enumerate(mbon_idx)}
    W_km = np.zeros((mbon_idx.size, kc_idx.size), dtype=np.float32)
    for pr, po, sw in zip(
        edge_df.loc[plastic_mask, "pre_idx"],
        edge_df.loc[plastic_mask, "post_idx"],
        edge_df.loc[plastic_mask, "signed_weight"],
    ):
        W_km[mb_pos[int(po)], kc_pos[int(pr)]] += float(abs(sw) * p["w_syn"])
    if (W_km > 0).sum() == 0:
        r_init = np.random.default_rng(args.seed + 9)
        W_km = (r_init.random((mbon_idx.size, kc_idx.size)) < 0.25).astype(np.float32) * 1.1
    W_km_init = W_km.copy()

    app_local = np.isin(mbon_idx, mbon_app)
    avo_local = np.isin(mbon_idx, mbon_avo)
    sil_mask = np.ones(N, dtype=np.float32)
    if silence_apl and apl_idx.size:
        sil_mask[apl_idx] = 0.0

    rng = np.random.default_rng(args.seed + 404)
    p_bg = 26.0 * dt_ms / 1000.0
    w_poi = float(p["w_syn"] * p["f_poi"] * 0.145)

    def simulate_trial(stim_pn: np.ndarray, shock_us: bool, plastic_on: bool, ext_mode: bool = False):
        nonlocal W_km
        v = np.full(N, float(p["v_0"]), dtype=np.float32)
        g = np.zeros(N, dtype=np.float32)
        ref = np.zeros(N, dtype=np.int16)
        elig_kc = np.zeros(kc_idx.size, dtype=np.float32)
        counts = np.zeros(N, dtype=np.int32)
        p_pn = min(0.9, 220.0 * dt_ms / 1000.0)
        p_us = min(0.9, 180.0 * dt_ms / 1000.0)

        for st in range(steps):
            v[rng.random(N, dtype=np.float32) < p_bg] += 2.7
            if stim_pn.size:
                hits = rng.random(stim_pn.size) < p_pn
                if hits.any():
                    v[stim_pn[hits]] += w_poi
            if shock_us and ppl1_idx.size and st >= steps // 3:
                uhits = rng.random(ppl1_idx.size) < p_us
                if uhits.any():
                    v[ppl1_idx[uhits]] += w_poi * 1.15

            act = ref <= 0
            v[act] = float(p["v_0"]) + (v[act] - float(p["v_0"])) * decay_v + g[act] * alpha_v
            g *= decay_g
            elig_kc *= decay_e
            ref[~act] -= 1

            fired = act & (v > float(p["v_th"])) & (sil_mask > 0.5)
            if fired.any():
                fi = np.flatnonzero(fired)
                v[fi] = float(p["v_rst"])
                g[fi] = 0.0
                ref[fi] = rfc_steps
                counts[fi] += 1

                spk_vec = fired.astype(np.float32)
                g += W_fixed.dot(spk_vec)
                kc_spk = spk_vec[kc_idx]
                if kc_spk.any():
                    g[mbon_idx] += W_km @ kc_spk
                    elig_kc += kc_spk

                if plastic_on:
                    da_signal = float(spk_vec[ppl1_idx].mean()) if ppl1_idx.size else (1.0 if shock_us else 0.0)
                    if da_signal > 0.0 and elig_kc.max() > 0.0:
                        # Трёхфакторная депрессия KC -> MBON_app при совпадении следа KC и спайков PPL1
                        delta = args.lr * da_signal * elig_kc[None, :]
                        W_km[app_local] = np.maximum(0.08 * W_km_init[app_local], W_km[app_local] * (1.0 - delta))
                    elif ext_mode and kc_spk.any() and st >= steps // 2:
                        # Параллельное ослабление избегающего компартмента при предъявлении CS+ без удара
                        W_km[avo_local] = np.maximum(
                            0.12 * W_km_init[avo_local],
                            W_km[avo_local] * (1.0 - 0.012 * args.lr * elig_kc[None, :]),
                        )

        rates = counts.astype(np.float32) / max(args.trial_sec, 1e-6)
        r_app = float(rates[mbon_app].mean())
        r_avo = float(rates[mbon_avo].mean())
        denom = max(r_app + r_avo, 1.0)
        valence_avoid = (r_avo - r_app) / denom
        kc_active_frac = float((counts[kc_idx] > 0).mean())
        non_mb = ~np.isin(np.arange(N), np.concatenate([pn_idx, kc_idx, mbon_idx, ppl1_idx]))
        bg_brain_hz = float(rates[non_mb].mean()) if non_mb.any() else float(rates.mean())
        return {
            "avoid_index": valence_avoid,
            "r_app_hz": r_app,
            "r_avo_hz": r_avo,
            "kc_active_frac": kc_active_frac,
            "brain_bg_hz": bg_brain_hz,
            "rates": rates,
        }

    history = []
    pre_A = simulate_trial(odor_A, shock_us=False, plastic_on=False)
    pre_B = simulate_trial(odor_B, shock_us=False, plastic_on=False)
    rates_before = pre_A["rates"]
    history.append({
        "режим": cond_name,
        "этап": "до_обучения",
        "проба": 0,
        "избегание_CS_plus": round(pre_A["avoid_index"], 4),
        "избегание_CS_minus": round(pre_B["avoid_index"], 4),
        "индекс_различения": round(pre_A["avoid_index"] - pre_B["avoid_index"], 4),
        "доля_активных_KC": round(pre_A["kc_active_frac"], 4),
        "фон_мозга_Гц": round(pre_A["brain_bg_hz"], 3),
    })

    for tr in range(1, args.n_trials + 1):
        _ = simulate_trial(odor_A, shock_us=True, plastic_on=True)
        _ = simulate_trial(odor_B, shock_us=False, plastic_on=True)
        probe_A = simulate_trial(odor_A, shock_us=False, plastic_on=False)
        probe_B = simulate_trial(odor_B, shock_us=False, plastic_on=False)
        history.append({
            "режим": cond_name,
            "этап": "обучение",
            "проба": tr,
            "избегание_CS_plus": round(probe_A["avoid_index"], 4),
            "избегание_CS_minus": round(probe_B["avoid_index"], 4),
            "индекс_различения": round(probe_A["avoid_index"] - probe_B["avoid_index"], 4),
            "доля_активных_KC": round(probe_A["kc_active_frac"], 4),
            "фон_мозга_Гц": round(probe_A["brain_bg_hz"], 3),
        })

    post_A = history[-1]["избегание_CS_plus"]
    post_B = history[-1]["избегание_CS_minus"]
    gen_C = simulate_trial(odor_C, shock_us=False, plastic_on=False)
    rates_after = simulate_trial(odor_A, shock_us=False, plastic_on=False)["rates"]

    for ex in range(1, args.n_ext + 1):
        _ = simulate_trial(odor_A, shock_us=False, plastic_on=True, ext_mode=True)
        pA = simulate_trial(odor_A, shock_us=False, plastic_on=False)
        pB = simulate_trial(odor_B, shock_us=False, plastic_on=False)
        history.append({
            "режим": cond_name,
            "этап": "угасание",
            "проба": args.n_trials + ex,
            "избегание_CS_plus": round(pA["avoid_index"], 4),
            "избегание_CS_minus": round(pB["avoid_index"], 4),
            "индекс_различения": round(pA["avoid_index"] - pB["avoid_index"], 4),
            "доля_активных_KC": round(pA["kc_active_frac"], 4),
            "фон_мозга_Гц": round(pA["brain_bg_hz"], 3),
        })

    return history, {
        "режим": cond_name,
        "CS_plus_после_обучения": round(post_A, 4),
        "CS_minus_после_обучения": round(post_B, 4),
        "обобщение_запах_C": round(gen_C["avoid_index"], 4),
        "индекс_различения": round(post_A - post_B, 4),
        "доля_активных_KC": round(float(np.mean([h["доля_активных_KC"] for h in history])), 4),
        "фон_до_Гц": round(float(rates_before.mean()), 3),
        "фон_после_Гц": round(float(rates_after.mean()), 3),
    }, rates_before, rates_after


all_hist = []
cond_summaries = []

h_intact, s_intact, r_bef, r_aft = run_condition("intact_connectome", edges, silence_apl=False)
all_hist.extend(h_intact)
cond_summaries.append(s_intact)
print(f"  интактный коннектом : различение CS+/CS- = {s_intact['индекс_различения']:+.3f}, активных KC = {s_intact['доля_активных_KC']*100:.1f}%")

h_noapl, s_noapl, _, _ = run_condition("apl_silenced", edges, silence_apl=True)
all_hist.extend(h_noapl)
cond_summaries.append(s_noapl)
print(f"  без торможения APL  : различение CS+/CS- = {s_noapl['индекс_различения']:+.3f}, активных KC = {s_noapl['доля_активных_KC']*100:.1f}%")

if not args.no_shuffled:
    shuf_edges = flylib.degree_preserving_shuffle(edges, np.random.default_rng(args.seed + 77))
    h_shuf, s_shuf, _, _ = run_condition("shuffled_connectome", shuf_edges, silence_apl=False)
    all_hist.extend(h_shuf)
    cond_summaries.append(s_shuf)
    print(f"  перемешанный граф   : различение CS+/CS- = {s_shuf['индекс_различения']:+.3f}, активных KC = {s_shuf['доля_активных_KC']*100:.1f}%")

df_hist = pd.DataFrame(all_hist)
df_cmp = pd.DataFrame(cond_summaries)
df_hist.to_csv(RUN / "whole_brain_learning.csv", index=False)
df_cmp.to_csv(RUN / "whole_brain_vs_shuffled.csv", index=False)

# График 2x2
plt, _, _ = flylib.setup_plot_style()
fig, axes = plt.subplots(2, 2, figsize=(12.2, 8.0), dpi=140)

# [A] Кривая дифференциального обучения и угасания в интактном мозге
sub_i = df_hist[df_hist["режим"] == "intact_connectome"]
axes[0, 0].plot(sub_i["проба"], sub_i["избегание_CS_plus"], marker="o", ms=4, lw=1.7, color=flylib.PALETTE["brick"], label="CS+ (запах A + PPL1)")
axes[0, 0].plot(sub_i["проба"], sub_i["избегание_CS_minus"], marker="s", ms=4, lw=1.5, color=flylib.PALETTE["steel"], label="CS- (запах B нейтральный)")
axes[0, 0].axvline(args.n_trials, color="#9a938a", lw=0.7, ls=":")
axes[0, 0].text(args.n_trials + 0.15, 0.95, "угасание", transform=axes[0, 0].get_xaxis_transform(), fontsize=7.5, va="top", color="#6b655e")
axes[0, 0].axhline(0, color="#3c3833", lw=0.6)
axes[0, 0].set_xlabel("номер пробы")
axes[0, 0].set_ylabel("спайковый индекс избегания MBON")
axes[0, 0].set_title("A. Дифференциальное обучение внутри целого мозга")
axes[0, 0].legend(frameon=False, fontsize=8)

# [B] Сравнение коннектома, выключения APL и перемешанного графа
xc = np.arange(len(df_cmp))
axes[0, 1].bar(xc - 0.18, df_cmp["CS_plus_после_обучения"], width=0.24, color=flylib.PALETTE["brick"], label="CS+ (запах A)")
axes[0, 1].bar(xc + 0.06, df_cmp["CS_minus_после_обучения"], width=0.24, color=flylib.PALETTE["steel"], label="CS- (запах B)")
axes[0, 1].bar(xc + 0.30, df_cmp["индекс_различения"], width=0.22, color=flylib.PALETTE["olive"], label="различение (A - B)")
axes[0, 1].axhline(0, color="#3c3833", lw=0.6)
axes[0, 1].set_xticks(xc, [r.replace("_", "\n") for r in df_cmp["режим"]], fontsize=8)
axes[0, 1].set_ylabel("индекс ответа")
axes[0, 1].set_title("B. Специфичность памяти: коннектом против контролей")
axes[0, 1].legend(frameon=False, fontsize=7.5)

# [C] Разреженность кода KC по пробам (роль APL)
for ci, rname in enumerate(df_cmp["режим"]):
    sub_r = df_hist[df_hist["режим"] == rname]
    axes[1, 0].plot(sub_r["проба"], sub_r["доля_активных_KC"] * 100.0, marker="o", ms=3.5, lw=1.5, color=flylib.SERIES_COLORS[ci], label=rname)
axes[1, 0].set_xlabel("номер пробы")
axes[1, 0].set_ylabel("активные клетки Кеньона, %")
axes[1, 0].set_title("C. Разреженность кода KC в полном мозге")
axes[1, 0].legend(frameon=False, fontsize=8)

# [D] Устойчивость сети мозга: распределение частот до и после пластичности
bins = np.linspace(0, max(20.0, float(np.percentile(np.concatenate([r_bef, r_aft]), 98))), 26)
axes[1, 1].hist(r_bef, bins=bins, alpha=0.65, color=flylib.PALETTE["stone"], edgecolor="#6b655e", label="до обучения")
axes[1, 1].hist(r_aft, bins=bins, histtype="step", lw=1.7, color=flylib.PALETTE["brick"], label="после обучения")
axes[1, 1].set_xlabel("частота нейрона сети, Гц")
axes[1, 1].set_ylabel("число нейронов")
axes[1, 1].set_title("D. Стабильность активности целого мозга (нет перевозбуждения)")
axes[1, 1].legend(frameon=False, fontsize=8)

fig.suptitle(
    f"Обучение в MB внутри целого мозга ({source}): N={N}, различение={s_intact['индекс_различения']:+.3f}",
    fontsize=10.5,
    x=0.012,
    ha="left",
)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(RUN / "whole_brain_mb.png")
plt.close(fig)

summary = {
    "задача": "i-mb-learning",
    "источник": source,
    "нейронов": int(N),
    "KC": int(kc_idx.size),
    "MBON": int(mbon_idx.size),
    "сравнение_режимов": cond_summaries,
    "файлы": ["whole_brain_learning.csv", "whole_brain_vs_shuffled.csv", "whole_brain_mb.png"],
    "время_счета_с": round(time.time() - t0, 2),
}
flylib.save_json(RUN / "summary.json", summary)
print(f"готово за {summary['время_счета_с']} с -> {RUN}")
