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
  /** ссылка для кнопки «источник», если файл лежит не на GitHub */
  page?: string;
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

export interface ScriptInfo { name: string; doc: string; size: number; mtime: number }
export interface RunInfo { dir: string; path: string; label: string; summary: Record<string, unknown> | null; files: string[]; mtime: number }
export interface RunOutput { runId: string; stream: "stdout" | "stderr" | "exit"; text: string; code?: number }
export interface LlmMessage { role: "system" | "user" | "assistant"; content: string }

export type LlmProvider = "deepseek" | "perplexity" | "openai";

/** Рабочее место проекта: где лежит код и куда падают прогоны */
export interface ProjectPaths { projectId: string; code: string; runs: string; defaults: { code: string; runs: string } }

/** Права помощника на файлы и запуск */
export interface Permissions { createFiles: boolean; overwriteFiles: boolean; runScripts: boolean }

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

  projectPaths(projectId: string): Promise<ProjectPaths>;
  chooseProjectFolder(projectId: string, kind: "code" | "runs", title?: string): Promise<ProjectPaths | null>;
  resetProjectFolder(projectId: string, kind: "code" | "runs"): Promise<ProjectPaths>;
  getPermissions(): Promise<Permissions>;
  setPermissions(patch: Partial<Permissions>): Promise<Permissions>;

  checkEnv(): Promise<EnvInfo>;
  openPath(p: string): Promise<string>;
  openExternal(url: string): Promise<void>;
  listData(): Promise<DataItem[]>;
  download(item: DataItem, destDir?: string): Promise<{ path: string; size: number }>;
  cancelDownload(id: string): Promise<void>;
  onDownloadProgress(cb: (p: { id: string; got: number; total: number }) => void): () => void;

  listScripts(projectId: string): Promise<ScriptInfo[]>;
  readScript(projectId: string, name: string): Promise<string>;
  writeScript(projectId: string, name: string, content: string, opts?: { allowOverwrite?: boolean }): Promise<{ file: string; path: string; created: boolean }>;
  deleteScript(projectId: string, name: string): Promise<boolean>;
  runScript(projectId: string, name: string, args: string[]): Promise<{ runId: string; runDir: string }>;
  killRun(runId: string): Promise<void>;
  onRunOutput(cb: (p: RunOutput) => void): () => void;

  getSecret(k: string): Promise<string | null>;
  setSecret(k: string, v: string | null): Promise<boolean>;
  llmChat(req: { provider: LlmProvider; model?: string; messages: LlmMessage[]; temperature?: number }): Promise<{ content: string; usage?: unknown }>;

  listRuns(projectId: string): Promise<RunInfo[]>;
  readRun(dir: string): Promise<{ log: string; summary: Record<string, unknown> | null }>;
}

declare global {
  interface Window { fly?: FlyBridge }
}

export const fly: FlyBridge | null = typeof window !== "undefined" && window.fly ? window.fly : null;
export const isElectron = !!fly;

export const fmtBytes = (n: number | null | undefined) => {
  if (n == null) return "нет данных";
  if (n < 1024) return `${n} Б`;
  if (n < 1024 ** 2) return `${(n / 1024).toFixed(0)} КБ`;
  if (n < 1024 ** 3) return `${(n / 1024 ** 2).toFixed(1)} МБ`;
  return `${(n / 1024 ** 3).toFixed(2)} ГБ`;
};
