const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..');
test('серия 73 фиксирует broad generator, 8 часов и десять holdout',()=>{
 const s=fs.readFileSync(path.join(root,'experiments/templates/73_eight_hour_broad_motion_observation.py'),'utf8');
 assert.match(s,/hours != 8/);assert.match(s,/budget != 28800/);assert.match(s,/choices=\(8,\)/);
 assert.match(s,/SeedSequence\(\[7301,ident\]\)/);for(const family of ['piecewise5','piecewise9','harmonic','chirp'])assert.match(s,new RegExp(family));
 assert.match(s,/prepared_holdouts_seed_7302/);assert.match(s,/range\(1,11\)/);assert.match(s,/holdout_\{80\+i:03d\}/);
 assert.match(s,/at least 7\/10 paired wins/);assert.match(s,/overlap_sample_broad/);assert.match(s,/synchronous=FULL/);
 const bat=fs.readFileSync(path.join(root,'experiments/RUN-EIGHT-HOUR-BROAD-MOTION-OBSERVATION.bat'),'utf8');assert.match(bat,/73_eight_hour_broad_motion_observation\.py/);assert.doesNotMatch(bat,/pip install|python -m venv/);
 assert.ok(fs.existsSync(path.join(root,'experiments/reports/eight-hour-broad-motion-observation-plan.md')));
});
