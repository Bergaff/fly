const test = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const root = path.join(__dirname, '..');
const python = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean).find(p => spawnSync(p, ['-c', 'import duckdb, pandas, pyarrow, matplotlib']).status === 0);
test('сравнение таблиц: объединение пар, знаки, границы ID и повреждённые входы', {skip: !python && 'нужны duckdb, pandas, pyarrow, matplotlib'}, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-compare-'));
  try {
    const res = spawnSync(python, [path.join(root, 'tests/compare-shiu-fixture.py'), dir], {encoding:'utf8', timeout:120000, cwd:root, env:{...process.env, PYTHONIOENCODING:'utf-8'}});
    assert.equal(res.status,0,res.stdout+'\n'+res.stderr);
  } finally { fs.rmSync(dir,{recursive:true,force:true}); }
});
