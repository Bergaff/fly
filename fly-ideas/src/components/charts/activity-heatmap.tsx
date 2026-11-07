import type { Idea } from "@/data/types";
import { activityGrid } from "@/lib/activity";

const WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"];

/** Календарь активности: квадрат на день, насыщенность означает число действий. */
export function ActivityHeatmap({ ideas }: { ideas: Idea[] }) {
  const { columns, max, total, activeDays } = activityGrid(ideas, 14);
  const level = (n: number) => (n <= 0 ? 0 : n === 1 ? 1 : n === 2 ? 2 : 3);
  const fill: Record<number, string> = { 0: "transparent", 1: "var(--muted-foreground)", 2: "var(--foreground)", 3: "var(--foreground)" };
  const opacity: Record<number, number> = { 0: 1, 1: 0.45, 2: 0.7, 3: 1 };

  const monthMarks: { index: number; label: string }[] = [];
  columns.forEach((col, i) => {
    const first = col[0];
    if (!first) return;
    const month = new Date(`${first.iso}T12:00:00`).toLocaleDateString("ru-RU", { month: "short" });
    if (monthMarks.length === 0 || monthMarks[monthMarks.length - 1].label !== month) monthMarks.push({ index: i, label: month });
  });

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <div className="flex flex-col gap-[2px] pt-[14px]">
          {WEEKDAYS.map((d, i) => (
            <span key={d} className="h-3 font-mono text-[9px] leading-3 text-muted-foreground/70">
              {i % 2 === 0 ? d : ""}
            </span>
          ))}
        </div>
        <div className="flex flex-col gap-1">
          <div className="flex gap-[2px]">
            {columns.map((_, i) => {
              const mark = monthMarks.find((m) => m.index === i);
              return (
                <span key={i} className="w-3 font-mono text-[9px] leading-none text-muted-foreground/70">
                  {mark ? mark.label : ""}
                </span>
              );
            })}
          </div>
          <div className="flex gap-[2px]">
            {columns.map((col, i) => (
              <div key={i} className="flex flex-col gap-[2px]">
                {col.map((cell) => (
                  <span
                    key={cell.iso}
                    title={cell.n < 0 ? "" : `${cell.label}: ${cell.n === 0 ? "нет действий" : `действий ${cell.n}`}`}
                    className="size-3 border border-border"
                    style={{ background: cell.n <= 0 ? "transparent" : fill[level(cell.n)], opacity: cell.n <= 0 ? 1 : opacity[level(cell.n)] }}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <span className="label">действий всего: {total}</span>
        <span className="label">дней с работой: {activeDays}</span>
        <span className="label">пик за день: {max}</span>
        <span className="ml-auto flex items-baseline gap-1.5">
          <span className="label">меньше</span>
          {[0, 1, 2, 3].map((l) => (
            <span key={l} className="size-3 border border-border" style={{ background: l === 0 ? "transparent" : fill[l], opacity: l === 0 ? 1 : opacity[l] }} />
          ))}
          <span className="label">больше</span>
        </span>
      </div>
    </div>
  );
}
