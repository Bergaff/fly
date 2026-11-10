import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { JSDOM } from 'jsdom';
import React from 'react';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { createServer } from 'vite';

const python=process.env.TWO_FLIES_TEST_PYTHON || 'python3';
const ready=spawnSync(python,['-c','import mujoco,numpy,brian2,PIL']);
test('шесть суставов, углы, независимое обучение и файл повтора', {skip:ready.status!==0?'нужна среда двух мух':false},()=>{
  const result=spawnSync(python,['tests/wing-studio-fixture.py'],{encoding:'utf8',timeout:60000});
  assert.equal(result.status,0,`${result.stdout}\n${result.stderr}`);
});
test('редактор, независимые оси, сохранение, загрузка и ошибки формата',async()=>{
  const dom=new JSDOM('<!doctype html><html><body></body></html>',{url:'http://localhost/'});
  for (const key of ['window','document','navigator','HTMLElement','HTMLCanvasElement','Element','Node','DocumentFragment','NodeFilter','MutationObserver','CustomEvent','Event','MouseEvent','KeyboardEvent','getComputedStyle']) Object.defineProperty(globalThis,key,{value:dom.window[key],configurable:true,writable:true});
  globalThis.localStorage=dom.window.localStorage; globalThis.ResizeObserver=class{observe(){} disconnect(){}};
  globalThis.IS_REACT_ACT_ENVIRONMENT=true;
  dom.window.HTMLCanvasElement.prototype.getContext=()=>null;
  dom.window.confirm=()=>true; globalThis.confirm=dom.window.confirm;
  let saved=null, opened=null;
  dom.window.fly={isElectron:true,saveFile:async opts=>{saved=opts.content;return 'C:\\wing.json'},openFile:async()=>opened};
  const vite=await createServer({configFile:new URL('../vite.config.ts',import.meta.url).pathname,server:{middlewareMode:true},appType:'custom'});
  const {render,fireEvent,screen,waitFor,cleanup}=await import('@testing-library/react');
  const consoleError=console.error;console.error=()=>{};
  try {
    const lib=await vite.ssrLoadModule('/src/lib/wing-trajectory.ts');
    const {WingStudioView}=await vite.ssrLoadModule('/src/views/wing-studio-view.tsx');
    assert.throws(()=>lib.parseTrajectory({...lib.initialTrajectory,duration_s:.51}));
    assert.throws(()=>lib.parseTrajectory({...lib.initialTrajectory,keyframes:[]}));
    assert.deepEqual(lib.interpolate(.25,lib.initialTrajectory),[35,12,10,-25,-8,5]);
    const generated=lib.randomTrajectory(2,()=>.25);
    assert.deepEqual(generated.keyframes.map(k=>k.t),[0,.5,1,1.5,2]);
    assert.ok(generated.keyframes.every(k=>k.angles_deg.every(v=>v===-23)));
    assert.deepEqual(lib.parseTrajectory(generated),generated);
    render(React.createElement(WingStudioView));
    assert.match(document.body.textContent,/ожидает результат/);
    fireEvent.change(screen.getByLabelText('Левое X подъём, градусы'),{target:{value:'25'}});
    assert.equal(screen.getByLabelText('Левое X подъём, градусы').value,'25');
    assert.equal(screen.getByLabelText('Правое X подъём, градусы').value,'0');
    fireEvent.click(screen.getByRole('button',{name:'Сохранить JSON'}));
    await waitFor(()=>assert.ok(saved));
    const t=JSON.parse(saved);assert.equal(t.keyframes[0].angles_deg[0],25);assert.equal(t.keyframes[0].angles_deg[3],0);
    fireEvent.change(screen.getByLabelText('Время просмотра'),{target:{value:'.12'}});
    fireEvent.click(screen.getByRole('button',{name:'Добавить на шкале'}));
    assert.match(document.body.textContent,/Кадр добавлен/);
    fireEvent.click(screen.getByRole('button',{name:'Удалить кадр'}));
    fireEvent.click(screen.getByRole('button',{name:'Сохранить JSON'}));
    await waitFor(()=>assert.equal(JSON.parse(saved).keyframes.length,t.keyframes.length));
    opened={content:'{"bad":true}',path:'bad.json'};fireEvent.click(screen.getByRole('button',{name:'Открыть траекторию'}));
    await waitFor(()=>assert.match(screen.getByRole('status').textContent,/Не удалось открыть/));
    opened={content:JSON.stringify(t),path:'ok.json'};fireEvent.click(screen.getByRole('button',{name:'Открыть траекторию'}));
    await waitFor(()=>assert.match(screen.getByRole('status').textContent,/Траектория загружена/));
    assert.equal(screen.getByLabelText('Левое X подъём, градусы').value,'25');
    if (ready.status === 0) {
      const dir=fs.mkdtempSync(path.join(os.tmpdir(),'fly-wings-'));
      try {
        const source=path.join(dir,'source.json');fs.writeFileSync(source,JSON.stringify(t));
        const actual=spawnSync(python,['experiments/templates/50_two_flies_wing_studio_pilot.py','--trajectory',source,'--output',dir,'--train-count','3','--eval-count','1'],{encoding:'utf8',timeout:60000});
        assert.equal(actual.status,0,`${actual.stdout}\n${actual.stderr}`);
        const run=fs.readdirSync(dir).find(name=>name.startsWith('wing_pilot_'));
        const playback=JSON.parse(fs.readFileSync(path.join(dir,run,'playback.json'),'utf8'));
        assert.equal(lib.parseResult(playback).samples.length,51);
        opened={content:JSON.stringify(playback),path:'playback.json'};
        fireEvent.click(screen.getByRole('button',{name:'Открыть playback.json'}));
        await waitFor(()=>assert.match(screen.getByRole('status').textContent,/Загружен рассчитанный результат/));
      } finally {fs.rmSync(dir,{recursive:true,force:true});}
    }
    if (ready.status === 0) {
      const dir=fs.mkdtempSync(path.join(os.tmpdir(),'fly-user-train-'));
      try {
        const objects=[t,structuredClone(t),structuredClone(t)];
        objects[1].keyframes[0].angles_deg[1]=15;
        objects[2].keyframes[0].angles_deg[1]=30;
        const paths=objects.map((obj,i)=>{const file=path.join(dir,`${i}.json`);fs.writeFileSync(file,JSON.stringify(obj));return file;});
        const actual=spawnSync(python,['experiments/templates/51_two_flies_user_trajectory_learning.py','--train',paths[0],paths[1],'--test',paths[2],'--output',dir],{encoding:'utf8',timeout:60000});
        assert.equal(actual.status,0,`${actual.stdout}\n${actual.stderr}`);
        const run=fs.readdirSync(dir).find(name=>name.startsWith('user_wing_learning_'));
        const playback=JSON.parse(fs.readFileSync(path.join(dir,run,'test_001/playback.json'),'utf8'));
        assert.equal(lib.parseResult(playback).holdout_label,'Все проверочные траектории пользователя');
        opened={content:JSON.stringify(playback),path:'playback.json'};
        fireEvent.click(screen.getByRole('button',{name:'Открыть playback.json'}));
        await waitFor(()=>assert.match(document.body.textContent,/Все проверочные траектории пользователя/));
      } finally {fs.rmSync(dir,{recursive:true,force:true});}
    }
    const samples=Array.from({length:51},(_,i)=>({t:i/25,teacher_deg:lib.interpolate(i/25,t),prediction_deg:i<2?null:[2,4,6,8,10,12]}));
    const metric={new:{rmse_rad:.2},zero:{rmse_rad:.3}};
    opened={content:JSON.stringify({schema:'fly-wings-result-v1',fps:25,duration_s:2,trajectory:t,samples,user_metrics:metric,holdout_metrics:metric}),path:'playback.json'};
    fireEvent.click(screen.getByRole('button',{name:'Открыть playback.json'}));
    await waitFor(()=>assert.match(screen.getByRole('status').textContent,/Загружен рассчитанный результат/));
    fireEvent.click(screen.getByRole('button',{name:'Повтор после показа'}));
    assert.match(document.body.textContent,/не автономная генерация/);
    fireEvent.change(screen.getByLabelText('Левое X подъём, градусы'),{target:{value:'18'}});
    assert.match(document.body.textContent,/ожидает результат/);
    fireEvent.click(screen.getByRole('button',{name:'Случайное движение, шаг 0,5 с'}));
    assert.match(screen.getByRole('status').textContent,/Создана новая случайная траектория/);
    assert.equal(screen.getAllByRole('button',{name:/с$/}).filter(b=>/^\d+\.\d{2} с$/.test(b.textContent || '')).length,5);
  } finally { cleanup();console.error=consoleError;await vite.close();dom.window.close(); }
});
