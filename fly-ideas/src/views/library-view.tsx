import { useMemo, useState } from "react";
import type { Idea, Reference } from "@/data/types";
import { formatReference, referenceLink } from "@/data/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { fly } from "@/lib/bridge";
import { LiteratureSearchDialog } from "@/components/literature-search";

interface Props {
  references: Reference[];
  ideas: Idea[];
  allIdeas: Idea[];
  scopeLabel: string;
  onOpen: (id: string) => void;
  onAdd: () => void;
  onOpenIdea: (id: string) => void;
  onAddReferences: (items: Partial<Reference>[]) => void;
}

export function LibraryView({ references, ideas, allIdeas, scopeLabel, onOpen, onAdd, onOpenIdea, onAddReferences }: Props) {
  const [q, setQ] = useState("");
  const [tag, setTag] = useState<string | null>(null);
  const [onlyScope, setOnlyScope] = useState(false);
  const [sort, setSort] = useState<"year" | "added" | "uses">("year");
  const [lit, setLit] = useState(false);

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

  const bibText = () => list.map((r, i) => `[${i + 1}] ${formatReference(r)}${r.doi ? ` https://doi.org/${r.doi}` : r.url ? ` ${r.url}` : ""}`).join("\n");
  const copyAll = () => navigator.clipboard.writeText(bibText());
  const saveAll = async () => {
    const name = `bibliography-${new Date().toISOString().slice(0, 10)}.txt`;
    if (fly) {
      const p = await fly.saveFile({ defaultName: name, content: bibText(), filters: [{ name: "Текст", extensions: ["txt", "md"] }], kind: "exports" });
      if (p) alert(`Сохранено: ${p}`);
      return;
    }
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([bibText()], { type: "text/plain" }));
    a.download = name;
    a.click();
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Автор, название, DOI, конспект" className="w-[280px]" />
        <div className="flex items-baseline gap-3 font-mono text-[10px] uppercase tracking-[0.06em]">
          {(["year", "uses", "added"] as const).map((k) => (
            <button
              key={k}
              onClick={() => setSort(k)}
              className={cn("cursor-pointer border-b border-transparent pb-0.5 hover:text-foreground", sort === k ? "border-foreground text-foreground" : "text-muted-foreground")}
            >
              {k === "year" ? "по году" : k === "uses" ? "по использованию" : "по добавлению"}
            </button>
          ))}
        </div>
        <label className="flex items-baseline gap-1.5 font-mono text-[10px] uppercase tracking-[0.06em] text-muted-foreground cursor-pointer">
          <input type="checkbox" checked={onlyScope} onChange={(e) => setOnlyScope(e.target.checked)} />
          только {scopeLabel}
        </label>
        <span className="label">
          {list.length} из {references.length}
        </span>
        <div className="ml-auto flex gap-2">
          <Button variant="outline" onClick={copyAll} disabled={!list.length} title="Скопировать список в буфер">
            Список
          </Button>
          <Button variant="outline" onClick={saveAll} disabled={!list.length} title="Сохранить список в файл">
            В файл
          </Button>
          <Button variant="outline" onClick={() => setLit(true)} title="Поиск литературы через Perplexity">
            Литература…
          </Button>
          <Button onClick={onAdd}>Источник</Button>
        </div>
      </div>

      {tags.length > 0 && (
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b px-4 py-2 font-mono text-[10px] uppercase tracking-[0.06em]">
          <span className="text-muted-foreground/70">метки</span>
          <button onClick={() => setTag(null)} className={cn("cursor-pointer border-b border-transparent hover:text-foreground", !tag ? "border-foreground text-foreground" : "text-muted-foreground")}>
            все
          </button>
          {tags.map((t) => (
            <button
              key={t}
              onClick={() => setTag(tag === t ? null : t)}
              className={cn("cursor-pointer border-b border-transparent hover:text-foreground", tag === t ? "border-foreground text-foreground" : "text-muted-foreground")}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        {list.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3">
            <p className="text-[12px] text-muted-foreground">{references.length ? "Ничего не найдено." : "База источников пуста."}</p>
            <Button variant="outline" onClick={onAdd}>
              Добавить источник
            </Button>
          </div>
        ) : (
          <table className="w-full border-collapse text-left align-top">
            <tbody>
              {list.map((r) => {
                const link = referenceLink(r);
                const used = usage.get(r.id) ?? [];
                return (
                  <tr key={r.id} className="cursor-pointer border-b hover:bg-accent/50" onClick={() => onOpen(r.id)}>
                    <td className="w-[70px] py-2 pl-4 font-mono text-[11px] text-muted-foreground">{r.year ?? ""}</td>
                    <td className="min-w-0 py-2 pr-4 text-[13px]">
                      <div className="leading-snug">
                        <span className="font-medium">{r.authors || "автор не указан"}</span>
                        {r.title && <span>. {r.title}</span>}
                      </div>
                      <div className="mt-0.5 flex flex-wrap items-baseline gap-x-3 text-[11px] text-muted-foreground">
                        {r.venue && <span className="italic">{r.venue}</span>}
                        {link && (
                          <a href={link} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()} className="font-mono hover:text-foreground">
                            {r.doi ? `doi:${r.doi}` : "ссылка"}
                          </a>
                        )}
                        {r.tags.map((t) => (
                          <span key={t} className="font-mono">
                            #{t}
                          </span>
                        ))}
                      </div>
                      {r.notes && <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">{r.notes}</p>}
                    </td>
                    <td className="w-[280px] py-2 pr-4 align-top" onClick={(e) => e.stopPropagation()}>
                      <div className="label mb-1">используется: {used.length}</div>
                      {used.length === 0 && <div className="text-[11px] text-muted-foreground/70">ни в одной идее</div>}
                      <div className="flex flex-col">
                        {used.map((i) => {
                          const why = i.citations.find((c) => c.refId === r.id)?.why;
                          return (
                            <button key={i.id} onClick={() => onOpenIdea(i.id)} className="truncate text-left text-[11px] hover:underline cursor-pointer" title={why || i.title}>
                              {i.title}
                              {why ? <span className="text-muted-foreground"> ({why})</span> : ""}
                            </button>
                          );
                        })}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <LiteratureSearchDialog
        open={lit}
        defaultQuery={q}
        onClose={() => setLit(false)}
        onAdd={(items) => onAddReferences(items)}
      />
    </div>
  );
}
