const test=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const path=require('node:path');
const root=path.resolve(__dirname,'..');
test('серия 76 frozen transfer не переобучает модель 75',()=>{
 const s=fs.readFileSync(path.join(root,'experiments/templates/76_frozen_visible_grooming_transfer.py'),'utf8');
 assert.match(s,/no_retraining':True/);assert.match(s,/7602/);assert.match(s,/range\(101,111\)/);
 for(const c of ['matched','fov50','fov65','lateral_camera','body_shift','one_eye','distal_mask','temporal_shuffle'])assert.match(s,new RegExp(c));
 assert.match(s,/source_before/);assert.match(s,/better_than_zero_conditions/);
});
test('серия 77 запрещает observation и teacher после задержки',()=>{
 const s=fs.readFileSync(path.join(root,'experiments/templates/77_observe_delay_autonomous_grooming.py'),'utf8');
 assert.match(s,/DELAY_S=\.5/);assert.match(s,/BASIS_DIM=12/);assert.match(s,/state_coefficients':6\*BASIS_DIM/);assert.match(s,/7702/);assert.match(s,/range\(121,131\)/);
 for(const forbidden of ['observation RGB','teacher commands','saved framewise predictions'])assert.match(s,new RegExp(forbidden));
 assert.match(s,/state_sha256_before_delay/);assert.match(s,/state_sha256_after_delay/);assert.match(s,/contact_trace/);assert.match(s,/kinematic qpos/);
});
test('оба этапа запускаются отдельными BAT без установки среды',()=>{
 for(const [bat,runner] of [['RUN-FROZEN-VISIBLE-GROOMING-TRANSFER.bat','76_frozen_visible_grooming_transfer.py'],['RUN-OBSERVE-DELAY-AUTONOMOUS-GROOMING.bat','77_observe_delay_autonomous_grooming.py']]){const s=fs.readFileSync(path.join(root,'experiments',bat),'utf8');assert.match(s,new RegExp(runner.replace('.','\\.')));assert.doesNotMatch(s,/pip install|python -m venv/);}
 assert.ok(fs.existsSync(path.join(root,'experiments/reports/frozen-transfer-and-autonomous-grooming-plan.md')));
});
