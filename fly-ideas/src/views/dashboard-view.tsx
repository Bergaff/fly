import type { Idea } from "@/data/types";
import { OUTCOME_COLORS, OUTCOME_LABELS, checklistProgress, deadlineInfo } from "@/data/types";
import { EffortImpactChart } from "@/components/charts/effort-impact-chart";
import { StatusFunnel } from "@/components/charts/status-funnel";
import { DependencyGraph } from "@/components/charts/dependency-graph";
import { ActivityHeatmap } from "@/components/charts/activity-heatmap";
import { ReadinessMeters } from "@/components/charts/readiness-meters";
import { Sparkline } from "@/components/charts/sparkline";
import { DeadlineBadge } from "@/components/deadline-badge";
import { activityPerWeek } from "@/lib/activity";

export function DashboardView({ ideas, onOpen }: { ideas: Idea[]; onOpen: (id: string) => void }) {
  const avg = (k: keyof Idea["scores"]) => (ideas.length ? (ideas.reduce((a, i) => a + i.scores[k], 0) / ideas.length).toFixed(1) : "0");
  const inWork = ideas.filter((i) => ["exploring", "active", "drafting"].includes(i.status)).length;
  const quick = ideas.filter((i) => i.scores.effort <= 5 && i.scores.impact >= 6).length;
  const withDeadline = ideas.filter((i) => deadlineInfo(i.deadline)).sort((a, b) => (a.deadline! < b.deadline! ? -1 : 1));
  const overdue = withDeadline.filter((i) => deadlineInfo(i.deadline)!.tone === "overdue").length;
  const totalSteps = ideas.reduce((a, i) => a + i.checklist.length, 0);
  const doneSteps = ideas.reduce((a, i) => a + i.checklist.filter((c) => c.done).length, 0);
  const week = activityPerWeek(ideas, 12);
  const recent = ideas
    .flatMap((i) => i.experiments.map((e) => ({ e, i })))
    .sort((a, b) => b.e.date.localeCompare(a.e.date) || b.e.createdAt.localeCompare(a.e.createdAt))
    .slice(0, 8);

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4">
      <section className="grid grid-cols-2 border xl:grid-cols-4">
        <Stat label="всего идей" value={ideas.length} hint={`влияние в среднем ${avg("impact")}`} />
        <Stat label="в работе" value={inWork} hint="изучаю, в работе, пишу" />
        <Stat label="быстрые победы" value={quick} hint="трудоёмкость до 5, влияние от 6" />
        <Stat label="этапов закрыто" value={`${doneSteps}/${totalSteps}`} hint={`трудоёмкость в среднем ${avg("effort")}`} last />
      </section>

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <Panel title="карта приоритетов" note="Трудоёмкость по горизонтали, влияние по вертикали, размер точки задаёт новизну, цвет означает статус. Штриховка отмечает зону быстрых побед. Нажатие на точку открывает идею.">
          <EffortImpactChart ideas={ideas} onSelect={onOpen} />
        </Panel>
        <Panel title="воронка статусов" note="Путь от бэклога до публикации: ширина ступени пропорциональна числу идей, доля считается от всего списка.">
          <StatusFunnel ideas={ideas} />
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <Panel title="дерево идей" note="Связь «B растёт из A»: слева самостоятельные работы, правее те, что на них опираются. Внутри узла доля закрытых этапов.">
          <DependencyGraph ideas={ideas} onSelect={onOpen} />
        </Panel>
        <Panel title="готовность к подаче" note="Верхние идеи по доле закрытых этапов: десять делений шкалы закрываются по мере продвижения.">
          <ReadinessMeters ideas={ideas} onSelect={onOpen} />
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <Panel
          title="активность по дням"
          note="Записи журнала и закрытые этапы за последние четырнадцать недель. Квадрат это день, насыщенность означает число действий."
          aside={<Sparkline values={week} label="Действия по неделям" />}
        >
          <ActivityHeatmap ideas={ideas} />
        </Panel>
        <Panel title="сроки" note={withDeadline.length ? `${withDeadline.length} с датой, просрочено: ${overdue}` : "Дедлайны задаются в диалоге идеи."}>
          {withDeadline.length === 0 ? (
            <p className="py-6 text-center text-[12px] text-muted-foreground">Пока ни одного срока.</p>
          ) : (
            <div className="flex flex-col">
              {withDeadline.map((i) => {
                const prog = checklistProgress(i);
                return (
                  <button key={i.id} onClick={() => onOpen(i.id)} className="flex items-center gap-3 border-b py-2 text-left last:border-b-0 hover:bg-accent cursor-pointer">
                    <span className="min-w-0 flex-1 truncate text-[12px]">{i.title}</span>
                    <span className="font-mono text-[10px] text-muted-foreground">{prog.pct}%</span>
                    <DeadlineBadge deadline={i.deadline} />
                  </button>
                );
              })}
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="последние записи журнала"
        note={`Всего записей: ${ideas.reduce((a, i) => a + i.experiments.length, 0)}. Нажатие открывает идею.`}
      >
        {recent.length === 0 ? (
          <p className="py-6 text-center text-[12px] text-muted-foreground">Журнал пуст: записи появляются из вкладки «Мозг» или вручную в идее.</p>
        ) : (
          <div className="grid md:grid-cols-2">
            {recent.map(({ e, i }) => (
              <button key={e.id} onClick={() => onOpen(i.id)} className="flex items-baseline gap-3 border-b px-1 py-2 text-left hover:bg-accent cursor-pointer md:odd:border-r md:odd:pr-3">
                <span className="mt-1 size-2 shrink-0" style={{ background: OUTCOME_COLORS[e.outcome] }} title={OUTCOME_LABELS[e.outcome]} />
                <span className="shrink-0 font-mono text-[10px] text-muted-foreground">{new Date(`${e.date}T00:00:00`).toLocaleDateString("ru-RU")}</span>
                <span className="min-w-0 flex-1 truncate text-[12px]">{e.title || <span className="text-muted-foreground italic">без названия</span>}</span>
                <span className="hidden max-w-[40%] truncate font-mono text-[10px] text-muted-foreground lg:block">{i.title}</span>
              </button>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function Stat({ label, value, hint, last }: { label: string; value: number | string; hint?: string; last?: boolean }) {
  return (
    <div className={"px-3 py-3" + (last ? "" : " border-r")}>
      <div className="label">{label}</div>
      <div className="mt-1 font-mono text-[26px] leading-none">{value}</div>
      {hint && <div className="mt-1 text-[11px] text-muted-foreground">{hint}</div>}
    </div>
  );
}

function Panel({ title, note, aside, children }: { title: string; note: string; aside?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="border">
      <div className="flex items-start justify-between gap-4 border-b px-3 py-2">
        <div>
          <div className="label">{title}</div>
          <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">{note}</p>
        </div>
        {aside && <div className="shrink-0 pt-0.5">{aside}</div>}
      </div>
      <div className="p-3">{children}</div>
    </section>
  );
}
