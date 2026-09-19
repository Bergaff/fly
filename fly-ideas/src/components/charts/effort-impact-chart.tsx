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
    s: i.scores.speed,
    r: i.scores.risk,
    title: i.title,
    status: i.status,
    fill: STATUS_COLORS[i.status],
  }));

  return (
    <div className="flex flex-col gap-2">
      <div className="h-[320px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 12, bottom: 20, left: 0 }}>
            <defs>
              {/* зона «мало усилий, много пользы» размечена штриховкой, без заливки-градиента */}
              <pattern id="quick-zone" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                <line x1="0" y1="0" x2="0" y2="6" stroke="var(--muted-foreground)" strokeWidth="1" strokeOpacity="0.35" />
              </pattern>
            </defs>
            <ReferenceArea x1={1} x2={5.5} y1={5.5} y2={10} fill="url(#quick-zone)" stroke="none" />
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
                  <div className="w-[240px] border bg-popover p-2">
                    <div className="text-[12px] leading-snug text-foreground">{p.title}</div>
                    <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1">
                      {[
                        ["трудоёмкость", p.x],
                        ["влияние", p.y],
                        ["новизна", p.z],
                        ["скорость", p.s],
                        ["риск", p.r],
                      ].map(([k, v]) => (
                        <span key={String(k)} className="flex items-baseline justify-between gap-2">
                          <span className="font-mono text-[9px] uppercase tracking-[0.06em] text-muted-foreground">{k}</span>
                          <span className="font-mono text-[11px] text-foreground">{v}</span>
                        </span>
                      ))}
                    </div>
                    <div className="mt-1.5 flex items-center gap-1.5 border-t pt-1.5">
                      <span className="size-2" style={{ background: p.fill }} />
                      <span className="font-mono text-[9px] uppercase tracking-[0.06em] text-muted-foreground">{STATUS_LABELS[p.status]}</span>
                    </div>
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
                    <rect x={cx - r} y={cy - r} width={r * 2} height={r * 2} fill={payload.fill} fillOpacity={0.2} />
                    <rect x={cx - r / 2} y={cy - r / 2} width={r} height={r} fill={payload.fill} />
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
        <span className="label ml-auto">штриховка: зона быстрых побед</span>
      </div>
    </div>
  );
}
