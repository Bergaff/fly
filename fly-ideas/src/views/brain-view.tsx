import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Bot, Check, CircleAlert, Cpu, Download, ExternalLink, FolderInput, FolderOpen, FolderOutput, HardDrive, ImageIcon, KeyRound, Loader2, NotebookPen, Play, RefreshCw, RotateCcw, Send, Square, Terminal, X } from "lucide-react";
import type { Idea } from "@/data/types";
import { fly, fmtBytes, isElectron, type DataItem, type DirKind, type EnvInfo, type ExternalSource, type LlmMessage, type Paths, type RunInfo, type ScriptInfo } from "@/lib/bridge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

interface Props {
  ideas: Idea[];
  onAddJournalEntry: (ideaId: string, entry: { title: string; params: string; result: string; conclusion: string }) => void;
}

export function BrainView({ ideas, onAddJournalEntry }: Props) {
  if (!isElectron) return <WebFallback />;
  return (
    <div className="flex h-full flex-col overflow-y-auto p-6">
      <Tabs defaultValue="data" className="gap-4">
        <TabsList>
          <TabsTrigger value="data"><HardDrive /> Данные мозга</TabsTrigger>
          <TabsTrigger value="env"><Cpu /> Окружение</TabsTrigger>
          <TabsTrigger value="scripts"><Terminal /> Скрипты</TabsTrigger>
          <TabsTrigger value="runs"><NotebookPen /> Прогоны</TabsTrigger>
          <TabsTrigger value="assistant"><Bot /> Помощник</TabsTrigger>
        </TabsList>
        <TabsContent value="data"><DataPanel /></TabsContent>
        <TabsContent value="env"><EnvPanel /></TabsContent>
        <TabsContent value="scripts"><ScriptsPanel /></TabsContent>
        <TabsContent value="runs"><RunsPanel ideas={ideas} onAddJournalEntry={onAddJournalEntry} /></TabsContent>
        <TabsContent value="assistant"><AssistantPanel ideas={ideas} /></TabsContent>
      </Tabs>
    </div>
  );
}

// ------------------------------------------------------------------
/** Строка «Папка: путь [Выбрать…] [Открыть] [Сбросить]» */
function FolderBar({ kind, label, paths, onChanged }: { kind: DirKind; label: string; paths: Paths | null; onChanged: () => void }) {
  const cur = paths?.[kind];
  const isDefault = !!paths && paths.defaults[kind] === cur;
  return (
    <div className="flex flex-wrap items-center gap-1.5 rounded-lg border bg-muted/30 px-2.5 py-1.5 text-xs">
      <FolderInput className="size-3.5 text-muted-foreground" />
      <span className="text-muted-foreground">{label}:</span>
      <span className="min-w-0 flex-1 truncate font-mono" title={cur ?? ""}>{cur ?? "…"}</span>
      <Button size="sm" variant="outline" className="h-7" onClick={async () => { const p = await fly!.chooseFolder(kind, `${label} — выбери папку`); if (p) onChanged(); }}>Выбрать…</Button>
      <Button size="sm" variant="ghost" className="h-7" onClick={() => cur && fly!.openPath(cur)} title="Открыть в проводнике"><FolderOpen /></Button>
      {!isDefault && <Button size="sm" variant="ghost" className="h-7" title="Вернуть папку по умолчанию" onClick={async () => { await fly!.resetFolder(kind); onChanged(); }}><RotateCcw /></Button>}
    </div>
  );
}

function WebFallback() {
  return (
    <div className="flex h-full items-center justify-center p-6">
      <Card className="max-w-lg">
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><CircleAlert className="size-4" /> Доступно только в окне программы</CardTitle>
          <CardDescription>Скачивание мозга, запуск скриптов и помощник работают через Electron (нужен доступ к диску и Python). В браузере эта вкладка отключена.</CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Запусти <code className="rounded bg-muted px-1">START.bat</code> — откроется окно, и здесь появятся кнопки «Скачать», «Запустить» и чат с помощником.
        </CardContent>
      </Card>
    </div>
  );
}

