const test = require('node:test');
const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');
const crypto = require('node:crypto');
const root = path.join(__dirname, '..');
test('авторский код сохраняется без изменений и без Windows-конвертации строк', () => {
  const file = fs.readFileSync(path.join(root, 'experiments/templates/26_shiu_author_model.py'));
  assert.equal(crypto.createHash('sha256').update(file).digest('hex'), 'fc45837d7122c6ce2a7f3f2f23c515992e4b232aadb919efabb72337fac88e4e');
  assert.match(fs.readFileSync(path.join(root, '.gitattributes'), 'utf8'), /26_shiu_author_model\.py text eol=lf/);
});
const python = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean).find(p => spawnSync(p, ['-c', 'import numpy, pandas, pyarrow, brian2, joblib']).status === 0);
test('сверка с оригинальным model.py и защита входных файлов на искусственной сети', {skip: !python && 'нужны numpy, pandas, pyarrow, brian2, joblib'}, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-original-'));
  try {
    const r = spawnSync(python, [path.join(root, 'tests/shiu-original-fixture.py'), dir], {cwd:root, encoding:'utf8', timeout:120000, env:{...process.env, PYTHONIOENCODING:'utf-8'}});
    assert.equal(r.status, 0, r.stdout+'\n'+r.stderr);
  } finally { fs.rmSync(dir, {recursive:true,force:true}); }
});
