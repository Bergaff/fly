"""Проверяет небольшую выборку вручную подключённых таблиц.

Читает FLY_CONNECTOME и дополнительные выбранные аннотации. Поддерживает CSV/TSV,
CSV.GZ/TSV.GZ и Parquet. Проверка не преобразует и не изменяет входные файлы,
не подтверждает версию коннектома и не является воспроизведением baseline.
"""
import argparse
import csv
import gzip
import json
import os
import re
import sys
from pathlib import Path

SAMPLE_SIZE = 20


def read_sample(file):
    name = file.name.lower()
    if name.endswith(".parquet"):
        import pyarrow.parquet as parquet
        reader = parquet.ParquetFile(file)
        columns = reader.schema_arrow.names
        batch = next(reader.iter_batches(batch_size=SAMPLE_SIZE, use_threads=False), None)
        rows = batch.to_pylist() if batch is not None else []
        return columns, rows
    if not name.endswith((".csv", ".csv.gz", ".tsv", ".tsv.gz")):
        raise ValueError("Формат не поддерживается: нужен CSV, TSV, CSV.GZ, TSV.GZ или Parquet")
    opener = gzip.open if name.endswith(".gz") else open
    separator = "\t" if name.endswith((".tsv", ".tsv.gz")) else ","
    with opener(file, "rt", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=separator)
        columns = reader.fieldnames or []
        rows = []
        for row in reader:
            rows.append(row)
            if len(rows) >= SAMPLE_SIZE:
                break
    return columns, rows


def inspect(role, location):
    if not location:
        return {"ok": False if role == "connections" else None,
                "error": "Файл не выбран в разделе «Данные и окружение»."}
    file = Path(location)
    result = {"ok": False, "path": str(file)}
    try:
        if not file.is_file():
            raise FileNotFoundError("Файл недоступен. Проверьте путь и подключите его снова.")
        result["size_bytes"] = file.stat().st_size
        columns, rows = read_sample(file)
        result["columns"] = columns
        result["sample_rows"] = len(rows)
        lowered = {str(c).strip().lower(): c for c in columns}
        if not rows:
            raise ValueError("Таблица не содержит строк данных.")
        if role == "connections":
            pre = next((lowered[k] for k in ("pre_root_id", "pre_pt_root_id", "pre", "bodyid_pre") if k in lowered), None)
            post = next((lowered[k] for k in ("post_root_id", "post_pt_root_id", "post", "bodyid_post") if k in lowered), None)
            if not pre or not post:
                raise ValueError("Нужны колонки ID до и после синапса, например pre_root_id и post_root_id.")
            invalid = sum(not re.fullmatch(r"[1-9][0-9]*", str(row.get(col, "")).strip())
                          for row in rows for col in (pre, post))
            if invalid:
                raise ValueError(f"В выборке {invalid} некорректных ID нейронов; ID должны быть целыми положительными числами.")
            result["pre_column"] = pre
            result["post_column"] = post
            result["count_column"] = next((lowered[k] for k in ("syn_count", "n_synapses", "count", "weight") if k in lowered), None)
            result["example_ids"] = [{"pre": str(r[pre]), "post": str(r[post])} for r in rows[:3]]
            result["note"] = "Проверена только выборка, не все строки. Версия и совместимость с моделью не установлены."
        else:
            root = next((lowered[k] for k in ("root_id", "flywire_id", "body_id", "bodyid") if k in lowered), None)
            if not root:
                raise ValueError("Не найдена колонка идентификатора нейрона, например root_id.")
            invalid = sum(not re.fullmatch(r"[1-9][0-9]*", str(row.get(root, "")).strip()) for row in rows)
            if invalid:
                raise ValueError(f"В выборке {invalid} некорректных ID нейронов; ID должны быть целыми положительными числами.")
            result["id_column"] = root
            result["note"] = "Проверена только выборка; соответствие ID таблице связей не установлено."
        result["ok"] = True
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=0, help="для совместимости; не используется")
    args = parser.parse_args()
    connections = inspect("connections", os.environ.get("FLY_CONNECTOME", ""))
    annotations = inspect("annotations", os.environ.get("FLY_ANNOTATIONS", ""))
    cell_types = inspect("cell_types", os.environ.get("FLY_CELL_TYPES", ""))
    neurotransmitters = inspect("neurotransmitters", os.environ.get("FLY_NEUROTRANSMITTERS", ""))
    report = {
        "args": vars(args), "connections": connections, "annotations": annotations,
        "cell_types": cell_types, "neurotransmitters": neurotransmitters,
        "scope": "Проверка только первых строк. Это не проверка всей таблицы, версии данных или baseline Shiu.",
    }
    run_dir = Path(os.environ.get("FLY_RUN_DIR", "."))
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "summary.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nПолный отчёт: {out}")
    return 0 if connections["ok"] and all(item["ok"] is not False for item in (annotations, cell_types, neurotransmitters)) else 1


if __name__ == "__main__":
    sys.exit(main())
