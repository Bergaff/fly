import type { Idea } from "@/data/types";
import { checklistProgress } from "@/data/types";

/** Шкала готовности: десять делений, заливка показывает закрытые этапы. */
export function ReadinessMeters({ ideas, onSelect, limit = 6 }: { ideas: Idea[]; onSelect?: (id: string) => void; limit?: number }) {
  const list = [...ideas].sort((a, b) => checklistProgress(b).pct - checklistProgress(a).pct || b.updatedAt.localeCompare(a.updatedAt)).slice(0, limit);
  if (list.length === 0) return <p className="py-6 text-center text-[12px] text-muted-foreground">Нет идей.</p>;

  return (
    <div className="flex flex-col border-t">
      {list.map((i) => {
        const prog = checklistProgress(i);
        const filled = Math.round(prog.pct / 10);
        return (
          <button key={i.id} onClick={() => onSelect?.(i.id)} className="flex items-center gap-3 border-b py-2 text-left last:border-b-0 hover:bg-accent cursor-pointer">
            <span className="min-w-0 flex-1 truncate text-[12px]">{i.title}</span>
            <span className="flex shrink-0 gap-[2px]">
              {Array.from({ length: 10 }, (_, k) => (
                <span key={k} className="h-3 w-2 border border-border" style={{ background: k < filled ? "var(--foreground)" : "transparent" }} />
              ))}
            </span>
            <span className="w-16 shrink-0 text-right font-mono text-[10px] text-muted-foreground">
              {prog.done}/{prog.total}, {prog.pct}%
            </span>
          </button>
        );
      })}
    </div>
  );
}
