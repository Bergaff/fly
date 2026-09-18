import type { Idea } from "@/data/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EffortImpactChart } from "@/components/charts/effort-impact-chart";
import { StatusFunnel } from "@/components/charts/status-funnel";

export function DashboardView({ ideas, onOpen }: { ideas: Idea[]; onOpen: (id: string) => void }) {
  const avg = (k: keyof Idea["scores"]) => (ideas.length ? (ideas.reduce((a, i) => a + i.scores[k], 0) / ideas.length).toFixed(1) : "—");
  const inWork = ideas.filter((i) => ["exploring", "active", "drafting"].includes(i.status)).length;
  const quick = ideas.filter((i) => i.scores.effort <= 5 && i.scores.impact >= 6).length;

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Всего идей" value={ideas.length} />
        <Stat label="В работе" value={inWork} hint="изучаю / в работе / пишу" />
        <Stat label="Быстрые победы" value={quick} hint="трудоёмкость ≤5, влияние ≥6" />
        <Stat label="Среднее влияние" value={avg("impact")} hint={`средняя трудоёмкость ${avg("effort")}`} />
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
