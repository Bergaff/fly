const fs = require('node:fs/promises');
const path = require('node:path');
const { isUtf8 } = require('node:buffer');

const TEXT_EXTENSIONS = new Set(['.json', '.csv', '.tsv', '.txt', '.log', '.md', '.py', '.yml', '.yaml', '.xml', '.svg']);
const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg']);
const MAX_BYTES = 8 * 1024 * 1024;

/** Копирует содержимое выбранного результата, но не заглушку предпросмотра. */
async function copyRunFile({ dir, name, withinRuns, withinRealRuns = withinRuns, clipboard, nativeImage }) {
  if (typeof dir !== 'string' || typeof name !== 'string' || !name || name === '.' || name === '..' || /[\\/\x00]/.test(name) || path.basename(name) !== name) {
    throw new Error('Некорректное имя файла результата.');
  }
  const full = path.join(dir, name);
  if (!withinRuns(full)) throw new Error('Файл вне папки прогонов.');
  const ext = path.extname(name).toLowerCase();
  if (!TEXT_EXTENSIONS.has(ext) && !IMAGE_EXTENSIONS.has(ext)) throw new Error('Этот формат нельзя скопировать как текст или изображение. Откройте файл через папку прогона.');
  const stat = await fs.lstat(full);
  if (!stat.isFile() || stat.isSymbolicLink()) throw new Error('Нужен обычный файл результата, ссылки не поддерживаются.');
  const realFull = await fs.realpath(full);
  if (!withinRealRuns(realFull)) throw new Error('Файл по ссылке находится вне папки прогонов.');
  if (stat.size > MAX_BYTES) throw new Error('Файл больше 8 МиБ: откройте папку прогона и скопируйте файл оттуда.');
  const handle = await fs.open(full, 'r');
  let buffer;
  try {
    // Ограничиваем чтение и в случае, если файл увеличился после проверки размера.
    buffer = Buffer.alloc(MAX_BYTES + 1);
    let offset = 0;
    while (offset < buffer.length) {
      const { bytesRead } = await handle.read(buffer, offset, buffer.length - offset, null);
      if (!bytesRead) break;
      offset += bytesRead;
    }
    if (offset > MAX_BYTES) throw new Error('Файл больше 8 МиБ: откройте папку прогона и скопируйте файл оттуда.');
    buffer = buffer.subarray(0, offset);
  } finally { await handle.close(); }
  if (TEXT_EXTENSIONS.has(ext)) {
    if (!isUtf8(buffer)) throw new Error('Файл не является текстом UTF-8. Откройте его через папку прогона.');
    clipboard.writeText(buffer.toString('utf8'));
    return { kind: 'text', bytes: buffer.length };
  }
  const image = nativeImage.createFromBuffer(buffer);
  if (image.isEmpty()) throw new Error('Не удалось прочитать изображение. Откройте файл через папку прогона.');
  clipboard.writeImage(image);
  return { kind: 'image', bytes: buffer.length };
}

module.exports = { copyRunFile, MAX_BYTES };
