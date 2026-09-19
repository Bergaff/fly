import { useState } from "react";
import type { Reference } from "@/data/types";
import { parseReferencesFromText } from "@/lib/refparse";
import { fly, isElectron } from "@/lib/bridge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface Props {
  open: boolean;
  defaultQuery?: string;
  onClose: () => void;
  onAdd: (items: Partial<Reference>[]) => void;
}

const SYSTEM = `Ты помогаешь аспиранту искать научную литературу по вычислительной нейробиологии дрозофилы,
обучению и памяти, грибовидным телам, коннектомам.
На запрос верни 5-8 публикаций, каждая отдельной строкой строго в формате:
Авторы (год). Название. Журнал или препринт. DOI: 10.xxxx/yyyy
Без нумерации, без вступлений и без общих рассуждений. Если DOI неизвестен, укажи URL.`;

/** Поиск литературы через Perplexity: ответ плюс разобранные строки, которые можно внести в базу */
export function LiteratureSearchDialog({ open, defaultQuery = "", onClose, onAdd }: Props) {
  const [q, setQ] = useState(defaultQuery);
  const [model, setModel] = useState("sonar");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [answer, setAnswer] = useState("");
  const [picked, setPicked] = useState<Set<number>>(new Set());
  const [keyInput, setKeyInput] = useState("");
  const [hasKey, setHasKey] = useState<boolean | null>(null);

  if (isElectron && hasKey === null) {
    fly!.getSecret("perplexity").then((k) => setHasKey(!!k));
  }

  const found = answer ? parseReferencesFromText(answer) : [];

  const search = async () => {
    const text = q.trim();
    if (!text || busy || !fly) return;
    setBusy(true);
    setErr("");
    setAnswer("");
    setPicked(new Set());
    try {
      const r = await fly.llmChat({ provider: "perplexity", model, messages: [{ role: "system", content: SYSTEM }, { role: "user", content: text }] });
      setAnswer(r.content);
      setPicked(new Set(parseReferencesFromText(r.content).map((_, i) => i)));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const saveKey = async () => {
    await fly!.setSecret("perplexity", keyInput.trim() || null);
    setHasKey(!!keyInput.trim());
    setKeyInput("");
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Поиск литературы</DialogTitle>
          <DialogDescription>
            Запрос уходит в Perplexity (модель sonar). Из ответа автоматически вытаскиваются строки с DOI и годом: отметь нужные и добавь в базу.
          </DialogDescription>
        </DialogHeader>

        {hasKey === false && (
          <div className="flex flex-wrap items-center gap-2 border border-dashed p-2">
            <span className="label">ключ perplexity не задан</span>
            <Input value={keyInput} onChange={(e) => setKeyInput(e.target.value)} type="password" placeholder="pplx-..." className="h-7 w-[240px] text-[12px]" />
            <Button size="sm" onClick={saveKey} disabled={!keyInput.trim()}>
              Сохранить ключ
            </Button>
            <span className="text-[11px] text-muted-foreground">
              взять на perplexity.ai/settings/api
            </span>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="что искать: например «спонтанное восстановление памяти после угасания у дрозофилы»"
            className="min-w-[280px] flex-1"
          />
          <Select value={model} onValueChange={setModel}>
            <SelectTrigger className="w-[190px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="sonar">sonar, быстрая</SelectItem>
              <SelectItem value="sonar-pro">sonar-pro, подробная</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={search} disabled={busy || !q.trim() || !fly}>
            {busy ? "ищу…" : "Найти"}
          </Button>
        </div>

        {err && <div className="border border-destructive/40 p-2 text-[12px] text-destructive">{err}</div>}

        {found.length > 0 && (
          <div className="border">
            <div className="flex items-center gap-3 border-b px-2 py-1.5">
              <span className="label">найдено работ: {found.length}, отмечено: {picked.size}</span>
              <Button
                size="sm"
                className="ml-auto"
                disabled={!picked.size}
                onClick={() => {
                  onAdd(found.filter((_, i) => picked.has(i)));
                  onClose();
                }}
              >
                Добавить в базу
              </Button>
            </div>
            <div className="flex max-h-[260px] flex-col overflow-y-auto">
              {found.map((r, i) => (
                <label key={i} className="flex cursor-pointer items-start gap-2 border-b px-2 py-1.5 last:border-b-0 hover:bg-accent">
                  <input
                    type="checkbox"
                    className="mt-1"
                    checked={picked.has(i)}
                    onChange={() =>
                      setPicked((p) => {
                        const n = new Set(p);
                        if (n.has(i)) n.delete(i);
                        else n.add(i);
                        return n;
                      })
                    }
                  />
                  <span className="min-w-0 text-[12px] leading-snug">
                    <span className="font-medium">{r.authors || "автор не указан"}</span>
                    {r.year ? ` (${r.year})` : ""}
                    {r.title ? `. ${r.title}` : ""}
                    {r.venue && <span className="text-muted-foreground"> {r.venue}</span>}
                    {(r.doi || r.url) && <span className="ml-1 font-mono text-[11px] text-muted-foreground">{r.doi ? `doi:${r.doi}` : r.url}</span>}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}

        {answer && (
          <details className="border">
            <summary className="label cursor-pointer px-2 py-1.5">полный ответ модели</summary>
            <pre className="max-h-[220px] overflow-auto border-t p-2 text-[12px] leading-relaxed whitespace-pre-wrap">{answer}</pre>
          </details>
        )}
      </DialogContent>
    </Dialog>
  );
}
