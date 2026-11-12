const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..');
test('этап 70 разделяет демонстратор, runtime и научные gates',()=>{
 const source=fs.readFileSync(path.join(root,'experiments/templates/70_embodied_connectome_pipeline.py'),'utf8');
 assert.match(source,/reviewed_visual_mapping/);assert.match(source,/preregistered_motor_readout/);assert.match(source,/scientific_result.*False/);
 const setup=fs.readFileSync(path.join(root,'experiments/SETUP-EMBODIED-FLY-STACK.bat'),'utf8');
 assert.match(setup,/Данные и окружение/);assert.doesNotMatch(setup,/pip install|download-pretrained/);
 const main=fs.readFileSync(path.join(root,'electron/main.cjs'),'utf8');
 assert.match(main,/fly:loadSeries69Demo/);assert.match(main,/holdoutIndex = 1/);assert.match(main,/availableHoldouts/);assert.match(main,/fly:chooseSeries69Demo/);assert.match(main,/series69DemoFolder/);assert.match(main,/matched-encoder-ablation/);assert.match(main,/isSymbolicLink/);
 assert.match(main,/fly:setupEmbodiedEnv/);assert.match(main,/flyvis==\$\{EMBODIED_FLYVIS_VERSION\}/);assert.match(main,/flygym==\$\{EMBODIED_FLYGYM_VERSION\}/);
 assert.match(main,/download-pretrained/);assert.match(main,/FLYVIS_ROOT_DIR/);assert.match(main,/\.venv-flyvis/);assert.match(main,/\.venv-flygym/);
 const view=fs.readFileSync(path.join(root,'src/views/brain-view.tsx'),'utf8');assert.match(view,/установить всё для зрения и тела/);assert.match(view,/setupEmbodiedEnv/);
 const demo=fs.readFileSync(path.join(root,'src/views/series69-demonstrator.tsx'),'utf8');assert.match(demo,/Выберите одно из пяти новых движений/);assert.match(demo,/Смотреть повтор/);assert.match(demo,/RMSE по осям/);
 const causal=fs.readFileSync(path.join(root,'experiments/templates/71_visual_population_causal_study.py'),'utf8');assert.match(causal,/T4a/);assert.match(causal,/mapping_permutation/);assert.match(causal,/Do not approve by name equality alone/);
 for(const name of ['src/views/series69-demonstrator.tsx','src/lib/series69-demo.ts','experiments/reports/embodied-connectome-integration-plan.md','experiments/RUN-VISUAL-POPULATION-CAUSAL-STUDY.bat','experiments/reports/visual-population-causal-study-plan.md'])assert.ok(fs.existsSync(path.join(root,name)),name);
});
