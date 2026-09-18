import { cn } from "@/lib/utils";

export function Progress({ value, className, color }: { value: number; className?: string; color?: string }) {
  return (
    <div className={cn("relative h-1.5 w-full overflow-hidden rounded-none border border-border bg-transparent", className)}>
      <div className="h-full rounded-none" style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color ?? "var(--foreground)" }} />
    </div>
  );
}
