const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const root = path.join(__dirname, '..');
const python = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean).find(p => spawnSync(p, ['-c', 'import numpy, pandas, pyarrow, brian2, joblib']).status === 0);
test('контроль v630 сверяет исходные данные и совпадает с авторским ядром на искусственной сети', {skip: !python && 'нужны numpy, pandas, pyarrow, brian2, joblib'}, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-v630-'));
  try {
    const r = spawnSync(python, [path.join(root, 'tests/shiu-v630-fixture.py'), dir], {cwd: root, encoding:'utf8', timeout:120000, env:{...process.env, PYTHONIOENCODING:'utf-8'}});
    assert.equal(r.status, 0, r.stdout + '\n' + r.stderr);
  } finally { fs.rmSync(dir, {recursive:true, force:true}); }
});
