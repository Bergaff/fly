const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..');
test('серия 75 исправляет невидимые capsule и блокирует constant RGB',()=>{
 const s=fs.readFileSync(path.join(root,'experiments/templates/75_eight_hour_visible_foreleg_grooming.py'),'utf8');
 assert.match(s,/hours != 8/);assert.match(s,/budget != 28800/);assert.match(s,/SeedSequence\(\[7501,ident\]\)/);assert.match(s,/prepared_holdouts_seed_7502/);assert.match(s,/holdout_\{100\+i:03d\}/);
 assert.equal((s.match(/type=\\?"ellipsoid\\?"/g)||[]).length>=6,true);assert.doesNotMatch(s,/type=\\?"capsule\\?"/);
 for(const guard of ['unique<10','changed<100','feature_std<1e-4','joint_changed'])assert.match(s,new RegExp(guard.replace(/[<]/g,'\\<')));
 assert.match(s,/visual_preflight/);assert.match(s,/saved\['visual_preflight'\]/);assert.match(s,/VISUAL GUARD изменился/);assert.match(s,/axis_primary/);
 const bat=fs.readFileSync(path.join(root,'experiments/RUN-EIGHT-HOUR-VISIBLE-FORELEG-GROOMING.bat'),'utf8');assert.match(bat,/75_eight_hour_visible_foreleg_grooming\.py/);assert.doesNotMatch(bat,/pip install|python -m venv/);
 assert.ok(fs.existsSync(path.join(root,'experiments/reports/eight-hour-visible-foreleg-grooming-plan.md')));
});