// ------------------------------------------------------------------
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
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => fly!.onDownloadProgress((p) => setProgress((s) => ({ ...s, [p.id]: { got: p.got, total: p.total } }))), []);

  const dl = async (item: DataItem, destDir?: string) => {
    setBusy((b) => ({ ...b, [item.id]: true }));
    setErrors((e) => ({ ...e, [item.id]: "" }));
    try {
      const r = await fly!.download(item, destDir);
      if (r.size < 2000 && item.sizeMB > 1) setErrors((e) => ({ ...e, [item.id]: "Скачался крошечный файл — это заглушка Git LFS. Скачай вручную из репозитория (кнопка ↗)." }));
    } catch (e) {
      setErrors((er) => ({ ...er, [item.id]: (e as Error).message }));
    } finally {
      setBusy((b) => ({ ...b, [item.id]: false }));
      setProgress((p) => { const n = { ...p }; delete n[item.id]; return n; });
      refresh();
    }
  };
  const dlAll = async () => { for (const it of items.filter((i) => !i.present)) await dl(it); };
  const dlAllTo = async () => {
    const dir = await fly!.pickFolder("Куда скачать все файлы данных");
    if (!dir) return;
    for (const it of items.filter((i) => i.dest !== "scripts")) await dl(it, dir);
  };
  const dlTo = async (item: DataItem) => {
    const dir = await fly!.pickFolder(`Куда скачать ${item.file}`);
    if (dir) await dl(item, dir);
  };

  const groups = useMemo(() => [...new Set(items.map((i) => i.group))], [items]);
  const missing = items.filter((i) => !i.present).length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={dlAll} disabled={!missing || Object.values(busy).some(Boolean)}>
          <Download /> {missing ? `Скачать мозг мухи (${missing} файл.)` : "Всё скачано"}
        </Button>
        <Button variant="outline" onClick={dlAllTo} disabled={Object.values(busy).some(Boolean)} title="Скачать данные в другую папку (например, на большой диск)"><FolderOutput /> Скачать в папку…</Button>
        <Button variant="ghost" size="icon" onClick={refresh}><RefreshCw /></Button>
      </div>
      <FolderBar kind="data" label="Папка данных" paths={paths} onChanged={refresh} />
      <p className="text-xs text-muted-foreground">
        Файлы берутся из открытого репозитория <a className="underline" href="https://github.com/eonsystemspbc/fly-brain" target="_blank" rel="noreferrer">eonsystemspbc/fly-brain</a> — это FlyWire v783 (последний публичный релиз коннектома, тот же, что в Nature 2024) и код модели Shiu et al. Полный мозг — ~100 МБ таблиц, не терабайты: сырые ЭМ-снимки для симуляции не нужны. Ссылки проверены 18.09.2026.
      </p>
      {groups.map((g) => (
        <Card key={g} className="gap-2">
          <CardHeader><CardTitle className="text-sm">{g}</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-2">
            {items.filter((i) => i.group === g).map((it) => {
              const pr = progress[it.id];
              const pct = pr && pr.total ? Math.round((pr.got / pr.total) * 100) : null;
              return (
                <div key={it.id} className="rounded-lg border px-3 py-2">
                  <div className="flex items-center gap-3">
                    <span className={cn("flex size-5 shrink-0 items-center justify-center rounded-full border", it.present ? "border-[var(--chart-2)] bg-[var(--chart-2)]/15 text-[var(--chart-2)]" : "border-muted-foreground/30")}>
                      {it.present && <Check className="size-3" strokeWidth={3} />}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm">{it.title} <span className="font-mono text-[11px] text-muted-foreground">{it.file}</span></div>
                      <div className="text-xs text-muted-foreground">{it.note}</div>
                    </div>
                    <span className="shrink-0 font-mono text-xs text-muted-foreground">{it.present ? fmtBytes(it.size) : `~${it.sizeMB} МБ`}</span>
                    <Button size="icon-sm" variant="ghost" title="Открыть источник" onClick={() => fly!.openExternal(it.url.replace("raw.githubusercontent.com", "github.com").replace("/main/", "/blob/main/"))}><ExternalLink /></Button>
                    {busy[it.id] ? (
                      <Button size="sm" variant="outline" onClick={() => fly!.cancelDownload(it.id)}><Square className="size-3" /> {pct ?? "…"}%</Button>
                    ) : (
                      <>
                        <Button size="icon-sm" variant="ghost" title="Скачать в другую папку…" onClick={() => dlTo(it)}><FolderOutput /></Button>
                        <Button size="sm" variant={it.present ? "ghost" : "default"} onClick={() => dl(it)}><Download /> {it.present ? "Обновить" : "Скачать"}</Button>
                      </>
                    )}
                  </div>
                  {pr && <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted"><div className="h-full bg-[var(--chart-1)] transition-all" style={{ width: `${pct ?? 5}%` }} /></div>}
                  {errors[it.id] && <div className="mt-1.5 text-xs text-destructive">{errors[it.id]}</div>}
                </div>
              );
            })}
          </CardContent>
        </Card>
      ))}
      {external.length > 0 && (
        <Card className="gap-2">
          <CardHeader>
            <CardTitle className="text-sm">Внешние источники (вручную)</CardTitle>
            <CardDescription className="text-xs">Официальные выгрузки и аннотации — требуют аккаунта или лежат не одним файлом. Открываются в браузере; скачанное можно положить в папку данных.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-1.5">
            {external.map((e) => (
              <button key={e.url} onClick={() => fly!.openExternal(e.url)} className="flex items-center gap-2 rounded-md border px-3 py-2 text-left text-sm hover:bg-accent cursor-pointer">
                <ExternalLink className="size-3.5 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <div>{e.title}</div>
                  <div className="text-xs text-muted-foreground">{e.note}</div>
                </div>
              </button>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ------------------------------------------------------------------
function EnvPanel() {
  const [env, setEnv] = useState<EnvInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const check = async () => { setLoading(true); try { setEnv(await fly!.checkEnv()); } finally { setLoading(false); } };
  useEffect(() => { check(); }, []);
  const need = ["numpy", "pandas", "pyarrow", "brian2"];
  const missing = env ? need.filter((m) => !env.packages[m]) : [];
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={check} disabled={loading}>{loading ? <Loader2 className="animate-spin" /> : <RefreshCw />} Проверить снова</Button>
      </div>
      {env && (
        <div className="grid gap-4 md:grid-cols-2">
          <Card className="gap-2">
            <CardHeader><CardTitle className="text-sm">Python и GPU</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-1.5 text-sm">
              <Row ok={!!env.python} label="Python 3" value={env.python ? `${env.python.version} (${env.python.cmd})` : "не найден"} />
              <Row ok={!!env.conda} label="conda" value={env.conda ?? "нет (не обязательно)"} soft />
              <Row ok={!!env.gpu} label="GPU (CUDA)" value={env.gpu ?? "нет — CPU-запуски Brian2 работают и так"} soft />
            </CardContent>
          </Card>
          <Card className="gap-2">
            <CardHeader><CardTitle className="text-sm">Пакеты</CardTitle></CardHeader>
            <CardContent className="flex flex-col gap-1.5 text-sm">
              {Object.entries(env.packages).map(([k, v]) => <Row key={k} ok={!!v} label={k} value={v ?? "не установлен"} soft={!need.includes(k)} />)}
            </CardContent>
          </Card>
        </div>
      )}
      <Card className="gap-2">
        <CardHeader>
          <CardTitle className="text-sm">Как поставить недостающее</CardTitle>
          <CardDescription>{missing.length ? `Не хватает: ${missing.join(", ")}` : env?.python ? "Для CPU-модели всё есть" : "Сначала Python"}</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 text-sm">
          {!env?.python && (
            <div>
              <div className="font-medium">1. Python</div>
              <p className="text-muted-foreground">Проще всего — <a className="underline" href="https://docs.anaconda.com/miniconda/" target="_blank" rel="noreferrer">Miniconda</a> (Windows 64-bit). При установке поставь галочку «Add to PATH». Затем перезапусти программу.</p>
            </div>
          )}
          <div>
            <div className="font-medium">{env?.python ? "1" : "2"}. Пакеты для CPU-модели (Anaconda Prompt или PowerShell)</div>
            <pre className="mt-1 overflow-x-auto rounded-md bg-muted p-2 font-mono text-xs">pip install numpy pandas pyarrow scipy matplotlib brian2</pre>
          </div>
          <div>
            <div className="font-medium">{env?.python ? "2" : "3"}. GPU-бэкенды (потом, когда упрёшься в скорость)</div>
            <p className="text-muted-foreground">PyTorch с CUDA: <code className="rounded bg-muted px-1">pip install torch --index-url https://download.pytorch.org/whl/cu124</code>. Brian2CUDA / GeNN — через WSL2, скрипт есть в репозитории Eon (<code className="rounded bg-muted px-1">scripts/setup_WSL_CUDA.sh</code>).</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ ok, label, value, soft }: { ok: boolean; label: string; value: string; soft?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span className={cn("size-2 rounded-full", ok ? "bg-[var(--chart-2)]" : soft ? "bg-muted-foreground/40" : "bg-destructive")} />
      <span className="w-24 text-muted-foreground">{label}</span>
      <span className="truncate font-mono text-xs">{value}</span>
    </div>
  );
}

// ------------------------------------------------------------------
function ScriptsPanel() {
  const [scripts, setScripts] = useState<ScriptInfo[]>([]);
  const [sel, setSel] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [dirty, setDirty] = useState(false);
  const [args, setArgs] = useState("");
  const [log, setLog] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [paths, setPaths] = useState<Paths | null>(null);
  const logRef = useRef<HTMLPreElement>(null);

  const refresh = useCallback(async () => { setScripts(await fly!.listScripts()); setPaths(await fly!.getPaths()); }, []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => fly!.onRunOutput((p) => {
    setLog((l) => l + p.text);
    if (p.stream === "exit") setRunId(null);
  }), []);
  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight }); }, [log]);

  const open = async (name: string) => { setSel(name); setCode(await fly!.readScript(name)); setDirty(false); };
  const save = async () => { if (sel) { await fly!.writeScript(sel, code); setDirty(false); refresh(); } };
  const run = async () => {
    if (!sel) return;
    if (dirty) await save();
    setLog("");
    const r = await fly!.runScript(sel, args.split(/\s+/).filter(Boolean));
    setRunId(r.runId);
    setLog(`$ python ${sel} ${args}\n→ ${r.runDir}\n\n`);
  };

  const importScript = async () => {
    const f = await fly!.openFile({ filters: [{ name: "Python", extensions: ["py"] }], kind: "exports" });
    if (!f) return;
    const name = f.path.replace(/^.*[\\/]/, "");
    await fly!.writeScript(name, f.content);
    await refresh();
    open(name);
  };
  const exportScript = async () => {
    if (!sel) return;
    const p = await fly!.saveFile({ defaultName: sel, content: code, filters: [{ name: "Python", extensions: ["py"] }] });
    if (p) alert(`Сохранено: ${p}`);
  };

  return (
    <div className="flex flex-col gap-3">
    <div className="grid gap-2 lg:grid-cols-2">
      <FolderBar kind="scripts" label="Папка скриптов" paths={paths} onChanged={async () => { await refresh(); setSel(null); }} />
      <FolderBar kind="runs" label="Папка прогонов" paths={paths} onChanged={refresh} />
    </div>
    <div className="grid gap-4 lg:grid-cols-[260px_1fr]">
      <Card className="gap-2 self-start">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">Скрипты</CardTitle>
          <Button size="icon-sm" variant="ghost" onClick={importScript} title="Добавить .py с диска"><FolderInput /></Button>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          {scripts.map((s) => (
            <button key={s.name} onClick={() => open(s.name)} className={cn("rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent cursor-pointer", sel === s.name && "bg-accent")}>
              <div className="font-mono text-xs">{s.name}</div>
              {s.doc && <div className="line-clamp-2 text-[11px] text-muted-foreground">{s.doc}</div>}
            </button>
          ))}
          <p className="mt-2 text-[11px] text-muted-foreground">Положи свой .py в папку — он появится здесь. Скрипт получает переменные окружения FLY_DATA, FLY_RUN_DIR; если запишет summary.json в FLY_RUN_DIR — результат подхватится во вкладке «Прогоны».</p>
        </CardContent>
      </Card>
      <div className="flex min-w-0 flex-col gap-3">
        {sel ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm">{sel}</span>
              {dirty && <Badge variant="secondary">не сохранено</Badge>}
              <Input value={args} onChange={(e) => setArgs(e.target.value)} placeholder="аргументы: --seed 1 --n-junk 100" className="h-8 w-[320px] font-mono text-xs" />
              <div className="ml-auto flex gap-2">
                <Button variant="ghost" size="sm" onClick={exportScript} title="Сохранить копию в другое место"><FolderOutput /> Копия…</Button>
                <Button variant="outline" size="sm" onClick={save} disabled={!dirty}>Сохранить</Button>
                {runId ? (
                  <Button size="sm" variant="destructive" onClick={() => fly!.killRun(runId)}><Square /> Остановить</Button>
                ) : (
                  <Button size="sm" onClick={run}><Play /> Запустить</Button>
                )}
              </div>
            </div>
            <Textarea value={code} onChange={(e) => { setCode(e.target.value); setDirty(true); }} spellCheck={false} className="min-h-[260px] font-mono text-[12px] leading-relaxed" />
            <pre ref={logRef} className="max-h-[300px] min-h-[120px] overflow-auto rounded-md border bg-muted/40 p-3 font-mono text-[12px] whitespace-pre-wrap">{log || "Вывод появится здесь."}</pre>
          </>
        ) : (
          <div className="flex h-full min-h-[200px] items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">Выбери скрипт слева. Начни с 00_check_env.py.</div>
        )}
      </div>
    </div>
    </div>
  );
}

