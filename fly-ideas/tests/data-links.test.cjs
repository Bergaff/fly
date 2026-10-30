const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const vm = require('node:vm');
const zlib = require('node:zlib');
const { spawnSync } = require('node:child_process');

const root = path.join(__dirname, '..');
const script = path.join(root, 'experiments/templates/21_check_linked_data.py');
const python = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean).find((p) => spawnSync(p, ['-c', 'import sys']).status === 0);

test('IPC связывает файлы, передаёт пути запущенному Python и не меняет данные', { skip: !python && 'Python не найден' }, async () => {
  const dir = await fsp.mkdtemp(path.join(os.tmpdir(), 'fly-links-'));
  try {
    const mainPath = path.join(root, 'electron/main.cjs');
    const realRequire = require('node:module').createRequire(mainPath);
    const handlers = new Map();
    let selected = '';
    let onExit;
    const electron = {
      app: { getPath: (name) => path.join(dir, name), whenReady: () => new Promise(() => {}), on: () => {} },
      ipcMain: { handle: (name, fn) => handlers.set(name, fn) }, BrowserWindow: {}, shell: {},
      dialog: { showOpenDialog: async () => selected ? { canceled: false, filePaths: [selected] } : { canceled: true, filePaths: [] } },
    };
    const fakeProcess = { ...process, env: { ...process.env, VITE_DEV_SERVER_URL: 'http://localhost:5173', FLY_CONNECTOME: 'not-inherited' }, platform: process.platform };
    const source = await fsp.readFile(mainPath, 'utf8');
    vm.runInNewContext(`${source}\npickPython = async () => ({exe: ${JSON.stringify(python)}, cmd: ${JSON.stringify(python)}, version: 'test'});\nregisterIpc(() => ({webContents:{send:(_channel, event) => { if(event.stream === 'exit') onExit(event); }}}));`, {
      require: (name) => name === 'electron' ? electron : realRequire(name),
      __dirname: path.join(dir, 'app', 'electron'), process: fakeProcess, console, setTimeout, clearTimeout, Buffer, URL,
      onExit: (ev) => onExit(ev), module: { exports: {} },
    });
    const call = (name, ...args) => handlers.get(`fly:${name}`)(null, ...args);
    const env = await call('checkEnv');
    assert.ok(Object.hasOwn(env.packages, 'duckdb'), 'duckdb must be included in environment diagnostics');
    const file = path.join(dir, 'ручные связи.csv.gz');
    const contents = zlib.gzipSync('pre_root_id,post_root_id,syn_count\n720575940000000001,720575940000000002,7\n');
    await fsp.writeFile(file, contents);
    selected = file;
    const links = await call('chooseDataFile', 'connections');
    assert.equal(links.connections.path, file);
    assert.equal(links.connections.available, true);
    assert.equal((await call('getDataFileLinks')).connections.path, file);
    const types = path.join(dir, 'типы.csv');
    await fsp.writeFile(types, 'root_id,primary_type\n720575940000000001,KC\n');
    selected = types;
    await call('chooseDataFile', 'cell_types');
    assert.equal((await call('getDataFileLinks')).cell_types.path, types);
    const authorConn = path.join(dir, 'авторские связи.parquet');
    const authorList = path.join(dir, 'авторские нейроны.csv');
    await fsp.writeFile(authorConn, 'test reference'); await fsp.writeFile(authorList, 'id\n1\n');
    selected = authorConn; await call('chooseDataFile', 'shiu_connections');
    selected = authorList; await call('chooseDataFile', 'shiu_neurons');
    assert.equal((await call('getDataFileLinks')).shiu_connections.path, authorConn);
    assert.equal((await call('getDataFileLinks')).shiu_neurons.path, authorList);
    await assert.rejects(call('chooseDataFile', '__proto__'), /Неизвестный/);
    selected = '';
    await call('chooseDataFile', 'connections');
    assert.equal((await call('getDataFileLinks')).connections.path, file);
    const ws = await call('projectPaths', 'idea:example');
    await fsp.copyFile(script, path.join(ws.code, '21_check_linked_data.py'));
    const completed = new Promise((resolve) => { onExit = resolve; });
    const run = await call('runScript', 'idea:example', '21_check_linked_data.py', []);
    assert.equal((await completed).code, 0);
    const report = JSON.parse(await fsp.readFile(path.join(run.runDir, 'summary.json'), 'utf8'));
    assert.equal(report.connections.path, file);
    assert.equal(report.connections.ok, true);
    assert.equal(report.connections.example_ids[0].pre, '720575940000000001');
    assert.equal(report.cell_types.path, types);
    assert.equal(report.cell_types.ok, true);
    assert.deepEqual(await fsp.readFile(file), contents);
    await fsp.writeFile(path.join(ws.code, 'check_refs.py'), `import os,json\nopen(os.path.join(os.environ['FLY_RUN_DIR'],'summary.json'),'w').write(json.dumps({k:os.environ.get(k) for k in ('FLY_CONNECTOME','FLY_SHIU_CONNECTIONS','FLY_SHIU_NEURONS')}))\n`);
    const refCompleted = new Promise((resolve) => { onExit = resolve; });
    const refRun = await call('runScript', 'idea:example', 'check_refs.py', []);
    assert.equal((await refCompleted).code, 0);
    const refReport = JSON.parse(await fsp.readFile(path.join(refRun.runDir, 'summary.json'), 'utf8'));
    assert.equal(refReport.FLY_CONNECTOME, file);
    assert.equal(refReport.FLY_SHIU_CONNECTIONS, authorConn);
    assert.equal(refReport.FLY_SHIU_NEURONS, authorList);
    await call('clearDataFile', 'shiu_neurons');
    assert.equal((await call('getDataFileLinks')).shiu_neurons.path, '');
    assert.equal((await call('getDataFileLinks')).connections.path, file);
    await fsp.unlink(file);
    assert.equal((await call('getDataFileLinks')).connections.available, false);
    await call('clearDataFile', 'connections');
    assert.equal((await call('getDataFileLinks')).connections.path, '');
    const completed2 = new Promise((resolve) => { onExit = resolve; });
    const next = await call('runScript', 'idea:example', '21_check_linked_data.py', []);
    assert.equal((await completed2).code, 1);
    const missing = JSON.parse(await fsp.readFile(path.join(next.runDir, 'summary.json'), 'utf8'));
    assert.equal(missing.connections.ok, false); // не наследуем FLY_CONNECTOME из ОС
  } finally { await fsp.rm(dir, { recursive: true, force: true }); }
});

