const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const root = path.resolve(__dirname, '..');
function load(file, aliases = {}, extras = {}, appended = '') {
  const source = fs.readFileSync(path.join(root, file), 'utf8') + appended;
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, require: (name) => aliases[name] || require(name), structuredClone, console, ...extras });
  return module.exports;
}
const memory = load('src/data/research-memory.ts');
const plain = (v) => JSON.parse(JSON.stringify(v));

test('архив устанавливается один раз, сохраняет прежние записи и разделяет идеи', () => {
  const custom = { id: 'custom', title: 'Моя запись', ideaId: 'i-lesions', results: 'не перезаписывать', files: [] };
  const old = { version: 'old', entries: [custom] };
  const merged = memory.installResearchMemory(old);
  assert.equal(merged.entries[0], custom);
  assert.equal(merged.entries.length, memory.RESEARCH_MEMORY.length + 1);
  assert.strictEqual(memory.installResearchMemory(merged), merged);
  assert.deepEqual(plain(old.entries), [custom]);
  const renamed = {...merged, entries: merged.entries.filter((entry) => entry.id !== 'session-v630-top200')};
  assert.strictEqual(memory.installResearchMemory(renamed), renamed);
  assert.equal(memory.memoryForIdea(merged,'i-individuality').length, 1);
  assert.ok(memory.memoryForIdea(merged,'i-lesions').length >= 4);
  assert.equal(memory.memoryForIdea(merged,'неизвестная').length, 0);
});

test('загрузка старого состояния добавляет память не меняя идеи, заметки и отметки', () => {
  const initial = { version: 1, ideas:[{id:'custom', notes:'МОЙ ТЕКСТ',checklist:[{id:'x',done:false}],experiments:[{id:'local',result:'важно'}]}], projects:[{id:'p'}], references:[], seeded:[] };
  let saved = JSON.stringify(initial);
  const localStorage = { getItem: () => saved, setItem: (_key, val) => { saved = val; } };
  const sessionStorage = { removeItem: () => {}, getItem: () => null };
  const seed = { SEED_STATE: { version:1, ideas:[], projects:[], references:[] }, makeChecklist: () => [] };
  const store = load('src/data/store.ts', {'./seed': seed, './research-memory': memory, '@/lib/utils': {uid: () => 'x'}}, {localStorage,sessionStorage}, '\nexport { load };');
  const result = store.load();
  assert.equal(result.ideas[0].notes, 'МОЙ ТЕКСТ');
  assert.equal(result.ideas[0].checklist[0].done, false);
  assert.equal(result.ideas[0].experiments[0].result, 'важно');
  assert.equal(result.researchMemory.entries.length, memory.RESEARCH_MEMORY.length);
  assert.equal(saved, JSON.stringify(initial));
  localStorage.setItem('fly-ideas:state:v1', JSON.stringify(result));
  assert.deepEqual(plain(store.load().researchMemory), plain(result.researchMemory));
});

test('архив виден в программе, пути и ограничения явно помечены', () => {
  const view = load('src/views/research-memory-view.tsx', {'@/lib/bridge': {fly:null}});
  const html = renderToStaticMarkup(React.createElement(view.ResearchMemoryView, {memory:memory.installResearchMemory()}));
  assert.match(html,/Память исследований и пути/);
  assert.match(html,/720575940623211725/);
  assert.match(html,/630\/630/);
  assert.match(html,/наличие здесь не проверено/);
  assert.ok(html.includes('E:\\ass\\fly\\fly-ideas'));
  const app = fs.readFileSync(path.join(root, 'src/App.tsx'),'utf8');
  const brain = fs.readFileSync(path.join(root, 'src/views/brain-view.tsx'),'utf8');
  assert.match(app, /<ResearchMemoryView memory=\{state\.researchMemory\}/);
  assert.match(brain, /provider === "deepseek" && sendMemory && contextIdea/);
  assert.match(brain, /memoryForIdea\(researchMemory, contextIdea\.id\)/);
  assert.match(brain, /пути не передаются/);
});

