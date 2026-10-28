const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs/promises");
const path = require("node:path");
const os = require("node:os");
const vm = require("node:vm");
const ts = require("typescript");
const { writeAssistantFile } = require("../electron/assistant-files.cjs");

test("помощник создаёт и изменяет только разрешённые файлы с резервной копией", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "fly-assistant-"));
  const base = { codeDir: dir, expectedDir: dir, name: "experiment.py", content: "print('new')\n", permissions: { createFiles: true, overwriteFiles: false } };
  try {
    await assert.rejects(writeAssistantFile({ ...base, permissions: { createFiles: false, overwriteFiles: false } }), /выключено/);
    const created = await writeAssistantFile(base);
    assert.equal(created.created, true);
    await assert.rejects(writeAssistantFile(base), /выключено/);
    const updating = { ...base, content: "print('updated')\n", permissions: { createFiles: true, overwriteFiles: true } };
    await assert.rejects(writeAssistantFile(updating), /откройте этот файл/);
    await assert.rejects(writeAssistantFile({ ...updating, expectedContent: "outdated" }), /изменился/);
    const updated = await writeAssistantFile({ ...updating, expectedContent: base.content });
    assert.equal(updated.created, false);
    assert.equal(await fs.readFile(updated.backup, "utf8"), base.content);
    assert.equal(await fs.readFile(updated.path, "utf8"), updating.content);
    const simultaneous = await Promise.allSettled([
      writeAssistantFile({ ...updating, content: "first", expectedContent: updating.content }),
      writeAssistantFile({ ...updating, content: "second", expectedContent: updating.content }),
    ]);
    assert.equal(simultaneous.filter((r) => r.status === "fulfilled").length, 1);
    assert.equal(simultaneous.filter((r) => r.status === "rejected").length, 1);
    await assert.rejects(writeAssistantFile({ ...base, expectedDir: path.join(dir, "other") }), /Папка кода изменилась/);
    await assert.rejects(writeAssistantFile({ ...base, name: "../outside.py" }), /безопасное имя/);
    await assert.rejects(writeAssistantFile({ ...base, name: "out.txt" }), /безопасное имя/);
    await assert.rejects(writeAssistantFile({ ...base, content: "  " }), /Пустой код/);
    if (process.platform !== "win32") {
      await fs.symlink(path.join(dir, "experiment.py"), path.join(dir, "link.py"));
      await assert.rejects(writeAssistantFile({ ...updating, name: "link.py", expectedContent: "first" }), /обычные файлы/);
    }
  } finally { await fs.rm(dir, { recursive: true, force: true }); }
});

test("сохранение принимает только завершённые блоки Python с именем", async () => {
  const source = await fs.readFile(path.join(__dirname, "../src/lib/assistant-code.ts"), "utf8");
  const code = ts.transpile(source, { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 });
  const context = { exports: {} };
  vm.runInNewContext(code, context);
  const extract = context.exports.extractAssistantFiles;
  const text = "Описание\r\n```python\r\n# file: alpha.py\r\nprint(1)\r\n```\n```py\n# file: beta.py\nprint(2)\n```\n```python\n# file: ../bad.py\nprint(3)\n```";
  assert.deepEqual(JSON.parse(JSON.stringify(extract(text))), [
    { name: "alpha.py", content: "# file: alpha.py\nprint(1)\n" },
    { name: "beta.py", content: "# file: beta.py\nprint(2)\n" },
  ]);
  assert.equal(extract("```python\n# file: missing.py\nprint(1)").length, 0);
  assert.equal(extract("```python\nprint(1)\n```").length, 0);
  assert.equal(extract("```javascript\n# file: fake.py\ntext\n```").length, 0);
  assert.equal(extract("```python\n# file: alpha.py\nprint(1)\n```\n```python\n# file: alpha.py\nprint(2)\n```").length, 0);
  const format = context.exports.formatAssistantResponse;
  assert.equal(format("Объяснение\n```python\n# file: alpha.py\nprint(1)\n```\nДетали", "code"), "```python\n# file: alpha.py\nprint(1)\n```");
  assert.equal(format("Что именно нужно?", "code"), "Что именно нужно?");
  assert.equal(format(text, "explain"), text);
});

test("Electron IPC сохраняет файлы раздельно по идеям и проверяет права", async () => {
  const dir = await fs.mkdtemp(path.join(os.tmpdir(), "fly-assistant-ipc-"));
  try {
    const mainPath = path.join(__dirname, "../electron/main.cjs");
    const realRequire = require("node:module").createRequire(mainPath);
    const handlers = new Map();
    const electron = {
      app: {
        getPath: (name) => path.join(dir, name),
        whenReady: () => new Promise(() => {}),
        on: () => {},
      },
      ipcMain: { handle: (name, fn) => handlers.set(name, fn) },
      BrowserWindow: {}, shell: {}, dialog: {},
    };
    const fakeProcess = { ...process, env: { ...process.env, VITE_DEV_SERVER_URL: "http://localhost:5173" }, platform: process.platform, execPath: process.execPath };
    const source = await fs.readFile(mainPath, "utf8");
    vm.runInNewContext(`${source}\nregisterIpc(() => null);`, {
      require: (name) => name === "electron" ? electron : realRequire(name),
      __dirname: path.join(dir, "app", "electron"),
      process: fakeProcess, console, setTimeout, clearTimeout, Buffer, URL,
      fetch: async () => ({ ok: true, json: async () => ({ choices: [{ message: { content: "код" }, finish_reason: "length" }], usage: { total_tokens: 42 } }) }),
      module: { exports: {} },
    });
    const call = (name, ...args) => handlers.get(`fly:${name}`)(null, ...args);
    await call("setSecret", "deepseek", "test-only-key");
    const response = await call("llmChat", { provider: "deepseek", messages: [{ role: "user", content: "test" }] });
    assert.equal(response.finishReason, "length");
    assert.equal(response.usage.total_tokens, 42);
    const a = await call("projectPaths", "idea:a");
    const b = await call("projectPaths", "idea:b");
    assert.notEqual(a.code, b.code);
    await call("setPermissions", { createFiles: true, overwriteFiles: false });
    await call("writeAssistantScript", "idea:a", "test.py", "# initial\n", { expectedDir: a.code });
    await assert.rejects(call("writeAssistantScript", "idea:a", "test.py", "# edited\n", { expectedDir: a.code, expectedContent: "# initial\n" }), /выключено/);
    await call("setPermissions", { overwriteFiles: true });
    const changed = await call("writeAssistantScript", "idea:a", "test.py", "# edited\n", { expectedDir: a.code, expectedContent: "# initial\n" });
    assert.equal(await fs.readFile(changed.backup, "utf8"), "# initial\n");
    assert.equal(await call("readScript", "idea:a", "test.py"), "# edited\n");
    assert.equal((await call("listScripts", "idea:b")).some((f) => f.name === "test.py"), false);
  } finally { await fs.rm(dir, { recursive: true, force: true }); }
});
