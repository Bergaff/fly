const fs = require("node:fs");
const fsp = require("node:fs/promises");
const path = require("node:path");
const crypto = require("node:crypto");

// Сериализуем операции на одном файле внутри приложения: второй запрос проверит
// снимок уже после первого и не затрёт его результат.
const pendingWrites = new Map();

/** Только файлы Python в выбранной папке кода. Замена требует снимка исходного файла. */
async function writeAssistantFile(options) {
  const key = `${path.resolve(options.codeDir)}\0${String(options.name).toLowerCase()}`;
  const previous = pendingWrites.get(key) || Promise.resolve();
  const operation = previous.catch(() => {}).then(() => writeAssistantFileOnce(options));
  pendingWrites.set(key, operation);
  try { return await operation; }
  finally { if (pendingWrites.get(key) === operation) pendingWrites.delete(key); }
}

async function writeAssistantFileOnce({ codeDir, expectedDir, name, content, permissions, expectedContent }) {
  permissions = typeof permissions === "function" ? permissions() : permissions;
  if (typeof expectedDir !== "string" || path.resolve(expectedDir) !== path.resolve(codeDir)) {
    throw new Error("Папка кода изменилась после отправки запроса. Проверьте путь и повторите запрос.");
  }
  if (typeof name !== "string" || !/^[A-Za-z0-9_][A-Za-z0-9_.-]*\.py$/.test(name) || name.includes("..")) {
    throw new Error("Нужно безопасное имя файла Python без папок, например analysis.py.");
  }
  if (typeof content !== "string" || !content.trim()) throw new Error("Пустой код не сохранён.");
  const file = path.join(codeDir, name);
  let info;
  try { info = await fsp.lstat(file); } catch (err) { if (err.code !== "ENOENT") throw err; }
  if (!info) {
    if (!permissions.createFiles) throw new Error("Создание файлов помощником выключено в правах.");
    try { await fsp.writeFile(file, content, { encoding: "utf8", flag: "wx" }); }
    catch (err) { if (err.code === "EEXIST") throw new Error("Файл появился после проверки. Отправьте запрос ещё раз."); throw err; }
    return { file: name, path: file, created: true };
  }
  if (!info.isFile() || info.isSymbolicLink()) throw new Error("Можно изменять только обычные файлы в папке идеи, не ссылки.");
  if (!permissions.overwriteFiles) throw new Error("Изменение существующих файлов помощником выключено в правах.");
  if (typeof expectedContent !== "string") throw new Error("Для изменения откройте этот файл и включите передачу его содержимого.");
  const before = await fsp.readFile(file, "utf8");
  if (before !== expectedContent) throw new Error("Файл изменился после отправки запроса. Новая версия не записана.");
  const backup = `${file}.bak-${Date.now()}-${crypto.randomBytes(3).toString("hex")}`;
  await fsp.copyFile(file, backup, fs.constants.COPYFILE_EXCL);
  if (await fsp.readFile(file, "utf8") !== expectedContent) {
    throw new Error("Файл изменился во время сохранения. Новая версия не записана.");
  }
  await fsp.writeFile(file, content, "utf8");
  return { file: name, path: file, created: false, backup };
}

module.exports = { writeAssistantFile };
