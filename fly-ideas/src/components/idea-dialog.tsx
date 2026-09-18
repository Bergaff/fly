import { useEffect, useRef, useState } from "react";
import type { Idea, IdeaScores, IdeaStatus, Project, Reference } from "@/data/types";
import { SCORE_LABELS, STATUS_COLORS, STATUS_LABELS, STATUS_ORDER, checklistProgress } from "@/data/types";
import { Checklist } from "@/components/checklist";
import { ExperimentLog } from "@/components/experiment-log";
import { CitationsEditor } from "@/components/citations-editor";
import { DeadlineBadge } from "@/components/deadline-badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";

interface Props {
 idea: Idea | null;
 allIdeas: Idea[];
 references: Reference[];
 projects: Project[];
 onCreateReference: (title: string) => Reference;
 onOpenReference: (id: string) => void;
 onClose: () => void;
 onSave: (id: string, patch: Partial<Idea>) => void;
 onDelete: (id: string) => void;
}

export function IdeaDialog({ idea, allIdeas, references, projects, onCreateReference, onOpenReference, onClose, onSave, onDelete, onOpenOther }: Props & { onOpenOther?: (id: string) => void }) {
 const [draft, setDraft] = useState<Idea | null>(idea);
 const [tagInput, setTagInput] = useState("");
 const [venueInput, setVenueInput] = useState("");
 const [linkLabel, setLinkLabel] = useState("");
 const [linkUrl, setLinkUrl] = useState("");
 const [tab, setTab] = useState("overview");
 const draftRef = useRef<Idea | null>(null);
 draftRef.current = draft;

 useEffect(() => {
 setDraft(idea ? structuredClone(idea) : null);
 setTagInput("");
 setVenueInput("");
 setLinkLabel("");
 setLinkUrl("");
 }, [idea]);

 if (!draft) return null;
 const set = <K extends keyof Idea>(k: K, v: Idea[K]) => setDraft((d) => (d ? { ...d, [k]: v } : d));
 const setScore = (k: keyof IdeaScores, v: number) => setDraft((d) => (d ? { ...d, scores: { ...d.scores, [k]: v } } : d));

 const save = () => {
 const { id, createdAt: _c, updatedAt: _u, ...rest } = draft;
 void _c;
 void _u;
 onSave(id, rest);
 onClose();
 };

 return (
 <Dialog open={!!idea} onOpenChange={(o) => !o && onClose()}>
 <DialogContent className="sm:max-w-4xl">
 <DialogHeader>
 <DialogTitle className="sr-only">Идея</DialogTitle>
 <DialogDescription className="sr-only">Просмотр и редактирование идеи</DialogDescription>
 <Input value={draft.title} onChange={(e) => set("title", e.target.value)} className="h-auto border-0 bg-transparent px-0 text-xl font-semibold dark:bg-transparent" placeholder="Название идеи" />
 <div className="flex flex-wrap items-center gap-2">
 <Select value={draft.status} onValueChange={(v) => set("status", v as IdeaStatus)}>
 <SelectTrigger className="h-8 w-[170px]">
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 {STATUS_ORDER.map((s) => (
 <SelectItem key={s} value={s}>
 <span className="mr-2 inline-block size-2 rounded-none" style={{ background: STATUS_COLORS[s] }} />
 {STATUS_LABELS[s]}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 <Select value={draft.projectId} onValueChange={(v) => set("projectId", v)}>
 <SelectTrigger className="h-8 w-[260px]">
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 {projects.map((p) => (
 <SelectItem key={p.id} value={p.id}>
 <span className="mr-2 inline-block size-2 rounded-none" style={{ background: p.color }} />
 {p.name}
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 <Input value={draft.timeline} onChange={(e) => set("timeline", e.target.value)} placeholder="Сроки (напр. 3–5 мес.)" className="h-8 w-[180px]" />
 <div className="flex items-center gap-1.5">
 
 <Input type="date" value={draft.deadline ?? ""} onChange={(e) => set("deadline", e.target.value || null)} className="h-8 w-[150px]" title="Дедлайн" />
 {draft.deadline && (
 <Button size="icon-sm" variant="ghost" className="size-7" onClick={() => set("deadline", null)} title="Снять срок">×</Button>
 )}
 <DeadlineBadge deadline={draft.deadline} />
 </div>
 </div>
 </DialogHeader>

 <Tabs value={tab} onValueChange={setTab}>
 <TabsList>
 <TabsTrigger value="overview"> Разбор</TabsTrigger>
 <TabsTrigger value="checklist"> Чеклист <span className="font-mono text-[10px] text-muted-foreground">{checklistProgress(draft).done}/{checklistProgress(draft).total}</span></TabsTrigger>
 <TabsTrigger value="log"> Журнал {draft.experiments.length > 0 && <span className="font-mono text-[10px] text-muted-foreground">{draft.experiments.length}</span>}</TabsTrigger>
 <TabsTrigger value="refs"> Источники {draft.citations.length > 0 && <span className="font-mono text-[10px] text-muted-foreground">{draft.citations.length}</span>}</TabsTrigger>
 <TabsTrigger value="links"> Связи {draft.dependsOn.length > 0 && <span className="font-mono text-[10px] text-muted-foreground">{draft.dependsOn.length}</span>}</TabsTrigger>
 </TabsList>

 <TabsContent value="log" className="pt-2">
 <ExperimentLog entries={draft.experiments} onChange={(experiments) => set("experiments", experiments)} />
 </TabsContent>

 <TabsContent value="refs" className="pt-2">
 <CitationsEditor
 citations={draft.citations}
 references={references}
 onChange={(citations) => set("citations", citations)}
 onCreateReference={onCreateReference}
 onOpenReference={(id) => {
 // сохраняем актуальный черновик (после setState), чтобы привязка не потерялась
 setTimeout(() => {
 const d = draftRef.current;
 if (d) {
 const { id: ideaId, createdAt: _c, updatedAt: _u, ...rest } = d;
 void _c; void _u;
 onSave(ideaId, rest);
 }
 onOpenReference(id);
 }, 0);
 }}
 />
 </TabsContent>

 <TabsContent value="checklist" className="pt-2">
 <p className="mb-3 text-xs text-muted-foreground">Этапы «от идеи до статьи». Галочки сохраняются с датой; порядок можно менять перетаскиванием.</p>
 <Checklist items={draft.checklist} onChange={(items) => set("checklist", items)} />
 </TabsContent>

 <TabsContent value="links" className="pt-2">
 <DependsOnEditor draft={draft} allIdeas={allIdeas} onChange={(ids) => set("dependsOn", ids)} onOpenOther={(id) => { onClose(); onOpenOther?.(id); }} />
 </TabsContent>

 <TabsContent value="overview" className="pt-2">
 <div className="grid gap-5 md:grid-cols-[1fr_260px]">
 <div className="flex flex-col gap-4">
 <Field label="Исследовательский вопрос">
 <Textarea value={draft.question} onChange={(e) => set("question", e.target.value)} className="min-h-[70px]" />
 </Field>
 <Field label="Метод">
 <Textarea value={draft.method} onChange={(e) => set("method", e.target.value)} className="min-h-[140px] font-mono text-[13px]" />
 </Field>
 <Field label="Валидация (с чем сверять)">
 <Textarea value={draft.validation} onChange={(e) => set("validation", e.target.value)} className="min-h-[60px]" />
 </Field>
 <Field label="Заметки">
 <Textarea value={draft.notes} onChange={(e) => set("notes", e.target.value)} className="min-h-[60px]" />
 </Field>
 </div>

 <div className="flex flex-col gap-4">
 <div className="rounded-[2px] border bg-muted/30 p-3">
 <div className="mb-2 text-xs font-medium text-muted-foreground">Оценки (1–10)</div>
 <div className="flex flex-col gap-2.5">
 {(Object.keys(SCORE_LABELS) as (keyof IdeaScores)[]).map((k) => (
 <div key={k} className="flex items-center gap-2 text-xs">
 <span className="w-24 text-muted-foreground">{SCORE_LABELS[k]}</span>
 <input type="range" min={1} max={10} value={draft.scores[k]} onChange={(e) => setScore(k, Number(e.target.value))} className="flex-1" />
 <span className="w-4 text-right font-mono">{draft.scores[k]}</span>
 </div>
 ))}
 </div>
 </div>

 <ChipList
 label="Теги"
 items={draft.tags}
 input={tagInput}
 setInput={setTagInput}
 placeholder="тег + Enter"
 onAdd={(v) => set("tags", [...draft.tags, v])}
 onRemove={(i) => set("tags", draft.tags.filter((_, idx) => idx !== i))}
 prefix="#"
 />
 <ChipList
 label="Журналы / конференции"
 items={draft.venues}
 input={venueInput}
 setInput={setVenueInput}
 placeholder="eLife + Enter"
 onAdd={(v) => set("venues", [...draft.venues, v])}
 onRemove={(i) => set("venues", draft.venues.filter((_, idx) => idx !== i))}
 />

 <div>
 <Label className="mb-1.5 text-xs text-muted-foreground">Ссылки</Label>
 <div className="flex flex-col gap-1.5">
 {draft.links.map((l, i) => (
 <div key={i} className="flex items-center gap-1.5 text-xs">
 <a href={l.url} target="_blank" rel="noreferrer" className="flex min-w-0 flex-1 items-center gap-1 truncate text-foreground hover:underline">
 <span className="truncate">{l.label || l.url}</span>
 </a>
 <button className="text-muted-foreground hover:text-destructive cursor-pointer" onClick={() => set("links", draft.links.filter((_, idx) => idx !== i))}>×</button>
 </div>
 ))}
 <div className="flex gap-1">
 <Input value={linkLabel} onChange={(e) => setLinkLabel(e.target.value)} placeholder="название" className="h-7 text-xs" />
 <Input value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} placeholder="https://" className="h-7 text-xs" />
 <Button
 size="icon-sm"
 variant="outline"
 className="h-7 w-7 shrink-0"
 disabled={!linkUrl}
 onClick={() => {
 set("links", [...draft.links, { label: linkLabel, url: linkUrl }]);
 setLinkLabel("");
 setLinkUrl("");
 }}
 >Добавить</Button>
 </div>
 </div>
 </div>
 </div>
 </div>
 </TabsContent>
 </Tabs>

 <Separator />
 <DialogFooter className="items-center sm:justify-between">
 <div className="text-[11px] text-muted-foreground">
 создано {new Date(draft.createdAt).toLocaleDateString("ru-RU")} · изменено {new Date(draft.updatedAt).toLocaleDateString("ru-RU")}
 </div>
 <div className="flex gap-2">
 <Button
 variant="ghost"
 className="text-destructive hover:text-destructive"
 onClick={() => {
 if (confirm("Удалить идею?")) {
 onDelete(draft.id);
 onClose();
 }
 }}
 >
 Удалить
 </Button>
 <Button variant="outline" onClick={onClose}>Отмена</Button>
 <Button onClick={save}>Сохранить</Button>
 </div>
 </DialogFooter>
 </DialogContent>
 </Dialog>
 );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
 return (
 <div className="flex flex-col gap-1.5">
 <Label className="text-xs text-muted-foreground">{label}</Label>
 {children}
 </div>
 );
}

function ChipList({
 label,
 items,
 input,
 setInput,
 placeholder,
 onAdd,
 onRemove,
 prefix = "",
}: {
 label: string;
 items: string[];
 input: string;
 setInput: (v: string) => void;
 placeholder: string;
 onAdd: (v: string) => void;
 onRemove: (i: number) => void;
 prefix?: string;
}) {
 return (
 <div>
 <Label className="mb-1.5 text-xs text-muted-foreground">{label}</Label>
 <div className="flex flex-wrap gap-1">
 {items.map((t, i) => (
 <Badge key={`${t}-${i}`} variant="secondary" className="gap-1 font-normal">
 {prefix}{t}
 <button className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => onRemove(i)}>×</button>
 </Badge>
 ))}
 </div>
 <Input
 value={input}
 onChange={(e) => setInput(e.target.value)}
 onKeyDown={(e) => {
 if (e.key === "Enter" && input.trim()) {
 e.preventDefault();
 onAdd(input.trim());
 setInput("");
 }
 }}
 placeholder={placeholder}
 className="mt-1.5"
 />
 </div>
 );
}

function DependsOnEditor({ draft, allIdeas, onChange, onOpenOther }: { draft: Idea; allIdeas: Idea[]; onChange: (ids: string[]) => void; onOpenOther: (id: string) => void }) {
 const parents = draft.dependsOn.map((id) => allIdeas.find((i) => i.id === id)).filter((i): i is Idea => !!i);
 const children = allIdeas.filter((i) => i.dependsOn.includes(draft.id));
 const candidates = allIdeas.filter((i) => i.id !== draft.id && !draft.dependsOn.includes(i.id) && !i.dependsOn.includes(draft.id));
 const [pick, setPick] = useState("");
 return (
 <div className="grid gap-5 md:grid-cols-2">
 <div>
 <Label className="mb-2 text-xs text-muted-foreground">Растёт из (нужно сделать раньше)</Label>
 <div className="flex flex-col gap-1.5">
 {parents.length === 0 && <div className="text-xs text-muted-foreground/70">Нет зависимостей: идея самостоятельная.</div>}
 {parents.map((p) => (
 <div key={p.id} className="flex items-center gap-2 border px-2 py-1.5 text-[13px]">
 <span className="size-2 shrink-0 rounded-none" style={{ background: STATUS_COLORS[p.status] }} />
 <button className="min-w-0 flex-1 truncate text-left hover:underline cursor-pointer" onClick={() => onOpenOther(p.id)}>{p.title}</button>
 <span className="font-mono text-[10px] text-muted-foreground">{checklistProgress(p).pct}%</span>
 <button className="cursor-pointer text-muted-foreground hover:text-destructive" onClick={() => onChange(draft.dependsOn.filter((d) => d !== p.id))}></button>
 </div>
 ))}
 <div className="mt-1 flex gap-1.5">
 <Select value={pick} onValueChange={setPick}>
 <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Добавить зависимость…" /></SelectTrigger>
 <SelectContent>
 {candidates.length === 0 && <div className="px-2 py-1.5 text-xs text-muted-foreground">Нечего добавить</div>}
 {candidates.map((c) => <SelectItem key={c.id} value={c.id}>{c.title}</SelectItem>)}
 </SelectContent>
 </Select>
 <Button size="sm" variant="outline" disabled={!pick} onClick={() => { onChange([...draft.dependsOn, pick]); setPick(""); }}>Добавить</Button>
 </div>
 </div>
 </div>
 <div>
 <Label className="mb-2 text-xs text-muted-foreground">Из неё растут</Label>
 <div className="flex flex-col gap-1.5">
 {children.length === 0 && <div className="text-xs text-muted-foreground/70">Пока ничего. Задай эту идею как «растёт из» у других.</div>}
 {children.map((c) => (
 <button key={c.id} className="flex items-center gap-2 rounded-[2px] border px-2 py-1.5 text-left text-sm hover:bg-accent cursor-pointer" onClick={() => onOpenOther(c.id)}>
 <span className="size-2 shrink-0 rounded-none" style={{ background: STATUS_COLORS[c.status] }} />
 <span className="min-w-0 flex-1 truncate">{c.title}</span>
 <span className="font-mono text-[10px] text-muted-foreground">{STATUS_LABELS[c.status]}</span>
 </button>
 ))}
 </div>
 </div>
 </div>
 );
}
