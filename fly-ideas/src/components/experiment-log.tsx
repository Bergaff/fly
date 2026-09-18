import { useState } from "react";
import type { ExperimentEntry, ExperimentOutcome } from "@/data/types";
import { OUTCOME_COLORS, OUTCOME_LABELS } from "@/data/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn, uid } from "@/lib/utils";

interface Props {
  entries: ExperimentEntry[];
  onChange: (entries: ExperimentEntry[]) => void;
}

const today = () => new Date().toISOString().slice(0, 10);

export function ExperimentLog({ entries, onChange }: Props) {
  const [open, setOpen] = useState<string | null>(entries[0]?.id ?? null);

  const add = () => {
    const e: ExperimentEntry = { id: uid("e"), date: today(), title: "", params: "", result: "", conclusion: "", outcome: "inconclusive", createdAt: new Date().toISOString() };
    onChange([e, ...entries]);
    setOpen(e.id);
  };
  const patch = (id: string, p: Partial<ExperimentEntry>) => onChange(entries.map((e) => (e.id === id ? { ...e, ...p } : e)));
  const remove = (id: string) => {
    if (!confirm("Удалить запись журнала?")) return;
    onChange(entries.filter((e) => e.id !== id));
  };
  const duplicate = (src: ExperimentEntry) => {
    const e: ExperimentEntry = {
      ...src,
      id: uid("e"),
      date: today(),
      result: "",
      conclusion: "",
      outcome: "inconclusive",
      createdAt: new Date().toISOString(),
      title: src.title ? `${src.title} (повтор)` : "",
    };
    onChange([e, ...entries]);
    setOpen(e.id);
  };

  const stats = (Object.keys(OUTCOME_LABELS) as ExperimentOutcome[]).map((k) => ({ k, n: entries.filter((e) => e.outcome === k).length })).filter((s) => s.n);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <span className="label">записей: {entries.length}</span>
        {stats.map((s) => (
          <span key={s.k} className="label">
            {OUTCOME_LABELS[s.k]}: {s.n}
          </span>
        ))}
        <Button size="sm" className="ml-auto" onClick={add}>
          Новая запись
        </Button>
      </div>

      {entries.length === 0 && (
        <p className="border border-dashed px-3 py-8 text-center text-[12px] text-muted-foreground">
          Лабораторный дневник: что запускал, с какими параметрами, что получилось и что из этого следует.
        </p>
      )}

      <ol className="flex flex-col">
        {entries.map((e) => {
          const isOpen = open === e.id;
          return (
            <li key={e.id} className="border-b">
              <div className="flex items-center gap-3 py-2">
                <span className="size-2 shrink-0" style={{ background: OUTCOME_COLORS[e.outcome] }} title={OUTCOME_LABELS[e.outcome]} />
                <span className="shrink-0 font-mono text-[11px] text-muted-foreground">{new Date(`${e.date}T00:00:00`).toLocaleDateString("ru-RU")}</span>
                <button className={cn("min-w-0 flex-1 truncate text-left text-[13px] cursor-pointer", !e.title && "text-muted-foreground italic")} onClick={() => setOpen(isOpen ? null : e.id)}>
                  {e.title || "без названия"}
                </button>
                <span className="label shrink-0">{OUTCOME_LABELS[e.outcome]}</span>
                <Button size="sm" variant="ghost" onClick={() => setOpen(isOpen ? null : e.id)}>
                  {isOpen ? "свернуть" : "открыть"}
                </Button>
              </div>

              {!isOpen && (e.conclusion || e.result) && <p className="line-clamp-2 pb-2 pl-5 text-[11px] text-muted-foreground">{e.conclusion || e.result}</p>}

              {isOpen && (
                <div className="flex flex-col gap-3 pb-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Input type="date" value={e.date} onChange={(ev) => patch(e.id, { date: ev.target.value })} className="w-[150px]" />
                    <Select value={e.outcome} onValueChange={(v) => patch(e.id, { outcome: v as ExperimentOutcome })}>
                      <SelectTrigger className="w-[170px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {(Object.keys(OUTCOME_LABELS) as ExperimentOutcome[]).map((k) => (
                          <SelectItem key={k} value={k}>
                            {OUTCOME_LABELS[k]}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <div className="ml-auto flex gap-1">
                      <Button size="sm" variant="ghost" title="Повторить с теми же параметрами" onClick={() => duplicate(e)}>
                        повторить
                      </Button>
                      <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => remove(e.id)}>
                        удалить
                      </Button>
                    </div>
                  </div>
                  <Field label="Что запускал">
                    <Input value={e.title} onChange={(ev) => patch(e.id, { title: ev.target.value })} placeholder="например: лезия AVLP 100 %, стимуляция сахарных GRN" />
                  </Field>
                  <Field label="Параметры (сид, бэкенд, коммит, длительность, файлы)">
                    <Textarea
                      value={e.params}
                      onChange={(ev) => patch(e.id, { params: ev.target.value })}
                      className="min-h-[60px] font-mono text-[12px]"
                      placeholder={"seed=42, backend=brian2 cpu, dt=0.1 ms, T=1 s\ncommit abc123, out: runs/2026-09-18_avlp/"}
                    />
                  </Field>
                  <Field label="Результат">
                    <Textarea value={e.result} onChange={(ev) => patch(e.id, { result: ev.target.value })} className="min-h-[60px]" placeholder="цифры, графики, что наблюдал" />
                  </Field>
                  <Field label="Вывод и что дальше">
                    <Textarea value={e.conclusion} onChange={(ev) => patch(e.id, { conclusion: ev.target.value })} className="min-h-[50px]" />
                  </Field>
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <Label className="text-[10px]">{label}</Label>
      {children}
    </div>
  );
}
