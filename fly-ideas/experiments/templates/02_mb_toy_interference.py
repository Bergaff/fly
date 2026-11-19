"""Игрушечная модель грибовидных тел: обучить → переучить → забить память → вспомнить первое.

Без коннектома, на numpy. Это прототип протокола для идеи «интерференция и восстановление».
Аргументы: --sparsity 0.05 --n-junk 50 --relearn extinction|reversal|competitor --seed 0

Модель (упрощённая, но по мотивам Aso 2014 / Hige 2015):
  запах → PN (200) → KC (2000, разреженный код, винер-тейк-олл как APL)
  KC → MBON_avoid и KC → MBON_approach; дофамин делает пресинаптическую депрессию
  KC→MBON в компартменте: «удар» ослабляет KC→approach (муха начинает избегать),
  «награда» ослабляет KC→avoid. Поведение = MBON_approach − MBON_avoid.
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np

RUN = Path(os.environ.get("FLY_RUN_DIR", "."))

ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--sparsity", type=float, default=0.05, help="доля активных KC (сила APL)")
ap.add_argument("--n-junk", type=int, default=50, help="сколько случайных ассоциаций «набить»")
ap.add_argument("--relearn", choices=["extinction", "reversal", "competitor", "none"], default="extinction")
ap.add_argument("--lr", type=float, default=0.15)
ap.add_argument("--decay", type=float, default=0.002, help="пассивное восстановление весов к базе за «единицу времени»")
ap.add_argument("--wait", type=int, default=200, help="сколько «времени» ждать для спонтанного восстановления")
args = ap.parse_args()

rng = np.random.default_rng(args.seed)
N_PN, N_KC = 200, 2000
K_ACTIVE = max(1, int(N_KC * args.sparsity))

W_pn_kc = (rng.random((N_PN, N_KC)) < 0.035).astype(float)  # каждая KC слушает ~7 PN
W0 = 1.0
W_app = np.full(N_KC, W0)  # KC → MBON_approach
W_avo = np.full(N_KC, W0)  # KC → MBON_avoid


def odor(seed_):
    r = np.random.default_rng(seed_)
    return (r.random(N_PN) < 0.1).astype(float)


def kc_code(pn):
    drive = pn @ W_pn_kc + rng.normal(0, 0.05, N_KC)
    idx = np.argpartition(drive, -K_ACTIVE)[-K_ACTIVE:]
    code = np.zeros(N_KC)
    code[idx] = 1.0
    return code


def behavior(pn):
    """>0 — приближается, <0 — избегает."""
    k = kc_code(pn)
    return float((k @ W_app - k @ W_avo) / K_ACTIVE)


def train(pn, us, n=1):
    """us = 'shock' | 'reward' | None ; дофамин → депрессия активных KC-синапсов в нужном компартменте."""
    global W_app, W_avo
    for _ in range(n):
        k = kc_code(pn)
        if us == "shock":
            W_app -= args.lr * k * W_app
        elif us == "reward":
            W_avo -= args.lr * k * W_avo
        # без US (угасание): по Felsenberg 2018 это НЕ откат весов, а новая
        # противоположная память — ослабляем KC→avoid, как при слабой награде
        else:
            W_avo -= 0.5 * args.lr * k * W_avo


def wait(t):
    global W_app, W_avo
    for _ in range(t):
        W_app += args.decay * (W0 - W_app)
        W_avo += args.decay * (W0 - W_avo)


A, B = odor(1001), odor(1002)
log = {}
print(f"seed={args.seed} sparsity={args.sparsity} K_active={K_ACTIVE} relearn={args.relearn} n_junk={args.n_junk}")

log["naive_A"] = behavior(A)
print(f"[0] наивная муха, A: {log['naive_A']:+.3f}")

train(A, "shock", 3)
log["after_learn_A"] = behavior(A)
W1 = W_app.copy()
print(f"[1] обучили A+удар ×3, A: {log['after_learn_A']:+.3f}  (ждём < 0)")

if args.relearn == "extinction":
    train(A, None, 6)
elif args.relearn == "reversal":
    train(A, "reward", 3)
elif args.relearn == "competitor":
    train(B, "shock", 3)
log["after_relearn_A"] = behavior(A)
print(f"[2] переучили ({args.relearn}), A: {log['after_relearn_A']:+.3f}")

for j in range(args.n_junk):
    train(odor(5000 + j), rng.choice(["shock", "reward"]), 1)
log["after_junk_A"] = behavior(A)
print(f"[3] набили {args.n_junk} случайных ассоциаций, A: {log['after_junk_A']:+.3f}")

# --- попытки вспомнить первое ---
snap_app, snap_avo = W_app.copy(), W_avo.copy()

wait(args.wait)
log["spontaneous_recovery_A"] = behavior(A)
print(f"[4a] спонтанное восстановление (t={args.wait}), A: {log['spontaneous_recovery_A']:+.3f}")

W_app, W_avo = snap_app.copy(), snap_avo.copy()
# reinstatement: удар без запаха — в этой модели он ничего не делает без KC-активности; добавим слабый фон
k_bg = (rng.random(N_KC) < args.sparsity).astype(float)
W_app -= 0.3 * args.lr * k_bg * W_app
log["reinstatement_A"] = behavior(A)
print(f"[4b] reinstatement (удар без запаха), A: {log['reinstatement_A']:+.3f}")

W_app, W_avo = snap_app.copy(), snap_avo.copy()
CRIT = 0.75 * log["after_learn_A"]  # вернуть 75 % исходной силы избегания
trials = 0
while behavior(A) > CRIT and trials < 20:
    train(A, "shock", 1)
    trials += 1
log["savings_trials_to_criterion"] = trials
# сравнение с наивной
W_app_n, W_avo_n = np.full(N_KC, W0), np.full(N_KC, W0)
tmp = (W_app, W_avo)
W_app, W_avo = W_app_n, W_avo_n
t_naive = 0
while behavior(A) > CRIT and t_naive < 20:
    train(A, "shock", 1)
    t_naive += 1
W_app, W_avo = tmp
log["savings_trials_naive"] = t_naive
print(f"[4c] savings: до критерия {trials} трайлов vs наивная {t_naive}")

# --- на уровне синапсов: стёрт или замаскирован? ---
kA = kc_code(A).astype(bool)
trace_left = float(1 - np.mean(W1[kA]))  # сколько депрессии осталось от обучения
trace_now = float(1 - np.mean(snap_app[kA]))
mask = float(1 - np.mean(snap_avo[kA]))  # противоположный след на другом MBON
log["trace_W1"] = trace_left
log["trace_after_all"] = trace_now
log["opposing_trace"] = mask
if trace_now < 0.5 * trace_left:
    verdict = "стёрт (депрессия KC→approach откатилась)"
elif mask > 0.05:
    verdict = "замаскирован: первый след цел, поверх лежит противоположный (KC→avoid)"
else:
    verdict = "сохранён и виден в поведении"
log["verdict"] = verdict
print(f"\nСлед A в KC→approach: после обучения {trace_left:.2f}, сейчас {trace_now:.2f}; противоположный след {mask:.2f} → {verdict}")

(RUN / "summary.json").write_text(json.dumps({"args": vars(args), **log}, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nsummary.json → {RUN}")
