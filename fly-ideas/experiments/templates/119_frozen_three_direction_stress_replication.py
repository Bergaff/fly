#!/usr/bin/env python3
"""Series119: frozen out-of-family stress replication of Series118 A/B/C."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sqlite3
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORTS = HERE.parent / "reports"
ROOT = Path("workspace/runs/ideas/i-observational/frozen-three-direction-stress-119")
BASE_RUNNER = HERE / "118_four_hour_adaptive_three_direction.py"
BASE_RUNNER_SHA = "d75169f8f67dafbda4f61cc901fdc8debc73088ca26456cdb8ec71217195fa82"
R118 = REPORTS / "adaptive-three-direction-118-user-result.json"
R118_SHA = "f1a5751b664e28f485f25cabb8949a266debb275aa8af8d9957b292108f0c5b1"
FROZEN_CONFIG = {"alpha": 0.125, "beta": 0.5, "ridge": 0.01, "subset": 20, "derivative": 0.0}
PROFILES = (
    {"name": "mild", "edge_dropout": 0.05, "edge_sigma": 0.12, "dn_dropout": 0, "case_sigma": 0.18},
    {"name": "medium", "edge_dropout": 0.10, "edge_sigma": 0.18, "dn_dropout": 1, "case_sigma": 0.22},
    {"name": "severe", "edge_dropout": 0.15, "edge_sigma": 0.24, "dn_dropout": 2, "case_sigma": 0.28},
)
REPS_PER_PROFILE = 8
PAUSE = threading.Event()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf8")


def load_base():
    if sha(BASE_RUNNER) != BASE_RUNNER_SHA:
        raise ValueError("Exact Series118 runner changed.")
    if sha(R118) != R118_SHA:
        raise ValueError("Exact genuine Series118 result changed.")
    result = json.loads(R118.read_text(encoding="utf8"))
    if result["selected_config"] != FROZEN_CONFIG or not result["primary"]["all_three_directions_passed"]:
        raise ValueError("Series118 frozen selection/result contract changed.")
    spec = importlib.util.spec_from_file_location("series118_frozen", BASE_RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    module.setup_data()
    return module


def stress_bundle(base, seed: int, reps_per_profile: int = REPS_PER_PROFILE) -> list[dict]:
    np = base.np
    raw, p0, priority = base.DATA["raw"], base.DATA["P"], base.DATA["priority"]
    out = []
    for profile_index, profile in enumerate(PROFILES):
        rng = np.random.default_rng(seed + profile_index * 1_000_003)
        rows = []
        for _ in range(reps_per_profile):
            keep = rng.random(raw.shape) >= profile["edge_dropout"]
            stressed_raw = np.where(raw > 0, raw * keep * rng.lognormal(0, profile["edge_sigma"], raw.shape), 0)
            w = base.normrows(np.log1p(stressed_raw))
            a_stability = base.corr(base.ranks(raw.sum(1)), base.ranks(stressed_raw.sum(1)))
            q = base.normrows(np.maximum((np.eye(61) + FROZEN_CONFIG["alpha"] * w + FROZEN_CONFIG["beta"] * (w @ w)) @ p0, 0))
            if profile["dn_dropout"]:
                dropped = rng.choice(q.shape[1], profile["dn_dropout"], replace=False)
                q[:, dropped] = 0
                q = base.normrows(q)
            u, _, _ = np.linalg.svd(q, full_matrices=False)
            proto = base.normrows(np.abs(u[:, :3].T))
            proto = base.normrows(np.maximum(proto + proto @ w, 0))
            idx = np.array(priority[: FROZEN_CONFIG["subset"]])
            train, valid = [], []
            for action in range(3):
                for case in range(12):
                    z = np.maximum(proto[action] * (1 + rng.normal(0, profile["case_sigma"], 61)) + rng.uniform(0, 0.002, 61), 0)
                    z /= z.sum()
                    dn = z @ q
                    observe = z @ w + z
                    execute = dn @ q.T
                    execute = execute @ w + execute
                    (train if case < 8 else valid).append((observe[idx], execute[idx], action, z))
            obs_train = np.array([x[0] for x in train])
            exe_train = np.array([x[1] for x in train])
            obs_valid = np.array([x[0] for x in valid])
            exe_valid = np.array([x[1] for x in valid])
            labels = [x[2] for x in valid]
            model = base.fit(obs_train, exe_train, FROZEN_CONFIG["ridge"])
            margin, accuracy = base.evaluate(obs_valid, exe_valid, labels, model)

            paired_model = base.fit(np.roll(obs_train, 8, axis=0), exe_train, FROZEN_CONFIG["ridge"])
            pairing_margin, _ = base.evaluate(obs_valid, exe_valid, labels, paired_model)
            permutation = rng.permutation(61)
            shuffled_q = q[permutation]
            shuffled_train, shuffled_valid = [], []
            for _, _, _, z in train:
                dn = z @ shuffled_q
                e = dn @ shuffled_q.T
                shuffled_train.append((e @ w + e)[idx])
            for _, _, _, z in valid:
                dn = z @ shuffled_q
                e = dn @ shuffled_q.T
                shuffled_valid.append((e @ w + e)[idx])
            shuffled_model = base.fit(obs_train, np.array(shuffled_train), FROZEN_CONFIG["ridge"])
            structure_margin, shuffled_accuracy = base.evaluate(obs_valid, np.array(shuffled_valid), labels, shuffled_model)
            identity_margin, _ = base.evaluate(obs_valid, exe_valid[:, ::-1], labels, model)
            shuffled_labels = list(np.asarray(labels)[rng.permutation(len(labels))])
            label_margin, _ = base.evaluate(obs_valid, exe_valid, shuffled_labels, model)
            zero_margin, _ = base.evaluate(obs_valid, np.zeros_like(exe_valid), labels, model)
            strongest = max(pairing_margin, structure_margin, identity_margin, label_margin, zero_margin)
            rows.append((a_stability, accuracy, shuffled_accuracy, margin, margin - strongest, pairing_margin, structure_margin, identity_margin, label_margin, zero_margin))
        z = np.asarray(rows, float)
        out.append({
            "profile": profile["name"], "seed": seed, "replicates": reps_per_profile,
            "a_mean": float(z[:, 0].mean()), "a_min": float(z[:, 0].min()),
            "b_accuracy": float(z[:, 1].mean()), "b_shuffled_accuracy": float(z[:, 2].mean()),
            "c_margin": float(z[:, 3].mean()), "c_advantage": float(z[:, 4].mean()),
            "c_win_rate": float((z[:, 4] > 0).mean()), "pairing_margin": float(z[:, 5].mean()),
            "structure_margin": float(z[:, 6].mean()), "identity_margin": float(z[:, 7].mean()),
            "label_margin": float(z[:, 8].mean()), "zero_margin": float(z[:, 9].mean()),
        })
    return out


def schema(db: sqlite3.Connection) -> None:
    db.executescript("""
    CREATE TABLE IF NOT EXISTS trials(
      profile TEXT, seed INTEGER, replicates INTEGER, a_mean REAL, a_min REAL,
      b_accuracy REAL, b_shuffled_accuracy REAL, c_margin REAL, c_advantage REAL,
      c_win_rate REAL, pairing_margin REAL, structure_margin REAL, identity_margin REAL,
      label_margin REAL, zero_margin REAL, PRIMARY KEY(profile, seed));
    CREATE TABLE IF NOT EXISTS state(k TEXT PRIMARY KEY, v TEXT);
    """)
    db.commit()


def put_state(db: sqlite3.Connection, key: str, value: object) -> None:
    db.execute("INSERT OR REPLACE INTO state VALUES(?,?)", (key, json.dumps(value)))
    db.commit()


def get_state(db: sqlite3.Connection, key: str, default=None):
    row = db.execute("SELECT v FROM state WHERE k=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default


def aggregate(db: sqlite3.Connection, profile: str | None = None) -> dict:
    query = "SELECT replicates,a_mean,a_min,b_accuracy,b_shuffled_accuracy,c_margin,c_advantage,c_win_rate,pairing_margin,structure_margin,identity_margin,label_margin,zero_margin FROM trials"
    args = ()
    if profile:
        query += " WHERE profile=?"
        args = (profile,)
    rows = db.execute(query, args).fetchall()
    if not rows:
        raise ValueError("No frozen stress rows.")
    np = __import__("numpy")
    z = np.asarray(rows, float)
    weights = z[:, 0]
    mean = lambda column: float(np.average(z[:, column], weights=weights))
    return {
        "rows": len(rows), "replicates": int(weights.sum()),
        "a_stability_mean": mean(1), "a_stability_min": float(z[:, 2].min()),
        "b_accuracy": mean(3), "b_shuffled_accuracy": mean(4),
        "c_margin": mean(5), "c_advantage": mean(6), "c_win_rate": mean(7),
        "controls": {"pairing_margin": mean(8), "structure_margin": mean(9),
                     "identity_margin": mean(10), "label_margin": mean(11), "zero_margin": mean(12)},
    }


def execute(folder: Path, hours: float, workers: int, fixture: bool, progress):
    base = load_base()
    db = sqlite3.connect(folder / "study.sqlite3")
    schema(db)
    target_seconds = 5.0 if fixture else hours * 3600
    total = get_state(db, "total_bundles")
    if total is None:
        # Measure wall throughput under the same concurrent full-bundle load used by the run.
        # The original serial calibration overestimated six-worker throughput by3.59x.
        calibration_count = max(4, workers * 2)
        calibration_reps = 1 if fixture else REPS_PER_PROFILE
        calibration_seeds = [119000000 + i for i in range(calibration_count)]
        before = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as calibration_pool:
            list(calibration_pool.map(lambda seed: stress_bundle(base, seed, calibration_reps), calibration_seeds))
        calibration = max(time.perf_counter() - before, 0.001)
        observed_rate = calibration_count / calibration
        total = max(workers * 2, int(target_seconds * observed_rate))
        total = min(total, 8 if fixture else 200000)
        put_state(db, "calibration_seconds", calibration)
        put_state(db, "calibration_concurrent_bundles", calibration_count)
        put_state(db, "observed_bundles_per_second", observed_rate)
        put_state(db, "total_bundles", total)
    done = db.execute("SELECT COUNT(DISTINCT seed) FROM trials").fetchone()[0]
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while done < total and not PAUSE.is_set():
            count = min(workers * 2, total - done)
            seeds = [119900000 + done + i for i in range(count)]
            batches = list(pool.map(lambda seed: stress_bundle(base, seed, 1 if fixture else REPS_PER_PROFILE), seeds))
            for batch in batches:
                for row in batch:
                    db.execute("INSERT OR IGNORE INTO trials VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                        row["profile"], row["seed"], row["replicates"], row["a_mean"], row["a_min"],
                        row["b_accuracy"], row["b_shuffled_accuracy"], row["c_margin"], row["c_advantage"],
                        row["c_win_rate"], row["pairing_margin"], row["structure_margin"], row["identity_margin"],
                        row["label_margin"], row["zero_margin"]))
            db.commit()
            done += count
            progress("Frozen out-of-family A/B/C stress final", done / total, done, total)
    active = get_state(db, "active_seconds", 0.0) + time.monotonic() - started
    put_state(db, "active_seconds", active)
    if PAUSE.is_set():
        db.close()
        return None
    overall = aggregate(db)
    profiles = {p["name"]: aggregate(db, p["name"]) for p in PROFILES}
    severe = profiles["severe"]
    gate_a = overall["a_stability_mean"] >= 0.95 and overall["a_stability_min"] >= 0.85 and severe["a_stability_mean"] >= 0.95
    gate_b = (overall["b_accuracy"] >= 0.85 and overall["b_shuffled_accuracy"] <= 0.75
              and overall["b_accuracy"] - overall["b_shuffled_accuracy"] >= 0.10
              and severe["b_accuracy"] >= 0.65 and severe["b_accuracy"] - severe["b_shuffled_accuracy"] >= 0.05)
    gate_c = (overall["c_margin"] >= 0.20 and overall["c_advantage"] >= 0.10 and overall["c_win_rate"] >= 0.80
              and severe["c_margin"] >= 0.20 and severe["c_advantage"] >= 0.10 and severe["c_win_rate"] >= 0.70)
    result = {
        "schema": "frozen-three-direction-stress-119-v1", "status": "fixture_completed" if fixture else "completed",
        "protocol": {"target_hours": hours, "workers": workers, "adaptive_search": False, "post_result_tuning": False,
                     "source118_sha256": R118_SHA, "source118_runner_sha256": BASE_RUNNER_SHA,
                     "frozen_config": FROZEN_CONFIG, "profiles": PROFILES, "replicates_per_profile_per_bundle": 1 if fixture else REPS_PER_PROFILE,
                     "seed_namespace": "119900000+", "primary_gate": "overall A mean>=.95,min>=.85; B acc>=.85,shuffled<=.75,delta>=.10; C margin>=.20,advantage>=.10,win>=.80; severe A mean>=.95; B acc>=.65,delta>=.05; C margin>=.20,advantage>=.10,win>=.70"},
        "active_wall_seconds": active, "overall": overall, "profiles": profiles,
        "primary": {"all_three_frozen_stress_directions_passed": bool(gate_a and gate_b and gate_c),
                    "a_stress_robustness_passed": bool(gate_a), "b_stress_readout_passed": bool(gate_b),
                    "c_stress_specificity_passed": bool(gate_c), "biological_claim": False,
                    "scientific_biological_result": False},
    }
    save(folder / "summary.json", result)
    (folder / "ИТОГ.txt").write_text(
        "SERIES119 — FROZEN THREE-DIRECTION STRESS REPLICATION\n\n"
        f"A: {gate_a}\nB: {gate_b}\nC: {gate_c}\nAll three: {gate_a and gate_b and gate_c}\n"
        "Biological claim: NO.\n", encoding="utf-8-sig")
    put_state(db, "phase", "completed")
    db.close()
    progress("Готово", 1, total, total)
    return folder


def new_run(hours: float, workers: int, fixture: bool, output_root: Path, progress):
    output_root.mkdir(parents=True, exist_ok=True)
    folder = output_root / ("frozen_three_direction_stress_119_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8])
    folder.mkdir()
    save(folder / "protocol_start.json", {"created_utc": datetime.now(timezone.utc).isoformat(), "hours": hours, "workers": workers, "fixture": fixture})
    return execute(folder, hours, workers, fixture, progress)


def latest_incomplete(root: Path = ROOT):
    folders = sorted((p for p in root.glob("frozen_three_direction_stress_119_*") if (p / "study.sqlite3").exists()), key=lambda p: p.stat().st_mtime, reverse=True)
    for folder in folders:
        with sqlite3.connect(folder / "study.sqlite3") as db:
            try:
                if get_state(db, "phase") != "completed":
                    return folder
            except sqlite3.Error:
                pass
    return None


def gui() -> None:
    import tkinter as tk
    from tkinter import messagebox
    root = tk.Tk()
    root.title("Series119: frozen A/B/C stress replication")
    root.geometry("900x540+70+35")
    root.attributes("-topmost", True)
    workers = tk.IntVar(value=min(6, os.cpu_count() or 2))
    status, detail = tk.StringVar(value="Frozen: никакой адаптации или tuning"), tk.StringVar(value="")
    percent = tk.DoubleVar(value=0)
    running = {"value": False}
    clock = {"start": None}
    tk.Label(root, text="Series119 — frozen stress replication всех трёх направлений", font=("Arial", 14, "bold"), pady=14).pack()
    tk.Label(root, text="Новые edge/DN/case perturbations · один frozen config · отдельные seeds\nЭто цифровая stress-проверка, не биологический эксперимент.", justify="center").pack()
    worker_frame = tk.Frame(root); worker_frame.pack(pady=8)
    tk.Label(worker_frame, text="Workers:").pack(side="left")
    maximum = max(1, os.cpu_count() or 2)
    for value in (2, 4, 6, maximum):
        tk.Radiobutton(worker_frame, text="Max" if value == maximum else str(value), variable=workers, value=value).pack(side="left")
    for key, value in (("2", 2), ("4", 4), ("6", 6), ("m", maximum), ("M", maximum)):
        root.bind(key, lambda _event, selected=value: workers.set(selected))
    tk.Label(root, textvariable=status, pady=8).pack()
    tk.Scale(root, variable=percent, from_=0, to=100, orient="horizontal", length=720, state="disabled").pack()
    tk.Label(root, textvariable=detail).pack()
    buttons = tk.Frame(root); buttons.pack(pady=16)

    def update(text, fraction, done, total):
        elapsed = time.time() - clock["start"] if clock["start"] else 0
        remaining = elapsed * (1 - fraction) / fraction if fraction > 0.01 else 0
        finish = time.strftime("%H:%M", time.localtime(time.time() + remaining)) if remaining else "—"
        root.after(0, lambda: (status.set(text), percent.set(100 * fraction), detail.set(f"{100*fraction:.1f}% · {done}/{total} · осталось ~{remaining/60:.0f} мин · финиш ~{finish}")))

    def launch(continue_run: bool):
        if running["value"]:
            return
        PAUSE.clear(); running["value"] = True; clock["start"] = time.time()
        start_button.config(state="disabled"); continue_button.config(state="disabled")
        def work():
            try:
                folder = latest_incomplete() if continue_run else None
                result = execute(folder, 4, workers.get(), False, update) if folder else new_run(4, workers.get(), False, ROOT, update)
                def done():
                    running["value"] = False; start_button.config(state="normal"); continue_button.config(state="normal")
                    status.set("Пауза сохранена" if result is None else "Готово")
                    if result and os.name == "nt": os.startfile(str(result.resolve()))
                    if result: messagebox.showinfo("Series119", f"Расчёт завершён.\n{result.resolve()}", parent=root)
                root.after(0, done)
            except Exception as error:
                path = ROOT / "ПОСЛЕДНЯЯ-ОШИБКА-119.txt"; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(type(error).__name__ + ": " + str(error) + "\n\n" + traceback.format_exc(), encoding="utf-8-sig")
                root.after(0, lambda: (messagebox.showerror("Series119", f"{error}\n\n{path.resolve()}", parent=root), root.destroy()))
        threading.Thread(target=work, daemon=True).start()

    start_button = tk.Button(buttons, text="Начать новый ~4 ч", command=lambda: launch(False), padx=15, pady=8); start_button.pack(side="left", padx=5)
    continue_button = tk.Button(buttons, text="Продолжить", command=lambda: launch(True), padx=15, pady=8); continue_button.pack(side="left", padx=5)
    tk.Button(buttons, text="Пауза после batch", command=PAUSE.set, padx=15, pady=8).pack(side="left", padx=5)
    root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument("--hours", type=float, default=4)
    parser.add_argument("--workers", type=int, default=min(6, os.cpu_count() or 2))
    parser.add_argument("--output-root", type=Path, default=ROOT)
    args = parser.parse_args()
    if args.gui:
        gui()
    else:
        print(new_run(0.002 if args.fixture else args.hours, args.workers, args.fixture, args.output_root, lambda *_: None))


if __name__ == "__main__":
    main()
