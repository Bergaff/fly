const test = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const python = [process.env.FLY_TEST_PYTHON,'python3','python'].filter(Boolean).find(p=>spawnSync(p,['-c','import numpy,pandas,pyarrow,brian2,joblib']).status===0);
test('лезии: исходящее отключение, авторское ядро, контроль отбора и resume', {skip:!python && 'нужны numpy, pandas, pyarrow, brian2, joblib'},()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'fly-lesion-'));
  try {
    const result=spawnSync(python,[path.join(__dirname,'shiu-lesions-fixture.py'),dir],{encoding:'utf8',timeout:120000,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
    assert.equal(result.status,0,result.stdout+'\n'+result.stderr);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});
