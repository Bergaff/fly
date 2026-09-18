import type { Idea } from "@/data/types";
import { STATUS_COLORS, STATUS_LABELS, STATUS_ORDER } from "@/data/types";

export function StatusFunnel({ ideas }: { ideas: Idea[] }) {
  const counts = STATUS_ORDER.map((s) => ({ status: s, n: ideas.filter((i) => i.status === s).length }));
  const max = Math.max(1, ...counts.map((c) => c.n));
  return (
    <div className="flex flex-col gap-2">
      {counts.map((c) => (
        <div key={c.status} className="flex items-center gap-3 text-sm">
          <div className="w-28 shrink-0 text-muted-foreground">{STATUS_LABELS[c.status]}</div>
          <div className="relative h-7 flex-1 overflow-hidden rounded-md bg-muted/50">
            <div
              className="h-full rounded-md transition-all duration-500"
              style={{ width: `${(c.n / max) * 100}%`, background: `linear-gradient(90deg, ${STATUS_COLORS[c.status]}, color-mix(in oklch, ${STATUS_COLORS[c.status]} 45%, transparent))`, minWidth: c.n ? 8 : 0 }}
            />
            <span className="absolute inset-y-0 left-2 flex items-center font-mono text-xs text-foreground/90">{c.n || ""}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
