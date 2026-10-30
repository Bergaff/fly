import { useMemo } from "react";
import type { Idea } from "@/data/types";
import { STATUS_COLORS, checklistProgress } from "@/data/types";

/**
 * Слоистый граф «растёт из»: идеи без зависимостей слева, дальше по глубине.
 * Чистый SVG, без внешних библиотек.
 */
export function DependencyGraph({ ideas, onSelect, highlight }: { ideas: Idea[]; onSelect?: (id: string) => void; highlight?: string | null }) {
  const layout = useMemo(() => {
    const byId = new Map(ideas.map((i) => [i.id, i]));
    const depth = new Map<string, number>();
    const visit = (id: string, stack: Set<string>): number => {
      if (depth.has(id)) return depth.get(id)!;
      if (stack.has(id)) return 0;
      stack.add(id);
      const i = byId.get(id);
      const parents = (i?.dependsOn ?? []).filter((d) => byId.has(d));
      const d = parents.length ? 1 + Math.max(...parents.map((p) => visit(p, stack))) : 0;
      depth.set(id, d);
      stack.delete(id);
      return d;
    };
    ideas.forEach((i) => visit(i.id, new Set()));

    const columns = new Map<number, Idea[]>();
    ideas.forEach((i) => {
      const d = depth.get(i.id) ?? 0;
      columns.set(d, [...(columns.get(d) ?? []), i]);
    });
    const maxDepth = Math.max(0, ...columns.keys());
    const maxRows = Math.max(1, ...[...columns.values()].map((c) => c.length));

    const W = 220, H = 56, GX = 90, GY = 18, PAD = 16;
    const width = PAD * 2 + (maxDepth + 1) * W + maxDepth * GX;
    const height = PAD * 2 + maxRows * H + (maxRows - 1) * GY;

    const pos = new Map<string, { x: number; y: number }>();
    for (const [d, col] of columns) {
      const colH = col.length * H + (col.length - 1) * GY;
      const y0 = PAD + (height - PAD * 2 - colH) / 2;
      col.forEach((i, r) => pos.set(i.id, { x: PAD + d * (W + GX), y: y0 + r * (H + GY) }));
    }
    const edges: { from: string; to: string }[] = [];
    ideas.forEach((i) => i.dependsOn.forEach((p) => byId.has(p) && edges.push({ from: p, to: i.id })));
    return { pos, edges, width, height, W, H };
  }, [ideas]);

  if (ideas.length === 0) return <div className="py-10 text-center text-[12px] text-muted-foreground">Нет идей.</div>;
  const { pos, edges, width, height, W, H } = layout;
  const hasEdges = edges.length > 0;

  return (
    <div className="overflow-x-auto">
      <svg width={width} height={height} className="mx-auto block" style={{ minWidth: 320 }}>
        <defs>
          <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--muted-foreground)" />
          </marker>
        </defs>
        {edges.map((e, k) => {
          const a = pos.get(e.from)!;
          const b = pos.get(e.to)!;
          const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2;
          const mx = (x1 + x2) / 2;
          const active = highlight && (e.from === highlight || e.to === highlight);
          return (
            <path
              key={k}
              d={`M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`}
              fill="none"
              stroke={active ? "var(--foreground)" : "var(--muted-foreground)"}
              strokeOpacity={active ? 1 : 0.5}
              strokeWidth={1}
              markerEnd="url(#arrow)"
            />
          );
        })}
        {ideas.map((i) => {
          const p = pos.get(i.id)!;
          const prog = checklistProgress(i);
          const active = highlight === i.id;
          return (
            <g key={i.id} transform={`translate(${p.x},${p.y})`} className="cursor-pointer" onClick={() => onSelect?.(i.id)}>
              <rect width={W} height={H} fill="var(--card)" stroke={active ? "var(--foreground)" : "var(--border)"} strokeWidth={1} />
              <foreignObject x={8} y={6} width={W - 16} height={H - 12}>
                <div className="flex h-full flex-col justify-between text-[12px] leading-tight text-foreground">
                  <div className="flex items-start gap-1.5">
                    <span className="mt-1 size-2 shrink-0" style={{ background: STATUS_COLORS[i.status] }} />
                    <span className="line-clamp-2">{i.title}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="h-2 flex-1 border border-border">
                      <span className="block h-full bg-foreground" style={{ width: `${prog.pct}%` }} />
                    </span>
                    <span className="font-mono text-[10px] text-muted-foreground">{prog.pct}%</span>
                  </div>
                </div>
              </foreignObject>
            </g>
          );
        })}
      </svg>
      {!hasEdges && <p className="mt-2 text-center font-mono text-[10px] uppercase tracking-[0.05em] text-muted-foreground">Связей пока нет: задай «растёт из» в диалоге идеи</p>}
    </div>
  );
}
