import type { AppState, ChecklistItem, Idea, Project, Reference } from "./types";
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

type Optional = "links" | "notes" | "checklist" | "deadline" | "dependsOn" | "experiments" | "citations";
const idea = (partial: Omit<Idea, "createdAt" | "updatedAt" | Optional> & Partial<Pick<Idea, Optional>>): Idea => ({
 notes: "",
 links: [],
 checklist: makeChecklist(),
 deadline: null,
 dependsOn: [],
 experiments: [],
 citations: [],
 createdAt: now,
 updatedAt: now,
 ...partial,
});

export const SEED_REFERENCES: Reference[] = [
 {
 id: "r-shiu2024",
 authors: "Shiu PK, Sterne GR, Spiller N, et al.",
 year: 2024,
 title: "A Drosophila computational brain model reveals sensorimotor processing",
 venue: "Nature 634, 210–219",
 doi: "10.1038/s41586-024-07763-9",
 url: "",
 tags: ["модель", "LIF", "baseline"],
 notes: "Эталонная LIF-модель на коннектоме FlyWire. Предсказание моторных ответов на вкус и груминг 91–95 %. Код: philshiu/Drosophila_brain_model.",
 createdAt: now,
 },
 {
 id: "r-dorkenwald2024",
 authors: "Dorkenwald S, Matsliah A, Sterling AR, et al.",
 year: 2024,
 title: "Neuronal wiring diagram of an adult brain",
 venue: "Nature 634, 124–138",
 doi: "10.1038/s41586-024-07558-y",
 url: "",
 tags: ["коннектом", "FlyWire"],
 notes: "Полный коннектом мозга самки дрозофилы: ~139 тыс. нейронов, ~50 млн синапсов. Основа всех симуляций.",
 createdAt: now,
 },
 {
 id: "r-schlegel2024",
 authors: "Schlegel P, Yin Y, Bates AS, et al.",
 year: 2024,
 title: "Whole-brain annotation and multi-connectome cell typing of Drosophila",
 venue: "Nature 634, 139–152",
 doi: "10.1038/s41586-024-07686-5",
 url: "",
 tags: ["коннектом", "типы клеток", "аннотации"],
 notes: "Аннотации типов клеток и нейропилей: по ним выбираются области для лезий и контуры (MB, CX).",
 createdAt: now,
 },
 {
 id: "r-eckstein2024",
 authors: "Eckstein N, Bates AS, Champion A, et al.",
 year: 2024,
 title: "Neurotransmitter classification from electron microscopy images at synaptic sites in Drosophila melanogaster",
 venue: "Cell 187, 2574–2594",
 doi: "10.1016/j.cell.2024.03.016",
 url: "",
 tags: ["нейромедиаторы", "веса"],
 notes: "Предсказание нейромедиатора по ЭМ: откуда берутся знаки синапсов (возб./торм.) в LIF-модели.",
 createdAt: now,
 },
 {
 id: "r-aso2014",
 authors: "Aso Y, Hattori D, Yu Y, et al.",
 year: 2014,
 title: "The neuronal architecture of the mushroom body provides a logic for associative learning",
 venue: "eLife 3, e04577",
 doi: "10.7554/eLife.04577",
 url: "",
 tags: ["грибовидные тела", "обучение", "дофамин"],
 notes: "Архитектура MB: компартменты, DAN → KC → MBON. Логика ассоциативного обучения.",
 createdAt: now,
 },
 {
 id: "r-lappalainen2024",
 authors: "Lappalainen JK, Tschopp FD, Prakhya S, et al.",
 year: 2024,
 title: "Connectome-constrained networks predict neural activity across the fly visual system",
 venue: "Nature 634, 1132–1140",
 doi: "10.1038/s41586-024-07939-3",
 url: "",
 tags: ["flyvis", "зрение", "дифференцируемая"],
 notes: "Дифференцируемая сеть на коннектоме зрительной системы (flyvis). Сравнение «структура vs обучение».",
 createdAt: now,
 },
];