test('проверка связей читает только выборку и сообщает о неподходящих файлах', { skip: !python && 'Python не найден' }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-linked-check-'));
  try {
    const file = path.join(dir, 'connections.csv.gz');
    const source = 'pre_root_id,post_root_id,neuropil,syn_count,nt_type\n' + Array.from({length: 30}, (_, i) => `720575940000000001,720575940000000002,MB,${i + 1},GABA`).join('\n') + '\n';
    fs.writeFileSync(file, zlib.gzipSync(source));
    const ann = path.join(dir, 'types.csv');
    fs.writeFileSync(ann, 'root_id,primary_type\n720575940000000001,KC\n');
    const run = (connections, extra = {}) => {
      const result = spawnSync(python, [script], { encoding: 'utf8', env: { ...process.env, FLY_RUN_DIR: dir, FLY_CONNECTOME: connections, FLY_ANNOTATIONS: '', FLY_CELL_TYPES: '', FLY_NEUROTRANSMITTERS: '', ...extra } });
      return { code: result.status, report: JSON.parse(fs.readFileSync(path.join(dir, 'summary.json'), 'utf8')) };
    };
    const good = run(file, { FLY_CELL_TYPES: ann });
    assert.equal(good.code, 0);
    assert.equal(good.report.connections.sample_rows, 20);
    assert.equal(good.report.connections.example_ids[0].pre, '720575940000000001');
    assert.equal(good.report.cell_types.id_column, 'root_id');
    assert.match(good.report.scope, /не проверка всей таблицы/);
    fs.writeFileSync(ann, 'id,unrelated\n1,2\n');
    const badAnn = run(file, { FLY_CELL_TYPES: ann });
    assert.equal(badAnn.code, 1);
    assert.equal(badAnn.report.cell_types.ok, false);
    const bad = path.join(dir, 'bad.csv'); fs.writeFileSync(bad, 'x,y\n1,2\n');
    assert.equal(run(bad).report.connections.ok, false);
    fs.writeFileSync(bad, 'pre_root_id,post_root_id\n7.2e17,720575940000000002\n');
    assert.match(run(bad).report.connections.error, /некорректных ID/);
    assert.equal(run(path.join(dir, 'missing.csv')).report.connections.ok, false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

const hasArrow = python && spawnSync(python, ['-c', 'import pyarrow.parquet']).status === 0;
test('таблица Parquet сохраняет точные 64-битные ID нейронов', { skip: !hasArrow && 'pyarrow не установлен в тестовом Python' }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-parquet-'));
  try {
    const input = path.join(dir, 'connections.parquet');
    const create = spawnSync(python, ['-c', 'import pyarrow as a, pyarrow.parquet as p, sys; p.write_table(a.table({"pre_root_id": [720575940000000001], "post_root_id": [720575940000000002], "syn_count": [5]}), sys.argv[1])', input], { encoding: 'utf8' });
    assert.equal(create.status, 0, create.stderr);
    const result = spawnSync(python, [script], { encoding: 'utf8', env: { ...process.env, FLY_RUN_DIR: dir, FLY_CONNECTOME: input, FLY_ANNOTATIONS: '', FLY_CELL_TYPES: '', FLY_NEUROTRANSMITTERS: '' } });
    assert.equal(result.status, 0, result.stderr);
    const report = JSON.parse(fs.readFileSync(path.join(dir, 'summary.json'), 'utf8'));
    assert.equal(report.connections.example_ids[0].pre, '720575940000000001');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
