import type { Idea, IdeaStatus, Project } from "@/data/types";
import { STATUS_COLORS, STATUS_LABELS, STATUS_ORDER, deadlineInfo } from "@/data/types";
import { priorityOf } from "@/lib/priority";
import { checklistProgress } from "@/data/types";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { DeadlineBadge } from "@/components/deadline-badge";
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

/** Строка описи идей: плотная таблица вместо витрины карточек. */
export function IdeaCard({ idea, projects, onOpen, onMove, onCopyTo, onDelete, onStatus, selected, onToggleSelect }: Props) {
  const prog = checklistProgress(idea);
  const others = projects.filter((p) => p.id !== idea.projectId);
  const scores = idea.scores;
  const row = priorityOf(idea);

  return (
    <tr
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/idea-id", idea.id);
        e.dataTransfer.effectAllowed = "move";
      }}
      className={cn("group cursor-pointer border-b align-top hover:bg-accent/50", selected && "bg-accent/40")}
      onClick={() => onOpen(idea.id)}
    >
      <td className="py-2 pl-3" onClick={(e) => e.stopPropagation()}>
        <span title="Отметить для сравнения" className="inline-flex">
          <input type="checkbox" checked={!!selected} onChange={() => onToggleSelect?.(idea.id)} className="cursor-pointer" />
        </span>
      </td>

      <td className="w-[130px] py-2 pr-3">
        <span className="flex items-center gap-1.5">
          <span className="size-2 shrink-0" style={{ background: STATUS_COLORS[idea.status] }} />
          <span className="label truncate">{STATUS_LABELS[idea.status]}</span>
        </span>
        {idea.timeline && <div className="mt-1 font-mono text-[10px] text-muted-foreground">{idea.timeline}</div>}
      </td>

      <td className="min-w-0 py-2 pr-4">
        <div className="text-[13px] leading-snug font-medium tracking-[-0.01em]">{idea.title}</div>
        {idea.question && <div className="mt-0.5 line-clamp-1 text-[11px] text-muted-foreground">{idea.question}</div>}
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[10px] text-muted-foreground">
          {idea.tags.slice(0, 5).map((t) => (
            <span key={t}>#{t}</span>
          ))}
          {idea.citations.length > 0 && <span>источников: {idea.citations.length}</span>}
          {idea.experiments.length > 0 && <span>журнал: {idea.experiments.length}</span>}
          {idea.dependsOn.length > 0 && <span>растёт из: {idea.dependsOn.length}</span>}
          {idea.links.length > 0 && <span>ссылок: {idea.links.length}</span>}
        </div>
      </td>

      <td className="w-[170px] py-2 pr-4 font-mono text-[10px]">
        <div className="flex items-baseline gap-2">
          <span className="text-[13px]">{row.toFixed(1)}</span>
          <span className="text-muted-foreground">
            вл {scores.impact} / нв {scores.novelty} / тр {scores.effort} / рс {scores.risk}
          </span>
        </div>
      </td>

      <td className="w-[140px] py-2 pr-4">
        <div className="flex items-center gap-2">
          <Progress value={prog.pct} className="w-20" color={prog.pct === 100 ? "var(--chart-2)" : "var(--foreground)"} />
          <span className="font-mono text-[10px] text-muted-foreground">
            {prog.done}/{prog.total}
          </span>
        </div>
      </td>

      <td className="w-[150px] py-2 pr-4">
        {idea.deadline ? <DeadlineBadge deadline={idea.deadline} /> : <span className="font-mono text-[10px] text-muted-foreground/60">без срока</span>}
      </td>

      <td className="w-[110px] py-2 pr-3 text-right" onClick={(e) => e.stopPropagation()}>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" title="Действия с идеей">···</Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>Статус</DropdownMenuLabel>
            {STATUS_ORDER.map((s) => (
              <DropdownMenuItem key={s} onClick={() => onStatus(idea.id, s)}>
                <span className="size-2 shrink-0" style={{ background: STATUS_COLORS[s] }} />
                {STATUS_LABELS[s]}
                {s === idea.status && <span className="label ml-auto">текущий</span>}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuLabel>Переместить в</DropdownMenuLabel>
            {others.length === 0 && <DropdownMenuItem disabled>нет других проектов</DropdownMenuItem>}
            {others.map((p) => (
              <DropdownMenuItem key={p.id} onClick={() => onMove(idea.id, p.id)}>
                <span className="size-2 shrink-0" style={{ background: p.color }} />
                {p.name}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuLabel>Копировать в</DropdownMenuLabel>
            {projects.map((p) => (
              <DropdownMenuItem key={p.id} onClick={() => onCopyTo(idea.id, p.id)}>
                <span className="size-2 shrink-0" style={{ background: p.color }} />
                {p.name}
              </DropdownMenuItem>
            ))}
            <DropdownMenuSeparator />
            <DropdownMenuItem variant="destructive" onClick={() => onDelete(idea.id)}>
              Удалить
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </td>
    </tr>
  );
}

export { deadlineInfo };
