#!/usr/bin/env python3
"""Series121: local Ollama versus exact project solver on one shared narrow graph-routing task."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import threading
import time
import traceback
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPORTS = HERE.parent / "reports"
PATHS = REPORTS / "biological-digital-pipeline-116b-61x8.csv"
PATHS_SHA = "4186bb6fdbe0a0e81f8626469027976ade1d416ff0549af94b85fb1b07aa3ca1"
OUTPUT_ROOT = Path("workspace/runs/ideas/i-observational/local-ollama-benchmark-121")
OLLAMA = "http://127.0.0.1:11434"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request_json(path: str, payload: dict | None = None, timeout: float = 180) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf8")
    request = urllib.request.Request(OLLAMA + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf8"))


def list_models() -> list[dict]:
    return request_json("/api/tags", timeout=8).get("models", [])


def read_paths():
    if sha(PATHS) != PATHS_SHA:
        raise ValueError("Exact61×8 paths artifact changed.")
    with PATHS.open(encoding="utf8") as handle:
        rows = list(csv.reader(handle))
    return rows[0][1:], [row[0] for row in rows[1:]], np.asarray([[float(v) for v in row[1:]] for row in rows[1:]], float)


def make_cases(case_count: int) -> list[dict]:
    channels, types, values = read_paths()
    normalized = values / np.maximum(values.sum(axis=1, keepdims=True), 1e-15)
    rng = np.random.default_rng(121_000_001)
    cases = []
    attempts = 0
    while len(cases) < case_count and attempts < case_count * 100:
        attempts += 1
        selected = rng.choice(len(types), 4, replace=False)
        weights = rng.uniform(0.15, 1.0, len(channels))
        scores = normalized[selected] @ weights
        order = np.argsort(scores)[::-1]
        if scores[order[0]] - scores[order[1]] < 0.015:
            continue
        answer = types[int(selected[order[0]])]
        candidates = [{"type": types[int(index)], "dn_vector": [round(float(v), 6) for v in normalized[index]]} for index in selected]
        cases.append({"id": len(cases) + 1, "channels": channels, "weights": [round(float(v), 6) for v in weights], "candidates": candidates, "answer": answer, "exact_scores": {types[int(index)]: float(score) for index, score in zip(selected, scores)}})
    if len(cases) != case_count:
        raise RuntimeError("Could not construct separated benchmark cases.")
    return cases


def exact_answer(case: dict) -> str:
    weights = np.asarray(case["weights"])
    return max(case["candidates"], key=lambda candidate: float(np.asarray(candidate["dn_vector"]) @ weights))["type"]


def prompt(case: dict) -> str:
    compact = {"weights": case["weights"], "candidates": case["candidates"]}
    return (
        "You are solving one narrow numeric graph-routing task. For every candidate compute the dot product "
        "of dn_vector and weights. Return the type with the largest value. Reply ONLY as JSON: "
        '{"answer":"exact type name"}. Do not explain. Data: ' + json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    )


def parse_answer(text: str) -> str:
    try:
        value = json.loads(text)
        if isinstance(value, dict) and isinstance(value.get("answer"), str):
            return value["answer"].strip()
    except json.JSONDecodeError:
        pass
    match = re.search(r'"answer"\s*:\s*"([^"]+)"', text)
    return match.group(1).strip() if match else ""


def model_metadata(model: str) -> dict:
    tags = {item.get("name"): item for item in list_models()}
    selected = tags.get(model, {})
    try:
        shown = request_json("/api/show", {"model": model}, timeout=30)
    except Exception:
        shown = {}
    info = shown.get("model_info", {})
    parameter_count = next((value for key, value in info.items() if key.endswith(".parameter_count") and isinstance(value, int)), None)
    return {"name": model, "digest": selected.get("digest"), "size_bytes": selected.get("size"), "parameter_count_if_reported": parameter_count, "family": shown.get("details", {}).get("family")}


def run(model: str, case_count: int, output_root: Path, progress=lambda *_: None, fixture: bool = False) -> Path:
    cases = make_cases(case_count)
    folder = output_root / ("ollama_narrow_benchmark_121_" + datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True, exist_ok=False)
    iterations = 2000
    start = time.perf_counter()
    project_answers = []
    for _ in range(iterations):
        project_answers = [exact_answer(case) for case in cases]
    project_seconds = time.perf_counter() - start
    ollama_rows = []
    for index, case in enumerate(cases):
        before = time.perf_counter()
        if fixture:
            raw = json.dumps({"answer": case["answer"] if index % 4 else "fixture_wrong"})
            response = {"response": raw, "eval_count": 1, "eval_duration": 1}
        else:
            response = request_json("/api/generate", {"model": model, "prompt": prompt(case), "stream": False, "format": "json", "options": {"temperature": 0, "seed": 121000001}}, timeout=600)
            raw = response.get("response", "")
        wall = time.perf_counter() - before
        answer = parse_answer(raw)
        ollama_rows.append({"case": case["id"], "expected": case["answer"], "answer": answer, "correct": answer == case["answer"], "wall_seconds": wall, "eval_count": response.get("eval_count"), "eval_duration_ns": response.get("eval_duration"), "raw_response": raw})
        progress(index + 1, len(cases))
    project_correct = sum(answer == case["answer"] for answer, case in zip(project_answers, cases))
    ollama_correct = sum(row["correct"] for row in ollama_rows)
    metadata = {"name": model, "fixture": True} if fixture else model_metadata(model)
    result = {
        "schema": "local-ollama-narrow-benchmark-121-v1", "status": "fixture_completed" if fixture else "completed",
        "benchmark_contract": {"task": "choose the largest weighted61-to-8 DN routing score among four candidates", "shared_cases": True, "case_count": len(cases), "seed": 121000001, "paths_sha256": PATHS_SHA, "not_general_intelligence_benchmark": True, "project_has_exact_task_specific_solver": True, "ollama_uses_prompted_general_model": True},
        "project": {"dense_scalar_capacity": 4214, "correct": project_correct, "accuracy": project_correct / len(cases), "timed_solver_iterations": iterations, "total_solver_seconds": project_seconds, "mean_seconds_per_case": project_seconds / (iterations * len(cases))},
        "ollama": {"model": metadata, "correct": ollama_correct, "accuracy": ollama_correct / len(cases), "total_wall_seconds": sum(row["wall_seconds"] for row in ollama_rows), "mean_wall_seconds_per_case": float(np.mean([row["wall_seconds"] for row in ollama_rows])), "rows": ollama_rows},
        "comparison": {"project_accuracy_minus_ollama": project_correct / len(cases) - ollama_correct / len(cases), "speed_ratio_ollama_wall_to_project_exact": float(np.mean([row["wall_seconds"] for row in ollama_rows])) / max(project_seconds / (iterations * len(cases)), 1e-15), "valid_scope": "only this narrow numeric routing benchmark", "general_ai_superiority_claim": False, "biological_claim": False},
    }
    (folder / "cases.json").write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    (folder / "summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    (folder / "ИТОГ.txt").write_text(
        "SERIES121 — PROJECT VS LOCAL OLLAMA\n\n"
        f"Model: {model}\nCases: {len(cases)}\nProject: {project_correct}/{len(cases)}\nOllama: {ollama_correct}/{len(cases)}\n"
        f"Project mean: {result['project']['mean_seconds_per_case']:.9f}s/case\nOllama mean wall: {result['ollama']['mean_wall_seconds_per_case']:.3f}s/case\n\n"
        "This compares one narrow numeric graph-routing task, not general intelligence.\n",
        encoding="utf-8-sig")
    return folder


def gui() -> None:
    import tkinter as tk
    from tkinter import messagebox, ttk
    root = tk.Tk(); root.title("Series121: проект против локальной Ollama"); root.geometry("760x410+90+60"); root.attributes("-topmost", True)
    model = tk.StringVar(); cases = tk.IntVar(value=18); status = tk.StringVar(value="Проверяю локальную Ollama…"); progress_value = tk.DoubleVar(value=0)
    tk.Label(root, text="Локальное сравнение проекта с Ollama", font=("Arial", 15, "bold"), pady=15).pack()
    tk.Label(root, text="Одинаковые задачи: выбрать максимальный взвешенный DN-маршрут.\nЭто узкий benchmark вычислений, не тест общего интеллекта.", justify="center").pack()
    form = tk.Frame(root); form.pack(pady=14)
    tk.Label(form, text="Модель Ollama:").grid(row=0, column=0, sticky="e", padx=6, pady=6)
    combo = ttk.Combobox(form, textvariable=model, width=38, state="readonly"); combo.grid(row=0, column=1, padx=6, pady=6)
    tk.Label(form, text="Количество задач:").grid(row=1, column=0, sticky="e", padx=6, pady=6)
    tk.Spinbox(form, from_=6, to=60, increment=6, textvariable=cases, width=8).grid(row=1, column=1, sticky="w", padx=6, pady=6)
    tk.Label(root, textvariable=status).pack(pady=5)
    ttk.Progressbar(root, variable=progress_value, maximum=100, length=580).pack(pady=5)
    start_button = tk.Button(root, text="Запустить сравнение", state="disabled", padx=20, pady=9); start_button.pack(pady=12)

    def detect():
        try:
            names = [item.get("name") for item in list_models() if item.get("name")]
            if not names: raise RuntimeError("Ollama работает, но локальные модели не найдены.")
            def ready(): combo["values"] = names; model.set(names[0]); status.set(f"Найдено моделей: {len(names)}"); start_button.config(state="normal")
            root.after(0, ready)
        except Exception as error:
            root.after(0, lambda: (status.set("Ollama недоступна"), messagebox.showerror("Series121", f"Не удалось подключиться к {OLLAMA}.\nЗапустите Ollama и повторите.\n\n{error}", parent=root)))

    def start():
        if not model.get(): return
        start_button.config(state="disabled"); selected, count = model.get(), int(cases.get())
        def work():
            try:
                output = run(selected, count, OUTPUT_ROOT, lambda done, total: root.after(0, lambda: (progress_value.set(done / total * 100), status.set(f"Ollama: {done}/{total}"))))
                def completed():
                    status.set("Готово"); start_button.config(state="normal")
                    if os.name == "nt": os.startfile(str(output.resolve()))
                    messagebox.showinfo("Series121", f"Сравнение завершено.\n{output.resolve()}", parent=root)
                root.after(0, completed)
            except Exception as error:
                path = OUTPUT_ROOT / "ПОСЛЕДНЯЯ-ОШИБКА-121.txt"; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(type(error).__name__ + ": " + str(error) + "\n\n" + traceback.format_exc(), encoding="utf-8-sig")
                root.after(0, lambda: (start_button.config(state="normal"), messagebox.showerror("Series121", f"{error}\n\n{path.resolve()}", parent=root)))
        threading.Thread(target=work, daemon=True).start()
    start_button.config(command=start)
    threading.Thread(target=detect, daemon=True).start(); root.mainloop()


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--gui", action="store_true"); parser.add_argument("--model"); parser.add_argument("--cases", type=int, default=18); parser.add_argument("--fixture", action="store_true"); parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT); args = parser.parse_args()
    if args.gui: gui()
    else:
        if not args.model and not args.fixture: raise SystemExit("--model is required without --gui")
        print(run(args.model or "fixture-model", args.cases, args.output_root, fixture=args.fixture))


if __name__ == "__main__": main()
