import type { Idea, ResearchStageId } from "@/data/types";
import { RESEARCH_STAGES, researchProgress } from "@/data/types";

export function ResearchProgress({ idea, onUpdateIdea }: { idea: Idea; onUpdateIdea: (id: string, patch: Partial<Idea>) => void }) {
  const progress = researchProgress(idea);
  const update = (id: ResearchStageId, patch: { done?: boolean; evidence?: string; doneAt?: string | null }) => {
    const stages = idea.researchProgress ?? {};
    const previous = stages[id] ?? { done: false, evidence: "" };
    onUpdateIdea(idea.id, { researchProgress: { ...stages, [id]: { ...previous, ...patch } } });
  };
  return <details className="border-t" open>
    <summary className="cursor-pointer px-2 py-1.5 text-[10.5px]">
      <span className="font-medium">Научный прогресс</span><span className="ml-2 font-mono text-muted-foreground">{progress.done}/{progress.total} · {progress.pct}%</span>
    </summary>
    <div className="border-t px-2 py-1.5">
      <p className="mb-1.5 text-[10px] text-muted-foreground">Самооценка по этой идее, не доказательство результата. Отмечайте этапы вручную и указывайте основание. Прежние этапы статьи сохранены отдельно.</p>
      {RESEARCH_STAGES.map((stage, index) => {
        const value = idea.researchProgress?.[stage.id];
        const done = value?.done === true;
        return <div key={stage.id} className="border-t py-1.5">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[10px] text-muted-foreground">0{index + 1}</span>
            <span className="min-w-0 flex-1 text-[11px]">{stage.label}</span>
            <button type="button" className="border px-1.5 py-0.5 font-mono text-[10px] cursor-pointer hover:bg-accent" aria-label={`${stage.label}: ${done ? "отмечено" : "не отмечено"}`} onClick={() => update(stage.id, { done: !done, doneAt: !done ? new Date().toISOString() : null })}>{done ? "отмечено" : "не отмечено"}</button>
          </div>
          <div className="mt-1 text-[10px] text-muted-foreground">{stage.description}</div>
          <textarea aria-label={`Основание: ${stage.label}`} value={value?.evidence ?? ""} onChange={(e) => update(stage.id, { evidence: e.target.value })} placeholder="Источник, файл, результат или ограничение" className="mt-1 w-full resize-y border bg-background px-1.5 py-1 text-[10px]" rows={2} />
        </div>;
      })}
    </div>
  </details>;
}
