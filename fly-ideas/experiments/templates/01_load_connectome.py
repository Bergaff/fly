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
use_synth = "--synth" in sys.argv
if not use_synth:
    for p in (comp_p, conn_p):
        if not p.exists() or p.stat().st_size < 1000:
            sys.exit(f"Файл не найден или это заглушка LFS: {p}\nСкачай во вкладке «Мозг» (или запусти с флагом --synth).")

if use_synth:
    HERE = Path(__file__).resolve().parent
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import flylib
    comp, edges_s, _ = flylib.build_synthetic_connectome(seed=0)
    conn = pd.DataFrame({
        "Presynaptic_Index": edges_s["pre_idx"].to_numpy(),
        "Postsynaptic_Index": edges_s["post_idx"].to_numpy(),
        "Connectivity": edges_s["syn_count"].to_numpy(),
        "Excitatory x Connectivity": edges_s["signed_weight"].to_numpy(),
    })
    print(f"Синтетический обзор коннектома: {len(comp):,} нейронов, {len(conn):,} рёбер")
else:
    print("Читаю нейроны...")
    comp = pd.read_csv(comp_p, index_col=0).reset_index()
    comp = comp.rename(columns={comp.columns[0]: "root_id"})
    for ann_name in ("Supplemental_file1_neuron_annotations.tsv", "flywire_annotations.tsv"):
        ann_p = DATA / ann_name
        if ann_p.exists() and ann_p.stat().st_size > 1000:
            print(f"Присоединяю аннотации типов клеток: {ann_name}")
            ann = pd.read_csv(ann_p, sep="\t", low_memory=False)
            if "root_id" in ann.columns:
                keep_cols = [c for c in ("root_id", "cell_type", "cell_class", "super_class", "hemibrain_type", "top_nt", "side", "dimorphism") if c in ann.columns]
                comp = comp.merge(ann[keep_cols].drop_duplicates("root_id"), on="root_id", how="left")
            break
    print(f"  {len(comp):,} нейронов, колонки: {list(comp.columns)[:12]}")

    print("Читаю связность...")
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

pre = find(conn.columns, "presynaptic_index", "pre_root_id", "pre", "pre_pt_root_id", "source")
post = find(conn.columns, "postsynaptic_index", "post_root_id", "post", "post_pt_root_id", "target")
w = find(conn.columns, "connectivity", "syn_count", "weight", "count", "n_syn")
signed_col = find(conn.columns, "excitatory x connectivity")
nt = find(conn.columns, "nt_type", "neurotransmitter", "nt")
print(f"  pre={pre} post={post} weight={w} signed={signed_col}")

stats = {
    "neurons": int(len(comp)),
    "edges": int(len(conn)),
    "synapses_total": int(conn[w].abs().sum()) if w else None,
    "mean_out_degree": float(conn.groupby(pre).size().mean()) if pre else None,
    "inhibitory_edges_pct": round(float((conn[signed_col] < 0).mean() * 100), 2) if signed_col else None,
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
