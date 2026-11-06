const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const python = process.env.TWO_FLIES_TEST_PYTHON || 'python3';
const env = { ...process.env, MUJOCO_GL: 'disable', OMP_NUM_THREADS: '1', OPENBLAS_NUM_THREADS: '1' };
const check = spawnSync(python, ['-c', 'import mujoco, numpy, brian2, PIL'], { env });
test('кинематическая сцена, зрение, вмешательства и полные спайки', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 60000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('фаза, независимые перестановки, воспроизведение и сохранность входных файлов', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-phase-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 90000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('контроли объекта, фаз и частот с неизменностью прежних результатов', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-visual-controls-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 90000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('управление крыльями, контроль readout и защита исходной серии', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-motor-bridge-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 90000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('покадрово сопоставленные зрительные контроли и спайки каждого нейрона', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-matched-controls-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 120000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
