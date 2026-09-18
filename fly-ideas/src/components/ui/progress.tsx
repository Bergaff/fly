import { cn } from "@/lib/utils";

export function Progress({ value, className, color }: { value: number; className?: string; color?: string }) {
  return (
    <div className={cn("bg-primary/15 relative h-1.5 w-full overflow-hidden rounded-full", className)}>
      <div className="h-full rounded-full transition-all" style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color ?? "var(--primary)" }} />
    </div>
  );
}
