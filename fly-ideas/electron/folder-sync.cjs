const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const crypto = require('node:crypto');

const ROLES = ['connections', 'annotations', 'cell_types', 'neurotransmitters'];
const SKIP_DIRS = new Set(['.git', '.venv', 'node_modules', '__pycache__']);
const SKIP_FILES = new Set(['secrets.json', '.env']);
const ID_RE = /^[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,119}$/;
const SNAP_RE = /^\d{8}T\d{6}Z-[a-f0-9]{16}$/;

function scopesFor(ui) {
  const state = ui?.state;
  if (!state || state.version !== 1 || !Array.isArray(state.projects) || !Array.isArray(state.ideas) || !Array.isArray(state.references)) throw new Error('Некорректное состояние идей.');
  if (!ui.chats || typeof ui.chats !== 'object' || Array.isArray(ui.chats)) throw new Error('Некорректная история чатов.');
  for (const [key, value] of Object.entries(ui.chats)) {
    if (!key.startsWith('fly-ideas:chat:') || typeof value !== 'string' || !Array.isArray(JSON.parse(value))) throw new Error('Некорректная история чата.');
  }
  if (ui.rates !== null && typeof ui.rates !== 'string') throw new Error('Некорректные тарифы API.');
  if (ui.rates !== null) JSON.parse(ui.rates);
  const ids = (items, prefix) => items.map((item) => {
    if (!item || typeof item.id !== 'string' || !ID_RE.test(item.id) || item.id.includes('..') || /^-|-$/.test(item.id) || !safeRel(item.id) || (!prefix && item.id.startsWith('idea__'))) throw new Error('Недопустимый идентификатор идеи или проекта.');
    return prefix + item.id;
  });
  const all = [...ids(state.projects, ''), ...ids(state.ideas, 'idea:')];
  if (new Set(all.map((s) => s.toLowerCase())).size !== all.length) throw new Error('Повторяющиеся идентификаторы рабочих пространств.');
  return all;
}

