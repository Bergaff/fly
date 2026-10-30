import { useMemo, useState } from "react";
import type { IdeaCitation, Reference } from "@/data/types";
import { formatReference, referenceLink } from "@/data/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface Props {
  citations: IdeaCitation[];
  references: Reference[];
  onChange: (c: IdeaCitation[]) => void;
  onCreateReference: (title: string) => Reference;
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

  const attach = (refId: string) => {
    onChange([...citations, { refId, why: "" }]);
    setQ("");
  };
  const setWhy = (refId: string, why: string) => onChange(citations.map((c) => (c.refId === refId ? { ...c, why } : c)));
  const detach = (refId: string) => onChange(citations.filter((c) => c.refId !== refId));

  return (
    <div className="flex flex-col gap-4">
      <div>
        <div className="label mb-2">привязано к идее: {attached.length}. Поле справа уточняет, зачем источник нужен здесь</div>
        {attached.length === 0 && <p className="border border-dashed px-3 py-6 text-center text-[12px] text-muted-foreground">Пока ничего не привязано.</p>}

        <ol className="flex flex-col border-t">
          {attached.map(({ c, r }, idx) => {
            const link = referenceLink(r);
            return (
              <li key={r.id} className="grid grid-cols-[1fr_minmax(200px,0.8fr)] gap-3 border-b py-2">
                <div className="min-w-0 text-[13px]">
                  <div className="flex items-baseline gap-2">
                    <span className="shrink-0 font-mono text-[10px] text-muted-foreground">[{idx + 1}]</span>
                    <button className="min-w-0 text-left leading-snug hover:underline cursor-pointer" onClick={() => onOpenReference(r.id)}>
                      <span className="font-medium">{r.authors || "автор не указан"}</span>
                      {r.year ? ` (${r.year})` : ""}. {r.title}
                    </button>
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-baseline gap-x-3 pl-6 text-[11px] text-muted-foreground">
                    {r.venue && <span className="italic">{r.venue}</span>}
                    {link && (
                      <a href={link} target="_blank" rel="noreferrer" className="font-mono hover:text-foreground">
                        {r.doi ? `doi:${r.doi}` : "ссылка"}
                      </a>
                    )}
                    {r.tags.slice(0, 3).map((t) => (
                      <span key={t}>#{t}</span>
                    ))}
                  </div>
                </div>
                <div className="flex items-start gap-1">
                  <Input value={c.why} onChange={(e) => setWhy(r.id, e.target.value)} placeholder="зачем нужна здесь" className="text-[12px]" />
                  <Button size="sm" variant="ghost" className="text-muted-foreground hover:text-destructive" onClick={() => detach(r.id)} title="Отвязать">
                    ×
                  </Button>
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      <div className="border p-3">
        <div className="label mb-2">добавить из общей базы</div>
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="автор, название, DOI, тег" className="text-[12px]" />
        <div className="mt-2 flex flex-col">
          {candidates.map((r) => (
            <button key={r.id} onClick={() => attach(r.id)} className="flex items-baseline gap-2 border-b px-1 py-1.5 text-left text-[12px] last:border-b-0 hover:bg-accent cursor-pointer">
              <span className="shrink-0 font-mono text-[10px] text-muted-foreground">привязать</span>
              <span className="min-w-0 flex-1 truncate">{formatReference(r)}</span>
            </button>
          ))}
          {candidates.length === 0 && <div className="px-1 py-1.5 text-[12px] text-muted-foreground">{s ? "Ничего не найдено." : "Все источники базы уже привязаны."}</div>}
          <Button
            className="mt-2 self-start"
            variant="outline"
            onClick={() => {
              const r = onCreateReference(q.trim());
              attach(r.id);
              onOpenReference(r.id);
            }}
          >
            {q.trim() ? `Создать источник «${q.trim().slice(0, 40)}»` : "Новый источник в базу"}
          </Button>
        </div>
      </div>
    </div>
  );
}
