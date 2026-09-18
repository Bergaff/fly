import type { AppState, ChecklistItem, Idea, Project } from "./types";
import { DEFAULT_CHECKLIST } from "./types";
import { uid } from "@/lib/utils";

const now = new Date().toISOString();

export const SEED_PROJECTS: Project[] = [
  {
    id: "p-fly-brain",
    name: "Мозг мухи (whole-brain emulation)",
    description: "Идеи статей на модели Shiu et al. 2024 / Eon fly-brain / FlyWire v783",
    color: "var(--chart-2)",
    createdAt: now,
  },
  {
    id: "p-phd",
    name: "Основная диссертация",
    description: "Идеи, которые могут пригодиться в основном направлении",
    color: "var(--chart-1)",
    createdAt: now,
  },
  {
    id: "p-archive",
    name: "Архив / когда-нибудь",
    description: "Интересно, но не сейчас",
    color: "var(--muted-foreground)",
    createdAt: now,
  },
];

export const makeChecklist = (doneCount = 0): ChecklistItem[] =>
  DEFAULT_CHECKLIST.map((text, i) => ({ id: uid("c"), text, done: i < doneCount, doneAt: i < doneCount ? now : null }));

const plusDays = (n: number) => {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
};

type Optional = "links" | "notes" | "checklist" | "deadline" | "dependsOn";
const idea = (partial: Omit<Idea, "createdAt" | "updatedAt" | Optional> & Partial<Pick<Idea, Optional>>): Idea => ({
  notes: "",
  links: [],
  checklist: makeChecklist(),
  deadline: null,
  dependsOn: [],
  createdAt: now,
  updatedAt: now,
  ...partial,
});