// ------------------------------------------------------------------
function RunsPanel({ ideas, onAddJournalEntry }: Props) {
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [sel, setSel] = useState<RunInfo | null>(null);
  const [detail, setDetail] = useState<{ log: string; summary: Record<string, unknown> | null } | null>(null);
  const [ideaId, setIdeaId] = useState<string>(ideas[0]?.id ?? "");
  const [added, setAdded] = useState<string | null>(null);
  const [paths, setPaths] = useState<Paths | null>(null);
  const [images, setImages] = useState<{ name: string; dataUrl: string }[]>([]);
  const [viewFile, setViewFile] = useState<{ name: string; text: string } | null>(null);

  const refresh = useCallback(async () => { setRuns(await fly!.listRuns()); setPaths(await fly!.getPaths()); }, []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (!sel) return;
    setViewFile(null);
    fly!.readRun(sel.dir).then(setDetail);
    const imgs = sel.files.filter((f) => /\.(png|jpe?g|svg|gif)$/i.test(f));
    Promise.all(imgs.map(async (name) => { const r = await fly!.readRunFile(sel.dir, name); return r.kind === "image" ? { name, dataUrl: r.dataUrl } : null; })).then((r) => setImages(r.filter((x): x is { name: string; dataUrl: string } => !!x)));
  }, [sel]);
  const otherFiles = sel ? sel.files.filter((f) => !/\.(png|jpe?g|svg|gif)$/i.test(f) && f !== "log.txt" && f !== "summary.json") : [];

  const toJournal = () => {
    if (!sel || !ideaId) return;
    const summary = detail?.summary;
    const args = summary && typeof summary.args === "object" ? JSON.stringify(summary.args) : "";
    const script = sel.dir.replace(/^\S+?_/, "");
    onAddJournalEntry(ideaId, {
      title: `Прогон ${script}`,
      params: [`run: ${sel.dir}`, args && `args: ${args}`].filter(Boolean).join("\n"),
      result: [summary ? JSON.stringify(summary, null, 2).slice(0, 1400) : (detail?.log ?? "").slice(-1200), images.length ? `графики: ${images.map((i) => i.name).join(", ")}` : ""].filter(Boolean).join("\n"),
      conclusion: "",
    });
    setAdded(sel.dir);
    setTimeout(() => setAdded(null), 2500);
  };

  return (
    <div className="flex flex-col gap-3">
    <FolderBar kind="runs" label="Папка прогонов" paths={paths} onChanged={async () => { setSel(null); await refresh(); }} />
    <div className="grid gap-4 lg:grid-cols-[320px_1fr]">
      <Card className="gap-2 self-start">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">Прогоны</CardTitle>
          <Button size="icon-sm" variant="ghost" onClick={refresh}><RefreshCw /></Button>
        </CardHeader>
        <CardContent className="flex max-h-[60vh] flex-col gap-1 overflow-y-auto">
          {runs.length === 0 && <div className="text-xs text-muted-foreground">Пока пусто — запусти скрипт.</div>}
          {runs.map((r) => (
            <button key={r.dir} onClick={() => setSel(r)} className={cn("rounded-md px-2 py-1.5 text-left hover:bg-accent cursor-pointer", sel?.dir === r.dir && "bg-accent")}>
              <div className="font-mono text-[11px]">{r.dir}</div>
              <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">{r.summary ? "summary.json ✓" : "без summary"} · {r.files.length} файл.{r.files.some((f) => /\.(png|jpe?g|svg)$/i.test(f)) && <ImageIcon className="size-3" />}</div>
            </button>
          ))}
        </CardContent>
      </Card>
      <div className="flex min-w-0 flex-col gap-3">
        {sel ? (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-mono text-sm">{sel.dir}</span>
              <Button size="sm" variant="ghost" onClick={() => fly!.openPath(sel.path)}><FolderOpen /> Папка</Button>
              <Button size="sm" variant="ghost" title="Скопировать папку прогона в другое место" onClick={async () => { const p = await fly!.exportRun(sel.dir); if (p) alert(`Скопировано: ${p}`); }}><FolderOutput /> Экспорт…</Button>
              <div className="ml-auto flex items-center gap-2">
                <Select value={ideaId} onValueChange={setIdeaId}>
                  <SelectTrigger className="h-8 w-[280px] text-xs"><SelectValue placeholder="В какую идею" /></SelectTrigger>
                  <SelectContent>{ideas.map((i) => <SelectItem key={i.id} value={i.id}>{i.title}</SelectItem>)}</SelectContent>
                </Select>
                <Button size="sm" onClick={toJournal} disabled={!ideaId}>{added === sel.dir ? <><Check /> Добавлено</> : <><NotebookPen /> В журнал идеи</>}</Button>
              </div>
            </div>
            {images.length > 0 && (
              <div className="grid gap-3 md:grid-cols-2">
                {images.map((im) => (
                  <figure key={im.name} className="overflow-hidden rounded-lg border bg-white">
                    <img src={im.dataUrl} alt={im.name} className="w-full" />
                    <figcaption className="border-t bg-card px-2 py-1 font-mono text-[11px] text-muted-foreground">{im.name}</figcaption>
                  </figure>
                ))}
              </div>
            )}
            {otherFiles.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {otherFiles.map((f) => (
                  <button key={f} onClick={async () => { const r = await fly!.readRunFile(sel.dir, f); if (r.kind === "text") setViewFile({ name: f, text: r.text }); }} className={cn("rounded-md border px-2 py-1 font-mono text-[11px] hover:bg-accent cursor-pointer", viewFile?.name === f && "bg-accent")}>{f}</button>
                ))}
              </div>
            )}
            {viewFile && <pre className="max-h-[300px] overflow-auto rounded-md border bg-muted/40 p-3 font-mono text-[11px] whitespace-pre-wrap">{viewFile.text}</pre>}
            {detail?.summary && (
              <pre className="max-h-[300px] overflow-auto rounded-md border bg-muted/40 p-3 font-mono text-[12px]">{JSON.stringify(detail.summary, null, 2)}</pre>
            )}
            <pre className="max-h-[360px] overflow-auto rounded-md border p-3 font-mono text-[12px] whitespace-pre-wrap text-muted-foreground">{detail?.log || "лог пуст"}</pre>
          </>
        ) : (
          <div className="flex min-h-[200px] items-center justify-center rounded-lg border border-dashed text-sm text-muted-foreground">Выбери прогон, чтобы посмотреть результат и отправить его в журнал идеи.</div>
        )}
      </div>
    </div>
    </div>
  );
}

