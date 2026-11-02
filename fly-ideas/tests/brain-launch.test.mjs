import { test } from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
import React from 'react';
import { createServer } from 'vite';

// Реальный React-интерфейс и подставной Electron IPC; тяжёлые расчёты не запускаются.
test('кнопки топ-200: выбор, запуск, быстрый выход, ошибка и установка в окружении', async () => {
  const dom = new JSDOM('<!doctype html><html><body></body></html>', {url:'http://localhost/'});
  for (const key of ['window','document','navigator','HTMLElement','HTMLFormElement','HTMLInputElement','HTMLButtonElement','Element','Node','DocumentFragment','NodeFilter','MutationObserver','CustomEvent','Event','MouseEvent','KeyboardEvent','getComputedStyle']) {
    Object.defineProperty(globalThis,key,{value:dom.window[key], configurable:true, writable:true});
  }
  globalThis.IS_REACT_ACT_ENVIRONMENT = true;
  dom.window.HTMLElement.prototype.scrollTo = function() {};
  dom.window.HTMLElement.prototype.scrollIntoView = function() {};
  globalThis.ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
  let output = () => {}, calls = [], quick = true, failStart = false, delayStart = false, releaseStart, prepare = {name:'27_shiu_top200_v630.py',matches:true,conflict:null,added:[]}, resumePath='C:\\run with space';
  const py={exe:'python',cmd:'python',version:'3.11',source:'test',majorMinor:[3,11],hasCore:true,okMap:{},note:''};
  const env={python:py,packages:{numpy:'1',pandas:'1',scipy:'1',matplotlib:'1',pyarrow:'1',duckdb:'1',brian2:'1',joblib:'1'},conda:null,gpu:null};
  const paths={projectId:'idea:i',code:'C:\\idea\\code',runs:'C:\\idea\\runs',defaults:{code:'C:\\idea\\code',runs:'C:\\idea\\runs'}};
  dom.window.fly = {
    isElectron:true, getActiveRun:async()=>null, projectPaths:async()=>paths, listScripts:async()=>[],listRuns:async()=>[],
    getPermissions:async()=>({runScripts:true,createFiles:true,overwriteFiles:false}),
    onRunOutput:cb=>{output=cb;return()=>{}}, prepareTop200:async()=>prepare,
    pickFolder:async()=>resumePath,
    runScript:async(scope,name,args)=>{calls.push({scope,name,args});
      // Событие приходит до разрешения IPC. Прогон не должен остаться «выполняется».
      if (failStart) throw new Error("Запуск скриптов выключен");
      if (quick) output({runId:`r${calls.length}`,projectId:scope,runDir:'C:\\run',stream:'exit',text:'done',code:0});
      if (delayStart) await new Promise(resolve => {releaseStart=resolve;});
      return {runId:`r${calls.length}`,runDir:'C:\\run'};
    },
    readRun:async()=>({log:'',summary:null}),readRunFile:async()=>({kind:'text',text:''}),
    checkEnv:async()=>env,listPythons:async()=>[py],onEnvSetupOutput:()=>()=>{},
    agentInfo:async()=>null,listData:async()=>[],getPaths:async()=>null,listExternal:async()=>[],getDataFileLinks:async()=>({}),onDownloadProgress:()=>()=>{},
  };
  const vite=await createServer({configFile: new URL('../vite.config.ts', import.meta.url).pathname,server:{middlewareMode:true},appType:'custom'});
  const {render,fireEvent,screen,waitFor,cleanup,act}=await import('@testing-library/react');
  try {
    const {BrainView}=await vite.ssrLoadModule('/src/views/brain-view.tsx');
    const noop=()=>{};
    render(React.createElement(BrainView,{ideas:[{id:'i',projectId:'p',title:'Лезии',checklist:[],citations:[],links:[]}],projects:[{id:'p',name:'Проект',color:'#777'}],activeProject:'p',onSelectProject:noop,onAddProject:noop,onAddIdea:noop,onOpenIdeaCard:noop,onUpdateIdea:noop,onCompleteStages:noop,onAddJournalEntry:noop,onAddReferences:noop,onDirtyChange:noop}));
    const top=await screen.findByRole('button',{name:'топ-200'});
    fireEvent.click(top);
    assert.equal(calls.length,0);
    assert.match(screen.getByRole('dialog').textContent,/200 Гц/);
    fireEvent.click(screen.getByRole('button',{name:'пилот: 1 повтор'}));
    await waitFor(()=>assert.equal(calls.length,1));
    assert.deepEqual(calls[0],{scope:'idea:i',name:'27_shiu_top200_v630.py',args:['--simulate','--pilot']});
    await waitFor(()=>assert.equal(top.disabled,false));
    assert.match(document.body.textContent,/Прогон завершён, код 0/);
    fireEvent.click(top);
    fireEvent.click(screen.getByRole('button',{name:'начать полный расчёт: 30 повторов'}));
    await waitFor(()=>assert.equal(calls.length,2));
    assert.deepEqual(calls[1].args,['--simulate']);
    await waitFor(()=>assert.equal(top.disabled,false));
    fireEvent.click(top);
    fireEvent.click(screen.getByRole('button',{name:'продолжить из папки прогона'}));
    await waitFor(()=>assert.equal(calls.length,3));
    assert.deepEqual(calls[2].args,['--simulate','--resume-from',resumePath]);
    await waitFor(()=>assert.equal(top.disabled,false));
    prepare={...prepare,matches:false,conflict:'25_shiu_v630_control.py'};
    fireEvent.click(top);fireEvent.click(screen.getByRole('button',{name:'пилот: 1 повтор'}));
    await waitFor(()=>assert.match(document.body.textContent,/Файл 25_shiu_v630_control.py изменён/));
    assert.equal(calls.length,3);
    prepare={...prepare,matches:true,conflict:null};
    resumePath=null;
    fireEvent.click(top);fireEvent.click(screen.getByRole('button',{name:'продолжить из папки прогона'}));
    await waitFor(()=>assert.match(document.body.textContent,/Продолжение отменено/));
    assert.equal(calls.length,3);
    quick=false; delayStart=true;
    fireEvent.click(top); fireEvent.click(screen.getByRole('button',{name:'пилот: 1 повтор'}));
    await waitFor(()=>assert.equal(calls.length,4));
    await screen.findByText(/Подготовка запуска 27_shiu_top200_v630.py/);
    assert.equal(top.disabled,true);
    await act(async()=>releaseStart());
    delayStart=false;
    await screen.findByRole('button',{name:'остановить расчёт'});
    assert.equal(top.disabled,true);
    act(()=>output({runId:'r4',projectId:'idea:i',runDir:'C:\\run',stream:'exit',text:'done',code:0}));
    await waitFor(()=>assert.equal(top.disabled,false));
    failStart=true;
    fireEvent.click(top); fireEvent.click(screen.getByRole('button',{name:'пилот: 1 повтор'}));
    await waitFor(()=>assert.match(document.body.textContent,/Не удалось запустить.*Запуск скриптов выключен/));
    assert.equal(calls.length,5);
    // Ошибка зависимости ведёт в раздел установки, без автоматического повтора.
    act(()=>output({runId:'external',projectId:'idea:i',stream:'stderr',text:"ModuleNotFoundError: No module named 'joblib'"}));
    const goto=await screen.findByRole('button',{name:'данные и окружение'});
    fireEvent.click(goto);
    await screen.findByText(/Последний прогон сообщил/);
    assert.ok(await screen.findByRole('button',{name:'установить Brian2 и joblib'}));
    assert.equal(calls.length,5);
    // При возвращении на вкладку уже идущий процесс снова доступен для остановки.
    cleanup();
    dom.window.fly.getActiveRun=async()=>({runId:'old-run',runDir:'C:\\old'});
    render(React.createElement(BrainView,{ideas:[{id:'i',projectId:'p',title:'Лезии',checklist:[],citations:[],links:[]}],projects:[{id:'p',name:'Проект',color:'#777'}],activeProject:'p',onSelectProject:noop,onAddProject:noop,onAddIdea:noop,onOpenIdeaCard:noop,onUpdateIdea:noop,onCompleteStages:noop,onAddJournalEntry:noop,onAddReferences:noop,onDirtyChange:noop}));
    await screen.findByRole('button',{name:'остановить расчёт'});
    act(()=>output({runId:'old-run',projectId:'idea:i',stream:'exit',text:'done',code:0}));
    await waitFor(()=>assert.equal(screen.getByRole('button',{name:'топ-200'}).disabled,false));
    // Если ответ о работающем процессе устарел до прихода в UI, кнопки не блокируются.
    cleanup();
    let releaseStatus;
    dom.window.fly.getActiveRun=()=>new Promise(resolve=>{releaseStatus=resolve});
    render(React.createElement(BrainView,{ideas:[{id:'i',projectId:'p',title:'Лезии',checklist:[],citations:[],links:[]}],projects:[{id:'p',name:'Проект',color:'#777'}],activeProject:'p',onSelectProject:noop,onAddProject:noop,onAddIdea:noop,onOpenIdeaCard:noop,onUpdateIdea:noop,onCompleteStages:noop,onAddJournalEntry:noop,onAddReferences:noop,onDirtyChange:noop}));
    act(()=>output({runId:'stale',projectId:'idea:i',stream:'exit',text:'done',code:0}));
    await act(async()=>releaseStatus({runId:'stale',runDir:'C:\\old'}));
    assert.equal(screen.getByRole('button',{name:'топ-200'}).disabled,false);
    assert.equal(screen.queryByRole('button',{name:'остановить расчёт'}),null);
  } catch (e) { if (e.errors) console.error(e.errors); throw e; } finally {cleanup();await vite.close();dom.window.close();}
});
