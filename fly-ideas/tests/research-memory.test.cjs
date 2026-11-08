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
