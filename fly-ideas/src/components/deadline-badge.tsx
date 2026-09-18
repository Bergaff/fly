import { CalendarClock, AlertTriangle } from "lucide-react";
import { deadlineInfo } from "@/data/types";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function DeadlineBadge({ deadline, className }: { deadline: string | null | undefined; className?: string }) {
  const d = deadlineInfo(deadline);
  if (!d) return null;
  return (
    <Badge
      variant="outline"
      title={`Дедлайн: ${d.date}`}
      className={cn(
        "gap-1 font-normal",
        d.tone === "overdue" && "border-destructive/60 bg-destructive/10 text-destructive",
        d.tone === "soon" && "border-[var(--chart-3)]/60 bg-[var(--chart-3)]/10 text-[var(--chart-3)]",
        d.tone === "ok" && "text-muted-foreground",
        className,
      )}
    >
      {d.tone === "overdue" ? <AlertTriangle className="size-3" /> : <CalendarClock className="size-3" />}
      {d.date} · {d.label}
    </Badge>
  );
}
