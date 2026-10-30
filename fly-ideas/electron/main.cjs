const { app, BrowserWindow, shell, ipcMain, dialog } = require("electron");
const os = require("node:os");
const path = require("node:path");
const fs = require("node:fs");
const fsp = require("node:fs/promises");
const { spawn } = require("node:child_process");
const https = require("node:https");
const http = require("node:http");
const crypto = require("node:crypto");
const { writeAssistantFile } = require("./assistant-files.cjs");
const folderSync = require("./folder-sync.cjs");

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
const API_CALLS_FILE = path.join(app.getPath("userData"), "api-calls.json");
let apiCallWriteQueue = Promise.resolve();

function readConfig() {
  try { return JSON.parse(fs.readFileSync(CONFIG, "utf8")); } catch { return {}; }
}
function writeConfig(c) {
  fs.mkdirSync(path.dirname(CONFIG), { recursive: true });
  fs.writeFileSync(CONFIG, JSON.stringify(c, null, 2));
}

const DATA_FILE_ROLES = { connections: "FLY_CONNECTOME", annotations: "FLY_ANNOTATIONS", cell_types: "FLY_CELL_TYPES", neurotransmitters: "FLY_NEUROTRANSMITTERS" };
function dataFileLinks() {
  const saved = readConfig().dataFiles || {};
  return Object.fromEntries(Object.keys(DATA_FILE_ROLES).map((role) => {
    const file = typeof saved[role] === "string" ? saved[role] : "";
    try {
      const info = fs.statSync(file);
      fs.accessSync(file, fs.constants.R_OK);
      return [role, { path: file, available: info.isFile(), size: info.isFile() ? info.size : null }];
    } catch {
      return [role, { path: file, available: false, size: null }];
    }
  }));
}
/** Текущие папки: пользовательские из config.json поверх дефолтных */
function getDirs() {
  const c = readConfig().dirs || {};
  const d = { ...DEFAULT_DIRS };
  for (const k of Object.keys(DEFAULT_DIRS)) if (c[k] && typeof c[k] === "string") d[k] = c[k];
  return d;
}
const DIRS = new Proxy({}, { get: (_t, k) => getDirs()[k] });

/** Стартовый набор скриптов для каждой из 10 базовых идей (в папку идеи кладутся только нужные ей файлы + flylib.py + 00_check_env.py) */
const IDEA_TEMPLATE_MAP = {
  "i-lesions": ["10_virtual_lesions.py", "03_shiu_activate.py", "06_brian2_shiu.py"],
  "i-interference": ["11_mb_interference_connectome.py", "02_mb_toy_interference.py", "04_mb_sweep_heatmap.py", "09_mb_circuit_v783.py"],
  "i-benchmark": ["12_backend_benchmark.py", "00_check_env.py", "06_brian2_shiu.py"],
  "i-mb-learning": ["13_whole_brain_mb_learning.py", "09_mb_circuit_v783.py", "06_brian2_shiu.py"],
  "i-courtship-memory": ["14_malecns_courtship_memory.py", "08_malecns_loader.py", "07_morph_activity_figure.py"],
  "i-memory-to-action": ["15_memory_to_motor_vnc.py", "08_malecns_loader.py", "05_neuron_gallery.py"],
  "i-observational": ["16_observational_learning.py", "09_mb_circuit_v783.py"],
  "i-individuality": ["17_individuality_phenotypes.py", "06_brian2_shiu.py", "20_brian2_smoke_test.py"],
  "i-song": ["18_courtship_song_ipi.py", "08_malecns_loader.py"],
  "i-pci": ["19_pci_integration.py", "06_brian2_shiu.py"],
};

function copyTemplates(scriptsDir, opts) {
  if (!fs.existsSync(TEMPLATES)) return [];
  const overwrite = !!(opts && opts.overwrite);
  const filterSet = opts && opts.only ? new Set(opts.only) : null;
  const copied = [];
  for (const f of fs.readdirSync(TEMPLATES)) {
    if (!/\.(py|md|json|yml)$/i.test(f)) continue;
    if (filterSet && !filterSet.has(f)) continue;
    const src = path.join(TEMPLATES, f);
    if (!fs.statSync(src).isFile()) continue;
    const dst = path.join(scriptsDir, f);
    if (overwrite || !fs.existsSync(dst)) {
      fs.copyFileSync(src, dst);
      copied.push(f);
    }
  }
  return copied;
}

/** Имя проекта/идеи приводим к безопасному виду: оно становится именем папки */
function slug(projectId) {
  const s = String(projectId || "project").replace(/[^A-Za-z0-9._-]/g, "-").replace(/^-+|-+$/g, "");
  return s || "project";
}

/** Разбор идентификатора рабочего пространства:
 *  - "idea:<ideaId>" или "idea__<ideaId>" -> отдельная папка идеи workspace/scripts/ideas/<ideaId> и workspace/runs/ideas/<ideaId>
 *  - иначе -> общая папка проекта workspace/scripts/<projectId> и workspace/runs/<projectId>
 */
function parseScope(scopeOrProjectId) {
  const raw = String(scopeOrProjectId || "project").trim();
  const m = raw.match(/^idea(?::|__)(.+)$/);
  if (m) {
    const ideaId = slug(m[1]);
    return {
      kind: "idea",
      scopeId: `idea:${ideaId}`,
      cfgKey: `idea__${ideaId}`,
      ideaId,
      defaults: {
        code: path.join(DIRS.scripts, "ideas", ideaId),
        runs: path.join(DIRS.runs, "ideas", ideaId),
      },
    };
  }
  const id = slug(raw);
  return {
    kind: "project",
    scopeId: id,
    cfgKey: id,
    ideaId: null,
    defaults: {
      code: path.join(DIRS.scripts, id),
      runs: path.join(DIRS.runs, id),
    },
  };
}

function allowedTemplatesForScope(scope, includeAll = false) {
  if (includeAll || scope.kind !== "idea") return null;
  const specific = IDEA_TEMPLATE_MAP[scope.ideaId] || ["01_load_connectome.py"];
  return new Set(["flylib.py", "00_check_env.py", "21_check_linked_data.py", "small_sample_lif_fixed.py", ...specific]);
}

function migrateLegacyIdeaScripts(scope, codeDir) {
  if (scope.kind !== "idea") return;
  const c = readConfig();
  c.ideaWorkspaceInitialized = c.ideaWorkspaceInitialized || {};
  if (c.ideaWorkspaceInitialized[scope.ideaId]) return;
  const sourceProjectId = scope.ideaId === "i-pci" ? "p-archive" : "p-fly-brain";
  const sourceOverride = c.projectDirs?.[sourceProjectId]?.code;
  const sourceDir = typeof sourceOverride === "string" ? sourceOverride : path.join(DIRS.scripts, sourceProjectId);
  const allow = allowedTemplatesForScope(scope);
  if (fs.existsSync(sourceDir) && allow) {
    for (const name of allow) {
      const from = path.join(sourceDir, name);
      const to = path.join(codeDir, name);
      try {
        if (!fs.existsSync(to) && fs.statSync(from).isFile()) fs.copyFileSync(from, to);
      } catch {}
    }
  }
  c.ideaWorkspaceInitialized[scope.ideaId] = true;
  writeConfig(c);
}

