const { app, BrowserWindow, shell, ipcMain, dialog } = require("electron");
const path = require("node:path");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const { spawn } = require("node:child_process");
const https = require("node:https");
const http = require("node:http");

const isDev = !!process.env.VITE_DEV_SERVER_URL;

// ------------------------------------------------------------
// Пути: всё рабочее лежит рядом с программой в папке workspace/
//   workspace/data      — скачанные данные коннектома
//   workspace/scripts   — python-скрипты (шаблоны копируются при первом запуске)
//   workspace/runs      — результаты прогонов (по папке на запуск)
// ------------------------------------------------------------
const appRoot = isDev ? path.join(__dirname, "..") : path.dirname(process.execPath);
const WS = path.join(appRoot, "workspace");
const DEFAULT_DIRS = { data: path.join(WS, "data"), scripts: path.join(WS, "scripts"), runs: path.join(WS, "runs"), exports: app.getPath("documents") };
const TEMPLATES = isDev ? path.join(__dirname, "..", "experiments", "templates") : path.join(process.resourcesPath, "templates");
const SECRETS = path.join(app.getPath("userData"), "secrets.json");
const CONFIG = path.join(app.getPath("userData"), "config.json");

function readConfig() {
  try { return JSON.parse(fs.readFileSync(CONFIG, "utf8")); } catch { return {}; }
}
function writeConfig(c) {
  fs.mkdirSync(path.dirname(CONFIG), { recursive: true });
  fs.writeFileSync(CONFIG, JSON.stringify(c, null, 2));
}
/** Текущие папки: пользовательские из config.json поверх дефолтных */
function getDirs() {
  const c = readConfig().dirs || {};
  const d = { ...DEFAULT_DIRS };
  for (const k of Object.keys(DEFAULT_DIRS)) if (c[k] && typeof c[k] === "string") d[k] = c[k];
  return d;
}
const DIRS = new Proxy({}, { get: (_t, k) => getDirs()[k] });

function copyTemplates(scriptsDir) {
  if (!fs.existsSync(TEMPLATES)) return;
  for (const f of fs.readdirSync(TEMPLATES)) {
    const dst = path.join(scriptsDir, f);
    if (!fs.existsSync(dst)) fs.copyFileSync(path.join(TEMPLATES, f), dst);
  }
}
function ensureDirs() {
  const d = getDirs();
  for (const k of ["data", "scripts", "runs"]) fs.mkdirSync(d[k], { recursive: true });
  copyTemplates(d.scripts);
}

// ------------------------------------------------------------
// Права помощника на файлы: по умолчанию создавать можно, перезаписывать нельзя
// ------------------------------------------------------------
const DEFAULT_PERMS = { createFiles: true, overwriteFiles: false, runScripts: true };
function getPermissions() {
  return { ...DEFAULT_PERMS, ...(readConfig().permissions || {}) };
}
function setPermissions(patch) {
  const c = readConfig();
  c.permissions = { ...getPermissions(), ...patch };
  writeConfig(c);
  return c.permissions;
}

/** Имя проекта приводим к безопасному виду: оно становится именем папки */
function slug(projectId) {
  const s = String(projectId || "project").replace(/[^A-Za-z0-9._-]/g, "-").replace(/^-+|-+$/g, "");
  return s || "project";
}
/** Путь внутри родительской папки, не выше её */
function within(parent, target) {
  const rel = path.relative(parent, target);
  return !!rel && !rel.startsWith("..") && !path.isAbsolute(rel);
}

/** Рабочие папки проекта: код и прогоны. Можно переназначить через config.json. */
function projectPaths(projectId) {
  const id = slug(projectId);
  const cfg = readConfig().projectDirs || {};
  const over = cfg[id] || {};
  const defaults = { code: path.join(DIRS.scripts, id), runs: path.join(DIRS.runs, id) };
  const code = typeof over.code === "string" ? over.code : defaults.code;
  const runs = typeof over.runs === "string" ? over.runs : defaults.runs;
  fs.mkdirSync(code, { recursive: true });
  fs.mkdirSync(runs, { recursive: true });
  if (fs.readdirSync(code).length === 0) copyTemplates(code);
  return { projectId: id, code, runs, defaults };
}
function setProjectDir(projectId, kind, dir) {
  const id = slug(projectId);
  const c = readConfig();
  c.projectDirs = c.projectDirs || {};
  const cur = c.projectDirs[id] || {};
  if (dir) cur[kind] = dir;
  else delete cur[kind];
  c.projectDirs[id] = cur;
  writeConfig(c);
  return projectPaths(projectId);
}

