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
  if (idea.id === "i-lesions") {
    const extra = `v630 ${STUDY}: обновление после сообщения о 330/510: завершены 510/510 повторов при 50 Гц: контроль, 10 одиночных лезий, 5 пар и группа; по 30 seed. Левый MN9: контроль 19,10 Гц, лезия ранга 22: 29,67 Гц, ранга 62: 13,07 Гц. Пары и группа описательны; это не биологическая верификация и не результат на всех частотах.`;
    const stage = result.reproduction!;
    if (!stage.evidence.includes(extra)) result.reproduction = { ...stage, evidence: [stage.evidence.trim(), extra].filter(Boolean).join("\n\n") };
  }
  if (idea.id === "i-individuality") {
    const extra = `v630 ${STUDY}, итог 20 seed: 200 повторов; контроль слева 18,20 Гц, среднее вариантов 18,92 Гц. Вариант 10 минус 9: 5,65 Гц, выше в 18/20 случаев; пара выбрана после просмотра первой серии. Это описание модельного эксперимента, не доказательство биологической индивидуальности.`;
    const stage = result.interpretation!;
    if (!stage.evidence.includes(extra)) result.interpretation = { ...stage, evidence: [stage.evidence.trim(), extra].filter(Boolean).join("\n\n") };
  }
  return result;
}

/** Отмечает только совпадающие стандартные этапы; пользовательские пункты не меняются. */
export function addV630Checklist(idea: Idea, at = new Date().toISOString()): Idea["checklist"] {
  if (!v630EvidenceAvailable(idea.id)) return idea.checklist;
  const completed = new Set([
    "Поднять окружение (conda, Brian2 / fly-brain)",
    "Написать протокол эксперимента",
    "Сделать прогоны, сохранить сырые данные и сиды",
  ]);
  return idea.checklist.map((item) => !item.done && completed.has(item.text)
    ? { ...item, done: true, doneAt: at }
    : item);
}
