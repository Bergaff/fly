import { RESEARCH_STAGES, type Idea } from "@/data/types";

export function canRequestSuggestions(enabled: boolean, busy: boolean, hasIdea: boolean, hasKey: boolean): boolean {
  return enabled && !busy && hasIdea && hasKey;
}

const clip = (value: unknown, max = 1000) => typeof value === "string" ? value.slice(0, max) : "";

/** Передаём только выбранную идею. Открытый файл и история чата не передаются. */
export function suggestionContext(idea: Idea) {
  return {
    title: clip(idea.title, 300), question: clip(idea.question), method: clip(idea.method, 2000), validation: clip(idea.validation),
    progress: RESEARCH_STAGES.map(({ id, label }) => ({ stage: label, marked: idea.researchProgress?.[id]?.done === true, evidence: clip(idea.researchProgress?.[id]?.evidence, 500) })),
    recentExperiments: [...(idea.experiments ?? [])].sort((a, b) => String(b.date ?? "").localeCompare(String(a.date ?? "")) || String(b.createdAt ?? "").localeCompare(String(a.createdAt ?? ""))).slice(0, 2).map((entry) => ({ title: clip(entry.title, 300), params: clip(entry.params, 500), result: clip(entry.result, 500), conclusion: clip(entry.conclusion, 500), outcome: entry.outcome })),
  };
}

export function parseSuggestions(content: string): string[] {
  const text = content.trim().replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/, "");
  let parsed: unknown;
  try { parsed = JSON.parse(text); } catch { throw new Error("DeepSeek вернул предложения в неподходящем формате. Попробуйте ещё раз."); }
  if (!parsed || typeof parsed !== "object" || !Array.isArray((parsed as { suggestions?: unknown }).suggestions)) throw new Error("В ответе DeepSeek нет списка предложений.");
  const items = (parsed as { suggestions: unknown[] }).suggestions;
  if (items.length < 1 || items.length > 3 || items.some((item) => typeof item !== "string" || !item.trim() || item.length > 500)) throw new Error("Некорректный список предложений DeepSeek.");
  return [...new Set(items.map((item) => (item as string).trim()))];
}