export const SEED_REFERENCES_EXTRA: Reference[] = [
  {
    id: "r-malecns2026",
    authors: "FlyEM (Janelia), Cambridge Drosophila Connectomics Group, Google Research",
    year: 2026,
    title: "Sexual dimorphism in the complete Drosophila male central nervous system connectome",
    venue: "Cell (препринт: bioRxiv 2025.10.09.680999)",
    doi: "",
    url: "https://www.biorxiv.org/content/10.1101/2025.10.09.680999v2",
    tags: ["коннектом", "самец", "половой диморфизм", "VNC", "оптические доли"],
    notes: "Первый полный коннектом ЦНС самца: мозг, оптические доли и брюшная нервная цепочка, 165 тыс. нейронов, около 12 тыс. типов клеток, 262 полоспецифичных и 114 диморфных типов. Данные: neuPrint male-cns:v1.0 и файлы feather на storage.googleapis.com, лицензия CC-BY 4.0.",
    createdAt: now,
  },
  {
    id: "r-keleman2012",
    authors: "Keleman K, Vrontou E, Kruttner S, et al.",
    year: 2012,
    title: "Dopamine neurons modulate pheromone responses in Drosophila courtship learning",
    venue: "Nature 489, 145-149",
    doi: "10.1038/nature11345",
    url: "",
    tags: ["ухаживание", "память", "дофамин", "MB", "самец"],
    notes: "Классический мужской парадигмальный опыт: неудачное ухаживание учит самца, обучение требует дофаминовых нейронов и рецептора DopR1 в gamma-нейронах MB. Готовая поведенческая рамка для проверки памяти на модели.",
    createdAt: now,
  },
  {
    id: "r-siegel1979",
    authors: "Siegel RW, Hall JC",
    year: 1979,
    title: "Conditioned responses in courtship behavior of normal and mutant Drosophila",
    venue: "PNAS 76, 3430-3434",
    doi: "10.1073/pnas.76.7.3430",
    url: "",
    tags: ["ухаживание", "обусловливание", "память", "история вопроса"],
    notes: "Первое описание обучения при ухаживании: самец, отвергнутый уже спарившейся самкой, снижает ухаживание. Поведенческий baseline для мужской модели.",
    createdAt: now,
  },

 {
 id: "r-danchin2018",
 authors: "Danchin E, Nöbel S, Pocheville A, et al.",
 year: 2018,
 title: "Cultural flies: Conformist social learning in fruitflies predicts long-lasting mate-choice traditions",
 venue: "Science 362, 1025–1030",
 doi: "10.1126/science.aat1590",
 url: "",
 tags: ["социальное обучение", "наблюдение", "поведение"],
 notes: "Дрозофилы копируют выбор партнёра, наблюдая за другими мухами: эмпирическое основание для «обучения через наблюдение». Проверить DOI.",
 createdAt: now,
 },
 {
 id: "r-vogt2016",
 authors: "Vogt K, Aso Y, Hige T, et al.",
 year: 2016,
 title: "Direct neural pathways convey distinct visual information to Drosophila mushroom bodies",
 venue: "eLife 5, e14009",
 doi: "10.7554/eLife.14009",
 url: "",
 tags: ["зрение", "грибовидные тела", "контур"],
 notes: "Зрительные проекционные нейроны идут напрямую в MB: канал, по которому «увиденное» может влиять на обучение наблюдателя.",
 createdAt: now,
 },
 {
 id: "r-felsenberg2018",
 authors: "Felsenberg J, Jacob PF, Walker T, et al.",
 year: 2018,
 title: "Integration of parallel opposing memories underlies memory extinction",
 venue: "Cell 175, 709–722",
 doi: "10.1016/j.cell.2018.08.021",
 url: "",
 tags: ["угасание", "память", "MBON", "дофамин"],
 notes: "Угасание у мухи это не стирание, а параллельная противоположная память. Ключевая рамка для «переучить и вспомнить первое». Проверить DOI.",
 createdAt: now,
 },
 {
 id: "r-lin2014",
 authors: "Lin AC, Bygrave AM, de Calignon A, Lee T, Miesenböck G",
 year: 2014,
 title: "Sparse, decorrelated odor coding in the mushroom body enhances learned odor discrimination",
 venue: "Nat Neurosci 17, 559–568",
 doi: "10.1038/nn.3660",
 url: "",
 tags: ["разреженное кодирование", "APL", "ёмкость"],
 notes: "APL держит код кенйоновых клеток разреженным (~5 %). От этого зависит ёмкость памяти: сколько ассоциаций можно «набить», прежде чем они начнут мешать друг другу.",
 createdAt: now,
 },
 {
 id: "r-bouton2004",
 authors: "Bouton ME",
 year: 2004,
 title: "Context and behavioral processes in extinction",
 venue: "Learn Mem 11, 485–494",
 doi: "10.1101/lm.78804",
 url: "",
 tags: ["психология", "угасание", "спонтанное восстановление", "интерференция"],
 notes: "Классика когнитивной психологии: спонтанное восстановление, renewal, reinstatement: что именно проверяем на мухе. Проверить DOI.",
 createdAt: now,
 },
];

