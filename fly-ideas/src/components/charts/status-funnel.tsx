import type { Idea } from "@/data/types";
import { STATUS_COLORS, STATUS_LABELS, STATUS_ORDER } from "@/data/types";

/**
 * Воронка пути: ступени сужаются по числу идей, поверх заливки лежит штриховка.
 */
export function StatusFunnel({ ideas }: { ideas: Idea[] }) {
  const counts = STATUS_ORDER.map((s) => ({ status: s, n: ideas.filter((i) => i.status === s).length }));
  const total = Math.max(1, ideas.length);
  const max = Math.max(1, ...counts.map((c) => c.n));
  const ROW = 26;
  const GAP = 4;
  const TOP = 26;
  const width = 260;
  const height = TOP + counts.length * (ROW + GAP);
  const widthOf = (n: number) => Math.max(6, (n / max) * width);

  return (
    <div className="flex flex-col gap-2">
      <svg width="100%" height={height} viewBox={`0 0 ${width + 200} ${height}`} preserveAspectRatio="xMinYMin meet" role="img" aria-label="Воронка статусов">
        <defs>
          <pattern id="funnel-hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="5" stroke="var(--background)" strokeWidth="1" strokeOpacity="0.55" />
          </pattern>
        </defs>
        {counts.map((c, i) => {
          const top = TOP + i * (ROW + GAP);
          const wTop = widthOf(c.n);
          const wBottom = widthOf(counts[i + 1]?.n ?? c.n * 0.7);
          const xTop = (width - wTop) / 2;
          const xBottom = (width - wBottom) / 2;
          const path = `M ${xTop} ${top} L ${xTop + wTop} ${top} L ${xBottom + wBottom} ${top + ROW} L ${xBottom} ${top + ROW} Z`;
          return (
            <g key={c.status}>
              <path d={path} fill={c.n ? STATUS_COLORS[c.status] : "transparent"} fillOpacity={c.n ? 0.85 : 1} stroke="var(--border)" strokeWidth="1" />
              {c.n > 0 && <path d={path} fill="url(#funnel-hatch)" stroke="none" />}
              <text x={width + 12} y={top + ROW / 2 + 3} className="font-mono" fontSize="10" letterSpacing="0.06em" fill="var(--muted-foreground)">
                {STATUS_LABELS[c.status].toUpperCase()}
              </text>
              <text x={width + 148} y={top + ROW / 2 + 3} textAnchor="end" className="font-mono" fontSize="10" fill="var(--foreground)">
                {c.n}
              </text>
              <text x={width + 196} y={top + ROW / 2 + 3} textAnchor="end" className="font-mono" fontSize="10" fill="var(--muted-foreground)">
                {Math.round((c.n / total) * 100)}%
              </text>
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="label">всего идей: {ideas.length}</span>
        <span className="label">в работе: {ideas.filter((i) => ["exploring", "active", "drafting"].includes(i.status)).length}</span>
      </div>
    </div>
  );
}
