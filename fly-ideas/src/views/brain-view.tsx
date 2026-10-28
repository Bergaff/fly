import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Idea, Project, Reference } from "@/data/types";
import {
  fly, fmtBytes, isElectron,
  type DataItem, type AgentInfo, type EnvInfo, type EnvSetupOutput, type PythonCandidate, type ExternalSource, type LlmMessage, type LlmProvider,
  type Paths, type Permissions, type ProjectPaths, type RunInfo, type ScriptInfo,
} from "@/lib/bridge";
import { parseReferencesFromText } from "@/lib/refparse";
import { TASK_PRESETS, presetForIdea, presetForScript, type TaskPreset } from "@/lib/task-presets";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface Props {
  ideas: Idea[];
  projects: Project[];
  activeProject: string | "all";
  focusIdeaId?: string | null;
  onClearFocusIdea?: () => void;
  onSelectProject: (id: string | "all") => void;
  onAddProject: (name: string) => Project;
  onAddIdea: (projectId: string, title: string) => Idea;
  onOpenIdeaCard: (ideaId: string) => void;
  onAddJournalEntry: (ideaId: string, entry: { title: string; params: string; result: string; conclusion: string }) => void;
  onAddReferences: (items: Partial<Reference>[]) => void;
}

const CODE_PROMPT = `Ты научный ассистент аспиранта, который работает с вычислительной моделью мозга дрозофилы
(LIF-модель Shiu et al. 2024 на коннектоме FlyWire v783, репозиторий eonsystemspbc/fly-brain; numpy, Brian2, pandas).
Пользователь пишет код с помощью ИИ и интересуется когнитивистикой: память, обучение в грибовидных телах,
интерференция, социальное обучение.

Правила:
- отвечай по-русски, кратко и конкретно;
- если даёшь код, верни полный запускаемый файл Python и начни его строкой "# file: имя_латиницей.py";
- скрипт получает переменные окружения: FLY_DATA (папка данных коннектома), FLY_RUN_DIR (папка этого прогона,
  туда писать summary.json и графики png), FLY_SCRIPTS (папка кода проекта), FLY_PROJECT (имя проекта);
- добавь argparse с --seed и основными параметрами протокола, значения по умолчанию обязательны;
- в summary.json положи args, метрики и имена созданных файлов;
- не выдумывай API Brian2: если не уверен, скажи, что нужно проверить в документации;
- честно указывай ограничения LIF-модели.`;

const LIT_PROMPT = `Ты помогаешь аспиранту искать научную литературу по вычислительной нейробиологии дрозофилы,
обучению и памяти, грибовидным телам, коннектомам и когнитивистике.
На вопрос верни 5-8 публикаций, каждая отдельной строкой строго в формате:
Авторы (год). Название. Журнал или препринт. DOI: 10.xxxx/yyyy
Без нумерации, без вступлений и без общих рассуждений. Если DOI неизвестен, укажи URL.
Ниже списка добавь короткий абзац (2-3 предложения) о том, что из этого ближе всего к вопросу.`;

const PROVIDERS: { id: LlmProvider; label: string; hint: string; models: [string, string][] }[] = [
  { id: "deepseek", label: "DeepSeek, код", hint: "ключ с platform.deepseek.com", models: [["deepseek-chat", "deepseek-chat, быстрый"], ["deepseek-reasoner", "deepseek-reasoner, думает дольше"]] },
  { id: "perplexity", label: "Perplexity, литература", hint: "ключ с perplexity.ai/settings/api", models: [["sonar", "sonar, быстрая"], ["sonar-pro", "sonar-pro, подробная"]] },
];

// ================================================================
export function BrainView({
  ideas,
  projects,
  activeProject,
  focusIdeaId,
  onClearFocusIdea,
  onSelectProject,
  onAddProject,
  onAddIdea,
  onOpenIdeaCard,
  onAddJournalEntry,
  onAddReferences,
}: Props) {
  const [tab, setTab] = useState<"work" | "setup">("work");
  const [help, setHelp] = useState(false);

  useEffect(() => {
    if (focusIdeaId) setTab("work");
  }, [focusIdeaId]);

  if (!isElectron) return <WebFallback />;

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b px-3 py-1.5">
        <span className="label">рабочее место</span>
        <div className="flex items-baseline gap-0.5">
          {(["work", "setup"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "cursor-pointer border-b px-2.5 py-1 text-[12px]",
                tab === t ? "border-foreground text-foreground" : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {t === "work" ? "Код и результаты" : "Данные и окружение"}
            </button>
          ))}
        </div>
        <Button size="sm" variant="ghost" className="ml-auto" onClick={() => setHelp(true)}>
          Как начать
        </Button>
      </div>

      {tab === "work" ? (
        <Workspace
          ideas={ideas}
          projects={projects}
          activeProject={activeProject}
          focusIdeaId={focusIdeaId}
          onClearFocusIdea={onClearFocusIdea}
          onSelectProject={onSelectProject}
          onAddProject={onAddProject}
          onAddIdea={onAddIdea}
          onOpenIdeaCard={onOpenIdeaCard}
          onAddJournalEntry={onAddJournalEntry}
          onAddReferences={onAddReferences}
        />
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <div className="flex flex-col gap-4">
            <DataPanel />
            <EnvPanel />
          </div>
        </div>
      )}

      <HelpDialog open={help} onClose={() => setHelp(false)} />
    </div>
  );
}

function WebFallback() {
  return (
    <div className="flex h-full items-center justify-center p-3">
      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle>Доступно только в окне программы</CardTitle>
          <CardDescription>
            Рабочее место работает через Electron: нужен доступ к диску, Python и папкам проекта. В браузере вкладка отключена.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-[12px] text-muted-foreground">
          Запусти <code className="bg-muted px-1">START.bat</code>: откроется окно, где появятся файлы проекта, редактор, прогоны и помощник.
        </CardContent>
      </Card>
    </div>
  );
}

// ================================================================
/** Строка «папка: путь [выбрать] [открыть] [сбросить]» */
function PathStrip({ label, value, onChoose, onOpen, onReset, isDefault }: { label: string; value: string; onChoose: () => void; onOpen: () => void; onReset: () => void; isDefault: boolean }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="label w-[74px] shrink-0">{label}</span>
      <span className="min-w-0 flex-1 truncate font-mono text-[11px] text-muted-foreground" title={value}>
        {value}
      </span>
      <Button size="sm" variant="ghost" onClick={onChoose}>
        выбрать
      </Button>
      <Button size="sm" variant="ghost" onClick={onOpen}>
        открыть
      </Button>
      {!isDefault && (
        <Button size="sm" variant="ghost" onClick={onReset} title="Вернуть папку по умолчанию">
          сбросить
        </Button>
      )}
    </div>
  );
}

