import { deadlineInfo } from "@/data/types";
import { cn } from "@/lib/utils";

export function DeadlineBadge({ deadline, className }: { deadline: string | null | undefined; className?: string }) {
  const d = deadlineInfo(deadline);
  if (!d) return null;
  return (
    <span
      title={`Дедлайн: ${d.date}`}
      className={cn(
        "inline-flex items-baseline gap-1.5 rounded-none border px-1.5 py-px font-mono text-[10px] uppercase tracking-[0.06em]",
        d.tone === "overdue" && "border-destructive/60 text-destructive",
        d.tone === "soon" && "border-[var(--chart-3)] text-[var(--chart-3)]",
        d.tone === "ok" && "border-border text-muted-foreground",
        className,
      )}
    >
      <span>{d.date}</span>
      <span>{d.label}</span>
    </span>
  );
}
