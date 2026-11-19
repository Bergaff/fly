const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const script = path.join(__dirname, "../experiments/templates/20_brian2_smoke_test.py");
const candidates = [process.env.FLY_TEST_PYTHON, "python3", "python"].filter(Boolean);
const python = candidates.find((exe) => spawnSync(exe, ["-c", "import sys"], { encoding: "utf8" }).status === 0);

function runWithReport(args = []) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "fly-brian-smoke-"));
  try {
    const result = spawnSync(python, [...args, script], {
      encoding: "utf8", env: { ...process.env, FLY_RUN_DIR: dir }, timeout: 60000,
    });
    const report = JSON.parse(fs.readFileSync(path.join(dir, "summary.json"), "utf8"));
    return { result, report };
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

test("проверка Brian2 сохраняет причину отсутствующего пакета", { skip: !python && "Python не найден" }, () => {
  const { result, report } = runWithReport(["-S"]);
  assert.equal(result.status, 1);
  assert.equal(report.brian2.import_ok, false);
  assert.equal(report.brian2.lif_ok, false);
  assert.match(report.brian2.error, /brian2/i);
  assert.match(report.scope, /не baseline/);
});

const hasBrian = python && spawnSync(python, ["-c", "import brian2"], { encoding: "utf8", timeout: 30000 }).status === 0;
test("Brian2 выполняет тестовую LIF-модель и создаёт спайки", { skip: !hasBrian && "Brian2 не установлен в тестовом Python" }, () => {
  const { result, report } = runWithReport();
  assert.equal(result.status, 0, result.stderr);
  assert.equal(report.brian2.import_ok, true);
  assert.equal(report.brian2.lif_ok, true);
  assert.ok(report.brian2.n_spikes > 0);
  assert.equal(report.brian2.backend, "numpy");
});
