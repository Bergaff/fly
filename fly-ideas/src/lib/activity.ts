import type { Idea } from "@/data/types";

export interface DayCell {
  iso: string;
  label: string;
  n: number;
}

const pad = (n: number) => String(n).padStart(2, "0");
const isoOf = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;

/**
 * Все действия по идеям: записи журнала (по дате опыта) и закрытые этапы (по дате галочки).
 */
function tally(ideas: Idea[]): Map<string, number> {
  const counts = new Map<string, number>();
  const bump = (iso: string) => counts.set(iso, (counts.get(iso) ?? 0) + 1);
  ideas.forEach((i) => {
    i.experiments.forEach((e) => e.date && bump(e.date));
    i.checklist.forEach((c) => c.doneAt && bump(c.doneAt.slice(0, 10)));
  });
  return counts;
}

/** Сетка календаря: недели слева направо, начиная с понедельника. */
export function activityGrid(ideas: Idea[], weeks = 14) {
  const counts = tally(ideas);
  const today = new Date();
  const end = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const monday = new Date(end);
  monday.setDate(monday.getDate() - ((end.getDay() + 6) % 7));
  const start = new Date(monday);
  start.setDate(start.getDate() - (weeks - 1) * 7);

  const columns: DayCell[][] = [];
  const cursor = new Date(start);
  while (cursor <= end) {
    const col: DayCell[] = [];
    for (let d = 0; d < 7; d++) {
      const day = new Date(cursor);
      day.setDate(day.getDate() + d);
      const iso = isoOf(day);
      col.push({ iso, label: day.toLocaleDateString("ru-RU", { day: "numeric", month: "long" }), n: day <= end ? counts.get(iso) ?? 0 : -1 });
    }
    columns.push(col);
    cursor.setDate(cursor.getDate() + 7);
  }

  const values = columns.flat().map((c) => Math.max(0, c.n));
  return {
    columns,
    max: Math.max(1, ...values),
    total: values.reduce((a, b) => a + b, 0),
    activeDays: values.filter((v) => v > 0).length,
  };
}

/** Число действий по неделям, старые слева. */
export function activityPerWeek(ideas: Idea[], weeks = 12): number[] {
  const grid = activityGrid(ideas, weeks);
  return grid.columns.map((col) => col.reduce((a, c) => a + Math.max(0, c.n), 0));
}
