const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const python = process.env.SHIU_PATH_TEST_PYTHON || 'python3';
const check = spawnSync(python, ['-c', 'import numpy, pyarrow']);
test('ранг 62: прямые и двухшаговые пути, проверка ID и источника', {skip: check.status !== 0 ? 'нужны numpy и pyarrow' : false}, () => {
  const result = spawnSync(python, [path.join(root, 'tests', 'shiu-rank62-paths-fixture.py')], {cwd: root, encoding: 'utf8', timeout: 60000});
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
});
