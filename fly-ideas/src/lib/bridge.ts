/** Типизированный мост к Electron (preload.cjs). В браузере window.fly отсутствует. */

export interface DataItem {
  id: string;
  group: string;
  title: string;
  file: string;
  url: string;
  sizeMB: number;
  note: string;
  dest?: "data" | "scripts";
  path: string;
  size: number | null;
  present: boolean;
}

export interface EnvInfo {
  python: { cmd: string; version: string } | null;
  conda: string | null;
  packages: Record<string, string | null>;
  gpu: string | null;
}

export interface ScriptInfo { name: string; doc: string }
export interface RunInfo { dir: string; path: string; summary: Record<string, unknown> | null; files: string[] }
export interface RunOutput { runId: string; stream: "stdout" | "stderr" | "exit"; text: string; code?: number }
export interface LlmMessage { role: "system" | "user" | "assistant"; content: string }

export type DirKind = "data" | "scripts" | "runs" | "exports";
export interface Paths { workspace: string; data: string; scripts: string; runs: string; exports: string; defaults: Record<DirKind, string>; templates: string }
export interface ExternalSource { title: string; url: string; note: string }
export interface FileFilter { name: string; extensions: string[] }

export interface FlyBridge {
  isElectron: true;
  getPaths(): Promise<Paths>;
  chooseFolder(kind: DirKind, title?: string): Promise<string | null>;
  pickFolder(title?: string): Promise<string | null>;
  resetFolder(kind: DirKind): Promise<string>;
  saveFile(opts: { defaultName: string; content: string; filters?: FileFilter[]; kind?: DirKind }): Promise<string | null>;
  openFile(opts: { filters?: FileFilter[]; kind?: DirKind }): Promise<{ path: string; content: string } | null>;
  listExternal(): Promise<ExternalSource[]>;
  readRunFile(dir: string, name: string): Promise<{ kind: "image"; dataUrl: string } | { kind: "text"; text: string }>;
  exportRun(dir: string): Promise<string | null>;
  checkEnv(): Promise<EnvInfo>;
  openPath(p: string): Promise<string>;
  openExternal(url: string): Promise<void>;
  listData(): Promise<DataItem[]>;
  download(item: DataItem, destDir?: string): Promise<{ path: string; size: number }>;
  cancelDownload(id: string): Promise<void>;
  onDownloadProgress(cb: (p: { id: string; got: number; total: number }) => void): () => void;
  listScripts(): Promise<ScriptInfo[]>;
  readScript(name: string): Promise<string>;
  writeScript(name: string, content: string): Promise<void>;
  runScript(name: string, args: string[]): Promise<{ runId: string; runDir: string }>;
  killRun(runId: string): Promise<void>;
  onRunOutput(cb: (p: RunOutput) => void): () => void;
  getSecret(k: string): Promise<string | null>;
  setSecret(k: string, v: string | null): Promise<boolean>;
  llmChat(req: { provider: "deepseek" | "openai"; model?: string; messages: LlmMessage[]; temperature?: number }): Promise<{ content: string; usage?: unknown }>;
  listRuns(): Promise<RunInfo[]>;
  readRun(dir: string): Promise<{ log: string; summary: Record<string, unknown> | null }>;
}

declare global {
  interface Window { fly?: FlyBridge }
}

export const fly: FlyBridge | null = typeof window !== "undefined" && window.fly ? window.fly : null;
export const isElectron = !!fly;

export const fmtBytes = (n: number | null | undefined) => {
  if (n == null) return "—";
  if (n < 1024) return `${n} Б`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(0)} КБ`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} МБ`;
  return `${(n / 1024 ** 3).toFixed(2)} ГБ`;
};
