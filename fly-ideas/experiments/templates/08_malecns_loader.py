#!/usr/bin/env python3
"""Загрузчик коннектома MaleCNS v1.0 (ЦНС самца, Janelia): связи и аннотации клеток.

Зачем: у FlyWire id и MaleCNS id это разные пространства, поэтому модель нельзя просто
переключить с одного коннектома на другой. Этот шаблон приводит MaleCNS к тому же виду,
что и таблицы fly-brain: связи pre, post, weight и подпись каждой клетки типом.

Что делает:
  1) спрашивает у бакета Janelia список файлов (публичный доступ, без ключей);
  2) находит таблицу связей и таблицу аннотаций, скачивает их в FLY_DATA;
  3) приводит связи к колонкам pre, post, weight (склеивает повторы суммой синапсов);
  4) сохраняет malecns_edgelist.parquet и malecns_neurons.parquet;
  5) пишет в лог, какие типы клеток нашлись, и готовый запрос к neuPrint на случай,
     если готовой таблицы связей в бакете не окажется.

Примеры:
  python 08_malecns_loader.py --check                  # только посмотреть, что лежит в бакете
  python 08_malecns_loader.py                          # скачать связи и аннотации
  python 08_malecns_loader.py --limit 500000 --min-syn 3   # обрезать по числу связей
  python 08_malecns_loader.py --synth                  # проверка формата без интернета

Результат: malecns_edgelist.parquet, malecns_neurons.parquet, summary.json.
Данные: FLY_DATA, результат: FLY_RUN_DIR.
"""
import argparse
import gzip
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DATA = Path(os.environ.get("FLY_DATA", "workspace/data"))
RUN = Path(os.environ.get("FLY_RUN_DIR", "."))

BUCKET = "flyem-male-cns"
API = f"https://storage.googleapis.com/storage/v1/b/{BUCKET}/o"
HTTP = f"https://storage.googleapis.com/{BUCKET}/"
PREFIXES = ["v1.0/connectome-data/", "v1.0/segmentation/"]
EDGE_HINT = re.compile(r"(edge|connect|adjacen|synap|partner)", re.I)
ANNOT_HINT = re.compile(r"(annotation|body-annotation)", re.I)
DATA_SUFFIX = (".csv", ".tsv", ".parquet", ".feather", ".csv.gz", ".tsv.gz")

ap = argparse.ArgumentParser(description="Загрузка связей и аннотаций MaleCNS v1.0")
ap.add_argument("--check", action="store_true", help="только показать найденные файлы")
ap.add_argument("--synth", action="store_true", help="синтетические данные вместо скачивания")
ap.add_argument("--prefix", action="append", default=[], help="дополнительный префикс в бакете")
ap.add_argument("--edge-file", default="", help="взять конкретный файл связей (имя объекта в бакете)")
ap.add_argument("--limit", type=int, default=0, help="оставить N сильнейших связей (0 = все)")
ap.add_argument("--min-syn", type=int, default=1, help="минимальное число синапсов на связь")
ap.add_argument("--keep-types", default="", help="оставить только эти типы клеток (шаблоны через запятую)")
ap.add_argument("--timeout", type=float, default=600.0)
args = ap.parse_args()


def list_objects(prefix, page_token=None, max_pages=12):
    """Публичный листинг бакета: имя, размер, время изменения."""
    items, pages = [], 0
    while pages < max_pages:
        query = {"prefix": prefix, "maxResults": 1000, "fields": "items(name,size,updated),nextPageToken"}
        if page_token:
            query["pageToken"] = page_token
        url = API + "?" + urllib.parse.urlencode(query)
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                payload = json.load(r)
        except urllib.error.URLError as e:
            print(f"  нет доступа к {prefix}: {e}")
            return items, False
        items.extend(payload.get("items", []))
        page_token = payload.get("nextPageToken")
        pages += 1
        if not page_token:
            break
    return items, True


def human(n):
    for unit, div in (("ГБ", 1 << 30), ("МБ", 1 << 20), ("КБ", 1 << 10)):
        if n >= div:
            return f"{n / div:.1f} {unit}"
    return f"{n} Б"