// ================================================================
/** Компактный переключатель проекта прямо в панели кода, результатов и помощника */
function ProjectInlinePicker({
  projects,
  value,
  onChange,
  onCreate,
  className,
  triggerClassName,
}: {
  projects: Project[];
  value: string;
  onChange: (projectId: string) => void;
  onCreate?: () => void;
  className?: string;
  triggerClassName?: string;
}) {
  return (
    <div className={cn("flex flex-1 items-center gap-1 sm:flex-initial", className)}>
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className={cn("h-6 min-w-[160px] max-w-[235px] text-[11px]", triggerClassName)} title="Проект, в чьи папки идут код и результаты прогонов">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {projects.map((p) => (
            <SelectItem key={p.id} value={p.id}>
              <span className="mr-1.5 inline-block size-2 shrink-0" style={{ background: p.color }} />
              {p.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {onCreate && (
        <Button size="sm" variant="ghost" className="h-6 px-1.5 font-mono text-[10.5px]" onClick={onCreate} title="Создать новый проект со своими папками кода и результатов">
          + проект
        </Button>
      )}
    </div>
  );
}

function Workspace({
  ideas,
  projects,
  activeProject,
  focusIdeaId,
  onClearFocusIdea,
  onSelectProject,
  onAddProject,
  onAddIdea,
  onOpenIdeaCard,
  onAddJournalEntry,
  onAddReferences,
}: Omit<Props, "activeProject"> & { activeProject: string | "all" }) {
  const pid = activeProject === "all" ? projects[0]?.id ?? "project" : activeProject;
  const [paths, setPaths] = useState<ProjectPaths | null>(null);
  const [perms, setPerms] = useState<Permissions | null>(null);
  const [showFolderSettings, setShowFolderSettings] = useState(false);
  const [files, setFiles] = useState<ScriptInfo[]>([]);
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [dirty, setDirty] = useState(false);
  const [args, setArgs] = useState("");
  const [activeRuns, setActiveRuns] = useState<Record<string, { runId: string; runDir: string } | undefined>>({});
  const [logsByProject, setLogsByProject] = useState<Record<string, string>>({});
  const [selRun, setSelRun] = useState<RunInfo | null>(null);
  const [detail, setDetail] = useState<{ log: string; summary: Record<string, unknown> | null } | null>(null);
  const [images, setImages] = useState<{ name: string; dataUrl: string }[]>([]);
  const [viewFile, setViewFile] = useState<{ name: string; text: string } | null>(null);
  const [ideaId, setIdeaId] = useState<string>(() => ideas.find((i) => i.projectId === pid)?.id ?? ideas[0]?.id ?? "");
  const [workspaceIdeaId, setWorkspaceIdeaId] = useState<string>(() => focusIdeaId || ideas.find((i) => i.projectId === pid)?.id || "");
  const [rightTab, setRightTab] = useState<"presets" | "chat">("presets");
  const [selectedPresetIdea, setSelectedPresetIdea] = useState<string>(
    focusIdeaId || ideas.find((i) => i.projectId === pid)?.id || ideas[0]?.id || TASK_PRESETS[0].ideaId,
  );
  const [added, setAdded] = useState(false);
  const [saveNote, setSaveNote] = useState("");
  const [logCopied, setLogCopied] = useState(false);
  const [missingPackage, setMissingPackage] = useState<string | null>(null);
  const [installingPackages, setInstallingPackages] = useState(false);
  const pendingOpenScript = useRef<{ pid: string; file: string; autoRunArgs?: string } | null>(null);
  const pendingOpenRun = useRef<{ pid: string; runPath: string } | null>(null);
  const pendingPresetIdea = useRef<string | null>(null);
  const lastRunByScope = useRef<Record<string, { scriptName: string; args: string[] } | undefined>>({});
  const project = projects.find((p) => p.id === pid);
  const scopeId = workspaceIdeaId ? `idea:${workspaceIdeaId}` : pid;
  const selectedWorkspaceIdea = ideas.find((i) => i.id === workspaceIdeaId);
  const scopeLabel = selectedWorkspaceIdea?.title ?? project?.name ?? pid;
  const pidRef = useRef(scopeId);
  pidRef.current = scopeId;
  const logRef = useRef<HTMLDivElement>(null);

  const runId = activeRuns[scopeId]?.runId ?? null;
  const liveLog = logsByProject[scopeId] ?? "";
  const displayLog = runId ? liveLog : selRun ? detail?.log ?? liveLog : liveLog;
  const otherProjects = useMemo(() => projects.filter((p) => p.id !== pid), [projects, pid]);

  const orderedIdeasForJournal = useMemo(() => {
    const mine = ideas.filter((i) => i.projectId === pid);
    const rest = ideas.filter((i) => i.projectId !== pid);
    return [...mine, ...rest];
  }, [ideas, pid]);

  const loadFiles = useCallback(async (targetPid = scopeId) => {
    const bridge = fly;
    if (!bridge) return [];
    const p = await bridge.projectPaths(targetPid);
    const sc = await bridge.listScripts(targetPid);
    const rn = await bridge.listRuns(targetPid);
    if (pidRef.current === targetPid) {
      setPaths(p);
      setFiles(sc);
    }
    return rn;
  }, [scopeId]);

  const refreshRuns = useCallback(async (targetPid = scopeId) => {
    const bridge = fly;
    if (!bridge) return [];
    const r = await bridge.listRuns(targetPid);
    if (pidRef.current === targetPid) setRuns(r);
    return r;
  }, [scopeId]);

  function openRun(r: RunInfo) {
    const bridge = fly;
    if (!bridge) return;
    setSelRun(r);
    setViewFile(null);
    setImages([]);
    setDetail(null);
    void bridge.readRun(r.path).then(setDetail);
    const imgs = r.files.filter((f) => /\.(png|jpe?g|svg|gif)$/i.test(f));
    void Promise.all(
      imgs.map(async (name) => {
        const res = await bridge.readRunFile(r.path, name);
        return res.kind === "image" ? { name, dataUrl: res.dataUrl } : null;
      }),
    ).then((x) => setImages(x.filter((v): v is { name: string; dataUrl: string } => !!v)));
  }

  const startScriptInProject = useCallback(async (targetPid: string, scriptName: string, argList: string[]) => {
    const bridge = fly;
    if (!bridge) return;
      setLogsByProject((prev) => ({ ...prev, [targetPid]: "" }));
      if (pidRef.current === targetPid) {
      setDetail(null);
      setImages([]);
      setViewFile(null);
    }
    lastRunByScope.current[targetPid] = { scriptName, args: argList };
    if (pidRef.current === targetPid) setMissingPackage(null);
    try {
      const r = await bridge.runScript(targetPid, scriptName, argList);
      setActiveRuns((prev) => ({ ...prev, [targetPid]: { runId: r.runId, runDir: r.runDir } }));
      if (pidRef.current === targetPid) setAdded(false);
      setLogsByProject((prev) => ({
        ...prev,
        [targetPid]: `$ python ${scriptName} ${argList.join(" ")}\n-> ${r.runDir}\n\n`,
      }));
    } catch (e) {
      setLogsByProject((prev) => ({
        ...prev,
        [targetPid]: `не удалось запустить: ${(e as Error).message}\n`,
      }));
    }
  }, []);

  useEffect(() => {
    const keepProjectScope =
      (pendingOpenScript.current?.pid === pid && !pendingOpenScript.current.pid.startsWith("idea:")) ||
      (pendingOpenRun.current?.pid === pid && !pendingOpenRun.current.pid.startsWith("idea:"));
    if (keepProjectScope) {
      setWorkspaceIdeaId("");
      setIdeaId(ideas.find((i) => i.projectId === pid)?.id ?? "");
      return;
    }
    if (selectedWorkspaceIdea?.projectId === pid) return;
    const inProject = ideas.find((i) => i.projectId === pid);
    setWorkspaceIdeaId(inProject?.id ?? "");
    setIdeaId(inProject?.id ?? "");
  }, [pid, selectedWorkspaceIdea?.projectId, ideas]);

  useEffect(() => {
    let cancelled = false;
    setCurrent(null);
    setCode("");
    setDirty(false);
    setSelRun(null);
    setDetail(null);
    setImages([]);
    setViewFile(null);
    setSaveNote("");
    setMissingPackage(null);
    void loadFiles(scopeId).then(async (rn) => {
      if (cancelled) return;
      setRuns(rn);
      if (pendingOpenRun.current && pendingOpenRun.current.pid === scopeId) {
        const targetR = rn.find((x) => x.path === pendingOpenRun.current!.runPath) ?? rn[0];
        pendingOpenRun.current = null;
        if (targetR) openRun(targetR);
      }
      if (pendingOpenScript.current && pendingOpenScript.current.pid === scopeId) {
        const req = pendingOpenScript.current;
        pendingOpenScript.current = null;
        const bridge = fly;
        if (bridge) {
          const txt = await bridge.readScript(scopeId, req.file);
          if (!cancelled) {
            setCurrent(req.file);
            setCode(txt);
            setDirty(false);
            setSaveNote(`открыт в рабочем пространстве: ${req.file}`);
            if (req.autoRunArgs !== undefined) {
              setArgs(req.autoRunArgs);
              const argList = req.autoRunArgs.split(/\s+/).filter(Boolean);
              await startScriptInProject(scopeId, req.file, argList);
            }
          }
        }
      }
    });
    return () => {
      cancelled = true;
    };
  }, [scopeId, loadFiles, workspaceIdeaId, startScriptInProject]);

  useEffect(() => {
    void fly!.getPermissions().then(setPerms);
  }, []);

  useEffect(() => {
    const bridge = fly;
    if (!bridge) return;
    return bridge.onRunOutput((p) => {
      const evPid = p.projectId || pidRef.current;
      const missingModule = p.stream === "stderr" ? p.text.match(/No module named ["']([^"']+)["']/)?.[1] : null;
      if (missingModule && evPid === pidRef.current) {
        setMissingPackage(missingModule);
        setSaveNote(`Python-пакет ${missingModule} не установлен. Его можно установить и повторить запуск кнопкой рядом с логом.`);
      }
      setLogsByProject((prev) => ({
        ...prev,
        [evPid]: ((prev[evPid] ?? "") + p.text).slice(-60000),
      }));
      if (p.stream === "exit") {
        let finishedDir: string | undefined = p.runDir;
        setActiveRuns((prev) => {
          finishedDir = finishedDir || prev[evPid]?.runDir;
          const next = { ...prev };
          delete next[evPid];
          return next;
        });
        if (evPid === pidRef.current) {
          void refreshRuns(evPid).then((list) => {
            const target = finishedDir ? list.find((r) => r.path === finishedDir) : list[0];
            if (target) openRun(target);
          });
        } else {
          const doneProj = projects.find((pr) => pr.id === evPid);
          const doneIdea = evPid.startsWith("idea:") ? ideas.find((item) => item.id === evPid.slice(5)) : undefined;
          setSaveNote(`прогон завершён в «${doneIdea?.title ?? doneProj?.name ?? evPid}»`);
        }
      }
    });
  }, [refreshRuns, projects, ideas]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [liveLog]);

  const saveBeforeWorkspaceChange = useCallback(async () => {
    if (!dirty || !current || !fly) return true;
    const shouldSave = confirm(`Сохранить изменения в файле ${current} перед переключением рабочего пространства?`);
    if (!shouldSave) return true;
    await fly.writeScript(scopeId, current, code, { allowOverwrite: true });
    setDirty(false);
    return true;
  }, [dirty, current, scopeId, code]);

  const switchWorkspaceIdea = useCallback(async (nextIdeaId: string) => {
    if (nextIdeaId === workspaceIdeaId) return;
    await saveBeforeWorkspaceChange();
    const nextIdea = ideas.find((i) => i.id === nextIdeaId);
    if (nextIdea && nextIdea.projectId !== pid) onSelectProject(nextIdea.projectId);
    setWorkspaceIdeaId(nextIdeaId);
    setIdeaId(nextIdeaId || ideas.find((i) => i.projectId === pid)?.id || "");
  }, [workspaceIdeaId, saveBeforeWorkspaceChange, ideas, pid, onSelectProject]);

  const selectPresetIdea = useCallback((nextIdeaId: string) => {
    if (presetForIdea(nextIdeaId)) setSelectedPresetIdea(nextIdeaId);
    void switchWorkspaceIdea(nextIdeaId);
  }, [switchWorkspaceIdea]);

  const addIdeaInBrain = useCallback(() => {
    const raw = prompt("Название идеи для отдельного рабочего пространства:", "Новая идея");
    const title = raw?.trim();
    if (!title) return;
    const created = onAddIdea(pid, title);
    setWorkspaceIdeaId(created.id);
    setIdeaId(created.id);
    setSelectedPresetIdea(created.id);
  }, [pid, onAddIdea]);

  const switchProject = useCallback(
    async (nextPid: string) => {
      if (!nextPid || nextPid === pid) return;
      if (dirty && current && fly) {
        const shouldSave = confirm(`Сохранить изменения в файле ${current} (проект «${project?.name ?? pid}») перед переключением проекта?`);
        if (shouldSave) {
          await fly.writeScript(scopeId, current, code, { allowOverwrite: true });
          setDirty(false);
        }
      }
      onSelectProject(nextPid);
    },
    [pid, scopeId, dirty, current, code, project, onSelectProject],
  );

  const createNewProjectHere = useCallback(async () => {
    const raw = prompt("Название нового проекта (для него создадутся отдельные папки кода и результатов):", "Новый эксперимент");
    const trimmed = raw?.trim();
    if (!trimmed) return;
    if (dirty && current && fly) {
      if (confirm(`Сохранить изменения в файле ${current} перед переходом в новый проект?`)) {
        await fly.writeScript(scopeId, current, code, { allowOverwrite: true });
        setDirty(false);
      }
    }
    const created = onAddProject(trimmed);
    if (fly) await fly.projectPaths(created.id);
    onSelectProject(created.id);
  }, [dirty, current, pid, scopeId, code, onAddProject, onSelectProject]);

  const transferScriptToProject = useCallback(
    async (targetPid: string, opts: { move?: boolean; autoRun?: boolean }) => {
      const bridge = fly;
      if (!bridge || !current) return;
      const targetProj = projects.find((p) => p.id === targetPid);
      const r = await bridge.writeScript(targetPid, current, code, { allowOverwrite: true });
      if (opts.move) {
        await bridge.deleteScript(scopeId, current);
        setDirty(false);
      }
      pendingOpenScript.current = {
        pid: targetPid,
        file: r.file,
        autoRunArgs: opts.autoRun ? args : undefined,
      };
      setWorkspaceIdeaId("");
      onSelectProject(targetPid);
      setSaveNote(`${opts.move ? "перенесён" : "скопирован"} в «${targetProj?.name ?? targetPid}»`);
    },
    [current, code, pid, scopeId, args, projects, onSelectProject],
  );

  const transferSelectedRunToProject = useCallback(
    async (targetPid: string, move: boolean) => {
      const bridge = fly;
      if (!bridge || !selRun) return;
      const targetProj = projects.find((p) => p.id === targetPid);
      const res = await bridge.transferRun(selRun.path, targetPid, { move });
      if (move) {
        pendingOpenRun.current = { pid: targetPid, runPath: res.path };
        setWorkspaceIdeaId("");
        onSelectProject(targetPid);
      } else {
        setSaveNote(`прогон скопирован в «${targetProj?.name ?? targetPid}»`);
      }
    },
    [selRun, projects, onSelectProject],
  );

  const openFile = useCallback(async (name: string) => {
    const bridge = fly;
    if (!bridge) return;
    setCurrent(name);
    setCode(await bridge.readScript(scopeId, name));
    setDirty(false);
    setSaveNote("");
    const matched = presetForScript(name);
    if (matched) {
      setIdeaId(matched.ideaId);
      setSelectedPresetIdea(matched.ideaId);
    }
  }, [scopeId]);

  const handleAssistantSavedScript = useCallback(
    async (targetPid: string, fileName: string) => {
      const bridge = fly;
      if (!bridge) return;
      if (targetPid === pidRef.current) {
        setFiles(await bridge.listScripts(targetPid));
        await openFile(fileName);
        setSaveNote(`сохранено в рабочее пространство: ${fileName}`);
      } else {
        const targetIdea = targetPid.startsWith("idea:") ? ideas.find((i) => i.id === targetPid.slice(5)) : undefined;
        pendingOpenScript.current = { pid: targetPid, file: fileName };
        if (targetIdea) {
          setWorkspaceIdeaId(targetIdea.id);
          setIdeaId(targetIdea.id);
          onSelectProject(targetIdea.projectId);
        } else {
          setWorkspaceIdeaId("");
          onSelectProject(targetPid);
        }
      }
    },
    [openFile, onSelectProject, ideas],
  );

  const syncBuiltInTemplates = useCallback(async () => {
    const bridge = fly;
    if (!bridge) return;
    const res = await bridge.syncTemplates(scopeId);
    const updated = await bridge.listScripts(scopeId);
    setFiles(updated);
    setSaveNote(res.added.length ? `добавлено шаблонов: ${res.added.length}` : "все шаблоны на месте");
  }, [scopeId]);

  const applyPreset = useCallback(
    async (preset: TaskPreset, modeArgs: string, autoRun = false) => {
      const bridge = fly;
      if (!bridge) return;
      await bridge.syncTemplates(scopeId);
      const updated = await bridge.listScripts(scopeId);
      setFiles(updated);
      const txt = await bridge.readScript(scopeId, preset.script);
      setCurrent(preset.script);
      setCode(txt);
      setDirty(false);
      setArgs(modeArgs);
      setIdeaId(preset.ideaId);
      setSelectedPresetIdea(preset.ideaId);
      setSaveNote(`готовый анализ: ${preset.script}`);
      if (autoRun && !runId) {
        const list = modeArgs.split(/\s+/).filter(Boolean);
        await startScriptInProject(scopeId, preset.script, list);
      }
    },
    [scopeId, runId, startScriptInProject],
  );

  useEffect(() => {
    if (!focusIdeaId) return;
    setRightTab("presets");
    setIdeaId(focusIdeaId);
    setSelectedPresetIdea(focusIdeaId);
    pendingPresetIdea.current = focusIdeaId;
    setWorkspaceIdeaId(focusIdeaId);
    if (workspaceIdeaId === focusIdeaId) {
      const preset = presetForIdea(focusIdeaId);
      pendingPresetIdea.current = null;
      if (preset) void applyPreset(preset, preset.modes[0]?.args ?? "--synth", false);
    }
    onClearFocusIdea?.();
  }, [focusIdeaId, workspaceIdeaId, applyPreset, onClearFocusIdea]);

  useEffect(() => {
    if (!workspaceIdeaId || pendingPresetIdea.current !== workspaceIdeaId) return;
    const preset = presetForIdea(workspaceIdeaId);
    pendingPresetIdea.current = null;
    if (preset) void applyPreset(preset, preset.modes[0]?.args ?? "--synth", false);
  }, [workspaceIdeaId, applyPreset]);

  const save = async (opts?: { silent?: boolean }) => {
    if (!current) return null;
    const r = await fly!.writeScript(scopeId, current, code, { allowOverwrite: true });
    setDirty(false);
    if (!opts?.silent) setSaveNote(`сохранено в «${project?.name ?? pid}»: ${r.file}`);
    setFiles(await fly!.listScripts(scopeId));
    return r;
  };
  const newFile = async () => {
    const name = prompt(`Имя нового файла в проекте «${project?.name ?? pid}»:`, "my_experiment.py");
    if (!name) return;
    const r = await fly!.writeScript(scopeId, name, '"""Новый эксперимент."""\n\nimport os\n\nRUN_DIR = os.environ["FLY_RUN_DIR"]\n');
    setFiles(await fly!.listScripts(scopeId));
    void openFile(r.file);
  };
  const importFile = async () => {
    const f = await fly!.openFile({ filters: [{ name: "Python", extensions: ["py"] }], kind: "exports" });
    if (!f) return;
    const name = f.path.replace(/^.*[\\/]/, "");
    await fly!.writeScript(scopeId, name, f.content, { allowOverwrite: true });
    setFiles(await fly!.listScripts(scopeId));
    void openFile(name);
  };
  const removeFile = async (name: string) => {
    if (!confirm(`Удалить ${name} из папки проекта «${project?.name ?? pid}»?`)) return;
    await fly!.deleteScript(scopeId, name);
    if (current === name) {
      setCurrent(null);
      setCode("");
    }
    setFiles(await fly!.listScripts(scopeId));
  };
  const exportFile = async () => {
    if (!current) return;
    const p = await fly!.saveFile({ defaultName: current, content: code, filters: [{ name: "Python", extensions: ["py"] }] });
    if (p) setSaveNote(`копия: ${p}`);
  };

  const run = async () => {
    if (!current) return;
    if (dirty) await save({ silent: true });
    const list = args.split(/\s+/).filter(Boolean);
    await startScriptInProject(scopeId, current, list);
  };

  const setPermission = async (patch: Partial<Permissions>) => {
    setPerms(await fly!.setPermissions(patch));
  };

  const toJournal = () => {
    if (!selRun || !ideaId) return;
    const summaryArgs = detail?.summary && typeof detail.summary.args === "object" ? JSON.stringify(detail.summary.args) : "";
    onAddJournalEntry(ideaId, {
      title: `Прогон ${selRun.label.replace(/^\S+?_/, "")}`,
      params: [`проект: ${project?.name ?? pid}`, `идея: ${scopeLabel}`, `run: ${selRun.path}`, summaryArgs && `args: ${summaryArgs}`].filter(Boolean).join("\n"),
      result: [
        detail?.summary ? JSON.stringify(detail.summary, null, 2).slice(0, 1400) : (detail?.log ?? "").slice(-1200),
        images.length ? `графики: ${images.map((i) => i.name).join(", ")}` : "",
      ]
        .filter(Boolean)
        .join("\n"),
      conclusion: "",
    });
    setAdded(true);
  };

  const otherFiles = selRun ? selRun.files.filter((f) => !/\.(png|jpe?g|svg|gif)$/i.test(f) && f !== "summary.json") : [];
  const copyLogs = async () => {
    const text = displayLog || "";
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      setLogCopied(true);
      window.setTimeout(() => setLogCopied(false), 1500);
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
      setLogCopied(true);
      window.setTimeout(() => setLogCopied(false), 1500);
    }
  };

  const installPackageAndRetry = async () => {
    const bridge = fly;
    const failedRun = lastRunByScope.current[scopeId];
    if (!bridge || !missingPackage || installingPackages) return;
    setInstallingPackages(true);
    setSaveNote(`устанавливаю ${missingPackage} в локальное окружение Python...`);
    const off = bridge.onEnvSetupOutput((p) => {
      setLogsByProject((prev) => ({
        ...prev,
        [scopeId]: ((prev[scopeId] ?? "") + p.text).slice(-60000),
      }));
    });
    try {
      await bridge.setupPythonEnv(missingPackage === "brian2" ? "full" : "core");
      setMissingPackage(null);
      setSaveNote(`пакеты установлены, повторяю ${failedRun?.scriptName ?? "скрипт"}`);
      if (failedRun) await startScriptInProject(scopeId, failedRun.scriptName, failedRun.args);
    } catch (e) {
      const message = (e as Error).message;
      setSaveNote(`не удалось установить пакеты: ${message}`);
      setLogsByProject((prev) => ({
        ...prev,
        [scopeId]: `${prev[scopeId] ?? ""}\n\n[ошибка установки] ${message}\n`,
      }));
    } finally {
      off();
      setInstallingPackages(false);
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* шапка: проект, папки кода и результатов, права */}
      <div className="shrink-0 border-b">
        <div className="flex flex-wrap items-center gap-1.5 px-3 py-1.5">
          <span className="label mr-1">проект</span>
          {projects.map((p) => {
            const isRunningHere = !!activeRuns[p.id] || ideas.some((i) => i.projectId === p.id && !!activeRuns[`idea:${i.id}`]);
            return (
              <button
                key={p.id}
                onClick={() => void switchProject(p.id)}
                className={cn(
                  "flex items-center gap-1.5 border px-2 py-0.5 text-[11px] cursor-pointer",
                  p.id === pid ? "border-foreground bg-accent text-foreground" : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                <span className="size-2 shrink-0" style={{ background: p.color }} />
                <span>{p.name}</span>
                {isRunningHere && <span className="font-mono text-[9.5px] text-[var(--chart-2)]">[счёт]</span>}
              </button>
            );
          })}
          <Button size="sm" variant="ghost" className="h-6 px-2 font-mono text-[11px]" onClick={() => void createNewProjectHere()}>
            + новый проект
          </Button>
          {paths && (
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <span className="hidden max-w-[360px] truncate font-mono text-[10px] text-muted-foreground xl:inline" title={`Код: ${paths.code}\nПрогоны: ${paths.runs}`}>
                код: {paths.code} · прогоны: {paths.runs}
              </span>
              <Button size="sm" variant="ghost" className="h-6 px-2 text-[11px]" onClick={() => setShowFolderSettings((s) => !s)}>
                {showFolderSettings ? "скрыть папки и права" : "папки и права"}
              </Button>
            </div>
          )}
        </div>
        {showFolderSettings && (
          <div className="flex flex-col gap-0.5 border-t px-3 py-1.5">
            {paths && (
              <>
                <PathStrip
                  label="папка кода"
                  value={paths.code}
                  isDefault={paths.code === paths.defaults.code}
                  onChoose={async () => {
                    const r = await fly!.chooseProjectFolder(scopeId, "code", `Папка кода: ${scopeLabel}`);
                    if (r) {
                      setPaths(r);
                      setFiles(await fly!.listScripts(scopeId));
                    }
                  }}
                  onOpen={() => fly!.openPath(paths.code)}
                  onReset={async () => {
                    setPaths(await fly!.resetProjectFolder(scopeId, "code"));
                    setFiles(await fly!.listScripts(scopeId));
                  }}
                />
                <PathStrip
                  label="папка прогонов"
                  value={paths.runs}
                  isDefault={paths.runs === paths.defaults.runs}
                  onChoose={async () => {
                    const r = await fly!.chooseProjectFolder(scopeId, "runs", `Папка прогонов: ${scopeLabel}`);
                    if (r) {
                      setPaths(r);
                      await refreshRuns();
                    }
                  }}
                  onOpen={() => fly!.openPath(paths.runs)}
                  onReset={async () => {
                    setPaths(await fly!.resetProjectFolder(scopeId, "runs"));
                    await refreshRuns();
                  }}
                />
              </>
            )}
            {perms && (
              <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1">
                <span className="label">права</span>
                {(
                  [
                    ["createFiles", "помощник создаёт файлы"],
                    ["overwriteFiles", "перезаписывает существующие"],
                    ["runScripts", "разрешён запуск скриптов"],
                  ] as const
                ).map(([k, label]) => (
                  <label key={k} className="flex cursor-pointer items-center gap-1.5 text-[11px] text-muted-foreground">
                    <input type="checkbox" checked={perms[k]} onChange={(e) => setPermission({ [k]: e.target.checked } as Partial<Permissions>)} />
                    {label}
                  </label>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* три колонки: файлы, код и результаты, готовые задачи / помощник */}
      <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[245px_minmax(0,1fr)_360px] lg:divide-x">
        {/* --- слева: проводник --- */}
        <aside className="flex min-h-0 flex-col overflow-hidden border-b lg:border-b-0">
          <div className="flex shrink-0 items-center gap-1 border-b px-2 py-1.5">
            <span className="label truncate" title={paths?.code}>файлы, .py ({files.length})</span>
            <Button size="sm" variant="ghost" className="ml-auto px-1.5" onClick={() => void syncBuiltInTemplates()} title="Докопировать встроенные скрипты анализа (00..19 и flylib.py)">
              шаблоны
            </Button>
            <Button size="sm" variant="ghost" className="px-1.5" onClick={newFile}>
              новый
            </Button>
            <Button size="sm" variant="ghost" className="px-1.5" onClick={importFile}>
              импорт
            </Button>
          </div>
          <div className="min-h-[120px] flex-1 overflow-y-auto">
            {files.length === 0 && <p className="px-2 py-3 text-[11px] text-muted-foreground">Папка пуста.</p>}
            {files.map((f) => (
              <div key={f.name} className={cn("group flex items-center gap-1.5 border-b px-2 py-1", current === f.name && "bg-accent")}>
                <button onClick={() => void openFile(f.name)} className="min-w-0 flex-1 text-left cursor-pointer" title={f.doc || f.name}>
                  <span className="block truncate font-mono text-[11px]">{f.name}</span>
                  <span className="block truncate text-[10px] text-muted-foreground">{f.doc || `${(f.size / 1024).toFixed(1)} КБ`}</span>
                </button>
                <button onClick={() => void removeFile(f.name)} className="shrink-0 cursor-pointer px-1 text-[11px] text-muted-foreground hover:text-destructive" title="Удалить файл">
                  ×
                </button>
              </div>
            ))}
          </div>

          <div className="flex shrink-0 items-center gap-1 border-y px-2 py-1.5">
            <span className="label truncate" title={paths?.runs}>прогоны ({runs.length})</span>
            <Button size="sm" variant="ghost" className="ml-auto" onClick={() => void refreshRuns()}>
              обновить
            </Button>
          </div>
          <div className="min-h-[100px] flex-1 overflow-y-auto">
            {runs.length === 0 && <p className="px-2 py-3 text-[11px] text-muted-foreground">В пространстве «{scopeLabel}» ещё нет прогонов.</p>}
            {runs.map((r) => (
              <button
                key={r.path}
                onClick={() => openRun(r)}
                className={cn("block w-full border-b px-2 py-1 text-left cursor-pointer hover:bg-accent", selRun?.path === r.path && "bg-accent")}
              >
                <span className="block truncate font-mono text-[10px]">{r.label}</span>
                <span className="block font-mono text-[10px] text-muted-foreground">
                  файлов: {r.files.length}
                  {r.summary ? " · summary" : ""}
                  {r.files.some((f) => /\.(png|jpe?g|svg)$/i.test(f)) ? " · графики" : ""}
                </span>
              </button>
            ))}
          </div>
        </aside>

        {/* --- центр: код и результат --- */}
        <section className="flex min-h-0 flex-col overflow-hidden border-b lg:border-b-0">
          <div className="flex shrink-0 flex-wrap items-center gap-1.5 border-b px-2 py-1.5">
            <span className="label">проект</span>
            <ProjectInlinePicker
              projects={projects}
              value={pid}
              onChange={(next) => void switchProject(next)}
              onCreate={() => void createNewProjectHere()}
            />
            <span className="label border-l pl-2">идея</span>
            <Select value={workspaceIdeaId || "__project__"} onValueChange={(value) => void switchWorkspaceIdea(value === "__project__" ? "" : value)}>
              <SelectTrigger className="h-6 min-w-[170px] max-w-[280px] text-[11px]" title="Отдельные папки кода, логов и прогонов для каждой идеи">
                <SelectValue placeholder="общее пространство проекта" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__project__">Общее пространство проекта</SelectItem>
                {ideas.map((i) => {
                  const ip = projects.find((p) => p.id === i.projectId);
                  return <SelectItem key={i.id} value={i.id}>{ip?.id === pid ? "" : `[${ip?.name ?? i.projectId}] `}{i.title}</SelectItem>;
                })}
              </SelectContent>
            </Select>
            <Button size="sm" variant="ghost" className="h-6 px-1.5 font-mono text-[10.5px]" onClick={addIdeaInBrain} title="Создать идею с отдельными папками для кода и прогонов">+ идея</Button>
            {selectedWorkspaceIdea && <Button size="sm" variant="ghost" className="h-6 px-1.5 text-[10.5px]" onClick={() => onOpenIdeaCard(selectedWorkspaceIdea.id)}>карточка</Button>}
            {current ? (
              <>
                <span className="border-l pl-2 font-mono text-[11px] font-medium">{current}</span>
                {dirty && <span className="label">не сохранено</span>}
                <Input value={args} onChange={(e) => setArgs(e.target.value)} placeholder="аргументы: --synth --seed 1" className="h-6 w-[210px] font-mono text-[11px]" />
                <Button size="sm" variant="ghost" onClick={() => void save()} disabled={!dirty}>
                  сохранить
                </Button>
                {otherProjects.length > 0 && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button size="sm" variant="ghost" title="Скопировать, перенести или сразу запустить этот код в другом проекте">
                        в другой проект
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-72">
                      <DropdownMenuLabel>Отправить {current} в проект</DropdownMenuLabel>
                      {otherProjects.map((p) => (
                        <div key={p.id}>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => void transferScriptToProject(p.id, { move: false, autoRun: false })}>
                            <span className="mr-1.5 inline-block size-2 shrink-0" style={{ background: p.color }} />
                            Скопировать в «{p.name}» и открыть
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => void transferScriptToProject(p.id, { move: false, autoRun: true })}>
                            <span className="mr-1.5 inline-block size-2 shrink-0" style={{ background: p.color }} />
                            Скопировать и запустить в «{p.name}»
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => void transferScriptToProject(p.id, { move: true, autoRun: false })}>
                            <span className="mr-1.5 inline-block size-2 shrink-0" style={{ background: p.color }} />
                            Перенести в «{p.name}» (убрать отсюда)
                          </DropdownMenuItem>
                        </div>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
                <Button size="sm" variant="ghost" onClick={() => void exportFile()} title="Сохранить копию файла на диск">
                  копия
                </Button>
                {runId ? (
                  <Button size="sm" variant="outline" onClick={() => fly!.killRun(runId)}>
                    остановить
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => void run()}
                    title={paths ? `Запустить в пространстве «${scopeLabel}»\nРезультаты: ${paths.runs}` : undefined}
                  >
                    запустить
                  </Button>
                )}
                <span className="ml-auto truncate font-mono text-[10px] text-muted-foreground">{saveNote}</span>
              </>
            ) : (
              <>
                <Button size="sm" variant="outline" className="h-6 px-2 text-[11px]" onClick={() => void newFile()}>
                  новый .py
                </Button>
                <Button size="sm" variant="ghost" className="h-6 px-2 text-[11px]" onClick={() => void importFile()}>
                  импорт .py
                </Button>
                <span className="ml-auto truncate font-mono text-[10px] text-muted-foreground">
                  {saveNote || `код и результаты пойдут в «${project?.name ?? pid}»`}
                </span>
              </>
            )}
          </div>

          <div className="min-h-[180px] flex-1 overflow-hidden p-2">
            {current ? (
              <textarea
                value={code}
                onChange={(e) => {
                  setCode(e.target.value);
                  setDirty(true);
                }}
                spellCheck={false}
                className="h-full w-full resize-none overflow-auto rounded-none border border-input bg-transparent p-2 font-mono text-[12px] leading-relaxed outline-none focus-visible:outline focus-visible:outline-1 focus-visible:outline-offset-1 focus-visible:outline-ring"
              />
            ) : (
              <div className="flex h-full flex-col items-center justify-center gap-2 border border-dashed px-4 text-center">
                <p className="max-w-[480px] text-[12px] leading-relaxed text-muted-foreground">
                  Активный проект: <strong className="font-medium text-foreground">{project?.name ?? pid}</strong>. Переключить проект можно прямо над этим полем, в правой панели или слева: тогда и код, и папка результатов сразу переключатся на нужный проект.
                </p>
                {paths && (
                  <div className="max-w-full truncate font-mono text-[10.5px] text-muted-foreground">
                    код: {paths.code} · результаты: {paths.runs}
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2 border-y px-2 py-1.5">
            <span className="label">результат · {scopeLabel}</span>
            {selRun ? (
              <>
                <span className="max-w-[200px] truncate font-mono text-[10px] text-muted-foreground">{selRun.label}</span>
                <Button size="sm" variant="ghost" onClick={() => fly!.openPath(selRun.path)}>
                  папка
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={async () => {
                    const p = await fly!.exportRun(selRun.path);
                    if (p) setSaveNote(`прогон скопирован: ${p}`);
                  }}
                >
                  экспорт
                </Button>
                {otherProjects.length > 0 && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button size="sm" variant="ghost" title="Скопировать или перенести папку этого прогона в другой проект">
                        прогон в проект
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-72">
                      <DropdownMenuLabel>Отправить результаты прогона</DropdownMenuLabel>
                      {otherProjects.map((p) => (
                        <div key={p.id}>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => void transferSelectedRunToProject(p.id, false)}>
                            <span className="mr-1.5 inline-block size-2 shrink-0" style={{ background: p.color }} />
                            Скопировать прогон в «{p.name}»
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => void transferSelectedRunToProject(p.id, true)}>
                            <span className="mr-1.5 inline-block size-2 shrink-0" style={{ background: p.color }} />
                            Перенести прогон в «{p.name}» и перейти
                          </DropdownMenuItem>
                        </div>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </>
            ) : (
              <span className="label">прогон не выбран</span>
            )}
            <div className="ml-auto flex items-center gap-1.5">
              <Select value={ideaId} onValueChange={setIdeaId}>
                <SelectTrigger className="h-6 w-[240px] text-[11px]" title="В лабораторный журнал какой идеи записать результат">
                  <SelectValue placeholder="в какую идею" />
                </SelectTrigger>
                <SelectContent>
                  {orderedIdeasForJournal.map((i) => {
                    const ip = projects.find((pr) => pr.id === i.projectId);
                    const prefix = i.projectId === pid ? "" : `[${ip?.name ?? i.projectId}] `;
                    return (
                      <SelectItem key={i.id} value={i.id}>
                        {prefix}{i.title}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
              <Button size="sm" onClick={toJournal} disabled={!selRun || !ideaId}>
                {added ? "добавлено" : "в журнал идеи"}
              </Button>
            </div>
          </div>

          <div ref={logRef} className="max-h-[40%] min-h-[130px] shrink-0 overflow-y-auto p-2">
            <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
              <span className="label">лог выполнения · {scopeLabel}</span>
              <div className="flex items-center gap-1">
                {missingPackage && (
                  <Button size="sm" variant="outline" className="h-6 px-2 text-[10.5px]" onClick={() => void installPackageAndRetry()} disabled={installingPackages}>
                    {installingPackages ? "устанавливаю…" : `установить ${missingPackage} и повторить`}
                  </Button>
                )}
                <Button size="sm" variant="ghost" className="h-6 px-2 text-[10.5px]" onClick={() => void copyLogs()} disabled={!displayLog}>
                  {logCopied ? "скопировано" : "копировать лог"}
                </Button>
              </div>
            </div>
            {images.length > 0 && (
              <div className="mb-2 grid gap-2 md:grid-cols-2">
                {images.map((im) => (
                  <figure key={im.name} className="border bg-card">
                    <img src={im.dataUrl} alt={im.name} className="w-full" />
                    <figcaption className="border-t px-2 py-0.5 font-mono text-[10px] text-muted-foreground">{im.name}</figcaption>
                  </figure>
                ))}
              </div>
            )}
            {otherFiles.length > 0 && (
              <div className="mb-2 flex flex-wrap gap-1">
                {otherFiles.map((f) => (
                  <button
                    key={f}
                    onClick={async () => {
                      const r = await fly!.readRunFile(selRun!.path, f);
                      if (r.kind === "text") setViewFile({ name: f, text: r.text });
                    }}
                    className={cn("border px-1.5 py-0.5 font-mono text-[10px] cursor-pointer hover:bg-accent", viewFile?.name === f && "bg-accent")}
                  >
                    {f}
                  </button>
                ))}
              </div>
            )}
            {viewFile && <pre className="mb-2 max-h-[240px] overflow-auto border bg-muted/40 p-2 font-mono text-[11px] whitespace-pre-wrap">{viewFile.text}</pre>}
            {detail?.summary && <pre className="mb-2 max-h-[240px] overflow-auto border bg-muted/40 p-2 font-mono text-[11px]">{JSON.stringify(detail.summary, null, 2)}</pre>}
            <pre className="overflow-auto font-mono text-[11px] leading-relaxed whitespace-pre-wrap text-muted-foreground">
              {displayLog || "лог появится здесь после запуска"}
            </pre>
          </div>
        </section>

        {/* --- справа: готовый анализ по задачам (без API) или помощник --- */}
        <aside className="flex min-h-0 flex-col overflow-hidden">
          <div className="flex shrink-0 items-center gap-1 border-b px-2 py-1">
            {(
              [
                ["presets", "По задачам (без API)"],
                ["chat", "Помощник API"],
              ] as const
            ).map(([k, lbl]) => (
              <button
                key={k}
                onClick={() => setRightTab(k)}
                className={cn(
                  "cursor-pointer border-b px-2 py-1 text-[11.5px]",
                  rightTab === k ? "border-foreground font-medium text-foreground" : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                {lbl}
              </button>
            ))}
          </div>
          {rightTab === "presets" ? (
            <PresetsColumn
              ideas={ideas}
              projects={projects}
              projectId={pid}
              onSwitchProject={(next) => void switchProject(next)}
              onCreateProject={() => void createNewProjectHere()}
              selectedIdeaId={selectedPresetIdea}
              workspaceIdeaId={workspaceIdeaId}
              onOpenIdeaCard={onOpenIdeaCard}
              onSelectIdea={selectPresetIdea}
              currentScript={current}
              running={!!runId}
              onApplyPreset={(preset, modeArgs, autoRun) => void applyPreset(preset, modeArgs, autoRun)}
              onOpenCompanion={(name) => void openFile(name)}
            />
          ) : (
            <ChatColumn
              pid={pid}
              workspaceId={scopeId}
              workspaceLabel={scopeLabel}
              projects={projects}
              paths={paths}
              onSwitchProject={(next) => void switchProject(next)}
              onCreateProject={() => void createNewProjectHere()}
              onScriptSaved={handleAssistantSavedScript}
              ideas={ideas}
              perms={perms}
              onAddReferences={onAddReferences}
            />
          )}
        </aside>
      </div>
    </div>
  );
}

// ================================================================
function PresetsColumn({
  ideas,
  projects,
  projectId,
  onSwitchProject,
  onCreateProject,
  selectedIdeaId,
  workspaceIdeaId,
  onOpenIdeaCard,
  onSelectIdea,
  currentScript,
  running,
  onApplyPreset,
  onOpenCompanion,
}: {
  ideas: Idea[];
  projects: Project[];
  projectId: string;
  onSwitchProject: (projectId: string) => void;
  onCreateProject: () => void;
  selectedIdeaId: string;
  workspaceIdeaId: string;
  onOpenIdeaCard: (ideaId: string) => void;
  onSelectIdea: (ideaId: string) => void;
  currentScript: string | null;
  running: boolean;
  onApplyPreset: (preset: TaskPreset, modeArgs: string, autoRun: boolean) => void;
  onOpenCompanion: (scriptName: string) => void;
}) {
  const [scope, setScope] = useState<"project" | "all">("all");
  const ideaMap = useMemo(() => new Map(ideas.map((i) => [i.id, i])), [ideas]);
  const projectMap = useMemo(() => new Map(projects.map((p) => [p.id, p])), [projects]);
  const activeProject = projectMap.get(projectId);

  const visiblePresets = useMemo(() => {
    if (scope === "all") return TASK_PRESETS;
    const filtered = TASK_PRESETS.filter((p) => ideaMap.get(p.ideaId)?.projectId === projectId);
    return filtered.length > 0 ? filtered : TASK_PRESETS;
  }, [scope, ideaMap, projectId]);

  const activePreset = useMemo(
    () => visiblePresets.find((p) => p.ideaId === selectedIdeaId) ?? visiblePresets[0] ?? TASK_PRESETS[0],
    [visiblePresets, selectedIdeaId],
  );
  const linkedIdea = ideaMap.get(activePreset.ideaId);
  const linkedIdeaProject = linkedIdea?.projectId ? projectMap.get(linkedIdea.projectId) : undefined;
  const [showIdeaIndex, setShowIdeaIndex] = useState(false);

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b px-2.5 py-2">
        <div className="mb-1.5 flex flex-wrap items-center gap-1.5">
          <span className="label">куда</span>
          <ProjectInlinePicker
            projects={projects}
            value={projectId}
            onChange={onSwitchProject}
            onCreate={onCreateProject}
            triggerClassName="flex-1 min-w-[150px]"
          />
        </div>
        <div className="flex items-center justify-between gap-2">
          <span className="label">готовые скрипты под задачи</span>
          <div className="flex items-center gap-1">
            {(
              [
                ["all", `все (${TASK_PRESETS.length})`],
                ["project", "этот проект"],
              ] as const
            ).map(([k, l]) => (
              <button
                key={k}
                onClick={() => setScope(k)}
                className={cn(
                  "border px-1.5 py-0.5 font-mono text-[10px] cursor-pointer",
                  scope === k ? "border-foreground bg-accent text-foreground" : "border-border text-muted-foreground hover:text-foreground",
                )}
              >
                {l}
              </button>
            ))}
          </div>
        </div>
        <p className="mt-1 text-[11px] leading-snug text-muted-foreground">
          Код анализа встроен (10..19 и flylib.py): откроется и запустится в проекте «{activeProject?.name ?? projectId}».
        </p>
      </div>

      <div className="shrink-0 border-b">
        <button className="flex w-full items-center justify-between px-2.5 py-1.5 text-left cursor-pointer hover:bg-accent/40" onClick={() => setShowIdeaIndex((v) => !v)}>
          <span className="label">идеи в мозге · отдельные рабочие пространства ({ideas.length})</span>
          <span className="font-mono text-[10px] text-muted-foreground">{showIdeaIndex ? "свернуть" : "показать"}</span>
        </button>
        {showIdeaIndex && (
          <div className="max-h-[170px] overflow-y-auto border-t">
            {ideas.map((idea) => {
              const ideaProject = projectMap.get(idea.projectId);
              const selected = idea.id === workspaceIdeaId;
              return (
                <div key={idea.id} className={cn("flex items-center gap-1 border-b px-2 py-1 last:border-b-0", selected && "bg-accent/60")}>
                  <button className="min-w-0 flex-1 text-left cursor-pointer" onClick={() => onSelectIdea(idea.id)} title={`Открыть отдельные код, логи и прогоны для идеи «${idea.title}»`}>
                    <span className="flex items-center gap-1 truncate text-[11px]">
                      {ideaProject && <span className="size-1.5 shrink-0" style={{ background: ideaProject.color }} />}
                      <span className="truncate">{idea.title}</span>
                    </span>
                    <span className="block truncate font-mono text-[9.5px] text-muted-foreground">{ideaProject?.name ?? idea.projectId} · {idea.status}</span>
                  </button>
                  {selected && <span className="label shrink-0">открыта</span>}
                  <Button size="sm" variant="ghost" className="h-6 shrink-0 px-1.5 text-[10px]" onClick={() => onOpenIdeaCard(idea.id)}>карточка</Button>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {/* Список задач (компактный переключатель) */}
        <div className="border-b">
          {visiblePresets.map((p) => {
            const idea = ideaMap.get(p.ideaId);
            const ideaProj = idea?.projectId ? projectMap.get(idea.projectId) : undefined;
            const isSelected = p.ideaId === selectedIdeaId;
            const isOpen = currentScript === p.script;
            return (
              <button
                key={p.ideaId}
                onClick={() => onSelectIdea(p.ideaId)}
                className={cn(
                  "flex w-full flex-col gap-0.5 border-b px-2.5 py-1.5 text-left last:border-b-0 cursor-pointer hover:bg-accent/60",
                  isSelected && "bg-accent",
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate font-mono text-[10.5px] text-foreground">{p.script}</span>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {p.ideaId === workspaceIdeaId && <span className="label">рабочая идея</span>}
                    {ideaProj && (
                      <span className="flex items-center gap-1 font-mono text-[9.5px] text-muted-foreground" title={`Проект идеи: ${ideaProj.name}`}>
                        <span className="size-1.5" style={{ background: ideaProj.color }} />
                        <span className="max-w-[90px] truncate">{ideaProj.name}</span>
                      </span>
                    )}
                    {isOpen && <span className="label shrink-0">открыт</span>}
                  </div>
                </div>
                <span className="line-clamp-1 text-[11.5px] text-muted-foreground">{idea?.title ?? p.shortTitle}</span>
              </button>
            );
          })}
        </div>

        {/* Подробная карточка выбранного готового анализа */}
        <div className="flex flex-col gap-2.5 p-2.5 text-[12px]">
          {linkedIdeaProject && linkedIdeaProject.id !== projectId && (
            <div className="flex flex-wrap items-center justify-between gap-1.5 border bg-muted/30 px-2 py-1.5 text-[11px]">
              <span className="text-muted-foreground">
                Идея относится к проекту <strong className="font-medium text-foreground">«{linkedIdeaProject.name}»</strong>
              </span>
              <Button size="sm" variant="outline" className="h-6 px-2 text-[10.5px]" onClick={() => onSwitchProject(linkedIdeaProject.id)}>
                переключить на него
              </Button>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between gap-2">
              <div className="label">выбранная готовая задача</div>
              {linkedIdea && <Button size="sm" variant="ghost" className="h-6 px-1.5 text-[10px]" onClick={() => onOpenIdeaCard(linkedIdea.id)}>карточка идеи</Button>}
            </div>
            <div className="mt-0.5 font-medium leading-snug">{linkedIdea?.title ?? activePreset.shortTitle}</div>
            <div className="mt-0.5 font-mono text-[11px] text-muted-foreground">отдельные код, логи и прогоны · {activePreset.script}</div>
            <p className="mt-1.5 text-[11.5px] leading-relaxed text-muted-foreground">{activePreset.summary}</p>
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="label">режимы запуска · проект «{activeProject?.name ?? projectId}»</div>
            {activePreset.modes.map((m) => (
              <div key={m.id} className="border p-2">
                <div className="text-[11.5px] font-medium">{m.label}</div>
                <div className="mt-0.5 break-all font-mono text-[10.5px] text-muted-foreground">
                  python {activePreset.script} {m.args}
                </div>
                <p className="mt-1 text-[11px] leading-snug text-muted-foreground">{m.hint}</p>
                <div className="mt-1.5 flex items-center gap-1.5">
                  <Button size="sm" variant="outline" onClick={() => onApplyPreset(activePreset, m.args, false)}>
                    в редактор
                  </Button>
                  <Button size="sm" disabled={running} onClick={() => onApplyPreset(activePreset, m.args, true)}>
                    {running ? "идёт расчёт..." : "запустить"}
                  </Button>
                </div>
              </div>
            ))}
          </div>

          <div className="border p-2">
            <div className="label">выходные файлы в папке прогона</div>
            <div className="mt-1 flex flex-wrap gap-1">
              {activePreset.outputs.map((out) => (
                <span key={out} className="border bg-muted/40 px-1.5 py-0.5 font-mono text-[10px]">
                  {out}
                </span>
              ))}
            </div>
            <div className="label mt-2">данные для полного режима (FLY_DATA)</div>
            <div className="mt-1 flex flex-col gap-0.5">
              {activePreset.requiredData.map((d) => (
                <span key={d} className="truncate font-mono text-[10px] text-muted-foreground" title={d}>
                  {d}
                </span>
              ))}
            </div>
            {activePreset.companionScripts && activePreset.companionScripts.length > 0 && (
              <>
                <div className="label mt-2">связанные базовые шаблоны</div>
                <div className="mt-1 flex flex-wrap gap-1">
                  {activePreset.companionScripts.map((cs) => (
                    <button
                      key={cs}
                      onClick={() => onOpenCompanion(cs)}
                      className="border px-1.5 py-0.5 font-mono text-[10px] cursor-pointer hover:bg-accent"
                    >
                      {cs}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ================================================================
interface ChatMessage extends LlmMessage {
  actions?: string[];
}

function ChatColumn({
  pid,
  workspaceId,
  workspaceLabel,
  projects,
  paths,
  onSwitchProject,
  onCreateProject,
  onScriptSaved,
  ideas,
  perms,
  onAddReferences,
}: {
  pid: string;
  workspaceId: string;
  workspaceLabel: string;
  projects: Project[];
  paths: ProjectPaths | null;
  onSwitchProject: (projectId: string) => void;
  onCreateProject: () => void;
  onScriptSaved: (targetPid: string, fileName: string) => Promise<void>;
  ideas: Idea[];
  perms: Permissions | null;
  onAddReferences: (items: Partial<Reference>[]) => void;
}) {
  const [provider, setProvider] = useState<LlmProvider>("deepseek");
  const [model, setModel] = useState("deepseek-chat");
  const [msgs, setMsgs] = useState<ChatMessage[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(`fly-ideas:chat:${workspaceId}`) ?? "[]") as ChatMessage[];
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [keys, setKeys] = useState<Record<string, boolean>>({});
  const [ctxIdea, setCtxIdea] = useState("none");
  const [autoSave, setAutoSave] = useState(true);
  const endRef = useRef<HTMLDivElement>(null);

  const conf = PROVIDERS.find((p) => p.id === provider)!;

  useEffect(() => {
    const nextIdea = workspaceId.startsWith("idea:") ? workspaceId.slice(5) : "none";
    setCtxIdea(ideas.some((i) => i.id === nextIdea) ? nextIdea : "none");
  }, [workspaceId, ideas]);

  useEffect(() => {
    setMsgs((() => {
      try {
        return JSON.parse(localStorage.getItem(`fly-ideas:chat:${workspaceId}`) ?? "[]") as ChatMessage[];
      } catch {
        return [];
      }
    })());
    fly!.getSecret("deepseek").then((k) => setKeys((s) => ({ ...s, deepseek: !!k })));
    fly!.getSecret("perplexity").then((k) => setKeys((s) => ({ ...s, perplexity: !!k })));
  }, [workspaceId, pid]);

  useEffect(() => {
    localStorage.setItem(`fly-ideas:chat:${workspaceId}`, JSON.stringify(msgs.slice(-60)));
  }, [msgs, workspaceId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs, busy]);

  const saveKey = async () => {
    await fly!.setSecret(provider, keyInput.trim() || null);
    setKeys((s) => ({ ...s, [provider]: !!keyInput.trim() }));
    setKeyInput("");
  };

  const writeBlocks = async (blocks: { lang?: string; content: string }[], targetPid: string) => {
    const actions: string[] = [];
      const targetIdea = targetPid.startsWith("idea:") ? ideas.find((i) => i.id === targetPid.slice(5)) : undefined;
      const targetName = targetPid === workspaceId ? workspaceLabel : targetIdea?.title ?? projects.find((p) => p.id === targetPid)?.name ?? targetPid;
    let lastSaved: string | null = null;
    for (const b of blocks) {
      if (!/^py/i.test(b.lang ?? "")) continue;
      const m = b.content.match(/^#\s*file:\s*([\w.-]+\.py)/m);
      const stamp = new Date().toISOString().slice(11, 19).replace(/:/g, "");
      const name = m?.[1] ?? `assistant_${stamp}.py`;
      try {
        const r = await fly!.writeScript(targetPid, name, b.content);
        lastSaved = r.file;
        actions.push(`${r.created ? "создан" : "обновлён"} ${r.file} в «${targetName}»`);
      } catch (e) {
        actions.push(`не сохранено: ${(e as Error).message}`);
      }
    }
    if (lastSaved) {
      await onScriptSaved(targetPid, lastSaved);
    }
    return actions;
  };

  const saveBlockToProject = async (codeText: string, name: string, targetPid: string) => {
    const targetIdea = ideas.find((i) => i.projectId === targetPid);
    const targetWorkspace = targetPid === pid ? workspaceId : targetIdea ? `idea:${targetIdea.id}` : targetPid;
    const r = await fly!.writeScript(targetWorkspace, name, codeText, { allowOverwrite: true });
    await onScriptSaved(targetWorkspace, r.file);
  };

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    const targetPidAtSend = workspaceId;
    const idea = ideas.find((i) => i.id === ctxIdea);
    const ctx =
      idea && provider === "deepseek"
        ? `\n\nКонтекст: идея пользователя «${idea.title}». Вопрос: ${idea.question || "не сформулирован"}. Метод: ${idea.method || "не описан"}.`
        : "";
    const next: ChatMessage[] = [...msgs, { role: "user", content: text }];
    setMsgs(next);
    setInput("");
    setBusy(true);
    setErr("");
    try {
      const r = await fly!.llmChat({
        provider,
        model,
        messages: [{ role: "system", content: (provider === "deepseek" ? CODE_PROMPT : LIT_PROMPT) + ctx }, ...next.slice(-10).map((m) => ({ role: m.role, content: m.content }))],
      });
      const blocks = [...r.content.matchAll(/```(\w+)?\n([\s\S]*?)```/g)].map((m) => ({ lang: m[1], content: m[2] }));
      const actions = autoSave && blocks.length && (perms?.createFiles ?? false) ? await writeBlocks(blocks, targetPidAtSend) : [];
      setMsgs((m) => [...m, { role: "assistant", content: r.content, actions }]);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const found = provider === "perplexity" && msgs.length ? parseReferencesFromText(msgs[msgs.length - 1].content) : [];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b px-2 py-1.5">
        <div className="mb-1.5 flex flex-wrap items-center gap-1.5" title={paths ? `Папка кода: ${paths.code}` : undefined}>
          <span className="label">куда код</span>
          <ProjectInlinePicker
            projects={projects}
            value={pid}
            onChange={onSwitchProject}
            onCreate={onCreateProject}
            triggerClassName="flex-1 min-w-[150px]"
          />
        </div>

        <div className="flex items-center gap-1.5">
          <span className="label">помощник</span>
          <Select
            value={provider}
            onValueChange={(v) => {
              setProvider(v as LlmProvider);
              const p = PROVIDERS.find((x) => x.id === v)!;
              setModel(p.models[0][0]);
            }}
          >
            <SelectTrigger className="h-6 w-[164px] text-[11px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PROVIDERS.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={model} onValueChange={setModel}>
            <SelectTrigger className="h-6 flex-1 text-[11px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {conf.models.map(([v, l]) => (
                <SelectItem key={v} value={v}>
                  {l}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="mt-1 flex items-center gap-1.5">
          {keys[provider] ? (
            <>
              <span className="label">ключ {provider === "deepseek" ? "deepseek" : "perplexity"} задан</span>
              <Button
                size="sm"
                variant="ghost"
                className="ml-auto"
                onClick={async () => {
                  await fly!.setSecret(provider, null);
                  setKeys((s) => ({ ...s, [provider]: false }));
                }}
              >
                удалить
              </Button>
            </>
          ) : (
            <>
              <Input value={keyInput} onChange={(e) => setKeyInput(e.target.value)} type="password" placeholder={conf.hint} className="h-6 flex-1 font-mono text-[11px]" />
              <Button size="sm" onClick={saveKey} disabled={!keyInput.trim()}>
                сохранить
              </Button>
            </>
          )}
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
          <span className="label">контекст</span>
          <Select value={ctxIdea} onValueChange={setCtxIdea}>
            <SelectTrigger className="h-6 flex-1 text-[11px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">без идеи</SelectItem>
              {ideas.map((i) => (
                <SelectItem key={i.id} value={i.id}>
                  {i.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <label className="flex w-full cursor-pointer items-center gap-1.5 text-[11px] text-muted-foreground">
            <input type="checkbox" checked={autoSave && (perms?.createFiles ?? false)} disabled={!perms?.createFiles} onChange={(e) => setAutoSave(e.target.checked)} />
            сохранять код в идею «{workspaceLabel}» и открывать
            {!perms?.createFiles && <span className="text-muted-foreground/70">(выключено в правах)</span>}
          </label>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {msgs.length === 0 && (
          <div className="flex flex-col gap-2 py-4">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              {provider === "deepseek"
                ? `Попроси написать скрипт: помощник сохранит его в отдельную папку идеи «${workspaceLabel}», обновит список файлов и откроет в редакторе.`
                : "Спроси про литературу: ответ придёт со списком работ, а строки с DOI можно внести в библиотеку."}
            </p>
            {[
              "Напиши скрипт: обучить MB запаху A с ударом, затем угасание, и построить график избегания",
              "Объясни, что делает 02_mb_toy_interference.py и какие у него параметры",
              "Какие нейроны FlyWire относятся к PPL1 и как их найти в Completeness?",
            ].map((q) => (
              <button key={q} onClick={() => setInput(q)} className="border px-2 py-1 text-left text-[11px] text-muted-foreground hover:bg-accent hover:text-foreground cursor-pointer">
                {q}
              </button>
            ))}
          </div>
        )}

        {msgs.map((m, i) => (
          <div key={i} className="border-b pb-2 mb-2 last:border-b-0">
            <div className="label mb-1">{m.role === "user" ? "запрос" : "ответ"}</div>
            <MessageBody
              content={m.content}
              currentPid={pid}
              projects={projects}
              onSaveCode={(codeText, name, targetPid) => void saveBlockToProject(codeText, name, targetPid)}
            />
            {m.actions && m.actions.length > 0 && (
              <ul className="mt-1 flex flex-col gap-0.5">
                {m.actions.map((a, k) => (
                  <li key={k} className="font-mono text-[10px] text-muted-foreground">
                    {a}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}

        {found.length > 0 && (
          <div className="border p-2">
            <div className="label mb-1">найдено работ: {found.length}</div>
            <Button size="sm" className="w-full" onClick={() => onAddReferences(found)}>
              добавить в библиотеку
            </Button>
          </div>
        )}

        {busy && <div className="label py-1">запрос отправлен…</div>}
        {err && <div className="border border-destructive/40 p-1.5 text-[11px] text-destructive">{err}</div>}
        <div ref={endRef} />
      </div>

      <div className="shrink-0 border-t p-2">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          placeholder={provider === "deepseek" ? "что написать: Enter отправляет" : "что искать в литературе: Enter отправляет"}
          className="max-h-[140px] min-h-[52px] text-[12px]"
          disabled={!keys[provider]}
        />
        <div className="mt-1 flex items-center gap-1.5">
          <Button size="sm" onClick={send} disabled={busy || !input.trim() || !keys[provider]}>
            отправить
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setMsgs([])} disabled={!msgs.length}>
            очистить
          </Button>
          {!keys[provider] && <span className="label ml-auto">сначала вставь ключ {provider}</span>}
        </div>
      </div>
    </div>
  );
}

/** Текст ответа с блоками кода: у каждого блока кнопка сохранения в текущий или другой проект */
function MessageBody({
  content,
  currentPid,
  projects,
  onSaveCode,
}: {
  content: string;
  currentPid: string;
  projects: Project[];
  onSaveCode: (code: string, name: string, targetPid: string) => void;
}) {
  const parts = useMemo(() => {
    const out: { type: "text" | "code"; content: string; lang?: string }[] = [];
    const re = /```(\w+)?\n([\s\S]*?)```/g;
    let last = 0;
    let m: RegExpExecArray | null;
    while ((m = re.exec(content))) {
      if (m.index > last) out.push({ type: "text", content: content.slice(last, m.index) });
      out.push({ type: "code", content: m[2], lang: m[1] });
      last = m.index + m[0].length;
    }
    if (last < content.length) out.push({ type: "text", content: content.slice(last) });
    return out;
  }, [content]);

  const currentProjectName = projects.find((p) => p.id === currentPid)?.name ?? currentPid;
  const otherProjects = projects.filter((p) => p.id !== currentPid);

  const askFileName = (raw: string) => {
    const m = raw.match(/^#\s*file:\s*([\w.-]+\.py)/m);
    return m?.[1] ?? prompt("Имя файла для скрипта:", "my_experiment.py") ?? "";
  };

  return (
    <div className="text-[12px] leading-relaxed">
      {parts.map((p, i) =>
        p.type === "text" ? (
          <div key={i} className="whitespace-pre-wrap">
            {p.content.trim()}
          </div>
        ) : (
          <div key={i} className="my-1.5">
            <pre className="max-h-[260px] overflow-auto border bg-muted/40 p-2 font-mono text-[11px]">{p.content}</pre>
            {(p.lang ?? "").match(/^py/i) && (
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    const name = askFileName(p.content);
                    if (name) onSaveCode(p.content, name, currentPid);
                  }}
                >
                  сохранить в «{currentProjectName}»
                </Button>
                {otherProjects.length > 0 && (
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button size="sm" variant="ghost">
                        в другой проект
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start" className="w-64">
                      <DropdownMenuLabel>Сохранить и открыть в проекте</DropdownMenuLabel>
                      <DropdownMenuSeparator />
                      {otherProjects.map((pr) => (
                        <DropdownMenuItem
                          key={pr.id}
                          onClick={() => {
                            const name = askFileName(p.content);
                            if (name) onSaveCode(p.content, name, pr.id);
                          }}
                        >
                          <span className="mr-1.5 inline-block size-2 shrink-0" style={{ background: pr.color }} />
                          {pr.name}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuContent>
                  </DropdownMenu>
                )}
              </div>
            )}
          </div>
        ),
      )}
    </div>
  );
}

// ================================================================
function HelpDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const steps: [string, string][] = [
    ["Данные", "раздел «Данные и окружение»: выбери папку и нажми «Скачать мозг мухи», это около 100 МБ. Для первой пробы данные не нужны: шаблон 02 работает сам по себе."],
    ["Окружение", "во вкладке «Данные и окружение» видны Python и пакеты. Если не хватает pandas или других основных библиотек, нажми «установить пакеты для анализов»: программа создаст workspace/.venv и настроит запуски на него. Brian2 можно установить отдельной кнопкой."],
    ["Готовый анализ задач (без API)", "справа открыта вкладка «По задачам (без API)»: там лежат готовые проверенные скрипты 10..19 под все 10 текущих идей (лезии, интерференция, бенчмарк бэкендов, обучение в целом мозге, память ухаживания MaleCNS, тракт в VNC, социальное обучение, индивидуальность, брачная песня, PCI) и общий модуль flylib.py. В каждом есть быстрый режим --synth и полный режим на локальных файлах FLY_DATA."],
    ["Идеи и рабочие пространства", "В центре выбери проект и идею. У каждой идеи свои папки кода, логов и прогонов; список «идеи в мозге» справа позволяет быстро переключаться и открывать карточку идеи. При переходе несохранённый код можно сохранить. Проектное общее пространство доступно отдельным пунктом."],
    ["Копирование логов", "Внизу панели результатов нажми «копировать лог», чтобы перенести вывод текущего запуска в буфер обмена."],
    ["Первый прогон", "слева открой 00_check_env.py и запусти, либо выбери любую задачу справа и нажми «запустить» на режиме --synth. Аргументы видны и редактируются в строке над кодом."],
    ["Посмотреть нейроны", "шаблон 05_neuron_gallery.py рисует морфологию нейронов в трёх проекциях и накладывает активность из прогона: --ids 12781 556329 (скелеты скачаются сами) или --spikes путь_к_spikes.parquet, с флагом --animate получится gif с распространением сигнала."],
    ["Прогон модели", "шаблон 06_brian2_shiu.py считает LIF-сеть на Brian2: сам подбирает фоновый вес под целевую частоту, стимулирует и заглушает заданные нейроны, пишет spikes.parquet, rates_top.csv, raster.png. Проверка без данных: --synth --n 2000 --t 0.5."],
    ["Связка фигур", "шаблон 07_morph_activity_figure.py кладёт морфологию и активность в одну фигуру. Половины подписаны, потому что id MaleCNS и FlyWire v783 не совпадают; таблица соответствия передаётся флагом --map."],
    ["Коннектом самца", "шаблон 08_malecns_loader.py сам находит в бакете Janelia таблицы MaleCNS v1.0 и приводит их к колонкам pre, post, weight: --check показывает, что там лежит, --synth проверяет разбор без интернета."],
    ["Протокол обучения", "шаблон 09_mb_circuit_v783.py берёт реальные KC, MBON и PPL1 из v783, ведёт два компартмента MBON и считает обучение, угасание и пассивную релаксацию: --n-pair 10 --extinction 20 --appetitive 6."],
    ["Результат", "внизу появятся графики, summary.json и лог. Кнопка «в журнал идеи» переносит запись в выбранную идею, дополни её в идее на вкладке «Журнал»."],
    ["Код помощником", "справа вставь ключ DeepSeek и напиши задачу словами. Файл из ответа сохраняется в папку проекта сам (галочка «сохранять код из ответа») либо кнопкой «сохранить в проект». Имя задаётся строкой # file: имя.py."],
    ["Литература", "переключи помощника на Perplexity (ключ с perplexity.ai), спроси про литературу и нажми «добавить в библиотеку»: строки с DOI разберутся в источники."],
    ["Агент извне", "в разделе «Данные и окружение» есть блок «Подключение агента»: он показывает порт, токен и готовые строки для DeepSeek Harness, Claude Code или Codex. Через мост агент видит идеи, журнал, литературу, данные и прогоны, запускает скрипты и может писать в журнал: записи появляются уведомлением справа внизу, а права проверяются в приложении."],
    ["Права", "над колонками видны галочки: создавать файлы, перезаписывать существующие, разрешать запуск. Выключи перезапись, если боишься потерять свои правки."],
  ];
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Порядок работы</DialogTitle>
          <DialogDescription>У каждого проекта своя папка кода и своя папка прогонов. Их можно переназначить в шапке рабочего места.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col">
          {steps.map(([t, d], i) => (
            <div key={t} className="flex gap-3 border-b py-2 last:border-b-0">
              <span className="mt-0.5 font-mono text-[10px] text-muted-foreground">{String(i + 1).padStart(2, "0")}</span>
              <div className="min-w-0">
                <div className="text-[12px] font-medium">{t}</div>
                <p className="mt-0.5 text-[11px] leading-relaxed text-muted-foreground">{d}</p>
              </div>
            </div>
          ))}
        </div>
        <div className="border p-2">
          <div className="label mb-1">шаблон запроса к помощнику</div>
          <pre className="overflow-x-auto font-mono text-[11px] leading-relaxed whitespace-pre-wrap">{`Напиши скрипт на Python для такой задачи: <что нужно>.
Требования: argparse с --seed и параметрами протокола; данные читать из FLY_DATA;
графики png и summary.json писать в FLY_RUN_DIR; в summary.json положить args и метрики;
первой строкой файла укажи "# file: имя_латиницей.py".`}</pre>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ================================================================
function DataPanel() {
  const [items, setItems] = useState<DataItem[]>([]);
  const [progress, setProgress] = useState<Record<string, { got: number; total: number }>>({});
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [paths, setPaths] = useState<Paths | null>(null);
  const [external, setExternal] = useState<ExternalSource[]>([]);

  const refresh = useCallback(async () => {
    setItems(await fly!.listData());
    setPaths(await fly!.getPaths());
    setExternal(await fly!.listExternal());
  }, []);
  useEffect(() => {
    refresh();
  }, [refresh]);
  useEffect(
    () =>
      fly!.onDownloadProgress((p) =>
        setProgress((s) => ({ ...s, [p.id]: { got: p.got, total: p.total } })),
      ),
    [],
  );

  const dl = async (item: DataItem, destDir?: string) => {
    setBusy((b) => ({ ...b, [item.id]: true }));
    setErrors((e) => ({ ...e, [item.id]: "" }));
    try {
      const r = await fly!.download(item, destDir);
      if (r.size < 2000 && item.sizeMB > 1) setErrors((e) => ({ ...e, [item.id]: "Скачался крошечный файл: скорее всего это заглушка Git LFS. Скачай вручную из репозитория." }));
    } catch (e) {
      setErrors((er) => ({ ...er, [item.id]: (e as Error).message }));
    } finally {
      setBusy((b) => ({ ...b, [item.id]: false }));
      setProgress((p) => {
        const n = { ...p };
        delete n[item.id];
        return n;
      });
      refresh();
    }
  };
  const dlAll = async () => {
    for (const it of items.filter((i) => !i.present)) await dl(it);
  };
  const dlAllTo = async () => {
    const dir = await fly!.pickFolder("Куда скачать все файлы данных");
    if (!dir) return;
    for (const it of items.filter((i) => i.dest !== "scripts")) await dl(it, dir);
  };

  const groups = useMemo(() => [...new Set(items.map((i) => i.group))], [items]);
  const missing = items.filter((i) => !i.present).length;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={dlAll} disabled={!missing || Object.values(busy).some(Boolean)}>
          {missing ? `Скачать мозг мухи, файлов: ${missing}` : "Всё скачано"}
        </Button>
        <Button variant="outline" onClick={dlAllTo} disabled={Object.values(busy).some(Boolean)}>
          Скачать в папку…
        </Button>
        <Button variant="ghost" onClick={refresh}>
          обновить
        </Button>
      </div>

      {paths && (
        <PathStrip
          label="данные"
          value={paths.data}
          isDefault={paths.data === paths.defaults.data}
          onChoose={async () => {
            await fly!.chooseFolder("data", "Папка данных");
            refresh();
          }}
          onOpen={() => fly!.openPath(paths.data)}
          onReset={async () => {
            await fly!.resetFolder("data");
            refresh();
          }}
        />
      )}

      <p className="max-w-[900px] text-[11px] leading-relaxed text-muted-foreground">
        Файлы берутся из открытого репозитория{" "}
        <a className="underline" href="https://github.com/eonsystemspbc/fly-brain" target="_blank" rel="noreferrer">
          eonsystemspbc/fly-brain
        </a>
        : FlyWire v783 (последний публичный релиз коннектома, тот же, что в Nature 2024) и код модели Shiu et al. Полный мозг занимает около 100 МБ таблиц, не терабайты.
      </p>

      {groups.map((g) => (
        <section key={g} className="border">
          <div className="label border-b px-2 py-1.5">{g}</div>
          <div className="flex flex-col">
            {items
              .filter((i) => i.group === g)
              .map((it) => {
                const pr = progress[it.id];
                const pct = pr && pr.total ? Math.round((pr.got / pr.total) * 100) : null;
                return (
                  <div key={it.id} className="border-b px-2 py-1.5 last:border-b-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={cn("size-2.5 shrink-0", it.present ? "bg-[var(--chart-2)]" : "border border-muted-foreground/40")} title={it.present ? "файл на месте" : "файла нет"} />
                      <div className="min-w-0 flex-1">
                        <div className="text-[12px]">
                          {it.title} <span className="font-mono text-[10px] text-muted-foreground">{it.file}</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground">{it.note}</div>
                      </div>
                      <span className="shrink-0 font-mono text-[10px] text-muted-foreground">{it.present ? fmtBytes(it.size) : `~${it.sizeMB} МБ`}</span>
                      <Button
                        size="sm"
                        variant="ghost"
                        title="Открыть страницу файла на GitHub"
                        onClick={() => fly!.openExternal(it.page ?? it.url.replace("raw.githubusercontent.com", "github.com").replace("/main/", "/blob/main/"))}
                      >
                        источник
                      </Button>
                      {busy[it.id] ? (
                        <Button size="sm" variant="outline" onClick={() => fly!.cancelDownload(it.id)}>
                          {pct ?? "…"}%
                        </Button>
                      ) : (
                        <>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={async () => {
                              const dir = await fly!.pickFolder(`Куда скачать ${it.file}`);
                              if (dir) await dl(it, dir);
                            }}
                          >
                            в папку
                          </Button>
                          <Button size="sm" variant={it.present ? "ghost" : "default"} onClick={() => dl(it)}>
                            {it.present ? "обновить" : "скачать"}
                          </Button>
                        </>
                      )}
                    </div>
                    {pr && (
                      <div className="mt-1 h-1 border">
                        <div className="h-full bg-[var(--chart-1)]" style={{ width: `${pct ?? 5}%` }} />
                      </div>
                    )}
                    {errors[it.id] && <div className="mt-1 text-[11px] text-destructive">{errors[it.id]}</div>}
                  </div>
                );
              })}
          </div>
        </section>
      ))}

      {external.length > 0 && (
        <section className="border">
          <div className="border-b px-2 py-1.5">
            <div className="label">внешние источники, вручную</div>
            <p className="mt-1 text-[11px] text-muted-foreground">Официальные выгрузки и аннотации: обычно требуют аккаунта или лежат не одним файлом. Открываются в браузере.</p>
          </div>
          <div className="flex flex-col">
            {external.map((e) => (
              <button key={e.url} onClick={() => fly!.openExternal(e.url)} className="border-b px-2 py-1.5 text-left last:border-b-0 hover:bg-accent cursor-pointer">
                <div className="text-[12px]">{e.title}</div>
                <div className="text-[11px] text-muted-foreground">{e.note}</div>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ================================================================
function AgentPanel() {
  const [info, setInfo] = useState<AgentInfo | null>(null);
  const [copied, setCopied] = useState("");
  const refresh = async () => setInfo(await fly!.agentInfo());
  useEffect(() => {
    void refresh();
  }, []);
  const copy = async (text: string, what: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(what);
    setTimeout(() => setCopied(""), 1500);
  };
  const snippet = info
    ? [
        "# в cordis.patch.yml профиля dsh добавь строку плагина MCP:",
        "# имя инструментов в диалоге будет mcp__fly__*",
        "- name: '@deepseek-ai/dsh-mcp-client'",
        "  config:",
        "    serverName: fly",
        "    transport: stdio",
        "    command: node",
        `    args: ['${info.mcp.replace(/\\/g, "/")}']`,
      ].join("\n")
    : "";
  const claude = info ? `claude mcp add fly -- node "${info.mcp}"` : "";

  return (
    <section className="border">
      <div className="flex items-start justify-between gap-3 border-b px-2 py-2">
        <div>
          <div className="label">Подключение агента (MCP)</div>
          <p className="mt-1 max-w-2xl text-[11px] leading-relaxed text-muted-foreground">
            Внешний агент (DeepSeek Harness, Claude Code, Codex) видит идеи, журнал, литературу, данные и прогоны, запускает
            скрипты проекта и может писать в журнал. Все действия проходят через это окно: права проверяются здесь, а записи
            агента всплывают уведомлением. Мост слушает только 127.0.0.1 и требует токен.
          </p>
        </div>
        <label className="flex shrink-0 items-center gap-2 text-[12px]">
          <input
            type="checkbox"
            checked={!!info?.enabled}
            onChange={async (e) => {
              await fly!.setAgentEnabled(e.target.checked);
              await refresh();
            }}
          />
          включён
        </label>
      </div>
      {info && (
        <div className="flex flex-col gap-2 p-2 text-[12px]">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px]">
            <span className={info.running ? "text-foreground" : "text-muted-foreground"}>
              {info.running ? `слушает ${info.url}` : "мост выключен"}
            </span>
            <span className="text-muted-foreground">файл: {info.file}</span>
            <span className="text-muted-foreground">
              {info.syncedAt ? `состояние синхронизировано ${new Date(info.syncedAt).toLocaleTimeString("ru-RU")}` : "снимок состояния ещё не отправлен"}
            </span>
          </div>
          {info.running && (
            <>
              <div>
                <div className="label">Строка для dsh (cordis.patch.yml)</div>
                <pre className="mt-1 overflow-x-auto border bg-muted/40 p-2 font-mono text-[11px]">{snippet}</pre>
                <Button size="sm" variant="outline" className="mt-1" onClick={() => void copy(snippet, "snippet")}>
                  {copied === "snippet" ? "скопировано" : "Скопировать"}
                </Button>
              </div>
              <div>
                <div className="label">Для Claude Code и Codex</div>
                <pre className="mt-1 overflow-x-auto border bg-muted/40 p-2 font-mono text-[11px]">{claude}</pre>
                <Button size="sm" variant="outline" className="mt-1" onClick={() => void copy(claude, "claude")}>
                  {copied === "claude" ? "скопировано" : "Скопировать"}
                </Button>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Токен лежит рядом с конфигом приложения, в agent.json. Схема плагина MCP у dsh пока в превью: если строка не
                подхватится, сверь её с документацией dsh по адресу deepseek.com/harness. Инструменты:
                fly_status, fly_list_ideas, fly_get_idea, fly_search_library, fly_list_scripts, fly_read_script, fly_list_runs,
                fly_read_run, fly_list_data, fly_run_script, fly_wait_run, fly_kill_run, fly_add_journal_entry, fly_add_idea,
                fly_update_idea, fly_add_reference.
              </p>
            </>
          )}
        </div>
      )}
    </section>
  );
}

function EnvPanel() {
  const [env, setEnv] = useState<EnvInfo | null>(null);
  const [pythons, setPythons] = useState<PythonCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [settingUp, setSettingUp] = useState(false);
  const [setupLog, setSetupLog] = useState("");
  const [setupError, setSetupError] = useState("");

  const check = async () => {
    setLoading(true);
    try {
      const [nextEnv, found] = await Promise.all([fly!.checkEnv(), fly!.listPythons()]);
      setEnv(nextEnv);
      setPythons(found);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void check();
    return fly!.onEnvSetupOutput((p: EnvSetupOutput) => {
      setSetupLog((prev) => (prev + p.text).slice(-30000));
      if (p.done && !p.ok) setSetupError("Установка не завершилась. Подробности есть в логе ниже.");
    });
  }, []);

  const need = ["numpy", "pandas", "scipy", "matplotlib", "pyarrow"];
  const missing = env ? need.filter((m) => !env.packages[m]) : need;
  const setup = async (mode: "core" | "full" = "core") => {
    setSettingUp(true);
    setSetupError("");
    setSetupLog("");
    try {
      const result = await fly!.setupPythonEnv(mode);
      setEnv(result);
      setPythons(await fly!.listPythons());
    } catch (e) {
      setSetupError((e as Error).message);
    } finally {
      setSettingUp(false);
    }
  };

  const selectPython = async (value: string) => {
    try {
      if (value === "__auto__") {
        setEnv(await fly!.setPython(null));
      } else {
        const selected = pythons.find((p) => p.exe === value);
        if (selected) setEnv(await fly!.setPython(selected.exe));
      }
    } catch (e) {
      setSetupError((e as Error).message);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <section className="border">
        <div className="flex flex-wrap items-center gap-2 border-b px-2 py-1.5">
          <div className="label mr-auto">Python для всех идей</div>
          <Button variant="outline" size="sm" onClick={check} disabled={loading || settingUp}>
            {loading ? "проверяю…" : "проверить снова"}
          </Button>
          <Button variant="ghost" size="sm" onClick={async () => {
            try {
              const result = await fly!.pickPythonExe();
              if (result) {
                setEnv(result);
                setPythons(await fly!.listPythons());
              }
            } catch (e) {
              setSetupError((e as Error).message);
            }
          }} disabled={settingUp}>
            выбрать python.exe
          </Button>
        </div>

        <div className="flex flex-col gap-2 p-2">
          {env?.python ? (
            <div className="flex flex-wrap items-center gap-2">
              <span className="label shrink-0">интерпретатор</span>
              <Select value={env.configuredPython || env.python.exe} onValueChange={(v) => void selectPython(v)}>
                <SelectTrigger className="h-7 min-w-[260px] flex-1 font-mono text-[10px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__auto__">автоматический выбор</SelectItem>
                  {pythons.map((p) => (
                    <SelectItem key={`${p.exe}-${p.source}`} value={p.exe}>
                      {p.version} · {p.source} · {p.exe}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <p className="text-[11px] text-destructive">Python 3 не найден. Установи Python 3.11 или 3.12 с python.org и отметь Add Python to PATH, затем перезапусти программу.</p>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <Button onClick={() => void setup("core")} disabled={settingUp || !env?.python || missing.length === 0}>
              {settingUp ? "устанавливаю…" : missing.length ? "установить пакеты для анализов" : "основные пакеты установлены"}
            </Button>
            {!!env?.python && !env.packages.brian2 && (
              <Button variant="outline" onClick={() => void setup("full")} disabled={settingUp}>
                установить Brian2
              </Button>
            )}
            <span className="label">
              {env ? (missing.length ? `не хватает: ${missing.join(", ")}` : "numpy, pandas, scipy, matplotlib и pyarrow доступны") : "проверка Python…"}
            </span>
          </div>
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            Установка создаёт отдельное окружение <code className="font-mono">workspace/.venv</code> и ставит в него pandas и остальные пакеты. Запуски автоматически используют это окружение, не меняя системный Python.
          </p>
          {setupError && <p className="text-[11px] text-destructive">{setupError}</p>}
          {setupLog && <pre className="max-h-[220px] overflow-auto border bg-muted/40 p-2 font-mono text-[10px] leading-relaxed whitespace-pre-wrap">{setupLog}</pre>}
        </div>
      </section>

      <AgentPanel />

      {env && (
        <div className="grid gap-3 md:grid-cols-2">
          <section className="border">
            <div className="label border-b px-2 py-1.5">Интерпретатор и GPU</div>
            <div className="flex flex-col p-2">
              <Row ok={!!env.python} label="Python 3" value={env.python ? `${env.python.version} (${env.python.exe})` : "не найден"} />
              <Row ok={!!env.conda} label="conda" value={env.conda ?? "не найдена, не обязательна"} soft />
              <Row ok={!!env.gpu} label="GPU (CUDA)" value={env.gpu ?? "CPU доступен"} soft />
            </div>
          </section>
          <section className="border">
            <div className="label border-b px-2 py-1.5">Пакеты в выбранном Python</div>
            <div className="flex flex-col p-2">
              {Object.entries(env.packages).map(([k, v]) => (
                <Row key={k} ok={!!v} label={k} value={v ?? "не установлен"} soft={!need.includes(k)} />
              ))}
            </div>
          </section>
        </div>
      )}

      <section className="border">
        <div className="label border-b px-2 py-1.5">Дополнительное окружение conda</div>
        <div className="p-2 text-[11px] leading-relaxed text-muted-foreground">
          Для анализа MaleCNS, нейроморфологии и остальных дополнительных инструментов можно поставить полный набор из <code className="font-mono">environment.yml</code>. Для ошибки pandas нажми «установить недостающие пакеты» выше: команда в консоли не нужна.
        </div>
      </section>
    </div>
  );
}

function Row({ ok, label, value, soft }: { ok: boolean; label: string; value: string; soft?: boolean }) {
  return (
    <div className="flex items-center gap-2 py-0.5">
      <span className={cn("size-2 shrink-0", ok ? "bg-[var(--chart-2)]" : soft ? "border border-muted-foreground/40" : "bg-destructive")} />
      <span className="w-20 shrink-0 text-[11px] text-muted-foreground">{label}</span>
      <span className="truncate font-mono text-[11px]">{value}</span>
    </div>
  );
}