export const SEED_IDEAS: Idea[] = [
  idea({
    id: "i-lesions",
    projectId: "p-fly-brain",
    title: "Виртуальные лезии: карта необходимости областей мозга",
    question:
      "Какие области / типы клеток необходимы для конкретных сенсомоторных преобразований (вкус → питание, механосенсорика → груминг)?",
    method: `1. Воспроизвести 1–2 фигуры Shiu et al. (Brian2, CPU) — baseline.
2. По очереди «выключать» нейропили из аннотаций FlyWire (AVLP, GNG, MB, CX…) — занулять спайки.
3. Мерить деградацию readout мотонейронов: точность, частота, доза-эффект (25/50/100 %).
4. Матрица «область × поведение». Бонус: двойные лезии — избыточность / компенсация.`,
    validation: "Литература по инактивации/лезиям у дрозофилы (десятилетия данных). Совпало — валидация; не совпало — граница LIF-приближения.",
    venues: ["eLife", "PLoS Comp Bio", "J Neurosci", "bioRxiv"],
    timeline: "3–5 месяцев парт-тайм",
    tags: ["lesions", "Brian2", "in silico", "первая статья"],
    status: "exploring",
    scores: { effort: 4, impact: 6, novelty: 5, speed: 7, risk: 2 },
    links: [
      { label: "philshiu/Drosophila_brain_model", url: "https://github.com/philshiu/Drosophila_brain_model" },
      { label: "FlyWire Codex", url: "https://codex.flywire.ai" },
    ],
    notes: "Рекомендуемый основной трек. Метод прост: глушить и мерять.",
    checklist: makeChecklist(1),
    deadline: plusDays(150),
  }),
  idea({
    id: "i-mb-learning",
    projectId: "p-fly-brain",
    title: "Обучение в грибовидных телах внутри целого мозга",
    question:
      "Можно ли получить ассоциативное обучение (запах + наказание → избегание), добавив дофамин-модулируемую пластичность в MB — и чтобы работало внутри полносвязной модели, а не в изолированном контуре?",
    method: `1. Выделить контур KC → APL → MBON по аннотациям типов клеток.
2. Добавить STDP + дофаминовый сигнал через PPL1 (как в DOOMFLY).
3. Протокол: запах A + наказание, запах B без → сдвиг readout к избеганию A. Кривые обучения, забывание, обобщение.
4. Контроль: shuffled connectome — учит ли именно структура.`,
    validation: "Кривые обусловливания у живых мух (Tully & Quinn, Aso et al.).",
    venues: ["eLife", "Nat Commun", "PLoS Comp Bio"],
    timeline: "4–7 месяцев",
    tags: ["plasticity", "STDP", "mushroom body", "learning"],
    status: "backlog",
    scores: { effort: 7, impact: 8, novelty: 7, speed: 4, risk: 5 },
    notes: "Пластичность в большой сети капризна: может всё перевозбудить или погасить. Вторая статья.",
    dependsOn: ["i-lesions"],
  }),
  idea({
    id: "i-individuality",
    projectId: "p-fly-brain",
    title: "Индивидуальность из одинакового мозга",
    question:
      "Откуда берутся устойчивые индивидуальные различия, если коннектом один? Расходятся ли «особи» на стабильные поведенческие фенотипы при разном шуме / инициализации / лёгкой пластичности?",
    method: `1. Baseline из идеи «Лезии».
2. Много запусков одного коннектома с разным шумом и сидом.
3. Поведенческий readout через мотонейроны или FlyGym-тело.
4. Кластеризация траекторий, «наследуемость» фенотипа между запусками.`,
    validation: "Работы по индивидуальности дрозофил (Janelia, de Bivort lab).",
    venues: ["Nat Neurosci?", "eLife", "Curr Biol"],
    timeline: "5–8 месяцев",
    tags: ["individuality", "noise", "nature vs nurture", "тёмная лошадка"],
    status: "backlog",
    scores: { effort: 6, impact: 9, novelty: 9, speed: 3, risk: 7 },
    notes: "Рамку «что считать фенотипом» придётся придумывать самому. Если получится — самая цитируемая.",
    dependsOn: ["i-lesions"],
  }),
  idea({
    id: "i-benchmark",
    projectId: "p-fly-brain",
    title: "Бенчмарк бэкендов fly-brain",
    question:
      "Насколько точно GPU-бэкенды (PyTorch, NEST GPU, GeNN, Brian2CUDA) воспроизводят эталонный Brian2 CPU на новых протоколах (шум, лезии, длинные прогоны)?",
    method: `1. Расширить скрипт сравнения Eon: больше протоколов, строгая статистика.
2. Замер скорости и памяти на CPU / GPU.
3. Таблицы расхождений, рекомендации по выбору бэкенда.`,
    validation: "Сам эталон Brian2 CPU (корреляция частот ≈ 0.995 в демо Eon).",
    venues: ["JOSS", "Front Neuroinform", "eNeuro (methods)"],
    timeline: "1–2 месяца",
    tags: ["benchmark", "GPU", "methods", "быстрая победа"],
    status: "exploring",
    scores: { effort: 3, impact: 4, novelty: 3, speed: 9, risk: 1 },
    links: [{ label: "eonsystemspbc/fly-brain", url: "https://github.com/eonsystemspbc/fly-brain" }],
    notes: "Запасной аэродром. Тебя заметят разработчики Eon / GeNN.",
    checklist: [
      ...makeChecklist(1).slice(0, 2),
      { id: uid("c"), text: "Запустить скрипт сравнения бэкендов из репозитория Eon", done: false, doneAt: null },
      { id: uid("c"), text: "Добавить протоколы: шум, лезии, длинные прогоны", done: false, doneAt: null },
      { id: uid("c"), text: "Замерить скорость и память на CPU / GPU", done: false, doneAt: null },
      ...makeChecklist().slice(6),
    ],
    deadline: plusDays(60),
  }),
  idea({
    id: "i-song",
    projectId: "p-fly-brain",
    title: "Слуховой контур брачной песни в LIF-модели",
    question:
      "Классифицирует ли статичный LIF-мозг pulse vs sine song по контуру JO → AMMC → WED/AVLP → vPN1 → pC1 без обучения? Где ломается временная обработка?",
    method: `1. Синтезировать спайковые паттерны песни на вход JO-нейронам.
2. Записать ответы вдоль тракта, посмотреть избирательность по межимпульсному интервалу.
3. Сравнить самца и самку (FlyWire vs MaleCNS).`,
    validation: "Записи из AMMC/WED (Murthy lab), поведенческие кривые предпочтения IPI.",
    venues: ["J Neurosci", "eLife"],
    timeline: "4–6 месяцев",
    tags: ["auditory", "courtship song", "communication", "фониатрия-рядом"],
    status: "backlog",
    scores: { effort: 6, impact: 6, novelty: 7, speed: 4, risk: 6 },
    notes: "Мостик к акустической коммуникации. Модели JO в симуляции нет — придётся достраивать.",
    dependsOn: ["i-lesions", "i-benchmark"],
  }),
  idea({
    id: "i-pci",
    projectId: "p-archive",
    title: "PCI / меры интеграции на мушином коннектоме",
    question:
      "Как ведёт себя пертурбационный индекс сложности (PCI) и меры интеграции на подграфах целого мозга мухи? Минимальный тест-кейс для GNW / IIT.",
    method: `1. Импульсная стимуляция случайных популяций, запись ответа всего мозга.
2. Lempel-Ziv сложность ответа как в клиническом PCI.
3. Сравнить с shuffled / lattice-сетями той же плотности.`,
    validation: "Только внутренняя (модельные контроли) — биологических данных PCI у мухи нет.",
    venues: ["Neurosci Conscious", "PLoS Comp Bio"],
    timeline: "3–4 месяца",
    tags: ["consciousness", "PCI", "IIT", "теория"],
    status: "parked",
    scores: { effort: 5, impact: 5, novelty: 8, speed: 5, risk: 6 },
    notes: "Осторожно с формулировками: не «есть ли сознание», а операциональные меры.",
  }),
];

export const SEED_STATE: AppState = {
  version: 1,
  projects: SEED_PROJECTS,
  ideas: SEED_IDEAS,
};