function safeRel(rel) {
  if (typeof rel !== 'string' || !rel || rel.length > 2048 || rel.includes('\\') || rel.includes(':') || rel.startsWith('/')) return false;
  return rel.split('/').every((part) => part && part !== '.' && part !== '..' && !/[\x00-\x1f<>"|?*]/.test(part) && !/[. ]$/.test(part) && !/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(part));
}

function overlaps(a, b) {
  const left = path.resolve(a), right = path.resolve(b);
  const inside = (parent, child) => { const rel = path.relative(parent, child); return rel === '' || (!rel.startsWith('..' + path.sep) && rel !== '..' && !path.isAbsolute(rel)); };
  return inside(left, right) || inside(right, left);
}

async function hashFile(file) {
  const hash = crypto.createHash('sha256');
  for await (const chunk of fs.createReadStream(file)) hash.update(chunk);
  return hash.digest('hex');
}

async function validateDirectoryPath(dir) {
  const absolute = path.resolve(dir), parsed = path.parse(absolute);
  let current = parsed.root;
  for (const part of absolute.slice(parsed.root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    const stat = await fsp.lstat(current);
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error(`Путь содержит ссылку или не является папкой: ${current}`);
  }
}

async function regularFile(file) {
  await validateDirectoryPath(path.dirname(file));
  const stat = await fsp.lstat(file);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error(`Недоступен обычный файл: ${file}`);
  return stat;
}

async function walk(root, output, kind, scope) {
  let info;
  try { info = await fsp.lstat(root); } catch (e) { if (e.code === 'ENOENT') return; throw e; }
  if (!info.isDirectory() || info.isSymbolicLink()) throw new Error(`Папка недоступна или является ссылкой: ${root}`);
  await validateDirectoryPath(root);
  async function visit(dir, prefix = '') {
    const entries = await fsp.readdir(dir, { withFileTypes: true });
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      if (entry.isSymbolicLink()) throw new Error(`Ссылки внутри синхронизируемых папок не поддерживаются: ${path.join(dir, entry.name)}`);
      const rel = prefix ? `${prefix}/${entry.name}` : entry.name;
      if (!safeRel(rel)) throw new Error(`Имя файла несовместимо с Windows: ${rel}`);
      if (entry.isDirectory()) { if (!SKIP_DIRS.has(entry.name.toLowerCase())) await visit(path.join(dir, entry.name), rel); }
      else if (entry.isFile() && !SKIP_FILES.has(entry.name.toLowerCase())) output.push({ kind, scope, rel, source: path.join(dir, entry.name) });
    }
  }
  await visit(root);
}

function makeId() { return `${new Date().toISOString().replace(/[-:]/g, '').slice(0, 15)}Z-${crypto.randomBytes(8).toString('hex')}`; }

async function collect(runtime, ui, includeData, extraScopes = []) {
  const scopes = [...new Set([...scopesFor(ui), ...extraScopes])];
  const sources = [];
  const roots = [];
  for (const scope of scopes) {
    const p = await runtime.projectPaths(scope);
    for (const kind of ['code', 'runs']) {
      roots.push(p[kind]);
      await walk(p[kind], sources, kind, scope);
    }
  }
  if (includeData) {
    roots.push(runtime.dataDir);
    await walk(runtime.dataDir, sources, 'data', null);
    const links = await runtime.getLinks();
    for (const role of ROLES) {
      const file = links[role]?.path;
      if (!file) continue;
      await regularFile(file);
      const name = path.basename(file);
      if (!safeRel(name) || SKIP_FILES.has(name.toLowerCase())) throw new Error(`Недопустимое имя подключённого файла: ${name}`);
      sources.push({ kind: 'linked', scope: role, rel: name, source: file });
      roots.push(file);
    }
  }
  return { sources, roots };
}

async function createSnapshot(root, runtime, ui, apiCalls, includeData, { extraScopes = [], kind = 'shared', progress = () => {} } = {}) {
  scopesFor(ui);
  if (!apiCalls || typeof apiCalls !== 'object' || Array.isArray(apiCalls)) throw new Error('Некорректный журнал API.');
  const { sources, roots } = await collect(runtime, ui, includeData, extraScopes);
  if (roots.some((source) => overlaps(root, source))) throw new Error('Папка синхронизации или резервных копий пересекается с папкой данных, кода или результатов. Выберите другую папку.');
  await ensureDirectory(root);
  const id = makeId();
  const temp = path.join(root, `.partial-${id}`), final = path.join(root, id);
  await fsp.mkdir(path.join(temp, 'files'), { recursive: true });
  try {
    const entries = [];
    for (let i = 0; i < sources.length; i++) {
      const item = sources[i], fileId = String(i).padStart(8, '0');
      progress({ phase: 'copy', done: i, total: sources.length, file: item.rel });
      const before = await regularFile(item.source);
      const dest = path.join(temp, 'files', fileId);
      await fsp.copyFile(item.source, dest, fs.constants.COPYFILE_EXCL);
      const [hash, originalHash, after] = await Promise.all([hashFile(dest), hashFile(item.source), regularFile(item.source)]);
      if (before.size !== after.size || before.mtimeMs !== after.mtimeMs || hash !== originalHash) throw new Error(`Файл изменился во время копирования: ${item.source}. Сохраните изменения и повторите.`);
      entries.push({ id: fileId, kind: item.kind, scope: item.scope, rel: item.rel, size: before.size, sha256: hash });
    }
    progress({ phase: 'finish', done: sources.length, total: sources.length, file: '' });
    const payload = JSON.stringify({ ui, apiCalls });
    await fsp.writeFile(path.join(temp, 'payload.json'), payload, 'utf8');
    const payloadHash = crypto.createHash('sha256').update(payload).digest('hex');
    const manifest = { version: 1, id, createdAt: new Date().toISOString(), kind, includeData: !!includeData, extraScopes, fileCount: entries.length, payloadHash, files: entries };
    await fsp.writeFile(path.join(temp, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');
    await fsp.rename(temp, final);
    return { id, createdAt: manifest.createdAt, includeData: manifest.includeData, fileCount: entries.length, path: final };
  } catch (error) {
    await fsp.rm(temp, { recursive: true, force: true }).catch(() => {});
    throw error;
  }
}

async function listSnapshots(root) {
  let dirs;
  try { dirs = await fsp.readdir(root, { withFileTypes: true }); } catch (e) { if (e.code === 'ENOENT') return []; throw e; }
  const result = [];
  for (const dir of dirs) {
    if (!dir.isDirectory() || dir.isSymbolicLink() || !SNAP_RE.test(dir.name)) continue;
    try {
      const p = path.join(root, dir.name, 'manifest.json');
      await regularFile(p);
      const m = JSON.parse(await fsp.readFile(p, 'utf8'));
      if (m.version === 1 && m.id === dir.name && Array.isArray(m.files) && typeof m.createdAt === 'string') result.push({ id: m.id, createdAt: m.createdAt, includeData: !!m.includeData, fileCount: m.files.length, kind: m.kind });
    } catch { /* Неполная синхронизация или повреждённый снимок. */ }
  }
  return result.sort((a, b) => b.createdAt.localeCompare(a.createdAt) || b.id.localeCompare(a.id));
}

async function ensureDirectory(dir) {
  const absolute = path.resolve(dir);
  const parsed = path.parse(absolute);
  let current = parsed.root;
  for (const part of absolute.slice(parsed.root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    try { await fsp.mkdir(current); } catch (e) { if (e.code !== 'EEXIST') throw e; }
    const stat = await fsp.lstat(current);
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw new Error(`Путь содержит ссылку или не является папкой: ${current}`);
  }
}

async function safeDestination(root, rel) {
  if (!safeRel(rel)) throw new Error(`Недопустимый путь в снимке: ${rel}`);
  const rootInfo = await fsp.lstat(root);
  if (!rootInfo.isDirectory() || rootInfo.isSymbolicLink()) throw new Error(`Папка назначения является ссылкой или недоступна: ${root}`);
  const parts = rel.split('/');
  let dir = root;
  for (const part of parts.slice(0, -1)) {
    dir = path.join(dir, part);
    try { await fsp.mkdir(dir); } catch (e) { if (e.code !== 'EEXIST') throw e; }
    const s = await fsp.lstat(dir);
    if (!s.isDirectory() || s.isSymbolicLink()) throw new Error(`Путь назначения содержит ссылку: ${dir}`);
  }
  const dest = path.join(dir, parts.at(-1));
  try { const s = await fsp.lstat(dest); if (!s.isFile() || s.isSymbolicLink()) throw new Error(`Недопустимый файл назначения: ${dest}`); } catch (e) { if (e.code !== 'ENOENT') throw e; }
  return dest;
}

async function readSnapshot(root, id, runtime, progress = () => {}, allowBackupScopes = false) {
  const rootInfo = await fsp.lstat(root);
  if (!rootInfo.isDirectory() || rootInfo.isSymbolicLink()) throw new Error('Папка снимков недоступна или является ссылкой.');
  await validateDirectoryPath(root);
  if (!SNAP_RE.test(id)) throw new Error('Недопустимый идентификатор снимка.');
  const dir = path.join(root, id);
  const dirStat = await fsp.lstat(dir);
  if (!dirStat.isDirectory() || dirStat.isSymbolicLink()) throw new Error('Папка снимка недоступна.');
  const manifestPath = path.join(dir, 'manifest.json'), payloadPath = path.join(dir, 'payload.json');
  await regularFile(manifestPath); await regularFile(payloadPath);
  const manifest = JSON.parse(await fsp.readFile(manifestPath, 'utf8'));
  if (manifest.version !== 1 || manifest.id !== id || !Array.isArray(manifest.files) || manifest.files.length > 200000 || typeof manifest.includeData !== 'boolean') throw new Error('Неверный формат снимка.');
  const payloadText = await fsp.readFile(payloadPath, 'utf8');
  if (crypto.createHash('sha256').update(payloadText).digest('hex') !== manifest.payloadHash) throw new Error('Снимок ещё не полностью загружен или повреждён (состояние).');
  const payload = JSON.parse(payloadText);
  const scopeSet = new Set(scopesFor(payload.ui));
  if (allowBackupScopes && manifest.kind === 'backup') {
    if (!Array.isArray(manifest.extraScopes)) throw new Error('Некорректные пространства резервной копии.');
    for (const scope of manifest.extraScopes) {
      const id = typeof scope === 'string' && scope.startsWith('idea:') ? scope.slice(5) : scope;
      if (typeof id !== 'string' || !ID_RE.test(id) || id.includes('..') || /^-|-$/.test(id) || !safeRel(id) || (!scope.startsWith('idea:') && id.startsWith('idea__'))) throw new Error('Недопустимое пространство резервной копии.');
      scopeSet.add(scope);
    }
  }
  if (!payload.apiCalls || typeof payload.apiCalls !== 'object' || Array.isArray(payload.apiCalls)) throw new Error('Некорректный журнал API в снимке.');
  const filesDir = path.join(dir, 'files');
  const filesInfo = await fsp.lstat(filesDir);
  if (!filesInfo.isDirectory() || filesInfo.isSymbolicLink()) throw new Error('Папка файлов снимка недоступна.');
  const seen = new Set(), targetSeen = new Map(), entries = [];
  for (let i = 0; i < manifest.files.length; i++) {
    const item = manifest.files[i];
    if (!item || !/^\d{8}$/.test(item.id) || seen.has(item.id) || !safeRel(item.rel) || !/^[a-f0-9]{64}$/.test(item.sha256) || !Number.isSafeInteger(item.size) || item.size < 0) throw new Error('Некорректный файл в снимке.');
    seen.add(item.id);
    let destRoot, destRel = item.rel;
    if (item.kind === 'code' || item.kind === 'runs') {
      if (!scopeSet.has(item.scope)) throw new Error('Рабочее пространство отсутствует в состоянии снимка.');
      destRoot = (await runtime.projectPaths(item.scope))[item.kind];
    } else if (item.kind === 'data' && manifest.includeData && item.scope === null) {
      destRoot = runtime.dataDir;
    } else if (item.kind === 'linked' && manifest.includeData && ROLES.includes(item.scope) && !item.rel.includes('/')) {
      destRoot = runtime.dataDir;
      destRel = `_fly-linked/${item.scope}/${item.rel}`;
    } else throw new Error('Неизвестный тип файла в снимке.');
    const source = path.join(filesDir, item.id), stat = await regularFile(source);
    progress({ phase: 'verify', done: i, total: manifest.files.length, file: item.rel });
    if (stat.size !== item.size || await hashFile(source) !== item.sha256) throw new Error(`Снимок не полностью загружен или повреждён: ${item.rel}. Дождитесь Google Диска и повторите.`);
    const targetKey = path.resolve(destRoot, ...destRel.split('/')).toLowerCase();
    if (targetSeen.has(targetKey) && targetSeen.get(targetKey) !== item.sha256) throw new Error(`Два разных файла снимка имеют одинаковый путь: ${destRel}`);
    targetSeen.set(targetKey, item.sha256);
    entries.push({ ...item, source, destRoot, destRel });
  }
  return { manifest, payload, entries };
}

async function restoreSnapshot(root, id, runtime, currentUi, currentApiCalls, backupRoot, progress = () => {}, allowBackupScopes = false) {
  const checked = await readSnapshot(root, id, runtime, progress, allowBackupScopes);
  const remoteScopes = [...new Set([...scopesFor(checked.payload.ui), ...checked.entries.filter((entry) => entry.kind === 'code' || entry.kind === 'runs').map((entry) => entry.scope)])];
  const backup = await createSnapshot(backupRoot, runtime, currentUi, currentApiCalls, checked.manifest.includeData, { extraScopes: remoteScopes, kind: 'backup', progress });
  const linked = {};
  try {
    for (let i = 0; i < checked.entries.length; i++) {
      const entry = checked.entries[i];
      progress({ phase: 'restore', done: i, total: checked.entries.length, file: entry.rel });
      await ensureDirectory(entry.destRoot);
      const dest = await safeDestination(entry.destRoot, entry.destRel);
      const tmp = `${dest}.fly-sync-${crypto.randomBytes(6).toString('hex')}.tmp`;
      try {
        await fsp.copyFile(entry.source, tmp, fs.constants.COPYFILE_EXCL);
        if (await hashFile(tmp) !== entry.sha256) throw new Error(`Файл снимка изменился во время копирования: ${entry.rel}`);
        await fsp.rename(tmp, dest);
      } finally { await fsp.rm(tmp, { force: true }).catch(() => {}); }
      if (entry.kind === 'linked') linked[entry.scope] = dest;
    }
    return { ui: checked.payload.ui, apiCalls: checked.payload.apiCalls, linked, includeData: checked.manifest.includeData, backup };
  } catch (e) {
    throw new Error(`Восстановление прервано, часть файлов могла измениться. Локальная резервная копия: ${backup.path}. ${e.message}`);
  }
}

module.exports = { scopesFor, createSnapshot, listSnapshots, restoreSnapshot };