test('восьмичасовой пользовательский результат отделён от локального пилота', () => {
  const item = memory.RESEARCH_MEMORY.find((entry) => entry.id === 'session-observation-long-imitation-user');
  assert.ok(item);
  assert.equal(item.ideaId, 'i-observational');
  assert.match(item.results, /144376|0,155050/);
  assert.match(item.results, /36.*28/);
  assert.match(item.results, /0,185470.*0,147418/);
  assert.match(item.limitations, /не слепой/);
  assert.match(item.limitations, /не проверены/);
  assert.ok(item.files.some((file) => file.includes('two-flies-long-imitation-user-report.md')));
});

test('выписка 64 последовательностей воспроизводит агрегаты и основные срезы', () => {
  const lines = fs.readFileSync(path.join(root, 'experiments/reports/two-flies-long-imitation-user-rounded.csv'), 'utf8').trim().split(/\r?\n/);
  assert.equal(lines.shift(), 'id,shape,freq,phase,distance,offset,amplitude,new,old,zero');
  const rows = lines.map((line) => {
    const [id,shape,freq,phase,distance,offset,amplitude,latest,old,zero] = line.split(',');
    return {id:Number(id),shape,freq:+freq,phase:+phase,distance:+distance,offset:+offset,amplitude:+amplitude,latest:+latest,old:+old,zero:+zero};
  });
  assert.equal(rows.length,64);
  assert.deepEqual(rows.map((row)=>row.id), Array.from({length:64},(_,i)=>i));
  for (const [key, expected] of [['latest',0.155050],['old',0.214169],['zero',0.362799]]) {
    const rmse = Math.sqrt(rows.reduce((acc,row)=>acc+row[key]**2,0)/rows.length);
    assert.ok(Math.abs(rmse-expected)<0.0000006, `${key}: ${rmse}`);
  }
  const outcomes = {sine:[6,5],harmonic:[2,9],chirp:[6,4],asymmetric:[22,10]};
  for (const [shape, [wins, losses]] of Object.entries(outcomes)) {
    const group=rows.filter((row)=>row.shape===shape);
    assert.equal(group.filter((row)=>row.latest<row.old).length,wins);
    assert.equal(group.filter((row)=>row.latest>row.old).length,losses);
  }
  assert.deepEqual(rows.filter((row)=>row.latest>row.zero).map((row)=>row.id),[48,62]);
  const improvement=(row)=>row.old**2-row.latest**2;
  const contribution=rows.filter((row)=>[34,48,60,62].includes(row.id)).reduce((a,row)=>a+improvement(row),0)/rows.reduce((a,row)=>a+improvement(row),0);
  assert.ok(Math.abs(contribution-0.793)<0.001);
  const entry=memory.RESEARCH_MEMORY.find((item)=>item.id==='session-observation-long-imitation-user-sequences');
  assert.ok(entry);
  assert.match(entry.limitations,/не слепая/);
});

test('покадровая выписка воспроизводит смещение и насыщение для ID 48 и 62', () => {
  const text = fs.readFileSync(path.join(root,'experiments/reports/two-flies-long-imitation-user-frames-48-62-rounded.csv'),'utf8').trim().split(/\r?\n/);
  assert.equal(text.shift(),'sequence_id,frame,time_s,teacher_angle_rad,new_angle_rad,old_angle_rad');
  const rows=text.map(line=>line.split(',').map(Number));
  assert.equal(rows.length,96);
  for (const [id, mean, negative, clippedOld, clippedNew, signMismatch, rmse] of [
    [48,-0.226104,48,35,0,11,0.247379], [62,-0.291867,46,43,1,13,0.324049],
  ]) {
    const group=rows.filter(r=>r[0]===id);
    assert.equal(group.length,48);
    assert.deepEqual(group.map(r=>r[1]),Array.from({length:48},(_,i)=>i+2));
    assert.ok(group.every(r=>Math.abs(r[2]-r[1]/25)<1e-8 && Math.abs(r[3])<0.65));
    const errors=group.map(r=>r[4]-r[3]);
    assert.ok(Math.abs(errors.reduce((a,b)=>a+b,0)/48-mean)<1e-6);
    assert.equal(errors.filter(x=>x<0).length,negative);
    assert.equal(group.filter(r=>r[5]===-0.65).length,clippedOld);
    assert.equal(group.filter(r=>Math.abs(r[4])===0.65).length,clippedNew);
    assert.equal(group.filter(r=>r[3]*r[4]<0).length,signMismatch);
    assert.ok(Math.abs(Math.sqrt(errors.reduce((a,b)=>a+b*b,0)/48)-rmse)<1e-6);
  }
  const entry=memory.RESEARCH_MEMORY.find(item=>item.id==='session-observation-long-imitation-frames-48-62');
  assert.ok(entry);
  assert.match(entry.source,/aafc0f5bd54df465a54b30748635022774af1156c697d04cf4982ba537b5ce57/);
  assert.match(entry.limitations,/не слепая/);
});

