"""Активация нейронов в полной LIF-модели (Shiu et al.) — каркас для первой репродукции.

Требует: brian2, скачанные данные и paper_model.py (кнопка «Скачать» во вкладке «Мозг»).
Аргументы: --ids 720575940624963786,720575940630233916 --rate 100 --t 1.0
По умолчанию берёт первые 5 нейронов из Completeness — просто чтобы проверить, что модель крутится.
"""
import argparse
import json
import os
import sys
from pathlib import Path

DATA = Path(os.environ.get("FLY_DATA", "workspace/data"))
RUN = Path(os.environ.get("FLY_RUN_DIR", "."))
SCRIPTS = Path(os.environ.get("FLY_SCRIPTS", "."))

ap = argparse.ArgumentParser()
ap.add_argument("--ids", type=str, default="", help="root_id нейронов через запятую")
ap.add_argument("--rate", type=float, default=100.0, help="Гц стимуляции")
ap.add_argument("--t", type=float, default=1.0, help="секунд биовремени")
args = ap.parse_args()

try:
    import pandas as pd
    import brian2  # noqa
except ImportError as e:
    sys.exit(f"Нет пакета: {e}. Для этого скрипта нужен brian2: pip install brian2 pandas pyarrow")

model_p = SCRIPTS / "paper_model.py"
if not model_p.exists():
    sys.exit("paper_model.py не найден — скачай «model.py — LIF-модель на Brian2» во вкладке «Мозг».")

comp = pd.read_csv(DATA / "2025_Completeness_783.csv")
id_col = next((c for c in comp.columns if "root" in c.lower() or c.lower().endswith("id")), comp.columns[0])
ids = [int(x) for x in args.ids.split(",") if x.strip()] or comp[id_col].head(5).astype(int).tolist()
print(f"Стимулирую {len(ids)} нейронов по {args.rate} Гц, {args.t} с: {ids[:5]}{'…' if len(ids) > 5 else ''}")

print("""
Дальше — ручной шаг (модель из статьи использует свои пути к данным):
  1. Открой paper_model.py и найди, откуда он читает Completeness/Connectivity.
  2. Подставь пути из папки workspace/data (переменная FLY_DATA).
  3. Вызови run_exp(exp_name='test', neu_exc=ids, ...) как в example.ipynb репозитория.
Этот каркас специально не делает это за тебя: API модели меняется между версиями,
и лучше один раз прочитать 100 строк model.py, чем гадать. Спроси Помощника —
он видит этот скрипт и может подсказать конкретные строки.
""")

(RUN / "summary.json").write_text(json.dumps({"ids": ids, "rate": args.rate, "t": args.t, "status": "scaffold"}, indent=2), encoding="utf-8")
