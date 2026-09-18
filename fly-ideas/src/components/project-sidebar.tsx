import { useState } from "react";
import { Check, FolderPlus, Layers, MoreHorizontal, Pencil, Trash2, X } from "lucide-react";
import type { Project, Idea } from "@/data/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

interface Props {
  projects: Project[];
  ideas: Idea[];
  activeId: string | "all";
  onSelect: (id: string | "all") => void;
  onAdd: (name: string) => void;
  onRename: (id: string, name: string) => void;
  onDelete: (id: string) => void;
  onDropIdea: (ideaId: string, projectId: string) => void;
}

export function ProjectSidebar({ projects, ideas, activeId, onSelect, onAdd, onRename, onDelete, onDropIdea }: Props) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [dragOver, setDragOver] = useState<string | null>(null);

  const count = (pid: string) => ideas.filter((i) => i.projectId === pid).length;

  return (
    <aside className="flex h-full w-[260px] shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground">
      <div className="px-4 pt-4 pb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">Проекты</div>
      <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-2">
        <button
          onClick={() => onSelect("all")}
          className={cn(
            "flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors hover:bg-accent cursor-pointer",
            activeId === "all" && "bg-accent font-medium",
          )}
        >
          <Layers className="size-4 text-muted-foreground" />
          <span className="flex-1">Все идеи</span>
          <span className="font-mono text-xs text-muted-foreground">{ideas.length}</span>
        </button>

        {projects.map((p) => (
          <div
            key={p.id}
            onDragOver={(e) => {
              e.preventDefault();
              e.dataTransfer.dropEffect = "move";
              setDragOver(p.id);
            }}
            onDragLeave={() => setDragOver((d) => (d === p.id ? null : d))}
            onDrop={(e) => {
              e.preventDefault();
              const id = e.dataTransfer.getData("text/idea-id");
              if (id) onDropIdea(id, p.id);
              setDragOver(null);
            }}
            className={cn(
              "group flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent",
              activeId === p.id && "bg-accent font-medium",
              dragOver === p.id && "ring-2 ring-ring/60 bg-accent",
            )}
          >
            <span className="size-2.5 shrink-0 rounded-full" style={{ background: p.color }} />
            {editing === p.id ? (
              <form
                className="flex flex-1 items-center gap-1"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (editName.trim()) onRename(p.id, editName.trim());
                  setEditing(null);
                }}
              >
                <Input autoFocus value={editName} onChange={(e) => setEditName(e.target.value)} className="h-6 px-1.5 text-xs" />
                <Button type="submit" size="icon-sm" variant="ghost" className="size-6"><Check className="size-3" /></Button>
                <Button type="button" size="icon-sm" variant="ghost" className="size-6" onClick={() => setEditing(null)}><X className="size-3" /></Button>
              </form>
            ) : (
              <>
                <button onClick={() => onSelect(p.id)} className="flex-1 truncate text-left cursor-pointer" title={p.description || p.name}>
                  {p.name}
                </button>
                <span className="font-mono text-xs text-muted-foreground">{count(p.id)}</span>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button size="icon-sm" variant="ghost" className="size-6 opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100">
                      <MoreHorizontal className="size-3.5" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => { setEditing(p.id); setEditName(p.name); }}>
                      <Pencil /> Переименовать
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      variant="destructive"
                      disabled={projects.length <= 1}
                      onClick={() => {
                        if (confirm(`Удалить проект «${p.name}»? Идеи переедут в другой проект.`)) onDelete(p.id);
                      }}
                    >
                      <Trash2 /> Удалить
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            )}
          </div>
        ))}
      </nav>

      <div className="border-t p-2">
        {adding ? (
          <form
            className="flex items-center gap-1"
            onSubmit={(e) => {
              e.preventDefault();
              if (name.trim()) onAdd(name.trim());
              setName("");
              setAdding(false);
            }}
          >
            <Input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Название проекта" className="h-8 text-xs" />
            <Button type="submit" size="icon-sm" variant="ghost"><Check className="size-4" /></Button>
            <Button type="button" size="icon-sm" variant="ghost" onClick={() => setAdding(false)}><X className="size-4" /></Button>
          </form>
        ) : (
          <Button variant="ghost" className="w-full justify-start text-muted-foreground" onClick={() => setAdding(true)}>
            <FolderPlus /> Новый проект
          </Button>
        )}
        <p className="mt-2 px-2 text-[11px] leading-snug text-muted-foreground/70">Перетащи карточку идеи на проект, чтобы перенести.</p>
      </div>
    </aside>
  );
}
