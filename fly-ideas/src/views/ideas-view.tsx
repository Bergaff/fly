import { useMemo, useState } from "react";
import type { Idea, IdeaStatus, Project } from "@/data/types";
import { STATUS_LABELS, STATUS_ORDER } from "@/data/types";
import { priorityOf } from "@/lib/priority";
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
      score: (a, b) => priorityOf(b) - priorityOf(a),
    };
    return [...list].sort(by[sort]);
  }, [ideas, q, status, sort]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b px-4 py-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Поиск по идеям" className="w-[280px]" />
        <Select value={status} onValueChange={(v) => setStatus(v as IdeaStatus | "all")}>
          <SelectTrigger className="w-[160px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Все статусы</SelectItem>
            {STATUS_ORDER.map((s) => (
              <SelectItem key={s} value={s}>
                {STATUS_LABELS[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
          <SelectTrigger className="w-[190px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="score">По приоритету</SelectItem>
            <SelectItem value="impact">По влиянию</SelectItem>
            <SelectItem value="effort">По лёгкости</SelectItem>
            <SelectItem value="speed">По скорости</SelectItem>
            <SelectItem value="updated">По дате изменения</SelectItem>
          </SelectContent>
        </Select>
        <span className="label">
          {filtered.length} из {ideas.length}
        </span>
        <div className="ml-auto flex items-center gap-3">
          <span className="label">для сравнения: {compare.length}/3</span>
          <Button onClick={onAdd}>Новая идея</Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {filtered.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <p className="text-[13px] text-muted-foreground">Ничего не найдено.</p>
            <Button variant="outline" onClick={onAdd}>
              Добавить идею
            </Button>
          </div>
        ) : (
          <table className="w-full border-collapse text-left">
            <thead className="sticky top-0 z-10 bg-background">
              <tr className="border-b">
                <th className="label w-8 py-2 pl-3 font-normal">сравн.</th>
                <th className="label w-[130px] py-2 pr-3 font-normal">статус</th>
                <th className="label py-2 pr-4 font-normal">идея</th>
                <th className="label w-[170px] py-2 pr-4 font-normal">оценки</th>
                <th className="label w-[140px] py-2 pr-4 font-normal">этапы</th>
                <th className="label w-[150px] py-2 pr-4 font-normal">срок</th>
                <th className="label w-[110px] py-2 pr-3 text-right font-normal">действия</th>
              </tr>
            </thead>
            <tbody>
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
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
