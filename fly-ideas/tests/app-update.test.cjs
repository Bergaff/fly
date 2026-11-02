const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const python = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean).find(p => spawnSync(p, ['-c', 'import sys']).status === 0);
test('обновление ветки: проверки архива, защита данных, резервные копии и откат', {skip: !python && 'нужен Python'}, () => {
  const r = spawnSync(python, [path.join(__dirname, 'app-update-fixture.py')], {encoding:'utf8',timeout:30000});
  assert.equal(r.status, 0, r.stdout+'\n'+r.stderr);
});
