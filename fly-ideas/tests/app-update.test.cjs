const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const python = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean).find(p => spawnSync(p, ['-c', 'import sys']).status === 0);
test('обновление ветки: проверки архива, защита данных, резервные копии и откат', {skip: !python && 'нужен Python'}, () => {
  const r = spawnSync(python, [path.join(__dirname, 'app-update-fixture.py')], {encoding:'utf8',timeout:30000});
  assert.equal(r.status, 0, r.stdout+'\n'+r.stderr);
});

test('журнал обновления переживает новое чтение и не следует ссылкам', () => {
  const fs = require('node:fs'), os = require('node:os');
  const store = require('../electron/app-update-status.cjs');
  const app = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-update-status-'));
  try {
    const first = { state: 'error', message: 'Ошибка сети', phase: 'prepare' };
    store.writeStatus(app, first);
    assert.deepEqual(store.readStatus(app), first);
    store.writeStatus(app, { state: 'completed', message: 'Готово' });
    assert.deepEqual(store.readStatus(app), { state: 'completed', message: 'Готово' });
    fs.unlinkSync(store.statusPath(app));
    try { fs.symlinkSync(path.join(app, 'outside.txt'), store.statusPath(app)); }
    catch (e) { if (!['EPERM', 'EACCES', 'ENOSYS'].includes(e.code)) throw e; return; }
    assert.equal(store.readStatus(app), null);
    store.writeStatus(app, first);
    assert.equal(fs.existsSync(path.join(app, 'outside.txt')), false);
    assert.deepEqual(store.readStatus(app), first);
  } finally { fs.rmSync(app, { recursive: true, force: true }); }
});


test('снимок обновления не инициирует Vite watcher', () => {
  const env = { ...process.env }; delete env.NODE_TEST_CONTEXT;
  const r = spawnSync(process.execPath, ['--test', path.join(__dirname, 'update-watch.test.mjs')], { encoding:'utf8', timeout:30000, env });
  assert.equal(r.status, 0, r.stdout + '\n' + r.stderr);
  assert.match(r.stdout, /# pass 1/);
});
test('диагностика конфликта и безопасная пауза снимка без потери данных', {skip: !python && 'нужен Python'}, () => {
  const r = spawnSync(python, [path.join(__dirname, 'update-recovery-fixture.py')], {encoding:'utf8',timeout:30000});
  assert.equal(r.status, 0, r.stdout+'\n'+r.stderr);
});

// Проверка безопасного восстановления отсутствующей зависимости 3D.
require('./repair-three.test.cjs');
