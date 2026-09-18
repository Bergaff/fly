import { useState } from "react";
import { Check, GripVertical, Plus, RotateCcw, X } from "lucide-react";
import type { ChecklistItem } from "@/data/types";
import { DEFAULT_CHECKLIST } from "@/data/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { uid } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface Props {
  items: ChecklistItem[];
  onChange: (items: ChecklistItem[]) => void;
}

export function Checklist({ items, onChange }: Props) {
  const [text, setText] = useState("");
  const [drag, setDrag] = useState<number | null>(null);
  const done = items.filter((i) => i.done).length;
  const pct = items.length ? Math.round((done / items.length) * 100) : 0;

  const toggle = (id: string) =>
    onChange(items.map((c) => (c.id === id ? { ...c, done: !c.done, doneAt: !c.done ? new Date().toISOString() : null } : c)));
  const remove = (id: string) => onChange(items.filter((c) => c.id !== id));
  const rename = (id: string, t: string) => onChange(items.map((c) => (c.id === id ? { ...c, text: t } : c)));
  const add = () => {
    if (!text.trim()) return;
    onChange([...items, { id: uid("c"), text: text.trim(), done: false, doneAt: null }]);
    setText("");
  };
  const reorder = (from: number, to: number) => {
    if (from === to) return;
    const next = [...items];
    const [m] = next.splice(from, 1);
    next.splice(to, 0, m);
    onChange(next);
  };
  const resetDefault = () => {
    if (items.length && !confirm("Заменить чеклист стандартным конвейером «идея → статья»?")) return;
    onChange(DEFAULT_CHECKLIST.map((t) => ({ id: uid("c"), text: t, done: false, doneAt: null })));
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-3">
        <Progress value={pct} color={pct === 100 ? "var(--chart-2)" : "var(--chart-1)"} className="h-2 flex-1" />
        <span className="font-mono text-xs text-muted-foreground">{done}/{items.length} · {pct}%</span>
        <Button size="icon-sm" variant="ghost" className="size-6" title="Стандартный конвейер" onClick={resetDefault}>
          <RotateCcw className="size-3" />
        </Button>
      </div>
      <ol className="flex flex-col">
        {items.map((c, idx) => (
          <li
            key={c.id}
            draggable
            onDragStart={() => setDrag(idx)}
            onDragOver={(e) => e.preventDefault()}
            onDrop={() => {
              if (drag !== null) reorder(drag, idx);
              setDrag(null);
            }}
            className={cn("group flex items-center gap-1.5 rounded-md px-1 py-1 text-sm hover:bg-muted/50", drag === idx && "opacity-40")}
          >
            <GripVertical className="size-3.5 shrink-0 cursor-grab text-muted-foreground/40 opacity-0 group-hover:opacity-100" />
            <button
              onClick={() => toggle(c.id)}
              className={cn(
                "flex size-4 shrink-0 cursor-pointer items-center justify-center rounded-[4px] border transition-colors",
                c.done ? "border-[var(--chart-2)] bg-[var(--chart-2)] text-background" : "border-muted-foreground/40 hover:border-foreground",
              )}
            >
              {c.done && <Check className="size-3" strokeWidth={3} />}
            </button>
            <span className="w-5 shrink-0 text-right font-mono text-[10px] text-muted-foreground/60">{idx + 1}</span>
            <input
              value={c.text}
              onChange={(e) => rename(c.id, e.target.value)}
              className={cn("min-w-0 flex-1 bg-transparent outline-none", c.done && "text-muted-foreground line-through")}
            />
            {c.done && c.doneAt && <span className="shrink-0 text-[10px] text-muted-foreground/60">{new Date(c.doneAt).toLocaleDateString("ru-RU")}</span>}
            <button onClick={() => remove(c.id)} className="shrink-0 cursor-pointer text-muted-foreground/50 opacity-0 hover:text-destructive group-hover:opacity-100">
              <X className="size-3.5" />
            </button>
          </li>
        ))}
      </ol>
      <div className="flex gap-1.5">
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder="Новый этап + Enter"
          className="h-8 text-sm"
        />
        <Button size="icon-sm" variant="outline" onClick={add} disabled={!text.trim()}>
          <Plus />
        </Button>
      </div>
    </div>
  );
}
