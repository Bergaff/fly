import type { LlmUsage } from "@/lib/bridge";

export function normalizeUsage(raw: unknown): LlmUsage | null {
  if (!raw || typeof raw !== "object") return null;
  const usage = raw as Record<string, unknown>;
  const pick = (...keys: string[]) => {
    for (const key of keys) {
      const value = usage[key];
      if (typeof value === "number" && Number.isFinite(value)) return Math.max(0, Math.floor(value));
    }
    return null;
  };
  const inputTokens = pick("prompt_tokens", "input_tokens");
  const outputTokens = pick("completion_tokens", "output_tokens");
  const totalTokens = pick("total_tokens") ?? (inputTokens !== null && outputTokens !== null ? inputTokens + outputTokens : null);
  return inputTokens === null && outputTokens === null && totalTokens === null ? null : { inputTokens, outputTokens, totalTokens };
}

