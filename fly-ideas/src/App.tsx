import { useMemo, useRef, useState } from "react";
import { BarChart3, Brain, Download, GitCompare, LayoutGrid, RotateCcw, Settings2, Upload } from "lucide-react";
import { useStore } from "@/data/store";
import { ProjectSidebar } from "@/components/project-sidebar";
import { IdeaDialog } from "@/components/idea-dialog";
import { IdeasView } from "@/views/ideas-view";
import { DashboardView } from "@/views/dashboard-view";
import { CompareView } from "@/views/compare-view";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { TooltipProvider } from "@/components/ui/tooltip";
import { ShimmerText } from "@/components/charts/shimmer-text";

export default function App() {
  const store = useStore();
  const { state } = store;
  const [active, setActive] = useState<string | "all">("all");
  const [openId, setOpenId] = useState<string | null>(null);
  const [compare, setCompare] = useState<string[]>([]);
  const [tab, setTab] = useState("ideas");
  const fileRef = useRef<HTMLInputElement>(null);

  const visible = useMemo(() => (active === "all" ? state.ideas : state.ideas.filter((i) => i.projectId === active)), [state.ideas, active]);
  const openIdea = state.ideas.find((i) => i.id === openId) ?? null;
  const compareIdeas = compare.map((id) => state.ideas.find((i) => i.id === id)).filter((i): i is NonNullable<typeof i> => !!i);
  const activeProject = state.projects.find((p) => p.id === active);

  const toggleCompare = (id: string) =>
    setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 3 ? [...c.slice(1), id] : [...c, id]));

  const addIdea = () => {
    const pid = active === "all" ? state.projects[0].id : active;
    const created = store.addIdea(pid);
    setOpenId(created.id);
  };

  const exportFile = () => {
    const blob = new Blob([store.exportJson()], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `fly-ideas-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  };

  const importFile = async (f: File) => {
    try {
      store.importJson(await f.text());
    } catch (e) {
      alert(`Не удалось импортировать: ${(e as Error).message}`);
    }
  };

  return (
    <TooltipProvider>
      <div className="dark flex h-screen w-screen overflow-hidden bg-background text-foreground">
        <ProjectSidebar
          projects={state.projects}
          ideas={state.ideas}
          activeId={active}
          onSelect={setActive}
          onAdd={(n) => store.addProject(n)}
          onRename={(id, name) => store.updateProject(id, { name })}
          onDelete={(id) => {
            store.deleteProject(id);
            if (active === id) setActive("all");
          }}
          onDropIdea={store.moveIdea}
        />
        <main className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center gap-3 border-b px-6 py-3">
            <div className="flex items-center gap-2">
              <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-[var(--chart-2)] to-[var(--chart-1)] text-background">
                <Brain className="size-4" />
              </div>
              <div className="leading-tight">
                <div className="text-sm font-semibold">Fly Ideas</div>
                <div className="text-[11px] text-muted-foreground">
                  {activeProject ? activeProject.name : <ShimmerText>все проекты · {state.ideas.length} идей</ShimmerText>}
                </div>
              </div>
            </div>
            <Tabs value={tab} onValueChange={setTab} className="ml-6">
              <TabsList>
                <TabsTrigger value="ideas"><LayoutGrid /> Идеи</TabsTrigger>
                <TabsTrigger value="dashboard"><BarChart3 /> Дашборд</TabsTrigger>
                <TabsTrigger value="compare"><GitCompare /> Сравнение {compare.length > 0 && <span className="rounded-full bg-primary px-1.5 text-[10px] text-primary-foreground">{compare.length}</span>}</TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="ml-auto">
              <DropdownMenu>
                <DropdownMenuTrigger asChild><Button variant="ghost" size="icon"><Settings2 /></Button></DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuItem onClick={exportFile}><Download /> Выгрузить JSON</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => fileRef.current?.click()}><Upload /> Загрузить JSON</DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem variant="destructive" onClick={() => confirm("Сбросить всё к стартовому набору идей?") && store.reset()}>
                    <RotateCcw /> Сброс к стартовым идеям
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <input ref={fileRef} type="file" accept="application/json" className="hidden" onChange={(e) => e.target.files?.[0] && importFile(e.target.files[0])} />
            </div>
          </header>

          <Tabs value={tab} onValueChange={setTab} className="min-h-0 flex-1 gap-0">
            <TabsContent value="ideas" className="min-h-0">
              <IdeasView
                ideas={visible}
                projects={state.projects}
                activeProject={active}
                onOpen={setOpenId}
                onAdd={addIdea}
                onMove={store.moveIdea}
                onCopyTo={(id, pid) => store.duplicateIdea(id, pid)}
                onDelete={(id) => confirm("Удалить идею?") && store.deleteIdea(id)}
                onStatus={store.setStatus}
                compare={compare}
                onToggleCompare={toggleCompare}
              />
            </TabsContent>
            <TabsContent value="dashboard" className="min-h-0 overflow-hidden">
              <DashboardView ideas={visible} onOpen={setOpenId} />
            </TabsContent>
            <TabsContent value="compare" className="min-h-0 overflow-hidden">
              <CompareView ideas={compareIdeas} all={state.ideas} onRemove={(id) => setCompare((c) => c.filter((x) => x !== id))} onOpen={setOpenId} />
            </TabsContent>
          </Tabs>
        </main>

        <IdeaDialog idea={openIdea} projects={state.projects} onClose={() => setOpenId(null)} onSave={store.updateIdea} onDelete={store.deleteIdea} />
      </div>
    </TooltipProvider>
  );
}
