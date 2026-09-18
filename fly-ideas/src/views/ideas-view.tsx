import { useMemo, useState } from "react";
import { Plus, Search, ArrowUpDown } from "lucide-react";
import type { Idea, IdeaStatus, Project } from "@/data/types";
import { STATUS_LABELS, STATUS_ORDER } from "@/data/types";
import { IdeaCard } from "@/components/idea-card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

type SortKey = "updated" | "impact" | "effort" | "speed" | "score";

interface Props {
  ideas: Idea[];
  projects: Project[];
  activeProject: string | "all";
  onOpen: (id: string) => void;
  onAdd: () => void;
  onMove: (id: string, projectId: string) => void;
  onCopyTo: (id: string, projectId: string) => void;
  onDelete: (id: string) => void;
  onStatus: (id: string, status: IdeaStatus) => void;
  compare: string[];
  onToggleCompare: (id: string) => void;
}

const priority = (i: Idea) => i.scores.impact * 0.4 + i.scores.novelty * 0.25 + i.scores.speed * 0.2 - i.scores.effort * 0.1 - i.scores.risk * 0.15;

export function IdeasView({ ideas, projects, onOpen, onAdd, onMove, onCopyTo, onDelete, onStatus, compare, onToggleCompare }: Props) {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState<IdeaStatus | "all">("all");
  const [sort, setSort] = useState<SortKey>("score");

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    let list = ideas.filter((i) => (status === "all" ? true : i.status === status));
    if (s) list = list.filter((i) => [i.title, i.question, i.method, i.notes, i.tags.join(" "), i.venues.join(" ")].join(" ").toLowerCase().includes(s));
    const by: Record<SortKey, (a: Idea, b: Idea) => number> = {
      updated: (a, b) => b.updatedAt.localeCompare(a.updatedAt),
      impact: (a, b) => b.scores.impact - a.scores.impact,
      effort: (a, b) => a.scores.effort - b.scores.effort,
      speed: (a, b) => b.scores.speed - a.scores.speed,
      score: (a, b) => priority(b) - priority(a),
    };
    return [...list].sort(by[sort]);
  }, [ideas, q, status, sort]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b px-6 py-3">
        <div className="relative w-[280px]">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск по идеям…" className="pl-8" />
        </div>
        <Select value={status} onValueChange={(v) => setStatus(v as IdeaStatus | "all")}>
          <SelectTrigger className="w-[160px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все статусы</SelectItem>
            {STATUS_ORDER.map((s) => <SelectItem key={s} value={s}>{STATUS_LABELS[s]}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
          <SelectTrigger className="w-[200px]"><ArrowUpDown className="size-3.5" /><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="score">По приоритету</SelectItem>
            <SelectItem value="impact">По влиянию</SelectItem>
            <SelectItem value="effort">По лёгкости</SelectItem>
            <SelectItem value="speed">По скорости</SelectItem>
            <SelectItem value="updated">По дате изменения</SelectItem>
          </SelectContent>
        </Select>
        <span className="text-xs text-muted-foreground">{filtered.length} из {ideas.length}</span>
        <div className="ml-auto flex items-center gap-2">
          {compare.length > 0 && <span className="text-xs text-muted-foreground">выбрано для сравнения: {compare.length}/3</span>}
          <Button onClick={onAdd}><Plus /> Новая идея</Button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        {filtered.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-muted-foreground">
            <p>Здесь пока пусто.</p>
            <Button variant="outline" onClick={onAdd}><Plus /> Добавить идею</Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
            {filtered.map((i) => (
              <IdeaCard
                key={i.id}
                idea={i}
                projects={projects}
                onOpen={onOpen}
                onMove={onMove}
                onCopyTo={onCopyTo}
                onDelete={onDelete}
                onStatus={onStatus}
                selected={compare.includes(i.id)}
                onToggleSelect={onToggleCompare}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
