import { PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Legend, Tooltip } from "recharts";
import type { Idea } from "@/data/types";
import { SCORE_LABELS } from "@/data/types";

/** Три идеи различаются тоном и штрихом линии, без спектра. */
const STROKES = ["var(--foreground)", "var(--chart-1)", "var(--chart-4)"];

export function IdeaRadarChart({ ideas }: { ideas: Idea[] }) {
  const axes = Object.keys(SCORE_LABELS) as (keyof typeof SCORE_LABELS)[];
  const data = axes.map((k) => {
    const row: Record<string, number | string> = { axis: SCORE_LABELS[k] };
    ideas.forEach((i) => {
      // для сравнения инвертируем «плохие» оси: меньше трудоёмкости и риска значит лучше
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
          <PolarAngleAxis dataKey="axis" tick={{ fill: "var(--muted-foreground)", fontSize: 11, fontFamily: "var(--font-mono)" }} />
          <PolarRadiusAxis domain={[0, 10]} tick={false} axisLine={false} />
          <Tooltip
            content={({ payload, label }) => {
              if (!payload?.length) return null;
              return (
                <div className="border bg-popover px-2 py-1.5 font-mono text-[10px] uppercase tracking-[0.05em]">
                  <div className="text-foreground">{label}</div>
                  {payload.map((p) => (
                    <div key={String(p.dataKey)} className="mt-0.5 flex items-baseline gap-2 text-muted-foreground">
                      <span className="max-w-[180px] truncate">{p.name}</span>
                      <span className="ml-auto text-foreground">{p.value}</span>
                    </div>
                  ))}
                </div>
              );
            }}
          />
          {ideas.map((i, idx) => (
            <Radar
              key={i.id}
              name={i.title}
              dataKey={i.id}
              stroke={STROKES[idx % STROKES.length]}
              strokeWidth={1}
              strokeDasharray={idx === 1 ? "4 2" : idx === 2 ? "1 2" : undefined}
              fill={STROKES[idx % STROKES.length]}
              fillOpacity={0.08}
              dot={{ r: 2, fillOpacity: 1 }}
              isAnimationActive={false}
            />
          ))}
          <Legend wrapperStyle={{ fontSize: 11, fontFamily: "var(--font-mono)" }} formatter={(v: string) => <span style={{ color: "var(--muted-foreground)" }}>{v.length > 44 ? v.slice(0, 44) + "…" : v}</span>} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