export const SEED_IDEAS: Idea[] = [
 idea({
 id: "i-observational",
 projectId: "p-fly-brain",
 title: "Обучение через наблюдение: муха-демонстратор учит муху-наблюдателя",
 question:
 "Может ли вторая (наивная) муха приобрести ассоциацию «запах → опасность», только наблюдая поведение первой, уже обученной? Какой минимальный контур (зрение → дофаминовые нейроны MB) для этого нужен, и чем такое «зеркальное» обучение отличается от прямого?",
 method: `Две копии одного мозга (демонстратор D и наблюдатель O), общая пластичность в грибовидных телах.

1. Обучить D напрямую: запах A + «удар» через PPL1-дофамин → D избегает A (baseline из идеи MB-обучения).
2. Верхняя граница («телепатия»): скопировать в O дельты весов KC→MBON из D. Проверить, что O избегает A. Это контроль того, что след вообще переносим.
3. Настоящее наблюдение: O получает запах A + ЗРИТЕЛЬНЫЙ вход: паттерн поведения D (резкий поворот/отскок), поданный на LC/зрительные проекционные нейроны в MB (Vogt 2016). Прямого удара O не получает.
 Гипотеза H1: зрительный сигнал «сородич в беде» через существующие входы на DAN даёт слабый учительский сигнал → O формирует ослабленную ассоциацию.
4. Контроли: (a) O видит D без запаха; (b) O нюхает A без D; (c) shuffled-контур от зрения к DAN; (d) D-демонстратор с нейтральным поведением.
5. Метрики: индекс избегания O; сила и скорость обучения vs прямое; какие DAN активируются при наблюдении; сколько «показов» нужно.
6. Расширение: цепочка D → O1 → O2 → … : деградирует ли «культурная» передача «культурная» передача (Danchin 2018).

Честная оговорка: классических зеркальных нейронов у мухи нет; изучаем минимальный механизм социального обучения и то, какой сенсорно-дофаминовой связи ему не хватает в статичном коннектоме.`,
 validation: "Поведенческие данные по социальному обучению дрозофил (mate-copying, Danchin 2018; выбор места кладки, Battesti 2012). Анатомия зрительных входов в MB и на DAN (Vogt 2016, Li 2020 hemibrain MB).",
 venues: ["eLife", "Curr Biol", "PLoS Comp Bio", "Cognitive Science (стык)"],
 timeline: "6–9 месяцев (после MB-обучения)",
 tags: ["social learning", "наблюдение", "зеркальные нейроны", "MB", "dopamine", "две мухи"],
 status: "backlog",
 scores: { effort: 8, impact: 8, novelty: 9, speed: 3, risk: 7 },
 dependsOn: ["i-mb-learning"],
 citations: [
 { refId: "r-danchin2018", why: "Доказательство, что мухи вообще учатся, глядя друг на друга" },
 { refId: "r-vogt2016", why: "Анатомический канал зрение → MB, по которому идёт «наблюдение»" },
 { refId: "r-aso2014", why: "Логика DAN → KC → MBON, куда встраиваем учительский сигнал" },
 ],
 notes: "Самая смелая идея. Даже отрицательный результат («в коннектоме нет пути от зрения к DAN достаточной силы»): публикуемый: показывает, чего не хватает для социального обучения.",
 }),
 idea({
 id: "i-interference",
 projectId: "p-fly-brain",
 title: "Переучить, забить память, вспомнить первое: интерференция и восстановление в MB",
 question:
 "Что происходит со следом первой памяти, когда муху переучивают (угасание/реверс), а потом «набивают» память десятками новых ассоциаций? Стирается след или маскируется? Возвращается ли первое воспоминание само (спонтанное восстановление), по подсказке (reinstatement) или быстрее переучивается (savings)?",
 method: `Фазы протокола (всё на одном мозге с пластичностью KC→MBON под дофамином):

1. Обучение: запах A + удар × N → тест избегания A. Сохранить снимок весов W1.
2. Переучивание, три варианта:
 (a) угасание: A без удара × M;
 (b) реверс: A + награда (PAM-дофамин);
 (c) конкурент: B + удар, A нейтрально.
 Тест A после каждого. Снимок W2.
3. Забить пространство: 20–100 случайных запахов с случайным подкреплением (нагрузка на ёмкость разреженного кода, Lin 2014). Тест A. Снимок W3.
4. Вспомнить первое:
 - спонтанное восстановление: «время» = пассивная релаксация весов к базе, тест A через t;
 - reinstatement: один удар без запаха, затем тест A;
 - savings: повторное обучение A + удар: сколько трайлов до критерия vs наивная муха;
 - renewal: смена «контекста» (фоновая активность / второй канал входа).
5. Анализ на уровне синапсов: сравнить W1, W2, W3 по перекрытию KC-ансамбля A: стёрт след (веса вернулись) или замаскирован (добавлен противоположный след на другой MBON, Felsenberg 2018).
6. Параметры: коэффициент разреженности (сила APL), скорость забывания, число «мусорных» запахов. Карта «когда память выживает».

Сначала игрушечная модель MB на numpy (есть в experiments/templates), затем перенос на реальный контур из коннектома.`,
 validation: "Психология памяти у человека и грызунов: Bouton 2004 (спонтанное восстановление, renewal); у мухи это Felsenberg 2017/2018 (угасание как параллельная память), реверсивное обучение, ёмкость MB (Lin 2014).",
 venues: ["eLife", "PLoS Comp Bio", "Learn Mem", "Neurobiol Learn Mem"],
 timeline: "4–6 месяцев (после MB-обучения; игрушечная версия занимает недели)",
 tags: ["память", "интерференция", "угасание", "spontaneous recovery", "MB", "ёмкость", "когнитивистика"],
 status: "exploring",
 scores: { effort: 6, impact: 8, novelty: 7, speed: 5, risk: 4 },
 dependsOn: ["i-mb-learning"],
 citations: [
 { refId: "r-bouton2004", why: "Определения: угасание, спонтанное восстановление, renewal, savings" },
 { refId: "r-felsenberg2018", why: "Угасание у мухи = параллельная противоположная память: главная гипотеза «маскировки»" },
 { refId: "r-lin2014", why: "Разреженность кода и ёмкость: что значит «забить пространство»" },
 { refId: "r-aso2014", why: "Компартменты MB, где живут противоположные следы" },
 ],
 notes: "Прямой мост между когнитивной психологией памяти и синапсами. Игрушечная модель уже лежит в experiments/templates/mb_toy_interference.py: можно запускать сегодня, без скачивания коннектома.",
 }),
 idea({
 id: "i-lesions",
 projectId: "p-fly-brain",
 title: "Виртуальные лезии: карта необходимости областей мозга",
 question:
 "Какие области / типы клеток необходимы для конкретных сенсомоторных преобразований (вкус → питание, механосенсорика → груминг)?",
 method: `1. Воспроизвести 1–2 фигуры Shiu et al. (Brian2, CPU): baseline.
2. По очереди «выключать» нейропили из аннотаций FlyWire (AVLP, GNG, MB, CX…): занулять спайки.
3. Мерить деградацию readout мотонейронов: точность, частота, доза-эффект (25/50/100 %).
4. Матрица «область × поведение». Бонус: двойные лезии покажут избыточность или компенсацию.`,
 validation: "Литература по инактивации/лезиям у дрозофилы (десятилетия данных). Совпало: валидация. Не совпало: граница LIF-приближения.",
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
 citations: [
 { refId: "r-shiu2024", why: "Baseline: воспроизводим фигуры, берём протоколы стимуляции" },
 { refId: "r-schlegel2024", why: "Границы нейропилей и типы клеток для лезий" },
 { refId: "r-eckstein2024", why: "Откуда знаки синапсов: учитывать при интерпретации" },
 ],
 experiments: [
 {
 id: "e-seed-1",
 date: now.slice(0, 10),
 title: "Пример записи: установка окружения",
 params: "conda env fly-brain, python 3.11, brian2 2.8, numpy 1.26",
 result: "Окружение поднялось, тест-скрипт Brian2 отработал.",
 conclusion: "Следующий шаг: клонировать philshiu/Drosophila_brain_model и запустить пример стимуляции вкусовых нейронов.",
 outcome: "success",
 createdAt: now,
 },
 ],
 }),
 idea({
 id: "i-mb-learning",
 projectId: "p-fly-brain",
 title: "Обучение в грибовидных телах внутри целого мозга",
 question:
 "Можно ли получить ассоциативное обучение (запах + наказание → избегание), добавив дофамин-модулируемую пластичность в MB, и чтобы работало внутри полносвязной модели, а не в изолированном контуре?",
 method: `1. Выделить контур KC → APL → MBON по аннотациям типов клеток.
2. Добавить STDP + дофаминовый сигнал через PPL1 (как в DOOMFLY).
3. Протокол: запах A + наказание, запах B без → сдвиг readout к избеганию A. Кривые обучения, забывание, обобщение.
4. Контроль: shuffled connectome: учит ли именно структура.`,
 validation: "Кривые обусловливания у живых мух (Tully & Quinn, Aso et al.).",
 venues: ["eLife", "Nat Commun", "PLoS Comp Bio"],
 timeline: "4–7 месяцев",
 tags: ["plasticity", "STDP", "mushroom body", "learning"],
 status: "backlog",
 scores: { effort: 7, impact: 8, novelty: 7, speed: 4, risk: 5 },
 notes: "Пластичность в большой сети капризна: может всё перевозбудить или погасить. Вторая статья.",
 dependsOn: ["i-lesions"],
 citations: [
 { refId: "r-aso2014", why: "Архитектура MB и логика дофаминового подкрепления" },
 { refId: "r-shiu2024", why: "Основа модели, в которую встраиваем пластичность" },
 ],
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
 notes: "Рамку «что считать фенотипом» придётся придумывать самому. Если получится, это самая цитируемая работа.",
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
 citations: [{ refId: "r-shiu2024", why: "Эталон Brian2 CPU, с которым сравниваем бэкенды" }],
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
 notes: "Мостик к акустической коммуникации. Модели JO в симуляции нет, придётся достраивать.",
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
 validation: "Только внутренняя (модельные контроли): биологических данных PCI у мухи нет.",
 venues: ["Neurosci Conscious", "PLoS Comp Bio"],
 timeline: "3–4 месяца",
 tags: ["consciousness", "PCI", "IIT", "теория"],
 status: "parked",
 scores: { effort: 5, impact: 5, novelty: 8, speed: 5, risk: 6 },
 notes: "Осторожно с формулировками: не «есть ли сознание», а операциональные меры.",
 }),
  idea({
    id: "i-courtship-memory",
    projectId: "p-fly-brain",
    title: "Память отвергнутого самца: ухаживание, отказ и угасание в полном коннектоме самца",
    question:
      "Можно ли воспроизвести обучение при ухаживании (самец, отвергнутый самкой, снижает ухаживание) на полном коннектоме самца MaleCNS: какие дофаминовые входы в MB несут учительский сигнал, и как эта память угасает и восстанавливается по сравнению с обонятельной?",
    method: `1. Данные: MaleCNS v1.0 (neuPrint, файлы feather), нейроны MB, DAN и MBON по аннотациям типов; проверка, что в мужском коннектоме те же классы, что в FlyWire v783.
2. Сборка LIF-модели на мужском коннектоме: перенести загрузчик fly-brain (Completeness + Connectivity) на таблицы MaleCNS, знаки синапсов взять из предсказаний нейромедиатора.
3. Протокол обучения при ухаживании: стимул «самка» (cVA через Or67d, зрительный вход) + наказание через PPL1-класс -> подавление ухаживания. Сравнить кривую обучения с обонятельной задачей (запах + удар).
4. Угасание и восстановление: повторные предъявления без наказания, затем спонтанное восстановление, reinstatement и savings. Сравнить с женским мозгом v783: различаются ли кривые и какие типы клеток за это отвечают.
5. Анализ диморфизма: пересечь найденные контуры со списком 262 полоспецифичных и 114 диморфных типов клеток.`,
    validation:
      "Поведение: Siegel & Hall 1979 (обучение при ухаживании), Keleman 2012 (дофамин и DopR1 в gamma-MB). Анатомия: аннотации MaleCNS и FlyWire v783.",
    venues: ["Nature Communications", "eLife", "Curr Biol"],
    timeline: "6-9 месяцев (перенос загрузчика занимает 1-3 месяца)",
    tags: ["ухаживание", "память", "MB", "дофамин", "коннектом самца", "половой диморфизм"],
    status: "backlog",
    scores: { effort: 8, impact: 8, novelty: 8, speed: 4, risk: 6 },
    dependsOn: ["i-interference", "i-mb-learning"],
    citations: [
      { refId: "r-malecns2026", why: "Собственно данные и сравнение полов" },
      { refId: "r-keleman2012", why: "Поведенческая парадигма и роль дофамина" },
      { refId: "r-siegel1979", why: "Исторический baseline задачи" },
      { refId: "r-felsenberg2018", why: "Рамка угасания как параллельной памяти" },
    ],
    notes:
      "Две публикации в одной: (а) методическая, если перенос модели на мужской коннектом получится и будет выложен код; (б) биологическая, если кривые обучения и угасания у полов разойдутся. Начинать с задачи (а), она полезна и при отрицательном биологическом результате. Количественная цель из Siegel & Hall 1979: у дикого типа память об ухаживании держится 2-3 часа, у мутанта amnesiac угасает меньше чем за час. Если модель воспроизводит порядок этих времён, у неё есть шанс на биологическую часть.",
  }),
  idea({
    id: "i-memory-to-action",
    projectId: "p-fly-brain",
    title: "От памяти к движению: моторный выход вместо декодированного readout",
    question:
      "Можно ли в модели читать последствия обучения не с MBON, а с моторных нейронов брюшной нервной цепочки: меняется ли рисунок движения после обучения, и видно ли память в мотонейронах раньше или позже, чем в MBON?",
    method: `1. Данные: MaleCNS v1.0 целиком, включая VNC и сохранённый шейный коннектор (мозг и цепочка в одном препарате).
2. Стимул (запах или зрительная сцена) подаётся в мозг, снимаем активность моторных нейронов VNC: поворот, ходьба, отскок.
3. Повторить протокол игрушечной MB-модели (обучение, переучивание, интерференция) уже на полном контуре.
4. Метрики: вектор «моторного ответа» на запах A до и после обучения; сравнить время появления следа в MBON и в мотонейронах; проверить избыточность (сколько мотонейронов нужно, чтобы прочитать память).
5. Контроль: усечённая или shuffled-цепочка: остаётся ли связь обучения с движением.`,
    validation:
      "Анатомия VNC и шейного коннектора MaleCNS; классические карты нисходящих нейронов дрозофилы (DN-классы) и работы по инактивации областей.",
    venues: ["eLife", "PLoS Comput Biol", "Cell Reports"],
    timeline: "4-6 месяцев (после сборки модели MaleCNS)",
    tags: ["VNC", "мотонейроны", "поведение", "коннектом самца", "чтение памяти"],
    status: "backlog",
    scores: { effort: 7, impact: 7, novelty: 8, speed: 5, risk: 5 },
    dependsOn: ["i-courtship-memory", "i-interference"],
    citations: [
      { refId: "r-malecns2026", why: "Цепочка и моторные нейроны в том же препарате, что мозг" },
      { refId: "r-felsenberg2018", why: "Что должно меняться в MBON после угасания" },
    ],
    notes:
      "Сильная сторона: поведенческий выход честнее «декодированного» избегания, которое мы считаем сейчас. Слабая: моторный контур требует больше настроек, чем MB, и результат зависит от стимула.",
  }),
];

export const SEED_STATE: AppState = {
 version: 1,
 projects: SEED_PROJECTS,
 ideas: SEED_IDEAS,
 references: [...SEED_REFERENCES, ...SEED_REFERENCES_EXTRA],
};
