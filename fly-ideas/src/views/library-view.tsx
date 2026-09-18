import { useMemo, useState } from "react";
import { BookOpen, Copy, ExternalLink, Plus, Search, Tag } from "lucide-react";
import type { Idea, Reference } from "@/data/types";
import { formatReference, referenceLink } from "@/data/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface Props {
  references: Reference[];
  ideas: Idea[]; // видимые (для фильтра «только этот проект»)
  allIdeas: Idea[];
  scopeLabel: string;
  onOpen: (id: string) => void;
  onAdd: () => void;
  onOpenIdea: (id: string) => void;
}

export function LibraryView({ references, ideas, allIdeas, scopeLabel, onOpen, onAdd, onOpenIdea }: Props) {
  const [q, setQ] = useState("");
  const [tag, setTag] = useState<string | null>(null);
  const [onlyScope, setOnlyScope] = useState(false);
  const [sort, setSort] = useState<"year" | "added" | "uses">("year");

  const usage = useMemo(() => {
    const m = new Map<string, Idea[]>();
    allIdeas.forEach((i) => i.citations.forEach((c) => m.set(c.refId, [...(m.get(c.refId) ?? []), i])));
    return m;
  }, [allIdeas]);
  const scopeIds = useMemo(() => new Set(ideas.flatMap((i) => i.citations.map((c) => c.refId))), [ideas]);
  const tags = useMemo(() => [...new Set(references.flatMap((r) => r.tags))].sort(), [references]);

  const list = useMemo(() => {
    const s = q.trim().toLowerCase();
    let l = references;
    if (onlyScope) l = l.filter((r) => scopeIds.has(r.id));
    if (tag) l = l.filter((r) => r.tags.includes(tag));
    if (s) l = l.filter((r) => [r.authors, r.title, r.venue, r.doi, r.notes, r.tags.join(" "), String(r.year ?? "")].join(" ").toLowerCase().includes(s));
    const by = {
      year: (a: Reference, b: Reference) => (b.year ?? 0) - (a.year ?? 0) || a.authors.localeCompare(b.authors),
      added: (a: Reference, b: Reference) => b.createdAt.localeCompare(a.createdAt),
      uses: (a: Reference, b: Reference) => (usage.get(b.id)?.length ?? 0) - (usage.get(a.id)?.length ?? 0),
    }[sort];
    return [...l].sort(by);
  }, [references, q, tag, onlyScope, scopeIds, sort, usage]);

  const copyAll = () => {
    const txt = list.map((r, i) => `[${i + 1}] ${formatReference(r)}${r.doi ? ` https://doi.org/${r.doi}` : r.url ? ` ${r.url}` : ""}`).join("\n");
    navigator.clipboard.writeText(txt);
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b px-6 py-3">
        <div className="relative w-[300px]">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Автор, название, DOI, конспект…" className="pl-8" />
        </div>
        <div className="flex rounded-lg bg-muted p-[3px] text-xs">
          {(["year", "uses", "added"] as const).map((k) => (
            <button key={k} onClick={() => setSort(k)} className={cn("rounded-md px-2.5 py-1 cursor-pointer", sort === k ? "bg-background shadow-sm" : "text-muted-foreground")}>
              {k === "year" ? "По году" : k === "uses" ? "По использованию" : "По добавлению"}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
          <input type="checkbox" checked={onlyScope} onChange={(e) => setOnlyScope(e.target.checked)} className="accent-[var(--chart-2)]" />
          только {scopeLabel}
        </label>
        <span className="text-xs text-muted-foreground">{list.length} из {references.length}</span>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" onClick={copyAll} disabled={!list.length} title="Скопировать список в буфер"><Copy /> Список</Button>
          <Button onClick={onAdd}><Plus /> Источник</Button>
        </div>
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5 border-b px-6 py-2">
          <Tag className="size-3.5 text-muted-foreground" />
          <button onClick={() => setTag(null)} className={cn("rounded-md px-2 py-0.5 text-xs cursor-pointer", !tag ? "bg-accent" : "text-muted-foreground hover:bg-accent/50")}>все</button>
          {tags.map((t) => (
            <button key={t} onClick={() => setTag(tag === t ? null : t)} className={cn("rounded-md px-2 py-0.5 text-xs cursor-pointer", tag === t ? "bg-accent" : "text-muted-foreground hover:bg-accent/50")}>{t}</button>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-6">
        {list.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-muted-foreground">
            <BookOpen className="size-8 opacity-40" />
            <p>{references.length ? "Ничего не найдено." : "База источников пуста."}</p>
            <Button variant="outline" onClick={onAdd}><Plus /> Добавить источник</Button>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {list.map((r) => {
              const link = referenceLink(r);
              const used = usage.get(r.id) ?? [];
              return (
                <Card key={r.id} className="cursor-pointer gap-0 py-3 transition-colors hover:border-foreground/20" onClick={() => onOpen(r.id)}>
                  <CardContent className="grid gap-3 md:grid-cols-[1fr_260px]">
                    <div className="min-w-0">
                      <div className="text-sm leading-snug">
                        <span className="font-medium">{r.authors || "—"}</span>
                        {r.year && <span className="text-muted-foreground"> ({r.year})</span>}
                        {r.title && <span>. {r.title}</span>}
                      </div>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                        {r.venue && <span className="italic">{r.venue}</span>}
                        {link && (
                          <a href={link} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} className="flex items-center gap-0.5 font-mono hover:text-foreground">
                            <ExternalLink className="size-3" />{r.doi || "url"}
                          </a>
                        )}
                        {r.tags.map((t) => <Badge key={t} variant="secondary" className="h-4 px-1.5 text-[10px] font-normal">{t}</Badge>)}
                      </div>
                      {r.notes && <p className="mt-1.5 line-clamp-2 text-xs text-muted-foreground">{r.notes}</p>}
                    </div>
                    <div className="text-xs text-muted-foreground" onClick={(e) => e.stopPropagation()}>
                      <div className="mb-1 text-[11px] uppercase tracking-wide opacity-70">Используется · {used.length}</div>
                      {used.length === 0 && <div className="italic opacity-70">ни в одной идее</div>}
                      <div className="flex flex-col gap-0.5">
                        {used.map((i) => {
                          const why = i.citations.find((c) => c.refId === r.id)?.why;
                          return (
                            <button key={i.id} onClick={() => onOpenIdea(i.id)} className="truncate text-left hover:text-foreground hover:underline cursor-pointer" title={why || i.title}>
                              {i.title}{why ? <span className="opacity-60"> — {why}</span> : ""}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
