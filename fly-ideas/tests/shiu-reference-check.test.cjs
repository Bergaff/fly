const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const zlib = require('node:zlib');
const { spawnSync } = require('node:child_process');
const script = path.join(__dirname, '../experiments/templates/22_shiu_reference_check.py');
const python = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean).find(p => spawnSync(p, ['-c', 'import pandas']).status === 0);
function fixture(fn) { const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-shiu-')); try { fn(dir); } finally { fs.rmSync(dir, {recursive: true, force: true}); } }
function run(dir, env) {
  const out = fs.mkdtempSync(path.join(dir, 'out-'));
  const p = spawnSync(python, [script], { encoding: 'utf8', timeout: 60000, env: { ...process.env, PYTHONIOENCODING: 'utf-8', FLY_RUN_DIR: out, FLY_CONNECTOME: '', FLY_ANNOTATIONS: '', FLY_CELL_TYPES: '', FLY_NEUROTRANSMITTERS: '', ...env } });
  return { p, summary: JSON.parse(fs.readFileSync(path.join(out, 'summary.json'), 'utf8')) };
}

test('сверяет конкретные ID авторского ноутбука полностью, без симуляции или вывода о версии', { skip: !python && 'нужен pandas' }, () => fixture(dir => {
  const file = path.join(dir, 'connections.csv.gz'), nt = path.join(dir, 'neurons.csv');
  const source = 'pre_root_id,post_root_id,syn_count\n720575940624963786,720575940660219265,3\n720575940660219265,720575940645521262,2\n720575940000000001,720575940624963786,1\n';
  fs.writeFileSync(file, zlib.gzipSync(source));
  fs.writeFileSync(nt, 'root_id,nt_type\n720575940660219265,ach\n720575940645521262,gaba\n');
  const {p, summary} = run(dir, {FLY_CONNECTOME: file, FLY_NEUROTRANSMITTERS: nt});
  assert.equal(p.status, 0, p.stderr); assert.equal(summary.status, 'ok');
  assert.equal(summary.tables.connections.rows_scanned, 3);
  assert.deepEqual(summary.matches_in_connections, {sugar_right: {found: 1, total: 21}, sugar_left: {found: 0, total: 10}, mn9_left: true, mn9_right: true});
  assert.deepEqual(summary.tables.connections.id_counts['720575940624963786'], {pre_rows: 1, post_rows: 1});
  assert.deepEqual(summary.tables.connections.id_counts['720575940660219265'], {pre_rows: 1, post_rows: 1});
  assert.equal(summary.tables.neurotransmitters.id_counts['720575940645521262'], 1);
  assert.equal(summary.tables.annotations.status, 'not_selected');
  assert.match(summary.scope, /не выполняются/);
  assert.ok(summary.caveats.some(c => c.includes('не доказывает')));
  assert.equal(summary.reference_ids.sugar_right_figure_1d.length, 21);
  assert.equal(summary.reference_ids.sugar_left_supplement.length, 10);
  assert.equal(zlib.gunzipSync(fs.readFileSync(file)).toString(), source);
}));

test('отсутствие или неподходящий формат связей не подменяются данными', { skip: !python && 'нужен pandas' }, () => fixture(dir => {
  const absent = run(dir, {});
  assert.equal(absent.p.status, 1); assert.equal(absent.summary.status, 'blocked');
  assert.equal(absent.summary.tables.connections.status, 'not_selected');
  const file = path.join(dir, 'bad.csv'); fs.writeFileSync(file, 'a,b\n1,2\n');
  const bad = run(dir, {FLY_CONNECTOME: file});
  assert.equal(bad.p.status, 1); assert.equal(bad.summary.status, 'blocked');
  assert.match(bad.summary.tables.connections.error, /формате/);
}));
