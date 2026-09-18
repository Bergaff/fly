import type { Idea } from "@/data/types";
import { STATUS_COLORS, checklistProgress, deadlineInfo } from "@/data/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EffortImpactChart } from "@/components/charts/effort-impact-chart";
import { StatusFunnel } from "@/components/charts/status-funnel";
import { DependencyGraph } from "@/components/charts/dependency-graph";
import { DeadlineBadge } from "@/components/deadline-badge";

export function DashboardView({ ideas, onOpen }: { ideas: Idea[]; onOpen: (id: string) => void }) {
  const avg = (k: keyof Idea["scores"]) => (ideas.length ? (ideas.reduce((a, i) => a + i.scores[k], 0) / ideas.length).toFixed(1) : "—");
  const inWork = ideas.filter((i) => ["exploring", "active", "drafting"].includes(i.status)).length;
  const quick = ideas.filter((i) => i.scores.effort <= 5 && i.scores.impact >= 6).length;
  const withDeadline = ideas
    .filter((i) => deadlineInfo(i.deadline))
    .sort((a, b) => (a.deadline! < b.deadline! ? -1 : 1));
  const overdue = withDeadline.filter((i) => deadlineInfo(i.deadline)!.tone === "overdue").length;
  const totalSteps = ideas.reduce((a, i) => a + i.checklist.length, 0);
  const doneSteps = ideas.reduce((a, i) => a + i.checklist.filter((c) => c.done).length, 0);

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Всего идей" value={ideas.length} />
        <Stat label="В работе" value={inWork} hint="изучаю / в работе / пишу" />
        <Stat label="Быстрые победы" value={quick} hint="трудоёмкость ≤5, влияние ≥6" />
        <Stat label="Этапов закрыто" value={`${doneSteps}/${totalSteps}`} hint={`среднее влияние ${avg("impact")}, трудоёмкость ${avg("effort")}`} />
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Карта приоритетов</CardTitle>
            <CardDescription>Трудоёмкость × влияние; размер точки — новизна; цвет — статус. Зелёная зона — «мало усилий, много пользы». Клик по точке открывает идею.</CardDescription>
          </CardHeader>
          <CardContent><EffortImpactChart ideas={ideas} onSelect={onOpen} /></CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Воронка статусов</CardTitle>
            <CardDescription>От бэклога до публикации</CardDescription>
          </CardHeader>
          <CardContent><StatusFunnel ideas={ideas} /></CardContent>
        </Card>
      </div>
      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Дерево идей</CardTitle>
            <CardDescription>Стрелка «A → B» значит «B растёт из A». Слева — самостоятельные идеи, правее — те, что на них опираются. Полоска — прогресс чеклиста.</CardDescription>
          </CardHeader>
          <CardContent><DependencyGraph ideas={ideas} onSelect={onOpen} /></CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Дедлайны</CardTitle>
            <CardDescription>{withDeadline.length ? `${withDeadline.length} с датой${overdue ? `, ${overdue} просрочено` : ""}` : "Дедлайны задаются в диалоге идеи"}</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-1.5">
            {withDeadline.length === 0 && <div className="py-6 text-center text-sm text-muted-foreground">Пусто</div>}
            {withDeadline.map((i) => {
              const p = checklistProgress(i);
              return (
                <button key={i.id} onClick={() => onOpen(i.id)} className="flex items-center gap-2 rounded-md border px-2.5 py-2 text-left text-sm hover:bg-accent cursor-pointer">
                  <span className="size-2 shrink-0 rounded-full" style={{ background: STATUS_COLORS[i.status] }} />
                  <span className="min-w-0 flex-1 truncate">{i.title}</span>
                  <span className="font-mono text-[10px] text-muted-foreground">{p.pct}%</span>
                  <DeadlineBadge deadline={i.deadline} />
                </button>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Stat({ label, value, hint }: { label: string; value: number | string; hint?: string }) {
  return (
    <Card className="gap-1 py-4">
      <CardHeader><CardDescription>{label}</CardDescription></CardHeader>
      <CardContent>
        <div className="text-3xl font-semibold tabular-nums">{value}</div>
        {hint && <div className="mt-1 text-xs text-muted-foreground">{hint}</div>}
      </CardContent>
    </Card>
  );
}
