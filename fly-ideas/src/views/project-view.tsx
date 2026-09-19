import { useEffect, useMemo, useState } from "react";
import type { Idea, Project, Reference } from "@/data/types";
import { OUTCOME_LABELS, STATUS_COLORS, STATUS_LABELS, STATUS_ORDER, checklistProgress } from "@/data/types";
import { priorityOf } from "@/lib/priority";
import { fly, type ProjectPaths, type RunInfo } from "@/lib/bridge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { DeadlineBadge } from "@/components/deadline-badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const PALETTE = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--chart-5)"];

interface Props {
  project: Project;
  ideas: Idea[];
  references: Reference[];
  onUpdate: (patch: Partial<Project>) => void;
  onOpenWorkspace: () => void;
  onOpenIdea: (id: string) => void;
  onAddIdea: () => void;
  onShowIdeas: () => void;
  onShowDashboard: () => void;
}

/** Страница проекта: описание, состояние работы, кнопка начала и продолжения в рабочем месте. */
export function ProjectView({
  project,
  ideas,
  references,
  onUpdate,
  onOpenWorkspace,
  onOpenIdea,
  onAddIdea,
  onShowIdeas,
  onShowDashboard,
}: Props) {
  const [paths, setPaths] = useState<ProjectPaths | null>(null);
  const [runs, setRuns] = useState<RunInfo[]>([]);
  const [desc, setDesc] = useState(project.description);
  const [name, setName] = useState(project.name);
  const [folders, setFolders] = useState(false);

  useEffect(() => {
    setDesc(project.description);
    setName(project.name);
  }, [project.id, project.description, project.name]);

  useEffect(() => {
    let alive = true;
    if (!fly) {
      setPaths(null);
      setRuns([]);
      return;
    }
    void fly.projectPaths(project.id).then((p) => alive && setPaths(p));
    void fly.listRuns(project.id).then((r) => alive && setRuns(r));
    return () => {
      alive = false;
    };
  }, [project.id]);

  const stats = useMemo(() => {
    const inWork = ideas.filter((i) => ["exploring", "active", "drafting"].includes(i.status)).length;
    const done = ideas.filter((i) => ["submitted", "done"].includes(i.status)).length;
    const progress = ideas.map((i) => checklistProgress(i));
    const pct = progress.length ? Math.round(progress.reduce((s, p) => s + p.pct, 0) / progress.length) : 0;
    const steps = progress.reduce((s, p) => ({ done: s.done + p.done, total: s.total + p.total }), { done: 0, total: 0 });
    const refs = new Set(ideas.flatMap((i) => i.citations.map((c) => c.refId)));
    const experiments = ideas.reduce((s, i) => s + i.experiments.length, 0);
    const deadlines = ideas
      .filter((i) => i.deadline && !["done", "parked"].includes(i.status))
      .sort((a, b) => (a.deadline ?? "").localeCompare(b.deadline ?? ""));
    const tags = Array.from(new Set(ideas.flatMap((i) => i.tags))).slice(0, 12);
    return { inWork, done, pct, steps, refs, refIds: Array.from(refs), experiments, nextDeadline: deadlines[0] ?? null, tags };
  }, [ideas]);

  const columns = useMemo(() => {
    return STATUS_ORDER.map((s) => ({ status: s, items: ideas.filter((i) => i.status === s) })).filter((c) => c.items.length);
  }, [ideas]);

  const journal = useMemo(
    () =>
      ideas
        .flatMap((i) => i.experiments.map((e) => ({ idea: i, e })))
        .sort((a, b) => (b.e.date + b.e.createdAt).localeCompare(a.e.date + a.e.createdAt))
        .slice(0, 6),
    [ideas],
  );

  const ranked = useMemo(() => [...ideas].sort((a, b) => priorityOf(b) - priorityOf(a)), [ideas]);
  const started = stats.experiments > 0 || runs.length > 0 || stats.inWork > 0;

  const lastRun = runs[0];
  const refById = useMemo(() => new Map(references.map((r) => [r.id, r])), [references]);

  return (
    <div className="scroll-pane h-full overflow-y-auto">
      <div className="flex flex-col gap-3 p-4">
        <section className="border">
          <div className="flex flex-wrap items-start gap-x-6 gap-y-3 border-b px-3 py-3">
            <div className="min-w-[280px] flex-1">
              <div className="label">проект</div>
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                onBlur={() => name.trim() && name !== project.name && onUpdate({ name: name.trim() })}
                className="mt-1 h-auto border-0 bg-transparent px-0 text-[22px] font-semibold tracking-[-0.01em] dark:bg-transparent"
                placeholder="Название проекта"
              />
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {PALETTE.map((c) => (
                  <button
                    key={c}
                    title="цвет проекта"
                    onClick={() => onUpdate({ color: c })}
                    className={"size-4 border cursor-pointer " + (project.color === c ? "outline outline-1 outline-foreground" : "")}
                    style={{ background: c }}
                  />
                ))}
                <span className="ml-2 font-mono text-[11px] text-muted-foreground">
                  создан {new Date(project.createdAt).toLocaleDateString("ru-RU")}
                </span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Button size="sm" onClick={onOpenWorkspace}>
                {started ? "Продолжить проект" : "Начать проект"}
              </Button>
              <Button size="sm" variant="outline" onClick={onAddIdea}>
                Новая идея
              </Button>
              <Button size="sm" variant="outline" onClick={onShowIdeas}>
                Идеи проекта
              </Button>
              <Button size="sm" variant="ghost" onClick={onShowDashboard}>
                Дашборд
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-2 border-b sm:grid-cols-3 lg:grid-cols-6">
            <Cell label="идей" value={ideas.length} hint={`в работе ${stats.inWork}`} />
            <Cell label="этапов пройдено" value={`${stats.steps.done}/${stats.steps.total}`} hint={`готовность ${stats.pct}%`} />
            <Cell label="прогонов" value={stats.experiments} hint={runs.length ? `в папке ${runs.length}` : "записей журнала"} />
            <Cell label="источников" value={stats.refs.size} hint={`в библиотеке ${references.length}`} />
            <Cell label="доведено" value={stats.done} hint="подано и опубликовано" />
            <Cell
              label="ближайший срок"
              value={stats.nextDeadline?.deadline ?? "нет"}
              hint={stats.nextDeadline ? stats.nextDeadline.title.slice(0, 28) : "дедлайны не заданы"}
              last
            />
          </div>

          <div className="grid gap-4 p-3 lg:grid-cols-[1.4fr_1fr]">
            <div>
              <div className="label">описание проекта</div>
              <Textarea
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                onBlur={() => desc !== project.description && onUpdate({ description: desc })}
                placeholder="Что за проект, какая цель, на какой вопрос отвечаем, чем ограничены по данным и срокам."
                className="mt-1 min-h-[92px] text-[12px] leading-relaxed"
              />
              {stats.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span className="label">метки идей</span>
                  {stats.tags.map((t) => (
                    <span key={t} className="border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="border">
              <div className="label border-b px-2 py-1.5">рабочее место</div>
              <div className="flex flex-col gap-2 p-2 text-[12px]">
                <div>
                  <div className="label">папка кода</div>
                  <div className="truncate font-mono text-[11px]" title={paths?.code}>
                    {paths?.code ?? "окно Electron не подключено"}
                  </div>
                </div>
                <div>
                  <div className="label">папка прогонов</div>
                  <div className="truncate font-mono text-[11px]" title={paths?.runs}>
                    {paths?.runs ?? "окно Electron не подключено"}
                  </div>
                </div>
                <div className="text-muted-foreground">
                  {lastRun
                    ? `последний прогон: ${lastRun.label}, файлов ${lastRun.files.length}`
                    : "прогонов пока нет, шаблоны скопируются при первом открытии"}
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  <Button size="sm" variant="outline" onClick={onOpenWorkspace}>
                    {started ? "Открыть рабочее место" : "Открыть и разложить шаблоны"}
                  </Button>
                  {paths && (
                    <>
                      <Button size="sm" variant="ghost" onClick={() => void fly?.openPath(paths.runs)}>
                        Показать прогоны
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setFolders(true)}>
                        Сменить папки
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        {ideas.length === 0 ? (
          <section className="border p-4">
            <div className="label">проект пуст</div>
            <p className="mt-1 max-w-2xl text-[12px] leading-relaxed text-muted-foreground">
              Порядок такой: заводите идею, у неё появляется вопрос, метод и чеклист от чтения литературы до подачи. Дальше
              кнопка «Начать проект» открывает рабочее место: слева файлы кода, в центре прогоны и результаты, справа помощник
              для кода и литературы.
            </p>
            <div className="mt-3 flex gap-2">
              <Button size="sm" onClick={onAddIdea}>
                Новая идея
              </Button>
              <Button size="sm" variant="outline" onClick={onOpenWorkspace}>
                Сразу в рабочее место
              </Button>
            </div>
          </section>
        ) : (
          <div className="grid gap-3 xl:grid-cols-[1.3fr_1fr]">
            <section className="border">
              <div className="flex items-center justify-between border-b px-3 py-2">
                <div>
                  <div className="label">идеи проекта по приоритету</div>
                  <p className="mt-1 text-[11px] text-muted-foreground">приоритет считается по оценкам: влияние, новизна, скорость против трудоёмкости и риска</p>
                </div>
                <span className="font-mono text-[11px] text-muted-foreground">{ideas.length}</span>
              </div>
              <div className="divide-y">
                {ranked.slice(0, 8).map((i) => {
                  const p = checklistProgress(i);
                  return (
                    <button key={i.id} onClick={() => onOpenIdea(i.id)} className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-accent cursor-pointer">
                      <span className="size-2 shrink-0" style={{ background: STATUS_COLORS[i.status] }} />
                      <span className="min-w-0 flex-1 truncate text-[12.5px]">{i.title}</span>
                      <span className="label w-[86px] shrink-0">{STATUS_LABELS[i.status]}</span>
                      <span className="hidden w-[92px] shrink-0 items-center gap-1.5 sm:flex">
                        <span className="h-1 flex-1 bg-muted">
                          <span className="block h-1" style={{ width: `${p.pct}%`, background: "var(--chart-2)" }} />
                        </span>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          {p.done}/{p.total}
                        </span>
                      </span>
                      <span className="w-[52px] shrink-0 text-right font-mono text-[11px] text-muted-foreground">{priorityOf(i)}</span>
                      <DeadlineBadge deadline={i.deadline} />
                    </button>
                  );
                })}
              </div>
            </section>

            <div className="flex flex-col gap-3">
              <section className="border">
                <div className="label border-b px-3 py-2">состояние по статусам</div>
                <div className="divide-y">
                  {columns.map((c) => (
                    <div key={c.status} className="flex items-center gap-3 px-3 py-1.5">
                      <span className="size-2" style={{ background: STATUS_COLORS[c.status] }} />
                      <span className="flex-1 text-[12px]">{STATUS_LABELS[c.status]}</span>
                      <span className="h-1 w-[110px] bg-muted">
                        <span className="block h-1" style={{ width: `${(c.items.length / ideas.length) * 100}%`, background: STATUS_COLORS[c.status] }} />
                      </span>
                      <span className="w-6 text-right font-mono text-[11px]">{c.items.length}</span>
                    </div>
                  ))}
                </div>
              </section>

              <section className="border">
                <div className="label border-b px-3 py-2">последние записи журнала</div>
                {journal.length === 0 ? (
                  <p className="px-3 py-3 text-[11.5px] text-muted-foreground">
                    Журнал пуст. Запись добавляется из рабочего места кнопкой «в журнал идеи» либо вручную на вкладке идеи.
                  </p>
                ) : (
                  <div className="divide-y">
                    {journal.map(({ idea, e }) => (
                      <div key={e.id} className="px-3 py-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[10px] text-muted-foreground">{e.date}</span>
                          <span className="min-w-0 flex-1 truncate text-[12px]">{e.title || "прогон без названия"}</span>
                          <span className="label">{OUTCOME_LABELS[e.outcome]}</span>
                        </div>
                        <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                          {e.result ? `${e.result} · ` : ""}
                          <button className="underline hover:text-foreground cursor-pointer" onClick={() => onOpenIdea(idea.id)}>
                            {idea.title}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>
            </div>
          </div>
        )}

        {stats.refs.size > 0 && (
          <section className="border">
            <div className="label border-b px-3 py-2">чем опирается проект</div>
            <div className="divide-y">
              {stats.refIds
                .map((id) => refById.get(id))
                .filter((r): r is Reference => !!r)
                .slice(0, 6)
                .map((r) => (
                  <div key={r.id} className="flex items-center gap-3 px-3 py-1.5 text-[12px]">
                    <span className="w-10 shrink-0 font-mono text-[11px] text-muted-foreground">{r.year ?? "—"}</span>
                    <span className="min-w-0 flex-1 truncate">{r.title || r.authors}</span>
                    <span className="hidden max-w-[220px] truncate text-[11px] text-muted-foreground sm:block">{r.venue}</span>
                  </div>
                ))}
            </div>
          </section>
        )}
      </div>

      <Dialog open={folders} onOpenChange={setFolders}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Папки проекта</DialogTitle>
            <DialogDescription className="text-xs">
              Код проекта и прогоны можно держать в любом месте диска, например на большом диске или в папке с данным
              коннектома. Выбор запоминается для этого проекта.
            </DialogDescription>
          </DialogHeader>
          {paths && (
            <div className="flex flex-col gap-3">
              {(
                [
                  ["код", "code"],
                  ["прогоны", "runs"],
                ] as const
              ).map(([title, kind]) => (
                <div key={kind} className="border">
                  <div className="label border-b px-2 py-1.5">{title}</div>
                  <div className="flex items-center gap-2 p-2">
                    <span className="min-w-0 flex-1 truncate font-mono text-[11px]" title={paths[kind]}>
                      {paths[kind]}
                    </span>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        const next = await fly?.chooseProjectFolder(project.id, kind, `Папка: ${title}`);
                        if (next) {
                          setPaths(next);
                          setRuns(await (fly?.listRuns(project.id) ?? Promise.resolve([])));
                        }
                      }}
                    >
                      Выбрать…
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={async () => {
                        const next = await fly?.resetProjectFolder(project.id, kind);
                        if (next) setPaths(next);
                      }}
                    >
                      по умолчанию
                    </Button>
                  </div>
                </div>
              ))}
              <p className="text-[11px] text-muted-foreground">
                По умолчанию: <span className="font-mono">{paths.defaults.code}</span> и{" "}
                <span className="font-mono">{paths.defaults.runs}</span> внутри папки приложения.
              </p>
            </div>
          )}
          <DialogFooter>
            <Button size="sm" onClick={() => setFolders(false)}>
              Готово
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Cell({ label, value, hint, last }: { label: string; value: number | string; hint?: string; last?: boolean }) {
  return (
    <div className={"px-3 py-3" + (last ? "" : " border-r")}>
      <div className="label">{label}</div>
      <div className="mt-1 truncate font-mono text-[20px] leading-none" title={String(value)}>
        {value}
      </div>
      {hint && <div className="mt-1 truncate text-[10.5px] text-muted-foreground">{hint}</div>}
    </div>
  );
}
