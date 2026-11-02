const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const fsp = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');
const vm = require('node:vm');
const zlib = require('node:zlib');
const { spawnSync } = require('node:child_process');

const root = path.join(__dirname, '..');
const script = path.join(root, 'experiments/templates/21_check_linked_data.py');
const python = [process.env.FLY_TEST_PYTHON, 'python3', 'python'].filter(Boolean).find((p) => spawnSync(p, ['-c', 'import sys']).status === 0);

test('IPC связывает файлы, передаёт пути запущенному Python и не меняет данные', { skip: !python && 'Python не найден' }, async () => {
  const dir = await fsp.mkdtemp(path.join(os.tmpdir(), 'fly-links-'));
  try {
    const mainPath = path.join(root, 'electron/main.cjs');
    const realRequire = require('node:module').createRequire(mainPath);
    const handlers = new Map();
    let selected = '';
    let onExit;
    const electron = {
      app: { getPath: (name) => path.join(dir, name), whenReady: () => new Promise(() => {}), on: () => {} },
      ipcMain: { handle: (name, fn) => handlers.set(name, fn) }, BrowserWindow: {}, shell: {},
      dialog: { showOpenDialog: async () => selected ? { canceled: false, filePaths: [selected] } : { canceled: true, filePaths: [] } },
    };
    const fakeProcess = { ...process, env: { ...process.env, VITE_DEV_SERVER_URL: 'http://localhost:5173', FLY_CONNECTOME: 'not-inherited' }, platform: process.platform };
    const source = await fsp.readFile(mainPath, 'utf8');
    vm.runInNewContext(`${source}\npickPython = async () => ({exe: ${JSON.stringify(python)}, cmd: ${JSON.stringify(python)}, version: 'test'});\nregisterIpc(() => ({webContents:{send:(_channel, event) => { if(event.stream === 'exit') onExit(event); }}}));`, {
      require: (name) => name === 'electron' ? electron : realRequire(name),
      __dirname: path.join(dir, 'app', 'electron'), process: fakeProcess, console, setTimeout, clearTimeout, Buffer, URL,
      onExit: (ev) => onExit(ev), module: { exports: {} },
    });
    const call = (name, ...args) => handlers.get(`fly:${name}`)(null, ...args);
    const env = await call('checkEnv');
    assert.ok(Object.hasOwn(env.packages, 'duckdb'), 'duckdb must be included in environment diagnostics');
    assert.ok(Object.hasOwn(env.packages, 'joblib'), 'joblib must be included in environment diagnostics');
    const file = path.join(dir, 'ручные связи.csv.gz');
    const contents = zlib.gzipSync('pre_root_id,post_root_id,syn_count\n720575940000000001,720575940000000002,7\n');
    await fsp.writeFile(file, contents);
    selected = file;
    const links = await call('chooseDataFile', 'connections');
    assert.equal(links.connections.path, file);
    assert.equal(links.connections.available, true);
    assert.equal((await call('getDataFileLinks')).connections.path, file);
    const types = path.join(dir, 'типы.csv');
    await fsp.writeFile(types, 'root_id,primary_type\n720575940000000001,KC\n');
    selected = types;
    await call('chooseDataFile', 'cell_types');
    assert.equal((await call('getDataFileLinks')).cell_types.path, types);
    const authorConn = path.join(dir, 'авторские связи.parquet');
    const authorList = path.join(dir, 'авторские нейроны.csv');
    await fsp.writeFile(authorConn, 'test reference'); await fsp.writeFile(authorList, 'id\n1\n');
    selected = authorConn; await call('chooseDataFile', 'shiu_connections');
    selected = authorList; await call('chooseDataFile', 'shiu_neurons');
    assert.equal((await call('getDataFileLinks')).shiu_connections.path, authorConn);
    assert.equal((await call('getDataFileLinks')).shiu_neurons.path, authorList);
    await assert.rejects(call('chooseDataFile', '__proto__'), /Неизвестный/);
    selected = '';
    await call('chooseDataFile', 'connections');
    assert.equal((await call('getDataFileLinks')).connections.path, file);
    const ws = await call('projectPaths', 'idea:example');
    const otherWs = await call('projectPaths', 'idea:other');
    const newName = '25_shiu_v630_control.py';
    const templateDir = path.join(dir, 'app', 'experiments', 'templates');
    await fsp.mkdir(templateDir, {recursive: true});
    await fsp.copyFile(path.join(root, 'experiments/templates', newName), path.join(templateDir, newName));
    await assert.rejects(fsp.stat(path.join(ws.code, newName)), {code: 'ENOENT'});
    await assert.rejects(call('prepareV630Template', 'project'), /идею/);
    const prepared = await call('prepareV630Template', 'idea:example');
    assert.equal(prepared.added, true); assert.equal(prepared.matches, true);
    assert.equal((await call('prepareV630Template', 'idea:example')).added, false);
    await assert.rejects(fsp.stat(path.join(otherWs.code, newName)), {code: 'ENOENT'});
    await fsp.writeFile(path.join(ws.code, newName), '# user edit\n');
    assert.equal((await call('prepareV630Template', 'idea:example')).matches, false);
    assert.equal(await fsp.readFile(path.join(ws.code, newName), 'utf8'), '# user edit\n');
    const originalFiles = ['26_shiu_original_check.py', '26_shiu_author_model.py', '26_shiu_author_LICENSE.txt'];
    for (const name of originalFiles) await fsp.copyFile(path.join(root, 'experiments/templates', name), path.join(templateDir, name));
    await assert.rejects(call('prepareShiuOriginal', 'project'), /идею/);
    const original = await call('prepareShiuOriginal', 'idea:example');
    assert.equal(original.matches, true); assert.equal(original.added.length, 3);
    for (const name of originalFiles) await assert.rejects(fsp.stat(path.join(otherWs.code, name)), {code: 'ENOENT'});
    assert.equal((await call('prepareShiuOriginal', 'idea:example')).added.length, 0);
    await fsp.writeFile(path.join(ws.code, originalFiles[1]), '# edited author file\n');
    const conflict = await call('prepareShiuOriginal', 'idea:example');
    assert.equal(conflict.matches, false); assert.equal(conflict.conflict, originalFiles[1]);
    assert.equal(await fsp.readFile(path.join(ws.code, originalFiles[1]), 'utf8'), '# edited author file\n');
    const topName = '27_shiu_top200_v630.py';
    // Маленькая заглушка проверяет IPC и папку запуска, модель не запускается.
    const stub = `import os,json,sys,hashlib
from pathlib import Path
base=Path(__file__).parent/'25_shiu_v630_control.py'
raw=base.read_bytes().replace(b'\\r\\n',b'\\n')
open(os.path.join(os.environ['FLY_RUN_DIR'],'summary.json'),'w').write(json.dumps({'base':hashlib.sha256(raw).hexdigest(),'script':__file__,'args':sys.argv[1:]}))
`;
    await fsp.writeFile(path.join(templateDir, topName), stub);
    await fsp.writeFile(path.join(ws.code, topName), '# user version, do not run\n');
    await assert.rejects(call('prepareTop200', 'project'), /идею/);
    const topReady = await call('prepareTop200', 'idea:example');
    assert.equal(topReady.matches, true); assert.equal(topReady.added.length, 2);
    assert.equal(topReady.code, path.join(ws.code, '.shiu-top200-v630'));
    assert.equal(await fsp.readFile(path.join(ws.code, newName), 'utf8'), '# user edit\n');
    assert.equal(await fsp.readFile(path.join(ws.code, topName), 'utf8'), '# user version, do not run\n');
    assert.equal((await call('prepareTop200', 'idea:example')).added.length, 0);
    await assert.rejects(fsp.stat(path.join(otherWs.code, '.shiu-top200-v630')), {code: 'ENOENT'});
    await assert.rejects(call('runTop200', 'idea:example', ['--anything']), /параметры/);
    const topCompleted = new Promise((resolve) => { onExit = resolve; });
    const topRun = await call('runTop200', 'idea:example', ['--simulate', '--pilot']);
    assert.equal((await topCompleted).code, 0);
    const topReport = JSON.parse(await fsp.readFile(path.join(topRun.runDir, 'summary.json'), 'utf8'));
    assert.equal(topReport.base, 'b5f200a3e9472c9aa6318acab8b5fb928d23af3b458c2d43fc29909241e95711');
    assert.equal(topReport.script, path.join(topReady.code, topName));
    assert.deepEqual(topReport.args, ['--simulate', '--pilot']);
    await fsp.writeFile(path.join(topReady.code, newName), '# do not overwrite\n');
    const topConflict = await call('prepareTop200', 'idea:example');
    assert.equal(topConflict.matches, false); assert.equal(topConflict.conflict, newName);
    await assert.rejects(call('runTop200', 'idea:example', ['--simulate']), /не перезаписана/);
    assert.equal(await fsp.readFile(path.join(topReady.code, newName), 'utf8'), '# do not overwrite\n');
    assert.equal(await fsp.readFile(path.join(ws.code, newName), 'utf8'), '# user edit\n');
    const lesionName = '28_shiu_lesions_v630.py';
    await fsp.writeFile(path.join(templateDir, lesionName), stub);
    await assert.rejects(call('prepareLesions', 'project'), /идею/);
    const lesionReady = await call('prepareLesions', 'idea:example');
    assert.equal(lesionReady.matches, true); assert.equal(lesionReady.added.length, 3);
    assert.equal(lesionReady.code, path.join(ws.code, '.shiu-lesions-v630'));
    assert.equal(await fsp.readFile(path.join(ws.code, newName), 'utf8'), '# user edit\n');
    await assert.rejects(call('runLesions', 'idea:example', ['--simulate', '--top-run', 'x', '--pilot', '--resume-from', 'x']), /параметры/);
    const lesionCompleted = new Promise((resolve) => { onExit = resolve; });
    const lesionRun = await call('runLesions', 'idea:example', ['--simulate', '--top-run', 'C:/top with spaces', '--pilot']);
    assert.equal((await lesionCompleted).code, 0);
    const lesionReport = JSON.parse(await fsp.readFile(path.join(lesionRun.runDir, 'summary.json'), 'utf8'));
    assert.equal(lesionReport.script, path.join(lesionReady.code, lesionName));
    assert.deepEqual(lesionReport.args, ['--simulate', '--top-run', 'C:/top with spaces', '--pilot']);
    assert.equal(lesionReport.base, 'b5f200a3e9472c9aa6318acab8b5fb928d23af3b458c2d43fc29909241e95711');
    const parallelName = '29_shiu_lesions_parallel.py';
    const parallelStub = `import json,os,time
out=os.environ['FLY_RUN_DIR']
while not os.path.exists(os.path.join(out,'stop.request')): time.sleep(0.02)
with open(os.path.join(out,'summary.json'),'w') as f: json.dump({'status':'stopped','args':__import__('sys').argv[1:]},f)
`;
    await fsp.writeFile(path.join(templateDir, parallelName), parallelStub);
    const parallelReady = await call('prepareParallelLesions', 'idea:example');
    assert.equal(parallelReady.name, parallelName); assert.equal(parallelReady.added.length, 1);
    assert.equal(parallelReady.code, lesionReady.code);
    await assert.rejects(call('runParallelLesions','idea:example',['--simulate','--top-run','x','--pilot']), /предыдущего/);
    const parallelCompleted = new Promise((resolve) => { onExit = resolve; });
    const parallelArgs = ['--simulate','--top-run','C:/top folder','--resume-from','C:/old lesions'];
    const parallelRun = await call('runParallelLesions','idea:example',parallelArgs);
    assert.equal((await call('getActiveRun','idea:example')).runId,parallelRun.runId);
    await call('killRun',parallelRun.runId);
    assert.equal((await parallelCompleted).code,0, 'graceful stop must not kill the process');
    const parallelReport=JSON.parse(await fsp.readFile(path.join(parallelRun.runDir,'summary.json'),'utf8'));
    assert.equal(parallelReport.status,'stopped'); assert.deepEqual(parallelReport.args,parallelArgs);
    assert.equal(await fsp.readFile(path.join(parallelRun.runDir,'stop.request'),'utf8'),'stop');
    const overviewName='30_shiu_lesion_overview.py'; const selectedName='31_shiu_selected_lesions.py';
    await fsp.writeFile(path.join(templateDir, overviewName), stub); await fsp.writeFile(path.join(templateDir, selectedName), stub);
    await assert.rejects(call('prepareFocusedLesions','project','overview'),/идею/);
    const overviewReady=await call('prepareFocusedLesions','idea:example','overview');
    assert.equal(overviewReady.name,overviewName);assert.equal(overviewReady.added.length,4);
    const selectedReady=await call('prepareFocusedLesions','idea:example','selected');
    assert.equal(selectedReady.name,selectedName);assert.equal(selectedReady.added.length,1);
    await assert.rejects(call('runFocusedLesions','idea:example','overview',['--source','x','--top-run','y','--mode','bad']),/параметры/);
    await assert.rejects(call('runFocusedLesions','idea:example','selected',['--source','x','--top-run','y','--stage','review']),/параметры/);
    const focusedDone=new Promise((resolve)=>{onExit=resolve;});
    const focused=await call('runFocusedLesions','idea:example','overview',['--source','C:/old run','--top-run','C:/top','--mode','individuality']);
    assert.equal((await focusedDone).code,0);
    const focusedReport=JSON.parse(await fsp.readFile(path.join(focused.runDir,'summary.json'),'utf8'));
    assert.equal(focusedReport.script,path.join(overviewReady.code,overviewName));
    const planDone=new Promise((resolve)=>{onExit=resolve;});
    const planArgs=['--source','C:/old run','--top-run','C:/top','--stage','plan'];
    const plan=await call('runFocusedLesions','idea:example','selected',planArgs);
    assert.equal((await planDone).code,0);
    assert.deepEqual(JSON.parse(await fsp.readFile(path.join(plan.runDir,'summary.json'),'utf8')).args,planArgs);
    // Большую выборочную симуляцию нельзя запускать параллельно с другим расчётом.
    const longName='another_wait.py'; await fsp.writeFile(path.join(otherWs.code,longName),'import time\ntime.sleep(2)\n');
    const otherDone=new Promise((resolve)=>{onExit=resolve;});
    await call('runScript','idea:other',longName,[]);
    await assert.rejects(call('runFocusedLesions','idea:example','selected',['--source','x','--top-run','y','--stage','singles']),/остановите другие/);
    assert.equal((await otherDone).code,0);
    const sharedName='32_shiu_shared_study.py';await fsp.writeFile(path.join(templateDir,sharedName),stub+"if 'singles' in sys.argv: import time; time.sleep(2)\n");
    const readyShared=await call('prepareSharedStudy','idea:i-lesions');
    assert.equal(readyShared.name,sharedName);assert.equal(readyShared.added.length,6);
    let sharedList=await call('listSharedStudies');assert.equal(sharedList.studies.length,0);
    const sharedRoot=sharedList.root;const sharedId='Study_20261102_123456_abcdef12';
    const sharedPath=path.join(sharedRoot,sharedId);await fsp.mkdir(sharedPath,{recursive:true});
    await fsp.writeFile(path.join(sharedPath,'manifest.json'),JSON.stringify({kind:'fly-shiu-v630-shared-1',id:sharedId,label:'Новый набор',created_unix:1}));
    await fsp.writeFile(path.join(sharedPath,'progress.json'),JSON.stringify({stage:'singles',completed:35,total:330}));
    sharedList=await call('listSharedStudies');assert.equal(sharedList.studies.length,1);assert.equal(sharedList.studies[0].id,sharedId);assert.equal(sharedList.studies[0].progress.completed,35);
    await assert.rejects(call('runSharedStudy','idea:i-lesions',['--stage','plan','--study','../wrong']),/набор/);
    await assert.rejects(call('runSharedStudy','idea:other',['--stage','plan','--study',sharedId]),/идею/);
    const sharedDone=new Promise((resolve)=>{onExit=resolve;});
    const sharedArgs=['--stage','plan','--study',sharedId];
    const sharedRun=await call('runSharedStudy','idea:i-lesions',sharedArgs);
    assert.equal((await sharedDone).code,0);
    assert.match(path.basename(sharedRun.runDir),/02_план_лезий/);
    const sharedReport=JSON.parse(await fsp.readFile(path.join(sharedRun.runDir,'summary.json'),'utf8'));
    assert.equal(sharedReport.script,path.join(readyShared.code,sharedName));assert.deepEqual(sharedReport.args,sharedArgs);
    assert.equal(await fsp.readFile(path.join(sharedPath,'manifest.json'),'utf8'),JSON.stringify({kind:'fly-shiu-v630-shared-1',id:sharedId,label:'Новый набор',created_unix:1}));
    const concurrentOther=new Promise((resolve)=>{onExit=resolve;});await call('runScript','idea:other',longName,[]);
    await assert.rejects(call('runSharedStudy','idea:i-lesions',['--stage','singles','--study',sharedId]),/остановите другие/);
    assert.equal((await concurrentOther).code,0);
    const concurrentShared=new Promise((resolve)=>{onExit=resolve;});await call('runSharedStudy','idea:i-lesions',['--stage','singles','--study',sharedId]);
    await assert.rejects(call('runScript','idea:other',longName,[]),/остановите другие/);
    assert.equal((await concurrentShared).code,0);
    // Пилот получает изолированные копии, только внутри идеи индивидуальности.
    const individualName='33_shiu_individuality_pilot.py';
    await fsp.writeFile(path.join(templateDir,individualName),`import os,sys,json,time\nout=os.environ['FLY_RUN_DIR']\nif sys.argv[2]=='pilot-run':\n while not os.path.exists(os.path.join(out,'stop.request')): time.sleep(0.02)\nwith open(os.path.join(out,'summary.json'),'w') as f: json.dump({'args':sys.argv[1:],'script':__file__,'root':os.environ['FLY_SHIU_SHARED_ROOT'],'threads':os.environ['OPENBLAS_NUM_THREADS']},f)\n`);
    await assert.rejects(call('runSharedStudy','idea:i-lesions',['--stage','pilot-run','--study',sharedId]),/идею/);
    await assert.rejects(call('runSharedStudy','idea:i-individuality',['--stage','pilot-plan','--study','../wrong']),/набор/);
    const individualDone=new Promise((resolve)=>{onExit=resolve;});
    const individualArgs=['--stage','pilot-plan','--study',sharedId];
    const individualRun=await call('runSharedStudy','idea:i-individuality',individualArgs);
    assert.equal((await individualDone).code,0);
    const individualReport=JSON.parse(await fsp.readFile(path.join(individualRun.runDir,'summary.json'),'utf8'));
    assert.deepEqual(individualReport.args,individualArgs);assert.match(individualReport.script,/\.shiu-individuality-v630/);
    assert.equal(individualReport.root,sharedRoot);assert.equal(individualReport.threads,'1');
    const pilotOther=new Promise((resolve)=>{onExit=resolve;});await call('runScript','idea:other',longName,[]);
    await assert.rejects(call('runSharedStudy','idea:i-individuality',['--stage','pilot-run','--study',sharedId]),/остановите другие/);
    assert.equal((await pilotOther).code,0);
    const pilotDone=new Promise((resolve)=>{onExit=resolve;});
    const pilotRun=await call('runSharedStudy','idea:i-individuality',['--stage','pilot-run','--study',sharedId]);
    await assert.rejects(call('runScript','idea:other',longName,[]),/остановите другие/);
    await call('killRun',pilotRun.runId);assert.equal((await pilotDone).code,0);
    assert.equal(await fsp.readFile(path.join(pilotRun.runDir,'stop.request'),'utf8'),'stop');
    const extensionName='34_shiu_individuality_extension.py';
    await fsp.writeFile(path.join(templateDir,extensionName),`import os,sys,json,time\nout=os.environ['FLY_RUN_DIR']\nif sys.argv[2]=='extend-run':\n while not os.path.exists(os.path.join(out,'stop.request')): time.sleep(0.02)\nwith open(os.path.join(out,'summary.json'),'w') as f: json.dump({'args':sys.argv[1:],'script':__file__,'root':os.environ['FLY_SHIU_SHARED_ROOT'],'threads':os.environ['OPENBLAS_NUM_THREADS']},f)\n`);
    await assert.rejects(call('runSharedStudy','idea:i-lesions',['--stage','extend-run','--study',sharedId]),/идею/);
    const extPlanDone=new Promise((resolve)=>{onExit=resolve;});
    const extArgs=['--stage','extend-plan','--study',sharedId];
    const extPlan=await call('runSharedStudy','idea:i-individuality',extArgs);assert.equal((await extPlanDone).code,0);
    const extReport=JSON.parse(await fsp.readFile(path.join(extPlan.runDir,'summary.json'),'utf8'));
    assert.deepEqual(extReport.args,extArgs);assert.match(extReport.script,/\.shiu-individuality-extension-v630/);
    assert.equal(extReport.root,sharedRoot);assert.equal(extReport.threads,'1');
    const extDone=new Promise((resolve)=>{onExit=resolve;});
    const extRun=await call('runSharedStudy','idea:i-individuality',['--stage','extend-run','--study',sharedId]);
    await assert.rejects(call('runScript','idea:other',longName,[]),/остановите другие/);
    await call('killRun',extRun.runId);assert.equal((await extDone).code,0);
    assert.equal(await fsp.readFile(path.join(extRun.runDir,'stop.request'),'utf8'),'stop');
    const holdName='35_shiu_individuality_holdout.py';
    await fsp.writeFile(path.join(templateDir,holdName),`import os,sys,json,time\nout=os.environ['FLY_RUN_DIR']\nif sys.argv[2]=='holdout-run':\n while not os.path.exists(os.path.join(out,'stop.request')): time.sleep(0.02)\nwith open(os.path.join(out,'summary.json'),'w') as f: json.dump({'args':sys.argv[1:],'script':__file__,'root':os.environ['FLY_SHIU_SHARED_ROOT'],'threads':os.environ['OPENBLAS_NUM_THREADS']},f)\n`);
    await assert.rejects(call('runSharedStudy','idea:i-lesions',['--stage','holdout-run','--study',sharedId]),/идею/);
    const holdPlanDone=new Promise((resolve)=>{onExit=resolve;});
    const holdArgs=['--stage','holdout-plan','--study',sharedId];
    const holdPlan=await call('runSharedStudy','idea:i-individuality',holdArgs);assert.equal((await holdPlanDone).code,0);
    const holdReport=JSON.parse(await fsp.readFile(path.join(holdPlan.runDir,'summary.json'),'utf8'));
    assert.deepEqual(holdReport.args,holdArgs);assert.match(holdReport.script,/\.shiu-individuality-holdout-v630/);
    assert.equal(holdReport.root,sharedRoot);assert.equal(holdReport.threads,'1');
    const holdDone=new Promise((resolve)=>{onExit=resolve;});
    const holdRun=await call('runSharedStudy','idea:i-individuality',['--stage','holdout-run','--study',sharedId]);
    await assert.rejects(call('runScript','idea:other',longName,[]),/остановите другие/);
    await call('killRun',holdRun.runId);assert.equal((await holdDone).code,0);
    assert.equal(await fsp.readFile(path.join(holdRun.runDir,'stop.request'),'utf8'),'stop');
    await fsp.writeFile(path.join(ws.code, 'wait_test.py'), 'import time\ntime.sleep(0.5)\n');
    const waitCompleted = new Promise((resolve) => { onExit = resolve; });
    const waiting = await call('runScript', 'idea:example', 'wait_test.py', []);
    assert.equal((await call('getActiveRun', 'idea:example')).runId, waiting.runId);
    assert.equal(await call('getActiveRun', 'idea:other'), null);
    await assert.rejects(call('runScript', 'idea:example', 'wait_test.py', []), /уже выполняется/);
    assert.equal((await waitCompleted).code, 0);
    assert.equal(await call('getActiveRun', 'idea:example'), null);
    await assert.rejects(call('runScript', 'idea:example', 'not_present.py', []), /не найден/);
    await fsp.copyFile(script, path.join(ws.code, '21_check_linked_data.py'));
    const completed = new Promise((resolve) => { onExit = resolve; });
    const run = await call('runScript', 'idea:example', '21_check_linked_data.py', []);
    assert.equal((await completed).code, 0);
    const report = JSON.parse(await fsp.readFile(path.join(run.runDir, 'summary.json'), 'utf8'));
    assert.equal(report.connections.path, file);
    assert.equal(report.connections.ok, true);
    assert.equal(report.connections.example_ids[0].pre, '720575940000000001');
    assert.equal(report.cell_types.path, types);
    assert.equal(report.cell_types.ok, true);
    assert.deepEqual(await fsp.readFile(file), contents);
    await fsp.writeFile(path.join(ws.code, 'check_refs.py'), `import os,json\nopen(os.path.join(os.environ['FLY_RUN_DIR'],'summary.json'),'w').write(json.dumps({k:os.environ.get(k) for k in ('FLY_CONNECTOME','FLY_SHIU_CONNECTIONS','FLY_SHIU_NEURONS')}))\n`);
    const refCompleted = new Promise((resolve) => { onExit = resolve; });
    const refRun = await call('runScript', 'idea:example', 'check_refs.py', []);
    assert.equal((await refCompleted).code, 0);
    const refReport = JSON.parse(await fsp.readFile(path.join(refRun.runDir, 'summary.json'), 'utf8'));
    assert.equal(refReport.FLY_CONNECTOME, file);
    assert.equal(refReport.FLY_SHIU_CONNECTIONS, authorConn);
    assert.equal(refReport.FLY_SHIU_NEURONS, authorList);
    await call('clearDataFile', 'shiu_neurons');
    assert.equal((await call('getDataFileLinks')).shiu_neurons.path, '');
    assert.equal((await call('getDataFileLinks')).connections.path, file);
    await fsp.unlink(file);
    assert.equal((await call('getDataFileLinks')).connections.available, false);
    await call('clearDataFile', 'connections');
    assert.equal((await call('getDataFileLinks')).connections.path, '');
    const completed2 = new Promise((resolve) => { onExit = resolve; });
    const next = await call('runScript', 'idea:example', '21_check_linked_data.py', []);
    assert.equal((await completed2).code, 1);
    const missing = JSON.parse(await fsp.readFile(path.join(next.runDir, 'summary.json'), 'utf8'));
    assert.equal(missing.connections.ok, false); // не наследуем FLY_CONNECTOME из ОС
  } finally { await fsp.rm(dir, { recursive: true, force: true }); }
});

