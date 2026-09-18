import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Idea, Reference } from "@/data/types";
import {
  fly, fmtBytes, isElectron,
  type DataItem, type EnvInfo, type ExternalSource, type LlmMessage, type LlmProvider,
  type Paths, type Permissions, type ProjectPaths, type RunInfo, type ScriptInfo,
} from "@/lib/bridge";
import { parseReferencesFromText } from "@/lib/refparse";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

interface Props {
  ideas: Idea[];
  projects: { id: string; name: string }[];
  activeProject: string | "all";
  onSelectProject: (id: string | "all") => void;
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
export function BrainView({ ideas, projects, activeProject, onSelectProject, onAddJournalEntry, onAddReferences }: Props) {
  const [tab, setTab] = useState<"work" | "setup">("work");
  const [help, setHelp] = useState(false);

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
          onSelectProject={onSelectProject}
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
function Workspace({ ideas, projects, activeProject, onSelectProject, onAddJournalEntry, onAddReferences }: Omit<Props, "activeProject"> & { activeProject: string | "all" }) {
  const pid = activeProject === "all" ? projects[0]?.id ?? "project" : activeProject;
  const [paths, setPaths] = useState<ProjectPaths | null>(null);
  const [perms, setPerms] = useState<Permissions | null>(null);
  const [files, setFiles] = useState<ScriptInfo[]>([]);
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [dirty, setDirty] = useState(false);
  const [args, setArgs] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [liveLog, setLiveLog] = useState("");
  const [selRun, setSelRun] = useState<RunInfo | null>(null);
  const [detail, setDetail] = useState<{ log: string; summary: Record<string, unknown> | null } | null>(null);
  const [images, setImages] = useState<{ name: string; dataUrl: string }[]>([]);
  const [viewFile, setViewFile] = useState<{ name: string; text: string } | null>(null);
  const [ideaId, setIdeaId] = useState<string>(ideas[0]?.id ?? "");
  const [added, setAdded] = useState(false);
  const [saveNote, setSaveNote] = useState("");
  const pendingRun = useRef<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  const loadFiles = useCallback(async () => {
    setPaths(await fly!.projectPaths(pid));
    setFiles(await fly!.listScripts(pid));
    return fly!.listRuns(pid);
  }, [pid]);

  const refreshRuns = useCallback(async () => {
    const r = await fly!.listRuns(pid);
    setRuns(r);
    return r;
  }, [pid]);

  useEffect(() => {
    setCurrent(null);
    setCode("");
    setDirty(false);
    setSelRun(null);
    setDetail(null);
    setImages([]);
    setViewFile(null);
    setLiveLog("");
    loadFiles().then(setRuns);
  }, [loadFiles]);

  useEffect(() => {
    fly!.getPermissions().then(setPerms);
  }, []);

  useEffect(
    () =>
      fly!.onRunOutput((p) => {
        setLiveLog((l) => (l + p.text).slice(-60000));
        if (p.stream === "exit") {
          setRunId(null);
          refreshRuns().then((list) => {
            const target = pendingRun.current ? list.find((r) => r.path === pendingRun.current) : null;
            if (target) openRun(target);
            pendingRun.current = null;
          });
        }
      }),
    [refreshRuns],
  );
  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [liveLog]);

  function openRun(r: RunInfo) {
    setSelRun(r);
    setViewFile(null);
    setImages([]);
    setDetail(null);
    fly!.readRun(r.path).then(setDetail);
    const imgs = r.files.filter((f) => /\.(png|jpe?g|svg|gif)$/i.test(f));
    Promise.all(
      imgs.map(async (name) => {
        const res = await fly!.readRunFile(r.path, name);
        return res.kind === "image" ? { name, dataUrl: res.dataUrl } : null;
      }),
    ).then((x) => setImages(x.filter((v): v is { name: string; dataUrl: string } => !!v)));
  }

  const openFile = async (name: string) => {
    setCurrent(name);
    setCode(await fly!.readScript(pid, name));
    setDirty(false);
    setSaveNote("");
  };
  const save = async (opts?: { silent?: boolean }) => {
    if (!current) return null;
    const r = await fly!.writeScript(pid, current, code, { allowOverwrite: true });
    setDirty(false);
    if (!opts?.silent) setSaveNote(`сохранено: ${r.file}`);
    setFiles(await fly!.listScripts(pid));
    return r;
  };
  const newFile = async () => {
    const name = prompt("Имя нового файла:", "my_experiment.py");
    if (!name) return;
    const r = await fly!.writeScript(pid, name, '"""Новый эксперимент."""\n\nimport os\n\nRUN_DIR = os.environ["FLY_RUN_DIR"]\n');
    await setFiles(await fly!.listScripts(pid));
    openFile(r.file);
  };
  const importFile = async () => {
    const f = await fly!.openFile({ filters: [{ name: "Python", extensions: ["py"] }], kind: "exports" });
    if (!f) return;
    const name = f.path.replace(/^.*[\\/]/, "");
    await fly!.writeScript(pid, name, f.content, { allowOverwrite: true });
    await setFiles(await fly!.listScripts(pid));
    openFile(name);
  };
  const removeFile = async (name: string) => {
    if (!confirm(`Удалить ${name} из папки проекта?`)) return;
    await fly!.deleteScript(pid, name);
    if (current === name) {
      setCurrent(null);
      setCode("");
    }
    setFiles(await fly!.listScripts(pid));
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
    setLiveLog("");
    setDetail(null);
    setImages([]);
    setViewFile(null);
    try {
      const r = await fly!.runScript(pid, current, list);
      pendingRun.current = r.runDir;
      setRunId(r.runId);
      setAdded(false);
      setLiveLog(`$ python ${current} ${list.join(" ")}\n→ ${r.runDir}\n\n`);
    } catch (e) {
      setLiveLog(`не удалось запустить: ${(e as Error).message}\n`);
    }
  };

  const setPermission = async (patch: Partial<Permissions>) => {
    setPerms(await fly!.setPermissions(patch));
  };

  const toJournal = () => {
    if (!selRun || !ideaId) return;
    const summaryArgs = detail?.summary && typeof detail.summary.args === "object" ? JSON.stringify(detail.summary.args) : "";
    onAddJournalEntry(ideaId, {
      title: `Прогон ${selRun.label.replace(/^\S+?_/, "")}`,
      params: [`run: ${selRun.path}`, summaryArgs && `args: ${summaryArgs}`].filter(Boolean).join("\n"),
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
  const project = projects.find((p) => p.id === pid);

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* шапка: проект, папки, права */}
      <div className="shrink-0 border-b">
        <div className="flex flex-wrap items-center gap-1.5 px-3 py-1.5">
          <span className="label mr-1">проект</span>
          {projects.map((p) => (
            <button
              key={p.id}
              onClick={() => onSelectProject(p.id)}
              className={cn(
                "border px-2 py-0.5 text-[11px] cursor-pointer",
                p.id === pid ? "border-foreground bg-accent text-foreground" : "border-border text-muted-foreground hover:text-foreground",
              )}
            >
              {p.name}
            </button>
          ))}
        </div>
        <div className="flex flex-col gap-0.5 border-t px-3 py-1.5">
          {paths && (
            <>
              <PathStrip
                label="папка кода"
                value={paths.code}
                isDefault={paths.code === paths.defaults.code}
                onChoose={async () => {
                  const r = await fly!.chooseProjectFolder(pid, "code", `Папка кода: ${project?.name ?? pid}`);
                  if (r) {
                    setPaths(r);
                    setFiles(await fly!.listScripts(pid));
                  }
                }}
                onOpen={() => fly!.openPath(paths.code)}
                onReset={async () => {
                  setPaths(await fly!.resetProjectFolder(pid, "code"));
                  setFiles(await fly!.listScripts(pid));
                }}
              />
              <PathStrip
                label="папка прогонов"
                value={paths.runs}
                isDefault={paths.runs === paths.defaults.runs}
                onChoose={async () => {
                  const r = await fly!.chooseProjectFolder(pid, "runs", `Папка прогонов: ${project?.name ?? pid}`);
                  if (r) {
                    setPaths(r);
                    await refreshRuns();
                  }
                }}
                onOpen={() => fly!.openPath(paths.runs)}
                onReset={async () => {
                  setPaths(await fly!.resetProjectFolder(pid, "runs"));
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
      </div>

      {/* три колонки: файлы, код и результаты, помощник */}
      <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[235px_minmax(0,1fr)_340px] lg:divide-x">
        {/* --- слева: проводник --- */}
        <aside className="flex min-h-0 flex-col overflow-hidden border-b lg:border-b-0">
          <div className="flex shrink-0 items-center gap-1 border-b px-2 py-1.5">
            <span className="label">файлы, .py</span>
            <Button size="sm" variant="ghost" className="ml-auto" onClick={newFile}>
              новый
            </Button>
            <Button size="sm" variant="ghost" onClick={importFile}>
              импорт
            </Button>
          </div>
          <div className="min-h-[120px] flex-1 overflow-y-auto">
            {files.length === 0 && <p className="px-2 py-3 text-[11px] text-muted-foreground">Папка пуста.</p>}
            {files.map((f) => (
              <div key={f.name} className={cn("group flex items-center gap-1.5 border-b px-2 py-1", current === f.name && "bg-accent")}>
                <button onClick={() => openFile(f.name)} className="min-w-0 flex-1 text-left cursor-pointer" title={f.doc || f.name}>
                  <span className="block truncate font-mono text-[11px]">{f.name}</span>
                  <span className="block truncate text-[10px] text-muted-foreground">{f.doc || `${(f.size / 1024).toFixed(1)} КБ`}</span>
                </button>
                <button onClick={() => removeFile(f.name)} className="shrink-0 cursor-pointer px-1 text-[11px] text-muted-foreground hover:text-destructive" title="Удалить файл">
                  ×
                </button>
              </div>
            ))}
          </div>

          <div className="flex shrink-0 items-center gap-1 border-y px-2 py-1.5">
            <span className="label">прогоны</span>
            <Button size="sm" variant="ghost" className="ml-auto" onClick={() => refreshRuns()}>
              обновить
            </Button>
          </div>
          <div className="min-h-[100px] flex-1 overflow-y-auto">
            {runs.length === 0 && <p className="px-2 py-3 text-[11px] text-muted-foreground">Ещё ничего не запускалось.</p>}
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
            {current ? (
              <>
                <span className="font-mono text-[11px]">{current}</span>
                {dirty && <span className="label">не сохранено</span>}
                <Input value={args} onChange={(e) => setArgs(e.target.value)} placeholder="аргументы: --seed 1 --n-junk 25" className="h-6 w-[240px] font-mono text-[11px]" />
                <Button size="sm" variant="ghost" onClick={() => save()} disabled={!dirty}>
                  сохранить
                </Button>
                <Button size="sm" variant="ghost" onClick={exportFile} title="Сохранить копию в другое место">
                  копия
                </Button>
                {runId ? (
                  <Button size="sm" variant="outline" onClick={() => fly!.killRun(runId)}>
                    остановить
                  </Button>
                ) : (
                  <Button size="sm" onClick={run}>
                    запустить
                  </Button>
                )}
                <span className="ml-auto truncate font-mono text-[10px] text-muted-foreground">{saveNote}</span>
              </>
            ) : (
              <span className="label">выбери файл слева или создай новый: помощник тоже умеет их писать</span>
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
              <div className="flex h-full items-center justify-center border border-dashed">
                <p className="max-w-[420px] px-4 text-center text-[12px] leading-relaxed text-muted-foreground">
                  Здесь появится код. Слева шаблоны (00 проверка окружения, 02 игрушечная модель, 04 развёртка), справа помощник: он пишет файлы прямо в папку проекта.
                </p>
              </div>
            )}
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2 border-y px-2 py-1.5">
            <span className="label">результат</span>
            {selRun ? (
              <>
                <span className="max-w-[220px] truncate font-mono text-[10px] text-muted-foreground">{selRun.label}</span>
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
              </>
            ) : (
              <span className="label">прогонов ещё нет</span>
            )}
            <div className="ml-auto flex items-center gap-1.5">
              <Select value={ideaId} onValueChange={setIdeaId}>
                <SelectTrigger className="h-6 w-[230px] text-[11px]">
                  <SelectValue placeholder="в какую идею" />
                </SelectTrigger>
                <SelectContent>
                  {ideas.map((i) => (
                    <SelectItem key={i.id} value={i.id}>
                      {i.title}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button size="sm" onClick={toJournal} disabled={!selRun || !ideaId}>
                {added ? "добавлено" : "в журнал идеи"}
              </Button>
            </div>
          </div>

          <div ref={logRef} className="max-h-[40%] min-h-[130px] shrink-0 overflow-y-auto p-2">
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
              {liveLog || detail?.log || "лог появится здесь после запуска"}
            </pre>
          </div>
        </section>

        {/* --- справа: помощник --- */}
        <ChatColumn pid={pid} ideas={ideas} perms={perms} onAddReferences={onAddReferences} />
      </div>
    </div>
  );
}

// ================================================================
interface ChatMessage extends LlmMessage {
  actions?: string[];
}

function ChatColumn({ pid, ideas, perms, onAddReferences }: { pid: string; ideas: Idea[]; perms: Permissions | null; onAddReferences: (items: Partial<Reference>[]) => void }) {
  const [provider, setProvider] = useState<LlmProvider>("deepseek");
  const [model, setModel] = useState("deepseek-chat");
  const [msgs, setMsgs] = useState<ChatMessage[]>(() => {
    try {
      return JSON.parse(localStorage.getItem(`fly-ideas:chat:${pid}`) ?? "[]") as ChatMessage[];
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
    setMsgs((() => {
      try {
        return JSON.parse(localStorage.getItem(`fly-ideas:chat:${pid}`) ?? "[]") as ChatMessage[];
      } catch {
        return [];
      }
    })());
    fly!.getSecret("deepseek").then((k) => setKeys((s) => ({ ...s, deepseek: !!k })));
    fly!.getSecret("perplexity").then((k) => setKeys((s) => ({ ...s, perplexity: !!k })));
  }, [pid]);

  useEffect(() => {
    localStorage.setItem(`fly-ideas:chat:${pid}`, JSON.stringify(msgs.slice(-60)));
  }, [msgs, pid]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs, busy]);

  const saveKey = async () => {
    await fly!.setSecret(provider, keyInput.trim() || null);
    setKeys((s) => ({ ...s, [provider]: !!keyInput.trim() }));
    setKeyInput("");
  };

  const writeBlocks = async (blocks: { lang?: string; content: string }[]) => {
    const actions: string[] = [];
    for (const b of blocks) {
      if (!/^py/i.test(b.lang ?? "")) continue;
      const m = b.content.match(/^#\s*file:\s*([\w.\-]+\.py)/m);
      const stamp = new Date().toISOString().slice(11, 19).replace(/:/g, "");
      const name = m?.[1] ?? `assistant_${stamp}.py`;
      try {
        const r = await fly!.writeScript(pid, name, b.content);
        actions.push(`${r.created ? "создан" : "обновлён"} файл ${r.file}`);
      } catch (e) {
        actions.push(`не сохранено: ${(e as Error).message}`);
      }
    }
    return actions;
  };

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
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
      const actions = autoSave && blocks.length && (perms?.createFiles ?? false) ? await writeBlocks(blocks) : [];
      setMsgs((m) => [...m, { role: "assistant", content: r.content, actions }]);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const found = provider === "perplexity" && msgs.length ? parseReferencesFromText(msgs[msgs.length - 1].content) : [];

  return (
    <aside className="flex min-h-0 flex-col overflow-hidden">
      <div className="shrink-0 border-b px-2 py-1.5">
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
            сохранять код из ответа в папку проекта
            {!perms?.createFiles && <span className="text-muted-foreground/70">(выключено в правах)</span>}
          </label>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {msgs.length === 0 && (
          <div className="flex flex-col gap-2 py-4">
            <p className="text-[11px] leading-relaxed text-muted-foreground">
              {provider === "deepseek"
                ? "Попроси написать скрипт: помощник сохранит его в папку проекта, и файл сразу появится слева."
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
            <MessageBody content={m.content} onSaveCode={(code, name) => fly!.writeScript(pid, name, code, { allowOverwrite: true }).then(() => null)} />
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
    </aside>
  );
}

/** Текст ответа с блоками кода: у каждого блока кнопка сохранения в проект */
function MessageBody({ content, onSaveCode }: { content: string; onSaveCode: (code: string, name: string) => void }) {
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
              <Button
                size="sm"
                variant="outline"
                className="mt-1"
                onClick={() => {
                  const m = p.content.match(/^#\s*file:\s*([\w.\-]+\.py)/m);
                  const name = m?.[1] ?? prompt("Имя файла для скрипта:", "my_experiment.py") ?? "";
                  if (name) onSaveCode(p.content, name);
                }}
              >
                сохранить в проект
              </Button>
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
    ["Окружение", "там же видно Python и пакеты. Чего не хватает, поставь командой, которая написана рядом."],
    ["Первый прогон", "слева открой 00_check_env.py и запусти, затем 02_mb_toy_interference.py. Аргументы пишутся в поле над редактором: --relearn extinction --n-junk 25 --seed 1"],
    ["Результат", "внизу появятся графики, summary.json и лог. Кнопка «в журнал идеи» переносит запись в выбранную идею, дополни её в идее на вкладке «Журнал»."],
    ["Код помощником", "справа вставь ключ DeepSeek и напиши задачу словами. Файл из ответа сохраняется в папку проекта сам (галочка «сохранять код из ответа») либо кнопкой «сохранить в проект». Имя задаётся строкой # file: имя.py."],
    ["Литература", "переключи помощника на Perplexity (ключ с perplexity.ai), спроси про литературу и нажми «добавить в библиотеку»: строки с DOI разберутся в источники."],
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
                        onClick={() => fly!.openExternal(it.url.replace("raw.githubusercontent.com", "github.com").replace("/main/", "/blob/main/"))}
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
function EnvPanel() {
  const [env, setEnv] = useState<EnvInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const check = async () => {
    setLoading(true);
    try {
      setEnv(await fly!.checkEnv());
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    check();
  }, []);
  const need = ["numpy", "pandas", "pyarrow", "brian2"];
  const missing = env ? need.filter((m) => !env.packages[m]) : [];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={check} disabled={loading}>
          {loading ? "проверяю…" : "Проверить снова"}
        </Button>
        <span className="label">{env ? (missing.length ? `не хватает: ${missing.join(", ")}` : "для CPU-модели всё есть") : ""}</span>
      </div>

      {env && (
        <div className="grid gap-3 md:grid-cols-2">
          <section className="border">
            <div className="label border-b px-2 py-1.5">Python и GPU</div>
            <div className="flex flex-col p-2">
              <Row ok={!!env.python} label="Python 3" value={env.python ? `${env.python.version} (${env.python.cmd})` : "не найден"} />
              <Row ok={!!env.conda} label="conda" value={env.conda ?? "нет, не обязательно"} soft />
              <Row ok={!!env.gpu} label="GPU (CUDA)" value={env.gpu ?? "нет, CPU-запуски Brian2 работают и так"} soft />
            </div>
          </section>
          <section className="border">
            <div className="label border-b px-2 py-1.5">Пакеты</div>
            <div className="flex flex-col p-2">
              {Object.entries(env.packages).map(([k, v]) => (
                <Row key={k} ok={!!v} label={k} value={v ?? "не установлен"} soft={!need.includes(k)} />
              ))}
            </div>
          </section>
        </div>
      )}

      <section className="border">
        <div className="label border-b px-2 py-1.5">как поставить недостающее</div>
        <div className="flex flex-col gap-2 p-2 text-[12px]">
          {!env?.python && (
            <div>
              <div className="font-medium">1. Python</div>
              <p className="text-muted-foreground">
                Проще всего поставить{" "}
                <a className="underline" href="https://docs.anaconda.com/miniconda/" target="_blank" rel="noreferrer">
                  Miniconda
                </a>{" "}
                (Windows 64-bit), при установке отметить «Add to PATH», затем перезапустить программу.
              </p>
            </div>
          )}
          <div>
            <div className="font-medium">{env?.python ? "1" : "2"}. Пакеты для CPU-модели</div>
            <pre className="mt-1 overflow-x-auto border bg-muted/40 p-2 font-mono text-[11px]">pip install numpy pandas pyarrow scipy matplotlib brian2</pre>
          </div>
          <div>
            <div className="font-medium">{env?.python ? "2" : "3"}. GPU-бэкенды, потом</div>
            <p className="text-muted-foreground">
              PyTorch с CUDA: <code className="bg-muted px-1">pip install torch --index-url https://download.pytorch.org/whl/cu124</code>. Brian2CUDA и GeNN ставятся через WSL2, скрипт лежит в репозитории Eon.
            </p>
          </div>
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
