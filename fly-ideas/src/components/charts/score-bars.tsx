import type { IdeaScores } from "@/data/types";
import { SCORE_LABELS } from "@/data/types";

/**
 * Оценки одной идеи. Цвет один: заливка означает «больше значит лучше»,
 * контур для трудоёмкости и риска, где больше значит хуже.
 */
const HOLLOW: (keyof IdeaScores)[] = ["effort", "risk"];

export function ScoreBars({ scores, compact }: { scores: IdeaScores; compact?: boolean }) {
  const keys = Object.keys(SCORE_LABELS) as (keyof IdeaScores)[];
  return (
    <div className={compact ? "grid grid-cols-2 gap-x-5 gap-y-1" : "flex flex-col gap-1.5"}>
      {keys.map((k) => (
        <div key={k} className="flex items-center gap-2">
          <span className={(compact ? "w-20" : "w-28") + " shrink-0 truncate text-[11px] text-muted-foreground"}>{SCORE_LABELS[k]}</span>
          <span className="h-2 min-w-0 flex-1 border border-border">
            {HOLLOW.includes(k) ? (
              <span className="block h-full border-r-2 border-foreground" style={{ width: `${scores[k] * 10}%` }} />
            ) : (
              <span className="block h-full bg-foreground" style={{ width: `${scores[k] * 10}%` }} />
            )}
          </span>
          <span className="w-5 shrink-0 text-right font-mono text-[11px]">{scores[k]}</span>
        </div>
      ))}
    </div>
  );
}