// ------------------------------------------------------------
// Каталог данных мозга: что можно скачать одной кнопкой
// ------------------------------------------------------------
const DATA_CATALOG = [
  {
    id: "completeness-783",
    group: "Eon fly-brain (FlyWire v783)",
    title: "Список нейронов (Completeness v783)",
    file: "2025_Completeness_783.csv",
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/data/2025_Completeness_783.csv",
    sizeMB: 3.2,
    note: "ID нейронов и метаданные — нужен для любого запуска модели",
  },
  {
    id: "connectivity-783",
    group: "Eon fly-brain (FlyWire v783)",
    title: "Связность (Connectivity v783, parquet)",
    file: "2025_Connectivity_783.parquet",
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/data/2025_Connectivity_783.parquet",
    sizeMB: 97,
    note: "Пре/пост-синаптические индексы и веса — сам «мозг». Может лежать в Git LFS: если файл окажется ~130 байт, скачай вручную из репозитория",
  },
  {
    id: "sez-neurons",
    group: "Eon fly-brain (FlyWire v783)",
    title: "Подмножество SEZ-нейронов (для фигур)",
    file: "sez_neurons.pickle",
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/data/sez_neurons.pickle",
    sizeMB: 0.5,
    note: "Нужен для воспроизведения фигур статьи Shiu et al.",
  },
  {
    id: "paper-model",
    group: "Код модели (Shiu et al.)",
    title: "model.py — LIF-модель на Brian2",
    file: "paper_model.py",
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/code/paper-phil-drosophila/model.py",
    sizeMB: 0.02,
    note: "Ядро модели из статьи (create_model, run_exp); кладём рядом со скриптами как paper_model.py",
    dest: "scripts",
  },
  {
    id: "paper-utils",
    group: "Код модели (Shiu et al.)",
    title: "utils.py — анализ спайков",
    file: "paper_utils.py",
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/code/paper-phil-drosophila/utils.py",
    sizeMB: 0.01,
    note: "load_exps, get_rate — помощники из статьи",
    dest: "scripts",
  },
  {
    id: "paper-example",
    group: "Код модели (Shiu et al.)",
    title: "example.ipynb — учебный ноутбук",
    file: "paper_example.ipynb",
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/code/paper-phil-drosophila/example.ipynb",
    sizeMB: 0.1,
    note: "Активация, глушение, анализ частот — открывать в Jupyter/VS Code",
    dest: "scripts",
  },
  {
    id: "eon-env",
    group: "Код модели (Shiu et al.)",
    title: "environment.yml — conda-окружение Eon",
    file: "eon_environment.yml",
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/environment.yml",
    sizeMB: 0.01,
    note: "conda env create -f eon_environment.yml — полный набор с GPU-бэкендами",
    dest: "scripts",
  },
];

/** Внешние источники — открываются в браузере, скачиваются вручную */
const EXTERNAL_SOURCES = [
  { title: "MaleCNS v1.0: коннектом ЦНС самца (Janelia)", url: "https://male-cns.janelia.org/", note: "Мозг, оптические доли и брюшная нервная цепочка в одном препарате, 165 тыс. нейронов. Файлы feather, лицензия CC-BY 4.0" },
  { title: "neuPrint: male-cns:v1.0", url: "https://neuprint.janelia.org/?dataset=male-cns%3Av1.0", note: "Запросы по связности и аннотациям, нужен бесплатный аккаунт; доступ из Python через neuprint-python" },
  { title: "MaleCNS Cell Type Explorer", url: "https://reiserlab.github.io/celltype-explorer-drosophila-male-cns/", note: "Просмотр типов клеток и связности между типами без аккаунта" },
  { title: "Сравнение полов: dimorphism overview", url: "https://janelia-flyem.github.io/male-cns/build/dimorphism_overview/", note: "Прямое сравнение связности диморфных клеток самца и самки FlyWire" },
  { title: "Код анализа к статье про MaleCNS", url: "https://github.com/flyconnectome/2025malecns", note: "Скрипты и производные таблицы статьи о диморфизме" },
  { title: "FlyWire Codex — обзор нейронов и скачивание v783", url: "https://codex.flywire.ai/api/download", note: "Официальные выгрузки коннектома (нужен бесплатный аккаунт)" },
  { title: "Schlegel et al. 2024 — аннотации типов клеток", url: "https://www.nature.com/articles/s41586-024-07686-5#Sec46", note: "Supplementary Data: типы клеток для выбора контуров (MB, CX)" },
  { title: "philshiu/Drosophila_brain_model — оригинал статьи", url: "https://github.com/philshiu/Drosophila_brain_model", note: "Исходный репозиторий Shiu et al., данные v630" },
  { title: "eonsystemspbc/fly-brain — все бэкенды", url: "https://github.com/eonsystemspbc/fly-brain", note: "Brian2 / CUDA / PyTorch / NEST / GeNN, бенчмарки" },
];

