import type { Idea, ResearchStageId, ResearchStageState } from "@/data/types";

const STUDY = "Study_20261102_135659_26e34eaf";
type Update = { evidence: string; completed: boolean };
const updates: Record<string, Partial<Record<ResearchStageId, Update>>> = {
  "i-individuality": {
    observation: { completed: true, evidence: `v630 ${STUDY}: 10 искусственных вариантов весов ±5%, 50 Гц, 1 с; обнаружены различия средних MN9. Это не животные и не поведение.` },
    reproduction: { completed: true, evidence: `v630 ${STUDY}: 100 исходных и 100 новых повторов, 10 вариантов × 20 seed; ранговая корреляция средних левого MN9 для seed 0–9 и 10–19: 0,657. Порядок воспроизвёлся частично.` },
    interpretation: { completed: true, evidence: `v630 ${STUDY}: вариант 10 выше 9 в среднем на новых seed на 4,2 Гц; пара выбрана после просмотра первой серии. Вариант 5 изменил положение. Одноимённый seed не гарантирует одинакового входа; доля индивидуальности не оценена.` },
    verification: { completed: false, evidence: `v630 ${STUDY}: проверены новые seed 10–19 и отдельные контроли. Одна модель, одна частота и искусственные веса; биологическая реалистичность и устойчивый фенотип не подтверждены. Нужны дополнительные независимые условия.` },
  },
  "i-lesions": {
    observation: { completed: true, evidence: `v630 ${STUDY}: контроль 50 Гц, 30 seed; левый MN9 19,10 ± 6,48 Гц, правый 14,17 ± 5,00 Гц (SD).` },
    reproduction: { completed: false, evidence: `v630 ${STUDY}: по последнему сообщённому состоянию готовы 30 контролей и 300 одиночных лезий, всего 330/510; 180 парных и групповых повторов ещё оставались. Текущее состояние может отличаться.` },
    interpretation: { completed: false, evidence: `v630 ${STUDY}: ранг 22 показал 155,3% среднего контроля слева, ранг 62: 68,4% при 50 Гц. Порог 80% не является тестом значимости; это не проверка всех частот.` },
    verification: { completed: false, evidence: `v630 ${STUDY}: сохранены 30 контрольных seed и проверки данных. Одинаковые номера seed не гарантируют идентичные входы. Выборочные лезии не доказывают необходимость клеток у животного.` },
  },
};

export function v630EvidenceAvailable(ideaId: string): boolean { return !!updates[ideaId]; }

/** Explicit import only: preserve existing notes and marks; repeat imports are idempotent. */
export function addV630Evidence(idea: Idea): Idea["researchProgress"] {
  const found = updates[idea.id];
  if (!found) return idea.researchProgress;
  const result = { ...(idea.researchProgress ?? {}) };
  for (const [key, item] of Object.entries(found) as [ResearchStageId, Update][]) {
    const old: ResearchStageState = result[key] ?? { done: false, evidence: "" };
    const evidence = old.evidence.includes(item.evidence) ? old.evidence : [old.evidence.trim(), item.evidence].filter(Boolean).join("\n\n");
    result[key] = { ...old, done: old.done || item.completed, evidence };
  }
  return result;
}
