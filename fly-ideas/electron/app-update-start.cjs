// Called by START.bat before the app starts. Only an explicitly staged update is applied.
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const app = path.resolve(__dirname, '..');
const base = path.join(app, 'workspace', '.app-updates');
const pending = path.join(base, 'pending.json');
const journal = path.join(base, 'journal.json');
if (fs.existsSync(pending) || fs.existsSync(journal)) {
  try {
    const m = JSON.parse(fs.readFileSync(pending, 'utf8'));
    if (typeof m.python !== 'string' || !path.isAbsolute(m.python) || !fs.existsSync(m.python)) throw new Error('Python, подготовивший обновление, недоступен.');
    const run = spawnSync(m.python, [path.join(__dirname, 'app-update.py'), '--apply', '--app', app], { stdio: 'inherit', windowsHide: true });
    if (run.error || run.status !== 0) throw run.error || new Error('Обновление не применено.');
  } catch (error) {
    console.error('Запуск остановлен:', error.message);
    process.exitCode = 1;
  }
}