def download(object_name, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = HTTP + urllib.parse.quote(object_name)
    t0 = time.time()
    with urllib.request.urlopen(url, timeout=args.timeout) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if total and got % (64 << 20) < (1 << 20):
                print(f"    {human(got)} из {human(total)}")
    print(f"  скачано {dest.name}: {human(dest.stat().st_size)} за {time.time() - t0:.0f} с")
    return dest


def read_table(path: Path):
    import pandas as pd
    name = path.name.lower()
    if name.endswith(".parquet"):
        return pd.read_parquet(path)
    if name.endswith(".feather"):
        return pd.read_feather(path)
    if name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
            head = f.read(4096)
        sep = "\t" if name.endswith(".tsv.gz") or head.count("\t") > head.count(",") else ","
        return pd.read_csv(path, sep=sep, compression="gzip", low_memory=False)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        head = f.read(4096)
    sep = "\t" if head.count("\t") > head.count(",") else ","
    return pd.read_csv(path, sep=sep, low_memory=False)


def pick_column(df, *aliases):
    low = {c.lower().replace("_", "").replace(" ", ""): c for c in df.columns}
    for a in aliases:
        key = a.lower().replace("_", "")
        if key in low:
            return low[key]
    return None


def normalize_edges(df):
    """Приводит таблицу связей к колонкам pre, post, weight."""
    pre = pick_column(df, "pre", "prerootid", "preptrootid", "bodyidpre", "body_pre", "source", "from")
    post = pick_column(df, "post", "postrootid", "postptrootid", "bodyidpost", "body_post", "target", "to")
    w = pick_column(df, "weight", "syncount", "count", "nsynapses", "nsyn", "size")
    if not pre or not post:
        return None, f"нет колонок pre/post. Есть: {list(df.columns)[:14]}"
    out = df[[pre, post]].copy()
    out.columns = ["pre", "post"]
    out["weight"] = df[w].astype(float).to_numpy() if w else 1.0
    out = out[out.pre != out.post]
    out = out[out.weight >= args.min_syn]
    out = out.groupby(["pre", "post"], as_index=False)["weight"].sum()
    if args.limit and len(out) > args.limit:
        out = out.nlargest(args.limit, "weight")
    out["connectome"] = "malecns-v1.0"
    return out, ""


def synth():
    import numpy as np
    import pandas as pd
    rng = np.random.default_rng(0)
    n_pre, n_post = 4000, 1200
    m = 40000
    pre = rng.integers(100000, 100000 + n_pre, m)
    post = rng.integers(500000, 500000 + n_post, m)
    w = rng.integers(1, 12, m)
    edges = pd.DataFrame({"pre": pre, "post": post, "weight": w.astype(float), "connectome": "malecns-v1.0"})
    edges = edges.groupby(["pre", "post"], as_index=False)["weight"].sum()
    types = rng.choice(["KCg-m", "MBON01", "PPL1-01", "SMP", "OA-VUMa", "DNa01", "unknown"], size=n_post,
                       p=[0.2, 0.05, 0.05, 0.2, 0.1, 0.1, 0.3])
    neurons = pd.DataFrame({"root_id": sorted(set(post.tolist())), "cell_type": types[:len(set(post))],
                            "side": rng.choice(["left", "right"], size=len(set(post))),
                            "connectome": "malecns-v1.0"})
    return edges, neurons


def main():
    import pandas as pd

    DATA.mkdir(parents=True, exist_ok=True)
    RUN.mkdir(parents=True, exist_ok=True)

    if args.synth:
        edges, neurons = synth()
        edges.to_parquet(DATA / "malecns_edgelist.parquet", index=False)
        neurons.to_parquet(DATA / "malecns_neurons.parquet", index=False)
        note = "синтетика: проверка формата без интернета"
        found_edges, found_annot = "синтетика", "синтетика"
    else:
        prefixes = PREFIXES + list(args.prefix)
        print(f"смотрю бакет {BUCKET}: {', '.join(prefixes)}")
        objects = []
        for p in prefixes:
            items, ok = list_objects(p)
            if ok:
                print(f"  {p}: {len(items)} объектов")
            objects.extend(items)
        if not objects:
            sys.exit("Бакет недоступен или пуст. Проверь интернет либо запусти с --synth.")
        tables = [o for o in objects if o["name"].lower().endswith(DATA_SUFFIX)]
        cand_edges = [o for o in tables if EDGE_HINT.search(o["name"])]
        cand_annot = [o for o in tables if ANNOT_HINT.search(o["name"])]
        print(f"всего таблиц: {len(tables)}, кандидатов на связи: {len(cand_edges)}, на аннотации: {len(cand_annot)}")
        for o in sorted(cand_edges, key=lambda x: -int(x.get("size", 0)))[:10]:
            print(f"  связь?   {o['name']}  {human(int(o.get('size', 0)))}")
        for o in sorted(cand_annot, key=lambda x: -int(x.get("size", 0)))[:5]:
            print(f"  подписи? {o['name']}  {human(int(o.get('size', 0)))}")
        if args.check:
            print("\nЗапусти без --check, чтобы скачать. Если подходящего файла связей нет, "
                  "используй neuPrint: https://neuprint.janelia.org/?dataset=male-cns%3Av1.0")
            return
        if not cand_edges:
            print("Готовой таблицы связей в бакете не нашлось.")
            print("Варианты: 1) neuPrint male-cns:v1.0, 2) synapse-таблицы cloud-volume, "
                  "3) раздел «Данные и окружение» во вкладке «Мозг».")
            return
        chosen = args.edge_file or sorted(cand_edges, key=lambda x: int(x.get("size", 0)))[0]["name"]
        print(f"беру связи: {chosen}")
        raw = download(chosen, DATA / Path(chosen).name)
        df = read_table(raw)
        edges, err = normalize_edges(df)
        if edges is None:
            sys.exit(f"Не разобрал таблицу связей: {err}")
        edges.to_parquet(DATA / "malecns_edgelist.parquet", index=False)
        found_edges = chosen
        neurons, found_annot = None, ""
        if cand_annot:
            chosen_a = sorted(cand_annot, key=lambda x: int(x.get("size", 0)))[0]["name"]
            print(f"беру подписи: {chosen_a}")
            raw_a = download(chosen_a, DATA / Path(chosen_a).name)
            ann = read_table(raw_a)
            rid = pick_column(ann, "bodyId", "rootid", "bodyid", "id", "body")
            ctype = pick_column(ann, "celltype", "type", "class", "cell_type")
            side = pick_column(ann, "side", "hemisphere")
            if rid:
                neurons = pd.DataFrame({"root_id": ann[rid].astype("int64")})
                if ctype:
                    neurons["cell_type"] = ann[ctype].astype(str)
                if side:
                    neurons["side"] = ann[side].astype(str)
                neurons["connectome"] = "malecns-v1.0"
                neurons.to_parquet(DATA / "malecns_neurons.parquet", index=False)
                found_annot = chosen_a
        note = "данные Janelia MaleCNS v1.0, лицензия CC-BY 4.0"

    if args.keep_types and "cell_type" in (neurons.columns if neurons is not None else []):
        import fnmatch
        pats = [t.strip() for t in args.keep_types.split(",") if t.strip()]
        keep = neurons[neurons.cell_type.apply(lambda t: any(fnmatch.fnmatch(str(t), p) for p in pats))]
        edges = edges_assemble(edges, keep.root_id.tolist())
        neurons = keep
        print(f"оставлено типов: {len(neurons)} клеток")

    types = neurons["cell_type"].value_counts().head(15).to_dict() if neurons is not None and "cell_type" in neurons.columns else {}
    summary = {
        "источник_связей": found_edges, "источник_подписей": found_annot,
        "связей": int(len(edges)), "нейронов_в_связях": int(len(set(edges.pre) | set(edges.post))),
        "клеток_с_подписями": int(len(neurons)) if neurons is not None else 0,
        "синапсов_всего": int(edges.weight.sum()),
        "частые_типы": types, "примечание": note,
        "файлы": [f for f in ("malecns_edgelist.parquet", "malecns_neurons.parquet") if (DATA / f).exists()],
        "важно": "id MaleCNS не совпадают с id FlyWire v783: спайки одной модели нельзя "
                 "накладывать на скелеты другого коннектома без соответствия",
    }
    (RUN / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"связей: {len(edges)}, клеток с подписями: {summary['клеток_с_подписями']}")
    print(f"таблица связей: {DATA / 'malecns_edgelist.parquet'}")
    print(f"сводка: {RUN / 'summary.json'}")


def edges_assemble(edges, keep_ids):  # заготовка на случай фильтра по типам
    keep = set(keep_ids)
    return edges[edges.pre.isin(keep) & edges.post.isin(keep)]


if __name__ == "__main__":
    main()
