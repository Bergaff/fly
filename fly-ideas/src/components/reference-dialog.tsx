import { useEffect, useState } from "react";
import { ExternalLink, Trash2, X } from "lucide-react";
import type { Reference } from "@/data/types";
import { referenceLink } from "@/data/types";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

interface Props {
  reference: Reference | null;
  usedBy: { id: string; title: string }[];
  onClose: () => void;
  onSave: (id: string, patch: Partial<Reference>) => void;
  onDelete: (id: string) => void;
}

/** Разбор строки вида "Shiu PK, et al. (2024). Title. Nature 634. doi:10.1038/..." — грубо, но экономит время */
function parseQuick(s: string): Partial<Reference> {
  const out: Partial<Reference> = {};
  const doi = s.match(/10\.\d{4,9}\/[^\s"<>]+/i);
  if (doi) out.doi = doi[0].replace(/[.,;)]+$/, "");
  const year = s.match(/\((\d{4})\)|\b(19|20)\d{2}\b/);
  if (year) out.year = Number(year[1] ?? year[0]);
  const url = s.match(/https?:\/\/\S+/);
  if (url && !doi) out.url = url[0];
  return out;
}

export function ReferenceDialog({ reference, usedBy, onClose, onSave, onDelete }: Props) {
  const [d, setD] = useState<Reference | null>(reference);
  const [tag, setTag] = useState("");
  const [quick, setQuick] = useState("");
  useEffect(() => { setD(reference ? structuredClone(reference) : null); setTag(""); setQuick(""); }, [reference]);
  if (!d) return null;
  const set = <K extends keyof Reference>(k: K, v: Reference[K]) => setD((x) => (x ? { ...x, [k]: v } : x));
  const link = referenceLink(d);

  return (
    <Dialog open={!!reference} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Источник</DialogTitle>
          <DialogDescription>Общая база: один источник можно привязать к нескольким идеям.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="flex gap-1.5">
            <Input value={quick} onChange={(e) => setQuick(e.target.value)} placeholder="Вставь строку с DOI / годом / ссылкой — подхвачу автоматически" className="h-8 text-xs" />
            <Button size="sm" variant="outline" disabled={!quick.trim()} onClick={() => { setD((x) => (x ? { ...x, ...parseQuick(quick) } : x)); setQuick(""); }}>Разобрать</Button>
          </div>
          <F label="Авторы"><Input value={d.authors} onChange={(e) => set("authors", e.target.value)} placeholder="Shiu PK, Sterne GR, et al." /></F>
          <F label="Название"><Input value={d.title} onChange={(e) => set("title", e.target.value)} /></F>
          <div className="grid grid-cols-[100px_1fr] gap-3">
            <F label="Год"><Input type="number" value={d.year ?? ""} onChange={(e) => set("year", e.target.value ? Number(e.target.value) : null)} /></F>
            <F label="Журнал / конференция / препринт"><Input value={d.venue} onChange={(e) => set("venue", e.target.value)} placeholder="Nature 634, 210–219" /></F>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <F label="DOI"><Input value={d.doi} onChange={(e) => set("doi", e.target.value)} placeholder="10.1038/…" className="font-mono text-xs" /></F>
            <F label="URL (если нет DOI)"><Input value={d.url} onChange={(e) => set("url", e.target.value)} placeholder="https://" className="font-mono text-xs" /></F>
          </div>
          {link && (
            <a href={link} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground hover:underline">
              <ExternalLink className="size-3" /> {link}
            </a>
          )}
          <F label="Теги">
            <div className="flex flex-wrap gap-1">
              {d.tags.map((t, i) => (
                <Badge key={i} variant="secondary" className="gap-1 font-normal">
                  {t}<button className="cursor-pointer opacity-60 hover:opacity-100" onClick={() => set("tags", d.tags.filter((_, j) => j !== i))}><X className="size-3" /></button>
                </Badge>
              ))}
            </div>
            <Input value={tag} onChange={(e) => setTag(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && tag.trim()) { e.preventDefault(); set("tags", [...d.tags, tag.trim()]); setTag(""); } }} placeholder="тег + Enter" className="mt-1 h-7 text-xs" />
          </F>
          <F label="Конспект (общий для всех идей)"><Textarea value={d.notes} onChange={(e) => set("notes", e.target.value)} className="min-h-[90px]" /></F>
          {usedBy.length > 0 && (
            <div className="text-xs text-muted-foreground">
              Используется в: {usedBy.map((u) => u.title).join(" · ")}
            </div>
          )}
        </div>
        <DialogFooter className="sm:justify-between">
          <Button variant="ghost" className="text-destructive hover:text-destructive" onClick={() => { if (confirm(usedBy.length ? `Источник привязан к ${usedBy.length} идеям. Удалить?` : "Удалить источник?")) { onDelete(d.id); onClose(); } }}>
            <Trash2 /> Удалить
          </Button>
          <div className="flex gap-2">
            <Button variant="outline" onClick={onClose}>Отмена</Button>
            <Button onClick={() => { const { id, createdAt: _c, ...rest } = d; void _c; onSave(id, rest); onClose(); }}>Сохранить</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function F({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="flex flex-col gap-1"><Label className="text-[11px] text-muted-foreground">{label}</Label>{children}</div>;
}
