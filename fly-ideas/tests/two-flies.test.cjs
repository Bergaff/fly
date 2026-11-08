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
test('большая серия: реальная пауза, SQLite-контрольная точка, возобновление и извлечение данных', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-large-study-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 120000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('блокировка progress.json: повтор записи и сохранность остальных ошибок', () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'long-study-progress-compat-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 15000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('после ошибки progress.json расчёт продолжает прежнюю контрольную точку', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'long-study-progress-recovery-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 120000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('парный анализ: реальные и искусственные спайки, целостность, частичный результат и блокировка', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-paired-analysis-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 120000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('запуск большой серии: блокировки progress и CSV без изменения SQLite и научного скрипта', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'long-study-safe-launcher-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 180000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('извлечение отличий tile_scramble из готовых CSV без доступа к SQLite', () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-tile-exception-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 30000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('обучение наблюдением: разделение данных, контроль утечек, сохранение и честные метрики', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-imitation-learning-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 120000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('замороженная модель: новый фиксированный план без обучения, проверка метрик и сохранность исходника', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-frozen-holdout-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 180000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
test('большая серия обучения: статистики, пауза, продолжение, честные метрики и защита контрольной точки', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'two-flies-long-imitation-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 180000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});

test('обучение на пользовательских траекториях, раздельная проверка и настоящие входы модели', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'user-wing-learning-fixture.py')], { cwd: root, env, encoding: 'utf8', timeout: 120000 });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});

test('диагностика пользовательского результата запускается через BAT и не переобучает модель', () => {
  const fs = require('node:fs');
  const bat = fs.readFileSync(path.join(root,'experiments/ANALYZE-USER-WING-INPUTS.bat'),'utf8');
  const script = fs.readFileSync(path.join(root,'experiments/templates/52_analyze_user_wing_inputs.py'),'utf8');
  assert.match(bat,/52_analyze_user_wing_inputs\.py" --choose/);
  assert.match(bat,/\.venv-two-flies/);
  assert.match(bat,/if errorlevel 1/);
  assert.match(script,/allow_pickle=False/);
  assert.match(script,/metadata\.json/);
  assert.match(script,/path\.name != 'user_predictions\.csv'|Path\(selected\)\.name != 'user_predictions\.csv'/);
  assert.doesNotMatch(script,/\.fit\(|scene\.render|np\.savez/);
});

test('подготовка длинной серии по пользовательским движениям: генерация, разделение и дубли', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result=spawnSync(python,[path.join(root,'tests','long-user-wing-stimuli-fixture.py')],{cwd:root,env,encoding:'utf8',timeout:60000});
  assert.equal(result.status,0,`${result.stdout}\n${result.stderr}`);
});
test('длинная серия: короткий локальный pilot генератора с условными глазами и 6-осевой ridge', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result=spawnSync(python,[path.join(root,'tests','long-user-wing-local-pilot.py')],{cwd:root,env,encoding:'utf8',timeout:120000});
  assert.equal(result.status,0,`${result.stdout}\n${result.stderr}`);
});

test('заготовка длительной серии: транзакции, восстановление и защита checkpoint', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result=spawnSync(python,[path.join(root,'tests','user-wing-checkpoint-fixture.py')],{cwd:root,env,encoding:'utf8',timeout:60000});
  assert.equal(result.status,0,`${result.stdout}\n${result.stderr}`);
});
test('заготовка длительной серии: checkpoint после реальных кадров двух камер', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result=spawnSync(python,[path.join(root,'tests','user-wing-checkpoint-scene-fixture.py')],{cwd:root,env,encoding:'utf8',timeout:120000});
  assert.equal(result.status,0,`${result.stdout}\n${result.stderr}`);
});

test('прототип длинного обучения: два процесса, сохранение и рестарт с отдельной проверкой', { skip: check.status !== 0 ? 'нужны mujoco, numpy, brian2, pillow' : false }, () => {
  const result=spawnSync(python,[path.join(root,'tests','user-wing-resume-prototype-fixture.py')],{cwd:root,env,encoding:'utf8',timeout:120000});
  assert.equal(result.status,0,`${result.stdout}\n${result.stderr}`);
});
