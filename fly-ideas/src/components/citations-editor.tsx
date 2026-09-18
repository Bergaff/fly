import { useMemo, useState } from "react";
import { BookOpen, ExternalLink, Plus, Search, X } from "lucide-react";
import type { IdeaCitation, Reference } from "@/data/types";
import { formatReference, referenceLink } from "@/data/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

interface Props {
  citations: IdeaCitation[];
  references: Reference[];
  onChange: (c: IdeaCitation[]) => void;
  onCreateReference: (title: string) => Reference; // создаёт в общей базе и возвращает
  onOpenReference: (id: string) => void;
}

export function CitationsEditor({ citations, references, onChange, onCreateReference, onOpenReference }: Props) {
  const [q, setQ] = useState("");
  const byId = useMemo(() => new Map(references.map((r) => [r.id, r])), [references]);
  const attached = citations.map((c) => ({ c, r: byId.get(c.refId) })).filter((x): x is { c: IdeaCitation; r: Reference } => !!x.r);
  const attachedIds = new Set(citations.map((c) => c.refId));

  const s = q.trim().toLowerCase();
  const candidates = references
    .filter((r) => !attachedIds.has(r.id))
    .filter((r) => !s || [r.authors, r.title, r.venue, r.doi, r.tags.join(" "), String(r.year ?? "")].join(" ").toLowerCase().includes(s))
    .slice(0, 8);

  const attach = (refId: string) => { onChange([...citations, { refId, why: "" }]); setQ(""); };
  const setWhy = (refId: string, why: string) => onChange(citations.map((c) => (c.refId === refId ? { ...c, why } : c)));
  const detach = (refId: string) => onChange(citations.filter((c) => c.refId !== refId));

  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="mb-2 text-xs text-muted-foreground">Источники этой идеи ({attached.length}). Поле справа — зачем источник нужен именно здесь.</div>
        {attached.length === 0 && (
          <div className="flex flex-col items-center gap-1 rounded-lg border border-dashed py-8 text-center text-sm text-muted-foreground">
            <BookOpen className="size-6 opacity-50" />
            <p>Пока ничего не привязано.</p>
          </div>
        )}
        <ol className="flex flex-col gap-2">
          {attached.map(({ c, r }, idx) => {
            const link = referenceLink(r);
            return (
              <li key={r.id} className="grid grid-cols-[1fr_minmax(180px,0.8fr)] gap-3 rounded-lg border px-3 py-2">
                <div className="min-w-0 text-sm">
                  <div className="flex items-start gap-1.5">
                    <span className="shrink-0 font-mono text-[10px] text-muted-foreground/70">[{idx + 1}]</span>
                    <button className="min-w-0 text-left leading-snug hover:underline cursor-pointer" onClick={() => onOpenReference(r.id)}>
                      <span className="font-medium">{r.authors || "—"}</span>{r.year ? ` (${r.year})` : ""}. {r.title}
                    </button>
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-1.5 pl-6 text-xs text-muted-foreground">
                    {r.venue && <span className="italic">{r.venue}</span>}
                    {link && <a href={link} target="_blank" rel="noreferrer" className="flex items-center gap-0.5 hover:text-foreground"><ExternalLink className="size-3" />{r.doi ? "doi" : "url"}</a>}
                    {r.tags.slice(0, 3).map((t) => <Badge key={t} variant="secondary" className="h-4 px-1 text-[10px] font-normal">{t}</Badge>)}
                  </div>
                </div>
                <div className="flex items-start gap-1">
                  <Input value={c.why} onChange={(e) => setWhy(r.id, e.target.value)} placeholder="Зачем нужна здесь" className="h-8 text-xs" />
                  <Button size="icon-sm" variant="ghost" className="size-8 shrink-0 text-muted-foreground hover:text-destructive" onClick={() => detach(r.id)}><X /></Button>
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      <div className="rounded-lg border bg-muted/30 p-3">
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Найти в общей базе по автору, названию, DOI, тегу…" className="h-8 pl-8 text-xs" />
        </div>
        <div className="mt-2 flex flex-col gap-1">
          {candidates.map((r) => (
            <button key={r.id} onClick={() => attach(r.id)} className="flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs hover:bg-accent cursor-pointer">
              <Plus className="size-3.5 shrink-0 text-muted-foreground" />
              <span className="min-w-0 flex-1 truncate">{formatReference(r)}</span>
            </button>
          ))}
          {candidates.length === 0 && references.filter((r) => !attachedIds.has(r.id)).length > 0 && <div className="px-2 py-1 text-xs text-muted-foreground">Ничего не найдено.</div>}
          <Button
            size="sm"
            variant="outline"
            className="mt-1 self-start"
            onClick={() => {
              const r = onCreateReference(q.trim());
              attach(r.id);
              onOpenReference(r.id);
            }}
          >
            <Plus /> {q.trim() ? `Создать источник «${q.trim().slice(0, 40)}»` : "Новый источник в базу"}
          </Button>
        </div>
      </div>
    </div>
  );
}
