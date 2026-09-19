"""Загрузка коннектома v783: считает базовую статистику и ищет нейроны грибовидных тел.

Нужны numpy, pandas, pyarrow и скачанные файлы Completeness/Connectivity.
Результат: summary.json + mb_neurons.csv в папке прогона.
"""
import json
import os
import sys
from pathlib import Path

DATA = Path(os.environ.get("FLY_DATA", "workspace/data"))
RUN = Path(os.environ.get("FLY_RUN_DIR", "."))

try:
    import numpy as np
    import pandas as pd
except ImportError as e:
    sys.exit(f"Нет пакета: {e}. pip install numpy pandas pyarrow")

comp_p = DATA / "2025_Completeness_783.csv"
conn_p = DATA / "2025_Connectivity_783.parquet"
for p in (comp_p, conn_p):
    if not p.exists() or p.stat().st_size < 1000:
        sys.exit(f"Файл не найден или это заглушка LFS: {p}\nСкачай во вкладке «Мозг».")

print("Читаю нейроны…")
comp = pd.read_csv(comp_p)
print(f"  {len(comp):,} нейронов, колонки: {list(comp.columns)[:12]}")

print("Читаю связность…")
conn = pd.read_parquet(conn_p)
print(f"  {len(conn):,} связей, колонки: {list(conn.columns)}")

# Универсальный поиск колонок: в разных выгрузках они называются по-разному
def find(cols, *cands):
    for c in cands:
        for col in cols:
            if col.lower() == c:
                return col
    for c in cands:
        for col in cols:
            if c in col.lower():
                return col
    return None

pre = find(conn.columns, "pre_root_id", "pre", "pre_pt_root_id", "source")
post = find(conn.columns, "post_root_id", "post", "post_pt_root_id", "target")
w = find(conn.columns, "syn_count", "weight", "count", "n_syn")
nt = find(conn.columns, "nt_type", "neurotransmitter", "nt")
print(f"  pre={pre} post={post} weight={w} nt={nt}")

stats = {
    "neurons": int(len(comp)),
    "edges": int(len(conn)),
    "synapses_total": int(conn[w].sum()) if w else None,
    "mean_out_degree": float(conn.groupby(pre).size().mean()) if pre else None,
}
if nt:
    stats["nt_distribution"] = {str(k): int(v) for k, v in conn[nt].value_counts().items()}
print(json.dumps(stats, ensure_ascii=False, indent=2))

# Грибовидные тела: ищем по любой текстовой колонке типов клеток
type_col = find(comp.columns, "cell_type", "type", "hemibrain_type", "cell_class", "super_class")
mb = None
if type_col:
    pat = r"^(KC|MBON|PAM|PPL1|APL|DPM)"
    mb = comp[comp[type_col].astype(str).str.match(pat, na=False)]
    print(f"\nГрибовидные тела (по колонке {type_col}): {len(mb):,} нейронов")
    print(mb[type_col].str.extract(r"^([A-Za-z0-9]+)")[0].value_counts().head(12).to_string())
    mb.to_csv(RUN / "mb_neurons.csv", index=False)
    stats["mb_neurons"] = int(len(mb))
else:
    print("\nКолонка с типами клеток не найдена — для MB понадобятся аннотации Schlegel 2024 (Supplementary Data).")

(RUN / "summary.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\nГотово. summary.json → {RUN}")
