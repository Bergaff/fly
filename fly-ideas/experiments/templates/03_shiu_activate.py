"""Активация нейронов в полной LIF-модели (Shiu et al.) — первый запуск целого мозга.

Требует: brian2, joblib, pandas, pyarrow; скачанные данные и paper_model.py (кнопка «Скачать» во вкладке «Мозг»).
Аргументы: --ids 720575940624963786,720575940630233916  --n-run 2  --t 0.5  --n-proc 2
По умолчанию берёт первые 3 нейрона из Completeness — просто чтобы проверить, что мозг крутится.
Одна попытка (trial) 1 с биовремени на CPU занимает минуты и ~4–8 ГБ RAM; начинай с --t 0.3 --n-run 1.
Результат: spikes.parquet (все спайки), rates_top.csv (самые активные нейроны), summary.json.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

DATA = Path(os.environ.get("FLY_DATA", "workspace/data"))
RUN = Path(os.environ.get("FLY_RUN_DIR", "."))
SCRIPTS = Path(os.environ.get("FLY_SCRIPTS", str(Path(__file__).resolve().parent)))

ap = argparse.ArgumentParser()
ap.add_argument("--ids", type=str, default="", help="flywire root_id через запятую (без пробелов)")
ap.add_argument("--silence", type=str, default="", help="root_id нейронов, которые заглушить")
ap.add_argument("--rate", type=float, default=150.0, help="Гц пуассоновской стимуляции")
ap.add_argument("--t", type=float, default=0.5, help="секунд биовремени на одну попытку")
ap.add_argument("--n-run", type=int, default=1, help="число попыток (trials)")
ap.add_argument("--n-proc", type=int, default=1, help="параллельных процессов (каждый ест RAM!)")
args = ap.parse_args()

for m in ("pandas", "brian2", "joblib"):
    try:
        __import__(m)
    except ImportError:
        sys.exit(f"Нет пакета {m}. pip install brian2 joblib pandas pyarrow")

import pandas as pd  # noqa: E402

model_p = SCRIPTS / "paper_model.py"
if not model_p.exists():
    sys.exit("paper_model.py не найден — скачай «model.py — LIF-модель на Brian2» во вкладке «Мозг».")
comp_p, con_p = DATA / "2025_Completeness_783.csv", DATA / "2025_Connectivity_783.parquet"
for p in (comp_p, con_p):
    if not p.exists() or p.stat().st_size < 1000:
        sys.exit(f"Нет данных: {p}. Скачай во вкладке «Мозг».")

sys.path.insert(0, str(SCRIPTS))
import paper_model as pm  # noqa: E402
from brian2 import ms, Hz  # noqa: E402

comp = pd.read_csv(comp_p, index_col=0)
all_ids = comp.index.astype(int)
ids = [int(x) for x in args.ids.split(",") if x.strip()] or all_ids[:3].tolist()
slnc = [int(x) for x in args.silence.split(",") if x.strip()]
bad = [i for i in ids + slnc if i not in set(all_ids)]
if bad:
    sys.exit(f"Этих root_id нет в Completeness v783: {bad[:5]}")

params = dict(pm.default_params)
params["t_run"] = args.t * 1000 * ms
params["n_run"] = args.n_run
params["r_poi"] = args.rate * Hz

print(f"Нейронов в модели: {len(comp):,}")
print(f"Активирую {len(ids)} нейронов @ {args.rate} Гц, глушу {len(slnc)}; {args.n_run} × {args.t} с; n_proc={args.n_proc}")
t0 = time.time()
pm.run_exp(exp_name="run", neu_exc=ids, neu_slnc=slnc, path_res=RUN, path_comp=comp_p, path_con=con_p, params=params, n_proc=args.n_proc)
wall = time.time() - t0

df = pd.read_parquet(RUN / "run.parquet")
n_spk = len(df)
active = df["flywire_id"].nunique()
rates = (df.groupby("flywire_id").size() / (args.t * args.n_run)).sort_values(ascending=False)
top = rates.head(30).rename("rate_hz").reset_index()
# подпишем типами клеток, если есть колонка
type_col = next((c for c in comp.columns if "type" in c.lower() or "class" in c.lower()), None)
if type_col:
    top[type_col] = top["flywire_id"].map(comp[type_col])
top.to_csv(RUN / "rates_top.csv", index=False)
(RUN / "run.parquet").rename(RUN / "spikes.parquet")

print(f"\nГотово за {wall:.0f} с: {n_spk:,} спайков у {active:,} нейронов")
print("Самые активные (Гц):")
print(top.head(15).to_string(index=False))

(RUN / "summary.json").write_text(json.dumps({
    "args": vars(args), "wall_s": round(wall, 1), "n_spikes": int(n_spk), "n_active_neurons": int(active),
    "top": top.head(15).to_dict(orient="records"),
}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
