const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { createSnapshot, listSnapshots, restoreSnapshot } = require('../electron/folder-sync.cjs');

const ui = (name, ideas = ['a']) => ({ state: { version: 1, projects: [{ id: 'p', name }], ideas: ideas.map(id => ({ id })), references: [] }, chats: { 'fly-ideas:chat:idea:a': JSON.stringify([{ role: 'user', content: name }]) }, rates: JSON.stringify({ price: name }) });
const runtime = (root, links = {}) => ({ dataDir: path.join(root, 'data'), getLinks: () => links, projectPaths: (id) => ({ code: path.join(root, 'code', id.replace(':', '_')), runs: path.join(root, 'runs', id.replace(':', '_')) }) });
async function put(file, content) { await fs.mkdir(path.dirname(file), { recursive: true }); await fs.writeFile(file, content); }
async function fixture(fn) { const dir = await fs.mkdtemp(path.join(os.tmpdir(), 'fly-sync-')); try { await fn(dir); } finally { await fs.rm(dir, { recursive: true, force: true }); } }

test('два компьютера: снимки независимы, локальные изменения и отсутствующие пространства сохраняются в резервной копии', async () => fixture(async dir => {
  const shared = path.join(dir, 'drive'), a = runtime(path.join(dir, 'a')), b = runtime(path.join(dir, 'b'));
  const aPath = a.projectPaths('idea:a').code, bPath = b.projectPaths('idea:a').code;
  await put(path.join(aPath, 'work.py'), 'computer A');
  await put(path.join(a.projectPaths('idea:a').runs, 'run', 'summary.json'), '{"result":1}');
  await put(path.join(aPath, 'secrets.json'), 'secret');
  await put(path.join(aPath, '.venv', 'lib.py'), 'venv');
  await put(path.join(bPath, 'work.py'), 'computer B');
  await put(path.join(bPath, 'keep.py'), 'not deleted');
  const apiA = { a: [{ question: 'question A' }] }, apiB = { b: [{ question: 'question B' }] };
  const first = await createSnapshot(shared, a, ui('A'), apiA, false);
  const second = await createSnapshot(shared, a, ui('A2'), apiA, false);
  assert.notEqual(first.id, second.id);
  assert.equal((await listSnapshots(shared)).length, 2);
  const result = await restoreSnapshot(shared, first.id, b, ui('B', []), apiB, path.join(dir, 'backups'));
  assert.deepEqual(result.ui, ui('A'));
  assert.deepEqual(result.apiCalls, apiA);
  assert.equal(await fs.readFile(path.join(bPath, 'work.py'), 'utf8'), 'computer A');
  assert.equal(await fs.readFile(path.join(bPath, 'keep.py'), 'utf8'), 'not deleted');
  await assert.rejects(fs.stat(path.join(bPath, 'secrets.json')), { code: 'ENOENT' });
  await assert.rejects(fs.stat(path.join(bPath, '.venv')), { code: 'ENOENT' });
  const back = await restoreSnapshot(path.join(dir, 'backups'), result.backup.id, b, ui('A'), apiA, path.join(dir, 'backups'), () => {}, true);
  assert.deepEqual(back.ui, ui('B', []));
  assert.deepEqual(back.apiCalls, apiB);
  assert.equal(await fs.readFile(path.join(bPath, 'work.py'), 'utf8'), 'computer B');
}));

test('данные и внешние таблицы включаются только по выбору и получают новые пути', async () => fixture(async dir => {
  const shared = path.join(dir, 'drive'), table = path.join(dir, 'outside', 'connections.csv');
  await put(table, 'edge data');
  const a = runtime(path.join(dir, 'a'), { connections: { path: table } }), b = runtime(path.join(dir, 'b'));
  await put(path.join(a.dataDir, 'data.csv'), 'data');
  const noData = await createSnapshot(shared, a, ui('A'), {}, false);
  const plain = await restoreSnapshot(shared, noData.id, b, ui('B'), {}, path.join(dir, 'backup'));
  assert.equal(plain.includeData, false);
  await assert.rejects(fs.stat(path.join(b.dataDir, 'data.csv')), { code: 'ENOENT' });
  const data = await createSnapshot(shared, a, ui('A'), {}, true);
  const result = await restoreSnapshot(shared, data.id, b, ui('B'), {}, path.join(dir, 'backup'));
  assert.equal(await fs.readFile(path.join(b.dataDir, 'data.csv'), 'utf8'), 'data');
  assert.equal(await fs.readFile(result.linked.connections, 'utf8'), 'edge data');
  assert.notEqual(result.linked.connections, table);
}));