test('шесть осей: итог пользователя, контроль по осям и честные ограничения', () => {
  const item = memory.RESEARCH_MEMORY.find(entry => entry.id === 'session-wing-studio-user-pilot');
  assert.ok(item);
  assert.equal(item.ideaId, 'i-observational');
  assert.match(item.results, /0,136600 \/ 0,207899/);
  assert.match(item.results, /правое Z 0,099703 \/ 0,080389/);
  assert.match(item.source, /не обучающая/);
  assert.match(item.limitations, /не проверялись/);
  assert.match(item.limitations, /не автономное/);
  const model = [0.162953,0.105329,0.078315,0.227275,0.081124,0.099703];
  const zero  = [0.336185,0.201565,0.112967,0.275915,0.101637,0.080389];
  const rmse = a => Math.sqrt(a.reduce((sum,v)=>sum+v*v,0)/a.length);
  assert.ok(Math.abs(rmse(model)-0.136600)<0.0000005);
  assert.ok(Math.abs(rmse(zero)-0.207899)<0.0000005);
  assert.equal(model.filter((v,i)=>v<zero[i]).length,5);
  assert.ok(Math.abs((model[5]/zero[5]-1)*100-24)<.1);
  const old = { version: 'v630-session-2026-11-07-v23', entries: [{ id:'custom', ideaId:'x', results:'не изменять', files:[] }] };
  const migrated = memory.installResearchMemory(old);
  assert.equal(migrated.entries[0],old.entries[0]);
  assert.equal(migrated.entries.filter(entry=>entry.id==='session-wing-studio-user-pilot').length,1);
  assert.strictEqual(memory.installResearchMemory(migrated),migrated);
});