// ------------------------------------------------------------------
const SYSTEM_PROMPT = `Ты — научный ассистент аспиранта, который работает с вычислительной моделью мозга дрозофилы (LIF-модель Shiu et al. 2024 на коннектоме FlyWire v783; репозитории philshiu/Drosophila_brain_model и eonsystemspbc/fly-brain; Brian2, PyTorch). Пользователь пишет код с помощью ИИ и интересуется когнитивистикой: память, обучение в грибовидных телах, интерференция, социальное обучение.
Правила: отвечай по-русски, кратко и конкретно. Если пишешь код — Python, полный запускаемый файл, с argparse, читающий пути из переменных окружения FLY_DATA (данные) и FLY_RUN_DIR (куда писать summary.json и графики). Не выдумывай API Brian2 — если не уверен, скажи, что нужно проверить в документации. Честно указывай ограничения LIF-модели.`;

function AssistantPanel({ ideas }: { ideas: Idea[] }) {
  const [key, setKey] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [model, setModel] = useState("deepseek-chat");
  const [msgs, setMsgs] = useState<LlmMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [ctxIdea, setCtxIdea] = useState<string>("none");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fly!.getSecret("deepseek").then(setKey); }, []);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const saveKey = async () => { await fly!.setSecret("deepseek", keyInput.trim() || null); setKey(await fly!.getSecret("deepseek")); setKeyInput(""); setShowKey(false); };

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setErr("");
    const idea = ideas.find((i) => i.id === ctxIdea);
    const ctx = idea ? `\n\nКонтекст — текущая идея пользователя:\nНазвание: ${idea.title}\nВопрос: ${idea.question}\nМетод:\n${idea.method}\nВалидация: ${idea.validation}\nЗаметки: ${idea.notes}` : "";
    const next: LlmMessage[] = [...msgs, { role: "user", content: text }];
    setMsgs(next);
    setInput("");
    setBusy(true);
    try {
      const r = await fly!.llmChat({ provider: "deepseek", model, messages: [{ role: "system", content: SYSTEM_PROMPT + ctx }, ...next.slice(-12)] });
      setMsgs([...next, { role: "assistant", content: r.content }]);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const saveCodeBlock = async (code: string) => {
    const m = code.match(/^#\s*file:\s*(\S+\.py)/m);
    const name = m?.[1] ?? prompt("Имя файла для скрипта:", "my_experiment.py");
    if (!name) return;
    await fly!.writeScript(name, code);
    alert(`Сохранено: ${name} — смотри вкладку «Скрипты».`);
  };

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
      <Card className="flex min-h-[60vh] flex-col gap-0 py-0">
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {msgs.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
              <Bot className="size-8 opacity-40" />
              <p>Спроси про модель, попроси написать скрипт эксперимента или объяснить вывод прогона.</p>
              <div className="mt-2 flex flex-wrap justify-center gap-1.5">
                {["Напиши скрипт: обучить MB запаху A с ударом и проверить избегание", "Объясни, что делает 02_mb_toy_interference.py", "Какие нейроны FlyWire относятся к PPL1 и как их найти в Completeness?"].map((q) => (
                  <button key={q} onClick={() => setInput(q)} className="rounded-full border px-2.5 py-1 text-xs hover:bg-accent cursor-pointer">{q}</button>
                ))}
              </div>
            </div>
          )}
          {msgs.map((m, i) => <Message key={i} m={m} onSaveCode={saveCodeBlock} />)}
          {busy && <div className="flex items-center gap-2 text-xs text-muted-foreground"><Loader2 className="size-3 animate-spin" /> думает…</div>}
          {err && <div className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-xs text-destructive">{err}</div>}
          <div ref={endRef} />
        </div>
        <div className="flex items-end gap-2 border-t p-3">
          <Textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} placeholder="Сообщение (Enter — отправить, Shift+Enter — перенос)" className="min-h-[44px] max-h-[160px]" disabled={!key} />
          <Button onClick={send} disabled={!key || busy || !input.trim()}><Send /></Button>
        </div>
      </Card>
      <div className="flex flex-col gap-3">
        <Card className="gap-2">
          <CardHeader><CardTitle className="flex items-center gap-2 text-sm"><KeyRound className="size-4" /> DeepSeek API</CardTitle></CardHeader>
          <CardContent className="flex flex-col gap-2 text-xs">
            {key && !showKey ? (
              <div className="flex items-center gap-2"><span className="size-2 rounded-full bg-[var(--chart-2)]" /><span className="font-mono">{key}</span><Button size="sm" variant="ghost" className="ml-auto h-6 px-2" onClick={() => setShowKey(true)}>Сменить</Button></div>
            ) : (
              <>
                <Input type="password" value={keyInput} onChange={(e) => setKeyInput(e.target.value)} placeholder="sk-…" className="h-8 font-mono text-xs" />
                <div className="flex gap-1.5">
                  <Button size="sm" className="h-7" onClick={saveKey} disabled={!keyInput.trim()}>Сохранить</Button>
                  {key && <Button size="sm" variant="ghost" className="h-7" onClick={() => setShowKey(false)}><X /></Button>}
                </div>
              </>
            )}
            <p className="text-muted-foreground">Ключ хранится только на этом компьютере (папка данных программы) и уходит только на api.deepseek.com. Взять ключ: <a className="underline" href="https://platform.deepseek.com/api_keys" target="_blank" rel="noreferrer">platform.deepseek.com</a>.</p>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="deepseek-chat">deepseek-chat (быстрый)</SelectItem>
                <SelectItem value="deepseek-reasoner">deepseek-reasoner (думает дольше)</SelectItem>
              </SelectContent>
            </Select>
          </CardContent>
        </Card>
        <Card className="gap-2">
          <CardHeader><CardTitle className="text-sm">Контекст</CardTitle><CardDescription className="text-xs">Помощник увидит вопрос и метод выбранной идеи</CardDescription></CardHeader>
          <CardContent>
            <Select value={ctxIdea} onValueChange={setCtxIdea}>
              <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">без идеи</SelectItem>
                {ideas.map((i) => <SelectItem key={i.id} value={i.id}>{i.title}</SelectItem>)}
              </SelectContent>
            </Select>
            <Button variant="ghost" size="sm" className="mt-2 w-full" onClick={() => setMsgs([])} disabled={!msgs.length}>Очистить чат</Button>
          </CardContent>
        </Card>
        <p className="text-[11px] text-muted-foreground">Если в ответе есть блок кода Python, под ним появится кнопка «Сохранить как скрипт» — файл попадёт в папку скриптов, и его можно сразу запустить. Чтобы задать имя, добавь в первую строку кода комментарий <code className="rounded bg-muted px-1"># file: имя.py</code>.</p>
      </div>
    </div>
  );
}