function syncProjectTemplates(scopeOrProjectId, codeDir, forceMissing = false, includeAll = false) {
  if (!fs.existsSync(TEMPLATES)) return [];
  const scope = parseScope(scopeOrProjectId);
  const allowed = allowedTemplatesForScope(scope, includeAll);
  const c = readConfig();
  c.seededTemplates = c.seededTemplates || {};
  const seeded = new Set(Array.isArray(c.seededTemplates[scope.cfgKey]) ? c.seededTemplates[scope.cfgKey] : []);
  const isEmpty = fs.readdirSync(codeDir).length === 0;
  const added = [];
  let changed = false;
  for (const f of fs.readdirSync(TEMPLATES)) {
    if (!/\.(py|md|json|yml)$/i.test(f)) continue;
    if (allowed && !allowed.has(f)) continue;
    const src = path.join(TEMPLATES, f);
    if (!fs.statSync(src).isFile()) continue;
    const dst = path.join(codeDir, f);
    if (!fs.existsSync(dst) && (isEmpty || forceMissing || !seeded.has(f))) {
      fs.copyFileSync(src, dst);
      added.push(f);
    }
    if (!seeded.has(f)) {
      seeded.add(f);
      changed = true;
    }
  }
  if (changed || added.length > 0) {
    c.seededTemplates[scope.cfgKey] = Array.from(seeded);
    writeConfig(c);
  }
  return added;
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

/** Путь внутри родительской папки, не выше её */
function within(parent, target) {
  const rel = path.relative(parent, target);
  return !!rel && !rel.startsWith("..") && !path.isAbsolute(rel);
}

/** Рабочие папки идеи или проекта: код и прогоны. Можно переназначить через config.json. */
function projectPaths(scopeOrProjectId) {
  assertNotSyncing();
  const scope = parseScope(scopeOrProjectId);
  const cfg = readConfig().projectDirs || {};
  const over = cfg[scope.cfgKey] || {};
  const defaults = scope.defaults;
  const code = typeof over.code === "string" ? over.code : defaults.code;
  const runs = typeof over.runs === "string" ? over.runs : defaults.runs;
  fs.mkdirSync(code, { recursive: true });
  fs.mkdirSync(runs, { recursive: true });
  migrateLegacyIdeaScripts(scope, code);
  syncProjectTemplates(scopeOrProjectId, code, false, false);
  return { projectId: scope.scopeId, ideaId: scope.ideaId, code, runs, defaults };
}
function setProjectDir(scopeOrProjectId, kind, dir) {
  const scope = parseScope(scopeOrProjectId);
  const c = readConfig();
  c.projectDirs = c.projectDirs || {};
  const cur = c.projectDirs[scope.cfgKey] || {};
  if (dir) cur[kind] = dir;
  else delete cur[kind];
  c.projectDirs[scope.cfgKey] = cur;
  writeConfig(c);
  return projectPaths(scopeOrProjectId);
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
    sizeMB: 3.1,
    note: "ID нейронов FlyWire v783 (138 639 клеток), нужен для запуска целого мозга и сопоставления индексов",
  },
  {
    id: "connectivity-783",
    group: "Eon fly-brain (FlyWire v783)",
    title: "Связность (Connectivity v783, parquet)",
    file: "2025_Connectivity_783.parquet",
    url: "https://raw.githubusercontent.com/eonsystemspbc/fly-brain/main/data/2025_Connectivity_783.parquet",
    sizeMB: 21.1,
    note: "Пре- и постсинаптические индексы и знаковые веса (Excitatory x Connectivity), основная матрица связей",
  },
  {
    id: "flywire-annotations-tsv",
    group: "Eon fly-brain (FlyWire v783)",
    title: "Аннотации типов клеток FlyWire (Schlegel et al. 2024, TSV)",
    file: "Supplemental_file1_neuron_annotations.tsv",
    url: "https://raw.githubusercontent.com/flyconnectome/flywire_annotations/main/supplemental_files/Supplemental_file1_neuron_annotations.tsv",
    sizeMB: 31.7,
    note: "Классы, типы клеток (KC, MBON, PAM, PPL1, APL, PN, DN), нейромедиатор и диморфизм для скриптов 01, 09 и 10..19",
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

const MALE_CNS_BASE = "https://storage.googleapis.com/flyem-male-cns/v0.9/connectome-data/flat-connectome/";

// ------------------------------------------------------------
// MaleCNS (полный коннектом ЦНС самца Janelia + таблицы сопоставления с FlyWire)
// ------------------------------------------------------------
DATA_CATALOG.push(
  {
    id: "malecns-annotations",
    group: "MaleCNS, ЦНС самца (Janelia)",
    title: "Аннотации нейронов: классы, типы, области и VNC",
    file: "body-annotations-male-cns-v0.9-minconf-0.5.feather",
    url: MALE_CNS_BASE + "body-annotations-male-cns-v0.9-minconf-0.5.feather",
    page: "https://male-cns.janelia.org/download/",
    sizeMB: 13,
    note: "Типы клеток мозга и брюшной нервной цепочки (включая pC1, P1, vPN1, aSP13, мотонейроны VNC). Читается pyarrow/pandas.",
    dest: "data",
  },
  {
    id: "malecns-neurotransmitters",
    group: "MaleCNS, ЦНС самца (Janelia)",
    title: "Предсказание нейромедиатора по нейрону",
    file: "body-neurotransmitters-male-cns-v0.9.feather",
    url: MALE_CNS_BASE + "body-neurotransmitters-male-cns-v0.9.feather",
    page: "https://male-cns.janelia.org/download/",
    sizeMB: 42,
    note: "Нужно для знаков синапсов при сборке LIF-модели на мужском коннектоме.",
    dest: "data",
  },
  {
    id: "malecns-fw-mapping",
    group: "MaleCNS, ЦНС самца (Janelia)",
    title: "Гомология клеток и связей MaleCNS <-> FlyWire v783",
    file: "mcns_fw_edge_comp_mappings.json",
    url: "https://raw.githubusercontent.com/flyconnectome/2025malecns/main/supplemental_data/mcns_fw_edge_comp_mappings.json",
    page: "https://github.com/flyconnectome/2025malecns",
    sizeMB: 6.7,
    note: "Таблица соответствия типов самца и самки для скриптов 07 и 14 (память ухаживания и половой диморфизм).",
    dest: "data",
  },
  {
    id: "malecns-dn-clusters",
    group: "MaleCNS, ЦНС самца (Janelia)",
    title: "Функциональные кластеры нисходящих нейронов (DNa/DNp -> VNC)",
    file: "dnan_cluster_function_20260509.csv",
    url: "https://raw.githubusercontent.com/flyconnectome/2025malecns/main/supplemental_data/dnan_cluster_function_20260509.csv",
    page: "https://github.com/flyconnectome/2025malecns",
    sizeMB: 0.1,
    note: "Разметка поведенческих пулов нисходящих нейронов шеи для скриптов 10 (лезии) и 15 (от памяти к мотонейронам VNC).",
    dest: "data",
  },
);

const activeDownloads = new Map();
let syncBusy = false;
let syncAwaitingReload = false;
let downloadsInFlight = 0;
let llmInFlight = 0;
let llmSettledAt = 0;
let environmentInFlight = 0;
let mutationsInFlight = 0;
let agentRequestsInFlight = 0;
function assertNotSyncing() {
  if (syncBusy) throw new Error("Дождитесь окончания синхронизации.");
}
async function withSyncLock(operation) {
  if (syncBusy || runs.size || downloadsInFlight || llmInFlight || environmentInFlight || mutationsInFlight || agentRequestsInFlight || agentWrites.size || Date.now() - llmSettledAt < 2000) {
    throw new Error("Дождитесь завершения расчётов, загрузок, установки окружения и ответов помощника, затем повторите.");
  }
  syncBusy = true;
  try { await apiCallWriteQueue; return await operation(); }
  finally { if (!syncAwaitingReload) syncBusy = false; }
}

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
// Окружение: python / conda / venv / установка пакетов / GPU
// ------------------------------------------------------------
function run(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    let out = "", err = "";
    let p;
    const useShell = opts.shell !== undefined ? opts.shell : (process.platform === "win32" && !path.isAbsolute(cmd) && /\.(cmd|bat)$/i.test(cmd));
    try {
      p = spawn(cmd, args, { windowsHide: true, ...opts, shell: useShell });
    } catch (e) {
      return resolve({ ok: false, out: "", err: String(e) });
    }
    p.stdout?.on("data", (d) => (out += d));
    p.stderr?.on("data", (d) => (err += d));
    p.on("error", (e) => {
      if (process.platform === "win32" && !useShell && !path.isAbsolute(cmd)) {
        run(cmd, args, { ...opts, shell: true }).then(resolve);
        return;
      }
      resolve({ ok: false, out, err: String(e) });
    });
    p.on("close", (code) => resolve({ ok: code === 0, out: out.trim(), err: err.trim(), code }));
  });
}

function parsePySpec(spec) {
  const s = String(spec || "").trim();
  if (s === "py -3") return { cmd: "py", prefix: ["-3"], raw: s };
  return { cmd: s, prefix: [], raw: s };
}

function runPy(spec, args, opts = {}) {
  const { cmd, prefix } = parsePySpec(spec);
  return run(cmd, [...prefix, ...args], opts);
}

function venvPythonExe(venvDir) {
  return process.platform === "win32"
    ? path.join(venvDir, "Scripts", "python.exe")
    : path.join(venvDir, "bin", "python");
}

function condaPythonExe(envDir) {
  return process.platform === "win32"
    ? path.join(envDir, "python.exe")
    : path.join(envDir, "bin", "python");
}