test('шесть осей: покадровая округлённая выписка согласуется с пользовательскими метриками', () => {
  const data=fs.readFileSync(path.join(root,'experiments/reports/wing-studio-user-frames-rounded.csv'),'utf8').trim().split(/\r?\n/);
  const header=data.shift().split(',');
  assert.equal(header.length,14);
  assert.equal(header[0],'frame');
  const rows=data.map(line=>line.split(','));
  assert.equal(rows.length,51);
  assert.deepEqual(rows.map(r=>Number(r[0])),Array.from({length:51},(_,i)=>i));
  assert.ok(rows.every((r,i)=>Math.abs(Number(r[1])-i/25)<1e-9));
  assert.ok(rows.slice(0,2).every(r=>r.slice(8).every(v=>v==='')));
  assert.ok(rows.slice(2).every(r=>r.length===14 && r.slice(8).every(v=>v!=='' && Number.isFinite(Number(v)))));
  const expected=[0.16295304331508692,0.10532898544228013,0.07831520324819559,0.227274583680489,0.08112446408683792,0.0997028970684356];
  const zeros=[0.33618502875491607,0.2015651106576034,0.1129666131389415,0.2759148254153233,0.10163698404716176,0.08038883822113908];
  let sum=0, rightX=0;
  for(let axis=0;axis<6;axis++) {
    let squared=0,zsquared=0,wins=0,opposite=0,strongOpposite=0,strong=0;
    for(const r of rows.slice(2)) {
      const target=Number(r[2+axis]),pred=Number(r[8+axis]);
      squared+=(pred-target)**2;zsquared+=target**2;
      if(Math.abs(pred-target)<Math.abs(target))wins++;
      if(Math.abs(target)>1e-6 && target*pred<0)opposite++;
      if(Math.abs(target)>=5) {strong++;if(target*pred<0)strongOpposite++;}
    }
    assert.ok(Math.abs(Math.sqrt(squared/49)*Math.PI/180-expected[axis])<2e-8);
    assert.ok(Math.abs(Math.sqrt(zsquared/49)*Math.PI/180-zeros[axis])<2e-8);
    sum+=squared;if(axis===3) {rightX=squared;assert.equal(wins,22);}
    if(axis===5) {assert.equal(wins,16);assert.equal(opposite,30);assert.equal(strong,13);assert.equal(strongOpposite,12);}
  }
  assert.ok(Math.abs(Math.sqrt(sum/(49*6))*Math.PI/180-0.13659962378188198)<2e-8);
  assert.ok(Math.abs(rightX/sum-0.4614)<0.0001);
  for(let frame=9;frame<=18;frame++) assert.deepEqual(rows[frame].slice(8),rows[frame+25].slice(8));
  const item=memory.RESEARCH_MEMORY.find(entry=>entry.id==='session-wing-studio-user-frames');
  assert.ok(item && item.ideaId==='i-observational');
  assert.match(item.source,/восстановлены/);
  assert.match(item.limitations,/зависимы/);
  assert.ok(item.files.includes('experiments/reports/wing-studio-user-frames-rounded.csv'));
  const old={version:'v630-session-2026-11-07-v24',entries:[{id:'custom',ideaId:'x',results:'сохранить',files:[]}]};
  const migrated=memory.installResearchMemory(old);
  assert.equal(migrated.entries[0],old.entries[0]);
  assert.equal(migrated.entries.filter(entry=>entry.id==='session-wing-studio-user-frames').length,1);
});

test('проба 51: пользовательские сводки, осевые RMSE и нижняя граница максимума', () => {
  const text=fs.readFileSync(path.join(root,'experiments/reports/user-wing-learning-user-test-summary.csv'),'utf8').trim().split(/\r?\n/);
  assert.equal(text.length,2);
  const labels=text[0].split(','); const values=text[1].split(',').map(Number);
  assert.equal(labels.length,11);assert.equal(values.length,11);
  assert.equal(values[0],1);assert.equal(values[1],49);
  const axes=values.slice(5); const pooled=Math.sqrt(axes.reduce((s,v)=>s+v*v,0)/6);
  assert.ok(Math.abs(pooled-values[2])<1e-14);
  assert.ok(Math.abs(values[2]-0.1087124191527928)<1e-14);
  assert.ok(Math.abs(values[3]-0.21308210046565054)<1e-14);
  assert.ok(Math.abs(values[4]-0.20489531671412559)<1e-14);
  const leftMae=0.05144688330350086,rightMae=0.040357272813083635;
  const leftBound=axes[0]**2/leftMae, rightBound=axes[5]**2/rightMae;
  assert.ok(Math.abs(leftBound*180/Math.PI-28.5578345)<1e-5);
  assert.ok(Math.abs(rightBound*180/Math.PI-24.1602543)<1e-5);
  assert.ok(Math.abs((1-axes[5]/0.13131518707876455)*100-0.65743185)<1e-6);
  const item=memory.RESEARCH_MEMORY.find(entry=>entry.id==='session-user-wing-learning-pilot');
  assert.ok(item && item.ideaId==='i-observational');
  assert.match(item.source,/независимо не предоставлены/);
  assert.match(item.results,/не менее/);
  assert.match(item.limitations,/одним углом|левое Z/);
  const old={version:'v630-session-2026-11-07-v25',entries:[{id:'custom',ideaId:'x',results:'сохранить',files:[]}]};
  const migrated=memory.installResearchMemory(old);
  assert.equal(migrated.entries[0],old.entries[0]);
  assert.equal(migrated.entries.filter(entry=>entry.id==='session-user-wing-learning-pilot').length,1);
});

