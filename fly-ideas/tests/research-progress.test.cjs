const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const vm = require('node:vm');
const root = path.join(__dirname, '..');

function load(file, aliases = {}) {
  const code = ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2022 } }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(code, { module, exports: module.exports, require: (name) => aliases[name] || require(name), console, Date });
  return module.exports;
}
const types = load('src/data/types.ts');
const suggestions = load('src/lib/idea-suggestions.ts', { '@/data/types': types });
const component = load('src/components/research-progress.tsx', { '@/data/types': types });
const plain = (x) => JSON.parse(JSON.stringify(x));
const idea = (name) => ({ id: name, title: name, question: `${name} question`, method: `${name} method`, validation: `${name} validation`, checklist: [{ id: 'old', done: true, text: 'старый этап' }], experiments: [] });

test('четыре самостоятельных этапа не выдумываются из старых отметок', () => {
  const a = idea('A'), b = idea('B');
  assert.deepEqual(plain(types.RESEARCH_STAGES.map(x => x.id)), ['observation', 'reproduction', 'interpretation', 'verification']);
  assert.deepEqual(plain(types.researchProgress(a)), { done: 0, total: 4, pct: 0 });
  a.researchProgress = { observation: { done: true, evidence: 'файл и условия' }, reproduction: { done: false, evidence: 'нужна проверка' } };
  assert.equal(types.researchProgress(a).pct, 25);
  assert.equal(types.researchProgress(b).pct, 0);
  assert.deepEqual(plain(JSON.parse(JSON.stringify(a)).researchProgress), plain(a.researchProgress));
});

test('отметка и основание изменяют только выбранный этап и сохраняют остальные', () => {
  const a = idea('A'); a.researchProgress = { verification: { done: true, evidence: 'контроль' } };
  let patch;
  const tree = component.ResearchProgress({ idea: a, onUpdateIdea: (id, value) => { assert.equal(id, 'A'); patch = value; } });
  function find(node, type) {
    if (!node || typeof node !== 'object') return [];
    const children = node.props?.children;
    return [...(node.type === type ? [node] : []), ...[children].flat(Infinity).flatMap((child) => find(child, type))];
  }
  const buttons = find(tree, 'button'), textareas = find(tree, 'textarea');
  assert.equal(buttons.length, 4); assert.equal(textareas.length, 4);
  buttons[0].props.onClick();
  assert.equal(patch.researchProgress.observation.done, true);
  assert.equal(patch.researchProgress.verification.evidence, 'контроль');
  textareas[1].props.onChange({ target: { value: 'повтор с seed 7' } });
  assert.equal(patch.researchProgress.reproduction.evidence, 'повтор с seed 7');
  assert.equal(patch.researchProgress.reproduction.done, false);
  assert.equal(a.checklist[0].done, true);
});

test('контекст предложений ограничен выбранной идеей и последними двумя записями', () => {
  const a = idea('A'), b = idea('B');
  a.researchProgress = { observation: { done: true, evidence: 'данные A' } };
  a.experiments = [1,2,3].map(n => ({ date: `2026-10-0${n}`, createdAt: `2026-10-0${n}T00:00:00Z`, title: 'run' + n, params: '', result: 'результат ' + n, conclusion: '', outcome: 'partial' }));
  const context = suggestions.suggestionContext(a);
  assert.equal(context.title, 'A'); assert.equal(context.progress[0].evidence, 'данные A');
  assert.deepEqual(plain(context.recentExperiments.map(e => e.title)), ['run3', 'run2']);
  assert.ok(!JSON.stringify(context).includes(b.question));
  assert.ok(!('chat' in context)); assert.ok(!('file' in context));
});

test('предложения принимаются только из корректного списка и никогда не превращаются в код', () => {
  assert.deepEqual(plain(suggestions.parseSuggestions('```json\n{"suggestions":["Вопрос A", "Вопрос B"]}\n```')), ['Вопрос A', 'Вопрос B']);
  assert.throws(() => suggestions.parseSuggestions('print("hello")'), /формате/);
  assert.throws(() => suggestions.parseSuggestions('{"suggestions":["a", "b", "c", "d"]}'), /Некорректный/);
  assert.throws(() => suggestions.parseSuggestions('{"suggestions":[42]}'), /Некорректный/);
});

test('выключенные предложения не разрешают запрос даже при наличии идеи и ключа', () => {
  assert.equal(suggestions.canRequestSuggestions(false, false, true, true), false);
  assert.equal(suggestions.canRequestSuggestions(true, true, true, true), false);
  assert.equal(suggestions.canRequestSuggestions(true, false, false, true), false);
  assert.equal(suggestions.canRequestSuggestions(true, false, true, false), false);
  assert.equal(suggestions.canRequestSuggestions(true, false, true, true), true);
});

test('научный прогресс расположен на отдельной вкладке карточки, а не в чате', () => {
  const brain = fs.readFileSync(path.join(root, 'src/views/brain-view.tsx'), 'utf8');
  const dialog = fs.readFileSync(path.join(root, 'src/components/idea-dialog.tsx'), 'utf8');
  assert.doesNotMatch(brain, /<ResearchProgress\b/);
  assert.match(dialog, /<TabsTrigger value="research">\s*Прогресс/);
  assert.match(dialog, /<TabsContent value="research"[\s\S]*?<ResearchProgress[\s\S]*?<\/TabsContent>/);
  assert.match(dialog, /onSave\(id, rest\)/);
});
