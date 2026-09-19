import type { Idea, Project, Reference } from "@/data/types";
import { OUTCOME_LABELS, SCORE_LABELS, STATUS_LABELS, checklistProgress, formatReference, referenceLink } from "@/data/types";

/** Собирает черновик статьи по идее: вопрос, метод, валидация, прогоны, литература, что осталось. */
export function draftMarkdown(idea: Idea, project: Project | undefined, references: Reference[]): string {
  const byId = new Map(references.map((r) => [r.id, r]));
  const used = idea.citations.map((c) => ({ ref: byId.get(c.refId), why: c.why })).filter((x) => x.ref);
  const progress = checklistProgress(idea);
  const today = new Date().toISOString().slice(0, 10);
  const line = (s: string) => s.trim();

  const parts: string[] = [];
  parts.push(`# ${idea.title}`);
  parts.push("");
  parts.push(
    [
      `Проект: ${project?.name ?? "без проекта"}`,
      `Статус: ${STATUS_LABELS[idea.status]}`,
      `Готовность конвейера: ${progress.done} из ${progress.total}`,
      idea.deadline ? `Срок: ${idea.deadline}` : null,
      idea.timeline ? `Оценка сроков: ${idea.timeline}` : null,
      `Черновик собран: ${today}`,
    ]
      .filter(Boolean)
      .join(" · "),
  );
  parts.push("");
  if (idea.tags.length) parts.push(`Метки: ${idea.tags.join(", ")}`, "");

  const section = (title: string, body: string) => {
    if (!line(body)) return;
    parts.push(`## ${title}`, "", body.trim(), "");
  };

  section("Вопрос", idea.question);
  section("Метод", idea.method);
  section("Валидация", idea.validation);
  section("Заметки", idea.notes);

  if (idea.experiments.length) {
    parts.push("## Прогоны", "");
    parts.push("| Дата | Что запускал | Параметры | Результат | Вывод | Исход |");
    parts.push("| --- | --- | --- | --- | --- | --- |");
    for (const e of [...idea.experiments].sort((a, b) => a.date.localeCompare(b.date))) {
      const cell = (s: string) => s.replace(/\|/g, "\\|").replace(/\n+/g, " ").trim() || "—";
      parts.push(
        `| ${e.date} | ${cell(e.title)} | ${cell(e.params)} | ${cell(e.result)} | ${cell(e.conclusion)} | ${OUTCOME_LABELS[e.outcome]} |`,
      );
    }
    parts.push("");
  }

  parts.push("## Оценки", "");
  parts.push(
    (Object.keys(SCORE_LABELS) as (keyof typeof SCORE_LABELS)[])
      .map((k) => `${SCORE_LABELS[k]} ${idea.scores[k]}/10`)
      .join(" · "),
  );
  parts.push("");

  const open = idea.checklist.filter((c) => !c.done);
  if (open.length) {
    parts.push("## Что осталось", "");
    for (const c of open) parts.push(`- ${c.text}`);
    parts.push("");
  }

  if (used.length) {
    parts.push("## Литература", "");
    used.forEach((u, i) => {
      const link = u.ref ? referenceLink(u.ref) : null;
      parts.push(`${i + 1}. ${u.ref ? formatReference(u.ref) : ""}${link ? ` ${link}` : ""}`);
      if (u.why) parts.push(`   зачем: ${u.why}`);
    });
    parts.push("");
  }

  if (idea.links.length) {
    parts.push("## Ссылки", "");
    for (const l of idea.links) parts.push(`- ${l.label || l.url}: ${l.url}`);
    parts.push("");
  }

  if (idea.venues.length) parts.push("## Куда подавать", "", idea.venues.join(", "), "");

  parts.push("---", "", "_Черновик собран в Fly Ideas. Перед отправкой проверьте цифры, сиды и ссылки._");
  return parts.join("\n");
}

export function draftFileName(idea: Idea): string {
  const slug = idea.title
    .toLowerCase()
    .replace(/[^a-zа-я0-9]+/gi, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
  return `${slug || "chernovik"}-${new Date().toISOString().slice(0, 10)}.md`;
}
