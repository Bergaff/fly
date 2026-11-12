const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..');
test('серия 72 фиксирует ровно пять часов и пять holdout до обучения',()=>{
 const source=fs.readFileSync(path.join(root,'experiments/templates/72_five_hour_wing_observation.py'),'utf8');
 assert.match(source,/hours != 5/);assert.match(source,/budget != 18000/);assert.match(source,/choices=\(5,\)/);
 assert.match(source,/prepared_holdouts_seed_7202/);assert.match(source,/default_rng\(7202\)/);assert.match(source,/holdout_\{70\+i:03d\}/);
 assert.match(source,/synchronous=FULL/);assert.match(source,/workers':2,'batch':2/);assert.match(source,/request_pause/);
 const bat=fs.readFileSync(path.join(root,'experiments/RUN-FIVE-HOUR-WING-OBSERVATION.bat'),'utf8');
 assert.match(bat,/72_five_hour_wing_observation\.py/);assert.doesNotMatch(bat,/pip install|python -m venv/);
 assert.ok(fs.existsSync(path.join(root,'experiments/reports/five-hour-wing-observation-plan.md')));
});
