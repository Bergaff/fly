import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis, ReferenceArea, ReferenceLine } from "recharts";
import type { Idea } from "@/data/types";
import { STATUS_COLORS, STATUS_LABELS, STATUS_ORDER } from "@/data/types";

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
    <div className="flex flex-col gap-2">
      <div className="h-[320px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 12, bottom: 20, left: 0 }}>
            <ReferenceArea x1={1} x2={5.5} y1={5.5} y2={10} fill="var(--chart-2)" fillOpacity={0.07} stroke="none" />
            <CartesianGrid stroke="var(--border)" strokeDasharray="1 3" />
            <XAxis
              type="number"
              dataKey="x"
              name="Трудоёмкость"
              domain={[1, 10]}
              tickCount={10}
              tick={{ fill: "var(--muted-foreground)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              label={{ value: "трудоёмкость", position: "insideBottomRight", offset: -12, fill: "var(--muted-foreground)", fontSize: 10, fontFamily: "var(--font-mono)" }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Влияние"
              domain={[1, 10]}
              tickCount={10}
              tick={{ fill: "var(--muted-foreground)", fontSize: 10, fontFamily: "var(--font-mono)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--border)" }}
              width={26}
              label={{ value: "влияние", angle: -90, position: "insideLeft", fill: "var(--muted-foreground)", fontSize: 10, fontFamily: "var(--font-mono)" }}
            />
            <ZAxis type="number" dataKey="z" range={[20, 160]} name="Новизна" />
            <ReferenceLine x={5.5} stroke="var(--border)" />
            <ReferenceLine y={5.5} stroke="var(--border)" />
            <Tooltip
              cursor={{ stroke: "var(--muted-foreground)", strokeDasharray: "2 2" }}
              content={({ payload }) => {
                const p = payload?.[0]?.payload as (typeof data)[number] | undefined;
                if (!p) return null;
                return (
                  <div className="max-w-[260px] border bg-popover px-2 py-1.5">
                    <div className="text-[12px] leading-snug text-foreground">{p.title}</div>
                    <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.05em] text-muted-foreground">
                      трудоёмкость {p.x}, влияние {p.y}, новизна {p.z}
                    </div>
                    <div className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.05em] text-muted-foreground">{STATUS_LABELS[p.status]}</div>
                  </div>
                );
              }}
            />
            <Scatter
              data={data}
              isAnimationActive={false}
              onClick={(d) => onSelect?.((d as unknown as { id: string }).id)}
              shape={(props: unknown) => {
                const { cx, cy, payload } = props as { cx: number; cy: number; payload: (typeof data)[number] };
                const r = 3.5 + payload.z * 0.55;
                return (
                  <g className="cursor-pointer">
                    <circle cx={cx} cy={cy} r={r} fill={payload.fill} fillOpacity={0.75} stroke="var(--background)" strokeWidth={1} />
                  </g>
                );
              }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        {STATUS_ORDER.map((s) => (
          <span key={s} className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.05em] text-muted-foreground">
            <span className="size-2" style={{ background: STATUS_COLORS[s] }} />
            {STATUS_LABELS[s]}
          </span>
        ))}
      </div>
    </div>
  );
}
