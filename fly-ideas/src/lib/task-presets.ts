/**
 * Каталог готового локального кода анализа под все текущие задачи проекта.
 * Позволяет сразу открывать и запускать проверенные Python-скрипты на ПК без платной генерации с нуля через API.
 */

export interface PresetMode {
  id: string;
  label: string;
  args: string;
  hint: string;
}

export interface TaskPreset {
  ideaId: string;
  script: string;
  companionScripts?: string[];
  shortTitle: string;
  summary: string;
  requiredData: string[];
  outputs: string[];
  modes: PresetMode[];
}

export const TASK_PRESETS: TaskPreset[] = [
  {
    ideaId: "i-lesions",
    script: "10_virtual_lesions.py",
    companionScripts: ["03_shiu_activate.py", "06_brian2_shiu.py"],
    shortTitle: "Карта виртуальных лезий: отключения областей и парный эпистаз",
    summary:
      "Поочерёдно отключает нейропильные области коннектома, снимает кривую доза-эффект при случайной потере 0..100% клеток области и строит матрицу парных лезий на предмет неаддитивного эпистаза и обходных путей.",
    requiredData: ["2025_Completeness_783.csv", "2025_Connectivity_783.parquet", "Supplemental_file1_neuron_annotations.tsv"],
    outputs: ["lesion_single.csv", "lesion_dose_response.csv", "lesion_epistasis.csv", "lesions_overview.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрая проверка без данных (--synth)",
        args: "--synth --n-run 4",
        hint: "Проверяет весь конвейер, таблицы и 4-панельную фигуру за ~12 с на любом ПК.",
      },
      {
        id: "connectome",
        label: "Прогон на локальном коннектоме (FLY_DATA)",
        args: "--max-neurons 4000 --n-run 5 --seed 0",
        hint: "Использует скачанные таблицы FlyWire v783 из папки данных.",
      },
      {
        id: "detailed",
        label: "Подробная сетка доз и статпроверка",
        args: "--max-neurons 6000 --doses 0,0.1,0.2,0.4,0.6,0.8,1.0 --n-run 8 --seed 1",
        hint: "Увеличенное число попыток и дробная шкала частичного отключения синапсов.",
      },
    ],
  },
  {
    ideaId: "i-interference",
    script: "11_mb_interference_connectome.py",
    companionScripts: ["02_mb_toy_interference.py", "04_mb_sweep_heatmap.py", "09_mb_circuit_v783.py"],
    shortTitle: "Ретроактивная интерференция в MB: стирание против маскировки следа",
    summary:
      "Сравнивает пассивное забывание, угасание без удара, контробусловливание наградой PAM и перегрузку новыми запахами; проводит 4 классических поведенческих теста (спонтанное восстановление, напоминание US, смена контекста ABA, экономия при переобучении) и измеряет сохранность первичного следа в синапсах KC->MBON.",
    requiredData: ["2025_Completeness_783.csv", "2025_Connectivity_783.parquet", "Supplemental_file1_neuron_annotations.tsv"],
    outputs: ["interference_curves.csv", "recovery_tests.csv", "interference_connectome.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрая проверка без данных (--synth)",
        args: "--synth --n-train 8 --n-relearn 14 --n-junk 8",
        hint: "Считает кривые обучения, 4 теста возврата памяти и сохранность весов за ~2 с.",
      },
      {
        id: "connectome",
        label: "Прогон на матрице KC->MBON из v783",
        args: "--n-train 10 --n-relearn 16 --n-junk 10 --seed 0",
        hint: "Строит компартментную сеть на реальных связях грибовидного тела из FLY_DATA.",
      },
      {
        id: "heavy-junk",
        label: "Сильная интерференция потоком запахов",
        args: "--n-train 10 --n-relearn 24 --n-junk 18 --lr 0.28 --seed 2",
        hint: "Проверяет предел ёмкости разреженного кода KC при плотном потоке конкурирующих стимулов.",
      },
    ],
  },
  {
    ideaId: "i-benchmark",
    script: "12_backend_benchmark.py",
    companionScripts: ["00_check_env.py", "06_brian2_shiu.py"],
    shortTitle: "Честный бенчмарк бэкендов LIF-модели (скорость и совпадение частот)",
    summary:
      "Гоняет идентичные уравнения Shiu et al. 2024 на одной и той же матрице весов и стимуле через Brian2 CPU, векторный разреженный SciPy/CSR, плотный NumPy и PyTorch (CPU и CUDA при наличии видеокарты), сверяя время компиляции, скорость шага, память и корреляцию частот спайков.",
    requiredData: ["2025_Completeness_783.csv", "2025_Connectivity_783.parquet"],
    outputs: ["benchmark_runs.csv", "backend_agreement.csv", "benchmark_summary.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрый тест на ноутбуке (--synth)",
        args: "--synth --max-neurons 1500 --t 0.25 --n-run 1",
        hint: "Сравнивает установленные бэкенды без скачивания файлов коннектома.",
      },
      {
        id: "connectome",
        label: "Бенчмарк на подсетях реального коннектома",
        args: "--max-neurons 6000 --t 0.4 --n-run 4 --seed 0",
        hint: "Реальная плотность связей FlyWire v783 и замер точности относительно Brian2.",
      },
      {
        id: "fast-large",
        label: "Масштабирование быстрых бэкендов (без Brian2)",
        args: "--backends scipy_sparse_cpu,torch_cpu,torch_cuda --max-neurons 40000 --t 0.3 --n-run 1",
        hint: "Проверяет скорость разреженного CSR и PyTorch/CUDA на десятках тысяч нейронов.",
      },
    ],
  },
  {
    ideaId: "i-mb-learning",
    script: "13_whole_brain_mb_learning.py",
    companionScripts: ["09_mb_circuit_v783.py", "06_brian2_shiu.py"],
    shortTitle: "Трехфакторное обучение в MB внутри спайковой сети целого мозга",
    summary:
      "Встраивает синаптическую пластичность KC->MBON (след спайка KC x сигнал дофамина PPL1/PAM) и возвратное торможение APL прямо в спайковую LIF-сеть мозга, проверяя дифференциальное обучение CS+/CS-, обобщение, устойчивость фона и деградацию при отключении APL или перемешивании графа.",
    requiredData: ["2025_Completeness_783.csv", "2025_Connectivity_783.parquet", "Supplemental_file1_neuron_annotations.tsv"],
    outputs: ["whole_brain_learning.csv", "whole_brain_vs_shuffled.csv", "whole_brain_mb.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрая проверка без данных (--synth)",
        args: "--synth --n-trials 4 --n-ext 4",
        hint: "Прогоняет интактный мозг, контроль без APL и перемешанный граф за ~12 с.",
      },
      {
        id: "connectome",
        label: "Обучение на коннектоме FlyWire v783",
        args: "--max-neurons 3500 --n-trials 6 --n-ext 5 --seed 0",
        hint: "Спайковый протокол CS+/CS- на реальной топологии с контролем отсутствия перевозбуждения.",
      },
      {
        id: "high-lr",
        label: "Усиленная пластичность и длинное угасание",
        args: "--max-neurons 3500 --n-trials 8 --n-ext 8 --lr 0.42 --seed 1",
        hint: "Проверка устойчивости возвратных петель при большом сдвиге весов KC->MBON.",
      },
    ],
  },
  {
    ideaId: "i-courtship-memory",
    script: "14_malecns_courtship_memory.py",
    companionScripts: ["08_malecns_loader.py", "07_morph_activity_figure.py"],
    shortTitle: "Память при ухаживании на мужском коннектоме MaleCNS против самки v783",
    summary:
      "Моделирует подавление ухаживания после обучения с отвергающей самкой (контур Or67d/vPN1 -> KCg + aSP13/PAM -> MBON -> pC1/P1 -> крыльевые мотонейроны), сверяет кривую удержания 0..4 ч дикого типа и мутанта amnesiac с данными Siegel & Hall 1979 и сравнивает мужской контур с женским гомологом.",
    requiredData: [
      "body-annotations-male-cns-v0.9-minconf-0.5.feather",
      "mcns_fw_edge_comp_mappings.json",
      "2025_Connectivity_783.parquet",
      "Supplemental_file1_neuron_annotations.tsv",
    ],
    outputs: ["courtship_retention.csv", "sex_dimorphism_circuit.csv", "dimorphic_audit.csv", "courtship_memory.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрая проверка без данных (--synth)",
        args: "--synth --train-min 60 --max-hours 4",
        hint: "Строит кривые удержания WT vs amnesiac и аудит диморфных узлов за ~1.5 с.",
      },
      {
        id: "connectome",
        label: "Сравнение локальных коннектомов MaleCNS и v783",
        args: "--train-min 60 --max-hours 4 --seed 0",
        hint: "Читает таблицы MaleCNS и FlyWire из папки данных и таблицу гомологии типов.",
      },
      {
        id: "short-train",
        label: "Короткое обучение (25 мин) и длинный хвост 6 ч",
        args: "--train-min 25 --max-hours 6 --seed 2",
        hint: "Проверяет зависимость длительности памяти от экспозиции феромону cVA.",
      },
    ],
  },
  {
    ideaId: "i-memory-to-action",
    script: "15_memory_to_motor_vnc.py",
    companionScripts: ["08_malecns_loader.py", "05_neuron_gallery.py"],
    shortTitle: "От следа памяти в MB через шейные DN к мотонейронам VNC",
    summary:
      "Заменяет условный линейный классификатор на полный анатомический тракт MB -> MBON -> LAL/DNa/DNp -> мотонейроны брюшной нервной цепочки VNC: измеряет миллисекундную латентность прихода следа памяти на каждом этаже и считает минимальное число мотонейронов для распознавания памяти на одной попытке.",
    requiredData: [
      "body-annotations-male-cns-v0.9-minconf-0.5.feather",
      "dnan_cluster_function_20260509.csv",
    ],
    outputs: ["motor_latency_traces.csv", "motor_redundancy.csv", "motor_vectors.csv", "memory_to_motor.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрая проверка без данных (--synth)",
        args: "--synth --n-trials 14",
        hint: "Считает задержки MBON->DN->VNC и кривую избыточности мотонейронов за ~3 с.",
      },
      {
        id: "connectome",
        label: "Прогон на коннектоме ЦНС с брюшной цепочкой",
        args: "--max-neurons 4500 --n-trials 16 --seed 0",
        hint: "Использует таблицы MaleCNS и кластеры нисходящих нейронов из FLY_DATA.",
      },
      {
        id: "high-trials",
        label: "Точная оценка декодирования по 1 попытке",
        args: "--max-neurons 4500 --n-trials 28 --stim-ms 300 --seed 1",
        hint: "Увеличенная выборка попыток для гладкой кривой достаточности k мотонейронов.",
      },
    ],
  },
  {
    ideaId: "i-observational",
    script: "16_observational_learning.py",
    companionScripts: ["09_mb_circuit_v783.py"],
    shortTitle: "Социальное обучение через наблюдение (D -> O) и культурная цепочка",
    summary:
      "Проводит анатомический аудит путей 1..3 шага от зрительных проекционных нейронов LC/VPN к клеткам Кеньона и дофаминовым нейронам PPL1/PAM, моделирует пару муха-демонстратор D и муха-наблюдатель O со всеми 4 контролями и проверяет затухание традиции вдоль цепочки D -> O1 -> O2 -> O3 -> O4.",
    requiredData: ["2025_Completeness_783.csv", "2025_Connectivity_783.parquet", "Supplemental_file1_neuron_annotations.tsv"],
    outputs: ["observational_conditions.csv", "cultural_chain.csv", "visual_to_dan_paths.csv", "observational_learning.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрая проверка без данных (--synth)",
        args: "--synth --n-direct 6 --n-obs 12",
        hint: "Считает аудит путей, все 4 контроля и цепочку из 4 поколений за ~1.5 с.",
      },
      {
        id: "connectome",
        label: "Аудит путей зрение->DAN и тест D->O на v783",
        args: "--max-neurons 6000 --n-direct 6 --n-obs 14 --seed 0",
        hint: "Оценивает реальную силу зрительно-дофаминового канала на таблицах FlyWire v783.",
      },
      {
        id: "amplified",
        label: "Проверка порога устойчивой традиции (--vis-gain 2.0)",
        args: "--max-neurons 6000 --n-obs 16 --vis-gain 2.0 --seed 1",
        hint: "Показывает, какого усиления связи LC->DAN требует сохранение навыка до O4.",
      },
    ],
  },
  {
    ideaId: "i-individuality",
    script: "17_individuality_phenotypes.py",
    companionScripts: ["06_brian2_shiu.py"],
    shortTitle: "Индивидуальность из одинакового мозга: шум против микро-вариации и опыта",
    summary:
      "Гоняет когорту виртуальных особей в День 1 и День 2 на одном и том же коннектоме в трёх режимах (чистый динамический шум, фиксированная микро-вариация синапсов развития, ранний пластический опыт), оценивая воспроизводимость выбора r(День 1, День 2), коэффициент ICC(1,1) и оси PCA.",
    requiredData: ["2025_Completeness_783.csv", "2025_Connectivity_783.parquet", "Supplemental_file1_neuron_annotations.tsv"],
    outputs: ["individual_flies.csv", "individuality_regimes.csv", "individuality_phenotypes.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрая проверка когорты (--synth)",
        args: "--synth --n-flies 16 --trials-per-day 3",
        hint: "Сравнивает 3 гипотезы индивидуальности на 16 особях за ~25 с.",
      },
      {
        id: "connectome",
        label: "Когорта 24 особей на коннектоме v783",
        args: "--max-neurons 2000 --n-flies 24 --trials-per-day 4 --seed 0",
        hint: "Полный расчёт ICC(1,1), тест-ретест корреляции и PCA-фенотипов.",
      },
      {
        id: "subtle-dev",
        label: "Малая вариация синаптогенеза (--weight-cv 0.10)",
        args: "--max-neurons 2000 --n-flies 24 --weight-cv 0.10 --thresh-sd 0.40 --seed 2",
        hint: "Проверяет минимальный порог синаптического разброса для появления устойчивого ранга особей.",
      },
    ],
  },
  {
    ideaId: "i-song",
    script: "18_courtship_song_ipi.py",
    companionScripts: ["08_malecns_loader.py"],
    shortTitle: "Слуховой контур брачной песни JO -> AMMC -> WED -> vPN1 -> pC1",
    summary:
      "Подаёт на механосенсорные нейроны Джонстонова органа пачки pulse song с межимпульсным интервалом IPI 15..90 мс, синусную песню 150 Гц и шум; наглядно показывает, почему чисто статичный LIF не выделяет видовой оптимум 35 мс и как кратковременная депрессия плюс задержанное торможение формируют полосовой фильтр.",
    requiredData: ["body-annotations-male-cns-v0.9-minconf-0.5.feather", "2025_Connectivity_783.parquet"],
    outputs: ["song_ipi_tuning.csv", "song_cascade_rates.csv", "courtship_song_ipi.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрая развёртка IPI 15..90 мс (--synth)",
        args: "--synth --ipis 15,25,35,45,55,70,90 --n-trials 6",
        hint: "Строит кривые настройки 5 ступеней тракта и сравнение pulse/sine за ~5 с.",
      },
      {
        id: "connectome",
        label: "Прогон на слуховом тракте из FLY_DATA",
        args: "--connectome malecns --ipis 15,25,30,35,40,50,70,90 --n-trials 8 --seed 0",
        hint: "Подробная сетка вокруг видового оптимума 35 мс на реальном контуре.",
      },
      {
        id: "female-v783",
        label: "Проверка слухового контура самки (FlyWire v783)",
        args: "--connectome flywire --ipis 15,25,35,45,60,85 --n-trials 8 --seed 1",
        hint: "Оценивает избирательность восприятия брачной песни на женском коннектоме.",
      },
    ],
  },
  {
    ideaId: "i-pci",
    script: "19_pci_integration.py",
    companionScripts: ["06_brian2_shiu.py"],
    shortTitle: "Индекс пертурбационной сложности PCI и баланс интеграции/дифференциации",
    summary:
      "Наносит локальный импульс возмущения на модуль сети, строит бинарную матрицу вызванного ответа S(m, t), считает нормированную сложность Лемпеля-Зива (PCI) при разном глобальном сцеплении g и сопоставляет модульный коннектом с перемешанным графом и изолированной решёткой.",
    requiredData: ["2025_Completeness_783.csv", "2025_Connectivity_783.parquet", "Supplemental_file1_neuron_annotations.tsv"],
    outputs: ["pci_regimes.csv", "pci_topologies.csv", "pci_complexity.png", "summary.json"],
    modes: [
      {
        id: "synth",
        label: "Быстрая проверка 3 топологий (--synth)",
        args: "--synth --couplings 0.45,0.75,1.05,1.45,2.05",
        hint: "Сравнивает коннектом, shuffled и решётку за ~8 с.",
      },
      {
        id: "connectome",
        label: "Развёртка PCI на коннектоме FlyWire v783",
        args: "--max-neurons 2500 --n-channels 36 --n-trials 8 --seed 0",
        hint: "Строит кривую сложности Лемпеля-Зива и матрицы отклика S(m, t) на реальных пулах.",
      },
      {
        id: "fine-grid",
        label: "Подробная шкала глобального сцепления g",
        args: "--max-neurons 2500 --couplings 0.35,0.6,0.85,1.05,1.3,1.65,2.1 --n-trials 10",
        hint: "Детальный поиск критической точки между затуханием и глобальной вспышкой.",
      },
    ],
  },
];

const BY_IDEA = new Map<string, TaskPreset>(TASK_PRESETS.map((p) => [p.ideaId, p]));
const BY_SCRIPT = new Map<string, TaskPreset>(TASK_PRESETS.map((p) => [p.script, p]));

export function presetForIdea(ideaId: string | null | undefined): TaskPreset | null {
  if (!ideaId) return null;
  return BY_IDEA.get(ideaId) ?? null;
}

export function presetForScript(scriptName: string | null | undefined): TaskPreset | null {
  if (!scriptName) return null;
  return BY_SCRIPT.get(scriptName) ?? null;
}
