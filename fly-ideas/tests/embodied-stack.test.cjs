const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..');
test('этап 70 разделяет демонстратор, runtime и научные gates',()=>{
 const source=fs.readFileSync(path.join(root,'experiments/templates/70_embodied_connectome_pipeline.py'),'utf8');
 assert.match(source,/reviewed_visual_mapping/);assert.match(source,/preregistered_motor_readout/);assert.match(source,/scientific_result.*False/);
 const setup=fs.readFileSync(path.join(root,'experiments/SETUP-EMBODIED-FLY-STACK.bat'),'utf8');
 assert.match(setup,/\.venv-flyvis/);assert.match(setup,/\.venv-flygym/);assert.doesNotMatch(setup,/\.venv-two-flies.*pip install/);
 const main=fs.readFileSync(path.join(root,'electron/main.cjs'),'utf8');assert.match(main,/fly:loadSeries69Demo/);assert.match(main,/isSymbolicLink/);
 for(const name of ['src/views/series69-demonstrator.tsx','src/lib/series69-demo.ts','experiments/reports/embodied-connectome-integration-plan.md'])assert.ok(fs.existsSync(path.join(root,name)),name);
});