function discoverPythonCandidates() {
  const seen = new Set();
  const list = [];
  const add = (cmd, source, note, mustExistFile = false) => {
    if (!cmd) return;
    const norm = process.platform === "win32" ? cmd.toLowerCase() : cmd;
    if (seen.has(norm)) return;
    if (mustExistFile && !fs.existsSync(cmd)) return;
    seen.add(norm);
    list.push({ cmd, source, note });
  };

  const configured = (readConfig().pythonPath || "").trim();
  if (configured) add(configured, "selected", "выбран вручную", path.isAbsolute(configured));

  add(venvPythonExe(path.join(WS, ".venv")), "venv", "локальное окружение workspace/.venv", true);
  add(venvPythonExe(path.join(appRoot, ".venv")), "venv", "локальное окружение .venv", true);

  // Conda: сначала ~/.conda/environments.txt (работает на любом диске C:, D:, E:), затем типовые папки
  const home = os.homedir();
  const envsTxt = path.join(home, ".conda", "environments.txt");
  if (fs.existsSync(envsTxt)) {
    try {
      const lines = fs.readFileSync(envsTxt, "utf8").split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
      const flyEnvs = lines.filter((l) => /fly[-_]?brain/i.test(path.basename(l)));
      const otherEnvs = lines.filter((l) => !/fly[-_]?brain/i.test(path.basename(l)));
      for (const dir of [...flyEnvs, ...otherEnvs]) {
        add(condaPythonExe(dir), "conda", `conda (${path.basename(dir)})`, true);
      }
    } catch {}
  }

  const condaRoots = [
    path.join(home, "miniconda3"),
    path.join(home, "anaconda3"),
    path.join(home, "miniforge3"),
    path.join(home, "mambaforge"),
    path.join(home, ".conda"),
    ...(process.env.LOCALAPPDATA ? [path.join(process.env.LOCALAPPDATA, "miniconda3"), path.join(process.env.LOCALAPPDATA, "anaconda3"), path.join(process.env.LOCALAPPDATA, "miniforge3")] : []),
    ...(process.env.PROGRAMDATA ? [path.join(process.env.PROGRAMDATA, "miniconda3"), path.join(process.env.PROGRAMDATA, "anaconda3")] : []),
    ...(process.platform === "win32" ? ["C:\\miniconda3", "D:\\miniconda3", "E:\\miniconda3", "C:\\anaconda3", "D:\\anaconda3", "E:\\anaconda3"] : []),
  ];
  for (const root of condaRoots) {
    add(condaPythonExe(path.join(root, "envs", "fly-brain")), "conda", "conda (fly-brain)", true);
  }
  for (const root of condaRoots) {
    add(condaPythonExe(root), "conda", `conda (${path.basename(root)})`, true);
  }

  const sysCands = process.platform === "win32" ? ["python", "py -3", "python3"] : ["python3", "python"];
  for (const c of sysCands) add(c, "system", "системный PATH", false);
  return list;
}

const QUICK_PROBE_CODE = [
  "import sys, json",
  "from importlib.util import find_spec",
  "mods = {}",
  "for m in ('numpy','pandas','scipy','matplotlib','pyarrow','brian2'):",
  "    try:",
  "        mods[m] = find_spec(m) is not None",
  "    except Exception:",
  "        mods[m] = False",
  "print(json.dumps({'ver': sys.version.split()[0], 'mm': list(sys.version_info[:2]), 'exe': sys.executable, 'ok': mods}))",
].join("\n");

async function probePythonCandidate(cand) {
  const r = await runPy(cand.cmd, ["-c", QUICK_PROBE_CODE]);
  if (!r.ok || !r.out) return null;
  try {
    const j = JSON.parse(r.out.split(/\r?\n/).pop());
    if (!Array.isArray(j.mm) || j.mm[0] < 3) return null;
    const hasCore = !!(j.ok && j.ok.numpy && j.ok.pandas && j.ok.matplotlib);
    return {
      cmd: cand.cmd,
      exe: j.exe || cand.cmd,
      version: `Python ${j.ver}`,
      majorMinor: j.mm,
      hasCore,
      okMap: j.ok || {},
      source: cand.source,
      note: cand.note,
    };
  } catch {
    return null;
  }
}

async function listPythons() {
  const cands = discoverPythonCandidates();
  const seenExe = new Set();
  const found = [];
  for (const c of cands) {
    const p = await probePythonCandidate(c);
    if (!p) continue;
    const key = process.platform === "win32" ? p.exe.toLowerCase() : p.exe;
    if (seenExe.has(key) && c.source !== "selected") continue;
    seenExe.add(key);
    found.push(p);
  }
  return found;
}

async function pickPython() {
  const cands = discoverPythonCandidates();
  let fallback = null;
  for (const c of cands) {
    const p = await probePythonCandidate(c);
    if (!p) continue;
    if (c.source === "selected") return p;
    if (p.hasCore) return p;
    if (!fallback) fallback = p;
  }
  return fallback;
}

