const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const root = path.join(__dirname, '..');
const python = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean).find(p => spawnSync(p, ['-c', 'import numpy, pandas, brian2, joblib']).status === 0);

test('проверка, блокировки и сравнение ядра с авторской моделью на искусственных данных', { skip: !python && 'нужны numpy, pandas, brian2, joblib' }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-shiu-adapted-'));
  try {
    const result = spawnSync(python, [path.join(root, 'tests/shiu-mn9-fixture.py'), dir], { cwd: root, encoding: 'utf8', timeout: 120000, env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
    assert.equal(result.status, 0, result.stdout + '\n' + result.stderr);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
