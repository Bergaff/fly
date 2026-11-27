/** Распознаём только полные ограждённые блоки с именем файла, без путей. */
export function extractAssistantFiles(text: string): { name: string; content: string }[] {
  const files: { name: string; content: string }[] = [];
  const duplicates = new Set<string>();
  const seen = new Set<string>();
  const blocks = /```([^\r\n`]*)\r?\n([\s\S]*?)```/g;
  for (const match of text.matchAll(blocks)) {
    const language = match[1].trim().toLowerCase();
    if (language && language !== "python" && language !== "py") continue;
    const body = match[2].replace(/\r\n/g, "\n");
    const firstLine = body.match(/^\s*#\s*file:\s*([^\s]+)\s*(?:\n|$)/i);
    const name = firstLine?.[1];
    if (!name || !/^[A-Za-z0-9_][A-Za-z0-9_.-]*\.py$/.test(name) || name.includes("..")) continue;
    if (seen.has(name.toLowerCase())) duplicates.add(name.toLowerCase());
    seen.add(name.toLowerCase());
    files.push({ name, content: body });
  }
  return files.filter((file) => !duplicates.has(file.name.toLowerCase()));
}

/** Ручное сохранение: пользователь сам выделяет код, начало должно содержать имя файла. */
export function extractSelectedAssistantFile(text: string): { name: string; content: string } | null {
  const content = text.replace(/\r\n/g, "\n").trim();
  const firstLine = content.match(/^#\s*file:[ \t]*([^\s]+)[ \t]*\n/i);
  const name = firstLine?.[1];
  if (!firstLine || !name || !/^[A-Za-z0-9_][A-Za-z0-9_.-]*\.py$/.test(name) || name.includes("..")) return null;
  if (!content.slice(firstLine[0].length).trim()) return null;
  return { name, content: `${content}\n` };
}

/** В режиме кода убираем только пояснения рядом с распознанными файлами.
 * Если файлов нет, оставляем ответ, например уточняющий вопрос. */
export function formatAssistantResponse(text: string, mode: "code" | "explain"): string {
  const files = extractAssistantFiles(text);
  return mode === "code" && files.length
    ? files.map((file) => `\`\`\`python\n${file.content.trimEnd()}\n\`\`\``).join("\n\n")
    : text;
}
