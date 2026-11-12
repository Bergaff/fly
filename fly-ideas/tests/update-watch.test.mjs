import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createServer } from 'vite';

test('Vite не отслеживает файлы временного снимка обновления в workspace', async () => {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'fly-vite-watch-'));
  await fs.mkdir(path.join(root, 'workspace/.app-updates/stage/src'), { recursive: true });
  await fs.mkdir(path.join(root, 'src'));
  await fs.writeFile(path.join(root, 'index.html'), '<html></html>');
  await fs.writeFile(path.join(root, 'src/live.html'), 'initial');
  const server = await createServer({ configFile: fileURLToPath(new URL('../vite.config.ts', import.meta.url)), root, logLevel: 'silent', server: { middlewareMode: true }, optimizeDeps: { noDiscovery: true, include: [] }, appType: 'custom' });
  try {
    const seen=[];
    server.watcher.on('all', (_event, file) => seen.push(file));
    const staged = path.join(root, 'workspace/.app-updates/stage/src/staged.html');
    const live = path.join(root, 'src/live.html');
    await fs.writeFile(staged, 'staged');
    const gotLive = new Promise((resolve, reject) => {
      const timer=setTimeout(() => reject(new Error('watcher не увидел обычный файл')), 5000);
      server.watcher.on('change', function callback(file) { if (file === live) { clearTimeout(timer); server.watcher.off('change', callback); resolve(); } });
    });
    await fs.writeFile(live, 'live');
    await gotLive;
    await new Promise(resolve => setTimeout(resolve, 300));
    assert.ok(seen.includes(live));
    assert.ok(!seen.some(file => file.includes(`${path.sep}workspace${path.sep}`)), `лишние события: ${seen}`);
  } finally { await server.close(); await fs.rm(root, { recursive: true, force: true }); }
});
