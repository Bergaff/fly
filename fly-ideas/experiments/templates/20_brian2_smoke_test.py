"""Проверка импорта Brian2 и короткого LIF-прогона на CPU.

Не проверяет коннектом, модель Shiu et al. или готовность к baseline.
Запускается из окна «Мозг»; отчёт записывается в FLY_RUN_DIR/summary.json.
"""
import argparse
import importlib
import json
import os
import sys
import traceback
from pathlib import Path


def check_brian2():
    try:
        brian = importlib.import_module("brian2")
    except Exception as exc:
        return {"import_ok": False, "lif_ok": False,
                "error": f"Импорт Brian2: {type(exc).__name__}: {exc}"}

    result = {"import_ok": True, "version": str(brian.__version__), "lif_ok": False}
    try:
        # NumPy-режим проверяет расчёт без C++ компилятора на Windows.
        brian.prefs.codegen.target = "numpy"
        brian.start_scope()
        neurons = brian.NeuronGroup(
            5,
            "dv/dt = (v_rest - v + resistance * current) / tau : volt (unless refractory)",
            threshold="v > -50*mV",
            reset="v = -65*mV",
            refractory=2 * brian.ms,
            method="euler",
            namespace={"v_rest": -65 * brian.mV, "resistance": 1 * brian.Gohm,
                       "current": 20 * brian.pA, "tau": 20 * brian.ms},
        )
        neurons.v = -65 * brian.mV
        spikes = brian.SpikeMonitor(neurons)
        network = brian.Network(neurons, spikes)
        network.run(50 * brian.ms)
        count = int(spikes.num_spikes)
        result.update({"lif_ok": count > 0, "n_neurons": 5, "duration_ms": 50,
                       "n_spikes": count, "backend": "numpy"})
        if count == 0:
            result["error"] = "Прогон завершился без ожидаемых спайков."
    except Exception as exc:
        result["error"] = f"LIF-прогон: {type(exc).__name__}: {exc}"
        result["traceback"] = traceback.format_exc()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0, help="для совместимости; в тесте не используется")
    args = parser.parse_args()
    result = check_brian2()
    report = {
        "python": sys.version.split()[0], "python_executable": sys.executable,
        "args": vars(args), "brian2": result,
        "scope": "Проверка Brian2 на короткой тестовой LIF-модели, не baseline и не проверка коннектома.",
    }
    run_dir = Path(os.environ.get("FLY_RUN_DIR", "."))
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "summary.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\nПолный отчёт: {out}")
    print(report["scope"])
    return 0 if result["import_ok"] and result["lif_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
