const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const vm = require('node:vm');
const ts = require('typescript');

const root = path.join(__dirname, '..');
const main = fs.readFileSync(path.join(root, 'electron/main.cjs'), 'utf8');
const brain = fs.readFileSync(path.join(root, 'src/views/brain-view.tsx'), 'utf8');
const usage = fs.readFileSync(path.join(root, 'src/lib/api-usage.ts'), 'utf8');
function tsFunction(source, name, end) {
  const start = source.indexOf(`function ${name}(`);
  const finish = source.indexOf(end, start);
  assert.ok(start >= 0 && finish > start);
  const javascript = ts.transpile(source.slice(start, finish + 2), { target: ts.ScriptTarget.ES2022 });
  return vm.runInNewContext(`${javascript}\n${name};`);
}

test('журнал API сохраняет одновременные вызовы и разделяет идеи', async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-api-test-'));
  const file = path.join(dir, 'api-calls.json');
  try {
    const code = main.slice(main.indexOf('function readApiCallStore()'), main.indexOf('async function llmChat('));
    const api = vm.runInNewContext(`let apiCallWriteQueue = Promise.resolve();\n${code}\n({ listApiCalls, appendApiCall });`, {
      fs, fsp, path, crypto, process, API_CALLS_FILE: file,
    });
    const record = (id) => ({ id, at: `2026-10-28T00:00:0${id}.000Z`, provider: 'deepseek', model: 'deepseek-chat', question: `вопрос ${id}`, answer: `ответ ${id}`, usage: { inputTokens: 10, outputTokens: 5, totalTokens: 15 }, status: 'ok' });
    await Promise.all([
      api.appendApiCall('idea:a', record(1)),
      api.appendApiCall('idea:b', record(2)),
      api.appendApiCall('idea:a', record(3)),
    ]);
    assert.equal((await api.listApiCalls('idea:a')).length, 2);
    assert.equal((await api.listApiCalls('idea:b'))[0].answer, 'ответ 2');
    assert.equal((await api.listApiCalls('__all__')).length, 3);
    assert.equal((await api.listApiCalls('idea:a'))[0].workspaceId, 'idea:a');
    await fsp.writeFile(file, '{broken');
    await assert.rejects(api.appendApiCall('idea:a', record(4)), /Не удалось прочитать журнал API/);
    assert.equal(await fsp.readFile(file, 'utf8'), '{broken');
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('новый тест Brian2 добавляется в идею и не заменяет пользовательские файлы', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-template-'));
  let config = {};
  try {
    const start = main.indexOf('const IDEA_TEMPLATE_MAP =');
    const end = main.indexOf('function ensureDirs()', start);
    const code = main.slice(start, end);
    const templates = vm.runInNewContext(`${code}\n({ syncProjectTemplates });`, {
      fs, path, TEMPLATES: path.join(root, 'experiments', 'templates'),
      DIRS: { scripts: path.join(dir, 'scripts'), runs: path.join(dir, 'runs') },
      readConfig: () => config, writeConfig: (value) => { config = value; },
    });
    const ideaDir = path.join(dir, 'idea');
    fs.mkdirSync(ideaDir);
    fs.writeFileSync(path.join(ideaDir, 'env_smoke_test.py'), '# пользовательский файл\n');
    templates.syncProjectTemplates('idea:i-individuality', ideaDir);
    const smoke = path.join(ideaDir, '20_brian2_smoke_test.py');
    assert.ok(fs.existsSync(smoke));
    assert.ok(fs.existsSync(path.join(ideaDir, '21_check_linked_data.py')));
    assert.ok(fs.existsSync(path.join(ideaDir, '22_shiu_reference_check.py')));
    const sample = path.join(ideaDir, 'small_sample_lif_fixed.py');
    assert.ok(fs.existsSync(sample));
    fs.writeFileSync(sample, '# изменения пользователя\n');
    templates.syncProjectTemplates('idea:i-individuality', ideaDir);
    assert.equal(fs.readFileSync(sample, 'utf8'), '# изменения пользователя\n');
    assert.equal(fs.readFileSync(path.join(ideaDir, 'env_smoke_test.py'), 'utf8'), '# пользовательский файл\n');
    fs.writeFileSync(smoke, '# изменён пользователем\n');
    templates.syncProjectTemplates('idea:i-individuality', ideaDir);
    assert.equal(fs.readFileSync(smoke, 'utf8'), '# изменён пользователем\n');
    const otherDir = path.join(dir, 'other');
    fs.mkdirSync(otherDir);
    templates.syncProjectTemplates('idea:i-lesions', otherDir);
    assert.equal(fs.existsSync(path.join(otherDir, '20_brian2_smoke_test.py')), false);
    assert.ok(fs.existsSync(path.join(otherDir, '21_check_linked_data.py')));
    assert.ok(fs.existsSync(path.join(otherDir, '22_shiu_reference_check.py')));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test('учёт токенов учитывает разные форматы и отсутствие данных', () => {
  const normalize = tsFunction(usage, 'normalizeUsage', '\n}\n');
  assert.deepEqual(JSON.parse(JSON.stringify(normalize({ prompt_tokens: 12, completion_tokens: 8 }))), { inputTokens: 12, outputTokens: 8, totalTokens: 20 });
  assert.deepEqual(JSON.parse(JSON.stringify(normalize({ input_tokens: 3, output_tokens: 9, total_tokens: 12 }))), { inputTokens: 3, outputTokens: 9, totalTokens: 12 });
  assert.equal(normalize({}), null);
});

test('предпросмотр таблиц читает кавычки, переносы и табуляцию', () => {
  const parse = tsFunction(brain, 'parseDelimited', '\n}\n\nfunction DelimitedTable');
  const rows = parse('a,b\n"один, два","строка\nдве"\n', ',');
  assert.deepEqual(JSON.parse(JSON.stringify(rows)), [['a', 'b'], ['один, два', 'строка\nдве']]);
  assert.deepEqual(JSON.parse(JSON.stringify(parse('a\tb\n1\t2', '\t'))), [['a', 'b'], ['1', '2']]);
});