test('проверка связей читает только выборку и сообщает о неподходящих файлах', { skip: !python && 'Python не найден' }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-linked-check-'));
  try {
    const file = path.join(dir, 'connections.csv.gz');
    const source = 'pre_root_id,post_root_id,neuropil,syn_count,nt_type\n' + Array.from({length: 30}, (_, i) => `720575940000000001,720575940000000002,MB,${i + 1},GABA`).join('\n') + '\n';
    fs.writeFileSync(file, zlib.gzipSync(source));
    const ann = path.join(dir, 'types.csv');
    fs.writeFileSync(ann, 'root_id,primary_type\n720575940000000001,KC\n');
    const run = (connections, extra = {}) => {
      const result = spawnSync(python, [script], { encoding: 'utf8', env: { ...process.env, FLY_RUN_DIR: dir, FLY_CONNECTOME: connections, FLY_ANNOTATIONS: '', FLY_CELL_TYPES: '', FLY_NEUROTRANSMITTERS: '', ...extra } });
      return { code: result.status, report: JSON.parse(fs.readFileSync(path.join(dir, 'summary.json'), 'utf8')) };
    };
    const good = run(file, { FLY_CELL_TYPES: ann });
    assert.equal(good.code, 0);
    assert.equal(good.report.connections.sample_rows, 20);
    assert.equal(good.report.connections.example_ids[0].pre, '720575940000000001');
    assert.equal(good.report.cell_types.id_column, 'root_id');
    assert.match(good.report.scope, /не проверка всей таблицы/);
    fs.writeFileSync(ann, 'id,unrelated\n1,2\n');
    const badAnn = run(file, { FLY_CELL_TYPES: ann });
    assert.equal(badAnn.code, 1);
    assert.equal(badAnn.report.cell_types.ok, false);
    const bad = path.join(dir, 'bad.csv'); fs.writeFileSync(bad, 'x,y\n1,2\n');
    assert.equal(run(bad).report.connections.ok, false);
    fs.writeFileSync(bad, 'pre_root_id,post_root_id\n7.2e17,720575940000000002\n');
    assert.match(run(bad).report.connections.error, /некорректных ID/);
    assert.equal(run(path.join(dir, 'missing.csv')).report.connections.ok, false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

const hasArrow = python && spawnSync(python, ['-c', 'import pyarrow.parquet']).status === 0;
test('таблица Parquet сохраняет точные 64-битные ID нейронов', { skip: !hasArrow && 'pyarrow не установлен в тестовом Python' }, () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fly-parquet-'));
  try {
    const input = path.join(dir, 'connections.parquet');
    const create = spawnSync(python, ['-c', 'import pyarrow as a, pyarrow.parquet as p, sys; p.write_table(a.table({"pre_root_id": [720575940000000001], "post_root_id": [720575940000000002], "syn_count": [5]}), sys.argv[1])', input], { encoding: 'utf8' });
    assert.equal(create.status, 0, create.stderr);
    const result = spawnSync(python, [script], { encoding: 'utf8', env: { ...process.env, FLY_RUN_DIR: dir, FLY_CONNECTOME: input, FLY_ANNOTATIONS: '', FLY_CELL_TYPES: '', FLY_NEUROTRANSMITTERS: '' } });
    assert.equal(result.status, 0, result.stderr);
    const report = JSON.parse(fs.readFileSync(path.join(dir, 'summary.json'), 'utf8'));
    assert.equal(report.connections.example_ids[0].pre, '720575940000000001');
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});
