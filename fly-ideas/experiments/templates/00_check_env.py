"""Проверка окружения: python, пакеты, GPU, наличие данных коннектома.

Запускается из вкладки «Мозг» → «Скрипты». Ничего не меняет.
"""
import importlib
import json
import os
import sys
from pathlib import Path

DATA = Path(os.environ.get("FLY_DATA", "workspace/data"))
RUN = Path(os.environ.get("FLY_RUN_DIR", "."))

print(f"python  : {sys.version.split()[0]}  ({sys.executable})")
print(f"data    : {DATA}")
print()

pk = {}
for m in ["numpy", "pandas", "pyarrow", "scipy", "matplotlib", "brian2", "torch"]:
    try:
        mod = importlib.import_module(m)
        pk[m] = getattr(mod, "__version__", "ok")
        print(f"  [ok]  {m:<11} {pk[m]}")
    except Exception:
        pk[m] = None
        print(f"  [--]  {m:<11} не установлен")

gpu = None
try:
    import torch  # noqa

    if torch.cuda.is_available():
        gpu = torch.cuda.get_device_name(0)
        print(f"\n  GPU: {gpu}")
    else:
        print("\n  GPU: CUDA недоступна (это нормально для CPU-запусков Brian2)")
except Exception:
    pass

print("\nДанные коннектома:")
files = {
    "2025_Completeness_783.csv": "список нейронов",
    "2025_Connectivity_783.parquet": "связность",
}
present = {}
for f, d in files.items():
    p = DATA / f
    present[f] = p.exists() and p.stat().st_size > 1000
    if present[f]:
        print(f"  [ok]  {f:<32} {p.stat().st_size/1e6:7.1f} МБ  ({d})")
    else:
        print(f"  [--]  {f:<32} нет  ({d}) — кнопка «Скачать» во вкладке «Мозг»")

missing = [m for m in ["numpy", "pandas", "pyarrow", "brian2"] if not pk.get(m)]
print()
if missing:
    print("Чтобы запускать модель Shiu et al., поставь:")
    print(f"  pip install {' '.join(missing)}")
    print("или создай conda-окружение из репозитория eonsystemspbc/fly-brain (environment.yml).")
else:
    print("Всё нужное для CPU-модели есть.")

(RUN / "summary.json").write_text(
    json.dumps({"packages": pk, "gpu": gpu, "data": present, "ok": not missing}, ensure_ascii=False, indent=2), encoding="utf-8"
)
