import type { Idea } from "@/data/types";

/** Сводный приоритет: влияние и новизна минус трудоёмкость и риск. */
export function priorityOf(i: Idea): number {
  const v = i.scores.impact * 0.4 + i.scores.novelty * 0.25 + i.scores.speed * 0.2 - i.scores.effort * 0.1 - i.scores.risk * 0.15;
  return Math.round(v * 10) / 10;
}
