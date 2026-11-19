const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const zlib = require('node:zlib');
const { spawnSync } = require('node:child_process');

const root = path.join(__dirname, '..');
const script = path.join(root, 'experiments/templates/small_sample_lif_fixed.py');
const candidates = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean);
const python = candidates.find(p => spawnSync(p, ['-c', 'import brian2, pandas, numpy']).status === 0);

function fixture(fn) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-lif-'));
  try { return fn(dir); } finally { fs.rmSync(dir, { recursive: true, force: true }); }
}
function data(dir, compress = false, nts = 'ACH,GABA,GLUT,UNKNOWN') {
  const [nt1,nt2,nt3,nt4] = nts.split(',');
  const links = `pre_root_id,post_root_id,syn_count,nt_type\n720575940000000001,720575940000000002,5,ACH\n720575940000000002,720575940000000001,3,GABA\n720575940000000003,720575940000000001,2,GLUT\n720575940000000004,720575940000000001,2,X\n`;
  const transmitters = `root_id,nt_type\n720575940000000001,${nt1}\n720575940000000002,${nt2}\n720575940000000003,${nt3}\n720575940000000004,${nt4}\n`;
  const conn = path.join(dir, compress ? 'links.csv.gz' : 'links.csv'), nt = path.join(dir, compress ? 'nt.csv.gz' : 'nt.csv');
  fs.writeFileSync(conn, compress ? zlib.gzipSync(links) : links);
  fs.writeFileSync(nt, compress ? zlib.gzipSync(transmitters) : transmitters);
  return { conn, nt };
}
function run(dir, files, args = []) {
  const out = path.join(dir, `run-${Math.random()}`); fs.mkdirSync(out);
  const env = { ...process.env, FLY_RUN_DIR: out, FLY_CONNECTOME: files.conn || '', FLY_NEUROTRANSMITTERS: files.nt || '', FLY_ANNOTATIONS: '', FLY_CELL_TYPES: '', PYTHONIOENCODING: 'utf-8' };
  const result = spawnSync(python, [script, ...args], { encoding: 'utf8', env, timeout: 60000 });
  return { result, out, summary: JSON.parse(fs.readFileSync(path.join(out, 'summary.json'), 'utf8')) };
}

test('Brian2 прогоняет исправленный подграф, сохраняет точные ID и исключает неподтверждённые знаки', { skip: !python && 'нужны numpy, pandas и Brian2' }, () => fixture(dir => {
  const files = data(dir, true);
  const {result, summary, out} = run(dir, files, ['--n-neurons', '4', '--stim-frac', '1', '--duration-ms', '50', '--dt-ms', '0.2']);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(summary.status, 'ok');
  assert.equal(summary.metrics.effective_dt_ms, 0.2);
  assert.equal(summary.metrics.candidate_edges, 4);
  assert.equal(summary.metrics.used_edges, 2);
  assert.equal(summary.metrics.ignored_edges_unknown_sign, 2);
  assert.equal(summary.metrics.ignored_types.glut, 1);
  assert.ok(summary.metrics.total_spikes > 0);
  assert.match(summary.scope, /не воспроизведение/);
  const rates = fs.readFileSync(path.join(out, 'sample_rates.csv'), 'utf8');
  const spikes = fs.readFileSync(path.join(out, 'spikes.csv'), 'utf8');
  assert.match(rates, /720575940000000001/); assert.match(rates, /720575940000000004/);
  assert.match(spikes, /720575940000000001/);
  assert.deepEqual(summary.files, ['sample_rates.csv', 'spikes.csv']);
}));

test('пустая стимуляция и отсутствие связей не выдаются за сетевой результат', { skip: !python && 'нужны numpy, pandas и Brian2' }, () => fixture(dir => {
  const files = data(dir, false, 'GLUT,GLUT,GLUT,GLUT');
  const {result, summary} = run(dir, files, ['--n-neurons', '4', '--stim-frac', '0', '--duration-ms', '10']);
  assert.equal(result.status, 0, result.stderr);
  assert.equal(summary.metrics.n_stimulated, 0);
  assert.equal(summary.metrics.total_spikes, 0);
  assert.equal(summary.metrics.used_edges, 0);
  assert.ok(summary.caveats.some(c => c.includes('независимых нейронов')));
}));

test('нет данных или неподходящий шаг дают ненулевой код и понятный отчёт без подмены данными', { skip: !python && 'нужны numpy, pandas и Brian2' }, () => fixture(dir => {
  const files = data(dir);
  const missing = run(dir, { conn: files.conn }, []);
  assert.equal(missing.result.status, 1);
  assert.equal(missing.summary.status, 'error');
  assert.match(missing.summary.error, /FLY_NEUROTRANSMITTERS/);
  assert.deepEqual(missing.summary.metrics, {});
  const bad = run(dir, files, ['--dt-ms', '8']);
  assert.equal(bad.result.status, 1);
  assert.match(bad.summary.error, /dt-ms/);
  const badFrac = run(dir, files, ['--stim-frac', '1.1']);
  assert.equal(badFrac.result.status, 1);
  assert.match(badFrac.summary.error, /stim-frac/);
}));

test('seed воспроизводит выбранные исходные ID', { skip: !python && 'нужны numpy, pandas и Brian2' }, () => fixture(dir => {
  const files = data(dir);
  const args = ['--n-neurons', '2', '--seed', '3', '--duration-ms', '10'];
  const a = run(dir, files, args), b = run(dir, files, args);
  assert.equal(a.result.status, 0, a.result.stderr);
  assert.equal(b.result.status, 0, b.result.stderr);
  assert.equal(fs.readFileSync(path.join(a.out, 'sample_rates.csv'), 'utf8'), fs.readFileSync(path.join(b.out, 'sample_rates.csv'), 'utf8'));
}));
