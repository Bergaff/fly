import { useState } from "react";
import { ChevronDown, ChevronRight, Copy, FlaskConical, Plus, Trash2 } from "lucide-react";
import type { ExperimentEntry, ExperimentOutcome } from "@/data/types";
import { OUTCOME_COLORS, OUTCOME_LABELS } from "@/data/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
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
    const e: ExperimentEntry = { ...src, id: uid("e"), date: today(), result: "", conclusion: "", outcome: "inconclusive", createdAt: new Date().toISOString(), title: src.title ? `${src.title} (повтор)` : "" };
    onChange([e, ...entries]);
    setOpen(e.id);
  };

  const stats = (Object.keys(OUTCOME_LABELS) as ExperimentOutcome[]).map((k) => ({ k, n: entries.filter((e) => e.outcome === k).length })).filter((s) => s.n);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-muted-foreground">{entries.length ? `${entries.length} записей` : "Записей пока нет"}</span>
        {stats.map((s) => (
          <Badge key={s.k} variant="outline" className="gap-1 font-normal text-muted-foreground">
            <span className="size-1.5 rounded-full" style={{ background: OUTCOME_COLORS[s.k] }} />
            {OUTCOME_LABELS[s.k]} {s.n}
          </Badge>
        ))}
        <Button size="sm" className="ml-auto" onClick={add}><Plus /> Новая запись</Button>
      </div>

      {entries.length === 0 && (
        <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed py-10 text-center text-sm text-muted-foreground">
          <FlaskConical className="size-6 opacity-50" />
          <p>Лабораторный дневник: что запускал, с какими параметрами, что получилось и что из этого следует.</p>
        </div>
      )}

      <ol className="relative flex flex-col gap-2 pl-4 before:absolute before:top-2 before:bottom-2 before:left-[5px] before:w-px before:bg-border">
        {entries.map((e) => {
          const isOpen = open === e.id;
          return (
            <li key={e.id} className="relative">
              <span className="absolute top-3.5 -left-4 size-[11px] rounded-full border-2 border-background" style={{ background: OUTCOME_COLORS[e.outcome] }} />
              <div className={cn("rounded-lg border bg-card transition-colors", isOpen && "border-foreground/20")}>
                <button className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm cursor-pointer" onClick={() => setOpen(isOpen ? null : e.id)}>
                  {isOpen ? <ChevronDown className="size-4 shrink-0 text-muted-foreground" /> : <ChevronRight className="size-4 shrink-0 text-muted-foreground" />}
                  <span className="shrink-0 font-mono text-xs text-muted-foreground">{new Date(`${e.date}T00:00:00`).toLocaleDateString("ru-RU")}</span>
                  <span className={cn("min-w-0 flex-1 truncate", !e.title && "text-muted-foreground italic")}>{e.title || "без названия"}</span>
                  <Badge variant="outline" className="shrink-0 gap-1 font-normal" style={{ borderColor: OUTCOME_COLORS[e.outcome] }}>
                    <span className="size-1.5 rounded-full" style={{ background: OUTCOME_COLORS[e.outcome] }} />
                    {OUTCOME_LABELS[e.outcome]}
                  </Badge>
                </button>
                {!isOpen && (e.conclusion || e.result) && (
                  <p className="line-clamp-2 px-3 pb-2 pl-9 text-xs text-muted-foreground">{e.conclusion || e.result}</p>
                )}
                {isOpen && (
                  <div className="flex flex-col gap-3 border-t px-3 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <Input type="date" value={e.date} onChange={(ev) => patch(e.id, { date: ev.target.value })} className="h-8 w-[150px]" />
                      <Select value={e.outcome} onValueChange={(v) => patch(e.id, { outcome: v as ExperimentOutcome })}>
                        <SelectTrigger className="h-8 w-[160px]"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {(Object.keys(OUTCOME_LABELS) as ExperimentOutcome[]).map((k) => (
                            <SelectItem key={k} value={k}>
                              <span className="mr-2 inline-block size-2 rounded-full" style={{ background: OUTCOME_COLORS[k] }} />
                              {OUTCOME_LABELS[k]}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <div className="ml-auto flex gap-1">
                        <Button size="icon-sm" variant="ghost" title="Повторить с теми же параметрами" onClick={() => duplicate(e)}><Copy /></Button>
                        <Button size="icon-sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => remove(e.id)}><Trash2 /></Button>
                      </div>
                    </div>
                    <Field label="Что запускал">
                      <Input value={e.title} onChange={(ev) => patch(e.id, { title: ev.target.value })} placeholder="напр. Лезия AVLP 100 %, стимуляция сахарных GRN" />
                    </Field>
                    <Field label="Параметры (сид, бэкенд, коммит, длительность, файлы)">
                      <Textarea value={e.params} onChange={(ev) => patch(e.id, { params: ev.target.value })} className="min-h-[60px] font-mono text-[12px]" placeholder={"seed=42, backend=brian2 cpu, dt=0.1ms, T=1s\ncommit abc123, out: runs/2026-09-18_avlp/"} />
                    </Field>
                    <Field label="Результат">
                      <Textarea value={e.result} onChange={(ev) => patch(e.id, { result: ev.target.value })} className="min-h-[60px]" placeholder="Цифры, графики, что наблюдал" />
                    </Field>
                    <Field label="Вывод / что дальше">
                      <Textarea value={e.conclusion} onChange={(ev) => patch(e.id, { conclusion: ev.target.value })} className="min-h-[50px]" />
                    </Field>
                  </div>
                )}
              </div>
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
      <Label className="text-[11px] text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}
