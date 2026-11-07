import { useMemo, useState } from "react";
import type { Idea, Project, Reference } from "@/data/types";
import { draftFileName, draftMarkdown } from "@/lib/draft";
import { fly } from "@/lib/bridge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";

interface Props {
  idea: Idea;
  project?: Project;
  references: Reference[];
}

/** Черновик статьи: markdown, собранный из идеи, журнала, чеклиста и литературы. */
export function ArticleDraftButton({ idea, project, references }: Props) {
  const [open, setOpen] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const markdown = useMemo(() => draftMarkdown(idea, project, references), [idea, project, references]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  const save = async () => {
    const name = draftFileName(idea);
    if (fly) {
      const path = await fly.saveFile({
        defaultName: name,
        content: markdown,
        filters: [{ name: "Markdown", extensions: ["md"] }],
        kind: "exports",
      });
      setSaved(path ?? null);
      return;
    }
    const url = URL.createObjectURL(new Blob([markdown], { type: "text/markdown" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = name;
    a.click();
    URL.revokeObjectURL(url);
    setSaved(name);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          Черновик статьи
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Черновик статьи</DialogTitle>
          <DialogDescription className="text-xs">
            Собран из идеи, оценок, журнала прогонов, чеклиста и привязанных источников. Проверьте цифры перед подачей.
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[46vh] overflow-auto rounded-sm border border-border bg-muted/30 p-3">
          <pre className="whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-foreground">{markdown}</pre>
        </div>
        <DialogFooter className="flex-wrap items-center gap-2 sm:justify-between">
          <span className="font-mono text-[11px] text-muted-foreground">
            {markdown.split("\n").length} строк · {idea.experiments.length} прогонов · {idea.citations.length} источников
            {saved ? ` · сохранено: ${saved}` : ""}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={copy}>
              {copied ? "Скопировано" : "Копировать"}
            </Button>
            <Button size="sm" onClick={save}>
              Сохранить .md
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