async function checkEnv() {
  const py = await pickPython();
  const configured = (readConfig().pythonPath || "").trim() || null;
  const result = { python: py, configuredPython: configured, conda: null, packages: {}, gpu: null, venvPath: path.join(WS, ".venv") };
  const conda = await run("conda", ["--version"], { shell: process.platform === "win32" });
  if (conda.ok) result.conda = conda.out;
  if (py) {
    const probe = `
import json, importlib
mods = ["numpy","pandas","pyarrow","brian2","torch","matplotlib","scipy"]
out = {}
for m in mods:
    try:
        mod = importlib.import_module(m); out[m] = getattr(mod, "__version__", "ok")
    except Exception:
        out[m] = None
try:
    import torch; out["cuda"] = torch.cuda.is_available() and torch.cuda.get_device_name(0)
except Exception:
    out["cuda"] = None
print(json.dumps(out))
`;
    const r = await runPy(py.cmd, ["-c", probe]);
    if (r.ok) {
      try {
        const j = JSON.parse(r.out.split(/\r?\n/).pop());
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

let envSetupBusy = false;
async function setupPythonEnv(win, mode = "core") {
  if (envSetupBusy) throw new Error("Установка пакетов уже выполняется, подожди завершения.");
  envSetupBusy = true;
  const emit = (text, extra = {}) => {
    win?.webContents.send("fly:envSetupOutput", { text, done: false, ...extra });
  };
  const runStreamed = (exe, args, envExtra = {}) =>
    new Promise((resolve) => {
      let codeOut = 1;
      let errMsg = "";
      let p;
      try {
        p = spawn(exe, args, {
          windowsHide: true,
          shell: false,
          env: { ...process.env, PYTHONIOENCODING: "utf-8", PIP_DISABLE_PIP_VERSION_CHECK: "1", ...envExtra },
        });
      } catch (e) {
        emit(`\n[ошибка запуска ${exe}: ${e.message || e}]\n`);
        return resolve({ ok: false, code: 1 });
      }
      p.stdout?.on("data", (d) => emit(d.toString()));
      p.stderr?.on("data", (d) => emit(d.toString()));
      p.on("error", (e) => {
        errMsg = String(e.message || e);
        emit(`\n[ошибка процесса: ${errMsg}]\n`);
        resolve({ ok: false, code: 1 });
      });
      p.on("close", (code) => {
        codeOut = code ?? 1;
        resolve({ ok: codeOut === 0, code: codeOut });
      });
    });

  try {
    const basePy = await pickPython();
    if (!basePy) {
      throw new Error("Python 3 не найден в системе. Сначала установи Python 3.11/3.12 с python.org (с галочкой Add Python to PATH) или Miniconda.");
    }

    const venvDir = path.join(WS, ".venv");
    const venvExe = venvPythonExe(venvDir);
    let targetExe = venvExe;
    let useUserFlag = false;

    if (!fs.existsSync(venvExe)) {
      emit(`[1/3] Создаю изолированное окружение Python в ${venvDir} ...\n`);
      fs.mkdirSync(path.dirname(venvDir), { recursive: true });
      const baseSpec = parsePySpec(basePy.exe || basePy.cmd);
      const mk = await runStreamed(baseSpec.cmd, [...baseSpec.prefix, "-m", "venv", venvDir]);
      if (!mk.ok || !fs.existsSync(venvExe)) {
        emit("[предупреждение] Не удалось создать venv, ставлю пакеты напрямую с флагом --user...\n");
        targetExe = basePy.exe || parsePySpec(basePy.cmd).cmd;
        useUserFlag = true;
      }
    } else {
      emit(`[1/3] Использую окружение ${venvExe}\n`);
    }

    const targetProbe = await probePythonCandidate({ cmd: targetExe, source: "venv", note: "" });
    const mm = targetProbe?.majorMinor || basePy.majorMinor || [3, 12];
    const isPy313Plus = mm[0] > 3 || (mm[0] === 3 && mm[1] >= 13);

    const corePkgs = isPy313Plus
      ? ["numpy", "pyarrow", "pandas", "scipy", "matplotlib"]
      : ["numpy<2", "pyarrow<19", "pandas", "scipy", "matplotlib"];
    const extraPkgs = isPy313Plus
      ? ["brian2", "networkx", "joblib", "requests", "tqdm", "pillow"]
      : ["brian2==2.9.0", "networkx", "joblib", "requests", "tqdm", "pillow"];
    const pkgs = mode === "full" ? [...corePkgs, ...extraPkgs] : corePkgs;

    emit(`[2/3] Ставлю пакеты для Python ${mm[0]}.${mm[1]}: ${pkgs.join(", ")}\n`);
    const pipArgs = ["-m", "pip", "install", "--prefer-binary", ...(useUserFlag ? ["--user"] : []), ...pkgs];
    const inst = await runStreamed(targetExe, pipArgs);
    if (!inst.ok) {
      emit(`\n[ошибка: pip завершился с кодом ${inst.code}]\n`, { done: true, ok: false });
      throw new Error(`Установка пакетов завершилась с кодом ${inst.code}. Проверь подключение к интернету и лог установки.`);
    }

    emit("[3/3] Проверяю импорт установленных библиотек...\n");
    const c = readConfig();
    c.pythonPath = targetExe;
    writeConfig(c);

    const env = await checkEnv();
    emit(`\n[готово] Активный интерпретатор: ${env.python?.exe || targetExe}\nТеперь можно нажимать «запустить».\n`, { done: true, ok: true });
    return env;
  } catch (e) {
    emit(`\n[ошибка] ${e.message || e}\n`, { done: true, ok: false });
    throw e;
  } finally {
    envSetupBusy = false;
  }
}

// ------------------------------------------------------------
// Запуск скриптов
// ------------------------------------------------------------
const runs = new Map();

async function runScript(win, projectId, name, args) {
  assertNotSyncing();
  const py = await pickPython();
  if (!py) throw new Error("Python 3 не найден. Установи Miniconda или Python 3.11/3.12 с python.org (галочка «Add to PATH»).");
  assertNotSyncing();
  if (!getPermissions().runScripts) throw new Error("Запуск скриптов выключен в правах рабочего места.");
  const ws = projectPaths(projectId);
  const file = path.join(ws.code, path.basename(name));
  if (!within(ws.code, file)) throw new Error("Скрипт вне папки рабочего пространства.");
  const { cmd, prefix } = parsePySpec(py.exe || py.cmd);
  const baseId = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + "_" + path.basename(name).replace(/\.py$/, "");
  let runId = baseId;
  let seq = 2;
  while (runs.has(runId) || runStatus.has(runId) || fs.existsSync(path.join(ws.runs, runId))) {
    runId = `${baseId}_${seq++}`;
  }
  const runDir = path.join(ws.runs, runId);
  fs.mkdirSync(runDir, { recursive: true });
  const script = file;
  const scriptArgs = [...(args || [])];
  if (path.basename(name) === "10_virtual_lesions.py") {
    for (let i = 0; i < scriptArgs.length; i++) {
      if (scriptArgs[i] === "--n-trials") scriptArgs[i] = "--n-run";
      else if (scriptArgs[i] === "--fractions") scriptArgs[i] = "--doses";
    }
  }
  const pyPath = [ws.code, TEMPLATES, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter);
  const links = dataFileLinks();
  const env = {
    ...process.env,
    FLY_DATA: DIRS.data,
    FLY_CONNECTOME: links.connections.path,
    FLY_ANNOTATIONS: links.annotations.path,
    FLY_CELL_TYPES: links.cell_types.path,
    FLY_NEUROTRANSMITTERS: links.neurotransmitters.path,
    FLY_RUN_DIR: runDir,
    FLY_SCRIPTS: ws.code,
    FLY_PROJECT: ws.projectId,
    ...(ws.ideaId ? { FLY_IDEA: ws.ideaId } : {}),
    PYTHONPATH: pyPath,
    PYTHONUNBUFFERED: "1",
    PYTHONIOENCODING: "utf-8",
  };
  const useShell = process.platform === "win32" && !path.isAbsolute(cmd) && /\.(cmd|bat)$/i.test(cmd);
  const p = spawn(cmd, [...prefix, script, ...scriptArgs], { cwd: ws.code, env, windowsHide: true, shell: useShell });
  runs.set(runId, p);
  const log = fs.createWriteStream(path.join(runDir, "log.txt"));
  const send = (stream, text) => {
    log.write(text);
    win?.webContents.send("fly:runOutput", { runId, projectId: ws.projectId, runDir, stream, text });
  };
  send("stdout", `[python] ${py.exe || py.cmd} (${py.version})\n`);
  p.stdout.on("data", (d) => send("stdout", d.toString()));
  p.stderr.on("data", (d) => send("stderr", d.toString()));
  p.on("error", (e) => send("stderr", `\n[ошибка запуска Python: ${e.message || e}]\n`));
  p.on("close", (code) => {
    log.end();
    runs.delete(runId);
    runStatus.set(runId, { code, dir: runDir, projectId: ws.projectId, finishedAt: new Date().toISOString() });
    win?.webContents.send("fly:runOutput", { runId, projectId: ws.projectId, runDir, stream: "exit", code, text: `\n[завершено, код ${code}]\n` });
  });
  return { runId, runDir, projectId: ws.projectId };
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

function readApiCallStore() {
  try {
    const store = JSON.parse(fs.readFileSync(API_CALLS_FILE, "utf8"));
    if (!store || typeof store !== "object" || Array.isArray(store)) throw new Error("Неверный формат журнала API.");
    return store;
  } catch (error) {
    if (error.code === "ENOENT") return {};
    throw new Error(`Не удалось прочитать журнал API (${API_CALLS_FILE}): ${error.message}`);
  }
}

async function listApiCalls(workspaceId) {
  await apiCallWriteQueue;
  const store = readApiCallStore();
  if (workspaceId === "__all__") {
    return Object.values(store).flatMap((items) => Array.isArray(items) ? items : []).sort((a, b) => String(a.at).localeCompare(String(b.at)));
  }
  const key = crypto.createHash("sha256").update(String(workspaceId)).digest("hex");
  return Array.isArray(store[key]) ? store[key] : [];
}

function appendApiCall(workspaceId, record) {
  const write = apiCallWriteQueue.then(async () => {
    if (!record || typeof record !== "object") throw new Error("Некорректная запись API-вызова.");
    const provider = ["deepseek", "perplexity", "openai"].includes(record.provider) ? record.provider : "deepseek";
    const usage = record.usage && typeof record.usage === "object" ? {
      inputTokens: Number.isFinite(record.usage.inputTokens) ? Math.max(0, Math.floor(record.usage.inputTokens)) : null,
      outputTokens: Number.isFinite(record.usage.outputTokens) ? Math.max(0, Math.floor(record.usage.outputTokens)) : null,
      totalTokens: Number.isFinite(record.usage.totalTokens) ? Math.max(0, Math.floor(record.usage.totalTokens)) : null,
    } : null;
    const safeRecord = {
      id: String(record.id || crypto.randomUUID()).slice(0, 100),
      workspaceId: String(workspaceId),
      at: String(record.at || new Date().toISOString()).slice(0, 40),
      provider,
      model: String(record.model || "unknown").slice(0, 120),
      question: String(record.question || ""),
      answer: String(record.answer || ""),
      usage,
      status: record.status === "ok" ? "ok" : "error",
    };
    const key = crypto.createHash("sha256").update(String(workspaceId)).digest("hex");
    const store = readApiCallStore();
    const list = Array.isArray(store[key]) ? store[key] : [];
    store[key] = [...list, safeRecord];
    await fsp.mkdir(path.dirname(API_CALLS_FILE), { recursive: true });
    const tempFile = `${API_CALLS_FILE}.${process.pid}.tmp`;
    await fsp.writeFile(tempFile, JSON.stringify(store), { encoding: "utf8", mode: 0o600 });
    await fsp.rename(tempFile, API_CALLS_FILE);
  });
  apiCallWriteQueue = write.catch(() => {});
  return write;
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
  return { content: j.choices?.[0]?.message?.content ?? "", usage: j.usage, finishReason: j.choices?.[0]?.finish_reason ?? null };
}

// ------------------------------------------------------------
// Мост для внешнего агента (MCP): локальный HTTP на 127.0.0.1 с токеном.
// Приложение остаётся источником правды: чтение из снимка состояния,
// запись и запуски проходят проверки и видны в интерфейсе.
// ------------------------------------------------------------
const AGENT_FILE = path.join(app.getPath("userData"), "agent.json");
const MCP_SERVER = isDev ? path.join(__dirname, "..", "mcp", "server.mjs") : path.join(process.resourcesPath, "mcp", "server.mjs");
const STATE_FILE = path.join(app.getPath("userData"), "state.json");
const AGENT = { token: crypto.randomBytes(24).toString("hex"), port: 0, server: null, state: null, syncedAt: 0 };
const agentWrites = new Map();
const runStatus = new Map();
let agentSeq = 0;
let snapshotTimer = null;

const win = () => BrowserWindow.getAllWindows()[0] || null;

function agentEnabled() {
  return readConfig().agentEnabled !== false;
}
/** Путь внутри любой из папок прогонов: общей или переназначенной проектом */
function withinRuns(p) {
  if (within(DIRS.runs, p)) return true;
  const cfg = readConfig().projectDirs || {};
  for (const v of Object.values(cfg)) if (v && typeof v.runs === "string" && within(v.runs, p)) return true;
  return false;
}
function agentNote(text) {
  win()?.webContents.send("fly:agentNotice", { text, at: Date.now() });
}
function writeSnapshot() {
  if (snapshotTimer) clearTimeout(snapshotTimer);
  snapshotTimer = setTimeout(() => {
    try {
      fs.mkdirSync(path.dirname(STATE_FILE), { recursive: true });
      fs.writeFileSync(STATE_FILE, JSON.stringify(AGENT.state || {}, null, 1));
    } catch {}
  }, 500);
}
/** Запись просим применить у окна: оно держит store и показывает уведомление */
function agentAsk(kind, payload, timeoutMs = 20000) {
  const w = win();
  if (!w) return Promise.reject(new Error("Окно приложения недоступно."));
  const reqId = `a${++agentSeq}`;
  return new Promise((resolve, reject) => {
    const t = setTimeout(() => {
      agentWrites.delete(reqId);
      reject(new Error("Приложение не подтвердило запись за 20 секунд."));
    }, timeoutMs);
    agentWrites.set(reqId, { resolve, reject, t });
    w.webContents.send("fly:agentWrite", { reqId, kind, payload });
  });
}
function agentAck(reqId, result) {
  const w = agentWrites.get(reqId);
  if (!w) return false;
  clearTimeout(w.t);
  agentWrites.delete(reqId);
  w.resolve(result);
  return true;
}

function state() {
  return AGENT.state || { projects: [], ideas: [], references: [] };
}
function findIdea({ id, title }) {
  const list = state().ideas || [];
  if (id) return list.find((i) => i.id === id || i.id.toLowerCase() === String(id).toLowerCase());
  if (title) {
    const q = String(title).toLowerCase();
    return list.find((i) => i.title.toLowerCase() === q) || list.find((i) => i.title.toLowerCase().includes(q));
  }
  return null;
}
const ideaBrief = (i) => ({
  id: i.id, title: i.title, projectId: i.projectId, status: i.status,
  scores: i.scores, deadline: i.deadline,
  чеклист: { пройдено: i.checklist.filter((c) => c.done).length, всего: i.checklist.length },
  метки: i.tags, прогонов: i.experiments.length, источников: i.citations.length,
});

async function agentRoute(route, q, body, method) {
  assertNotSyncing();
  switch (route) {
    case "/status": {
      const st = state();
      const dirs = getDirs();
      return {
        приложение: "Fly Ideas",
        порт: AGENT.port,
        agentFile: AGENT_FILE,
        состояниеОбновлено: AGENT.syncedAt ? new Date(AGENT.syncedAt).toISOString() : null,
        права: getPermissions(),
        папки: { данные: dirs.data, скрипты: dirs.scripts, прогоны: dirs.runs, экспорт: dirs.exports },
        проекты: (st.projects || []).map((p) => ({ id: p.id, name: p.name, идей: (st.ideas || []).filter((i) => i.projectId === p.id).length })),
        идейВсего: (st.ideas || []).length,
        источниковВсего: (st.references || []).length,
      };
    }
    case "/projects": {
      const st = state();
      return (st.projects || []).map((p) => ({ ...p, идей: (st.ideas || []).filter((i) => i.projectId === p.id).length }));
    }
    case "/ideas": {
      const st = state();
      let list = st.ideas || [];
      if (q.projectId && q.projectId !== "all") list = list.filter((i) => i.projectId === q.projectId);
      if (q.status) list = list.filter((i) => i.status === q.status);
      if (q.query) {
        const needle = String(q.query).toLowerCase();
        list = list.filter((i) => (i.title + " " + i.question + " " + i.method + " " + i.tags.join(" ")).toLowerCase().includes(needle));
      }
      list = [...list].sort((a, b) => b.scores.impact + b.scores.novelty + b.scores.speed - (b.scores.effort + b.scores.risk) - (a.scores.impact + a.scores.novelty + a.scores.speed - (a.scores.effort + a.scores.risk)));
      return list.slice(0, Number(q.limit) || 40).map(ideaBrief);
    }
    case "/idea": {
      if (method === "POST") {   // создание идеи
        if (!body.title) throw new Error("Нужно название идеи");
        const st0 = state();
        const projectId = body.projectId || (st0.projects || [])[0]?.id;
        if (!projectId) throw new Error("В приложении нет ни одного проекта");
        const res = await agentAsk("idea", {
          projectId, title: body.title, question: body.question || "", method: body.method || "", validation: body.validation || "",
        });
        agentNote(`агент завёл идею «${body.title}»`);
        return { ok: true, ...res };
      }
      const found = findIdea(q);
      if (!found) return { error: "Идея не найдена. Посмотри fly_list_ideas." };
      const st = state();
      const refs = new Map((st.references || []).map((r) => [r.id, r]));
      const project = (st.projects || []).find((p) => p.id === found.projectId);
      return {
        ...checkedIdea(found),
        проект: project ? { id: project.id, name: project.name } : null,
        чеклист: found.checklist.map((c) => ({ текст: c.text, сделано: c.done, дата: c.doneAt || null })),
        журнал: found.experiments.map((e) => ({ id: e.id, дата: e.date, что: e.title, параметры: e.params, результат: e.result, вывод: e.conclusion, исход: e.outcome })),
        источники: found.citations.map((c) => ({ refId: c.refId, зачем: c.why, ссылка: refs.get(c.refId) || null })),
        связи: (found.dependsOn || []).map((id) => ({ id, title: (st.ideas || []).find((i) => i.id === id)?.title || "?" })),
      };
    }
    case "/idea/patch": {
      if (!body.id) throw new Error("Нужен id идеи");
      const found = findIdea({ id: body.id });
      if (!found) throw new Error("Идея не найдена");
      const allowed = ["status", "question", "method", "validation", "notes", "deadline", "tags", "scores", "timeline", "venues"];
      const patch = {};
      for (const [k, v] of Object.entries(body.patch || {})) if (allowed.includes(k)) patch[k] = v;
      if (!Object.keys(patch).length) throw new Error("Нечего менять: допустимые поля " + allowed.join(", "));
      const res = await agentAsk("ideaPatch", { id: found.id, patch });
      agentNote(`агент поправил идею «${found.title}» (${Object.keys(patch).join(", ")})`);
      return { ok: true, ...res };
    }
    case "/library": {
      let list = state().references || [];
      if (q.tag) list = list.filter((r) => r.tags.includes(q.tag));
      if (q.query) {
        const needle = String(q.query).toLowerCase();
        list = list.filter((r) => (r.authors + " " + r.title + " " + r.venue + " " + r.doi + " " + r.tags.join(" ") + " " + r.notes).toLowerCase().includes(needle));
      }
      return list.slice(0, Number(q.limit) || 40).map((r) => ({ id: r.id, авторы: r.authors, год: r.year, название: r.title, журнал: r.venue, doi: r.doi, url: r.url, метки: r.tags, конспект: r.notes }));
    }
    case "/scripts": {
      const ws = projectPaths(q.projectId);
      const files = (await fsp.readdir(ws.code, { withFileTypes: true })).filter((f) => f.isFile() && f.name.endsWith(".py"));
      const out = [];
      for (const f of files) {
        const full = path.join(ws.code, f.name);
        const st = await fsp.stat(full);
        let doc = "";
        try {
          const head = (await fsp.readFile(full, "utf8")).split("\n").slice(0, 12).join(" ").replace(/"/g, "'");
          doc = (head.match(/"""(.+?)"""/) || head.match(/^#\s*(.+)/m) || ["", ""])[1].slice(0, 200);
        } catch {}
        out.push({ имя: f.name, описание: doc.trim(), размер: st.size, изменён: new Date(st.mtimeMs).toISOString() });
      }
      return { папка: ws.code, папкаПрогонов: ws.runs, файлы: out.sort((a, b) => a.имя.localeCompare(b.имя)) };
    }
    case "/script": {
      const ws = projectPaths(q.projectId);
      const file = path.join(ws.code, path.basename(q.name));
      if (!within(ws.code, file)) throw new Error("Скрипт вне папки проекта");
      return { имя: path.basename(q.name), код: await fsp.readFile(file, "utf8") };
    }
    case "/runs": {
      const ws = projectPaths(q.projectId);
      const entries = await fsp.readdir(ws.runs, { withFileTypes: true }).catch(() => []);
      const dirs = entries.filter((d) => d.isDirectory()).map((d) => d.name).sort().reverse().slice(0, Number(q.limit) || 20);
      const out = [];
      for (const d of dirs) {
        const full = path.join(ws.runs, d);
        let summary = null;
        try { summary = JSON.parse(await fsp.readFile(path.join(full, "summary.json"), "utf8")); } catch {}
        const files = await fsp.readdir(full).catch(() => []);
        const st = await fsp.stat(full).catch(() => null);
        out.push({ папка: full, когда: st ? new Date(st.mtimeMs).toISOString() : null, файлы: files, сводка: summary });
      }
      return { папкаПрогонов: ws.runs, прогоны: out };
    }
    case "/run": {
      if (q.dir) {  // GET: чтение итога
        if (!withinRuns(q.dir)) throw new Error("Папка вне каталога прогонов");
        const out = { папка: q.dir, файлы: await fsp.readdir(q.dir).catch(() => []) };
        try { out.сводка = JSON.parse(await fsp.readFile(path.join(q.dir, "summary.json"), "utf8")); } catch { out.сводка = null; }
        try { out.лог = (await fsp.readFile(path.join(q.dir, "log.txt"), "utf8")).slice(-8000); } catch { out.лог = ""; }
        return out;
      }
      // POST: запуск
      if (!body.script) throw new Error("Нужно имя скрипта");
      const started = await runScript(win(), body.projectId, body.script, body.args || []);
      agentNote(`агент запустил ${path.basename(body.script)}`);
      return { ...started, подсказка: "итог забирай через fly_wait_run или fly_read_run" };
    }
    case "/run/status": {
      const st = runStatus.get(q.runId);
      return { runId: q.runId, running: runs.has(q.runId), dir: st?.dir || null, код: st?.code ?? null, завершён: st?.finishedAt ?? null };
    }
    case "/kill": {
      const p = runs.get(body.runId);
      if (!p) throw new Error("Прогон не найден или уже завершён");
      p.kill();
      agentNote(`агент остановил прогон ${body.runId}`);
      return { ok: true };
    }
    case "/journal": {
      const idea = findIdea({ id: body.ideaId });
      if (!idea) throw new Error("Идея не найдена: посмотри fly_list_ideas");
      const res = await agentAsk("journal", {
        ideaId: idea.id, title: body.title || "запись агента", params: body.params || "",
        result: body.result || "", conclusion: body.conclusion || "", outcome: body.outcome || "inconclusive",
      });
      agentNote(`агент добавил запись в журнал идеи «${idea.title}»`);
      return { ok: true, идея: idea.title, ...res };
    }
    case "/reference": {
      if (!body.title) throw new Error("Нужно название источника");
      const res = await agentAsk("reference", body);
      agentNote(`агент добавил источник «${String(body.title).slice(0, 60)}»`);
      return { ok: true, ...res };
    }
    case "/data": {
      const dir = getDirs().data;
      const items = await fsp.readdir(dir, { withFileTypes: true }).catch(() => []);
      const out = [];
      for (const it of items) {
        const full = path.join(dir, it.name);
        if (it.isDirectory()) {
          const inside = await fsp.readdir(full).catch(() => []);
          out.push({ имя: it.name + "/", файлов: inside.length, примеры: inside.slice(0, 5) });
        } else {
          const st = await fsp.stat(full).catch(() => null);
          out.push({ имя: it.name, МБ: st ? +(st.size / 1048576).toFixed(1) : null });
        }
      }
      return { папка: dir, содержимое: out };
    }
    default:
      throw new Error("Неизвестный маршрут " + route);
  }
}

function checkedIdea(i) {
  return {
    id: i.id, title: i.title, status: i.status, вопрос: i.question, метод: i.method,
    валидация: i.validation, заметки: i.notes, оценки: i.scores, срок: i.deadline,
    срокиОценка: i.timeline, метки: i.tags, журналы: i.venues,
    ссылки: i.links, создана: i.createdAt, изменена: i.updatedAt,
  };
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let b = "";
    req.on("data", (c) => {
      b += c;
      if (b.length > 2_000_000) req.destroy();
    });
    req.on("end", () => {
      try { resolve(b ? JSON.parse(b) : {}); } catch (e) { reject(e); }
    });
    req.on("error", reject);
  });
}

function startAgentServer() {
  if (AGENT.server || !agentEnabled()) return;
  AGENT.server = http.createServer(async (req, res) => {
    const json = (code, data) => {
      res.writeHead(code, { "Content-Type": "application/json; charset=utf-8" });
      res.end(JSON.stringify(data));
    };
    const url = new URL(req.url, "http://127.0.0.1");
    if (!url.pathname.startsWith("/api/")) return json(404, { error: "Есть только /api/*" });
    const header = req.headers.authorization || "";
    const token = header.startsWith("Bearer ") ? header.slice(7) : url.searchParams.get("token") || "";
    if (token !== AGENT.token) return json(401, { error: "Неверный токен. Возьми его из agent.json." });
    try {
      const q = Object.fromEntries(url.searchParams.entries());
      const body = req.method === "POST" ? await readBody(req) : {};
      assertNotSyncing();
      agentRequestsInFlight++;
      try { json(200, await agentRoute(url.pathname.replace(/^\/api/, ""), q, body, req.method)); }
      finally { agentRequestsInFlight--; }
    } catch (e) {
      json(400, { error: String(e.message || e) });
    }
  });
  AGENT.server.on("error", (e) => {
    console.error("мост агента не поднялся:", e.message);
    AGENT.server = null;
  });
  AGENT.server.listen(0, "127.0.0.1", () => {
    AGENT.port = AGENT.server.address().port;
    try {
      fs.mkdirSync(path.dirname(AGENT_FILE), { recursive: true });
      fs.writeFileSync(AGENT_FILE, JSON.stringify({
        app: "fly-ideas", port: AGENT.port, token: AGENT.token, pid: process.pid,
        url: `http://127.0.0.1:${AGENT.port}`, mcp: MCP_SERVER,
        startedAt: new Date().toISOString(),
      }, null, 2), { mode: 0o600 });
    } catch (e) {
      console.error("не смог записать agent.json:", e.message);
    }
  });
}
function stopAgentServer() {
  AGENT.server?.close();
  AGENT.server = null;
  AGENT.port = 0;
  try { fs.rmSync(AGENT_FILE, { force: true }); } catch {}
}

// ------------------------------------------------------------
// IPC
// ------------------------------------------------------------
function registerIpc(getWin) {
  const mutations = new Set(["fly:writeScript", "fly:writeAssistantScript", "fly:deleteScript", "fly:transferRun", "fly:syncTemplates", "fly:chooseProjectFolder", "fly:resetProjectFolder", "fly:chooseDataFile", "fly:clearDataFile", "fly:chooseFolder", "fly:resetFolder"]);
  const handle = (name, fn) => ipcMain.handle(name, mutations.has(name) ? async (...args) => {
    assertNotSyncing(); mutationsInFlight++;
    try { return await fn(...args); } finally { mutationsInFlight--; }
  } : fn);

  // Снимки находятся в локальной папке Google Drive for desktop, а не передаются через Google API.
  const backupRoot = path.join(app.getPath("userData"), "sync-backups");
  const runtime = () => ({
    dataDir: DIRS.data,
    getLinks: dataFileLinks,
    projectPaths: (id) => {
      const scope = parseScope(id), override = (readConfig().projectDirs || {})[scope.cfgKey] || {};
      return { code: typeof override.code === "string" ? override.code : scope.defaults.code,
        runs: typeof override.runs === "string" ? override.runs : scope.defaults.runs };
    },
  });
  const sharedRoot = () => {
    const selected = readConfig().syncFolder;
    if (!selected || typeof selected !== "string") throw new Error("Сначала выберите папку Google Диска.");
    const info = fs.lstatSync(selected);
    if (!info.isDirectory() || info.isSymbolicLink()) throw new Error("Папка Google Диска недоступна или является ссылкой.");
    return path.join(selected, "FlyIdeas-sync", "snapshots");
  };
  const progress = (data) => { const win = getWin(); if (win && !win.isDestroyed?.()) win.webContents.send("fly:syncProgress", data); };
  handle("fly:syncInfo", async () => {
    const folder = readConfig().syncFolder || "";
    let shared = [], error = "";
    if (folder) { try { shared = await folderSync.listSnapshots(sharedRoot()); } catch (e) { error = e.message; } }
    const backups = await folderSync.listSnapshots(backupRoot);
    return { folder, shared, backups, backupRoot, error };
  });
  handle("fly:chooseSyncFolder", async () => {
    assertNotSyncing();
    const r = await dialog.showOpenDialog(getWin(), { title: "Выберите синхронизируемую папку Google Диска", properties: ["openDirectory", "createDirectory"] });
    if (r.canceled || !r.filePaths[0]) return null;
    const c = readConfig(); c.syncFolder = r.filePaths[0]; writeConfig(c); return c.syncFolder;
  });
  handle("fly:syncUpload", (_e, ui, includeData) => withSyncLock(async () => {
    return folderSync.createSnapshot(sharedRoot(), runtime(), ui, readApiCallStore(), !!includeData, { progress });
  }));
  handle("fly:syncRestore", (_e, source, id, ui) => withSyncLock(async () => {
    if (source !== "shared" && source !== "backup") throw new Error("Неизвестный источник снимка.");
    const result = await folderSync.restoreSnapshot(source === "shared" ? sharedRoot() : backupRoot, id, runtime(), ui, readApiCallStore(), backupRoot, progress, source === "backup");
    try {
      const temp = `${API_CALLS_FILE}.${process.pid}.sync.tmp`;
      await fsp.mkdir(path.dirname(API_CALLS_FILE), { recursive: true });
      try { await fsp.writeFile(temp, JSON.stringify(result.apiCalls, null, 2)); await fsp.rename(temp, API_CALLS_FILE); }
      finally { await fsp.rm(temp, { force: true }).catch(() => {}); }
      if (result.includeData) {
        const c = readConfig(); c.dataFiles = result.linked;
        const tempConfig = `${CONFIG}.${process.pid}.sync.tmp`;
        try { await fsp.writeFile(tempConfig, JSON.stringify(c, null, 2)); await fsp.rename(tempConfig, CONFIG); }
        finally { await fsp.rm(tempConfig, { force: true }).catch(() => {}); }
      }
    } catch (e) { throw new Error(`Не удалось применить журнал или пути данных. Локальная резервная копия: ${result.backup.path}. ${e.message}`); }
    syncAwaitingReload = true;
    return result;
  }));
  handle("fly:syncFinish", (_e, reload) => {
    if (!syncAwaitingReload) throw new Error("Нет ожидающего восстановления.");
    syncAwaitingReload = false; syncBusy = false;
    if (reload) getWin().webContents.reload();
  });

  handle("fly:getPaths", () => ({ workspace: WS, ...getDirs(), defaults: DEFAULT_DIRS, templates: TEMPLATES }));
  handle("fly:getDataFileLinks", () => dataFileLinks());
  handle("fly:chooseDataFile", async (_e, role) => {
    assertNotSyncing();
    if (!Object.hasOwn(DATA_FILE_ROLES, role)) throw new Error("Неизвестный тип файла данных.");
    const titles = { connections: "Выберите таблицу связей", annotations: "Выберите классификацию нейронов", cell_types: "Выберите таблицу типов клеток", neurotransmitters: "Выберите таблицу нейромедиаторов" };
    const r = await dialog.showOpenDialog(getWin(), {
      title: titles[role],
      defaultPath: getDirs().data,
      properties: ["openFile"],
      filters: [{ name: "Таблицы CSV, TSV, GZIP, Parquet", extensions: ["csv", "tsv", "gz", "parquet"] }],
    });
    if (r.canceled || !r.filePaths[0]) return dataFileLinks();
    const file = r.filePaths[0];
    if (!/\.(csv|tsv|csv\.gz|tsv\.gz|parquet)$/i.test(file)) throw new Error("Выберите таблицу CSV, TSV, CSV.GZ, TSV.GZ или Parquet.");
    const info = await fsp.stat(file);
    if (!info.isFile()) throw new Error("Выберите обычный файл таблицы.");
    await fsp.access(file, fs.constants.R_OK);
    const c = readConfig();
    c.dataFiles = { ...(c.dataFiles || {}), [role]: file };
    writeConfig(c);
    return dataFileLinks();
  });
  handle("fly:clearDataFile", (_e, role) => {
    assertNotSyncing();
    if (!Object.hasOwn(DATA_FILE_ROLES, role)) throw new Error("Неизвестный тип файла данных.");
    const c = readConfig();
    if (c.dataFiles) delete c.dataFiles[role];
    writeConfig(c);
    return dataFileLinks();
  });

  // --- выбор папок ---
  handle("fly:chooseFolder", async (_e, kind, title) => {
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
  handle("fly:pickFolder", async (_e, title) => {
    const r = await dialog.showOpenDialog(getWin(), { title: title || "Выбери папку", properties: ["openDirectory", "createDirectory"] });
    return r.canceled ? null : r.filePaths[0];
  });
  handle("fly:resetFolder", (_e, kind) => {
    const c = readConfig();
    if (c.dirs) delete c.dirs[kind];
    writeConfig(c);
    ensureDirs();
    return getDirs()[kind];
  });

  // --- сохранить / открыть файл через системный диалог ---
  handle("fly:saveFile", async (_e, { defaultName, content, filters, kind }) => {
    const dir = getDirs()[kind || "exports"] || app.getPath("documents");
    const r = await dialog.showSaveDialog(getWin(), { defaultPath: path.join(dir, defaultName || "file.txt"), filters: filters || [{ name: "Все файлы", extensions: ["*"] }] });
    if (r.canceled || !r.filePath) return null;
    await fsp.writeFile(r.filePath, content, "utf8");
    const c = readConfig();
    c.dirs = { ...(c.dirs || {}), exports: path.dirname(r.filePath) };
    writeConfig(c);
    return r.filePath;
  });
  handle("fly:openFile", async (_e, { filters, kind }) => {
    const dir = getDirs()[kind || "exports"] || app.getPath("documents");
    const r = await dialog.showOpenDialog(getWin(), { defaultPath: dir, filters: filters || [{ name: "Все файлы", extensions: ["*"] }], properties: ["openFile"] });
    if (r.canceled || !r.filePaths[0]) return null;
    return { path: r.filePaths[0], content: await fsp.readFile(r.filePaths[0], "utf8") };
  });
  handle("fly:checkEnv", () => checkEnv());
  handle("fly:listPythons", () => listPythons());
  handle("fly:setPython", async (_e, pyCmd) => {
    const c = readConfig();
    if (pyCmd && String(pyCmd).trim()) c.pythonPath = String(pyCmd).trim();
    else delete c.pythonPath;
    writeConfig(c);
    return checkEnv();
  });
  handle("fly:pickPythonExe", async () => {
    const r = await dialog.showOpenDialog(getWin(), {
      title: "Выбери интерпретатор Python (python.exe)",
      filters: process.platform === "win32" ? [{ name: "Python", extensions: ["exe"] }] : [{ name: "Все файлы", extensions: ["*"] }],
      properties: ["openFile"],
    });
    if (r.canceled || !r.filePaths[0]) return null;
    const chosen = r.filePaths[0];
    const probed = await probePythonCandidate({ cmd: chosen, source: "selected", note: "выбран вручную" });
    if (!probed) throw new Error("Выбранный файл не является рабочим интерпретатором Python 3.");
    const c = readConfig();
    c.pythonPath = chosen;
    writeConfig(c);
    return checkEnv();
  });
  handle("fly:setupPythonEnv", async (_e, mode) => { assertNotSyncing(); environmentInFlight++; try { return await setupPythonEnv(getWin(), mode || "core"); } finally { environmentInFlight--; } });
  handle("fly:openPath", (_e, p) => shell.openPath(p));
  handle("fly:openExternal", (_e, url) => shell.openExternal(url));

  handle("fly:listData", async () => {
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
  handle("fly:download", async (_e, item, destDir) => { assertNotSyncing(); downloadsInFlight++; try { return await download(getWin(), item, destDir); } finally { activeDownloads.delete(item.id); downloadsInFlight--; } });
  handle("fly:listExternal", () => EXTERNAL_SOURCES);
  handle("fly:cancelDownload", (_e, id) => { activeDownloads.get(id)?.destroy(); activeDownloads.delete(id); });

  // --- рабочее место проекта: папки кода и прогонов ---
  handle("fly:projectPaths", (_e, projectId) => projectPaths(projectId));
  handle("fly:chooseProjectFolder", async (_e, projectId, kind, title) => {
    assertNotSyncing();
    const r = await dialog.showOpenDialog(getWin(), {
      title: title || "Выбери папку проекта",
      defaultPath: projectPaths(projectId)[kind === "runs" ? "runs" : "code"],
      properties: ["openDirectory", "createDirectory"],
    });
    if (r.canceled || !r.filePaths[0]) return null;
    return setProjectDir(projectId, kind === "runs" ? "runs" : "code", r.filePaths[0]);
  });
  handle("fly:resetProjectFolder", (_e, projectId, kind) => { assertNotSyncing(); return setProjectDir(projectId, kind === "runs" ? "runs" : "code", null); });
  handle("fly:getPermissions", () => getPermissions());
  handle("fly:setPermissions", (_e, patch) => setPermissions(patch || {}));

  handle("fly:listScripts", async (_e, projectId) => {
    const ws = projectPaths(projectId);
    const files = (await fsp.readdir(ws.code)).filter((f) => f.endsWith(".py")).sort();
    return Promise.all(files.map(async (f) => {
      const full = path.join(ws.code, f);
      const txt = await fsp.readFile(full, "utf8");
      const m = txt.match(/^(?:#![^\n]*\n)?"""\s*\n?([\s\S]*?)"""/);
      const st = await fsp.stat(full);
      return { name: f, doc: m ? m[1].trim().split("\n")[0] : "", size: st.size, mtime: st.mtimeMs };
    }));
  });
  handle("fly:syncTemplates", (_e, projectId, opts) => {
    assertNotSyncing();
    const ws = projectPaths(projectId);
    const includeAll = !!(opts && opts.all);
    if (opts && opts.overwrite) {
      const scope = parseScope(projectId);
      const allowed = allowedTemplatesForScope(scope, includeAll);
      const copied = copyTemplates(ws.code, { overwrite: true, only: allowed ? Array.from(allowed) : null });
      return { added: copied, code: ws.code };
    }
    const added = syncProjectTemplates(projectId, ws.code, true, includeAll);
    return { added, code: ws.code };
  });
  handle("fly:readScript", (_e, projectId, name) => {
    const ws = projectPaths(projectId);
    const full = path.join(ws.code, path.basename(name));
    if (!within(ws.code, full)) throw new Error("Файл вне папки проекта.");
    return fsp.readFile(full, "utf8");
  });
  handle("fly:writeScript", async (_e, projectId, name, content, opts) => {
    assertNotSyncing();
    const ws = projectPaths(projectId);
    const perms = getPermissions();
    const base = path.basename(name).replace(/[^\w.-]+/g, "_");
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
  handle("fly:writeAssistantScript", (_e, projectId, name, content, opts) => {
    assertNotSyncing();
    const ws = projectPaths(projectId);
    return writeAssistantFile({ codeDir: ws.code, expectedDir: opts?.expectedDir, name, content, permissions: getPermissions, expectedContent: opts?.expectedContent });
  });
  handle("fly:deleteScript", async (_e, projectId, name) => {
    assertNotSyncing();
    const ws = projectPaths(projectId);
    const full = path.join(ws.code, path.basename(name));
    if (!within(ws.code, full)) throw new Error("Файл вне папки проекта.");
    await fsp.rm(full, { force: true });
    return true;
  });
  handle("fly:runScript", (_e, projectId, name, args) => runScript(getWin(), projectId, path.basename(name), args));
  handle("fly:killRun", (_e, runId) => { runs.get(runId)?.kill(); });

  handle("fly:getSecret", (_e, k) => { const s = readSecrets(); return s[k] ? `${s[k].slice(0, 6)}…${s[k].slice(-4)}` : null; });
  handle("fly:setSecret", (_e, k, v) => { const s = readSecrets(); if (v) s[k] = v; else delete s[k]; writeSecrets(s); return true; });
  handle("fly:llmChat", async (_e, req) => { assertNotSyncing(); llmInFlight++; try { return await llmChat(req); } finally { llmInFlight--; llmSettledAt = Date.now(); } });
  handle("fly:listApiCalls", (_e, workspaceId) => listApiCalls(workspaceId));
  handle("fly:appendApiCall", (_e, workspaceId, record) => { assertNotSyncing(); return appendApiCall(workspaceId, record); });

  handle("fly:listRuns", async (_e, projectId) => {
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
  handle("fly:readRunFile", async (_e, dir, name) => {
    const p = path.join(dir, path.basename(name));
    if (!withinRuns(p)) throw new Error("Файл вне папки прогонов.");
    const ext = path.extname(name).toLowerCase();
    if ([".png", ".jpg", ".jpeg", ".svg", ".gif"].includes(ext)) {
      const mime = ext === ".svg" ? "image/svg+xml" : ext === ".png" ? "image/png" : ext === ".gif" ? "image/gif" : "image/jpeg";
      return { kind: "image", dataUrl: `data:${mime};base64,${(await fsp.readFile(p)).toString("base64")}` };
    }
    const st = await fsp.stat(p);
    if (st.size > 400_000) return { kind: "text", text: `(файл ${(st.size / 1e6).toFixed(1)} МБ — открой в папке)` };
    return { kind: "text", text: await fsp.readFile(p, "utf8") };
  });
  handle("fly:exportRun", async (_e, dir) => {
    const src = dir;
    if (!withinRuns(src)) throw new Error("Папка вне каталога прогонов.");
    const dest = await dialog.showOpenDialog(getWin(), { title: "Куда скопировать прогон", properties: ["openDirectory", "createDirectory"] });
    if (dest.canceled || !dest.filePaths[0]) return null;
    const target = path.join(dest.filePaths[0], path.basename(dir));
    await fsp.cp(src, target, { recursive: true });
    return target;
  });
  handle("fly:transferRun", async (_e, dir, targetProjectId, opts) => {
    assertNotSyncing();
    const src = String(dir || "");
    if (!withinRuns(src)) throw new Error("Папка вне каталога прогонов.");
    const dstWs = projectPaths(targetProjectId);
    let baseName = path.basename(src);
    let target = path.join(dstWs.runs, baseName);
    if (path.resolve(src) === path.resolve(target)) {
      return { path: target, label: baseName, projectId: dstWs.projectId };
    }
    const origBase = baseName;
    let copyIdx = 1;
    while (fs.existsSync(target)) {
      baseName = copyIdx === 1 ? `${origBase}_copy` : `${origBase}_copy${copyIdx}`;
      copyIdx++;
      target = path.join(dstWs.runs, baseName);
    }
    await fsp.cp(src, target, { recursive: true });
    if (opts && opts.move) {
      await fsp.rm(src, { recursive: true, force: true });
    }
    return { path: target, label: baseName, projectId: dstWs.projectId };
  });
  handle("fly:syncState", (_e, st) => {
    AGENT.state = st && typeof st === "object" ? st : null;
    AGENT.syncedAt = Date.now();
    writeSnapshot();
    return true;
  });
  handle("fly:agentAck", (_e, reqId, result) => agentAck(reqId, result));
  handle("fly:agentInfo", () => ({
    enabled: agentEnabled(), running: !!AGENT.server, port: AGENT.port,
    url: AGENT.server ? `http://127.0.0.1:${AGENT.port}` : null,
    file: AGENT_FILE, token: AGENT.token,
    mcp: MCP_SERVER,
    syncedAt: AGENT.syncedAt || null,
    ideas: (state().ideas || []).length, projects: (state().projects || []).length,
  }));
  handle("fly:setAgentEnabled", (_e, on) => {
    const c = readConfig();
    c.agentEnabled = !!on;
    writeConfig(c);
    if (on) startAgentServer();
    else stopAgentServer();
    return { enabled: agentEnabled(), running: !!AGENT.server, port: AGENT.port };
  });
  handle("fly:readRun", async (_e, dir) => {
    const p = dir;
    if (!withinRuns(p)) throw new Error("Папка вне каталога прогонов.");
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
  startAgentServer();
  app.on("activate", () => BrowserWindow.getAllWindows().length === 0 && createWindow());
});
app.on("window-all-closed", () => process.platform !== "darwin" && app.quit());
app.on("before-quit", () => stopAgentServer());
