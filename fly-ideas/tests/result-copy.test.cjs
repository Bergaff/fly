const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const { copyRunFile, MAX_BYTES } = require('../electron/result-copy.cjs');

async function fixture(fn) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'fly-copy-'));
  try { await fn(root); } finally { await fs.rm(root, { recursive: true, force: true }); }
}
function isInside(root, target) {
  const r = path.relative(root, target);
  return !!r && r !== '..' && !r.startsWith('..' + path.sep) && !path.isAbsolute(r);
}

test('копирование выбранного результата сохраняет исходный текст, а не заглушку предпросмотра', async () => fixture(async root => {
  const dir = path.join(root, 'run'); await fs.mkdir(dir);
  const json = '{\n  "result": 900, "note": "нейроны"\n}\n';
  const csv = 'root_id,value\n720575940000000001,1\n' + 'x,2\n'.repeat(150000);
  await fs.writeFile(path.join(dir, 'summary.json'), json);
  await fs.writeFile(path.join(dir, 'rates.csv'), csv);
  await fs.writeFile(path.join(dir, 'log.txt'), 'это лог');
  let clipboardText = '';
  const options = { dir, withinRuns: p => isInside(root, p), clipboard: { writeText: value => { clipboardText = value; }, readText: () => clipboardText } };
  assert.equal((await copyRunFile({ ...options, name: 'summary.json' })).kind, 'text'); assert.equal(clipboardText, json);
  await copyRunFile({ ...options, name: 'rates.csv' }); assert.equal(clipboardText, csv); assert.ok(csv.length > 400000);
  await copyRunFile({ ...options, name: 'log.txt' }); assert.equal(clipboardText, 'это лог');
}));

test('поддерживает PNG и корректно отказывает в неподдерживаемых или больших файлах', async () => fixture(async root => {
  const dir = path.join(root, 'run'); await fs.mkdir(dir);
  let text = 'не менять', image = null;
  const opts = { dir, withinRuns: p => isInside(root, p), clipboard: { writeText: x => { text = x; }, writeImage: x => { image = x; } }, nativeImage: { createFromBuffer: b => ({ bytes: b.toString(), isEmpty: () => false }) } };
  await fs.writeFile(path.join(dir, 'graph.png'), 'test-png');
  await copyRunFile({ ...opts, name: 'graph.png' }); assert.equal(image.bytes, 'test-png');
  await fs.writeFile(path.join(dir, 'many.json'), Buffer.alloc(MAX_BYTES + 1, 97));
  await assert.rejects(copyRunFile({ ...opts, name: 'many.json' }), /8 МиБ/);
  await fs.writeFile(path.join(dir, 'table.parquet'), 'binary');
  await assert.rejects(copyRunFile({ ...opts, name: 'table.parquet' }), /нельзя скопировать/);
  await fs.writeFile(path.join(dir, 'bad.csv'), Buffer.from([0xff, 0xfe]));
  await assert.rejects(copyRunFile({ ...opts, name: 'bad.csv' }), /UTF-8/);
  assert.equal(text, 'не менять');
  await assert.rejects(copyRunFile({ ...opts, name: '../secret.txt' }), /имя/);
  await assert.rejects(copyRunFile({ ...opts, name: 'x\\secret.txt' }), /имя/);
  await assert.rejects(copyRunFile({ ...opts, dir: path.dirname(root), name: 'secret.txt' }), /вне папки/);
}));

test('не подтверждает копирование, если буфер остался со старым кодом', async () => fixture(async root => {
  const dir = path.join(root, 'run'); await fs.mkdir(dir);
  await fs.writeFile(path.join(dir, 'summary.json'), '{"status":"ok"}');
  let attempts = 0;
  const clipboard = { writeText: () => { attempts++; }, readText: () => 'import pandas as pd' };
  await assert.rejects(copyRunFile({ dir, name: 'summary.json', withinRuns: p => isInside(root, p), clipboard }), /Не удалось подтвердить/);
  assert.equal(attempts, 3);
}));

test('проверка буфера учитывает замену переносов строк в Windows и повторяет запись', async () => fixture(async root => {
  const dir = path.join(root, 'run'); await fs.mkdir(dir);
  await fs.writeFile(path.join(dir, 'summary.json'), '{\n"status": "ok"\n}\n');
  let value = 'old', attempts = 0;
  const clipboard = { writeText: v => { if (++attempts > 1) value = v.replace(/\n/g, '\r\n'); }, readText: () => value };
  await copyRunFile({ dir, name: 'summary.json', withinRuns: p => isInside(root, p), clipboard });
  assert.equal(attempts, 2); assert.equal(value, '{\r\n"status": "ok"\r\n}\r\n');
}));