function Message({ m, onSaveCode }: { m: LlmMessage; onSaveCode: (code: string) => void }) {
  const parts = useMemo(() => {
    const out: { type: "text" | "code"; content: string; lang?: string }[] = [];
    const re = /```(\w+)?\n([\s\S]*?)```/g;
    let last = 0, mm: RegExpExecArray | null;
    while ((mm = re.exec(m.content))) {
      if (mm.index > last) out.push({ type: "text", content: m.content.slice(last, mm.index) });
      out.push({ type: "code", content: mm[2], lang: mm[1] });
      last = mm.index + mm[0].length;
    }
    if (last < m.content.length) out.push({ type: "text", content: m.content.slice(last) });
    return out;
  }, [m.content]);
  return (
    <div className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
      <div className={cn("max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm", m.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted")}>
        {parts.map((p, i) =>
          p.type === "text" ? (
            <div key={i} className="whitespace-pre-wrap leading-relaxed">{p.content.trim()}</div>
          ) : (
            <div key={i} className="my-2">
              <pre className="overflow-x-auto rounded-md border bg-background p-2.5 font-mono text-[12px] text-foreground">{p.content}</pre>
              {(p.lang ?? "").match(/^py/i) && (
                <Button size="sm" variant="outline" className="mt-1 h-7 text-xs" onClick={() => onSaveCode(p.content)}><Terminal /> Сохранить как скрипт</Button>
              )}
            </div>
          ),
        )}
      </div>
    </div>
  );
}
