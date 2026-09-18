const { app, BrowserWindow, shell, ipcMain } = require("electron");
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
const DIRS = { data: path.join(WS, "data"), scripts: path.join(WS, "scripts"), runs: path.join(WS, "runs") };
const TEMPLATES = isDev ? path.join(__dirname, "..", "experiments", "templates") : path.join(process.resourcesPath, "templates");
const SECRETS = path.join(app.getPath("userData"), "secrets.json");

function ensureDirs() {
  for (const d of Object.values(DIRS)) fs.mkdirSync(d, { recursive: true });
  // копируем шаблоны, если их ещё нет
  if (fs.existsSync(TEMPLATES)) {
    for (const f of fs.readdirSync(TEMPLATES)) {
      const dst = path.join(DIRS.scripts, f);
      if (!fs.existsSync(dst)) fs.copyFileSync(path.join(TEMPLATES, f), dst);
    }
  }
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
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/code/paper-brian2/model.py",
    sizeMB: 0.02,
    note: "Ядро модели из статьи; кладём рядом со скриптами",
    dest: "scripts",
  },
  {
    id: "paper-utils",
    group: "Код модели (Shiu et al.)",
    title: "utils.py — анализ спайков",
    file: "paper_utils.py",
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/code/paper-brian2/utils.py",
    sizeMB: 0.01,
    note: "load_exps, get_rate — помощники из статьи",
    dest: "scripts",
  },
];

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

async function download(win, item) {
  const destDir = item.dest === "scripts" ? DIRS.scripts : DIRS.data;
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

async function runScript(win, name, args) {
  const py = await pickPython();
  if (!py) throw new Error("Python 3 не найден. Установи Miniconda или python.org (галочка «Add to PATH»).");
  const [cmd, ...pre] = py.cmd.split(" ");
  const runId = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + "_" + name.replace(/\.py$/, "");
  const runDir = path.join(DIRS.runs, runId);
  fs.mkdirSync(runDir, { recursive: true });
  const script = path.join(DIRS.scripts, name);
  const env = { ...process.env, FLY_DATA: DIRS.data, FLY_RUN_DIR: runDir, FLY_SCRIPTS: DIRS.scripts, PYTHONUNBUFFERED: "1", PYTHONIOENCODING: "utf-8" };
  const p = spawn(cmd, [...pre, script, ...(args || [])], { cwd: DIRS.scripts, env, shell: process.platform === "win32" });
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
    deepseek: { url: "https://api.deepseek.com/chat/completions", key: secrets.deepseek, model: model || "deepseek-chat" },
    openai: { url: "https://api.openai.com/v1/chat/completions", key: secrets.openai, model: model || "gpt-4o-mini" },
  }[provider || "deepseek"];
  if (!cfg) throw new Error("Неизвестный провайдер");
  if (!cfg.key) throw new Error("Ключ API не задан — вкладка «Мозг» → Помощник → ⚙");
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
  ipcMain.handle("fly:getPaths", () => ({ workspace: WS, ...DIRS, templates: TEMPLATES }));
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
  ipcMain.handle("fly:download", async (_e, item) => download(getWin(), item));
  ipcMain.handle("fly:cancelDownload", (_e, id) => { activeDownloads.get(id)?.destroy(); activeDownloads.delete(id); });

  ipcMain.handle("fly:listScripts", async () => {
    const files = (await fsp.readdir(DIRS.scripts)).filter((f) => f.endsWith(".py"));
    return Promise.all(files.map(async (f) => {
      const txt = await fsp.readFile(path.join(DIRS.scripts, f), "utf8");
      const m = txt.match(/^"""\s*\n?([\s\S]*?)"""/);
      return { name: f, doc: m ? m[1].trim().split("\n")[0] : "" };
    }));
  });
  ipcMain.handle("fly:readScript", (_e, name) => fsp.readFile(path.join(DIRS.scripts, path.basename(name)), "utf8"));
  ipcMain.handle("fly:writeScript", (_e, name, content) => fsp.writeFile(path.join(DIRS.scripts, path.basename(name)), content, "utf8"));
  ipcMain.handle("fly:runScript", (_e, name, args) => runScript(getWin(), path.basename(name), args));
  ipcMain.handle("fly:killRun", (_e, runId) => { runs.get(runId)?.kill(); });

  ipcMain.handle("fly:getSecret", (_e, k) => { const s = readSecrets(); return s[k] ? `${s[k].slice(0, 6)}…${s[k].slice(-4)}` : null; });
  ipcMain.handle("fly:setSecret", (_e, k, v) => { const s = readSecrets(); if (v) s[k] = v; else delete s[k]; writeSecrets(s); return true; });
  ipcMain.handle("fly:llmChat", (_e, req) => llmChat(req));

  ipcMain.handle("fly:listRuns", async () => {
    const dirs = (await fsp.readdir(DIRS.runs, { withFileTypes: true })).filter((d) => d.isDirectory()).map((d) => d.name).sort().reverse();
    return Promise.all(dirs.slice(0, 50).map(async (d) => {
      const p = path.join(DIRS.runs, d);
      let summary = null;
      try { summary = JSON.parse(await fsp.readFile(path.join(p, "summary.json"), "utf8")); } catch {}
      const files = await fsp.readdir(p);
      return { dir: d, path: p, summary, files };
    }));
  });
  ipcMain.handle("fly:readRun", async (_e, dir) => {
    const p = path.join(DIRS.runs, path.basename(dir));
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
    backgroundColor: "#18181b",
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
