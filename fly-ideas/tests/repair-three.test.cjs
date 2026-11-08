const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const root = path.resolve(__dirname, '..');
const bat = path.join(root, 'experiments/REPAIR-THREE.bat');
const runEmbedded = (app, action, tmp) => spawnSync(process.execPath, ['-e', "const f=require('fs');const s=f.readFileSync(process.argv[1],'utf8');const k='// FLY_REPAIR_'+'SCRIPT';new Function('require','process',s.slice(s.lastIndexOf(k)+k.length))(require,process)", bat, action], { cwd: app, env: { ...process.env, FLY_REPAIR_TMP: tmp }, encoding: 'utf8' });
test('восстановление three проверяет контрольную сумму и не заменяет существующие файлы', () => {
  const home = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-repair-test-'));
  try {
    const pkg = path.join(home, 'package');
    fs.mkdirSync(path.join(pkg, 'build'), { recursive: true });
    fs.mkdirSync(path.join(pkg, 'examples/jsm/controls'), { recursive: true });
    fs.writeFileSync(path.join(pkg, 'package.json'), JSON.stringify({ name: 'three', version: '0.180.0' }));
    fs.writeFileSync(path.join(pkg, 'build/three.module.js'), '// fixture');
    fs.writeFileSync(path.join(pkg, 'examples/jsm/controls/OrbitControls.js'), '// fixture');
    const archive = path.join(home, 'three-0.180.0.tgz');
    const tar = spawnSync('tar', ['-czf', archive, '-C', home, 'package'], { encoding: 'utf8' });
    if (tar.error?.code === 'ENOENT') return;
    assert.equal(tar.status, 0, tar.stderr);
    // The fixture archive must be extracted by the script, not reused from creation.
    fs.rmSync(pkg, { recursive: true });
    const integrity = 'sha512-' + crypto.createHash('sha512').update(fs.readFileSync(archive)).digest('base64');
    const app = path.join(home, 'app'); fs.mkdirSync(path.join(app, 'node_modules'), { recursive: true });
    fs.writeFileSync(path.join(app, 'package.json'), JSON.stringify({ dependencies: { three: '^0.180.0' } }));
    const lock = { packages: { 'node_modules/three': { version: '0.180.0', integrity } } };
    fs.writeFileSync(path.join(app, 'package-lock.json'), JSON.stringify(lock));
    fs.writeFileSync(path.join(app, 'node_modules', 'important-user-file.txt'), 'keep');
    assert.equal(runEmbedded(app, 'check', home).status, 1);
    lock.packages['node_modules/three'].integrity = 'sha512-' + Buffer.alloc(64).toString('base64');
    fs.writeFileSync(path.join(app, 'package-lock.json'), JSON.stringify(lock));
    let bad = runEmbedded(app, 'install', home);
    assert.equal(bad.status, 2); assert.match(bad.stderr, /Контрольная сумма/);
    assert.equal(fs.existsSync(path.join(app, 'node_modules/three')), false);
    lock.packages['node_modules/three'].integrity = integrity;
    fs.writeFileSync(path.join(app, 'package-lock.json'), JSON.stringify(lock));
    const good = runEmbedded(app, 'install', home);
    assert.equal(good.status, 0, good.stderr);
    assert.equal(runEmbedded(app, 'check', home).status, 0);
    assert.equal(fs.readFileSync(path.join(app, 'node_modules', 'important-user-file.txt'), 'utf8'), 'keep');
    const rerun = runEmbedded(app, 'install', home); assert.equal(rerun.status, 2);
    fs.unlinkSync(path.join(app, 'node_modules/three/build/three.module.js'));
    const incomplete = runEmbedded(app, 'check', home);
    assert.equal(incomplete.status, 2); assert.match(incomplete.stderr, /неполной/);
    assert.equal(fs.existsSync(path.join(app, 'node_modules/three/package.json')), true);
  } finally { fs.rmSync(home, { recursive: true, force: true }); }
});

test('проверка перед запуском не создаёт бесконечную ошибку Vite', () => {
  const app = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-preflight-test-'));
  try {
    fs.mkdirSync(path.join(app, 'electron'));
    for (const file of ['app-update-start.cjs', 'app-update-status.cjs']) fs.copyFileSync(path.join(root, 'electron', file), path.join(app, 'electron', file));
    fs.writeFileSync(path.join(app, 'package.json'), JSON.stringify({ dependencies: { three: '^0.180.0' } }));
    const run = () => spawnSync(process.execPath, [path.join(app, 'electron/app-update-start.cjs')], { encoding: 'utf8' });
    assert.equal(run().status, 0); // First installation is still handled by START.bat.
    fs.mkdirSync(path.join(app, 'node_modules'));
    const missing = run(); assert.equal(missing.status, 1); assert.match(missing.stderr, /REPAIR-THREE/);
    fs.mkdirSync(path.join(app, 'workspace/.app-updates'), { recursive: true });
    fs.writeFileSync(path.join(app, 'workspace/.app-updates/npm-pending'), 'install');
    assert.equal(run().status, 0); // Leave pending installation to START.bat.
  } finally { fs.rmSync(app, { recursive: true, force: true }); }
});