const MALE_CNS_BASE = "https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome/";

// ------------------------------------------------------------
// MaleCNS v1.0: полный коннектом ЦНС самца (Janelia), лицензия CC-BY 4.0
// ------------------------------------------------------------
DATA_CATALOG.push(
  {
    id: "malecns-annotations",
    group: "MaleCNS v1.0, ЦНС самца (Janelia)",
    title: "Аннотации нейронов: классы, типы, стороны",
    file: "body-annotations-male-cns-v1.0-minconf-0.5.feather",
    url: MALE_CNS_BASE + "body-annotations-male-cns-v1.0-minconf-0.5.feather",
    page: "https://male-cns.janelia.org/download/",
    sizeMB: 13,
    note: "Около 12 тыс. типов клеток, включая полоспецифичные и диморфные. Читается pyarrow или pandas.",
    dest: "data",
  },
  {
    id: "malecns-neurotransmitters",
    group: "MaleCNS v1.0, ЦНС самца (Janelia)",
    title: "Предсказание нейромедиатора по нейрону",
    file: "body-neurotransmitters-male-cns-v1.0.feather",
    url: MALE_CNS_BASE + "body-neurotransmitters-male-cns-v1.0.feather",
    page: "https://male-cns.janelia.org/download/",
    sizeMB: 42,
    note: "Нужно для знаков синапсов при сборке LIF-модели на мужском коннектоме.",
    dest: "data",
  },
);

const activeDownloads = new Map();

function fetchFollow(url, redirects = 0) {
  return new Promise((resolve, reject) => {
    const mod = url.startsWith("https") ? https : http;
    const req = mod.get(url, { headers: { "User-Agent": "fly-ideas" } }, (res) => {
      if ([301, 302, 303, 307, 308].includes(res.statusCode) && res.headers.location && redirects < 8) {
        res.resume();
        return resolve(fetchFollow(new URL(res.headers.location, url).toString(), redirects + 1));
      }
      if (res.statusCode !== 200) {
        res.resume();
        return reject(new Error(`HTTP ${res.statusCode}`));
      }
      resolve({ res, req });
    });
    req.on("error", reject);
  });
}

async function download(win, item, destDirOverride) {
  const destDir = destDirOverride || (item.dest === "scripts" ? DIRS.scripts : DIRS.data);
  fs.mkdirSync(destDir, { recursive: true });
  const dest = path.join(destDir, item.file);
  const tmp = dest + ".part";
  const { res, req } = await fetchFollow(item.url);
  activeDownloads.set(item.id, req);
  const total = Number(res.headers["content-length"] || 0);
  let got = 0;
  const out = fs.createWriteStream(tmp);
  await new Promise((resolve, reject) => {
    res.on("data", (chunk) => {
      got += chunk.length;
      win.webContents.send("fly:downloadProgress", { id: item.id, got, total });
    });
    res.on("error", reject);
    out.on("error", reject);
    out.on("finish", resolve);
    res.pipe(out);
  });
  activeDownloads.delete(item.id);
  await fsp.rename(tmp, dest);
  const st = await fsp.stat(dest);
  return { path: dest, size: st.size };
}

