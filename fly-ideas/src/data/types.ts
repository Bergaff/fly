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
  parked: "oklch(0.5 0.02 285)",
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
}
