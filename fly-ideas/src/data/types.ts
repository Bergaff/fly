export type IdeaStatus = "backlog" | "exploring" | "active" | "drafting" | "submitted" | "done" | "parked";

export const STATUS_LABELS: Record<IdeaStatus, string> = {
 backlog: "Бэклог",
 exploring: "Изучаю",
 active: "В работе",
 drafting: "Пишу статью",
 submitted: "Подано",
 done: "Опубликовано",
 parked: "Отложено",
};

export const STATUS_ORDER: IdeaStatus[] = ["backlog", "exploring", "active", "drafting", "submitted", "done", "parked"];

export const STATUS_COLORS: Record<IdeaStatus, string> = {
 backlog: "var(--muted-foreground)",
 exploring: "var(--chart-1)",
 active: "var(--chart-2)",
 drafting: "var(--chart-3)",
 submitted: "var(--chart-4)",
 done: "var(--chart-5)",
 parked: "oklch(0.6 0.012 80)",
};

/** Оценки 1–10 */
export interface IdeaScores {
 effort: number; // трудоёмкость (выше = тяжелее)
 impact: number; // научная ценность
 novelty: number; // новизна
 speed: number; // скорость до результата (выше = быстрее)
 risk: number; // риск не получить результат
}

export const SCORE_LABELS: Record<keyof IdeaScores, string> = {
 effort: "Трудоёмкость",
 impact: "Влияние",
 novelty: "Новизна",
 speed: "Скорость",
 risk: "Риск",
};

export interface ChecklistItem {
 id: string;
 text: string;
 done: boolean;
 doneAt?: string | null;
}

/** Стандартный конвейер «от идеи до статьи» */
export const DEFAULT_CHECKLIST: string[] = [
 "Прочитать ключевые статьи по теме",
 "Поднять окружение (conda, Brian2 / fly-brain)",
 "Воспроизвести baseline (фигуры Shiu et al.)",
 "Написать протокол эксперимента",
 "Сделать прогоны, сохранить сырые данные и сиды",
 "Сверить с литературой / валидировать",
 "Черновик статьи",
 "Препринт на bioRxiv",
 "Подача в журнал",
];

export type ExperimentOutcome = "success" | "partial" | "failed" | "inconclusive";

export const OUTCOME_LABELS: Record<ExperimentOutcome, string> = {
 success: "Получилось",
 partial: "Частично",
 failed: "Не получилось",
 inconclusive: "Неясно",
};

export const OUTCOME_COLORS: Record<ExperimentOutcome, string> = {
 success: "var(--chart-2)",
 partial: "var(--chart-3)",
 failed: "var(--chart-5)",
 inconclusive: "var(--muted-foreground)",
};

/** Запись лабораторного журнала */
export interface ExperimentEntry {
 id: string;
 date: string; // YYYY-MM-DD
 title: string; // что запускал
 params: string; // параметры / сид / бэкенд / коммит
 result: string; // что получилось (цифры, файлы)
 conclusion: string; // вывод, что дальше
 outcome: ExperimentOutcome;
 createdAt: string;
}

/** Источник в общей библиографии */
export interface Reference {
 id: string;
 authors: string; // "Shiu PK, Sterne GR, ..."
 year: number | null;
 title: string;
 venue: string; // журнал / конференция / препринт
 doi: string;
 url: string;
 tags: string[];
 notes: string; // общий конспект
 createdAt: string;
}

/** Привязка источника к идее: зачем он тут нужен */
export interface IdeaCitation {
 refId: string;
 why: string;
}

export interface Idea {
 id: string;
 projectId: string;
 title: string;
 question: string; // исследовательский вопрос
 method: string; // метод (markdown-ish текст)
 validation: string; // с чем сверять
 venues: string[]; // журналы/конференции
 timeline: string; // оценка сроков
 tags: string[];
 status: IdeaStatus;
 scores: IdeaScores;
 notes: string;
 links: { label: string; url: string }[];
 checklist: ChecklistItem[];
 deadline: string | null; // YYYY-MM-DD
 dependsOn: string[]; // id идей, из которых «растёт» эта
 experiments: ExperimentEntry[];
 citations: IdeaCitation[];
 createdAt: string;
 updatedAt: string;
}

export interface Project {
 id: string;
 name: string;
 description: string;
 color: string;
 createdAt: string;
}

export interface AppState {
 version: 1;
 projects: Project[];
 ideas: Idea[];
 references: Reference[];
 /** id стартовых идей и источников, которые уже показаны или удалены вручную:
 * по этому списку новые версии набора не возвращают убранное и не дублируют старое */
 seeded?: string[];
}

export function formatReference(r: Reference): string {
 const parts = [r.authors, r.year ? `(${r.year})` : "", r.title ? `${r.title}.` : "", r.venue].filter(Boolean);
 return parts.join(" ");
}

export function referenceLink(r: Reference): string | null {
 if (r.doi) return `https://doi.org/${r.doi.replace(/^https?:\/\/(dx\.)?doi\.org\//i, "")}`;
 return r.url || null;
}

export function checklistProgress(idea: Pick<Idea, "checklist">) {
 const total = idea.checklist.length;
 const done = idea.checklist.filter((c) => c.done).length;
 return { done, total, pct: total ? Math.round((done / total) * 100) : 0 };
}

export type DeadlineTone = "overdue" | "soon" | "ok";

export function deadlineInfo(deadline: string | null | undefined): { days: number; tone: DeadlineTone; label: string; date: string } | null {
 if (!deadline) return null;
 const d = new Date(`${deadline}T00:00:00`);
 if (Number.isNaN(d.getTime())) return null;
 const today = new Date();
 today.setHours(0, 0, 0, 0);
 const days = Math.round((d.getTime() - today.getTime()) / 86_400_000);
 const tone: DeadlineTone = days < 0 ? "overdue" : days <= 14 ? "soon" : "ok";
 const label = days < 0 ? `просрочено на ${-days} дн.` : days === 0 ? "сегодня" : days === 1 ? "завтра" : `через ${days} дн.`;
 return { days, tone, label, date: d.toLocaleDateString("ru-RU") };
}
