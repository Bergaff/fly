const test = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const python = [process.env.FLY_TEST_PYTHON,'python3','python'].filter(Boolean).find(p=>spawnSync(p,['-c','import numpy,pandas,pyarrow,matplotlib,brian2,joblib']).status===0);
test('обзор лезий, индивидуальность, выборка, пары и безопасный resume', {skip:!python && 'нужны numpy, matplotlib, brian2', timeout:120000},()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'fly-focused-'));
  try {
    const r=spawnSync(python,[path.join(__dirname,'shiu-focused-fixture.py'),dir],{encoding:'utf8',timeout:110000,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
    assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});
test('выборочные лезии: настоящая валидация входов и Brian2 на искусственной сети', {skip:!python && 'нужны numpy, matplotlib, brian2', timeout:180000},()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'fly-focused-real-'));
  try {
    const r=spawnSync(python,[path.join(__dirname,'shiu-selected-real-fixture.py'),dir],{encoding:'utf8',timeout:170000,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
    assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});
