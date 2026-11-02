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
  let output = () => {}, calls = [], quick = true, failStart = false, delayStart = false, releaseStart, prepare = {name:'27_shiu_top200_v630.py',matches:true,conflict:null,added:[],code:'C:\\idea\\code\\.shiu-top200-v630'}, resumePath='C:\\run with space';
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
  dom.window.fly.runTop200=(scope,args)=>dom.window.fly.runScript(scope,'27_shiu_top200_v630.py',args);
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
    await waitFor(()=>assert.match(document.body.textContent,/Проверочная копия 25_shiu_v630_control.py изменена/));
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
    // Запуск лезий требует выбор проверенного источника и явный выбор режима.
    failStart=false;quick=true;resumePath='C:\\top run';
    dom.window.fly.prepareLesions=async()=>({name:'28_shiu_lesions_v630.py',matches:true,conflict:null,added:[],code:'C:\\lesions'});
    dom.window.fly.runLesions=(scope,args)=>dom.window.fly.runScript(scope,'28_shiu_lesions_v630.py',args);
    fireEvent.click(screen.getByRole('button',{name:'Код и результаты'}));
    fireEvent.click(screen.getByRole('button',{name:'лезии v630'}));
    assert.match(screen.getByRole('dialog').textContent,/48 240/);
    assert.equal(calls.length,5);
    fireEvent.click(screen.getByRole('button',{name:'пилот: контроль и одна лезия'}));
    await waitFor(()=>assert.equal(calls.length,6));
    assert.deepEqual(calls[5].args,['--simulate','--top-run',resumePath,'--pilot']);
    await waitFor(()=>assert.equal(screen.getByRole('button',{name:'лезии v630'}).disabled,false));
    let selectedFolders=['C:\\top folder','C:\\lesion folder'];
    dom.window.fly.pickFolder=async()=>selectedFolders.shift() ?? null;
    fireEvent.click(screen.getByRole('button',{name:'лезии v630'}));
    fireEvent.click(screen.getByRole('button',{name:'продолжить из папки лезий'}));
    await waitFor(()=>assert.equal(calls.length,7));
    assert.deepEqual(calls[6].args,['--simulate','--top-run','C:\\top folder','--resume-from','C:\\lesion folder']);
    await waitFor(()=>assert.equal(screen.getByRole('button',{name:'лезии v630'}).disabled,false));
    dom.window.fly.prepareParallelLesions=async()=>({name:'29_shiu_lesions_parallel.py',matches:true,conflict:null,added:[],code:'C:\\lesions'});
    dom.window.fly.runParallelLesions=(scope,args)=>dom.window.fly.runScript(scope,'29_shiu_lesions_parallel.py',args);
    selectedFolders=['C:\\top folder','C:\\last lesion run'];
    fireEvent.click(screen.getByRole('button',{name:'лезии v630'}));
    assert.match(screen.getByRole('dialog').textContent,/8 ГиБ свободной RAM/);
    fireEvent.click(screen.getByRole('button',{name:'продолжить: 2 процесса'}));
    await waitFor(()=>assert.equal(calls.length,8));
    assert.equal(calls[7].name,'29_shiu_lesions_parallel.py');
    assert.deepEqual(calls[7].args,['--simulate','--top-run','C:\\top folder','--resume-from','C:\\last lesion run']);
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
    // Общий набор: топ выбирают один раз, затем не выбирают файлы SQLite.
    cleanup();dom.window.fly.getActiveRun=async()=>null;
    const studyId='Study_20261102_123456_abcdef12';
    dom.window.fly.listSharedStudies=async()=>({root:'C:\\data\\shiu-v630-shared',studies:[{id:studyId,label:'Новый набор',path:'C:\\data\\study',created:1,progress:null}]});
    dom.window.fly.prepareSharedStudy=async()=>({name:'32_shiu_shared_study.py',matches:true,conflict:null,added:[],code:'C:\\focused'});
    dom.window.fly.runSharedStudy=(scope,args)=>dom.window.fly.runScript(scope,args[1].startsWith('holdout-')?'35_shiu_individuality_holdout.py':args[1].startsWith('extend-')?'34_shiu_individuality_extension.py':args[1].startsWith('pilot-')?'33_shiu_individuality_pilot.py':'32_shiu_shared_study.py',args);
    dom.window.fly.prepareFocusedLesions=async(_scope,mode)=>({name:mode==='overview'?'30_shiu_lesion_overview.py':'31_shiu_selected_lesions.py',matches:true,conflict:null,added:[],code:'C:\\focused'});
    dom.window.fly.runFocusedLesions=(scope,mode,args)=>dom.window.fly.runScript(scope,mode==='overview'?'30_shiu_lesion_overview.py':'31_shiu_selected_lesions.py',args);
    const commonProps={projects:[{id:'p',name:'Проект',color:'#777'}],activeProject:'p',onSelectProject:noop,onAddProject:noop,onAddIdea:noop,onOpenIdeaCard:noop,onUpdateIdea:noop,onCompleteStages:noop,onAddJournalEntry:noop,onAddReferences:noop,onDirtyChange:noop};
    const oneStudy=dom.window.fly.listSharedStudies;
    dom.window.fly.listSharedStudies=async()=>{const info=await oneStudy();return {...info,studies:[...info.studies,{...info.studies[0],id:'Study_second',label:'Другой набор'}]};};
    render(React.createElement(BrainView,{...commonProps,ideas:[{id:'i-lesions',projectId:'p',title:'Лезии',checklist:[],citations:[],links:[]}]}));
    fireEvent.click(await screen.findByRole('button',{name:'выборочные лезии'}));
    await waitFor(()=>assert.match(screen.getByRole('dialog').textContent,/выберите набор/));
    assert.equal(screen.getByRole('button',{name:'план без симуляций'}).disabled,true);
    cleanup();dom.window.fly.listSharedStudies=oneStudy;
    render(React.createElement(BrainView,{...commonProps,ideas:[{id:'i-lesions',projectId:'p',title:'Лезии',checklist:[],citations:[],links:[]}]}));
    selectedFolders=['C:\\top'];
    fireEvent.click(await screen.findByRole('button',{name:'выборочные лезии'}));
    assert.match(screen.getByRole('dialog').textContent,/Топ-200 выбирается один раз/);
    fireEvent.click(screen.getByRole('button',{name:'создать набор из топ-200'}));
    await waitFor(()=>assert.equal(calls.length,9));
    assert.deepEqual(calls[8],{scope:'idea:i-lesions',name:'32_shiu_shared_study.py',args:['--stage','init','--top-run','C:\\top']});
    await waitFor(()=>assert.equal(screen.getByRole('button',{name:'выборочные лезии'}).disabled,false));
    fireEvent.click(screen.getByRole('button',{name:'выборочные лезии'}));
    const plan=await screen.findByRole('button',{name:'план без симуляций'});
    await waitFor(()=>assert.equal(plan.disabled,false));fireEvent.click(plan);
    await waitFor(()=>assert.equal(calls.length,10));
    assert.deepEqual(calls[9].args,['--stage','plan','--study',studyId]);
    await waitFor(()=>assert.equal(screen.getByRole('button',{name:'выборочные лезии'}).disabled,false));
    fireEvent.click(screen.getByRole('button',{name:'выборочные лезии'}));
    const pairs=await screen.findByRole('button',{name:'рассчитать или продолжить пары и группу'});
    await waitFor(()=>assert.equal(pairs.disabled,false));fireEvent.click(pairs);
    await waitFor(()=>assert.equal(calls.length,11));
    assert.deepEqual(calls[10].args,['--stage','all','--study',studyId]);
    cleanup();
    render(React.createElement(BrainView,{...commonProps,ideas:[{id:'i-individuality',projectId:'p',title:'Индивидуальность',checklist:[],citations:[],links:[]}]}));
    fireEvent.click(await screen.findByRole('button',{name:'контроли v630'}));
    assert.match(screen.getByRole('dialog').textContent,/не устойчивыми индивидуальными фенотипами/);
    const overview=await screen.findByRole('button',{name:'построить обзор общих контролей'});
    await waitFor(()=>assert.equal(overview.disabled,false));fireEvent.click(overview);
    await waitFor(()=>assert.equal(calls.length,12));
    assert.deepEqual(calls[11],{scope:'idea:i-individuality',name:'32_shiu_shared_study.py',args:['--stage','individuality','--study',studyId]});
    for (const [name,stage,index] of [['план пилота без симуляций','pilot-plan',12],['рассчитать или продолжить пилот','pilot-run',13],['обзор сохранённого пилота','pilot-review',14]]) {
      await waitFor(()=>assert.equal(screen.getByRole('button',{name:'контроли v630'}).disabled,false));
      fireEvent.click(screen.getByRole('button',{name:'контроли v630'}));
      const button=await screen.findByRole('button',{name});await waitFor(()=>assert.equal(button.disabled,false));fireEvent.click(button);
      await waitFor(()=>assert.equal(calls.length,index+1));
      assert.deepEqual(calls[index],{scope:'idea:i-individuality',name:'33_shiu_individuality_pilot.py',args:['--stage',stage,'--study',studyId]});
    }
    for (const [name,stage,index] of [['план продолжения до 10 seed','extend-plan',15],['рассчитать или продолжить 70 повторов','extend-run',16],['обзор продолжения на 10 seed','extend-review',17]]) {
      await waitFor(()=>assert.equal(screen.getByRole('button',{name:'контроли v630'}).disabled,false));
      fireEvent.click(screen.getByRole('button',{name:'контроли v630'}));
      const button=await screen.findByRole('button',{name});await waitFor(()=>assert.equal(button.disabled,false));fireEvent.click(button);
      await waitFor(()=>assert.equal(calls.length,index+1));
      assert.deepEqual(calls[index],{scope:'idea:i-individuality',name:'34_shiu_individuality_extension.py',args:['--stage',stage,'--study',studyId]});
    }
    for (const [name,stage,index] of [['план проверки на новых seed','holdout-plan',18],['рассчитать или продолжить проверку: 100 повторов','holdout-run',19],['обзор проверки на новых seed','holdout-review',20]]) {
      await waitFor(()=>assert.equal(screen.getByRole('button',{name:'контроли v630'}).disabled,false));
      fireEvent.click(screen.getByRole('button',{name:'контроли v630'}));
      const button=await screen.findByRole('button',{name});await waitFor(()=>assert.equal(button.disabled,false));fireEvent.click(button);
      await waitFor(()=>assert.equal(calls.length,index+1));
      assert.deepEqual(calls[index],{scope:'idea:i-individuality',name:'35_shiu_individuality_holdout.py',args:['--stage',stage,'--study',studyId]});
    }


  } catch (e) { if (e.errors) console.error(e.errors); throw e; } finally {cleanup();await vite.close();dom.window.close();}
});
