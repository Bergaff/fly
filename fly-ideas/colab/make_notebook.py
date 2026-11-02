"""Generate the self-contained Colab notebook from the checked repository files."""
import base64
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
files={name:(ROOT/'experiments/templates'/name).read_bytes() for name in ['25_shiu_v630_control.py','27_shiu_top200_v630.py','28_shiu_lesions_v630.py','30_shiu_lesion_overview.py']}
files['fly_colab.py']=(ROOT/'colab/fly_colab.py').read_bytes()
bundle={k:{'sha256':hashlib.sha256(v).hexdigest(),'gzip_base64':base64.b64encode(gzip.compress(v,mtime=0)).decode('ascii')} for k,v in files.items()}

def md(text):return {'cell_type':'markdown','metadata':{},'source':text.strip().splitlines(keepends=True)}
def code(text):return {'cell_type':'code','metadata':{},'execution_count':None,'outputs':[],'source':text.strip().splitlines(keepends=True)}

cells=[md('''# Shiu v630: полная серия в Google Colab

**Основная серия: CPU. GPU здесь только отдельная экспериментальная проба.** Блокнот начинает новую серию: старые SQLite не ищутся и не импортируются. Полный план состоит из 8 частот × 201 условие (контроль и 200 лезий) × 30 seed = **48 240 повторов**. Лезия обнуляет исходящие веса. Это модельные повторы, а не животные.

**Порядок работы:** (1) подключить Диск, (2) скопировать исходные файлы в указанную папку, (3) подготовить окружение, (4) проверить данные, (5) отдельно разрешить запуск CPU. Изменение параметров и повторный запуск ячейки после обрыва продолжает только сохранённую CPU-серию. Ячейки GPU и экспорта необязательны и по умолчанию ничего не рассчитывают.

Бесплатный Colab может прерывать сеанс, ограничивать время, память, GPU и квоты. Скорость и наличие видеокарты не гарантированы. На Google Диске должны быть свободное место и работающий доступ к записи. Держите открытой **только одну** сессию этого набора: при обнаружении расходящихся веток блокнот остановится, а не объединит их.

Файлы и код проверяются по контрольным суммам. Исходный топ был создан в другой среде; его исходные версии сохраняются и проверяются отдельно. Если между сеансами изменится версия Python, NumPy, Brian2 или протокол CPU, автоматическое смешивание блокируется. Снимки на Диске не заменяют отдельную копию на другом носителе.'''),
code('''#@title 1. Подключить Google Диск и создать папки для входных файлов
from google.colab import drive
from pathlib import Path

drive.mount('/content/drive')
ROOT = Path('/content/drive/MyDrive/Fly_Shiu_Colab')
INPUT = ROOT / '01_Исходные_файлы'
(INPUT / 'top200').mkdir(parents=True, exist_ok=True)
print('Папка для исходных данных:', INPUT)
print('Папка полного топ-200:', INPUT / 'top200')'''),
md('''## 2. Скопируйте исходные файлы на Диск

Через Google Диск поместите **копии** файлов в созданную папку:

```text
Мой диск/Fly_Shiu_Colab/01_Исходные_файлы/
  2023_03_23_connectivity_630_final.parquet
  2023_03_23_completeness_630_final.csv
  top200/
    summary.json
    checkpoint.json
    top200.csv
    counts_seed_00.npy ... counts_seed_29.npy
```

Внутрь `top200` положите именно содержимое полной папки топа, не ещё одну вложенную папку. Можно скопировать её из общего набора приложения (`01_top200`) или исходного завершённого прогона. Старые SQLite не нужны. Дождитесь полной загрузки файлов на Google Диск.'''),
code('''#@title 3. Подготовить изолированное CPU-окружение
import sys, subprocess, os, base64, gzip, hashlib
from pathlib import Path
if sys.version_info[:2] != (3, 12):
    raise RuntimeError('Этот блокнот подготовлен для Python 3.12 в Colab. Версия изменилась; не смешивайте результаты, нужна проверка окружения.')
CPU_PY = Path('/content/fly-shiu-cpu/bin/python')
if not CPU_PY.exists():
    subprocess.run([sys.executable, '-m', 'venv', str(CPU_PY.parents[1])], check=True)
subprocess.run([str(CPU_PY), '-m', 'pip', 'install', '-q', 'numpy==1.26.4', 'pandas==2.2.3', 'pyarrow==18.1.0', 'brian2==2.9.0', 'psutil==6.1.1'], check=True)
print('CPU-окружение готово.')'''),
code("""#@title 3б. Развернуть проверенный код из самого блокнота
BUNDLE = __BUNDLE__
CODE = Path('/content/fly-shiu-code')
CODE.mkdir(exist_ok=True)
for name, item in BUNDLE.items():
    contents = gzip.decompress(base64.b64decode(item['gzip_base64']))
    if hashlib.sha256(contents).hexdigest() != item['sha256']:
        raise RuntimeError('Ошибка контрольной суммы встроенного файла: ' + name)
    target = CODE / name
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != item['sha256']:
        raise RuntimeError('Файл кода был изменён и не будет перезаписан: ' + str(target))
    if not target.exists():
        target.write_bytes(contents)
print('Встроенный код проверен.')""".replace('__BUNDLE__',repr(bundle))),
code('''#@title 4. Проверить входные файлы и топ-200 без симуляций
subprocess.run([str(CPU_PY), str(CODE / 'fly_colab.py'), '--root', str(ROOT), '--mode', 'check'], check=True)'''),
md('''## 5. Основная серия CPU

Включите флажок **START_CPU**, только когда готовы к расчёту, и запустите следующую ячейку. До двух процессов используются, только если хватает свободной памяти; иначе один. Скорость зависит от выданной Colab машины, сеть строится заново для каждого повтора, ускорение относительно вашего компьютера не гарантируется. Для ориентира: прежний локальный замер около 28 секунд на повтор даёт примерно 380 часов последовательной симуляции для 48 240 повторов, без построения сети; Colab может быть быстрее или медленнее.

База работает на временном диске Colab. Каждые 25 завершённых повторов создаётся новый сжатый согласованный снимок на Google Диске и проверяется его чтение. При внезапном отключении последние повторы после снимка могут потеряться. Для продолжения подключитесь заново и выполните ячейки 1, 3, 3б, 4 и 5; в 5 снова включите флажок. Уже сохранённые повторы пропускаются. Снимки не удаляются автоматически, следите за свободным местом на Диске. При ошибке записи процесс прекращает работу. Сеть/Google Drive могут задерживать синхронизацию: после остановки убедитесь, что снимки действительно видны в Google Диске.

**Не запускайте две копии блокнота одновременно** с одной и той же папкой: блокировки Google Диска не дают надёжной гарантии между машинами. Если возникнут две ветки снимков, блокнот остановится. Не удаляйте и не объединяйте их самостоятельно.'''),
code('''#@title 5. Запустить или продолжить CPU-серию
START_CPU = False #@param {type:"boolean"}
CPU_WORKERS = 2 #@param [1, 2] {type:"raw"}
CHECKPOINT_EVERY = 25 #@param {type:"integer"}
MAX_TRIALS_THIS_SESSION = 0 #@param {type:"integer"}
# MAX_TRIALS_THIS_SESSION = 0 означает без ограничения на число повторов в этом сеансе.
if START_CPU:
    subprocess.run([str(CPU_PY), str(CODE / 'fly_colab.py'), '--root', str(ROOT), '--mode', 'cpu', '--workers', str(CPU_WORKERS), '--checkpoint-every', str(CHECKPOINT_EVERY), '--max-trials', str(MAX_TRIALS_THIS_SESSION)], check=True)
else:
    print('Расчёт не запущен. Для старта включите START_CPU и выполните ячейку.')'''),
md('''## 6. Отдельный экспериментальный GPU-пилот

**Не часть полного плана.** Для него потребуется GPU runtime Colab, NVIDIA CUDA и установка отдельного окружения. Смена типа среды завершит текущий сеанс, поэтому сначала остановите CPU и дождитесь сохранения снимка. Вернитесь и выполните ячейки 1, 3 и 3б. Затем включите флажок ниже.

Будут выполнены контроль и одна лезия при 100 Гц, seed 0, сначала на CPU, затем на GPU. CPU-пилот не добавляется в полную серию, GPU не добавляется в CPU-базу. Brian2CUDA использует другую версию Brian2 и другой генератор случайных чисел, поэтому одинаковые seed не гарантируют одинаковые спайки. Времена CPU и GPU также не являются корректным сравнением скорости: компиляция GPU включена, а время CPU из кода 28 не включает построение сети. Для выводов понадобится расширенная проверка и измерение. Проба может не запуститься или не поместиться в память бесплатной видеокарты. В этом случае CPU-серия остаётся независимой.

GPU-путь не проверен нами на настоящем Colab/GPU. Если будет ошибка, сохраните текст ячейки и пришлите его; не запускайте полный план на неподтверждённом GPU-коде.'''),
code('''#@title 6. Попробовать CPU и GPU отдельно
RUN_GPU_PILOT = False #@param {type:"boolean"}
if RUN_GPU_PILOT:
    import shutil
    if not shutil.which('nvidia-smi') or not shutil.which('nvcc'):
        raise RuntimeError('Нужен GPU runtime Colab с NVIDIA GPU и nvcc. GPU-пилот не запущен.')
    subprocess.run(['nvidia-smi'], check=True)
    GPU_PY = Path('/content/fly-shiu-gpu/bin/python')
    if not GPU_PY.exists():
        subprocess.run([sys.executable, '-m', 'venv', str(GPU_PY.parents[1])], check=True)
    subprocess.run([str(GPU_PY), '-m', 'pip', 'install', '-q', 'numpy==2.2.6', 'pandas==2.2.3', 'pyarrow==18.1.0', 'brian2cuda==1.0b1', 'psutil==6.1.1'], check=True)
    subprocess.run([str(CPU_PY), str(CODE / 'fly_colab.py'), '--root', str(ROOT), '--mode', 'cpu-pilot'], check=True)
    subprocess.run([str(GPU_PY), str(CODE / 'fly_colab.py'), '--root', str(ROOT), '--mode', 'gpu-pilot'], check=True)
    print('Пилоты сохранены отдельно в 04_Отдельные_GPU_пробы. Они не входят в полный план.')
else:
    print('GPU-пилот не запущен.')'''),
md('''## 7. Экспорт для приложения

При необходимости включите флажок ниже. Будет проверен последний снимок CPU-серии и создана **новая** папка с `lesions.sqlite3` на Диске. Её можно скачать после завершения записи. Для обзора в приложении потребуется также папка того же топ-200. Автоматическое продолжение этого файла на Windows может быть запрещено из-за различий версий Python; обзор не запускает симуляцию. Экспорт не изменяет исходные снимки.'''),
code('''#@title 7. Создать проверенную копию SQLite для приложения
EXPORT_CPU = False #@param {type:"boolean"}
if EXPORT_CPU:
    subprocess.run([str(CPU_PY), str(CODE / 'fly_colab.py'), '--root', str(ROOT), '--mode', 'export'], check=True)
else:
    print('Экспорт не запущен.')''')]
for i,cell in enumerate(cells): cell['id']=f'fly-shiu-{i:02d}'
notebook={'cells':cells,'metadata':{'colab':{'provenance':[]},'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.12'}},'nbformat':4,'nbformat_minor':5}
output=ROOT/'colab/Shiu_v630_Colab.ipynb';output.write_text(json.dumps(notebook,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Notebook:',output,'bytes:',output.stat().st_size)