// ------------------------------------------------------------
// Окружение: python / conda / brian2 / GPU
// ------------------------------------------------------------
function run(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    let out = "", err = "";
    let p;
    try {
      p = spawn(cmd, args, { shell: process.platform === "win32", ...opts });
    } catch (e) {
      return resolve({ ok: false, out: "", err: String(e) });
    }
    p.stdout?.on("data", (d) => (out += d));
    p.stderr?.on("data", (d) => (err += d));
    p.on("error", (e) => resolve({ ok: false, out, err: String(e) }));
    p.on("close", (code) => resolve({ ok: code === 0, out: out.trim(), err: err.trim(), code }));
  });
}

async function pickPython() {
  const cands = process.platform === "win32" ? ["python", "py -3", "python3"] : ["python3", "python"];
  for (const c of cands) {
    const [cmd, ...a] = c.split(" ");
    const r = await run(cmd, [...a, "--version"]);
    if (r.ok && /Python 3/.test(r.out + r.err)) return { cmd: c, version: (r.out + r.err).trim() };
  }
  return null;
}

async function checkEnv() {
  const py = await pickPython();
  const result = { python: py, conda: null, packages: {}, gpu: null };
  const conda = await run("conda", ["--version"]);
  if (conda.ok) result.conda = conda.out;
  if (py) {
    const [cmd, ...a] = py.cmd.split(" ");
    const probe = `
import json, importlib
mods = ["numpy","pandas","pyarrow","brian2","torch","matplotlib","scipy"]
out = {}
for m in mods:
    try:
        mod = importlib.import_module(m); out[m] = getattr(mod, "__version__", "ok")
    except Exception as e:
        out[m] = None
try:
    import torch; out["cuda"] = torch.cuda.is_available() and torch.cuda.get_device_name(0)
except Exception:
    out["cuda"] = None
print(json.dumps(out))
`;
    const r = await run(cmd, [...a, "-c", probe]);
    if (r.ok) {
      try {
        const j = JSON.parse(r.out.split("\n").pop());
        result.gpu = j.cuda || null;
        delete j.cuda;
        result.packages = j;
      } catch {}
    }
  }
  const nvsmi = await run("nvidia-smi", ["--query-gpu=name,memory.total", "--format=csv,noheader"]);
  if (nvsmi.ok && nvsmi.out) result.gpu = result.gpu || nvsmi.out;
  return result;
}

// ------------------------------------------------------------
// Запуск скриптов
// ------------------------------------------------------------
const runs = new Map();

async function runScript(win, projectId, name, args) {
  const py = await pickPython();
  if (!py) throw new Error("Python 3 не найден. Установи Miniconda или python.org (галочка «Add to PATH»).");
  if (!getPermissions().runScripts) throw new Error("Запуск скриптов выключен в правах рабочего места.");
  const ws = projectPaths(projectId);
  const file = path.join(ws.code, path.basename(name));
  if (!within(ws.code, file)) throw new Error("Скрипт вне папки проекта.");
  const [cmd, ...pre] = py.cmd.split(" ");
  const runId = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + "_" + path.basename(name).replace(/\.py$/, "");
  const runDir = path.join(ws.runs, runId);
  fs.mkdirSync(runDir, { recursive: true });
  const script = file;
  const env = { ...process.env, FLY_DATA: DIRS.data, FLY_RUN_DIR: runDir, FLY_SCRIPTS: ws.code, FLY_PROJECT: ws.projectId, PYTHONUNBUFFERED: "1", PYTHONIOENCODING: "utf-8" };
  const p = spawn(cmd, [...pre, script, ...(args || [])], { cwd: ws.code, env, shell: process.platform === "win32" });
  runs.set(runId, p);
  const log = fs.createWriteStream(path.join(runDir, "log.txt"));
  const send = (stream, text) => {
    log.write(text);
    win.webContents.send("fly:runOutput", { runId, stream, text });
  };
  p.stdout.on("data", (d) => send("stdout", d.toString()));
  p.stderr.on("data", (d) => send("stderr", d.toString()));
  p.on("close", (code) => {
    log.end();
    runs.delete(runId);
    win.webContents.send("fly:runOutput", { runId, stream: "exit", code, text: `\n[завершено, код ${code}]\n` });
  });
  return { runId, runDir };
}

// ------------------------------------------------------------
// Секреты и LLM
// ------------------------------------------------------------
function readSecrets() {
  try { return JSON.parse(fs.readFileSync(SECRETS, "utf8")); } catch { return {}; }
}
function writeSecrets(s) {
  fs.mkdirSync(path.dirname(SECRETS), { recursive: true });
  fs.writeFileSync(SECRETS, JSON.stringify(s, null, 2), { mode: 0o600 });
}

