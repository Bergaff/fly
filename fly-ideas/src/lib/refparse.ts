import type { Reference } from "@/data/types";

/** Грубый разбор строки вида «Shiu PK, et al. (2024). Title. Nature 634. doi:10.1038/...» */
export function parseReferenceLine(line: string): Partial<Reference> {
  const out: Partial<Reference> = {};
  const clean = line.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, "").replace(/\*\*/g, "").trim();
  const doi = clean.match(/10\.\d{4,9}\/[^\s"'<>)\]]+/i);
  if (doi) out.doi = doi[0].replace(/[.,;)]+$/, "");
  const url = clean.match(/https?:\/\/\S+/);
  if (url && !doi) out.url = url[0].replace(/[.,;)]+$/, "");
  const year = clean.match(/\((\d{4})[a-z]?\)/) || clean.match(/\b(19|20)\d{2}\b/);
  if (year) out.year = Number(year[1] ?? year[0]);

  let rest = clean;
  const head = clean.match(/^(.*?)\s*\((\d{4})[a-z]?\)[.:]?\s*/);
  if (head) {
    out.authors = head[1].replace(/[.,;]$/, "").trim();
    rest = clean.slice(head[0].length);
  } else {
    out.authors = "";
  }
  rest = rest.replace(/10\.\d{4,9}\/\S+/i, "").replace(/https?:\/\/\S+/i, "").trim();
  const sentences = rest.split(/\.\s+/);
  if (sentences[0]) out.title = sentences[0].replace(/\.$/, "").trim();
  const venue = sentences.slice(1).join(". ").replace(/\.$/, "").trim();
  if (venue) out.venue = venue.slice(0, 160);
  if (!out.title && !out.doi && !out.url) return {};
  return out;
}

/** Все похожие на публикации строки из ответа модели */
export function parseReferencesFromText(text: string): Partial<Reference>[] {
  const out: Partial<Reference>[] = [];
  const seen = new Set<string>();
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (line.length < 25) continue;
    const hasDoi = /10\.\d{4,9}\//i.test(line);
    const hasYearInParens = /\((?:19|20)\d{2}[a-z]?\)/.test(line);
    if (!hasDoi && !hasYearInParens) continue;
    const ref = parseReferenceLine(line);
    const key = ref.doi || ref.title || "";
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(ref);
  }
  return out.slice(0, 12);
}
