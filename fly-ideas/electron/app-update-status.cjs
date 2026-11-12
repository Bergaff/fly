// Small local status record; never traverses links or writes into user projects.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
function folder(app) {
  let dir = app;
  for (const part of ['workspace', '.app-updates']) {
    dir = path.join(dir, part);
    const st = fs.lstatSync(dir);
    if (!st.isDirectory() || st.isSymbolicLink()) throw new Error(`Небезопасная папка журнала: ${dir}`);
  }
  return dir;
}
function statusPath(app, create = false) {
  // mkdir separately, without accepting links, and tolerate existing directories.
  if (create) {
    let dir = app;
    for (const part of ['workspace', '.app-updates']) {
      dir = path.join(dir, part);
      try { fs.mkdirSync(dir); } catch (e) { if (e.code !== 'EEXIST') throw e; }
      const st = fs.lstatSync(dir);
      if (!st.isDirectory() || st.isSymbolicLink()) throw new Error(`Небезопасная папка журнала: ${dir}`);
    }
    return path.join(dir, 'update-status.json');
  }
  return path.join(folder(app), 'update-status.json');
}
function writeStatus(app, status) {
  const file = statusPath(app, true);
  const temp = path.join(path.dirname(file), `.update-status-${process.pid}-${crypto.randomBytes(8).toString('hex')}.tmp`);
  try {
    fs.writeFileSync(temp, JSON.stringify(status, null, 2), { encoding: 'utf8', flag: 'wx' });
    fs.renameSync(temp, file);
  } finally { try { fs.unlinkSync(temp); } catch { /* Best-effort cleanup; do not hide the original error. */ } }
  return file;
}
function readStatus(app) {
  try {
    const file = statusPath(app);
    const st = fs.lstatSync(file);
    if (!st.isFile() || st.isSymbolicLink() || st.size > 128 * 1024) return null;
    const value = JSON.parse(fs.readFileSync(file, 'utf8'));
    return value && typeof value === 'object' ? value : null;
  } catch { return null; }
}
module.exports = { statusPath, writeStatus, readStatus };
