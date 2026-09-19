import { useState } from "react";
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
        <Progress value={pct} className="h-1.5 flex-1" color={pct === 100 ? "var(--chart-2)" : "var(--foreground)"} />
        <span className="font-mono text-[11px] text-muted-foreground">
          {done}/{items.length}, {pct}%
        </span>
        <Button size="sm" variant="ghost" title="Вернуть стандартный конвейер" onClick={resetDefault}>
          по умолчанию
        </Button>
      </div>

      <ol className="flex flex-col border-t">
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
            className={cn("group flex items-center gap-2 border-b px-1 py-1 text-[13px]", drag === idx && "opacity-40")}
          >
            <span className="w-6 shrink-0 cursor-grab text-right font-mono text-[10px] text-muted-foreground/60" title="Перетащить">
              {idx + 1}
            </span>
            <input type="checkbox" checked={c.done} onChange={() => toggle(c.id)} className="shrink-0 cursor-pointer" title="Этап закрыт" />
            <input
              value={c.text}
              onChange={(e) => rename(c.id, e.target.value)}
              className={cn("min-w-0 flex-1 bg-transparent outline-none", c.done && "text-muted-foreground line-through")}
            />
            {c.done && c.doneAt && <span className="shrink-0 font-mono text-[10px] text-muted-foreground/70">{new Date(c.doneAt).toLocaleDateString("ru-RU")}</span>}
            <button onClick={() => remove(c.id)} className="shrink-0 cursor-pointer px-1 font-mono text-[11px] text-muted-foreground/60 hover:text-destructive">
              ×
            </button>
          </li>
        ))}
      </ol>

      <div className="flex gap-1.5">
        <Input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), add())}
          placeholder="Новый этап, Enter"
        />
        <Button variant="outline" onClick={add} disabled={!text.trim()}>
          Добавить
        </Button>
      </div>
    </div>
  );
}
