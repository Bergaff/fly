const fs=require('node:fs');const path=require('node:path');const test=require('node:test');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');
const runner=fs.readFileSync(path.join(root,'experiments/templates/78_eight_hour_view_robust_autonomous_grooming.py'),'utf8');
const bat=fs.readFileSync(path.join(root,'experiments/RUN-EIGHT-HOUR-VIEW-ROBUST-AUTONOMOUS-GROOMING.bat'),'utf8');
test('series 78 preregisters continuous view augmentation and unseen views',()=>{
 for(const text of ["'seed':7801","'view_seed':7803","'view_seed':7804","list(range(141,151))","'camera_fov_deg_range':[30,70]","'body_y_range':[-.32,.32]"])assert.ok(runner.includes(text),text);
});
test('series 78 autonomous replay has immutable compressed state and forbidden inputs',()=>{
 for(const text of ['state_coefficients\':72','delay_s\':.5','observation RGB','teacher commands','saved framewise predictions','state_sha256_before_delay','state_sha256_after_delay'])assert.ok(runner.includes(text),text);
 assert.ok(runner.includes("better==3"));
});
test('series 78 uses the existing environment and one double-click BAT',()=>{
 assert.ok(bat.includes('workspace\\.venv-two-flies\\Scripts\\python.exe'));
 assert.ok(bat.includes('78_eight_hour_view_robust_autonomous_grooming.py'));
 assert.ok(!bat.toLowerCase().includes('pip install'));
});
