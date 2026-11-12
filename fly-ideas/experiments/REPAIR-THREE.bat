@echo off
chcp 65001 >nul
setlocal DisableDelayedExpansion
set "APP=%~dp0"
if not exist "%APP%START.bat" if exist "%APP%..\START.bat" for %%I in ("%APP%..") do set "APP=%%~fI\"
if not exist "%APP%START.bat" (
  echo Не найдена папка Fly Ideas. Переместите этот BAT в папку, где лежит START.bat.
  pause
  exit /b 1
)
cd /d "%APP%"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js не найден. Исправление остановлено.
  pause
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo npm не найден. Исправление остановлено.
  pause
  exit /b 1
)
echo Проверка библиотеки three. Закройте перед этим все окна Fly Ideas.
node -e "const f=require('fs');const s=f.readFileSync(process.argv[1],'utf8');const k='// FLY_REPAIR_'+'SCRIPT';new Function('require','process',s.slice(s.lastIndexOf(k)+k.length))(require,process)" "%~f0" check
if errorlevel 2 goto failed
if not errorlevel 1 goto done
for /f "delims=" %%V in ('node -e "let v=require('./package-lock.json').packages['node_modules/three'].version;if(!/^\d+\.\d+\.\d+$/.test(v))process.exit(1);console.log(v)"') do set "THREE_VERSION=%%V"
if not defined THREE_VERSION goto failed
for /f "delims=" %%D in ('node -e "console.log(require('fs').mkdtempSync(require('path').join(require('os').tmpdir(),'fly-three-')))"') do set "FLY_REPAIR_TMP=%%D"
if not defined FLY_REPAIR_TMP goto failed
echo Скачиваю three версии %THREE_VERSION%. Нужен интернет.
call npm pack "three@%THREE_VERSION%" --ignore-scripts --pack-destination "%FLY_REPAIR_TMP%"
if errorlevel 1 goto failed
node -e "const f=require('fs');const s=f.readFileSync(process.argv[1],'utf8');const k='// FLY_REPAIR_'+'SCRIPT';new Function('require','process',s.slice(s.lastIndexOf(k)+k.length))(require,process)" "%~f0" install
if errorlevel 1 goto failed
:done
echo.
echo Готово. Теперь откройте START.bat обычным двойным щелчком.
pause
exit /b 0
:failed
echo.
echo Исправление остановлено. Сохраните это сообщение и пришлите его.
echo Рабочие данные и существующие библиотеки не удалялись этим BAT.
pause
exit /b 1
// FLY_REPAIR_SCRIPT
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
try {
  const app = process.cwd();
  const manifest = JSON.parse(fs.readFileSync(path.join(app, 'package.json'), 'utf8'));
  const lock = JSON.parse(fs.readFileSync(path.join(app, 'package-lock.json'), 'utf8'));
  const entry = lock.packages && lock.packages['node_modules/three'];
  if (!manifest.dependencies || !manifest.dependencies.three || !entry || !/^\d+\.\d+\.\d+$/.test(entry.version) || !/^sha512-[A-Za-z0-9+/]+={0,2}$/.test(entry.integrity)) throw new Error('В package.json или package-lock.json нет корректной записи three. Нужна диагностика обновления.');
  const modules = path.join(app, 'node_modules');
  const st = fs.lstatSync(modules);
  if (!st.isDirectory() || st.isSymbolicLink()) throw new Error('node_modules отсутствует или является ссылкой. Автоматическое исправление остановлено.');
  const target = path.join(modules, 'three');
  const targetExists = () => { try { fs.lstatSync(target); return true; } catch (e) { if (e.code === 'ENOENT') return false; throw e; } };
  if (process.argv[2] === 'check') {
    if (targetExists()) {
      const real = fs.lstatSync(target);
      if (real.isSymbolicLink() || !real.isDirectory()) throw new Error('Путь node_modules/three уже занят. Ничего не заменено.');
      const installed = JSON.parse(fs.readFileSync(path.join(target, 'package.json'), 'utf8'));
      if (installed.name !== 'three' || installed.version !== entry.version || !fs.existsSync(path.join(target, 'build', 'three.module.js')) || !fs.existsSync(path.join(target, 'examples', 'jsm', 'controls', 'OrbitControls.js'))) throw new Error('Папка three уже существует, но выглядит неполной или другой версии. Ничего не заменено.');
      console.log('Библиотека three уже установлена; ничего не изменено.');
      process.exit(0);
    }
    console.log('Библиотека three отсутствует, можно установить её отдельно.');
    process.exit(1);
  }
  if (process.argv[2] !== 'install') throw new Error('Неизвестный этап исправления.');
  const tmp = process.env.FLY_REPAIR_TMP;
  if (!tmp || !fs.statSync(tmp).isDirectory()) throw new Error('Нет временной папки загрузки.');
  const tarball = path.join(tmp, `three-${entry.version}.tgz`);
  const actual = 'sha512-' + crypto.createHash('sha512').update(fs.readFileSync(tarball)).digest('base64');
  if (actual !== entry.integrity) throw new Error('Контрольная сумма архива не совпадает с package-lock.json. Ничего не установлено.');
  if (targetExists()) throw new Error('Папка three появилась во время установки. Ничего не заменено.');
  const result = spawnSync('tar', ['-xzf', tarball, '-C', tmp], { encoding: 'utf8', windowsHide: true });
  if (result.error || result.status !== 0) throw new Error(`Не удалось распаковать архив: ${result.error?.message || result.stderr || result.status}`);
  const source = path.join(tmp, 'package');
  const info = JSON.parse(fs.readFileSync(path.join(source, 'package.json'), 'utf8'));
  if (info.name !== 'three' || info.version !== entry.version || !fs.existsSync(path.join(source, 'build', 'three.module.js')) || !fs.existsSync(path.join(source, 'examples', 'jsm', 'controls', 'OrbitControls.js'))) throw new Error('Архив не содержит ожидаемую библиотеку three.');
  const stage = fs.mkdtempSync(path.join(modules, '.fly-three-'));
  try {
    fs.cpSync(source, stage, { recursive: true, force: false, errorOnExist: true });
    if (targetExists()) throw new Error('Папка three появилась во время установки. Ничего не заменено.');
    fs.renameSync(stage, target);
  } catch (e) {
    // This uniquely named temporary directory was created by this operation.
    try { fs.rmSync(stage, { recursive: true, force: true }); } catch {}
    throw e;
  }
  console.log(`Установлена three ${entry.version} после проверки SHA-512.`);
} catch (e) {
  console.error('ОШИБКА:', e.message || String(e));
  process.exit(2);
}