test('неполный или повреждённый снимок не изменяет файлы', async () => fixture(async dir => {
  const shared = path.join(dir, 'drive'), a = runtime(path.join(dir, 'a')), b = runtime(path.join(dir, 'b'));
  await put(path.join(a.projectPaths('idea:a').code, 'x.py'), 'A');
  const target = path.join(b.projectPaths('idea:a').code, 'x.py'); await put(target, 'B');
  const snap = await createSnapshot(shared, a, ui('A'), {}, false);
  await fs.writeFile(path.join(snap.path, 'files', '00000000'), 'corrupt');
  await assert.rejects(restoreSnapshot(shared, snap.id, b, ui('B'), {}, path.join(dir, 'backup')), /повреждён/);
  assert.equal(await fs.readFile(target, 'utf8'), 'B');
  assert.deepEqual(await listSnapshots(path.join(dir, 'backup')), []);
}));

test('запрещены ссылки и выход из папки назначения', async () => fixture(async dir => {
  const shared = path.join(dir, 'drive'), a = runtime(path.join(dir, 'a')), b = runtime(path.join(dir, 'b'));
  const code = a.projectPaths('idea:a').code;
  await put(path.join(code, 'nested', 'x.py'), 'A');
  const snap = await createSnapshot(shared, a, ui('A'), {}, false);
  const outside = path.join(dir, 'outside'); await fs.mkdir(outside);
  const bcode = b.projectPaths('idea:a').code; await fs.mkdir(bcode, { recursive: true });
  await fs.symlink(outside, path.join(bcode, 'nested'), 'dir');
  await assert.rejects(restoreSnapshot(shared, snap.id, b, ui('B'), {}, path.join(dir, 'backup')), /ссылк/i);
  await assert.rejects(fs.stat(path.join(outside, 'x.py')), { code: 'ENOENT' });
  const manifestPath = path.join(snap.path, 'manifest.json');
  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'));
  manifest.files[0].rel = '../escape.py';
  await fs.writeFile(manifestPath, JSON.stringify(manifest));
  await assert.rejects(restoreSnapshot(shared, snap.id, b, ui('B'), {}, path.join(dir, 'backup')), /Некорректный файл/);
}));

test('Electron IPC блокирует синхронизацию во время расчёта и переносит журнал API', async () => fixture(async dir => {
  const vm = require('node:vm');
  const mainPath = path.join(__dirname, '../electron/main.cjs');
  const realRequire = require('node:module').createRequire(mainPath);
  const handlers = new Map();
  const drive = path.join(dir, 'drive'); await fs.mkdir(drive);
  const electron = {
    app: { getPath: name => path.join(dir, name), whenReady: () => new Promise(() => {}), on: () => {} },
    ipcMain: { handle: (name, fn) => handlers.set(name, fn) }, BrowserWindow: {}, shell: {},
    dialog: { showOpenDialog: async () => ({ canceled: false, filePaths: [drive] }) },
  };
  const context = { require: name => name === 'electron' ? electron : realRequire(name), __dirname: path.join(dir, 'app', 'electron'), process: { ...process, env: { ...process.env, VITE_DEV_SERVER_URL: 'http://localhost:5173' } }, console, setTimeout, clearTimeout, Buffer, URL, module: { exports: {} } };
  const source = await fs.readFile(mainPath, 'utf8');
  vm.runInNewContext(`${source}\nregisterIpc(() => ({webContents:{send:()=>{}, reload:()=>{}}}));\nglobalThis.testRuns = runs;`, context);
  const call = (name, ...args) => handlers.get(`fly:${name}`)(null, ...args);
  await call('chooseSyncFolder');
  context.testRuns.set('active', {});
  await assert.rejects(call('syncUpload', ui('A'), false), /Дождитесь завершения/);
  context.testRuns.clear();
  await call('appendApiCall', 'idea:a', { id: '1', at: new Date().toISOString(), workspaceId: 'idea:a', provider: 'deepseek', model: 'm', question: 'q', answer: 'a', usage: null, status: 'ok' });
  const snapshot = await call('syncUpload', ui('A'), false);
  assert.equal((await call('syncInfo')).shared.length, 1);
  const result = await call('syncRestore', 'shared', snapshot.id, ui('B'));
  assert.equal(result.ui.state.projects[0].name, 'A');
  await assert.rejects(call('syncUpload', ui('A'), false), /Дождитесь/);
  await call('syncFinish', false);
  assert.equal((await call('listApiCalls', 'idea:a')).length, 1);
}));