test('проба 51: транскрипция 49 кадров сверяется с метриками и начальной ошибкой', () => {
  const file=fs.readFileSync(path.join(root,'experiments/reports/user-wing-learning-user-predictions-transcribed.csv'),'utf8');
  assert.equal(require('node:crypto').createHash('sha256').update(file).digest('hex'),'3af3c26e4a07b9926bbad37fba684062e2ce067d34bae5a0bee57dba007fde55');
  const lines=file.trim().split(/\r?\n/); assert.equal(lines.length,50);
  const rows=lines.slice(1).map(line=>line.split(',').map(Number));
  const axes=['left_x','left_y','left_z','right_x','right_y','right_z'];
  const rmseModel=[0.16013300558542773,0.04704157405450404,0.07340626895522592,0.10382024317533987,0.09934805129867715,0.1304518792091887];
  const maeModel=[0.05144688330350086,0.019740173467985823,0.026974199902111924,0.04272263209506131,0.036555796789760696,0.040357272813083635];
  const zeroRmse=[0.31695816271467503,0.2015651106576034,0.12616867871813853,0.2696049682537521,0.15307224519763885,0.13891159721496849];
  const mean=xs=>xs.reduce((s,x)=>s+x,0)/xs.length;
  const rmse=xs=>Math.sqrt(mean(xs.map(x=>x*x)));
  const errors=rows.map((r,i)=>{
    assert.equal(r.length,13); assert.ok(r.every(Number.isFinite));
    assert.ok(Math.abs(r[0]-(0.08+i*0.04))<1e-12);
    return axes.map((_,j)=>r[j+7]-r[j+1]);
  });
  axes.forEach((_,j)=>{
    assert.ok(Math.abs(rmse(errors.map(e=>e[j]))-rmseModel[j])<1e-14);
    assert.ok(Math.abs(mean(errors.map(e=>Math.abs(e[j])))-maeModel[j])<1e-14);
    assert.ok(Math.abs(rmse(rows.map(r=>r[j+1]))-zeroRmse[j])<1e-14);
  });
  const flat=errors.flat(); const ss=es=>es.flat().reduce((s,x)=>s+x*x,0);
  assert.ok(Math.abs(rmse(flat)-0.1087124191527928)<1e-14);
  assert.ok(Math.abs(mean(flat.map(Math.abs))-0.03629949306191737)<1e-14);
  assert.ok(Math.abs(ss(errors.slice(0,4))/ss(errors)-0.9595968755615126)<1e-12);
  assert.ok(Math.abs(ss(errors.slice(0,1))/ss(errors)-0.6857505275866363)<1e-12);
  assert.ok(Math.abs(rmse(errors.slice(4).flat())-0.022802287587150732)<1e-14);
  assert.ok(Math.abs(rmse(rows.slice(4).flatMap(r=>r.slice(1,7)))-0.1920110902821396)<1e-14);
  assert.ok(Math.abs(rmse(rows.slice(0,4).flatMap(r=>r.slice(1,7)))-0.37607294830714283)<1e-14);
  const maxLeft=errors.reduce((best,e,i)=>Math.abs(e[0])>Math.abs(errors[best][0])?i:best,0);
  assert.equal(rows[maxLeft][0],0.08);
  assert.ok(Math.abs(errors[maxLeft][0]*180/Math.PI-58.6073717683)<1e-8);
  const old={version:'v630-session-2026-11-07-v26',entries:[{id:'custom',results:'сохранить',files:[]}]};
  const migrated=memory.installResearchMemory(old);
  assert.equal(migrated.entries[0],old.entries[0]);
  assert.equal(migrated.entries.filter(e=>e.id==='session-user-wing-learning-frames').length,1);
  assert.match(migrated.entries.find(e=>e.id==='session-user-wing-learning-frames').limitations,/после просмотра/);
});
