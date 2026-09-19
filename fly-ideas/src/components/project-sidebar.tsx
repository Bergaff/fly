import { useState } from "react";
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
    <aside className="bg-sidebar text-sidebar-foreground flex h-full w-[248px] shrink-0 flex-col border-r">
      <div className="label border-b px-3 py-2">проекты</div>

      <nav className="flex flex-1 flex-col overflow-y-auto py-1">
        <button
          onClick={() => onSelect("all")}
          className={cn(
            "flex items-center gap-2 px-3 py-1.5 text-left text-[13px] hover:bg-accent cursor-pointer",
            activeId === "all" && "bg-accent font-medium",
          )}
        >
          <span className="flex-1">Все идеи</span>
          <span className="font-mono text-[11px] text-muted-foreground">{ideas.length}</span>
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
              "group flex items-center gap-2 px-3 py-1.5 text-[13px] hover:bg-accent",
              activeId === p.id && "bg-accent font-medium",
              dragOver === p.id && "bg-accent outline outline-1 outline-foreground",
            )}
          >
            <span className="size-2 shrink-0" style={{ background: p.color }} />
            {editing === p.id ? (
              <form
                className="flex flex-1 items-center gap-1"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (editName.trim()) onRename(p.id, editName.trim());
                  setEditing(null);
                }}
              >
                <Input autoFocus value={editName} onChange={(e) => setEditName(e.target.value)} className="h-6 flex-1 px-1 text-[12px]" />
                <Button type="submit" size="sm" variant="ghost" className="h-6 px-1.5">
                  ок
                </Button>
              </form>
            ) : (
              <>
                <button onClick={() => onSelect(p.id)} className="flex-1 truncate text-left cursor-pointer" title={p.description || p.name}>
                  {p.name}
                </button>
                <span className="font-mono text-[11px] text-muted-foreground">{count(p.id)}</span>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button size="sm" variant="ghost" className="h-6 px-1.5 text-muted-foreground" title="Проект">
                      ···
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => {
                        setEditing(p.id);
                        setEditName(p.name);
                      }}
                    >
                      Переименовать
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      variant="destructive"
                      disabled={projects.length <= 1}
                      onClick={() => {
                        if (confirm(`Удалить проект «${p.name}»? Идеи переедут в другой проект.`)) onDelete(p.id);
                      }}
                    >
                      Удалить
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
            <Input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Название проекта" className="h-7 flex-1 text-[12px]" />
            <Button type="submit" size="sm" variant="ghost" className="h-7 px-1.5">
              ок
            </Button>
            <Button type="button" size="sm" variant="ghost" className="h-7 px-1.5" onClick={() => setAdding(false)}>
              отмена
            </Button>
          </form>
        ) : (
          <Button variant="ghost" className="w-full justify-start text-muted-foreground" onClick={() => setAdding(true)}>
            Новый проект
          </Button>
        )}
        <p className="mt-2 px-1 font-mono text-[10px] leading-relaxed text-muted-foreground/70">Строку идеи можно перетащить на проект.</p>
      </div>
    </aside>
  );
}
