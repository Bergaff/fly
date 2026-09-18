import type { Idea } from "@/data/types";
import { STATUS_COLORS, STATUS_LABELS, STATUS_ORDER } from "@/data/types";

/** Полосы во всю ширину: плоская заливка, подпись слева, число справа. */
export function StatusFunnel({ ideas }: { ideas: Idea[] }) {
  const counts = STATUS_ORDER.map((s) => ({ status: s, n: ideas.filter((i) => i.status === s).length }));
  const max = Math.max(1, ...counts.map((c) => c.n));
  return (
    <div className="flex flex-col border-t">
      {counts.map((c) => (
        <div key={c.status} className="flex items-center gap-3 border-b py-1.5 text-[12px]">
          <div className="w-28 shrink-0 text-muted-foreground">{STATUS_LABELS[c.status]}</div>
          <div className="relative h-3 flex-1 border border-border">
            <div className="h-full" style={{ width: `${(c.n / max) * 100}%`, background: STATUS_COLORS[c.status] }} />
          </div>
          <div className="w-6 shrink-0 text-right font-mono">{c.n}</div>
        </div>
      ))}
    </div>
  );
}
