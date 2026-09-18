import { useMemo, useRef, useState } from "react";
import { BrainView } from "@/views/brain-view";
import { useTheme } from "@/lib/theme";
import { fly, isElectron } from "@/lib/bridge";
import { useStore } from "@/data/store";
import { ProjectSidebar } from "@/components/project-sidebar";
import { IdeaDialog } from "@/components/idea-dialog";
import { IdeasView } from "@/views/ideas-view";
import { DashboardView } from "@/views/dashboard-view";
import { CompareView } from "@/views/compare-view";
import { LibraryView } from "@/views/library-view";
import { ReferenceDialog } from "@/components/reference-dialog";
import { LegalDialog, type LegalKind } from "@/components/legal-dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { TooltipProvider } from "@/components/ui/tooltip";

export default function App() {
  const store = useStore();
  const { state } = store;
  const [active, setActive] = useState<string | "all">("all");
  const [openId, setOpenId] = useState<string | null>(null);
  const [openRefId, setOpenRefId] = useState<string | null>(null);
  const [compare, setCompare] = useState<string[]>([]);
  const [tab, setTab] = useState("ideas");
  const [legal, setLegal] = useState<LegalKind | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const { theme, toggle: toggleTheme } = useTheme();

  const visible = useMemo(() => (active === "all" ? state.ideas : state.ideas.filter((i) => i.projectId === active)), [state.ideas, active]);
  const openIdea = state.ideas.find((i) => i.id === openId) ?? null;
  const compareIdeas = compare.map((id) => state.ideas.find((i) => i.id === id)).filter((i): i is NonNullable<typeof i> => !!i);
  const activeProject = state.projects.find((p) => p.id === active);
  const openRef = state.references.find((r) => r.id === openRefId) ?? null;
  const refUsedBy = openRef ? state.ideas.filter((i) => i.citations.some((c) => c.refId === openRef.id)).map((i) => ({ id: i.id, title: i.title })) : [];

  const toggleCompare = (id: string) =>
    setCompare((c) => (c.includes(id) ? c.filter((x) => x !== id) : c.length >= 3 ? [...c.slice(1), id] : [...c, id]));

  const addIdea = () => {
    const pid = active === "all" ? state.projects[0].id : active;
    const created = store.addIdea(pid);
    setOpenId(created.id);
  };

  const exportFile = async () => {
    const name = `fly-ideas-${new Date().toISOString().slice(0, 10)}.json`;
    if (fly) {
      const p = await fly.saveFile({ defaultName: name, content: store.exportJson(), filters: [{ name: "JSON", extensions: ["json"] }], kind: "exports" });
      if (p) alert(`Сохранено: ${p}`);
      return;
    }
    const blob = new Blob([store.exportJson()], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
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
  const importClick = async () => {
    if (!fly) return fileRef.current?.click();
    const r = await fly.openFile({ filters: [{ name: "JSON", extensions: ["json"] }], kind: "exports" });
    if (!r) return;
    try {
      store.importJson(r.content);
    } catch (e) {
      alert(`Не удалось импортировать: ${(e as Error).message}`);
    }
  };

  const counters: Record<string, string> = {
    ideas: String(visible.length),
    dashboard: `${state.ideas.filter((i) => ["exploring", "active", "drafting"].includes(i.status)).length} в работе`,
    compare: compare.length ? `${compare.length} из 3` : "",
    library: String(state.references.length),
    brain: "",
  };

  return (
    <TooltipProvider>
      <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
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
          <header className="flex flex-wrap items-center gap-x-5 gap-y-2 border-b px-4 py-2">
            <div className="flex items-center gap-2.5">
              <span className="flex size-8 shrink-0 items-center justify-center border font-mono text-[12px] tracking-[0.1em]">FI</span>
              <div className="leading-tight">
                <div className="text-[13px] font-semibold tracking-[-0.01em]">Fly Ideas</div>
                <div className="label">{activeProject ? activeProject.name : `все проекты, идей: ${state.ideas.length}`}</div>
              </div>
            </div>

            <Tabs value={tab} onValueChange={setTab}>
              <TabsList>
                {(
                  [
                    ["ideas", "Идеи"],
                    ["dashboard", "Дашборд"],
                    ["compare", "Сравнение"],
                    ["library", "Библиотека"],
                    ["brain", "Мозг"],
                  ] as const
                ).map(([key, label]) => (
                  <TabsTrigger key={key} value={key}>
                    {label}
                    {counters[key] && <span className="font-mono text-[10px] text-muted-foreground">{counters[key]}</span>}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>

            <div className="ml-auto flex items-center gap-1.5">
              <span className="label hidden xl:inline">источник: {isElectron ? "локальное окно" : "браузер, часть функций недоступна"}</span>
              <Button variant="ghost" size="sm" onClick={toggleTheme} title="Переключить светлую и тёмную тему">
                {theme === "dark" ? "светлая" : "тёмная"}
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">Меню</Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-64">
                  <DropdownMenuLabel>Данные</DropdownMenuLabel>
                  <DropdownMenuItem onClick={exportFile}>Выгрузить JSON…</DropdownMenuItem>
                  <DropdownMenuItem onClick={importClick}>Загрузить JSON…</DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuLabel>Документы</DropdownMenuLabel>
                  <DropdownMenuItem onClick={() => setLegal("terms")}>Условия использования</DropdownMenuItem>
                  <DropdownMenuItem onClick={() => setLegal("privacy")}>Политика конфиденциальности</DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem variant="destructive" onClick={() => confirm("Сбросить всё к стартовому набору идей?") && store.reset()}>
                    Сброс к стартовым идеям
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
            <TabsContent value="library" className="min-h-0">
              <LibraryView
                references={state.references}
                ideas={visible}
                allIdeas={state.ideas}
                scopeLabel={activeProject ? `«${activeProject.name}»` : "видимые идеи"}
                onOpen={setOpenRefId}
                onAdd={() => setOpenRefId(store.addReference().id)}
                onOpenIdea={(id) => {
                  setTab("ideas");
                  setOpenId(id);
                }}
              />
            </TabsContent>
            <TabsContent value="brain" className="min-h-0 overflow-hidden">
              <BrainView ideas={state.ideas} onAddJournalEntry={(ideaId, e) => store.addExperiment(ideaId, { ...e, outcome: "inconclusive" })} />
            </TabsContent>
            <TabsContent value="compare" className="min-h-0 overflow-hidden">
              <CompareView ideas={compareIdeas} all={state.ideas} onRemove={(id) => setCompare((c) => c.filter((x) => x !== id))} onOpen={setOpenId} />
            </TabsContent>
          </Tabs>
        </main>

        <IdeaDialog
          idea={openIdea}
          allIdeas={state.ideas}
          references={state.references}
          projects={state.projects}
          onCreateReference={(title) => store.addReference({ title })}
          onOpenReference={(id) => {
            setOpenId(null);
            setTimeout(() => setOpenRefId(id), 0);
          }}
          onOpenOther={(id) => setTimeout(() => setOpenId(id), 0)}
          onClose={() => setOpenId(null)}
          onSave={store.updateIdea}
          onDelete={store.deleteIdea}
        />
        <ReferenceDialog reference={openRef} usedBy={refUsedBy} onClose={() => setOpenRefId(null)} onSave={store.updateReference} onDelete={store.deleteReference} />
        <LegalDialog kind={legal} onClose={() => setLegal(null)} />
      </div>
    </TooltipProvider>
  );
}
