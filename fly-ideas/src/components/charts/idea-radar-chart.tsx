import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Legend, Tooltip } from "recharts";
import type { Idea } from "@/data/types";
import { SCORE_LABELS } from "@/data/types";

const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-4)"];

export function IdeaRadarChart({ ideas }: { ideas: Idea[] }) {
  const axes = Object.keys(SCORE_LABELS) as (keyof typeof SCORE_LABELS)[];
  const data = axes.map((k) => {
    const row: Record<string, number | string> = { axis: SCORE_LABELS[k] };
    ideas.forEach((i) => {
      // для сравнения инвертируем "плохие" оси: меньше трудоёмкость и риск = лучше
      const v = k === "effort" || k === "risk" ? 11 - i.scores[k] : i.scores[k];
      row[i.id] = v;
    });
    return row;
  });

  return (
    <div className="h-[380px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--muted-foreground)", fontSize: 12 }} />
          <PolarRadiusAxis domain={[0, 10]} tick={false} axisLine={false} />
          <Tooltip
            content={({ payload, label }) => {
              if (!payload?.length) return null;
              return (
                <div className="rounded-lg border bg-popover/95 px-3 py-2 text-xs shadow-md backdrop-blur">
                  <div className="font-medium">{label}</div>
                  {payload.map((p) => (
                    <div key={String(p.dataKey)} className="mt-1 flex items-center gap-1.5 text-muted-foreground">
                      <span className="size-2 rounded-full" style={{ background: p.color }} />
                      <span className="max-w-[200px] truncate">{p.name}</span>
                      <span className="ml-auto font-mono text-foreground">{p.value}</span>
                    </div>
                  ))}
                  <div className="mt-1 text-[10px] text-muted-foreground/70">Трудоёмкость и риск инвертированы: больше = лучше</div>
                </div>
              );
            }}
          />
          {ideas.map((i, idx) => (
            <Radar key={i.id} name={i.title} dataKey={i.id} stroke={COLORS[idx % COLORS.length]} fill={COLORS[idx % COLORS.length]} fillOpacity={0.18} strokeWidth={2} dot={{ r: 3, fillOpacity: 1 }} />
          ))}
          <Legend wrapperStyle={{ fontSize: 12 }} formatter={(v: string) => <span className="text-muted-foreground">{v.length > 40 ? v.slice(0, 40) + "…" : v}</span>} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
