// Called by START.bat before the app starts. Only an explicitly staged update is applied.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const statusStore = require('./app-update-status.cjs');
const app = path.resolve(__dirname, '..');
const base = path.join(app, 'workspace', '.app-updates');
const pending = path.join(base, 'pending.json');
const journal = path.join(base, 'journal.json');
function record(state, message) {
  try { statusStore.writeStatus(app, { state, phase: 'apply', message: message.slice(-16000), done: 0, total: null, unit: null, updatedAt: new Date().toISOString(), logPath: path.join(base, 'update-status.json') }); }
  catch (error) { console.error('Не удалось сохранить журнал обновления:', error.message); }
}
if (fs.existsSync(pending) || fs.existsSync(journal)) {
  try {
    const m = JSON.parse(fs.readFileSync(pending, 'utf8'));
    if (typeof m.python !== 'string' || !path.isAbsolute(m.python) || !fs.existsSync(m.python)) throw new Error('Python, подготовивший обновление, недоступен.');
    const run = spawnSync(m.python, [path.join(__dirname, 'app-update.py'), '--apply', '--app', app], { encoding: 'utf8', windowsHide: true, maxBuffer: 1024 * 1024, env: { ...process.env, PYTHONIOENCODING: 'utf-8' } });
    if (run.stdout) process.stdout.write(run.stdout);
    if (run.stderr) process.stderr.write(run.stderr);
    if (run.error || run.status !== 0) throw new Error([run.error?.message, run.stderr?.trim(), run.stdout?.trim()].filter(Boolean).join('\n') || `Обновление не применено (код ${run.status}).`);
    record('completed', run.stdout?.trim() || 'Обновление применено.');
  } catch (error) {
    record('error', `Не удалось применить обновление: ${error.message}`);
    console.error('Запуск остановлен:', error.message);
    console.error('Сохранён журнал:', path.join(base, 'update-status.json'));
    process.exitCode = 1;
  }
}
