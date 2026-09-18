import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis, ReferenceArea, ReferenceLine } from "recharts";
import type { Idea } from "@/data/types";
import { STATUS_COLORS, STATUS_LABELS } from "@/data/types";

interface Props {
  ideas: Idea[];
  onSelect?: (id: string) => void;
}

export function EffortImpactChart({ ideas, onSelect }: Props) {
  const data = ideas.map((i) => ({
    id: i.id,
    x: i.scores.effort,
    y: i.scores.impact,
    z: i.scores.novelty,
    title: i.title,
    status: i.status,
    fill: STATUS_COLORS[i.status],
  }));

  return (
    <div className="h-[340px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
          <defs>
            <linearGradient id="quad-good" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="var(--chart-2)" stopOpacity={0.18} />
              <stop offset="100%" stopColor="var(--chart-2)" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <ReferenceArea x1={1} x2={5.5} y1={5.5} y2={10} fill="url(#quad-good)" stroke="none" />
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis type="number" dataKey="x" name="Трудоёмкость" domain={[1, 10]} tickCount={10} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} axisLine={false} tickLine={false} label={{ value: "Трудоёмкость →", position: "insideBottomRight", offset: -8, fill: "var(--muted-foreground)", fontSize: 11 }} />
          <YAxis type="number" dataKey="y" name="Влияние" domain={[1, 10]} tickCount={10} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} axisLine={false} tickLine={false} width={28} label={{ value: "Влияние ↑", angle: -90, position: "insideLeft", fill: "var(--muted-foreground)", fontSize: 11 }} />
          <ZAxis type="number" dataKey="z" range={[80, 420]} name="Новизна" />
          <ReferenceLine x={5.5} stroke="var(--border)" strokeDasharray="4 4" />
          <ReferenceLine y={5.5} stroke="var(--border)" strokeDasharray="4 4" />
          <Tooltip
            cursor={{ strokeDasharray: "3 3", stroke: "var(--muted-foreground)" }}
            content={({ payload }) => {
              const p = payload?.[0]?.payload as (typeof data)[number] | undefined;
              if (!p) return null;
              return (
                <div className="rounded-lg border bg-popover/95 px-3 py-2 text-xs shadow-md backdrop-blur">
                  <div className="font-medium text-foreground max-w-[220px]">{p.title}</div>
                  <div className="mt-1 text-muted-foreground">
                    Трудоёмкость {p.x} · Влияние {p.y} · Новизна {p.z}
                  </div>
                  <div className="mt-0.5 flex items-center gap-1.5 text-muted-foreground">
                    <span className="size-2 rounded-full" style={{ background: p.fill }} />
                    {STATUS_LABELS[p.status]}
                  </div>
                </div>
              );
            }}
          />
          <Scatter
            data={data}
            onClick={(d) => onSelect?.((d as unknown as { id: string }).id)}
            shape={(props: unknown) => {
              const { cx, cy, payload } = props as { cx: number; cy: number; payload: (typeof data)[number] };
              const r = 6 + payload.z * 1.1;
              return (
                <g className="cursor-pointer">
                  <circle cx={cx} cy={cy} r={r + 6} fill={payload.fill} opacity={0.12} />
                  <circle cx={cx} cy={cy} r={r} fill={payload.fill} opacity={0.85} stroke="var(--background)" strokeWidth={2} />
                </g>
              );
            }}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
