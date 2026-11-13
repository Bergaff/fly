const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..');
test('серия 74 изолирует шесть суставов grooming и задаёт осевой критерий',()=>{
 const s=fs.readFileSync(path.join(root,'experiments/templates/74_eight_hour_foreleg_grooming_observation.py'),'utf8');
 assert.match(s,/hours != 8/);assert.match(s,/budget != 28800/);assert.match(s,/SeedSequence\(\[7401,ident\]\)/);assert.match(s,/prepared_holdouts_seed_7402/);
 for(const axis of ['left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal'])assert.match(s,new RegExp(axis));
 assert.match(s,/fov=35/);assert.match(s,/three-joint opposed grooming/);assert.match(s,/range\(1,11\)/);assert.match(s,/holdout_\{90\+i:03d\}/);
 assert.match(s,/axis_primary/);assert.match(s,/all\(v\['passed'\] for v in axis_primary\.values\(\)\)/);assert.match(s,/at least 7\/10 paired wins/);
 const bat=fs.readFileSync(path.join(root,'experiments/RUN-EIGHT-HOUR-FORELEG-GROOMING-OBSERVATION.bat'),'utf8');assert.match(bat,/74_eight_hour_foreleg_grooming_observation\.py/);assert.doesNotMatch(bat,/pip install|python -m venv/);
 assert.ok(fs.existsSync(path.join(root,'experiments/reports/eight-hour-foreleg-grooming-observation-plan.md')));
});
