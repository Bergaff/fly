import type { IdeaScores } from "@/data/types";
import { SCORE_LABELS } from "@/data/types";
import { Progress } from "@/components/ui/progress";

const COLORS: Record<keyof IdeaScores, string> = {
  effort: "var(--chart-5)",
  impact: "var(--chart-2)",
  novelty: "var(--chart-4)",
  speed: "var(--chart-1)",
  risk: "var(--chart-3)",
};

export function ScoreBars({ scores, compact }: { scores: IdeaScores; compact?: boolean }) {
  const keys = Object.keys(SCORE_LABELS) as (keyof IdeaScores)[];
  return (
    <div className={compact ? "grid grid-cols-2 gap-x-4 gap-y-1.5" : "flex flex-col gap-2"}>
      {keys.map((k) => (
        <div key={k} className="flex items-center gap-2 text-xs">
          <span className={compact ? "w-20 truncate text-muted-foreground" : "w-28 text-muted-foreground"}>{SCORE_LABELS[k]}</span>
          <Progress value={scores[k] * 10} color={COLORS[k]} className="flex-1" />
          <span className="w-4 text-right font-mono text-muted-foreground">{scores[k]}</span>
        </div>
      ))}
    </div>
  );
}
