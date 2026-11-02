const test = require('node:test');
const assert = require('node:assert/strict');
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const python = [process.env.FLY_TEST_PYTHON,'python3','python'].filter(Boolean).find(p=>spawnSync(p,['-c','import numpy,pandas,pyarrow,brian2,psutil']).status===0);
test('самостоятельный Colab notebook: структура, встроенный код и безопасные значения',()=>{
  const p=process.env.FLY_TEST_PYTHON||'python3';
  const r=spawnSync(p,[path.join(__dirname,'colab-notebook-check.py')],{encoding:'utf8'});
  assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
});
test('Colab bootstrap: независимый Python, проверка целостности и безопасное извлечение',()=>{
  const p=process.env.FLY_TEST_PYTHON||'python3';
  const r=spawnSync(p,[path.join(__dirname,'colab-bootstrap-check.py')],{encoding:'utf8'});
  assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
});
test('GPU-пилот CUDA 13: C++17 без изменения кода CPU и отдельный журнал компиляции',()=>{
  const p=process.env.FLY_TEST_PYTHON||'python3';
  const r=spawnSync(p,[path.join(__dirname,'colab-gpu-wrapper-check.py')],{encoding:'utf8'});
  assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
});
test('Повторное использование сборки: малая сеть C++ standalone, не CUDA', {skip:(!python || spawnSync('g++',['--version']).status!==0) && 'нужны Brian2 и g++',timeout:60000},()=>{
  const r=spawnSync(python,[path.join(__dirname,'colab-gpu-reuse-check.py')],{encoding:'utf8',timeout:55000,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
  assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
});
test('Colab CPU: проверка топа, настоящая малая сеть Brian2, снимки, продолжение и ветви', {skip:!python && 'нужны numpy, pandas, pyarrow, brian2, psutil',timeout:180000},()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'fly-colab-'));
  try {
    const r=spawnSync(python,[path.join(__dirname,'colab-fixture.py'),dir],{encoding:'utf8',timeout:170000,env:{...process.env,PYTHONIOENCODING:'utf-8'}});
    assert.equal(r.status,0,r.stdout+'\n'+r.stderr);
  } finally {fs.rmSync(dir,{recursive:true,force:true});}
});