async function llmChat({ provider, model, messages, temperature }) {
  const secrets = readSecrets();
  const cfg = {
    deepseek: { url: "https://api.deepseek.com/chat/completions", key: secrets.deepseek, model: model || "deepseek-chat", keyName: "DeepSeek" },
    perplexity: { url: "https://api.perplexity.ai/chat/completions", key: secrets.perplexity, model: model || "sonar", keyName: "Perplexity" },
    openai: { url: "https://api.openai.com/v1/chat/completions", key: secrets.openai, model: model || "gpt-4o-mini", keyName: "OpenAI" },
  }[provider || "deepseek"];
  if (!cfg) throw new Error("Неизвестный провайдер");
  if (!cfg.key) throw new Error(`Ключ ${cfg.keyName} не задан: вкладка «Мозг», панель помощника.`);
  const res = await fetch(cfg.url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${cfg.key}` },
    body: JSON.stringify({ model: cfg.model, messages, temperature: temperature ?? 0.3, stream: false }),
  });
  if (!res.ok) throw new Error(`${provider}: HTTP ${res.status} ${await res.text()}`);
  const j = await res.json();
  return { content: j.choices?.[0]?.message?.content ?? "", usage: j.usage };
}

// ------------------------------------------------------------
// IPC
// ------------------------------------------------------------
function registerIpc(getWin) {
  ipcMain.handle("fly:getPaths", () => ({ workspace: WS, ...getDirs(), defaults: DEFAULT_DIRS, templates: TEMPLATES }));

  // --- выбор папок ---
  ipcMain.handle("fly:chooseFolder", async (_e, kind, title) => {
    const r = await dialog.showOpenDialog(getWin(), { title: title || "Выбери папку", defaultPath: getDirs()[kind] || app.getPath("documents"), properties: ["openDirectory", "createDirectory"] });
    if (r.canceled || !r.filePaths[0]) return null;
    const p = r.filePaths[0];
    if (kind && kind in DEFAULT_DIRS) {
      const c = readConfig();
      c.dirs = { ...(c.dirs || {}), [kind]: p };
      writeConfig(c);
      if (kind === "scripts") copyTemplates(p);
      else fs.mkdirSync(p, { recursive: true });
    }
    return p;
  });
  ipcMain.handle("fly:pickFolder", async (_e, title) => {
    const r = await dialog.showOpenDialog(getWin(), { title: title || "Выбери папку", properties: ["openDirectory", "createDirectory"] });
    return r.canceled ? null : r.filePaths[0];
  });
  ipcMain.handle("fly:resetFolder", (_e, kind) => {
    const c = readConfig();
    if (c.dirs) delete c.dirs[kind];
    writeConfig(c);
    ensureDirs();
    return getDirs()[kind];
  });

  // --- сохранить / открыть файл через системный диалог ---
  ipcMain.handle("fly:saveFile", async (_e, { defaultName, content, filters, kind }) => {
    const dir = getDirs()[kind || "exports"] || app.getPath("documents");
    const r = await dialog.showSaveDialog(getWin(), { defaultPath: path.join(dir, defaultName || "file.txt"), filters: filters || [{ name: "Все файлы", extensions: ["*"] }] });
    if (r.canceled || !r.filePath) return null;
    await fsp.writeFile(r.filePath, content, "utf8");
    const c = readConfig();
    c.dirs = { ...(c.dirs || {}), exports: path.dirname(r.filePath) };
    writeConfig(c);
    return r.filePath;
  });
  ipcMain.handle("fly:openFile", async (_e, { filters, kind }) => {
    const dir = getDirs()[kind || "exports"] || app.getPath("documents");
    const r = await dialog.showOpenDialog(getWin(), { defaultPath: dir, filters: filters || [{ name: "Все файлы", extensions: ["*"] }], properties: ["openFile"] });
    if (r.canceled || !r.filePaths[0]) return null;
    return { path: r.filePaths[0], content: await fsp.readFile(r.filePaths[0], "utf8") };
  });
  ipcMain.handle("fly:checkEnv", () => checkEnv());
  ipcMain.handle("fly:openPath", (_e, p) => shell.openPath(p));
  ipcMain.handle("fly:openExternal", (_e, url) => shell.openExternal(url));

  ipcMain.handle("fly:listData", async () => {
    return Promise.all(
      DATA_CATALOG.map(async (item) => {
        const dir = item.dest === "scripts" ? DIRS.scripts : DIRS.data;
        const p = path.join(dir, item.file);
        let size = null;
        try { size = (await fsp.stat(p)).size; } catch {}
        return { ...item, path: p, size, present: size !== null };
      }),
    );
  });
  ipcMain.handle("fly:download", async (_e, item, destDir) => download(getWin(), item, destDir));
  ipcMain.handle("fly:listExternal", () => EXTERNAL_SOURCES);
  ipcMain.handle("fly:cancelDownload", (_e, id) => { activeDownloads.get(id)?.destroy(); activeDownloads.delete(id); });

  // --- рабочее место проекта: папки кода и прогонов ---
  ipcMain.handle("fly:projectPaths", (_e, projectId) => projectPaths(projectId));
  ipcMain.handle("fly:chooseProjectFolder", async (_e, projectId, kind, title) => {
    const r = await dialog.showOpenDialog(getWin(), {
      title: title || "Выбери папку проекта",
      defaultPath: projectPaths(projectId)[kind === "runs" ? "runs" : "code"],
      properties: ["openDirectory", "createDirectory"],
    });
    if (r.canceled || !r.filePaths[0]) return null;
    return setProjectDir(projectId, kind === "runs" ? "runs" : "code", r.filePaths[0]);
  });
  ipcMain.handle("fly:resetProjectFolder", (_e, projectId, kind) => setProjectDir(projectId, kind === "runs" ? "runs" : "code", null));
  ipcMain.handle("fly:getPermissions", () => getPermissions());
  ipcMain.handle("fly:setPermissions", (_e, patch) => setPermissions(patch || {}));

  ipcMain.handle("fly:listScripts", async (_e, projectId) => {
    const ws = projectPaths(projectId);
    const files = (await fsp.readdir(ws.code)).filter((f) => f.endsWith(".py"));
    return Promise.all(files.map(async (f) => {
      const full = path.join(ws.code, f);
      const txt = await fsp.readFile(full, "utf8");
      const m = txt.match(/^"""\s*\n?([\s\S]*?)"""/);
      const st = await fsp.stat(full);
      return { name: f, doc: m ? m[1].trim().split("\n")[0] : "", size: st.size, mtime: st.mtimeMs };
    }));
  });
  ipcMain.handle("fly:readScript", (_e, projectId, name) => {
    const ws = projectPaths(projectId);
    const full = path.join(ws.code, path.basename(name));
    if (!within(ws.code, full)) throw new Error("Файл вне папки проекта.");
    return fsp.readFile(full, "utf8");
  });
  ipcMain.handle("fly:writeScript", async (_e, projectId, name, content, opts) => {
    const ws = projectPaths(projectId);
    const perms = getPermissions();
    const base = path.basename(name).replace(/[^\w.\-]+/g, "_");
    const file = path.join(ws.code, base.endsWith(".py") ? base : base + ".py");
    if (!within(ws.code, file)) throw new Error("Файл вне папки проекта.");
    const exists = fs.existsSync(file);
    if (!exists && !perms.createFiles) throw new Error("Создание файлов выключено: включи галочку «помощник создаёт файлы».");
    if (exists && !perms.overwriteFiles && !(opts && opts.allowOverwrite)) {
      throw new Error(`Файл ${path.basename(file)} уже есть. Включи «перезапись» или сохрани под другим именем.`);
    }
    await fsp.writeFile(file, content, "utf8");
    return { file: path.basename(file), path: file, created: !exists };
  });
  ipcMain.handle("fly:deleteScript", async (_e, projectId, name) => {
    const ws = projectPaths(projectId);
    const full = path.join(ws.code, path.basename(name));
    if (!within(ws.code, full)) throw new Error("Файл вне папки проекта.");
    await fsp.rm(full, { force: true });
    return true;
  });
  ipcMain.handle("fly:runScript", (_e, projectId, name, args) => runScript(getWin(), projectId, path.basename(name), args));
  ipcMain.handle("fly:killRun", (_e, runId) => { runs.get(runId)?.kill(); });

  ipcMain.handle("fly:getSecret", (_e, k) => { const s = readSecrets(); return s[k] ? `${s[k].slice(0, 6)}…${s[k].slice(-4)}` : null; });
  ipcMain.handle("fly:setSecret", (_e, k, v) => { const s = readSecrets(); if (v) s[k] = v; else delete s[k]; writeSecrets(s); return true; });
  ipcMain.handle("fly:llmChat", (_e, req) => llmChat(req));

  ipcMain.handle("fly:listRuns", async (_e, projectId) => {
    const ws = projectPaths(projectId);
    const entries = await fsp.readdir(ws.runs, { withFileTypes: true }).catch(() => []);
    const dirs = entries.filter((d) => d.isDirectory()).map((d) => d.name).sort().reverse();
    return Promise.all(dirs.slice(0, 50).map(async (d) => {
      const full = path.join(ws.runs, d);
      let summary = null;
      try { summary = JSON.parse(await fsp.readFile(path.join(full, "summary.json"), "utf8")); } catch {}
      const files = await fsp.readdir(full);
      let mtime = 0;
      try { mtime = (await fsp.stat(full)).mtimeMs; } catch {}
      return { dir: full, path: full, label: d, summary, files, mtime };
    }));
  });
  ipcMain.handle("fly:readRunFile", async (_e, dir, name) => {
    const p = path.join(dir, path.basename(name));
    if (!within(DIRS.runs, p)) throw new Error("Файл вне папки прогонов.");
    const ext = path.extname(name).toLowerCase();
    if ([".png", ".jpg", ".jpeg", ".svg", ".gif"].includes(ext)) {
      const mime = ext === ".svg" ? "image/svg+xml" : ext === ".png" ? "image/png" : ext === ".gif" ? "image/gif" : "image/jpeg";
      return { kind: "image", dataUrl: `data:${mime};base64,${(await fsp.readFile(p)).toString("base64")}` };
    }
    const st = await fsp.stat(p);
    if (st.size > 400_000) return { kind: "text", text: `(файл ${(st.size / 1e6).toFixed(1)} МБ — открой в папке)` };
    return { kind: "text", text: await fsp.readFile(p, "utf8") };
  });
  ipcMain.handle("fly:exportRun", async (_e, dir) => {
    const src = dir;
    if (!within(DIRS.runs, src)) throw new Error("Папка вне каталога прогонов.");
    const dest = await dialog.showOpenDialog(getWin(), { title: "Куда скопировать прогон", properties: ["openDirectory", "createDirectory"] });
    if (dest.canceled || !dest.filePaths[0]) return null;
    const target = path.join(dest.filePaths[0], path.basename(dir));
    await fsp.cp(src, target, { recursive: true });
    return target;
  });
  ipcMain.handle("fly:readRun", async (_e, dir) => {
    const p = dir;
    if (!within(DIRS.runs, p)) throw new Error("Папка вне каталога прогонов.");
    const out = { log: "", summary: null };
    try { out.log = (await fsp.readFile(path.join(p, "log.txt"), "utf8")).slice(-20000); } catch {}
    try { out.summary = JSON.parse(await fsp.readFile(path.join(p, "summary.json"), "utf8")); } catch {}
    return out;
  });
}

// ------------------------------------------------------------
let mainWin = null;
function createWindow() {
  mainWin = new BrowserWindow({
    width: 1480,
    height: 920,
    minWidth: 1024,
    minHeight: 640,
    backgroundColor: "#262320",
    autoHideMenuBar: true,
    title: "Fly Ideas",
    webPreferences: { contextIsolation: true, nodeIntegration: false, preload: path.join(__dirname, "preload.cjs") },
  });
  mainWin.webContents.setWindowOpenHandler(({ url }) => {
    if (/^https?:/i.test(url)) shell.openExternal(url);
    return { action: "deny" };
  });
  if (isDev) mainWin.loadURL(process.env.VITE_DEV_SERVER_URL);
  else mainWin.loadFile(path.join(__dirname, "..", "dist", "index.html"));
}

app.whenReady().then(() => {
  ensureDirs();
  registerIpc(() => mainWin);
  createWindow();
  app.on("activate", () => BrowserWindow.getAllWindows().length === 0 && createWindow());
});
app.on("window-all-closed", () => process.platform !== "darwin" && app.quit());
