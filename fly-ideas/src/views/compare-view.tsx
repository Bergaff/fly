import type { Idea } from "@/data/types";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { IdeaRadarChart } from "@/components/charts/idea-radar-chart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

export function CompareView({ ideas, all, onRemove, onOpen }: { ideas: Idea[]; all: Idea[]; onRemove: (id: string) => void; onOpen: (id: string) => void }) {
  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-6">
      <Card>
        <CardHeader>
          <CardTitle>Сравнение идей</CardTitle>
          <CardDescription>
            Отметь до трёх идей галочкой на вкладке «Идеи». Трудоёмкость и риск инвертированы: чем больше площадь, тем лучше.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {ideas.length === 0 ? (
            <div className="py-16 text-center text-sm text-muted-foreground">Ничего не выбрано ({all.length} идей доступно).</div>
          ) : (
            <IdeaRadarChart ideas={ideas} />
          )}
        </CardContent>
      </Card>
      {ideas.length > 0 && (
        <div className="grid gap-4 md:grid-cols-3">
          {ideas.map((i) => (
            <Card key={i.id} className="gap-2 py-3">
              <CardHeader className="flex-row items-start justify-between gap-2">
                <CardTitle className="text-sm leading-snug cursor-pointer hover:underline" onClick={() => onOpen(i.id)}>{i.title}</CardTitle>
                <Button size="icon-sm" variant="ghost" onClick={() => onRemove(i.id)}><X /></Button>
              </CardHeader>
              <CardContent className="flex flex-col gap-2 text-xs text-muted-foreground">
                <p className="line-clamp-3">{i.question}</p>
                <div><span className="font-medium text-foreground">Сроки:</span> {i.timeline || "—"}</div>
                <div><span className="font-medium text-foreground">Куда:</span> {i.venues.join(", ") || "—"}</div>
                <div className="flex flex-wrap gap-1">{i.tags.map((t) => <Badge key={t} variant="secondary" className="font-normal">#{t}</Badge>)}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