test('не копирует файл или родительскую папку, ведущие по ссылке за пределы прогонов', { skip: process.platform === 'win32' && 'создание ссылок на Windows может требовать разрешения' }, async () => fixture(async root => {
  const run = path.join(root, 'runs', 'run'), outside = path.join(root, 'outside');
  await fs.mkdir(run, { recursive: true }); await fs.mkdir(outside);
  await fs.writeFile(path.join(outside, 'secret.txt'), 'secret');
  await fs.symlink(path.join(outside, 'secret.txt'), path.join(run, 'link.txt'));
  const opts = { dir: run, name: 'link.txt', withinRuns: p => isInside(path.join(root, 'runs'), p), clipboard: { writeText: () => { throw new Error('не должно вызываться'); } } };
  await assert.rejects(copyRunFile(opts), /ссылки/);
  const linkDir = path.join(root, 'runs', 'external');
  await fs.symlink(outside, linkDir, 'dir');
  await assert.rejects(copyRunFile({ ...opts, dir: linkDir, name: 'secret.txt' }), /вне папки/);
}));

test('IPC копирует конкретный выбранный файл и проверяет реальные папки прогонов', async () => fixture(async root => {
  const mainPath = path.join(__dirname, '../electron/main.cjs');
  const realRequire = require('node:module').createRequire(mainPath);
  const handlers = new Map(); let clipboardText = '';
  const electron = {
    app: { getPath: name => path.join(root, name), whenReady: () => new Promise(() => {}), on: () => {} },
    ipcMain: { handle: (name, fn) => handlers.set(name, fn) }, BrowserWindow: {}, shell: {}, dialog: {},
    clipboard: { writeText: value => { clipboardText = value; }, readText: () => clipboardText }, nativeImage: {},
  };
  const source = await fs.readFile(mainPath, 'utf8');
  vm.runInNewContext(`${source}\nregisterIpc(() => null);`, { require: name => name === 'electron' ? electron : realRequire(name), __dirname: path.join(root, 'app', 'electron'), process: { ...process, env: { ...process.env, VITE_DEV_SERVER_URL: 'http://localhost:5173' } }, console, setTimeout, clearTimeout, Buffer, URL, module: { exports: {} } });
  const call = (name, ...args) => handlers.get(`fly:${name}`)(null, ...args);
  const ws = await call('projectPaths', 'idea:test');
  const run = path.join(ws.runs, 'run1'); await fs.mkdir(run);
  await fs.writeFile(path.join(run, 'summary.json'), '{"value":3}');
  await fs.writeFile(path.join(run, 'log.txt'), 'лог');
  await call('copyRunFile', run, 'summary.json'); assert.equal(clipboardText, '{"value":3}');
  await call('copyRunFile', run, 'log.txt'); assert.equal(clipboardText, 'лог');
  await assert.rejects(call('copyRunFile', root, 'summary.json'), /вне папки/);
}));

test('переключение выбирает отдельный результат, лог не подставляется при ошибке', async () => {
  const source = await fs.readFile(path.join(__dirname, '../src/views/brain-view.tsx'), 'utf8');
  assert.match(source, /setSelectedArtifact\(name\)/);
  assert.match(source, /disabled=\{copyBusy \|\| \(!selectedArtifact/);
  assert.match(source, /показать \{f\}/);
  assert.match(source, /resultFiles = selRun \? selRun\.files\.filter\(\(f\) => f !== "log\.txt"\)/);
  const start = source.indexOf('  const copyCurrentResult = async () => {');
  const end = source.indexOf('  const installPackageAndRetry', start);
  assert.ok(start >= 0 && end > start);
  const code = ts.transpile(source.slice(start, end), { target: ts.ScriptTarget.ES2022 });
  const calls = [], status = [], context = {
    selectedArtifact: 'summary.json', selRun: { path: '/run/a', files: ['summary.json', 'log.txt'] }, displayLog: 'не копировать этот лог',
    copyRequest: { current: 0 }, setCopyStatus: v => status.push(v), setCopyBusy: () => {},
    fly: { copyRunFile: async (dir, name) => { calls.push([dir, name]); return { kind: 'text' }; } },
    navigator: { clipboard: { writeText: () => { throw new Error('не должен копироваться лог'); } } },
  };
  const runCopy = vm.runInNewContext(`${code}\ncopyCurrentResult;`, context);
  await runCopy(); assert.deepEqual(calls, [['/run/a', 'summary.json']]); assert.match(status.at(-1), /summary\.json/);
  context.selectedArtifact = 'sample_rates.csv';
  context.fly.copyRunFile = async () => { throw new Error('слишком большой'); };
  await runCopy(); assert.match(status.at(-1), /слишком большой/);
  context.selectedArtifact = null;
  context.fly.copyRunFile = async (dir, name) => { calls.push([dir, name]); return { kind: 'text' }; };
  await runCopy(); assert.deepEqual(calls.at(-1), ['/run/a', 'log.txt']);
});
