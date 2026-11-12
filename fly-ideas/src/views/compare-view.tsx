import type { Idea } from "@/data/types";
import { SCORE_LABELS, STATUS_LABELS, checklistProgress } from "@/data/types";
import { IdeaRadarChart } from "@/components/charts/idea-radar-chart";
import { Button } from "@/components/ui/button";

export function CompareView({ ideas, all, onRemove, onOpen }: { ideas: Idea[]; all: Idea[]; onRemove: (id: string) => void; onOpen: (id: string) => void }) {
  const rows: { label: string; value: (i: Idea) => React.ReactNode }[] = [
    { label: "Статус", value: (i) => STATUS_LABELS[i.status] },
    { label: "Проект", value: (i) => i.projectId.replace("p-", "") },
    { label: "Вопрос", value: (i) => <span className="text-muted-foreground">{i.question || "не сформулирован"}</span> },
    { label: "Сроки", value: (i) => i.timeline || "не заданы" },
    { label: "Дедлайн", value: (i) => i.deadline || "нет" },
    ...(Object.keys(SCORE_LABELS) as (keyof Idea["scores"])[]).map((k) => ({ label: SCORE_LABELS[k], value: (i: Idea) => <span className="font-mono">{i.scores[k]}</span> })),
    { label: "Этапы", value: (i) => <span className="font-mono">{checklistProgress(i).done}/{checklistProgress(i).total}</span> },
    { label: "Источников", value: (i) => <span className="font-mono">{i.citations.length}</span> },
    { label: "Записей журнала", value: (i) => <span className="font-mono">{i.experiments.length}</span> },
    { label: "Куда", value: (i) => i.venues.join(", ") || "не выбрано" },
    { label: "Метки", value: (i) => i.tags.map((t) => `#${t}`).join(" ") || "нет" },
  ];

  return (
    <div className="h-full overflow-y-auto p-4"><div className="flex flex-col gap-4">
      <section className="border">
        <div className="label border-b px-3 py-2">Профиль оценок. Трудоёмкость и риск инвертированы: больше площади значит лучше</div>
        <div className="p-3">
          {ideas.length === 0 ? (
            <p className="py-12 text-center text-[12px] text-muted-foreground">Ничего не выбрано. Всего доступно идей: {all.length}.</p>
          ) : (
            <IdeaRadarChart ideas={ideas} />
          )}
        </div>
      </section>

      {ideas.length > 0 && (
        <section className="overflow-x-auto border">
          <table className="w-full border-collapse text-left align-top">
            <thead>
              <tr className="border-b">
                <th className="label w-[160px] px-3 py-2 font-normal">признак</th>
                {ideas.map((i) => (
                  <th key={i.id} className="min-w-[220px] border-l px-3 py-2 align-top font-normal">
                    <div className="flex items-start justify-between gap-2">
                      <button className="text-left text-[13px] leading-snug font-medium hover:underline cursor-pointer" onClick={() => onOpen(i.id)}>
                        {i.title}
                      </button>
                      <Button size="sm" variant="ghost" className="text-muted-foreground" onClick={() => onRemove(i.id)} title="Убрать из сравнения">
                        ×
                      </Button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.label} className="border-b align-top">
                  <th className="label px-3 py-2 text-left font-normal">{r.label}</th>
                  {ideas.map((i) => (
                    <td key={i.id} className="border-l px-3 py-2 text-[12px] leading-relaxed">
                      {r.value(i)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      </div>
    </div>
  );
}
