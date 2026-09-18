import { ArrowRightLeft, Copy, MoreHorizontal, Trash2, Clock, ExternalLink, GitBranch, ListChecks, FlaskConical, BookOpen } from "lucide-react";
import { DeadlineBadge } from "@/components/deadline-badge";
import type { Idea, IdeaStatus, Project } from "@/data/types";
import { STATUS_COLORS, STATUS_LABELS, STATUS_ORDER, checklistProgress } from "@/data/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ScoreBars } from "@/components/charts/score-bars";
import { cn } from "@/lib/utils";

interface Props {
  idea: Idea;
  projects: Project[];
  onOpen: (id: string) => void;
  onMove: (id: string, projectId: string) => void;
  onCopyTo: (id: string, projectId: string) => void;
  onDelete: (id: string) => void;
  onStatus: (id: string, status: IdeaStatus) => void;
  selected?: boolean;
  onToggleSelect?: (id: string) => void;
}

export function IdeaCard({ idea, projects, onOpen, onMove, onCopyTo, onDelete, onStatus, selected, onToggleSelect }: Props) {
  const others = projects.filter((p) => p.id !== idea.projectId);
  const prog = checklistProgress(idea);
  return (
    <Card
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/idea-id", idea.id);
        e.dataTransfer.effectAllowed = "move";
      }}
      className={cn(
        "group relative cursor-pointer gap-3 py-3 transition-all hover:-translate-y-0.5 hover:shadow-md hover:border-foreground/20",
        selected && "ring-2 ring-ring/60",
      )}
      onClick={() => onOpen(idea.id)}
    >
      <div className="absolute inset-x-0 top-0 h-0.5 rounded-t-xl" style={{ background: STATUS_COLORS[idea.status] }} />
      <CardHeader className="gap-2 px-4 pt-1">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-[15px] leading-snug">{idea.title}</CardTitle>
          <div className="flex shrink-0 items-center gap-1" onClick={(e) => e.stopPropagation()}>
            {onToggleSelect && (
              <input
                type="checkbox"
                checked={!!selected}
                onChange={() => onToggleSelect(idea.id)}
                className="size-4 accent-[var(--chart-2)] cursor-pointer"
                title="Выбрать для сравнения"
              />
            )}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon-sm" className="opacity-60 group-hover:opacity-100">
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuLabel>Статус</DropdownMenuLabel>
                {STATUS_ORDER.map((s) => (
                  <DropdownMenuItem key={s} onClick={() => onStatus(idea.id, s)}>
                    <span className="size-2 rounded-full" style={{ background: STATUS_COLORS[s] }} />
                    {STATUS_LABELS[s]}
                    {s === idea.status && <span className="ml-auto text-xs text-muted-foreground">текущий</span>}
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="flex items-center gap-1.5"><ArrowRightLeft className="size-3" /> Переместить в…</DropdownMenuLabel>
                {others.length === 0 && <DropdownMenuItem disabled>Нет других проектов</DropdownMenuItem>}
                {others.map((p) => (
                  <DropdownMenuItem key={p.id} onClick={() => onMove(idea.id, p.id)}>
                    <span className="size-2 rounded-full" style={{ background: p.color }} />
                    {p.name}
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
                <DropdownMenuLabel className="flex items-center gap-1.5"><Copy className="size-3" /> Копировать в…</DropdownMenuLabel>
                {projects.map((p) => (
                  <DropdownMenuItem key={p.id} onClick={() => onCopyTo(idea.id, p.id)}>
                    <span className="size-2 rounded-full" style={{ background: p.color }} />
                    {p.name}
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onClick={() => onDelete(idea.id)}>
                  <Trash2 /> Удалить
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
        {idea.question && <p className="line-clamp-2 text-[13px] text-muted-foreground">{idea.question}</p>}
      </CardHeader>
      <CardContent className="flex flex-col gap-3 px-4">
        <ScoreBars scores={idea.scores} compact />
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground" title="Прогресс чеклиста">
          <ListChecks className="size-3.5" />
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
            <div className="h-full rounded-full transition-all" style={{ width: `${prog.pct}%`, background: prog.pct === 100 ? "var(--chart-2)" : "var(--chart-1)" }} />
          </div>
          <span className="font-mono">{prog.done}/{prog.total}</span>
          {idea.dependsOn.length > 0 && <span className="flex items-center gap-0.5" title="Растёт из других идей"><GitBranch className="size-3" />{idea.dependsOn.length}</span>}
          {idea.experiments.length > 0 && <span className="flex items-center gap-0.5" title="Записей в журнале"><FlaskConical className="size-3" />{idea.experiments.length}</span>}
          {idea.citations.length > 0 && <span className="flex items-center gap-0.5" title="Источников"><BookOpen className="size-3" />{idea.citations.length}</span>}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <Badge variant="outline" className="gap-1.5" style={{ borderColor: STATUS_COLORS[idea.status] }}>
            <span className="size-1.5 rounded-full" style={{ background: STATUS_COLORS[idea.status] }} />
            {STATUS_LABELS[idea.status]}
          </Badge>
          <DeadlineBadge deadline={idea.deadline} />
          {idea.timeline && (
            <Badge variant="secondary" className="gap-1 font-normal">
              <Clock className="size-3" /> {idea.timeline}
            </Badge>
          )}
          {idea.tags.slice(0, 4).map((t) => (
            <Badge key={t} variant="secondary" className="font-normal text-muted-foreground">
              #{t}
            </Badge>
          ))}
          {idea.links.length > 0 && (
            <span className="ml-auto flex items-center gap-1 text-[11px] text-muted-foreground">
              <ExternalLink className="size-3" /> {idea.links.length}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
