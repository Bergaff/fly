const fs=require('node:fs');const path=require('node:path');const test=require('node:test');const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..');const runner=fs.readFileSync(path.join(root,'experiments/templates/79_frozen_view_stress_map.py'),'utf8');const bat=fs.readFileSync(path.join(root,'experiments/RUN-FROZEN-VIEW-STRESS-MAP.bat'),'utf8');
test('series 79 is frozen and isolates its primary subset',()=>{
 for(const x of ["'no_retraining':True","'holdout_seed':7902","list(range(161,165))","c['kind']=='core_corner'","posthoc_series78_failure_probe","passed_cells>=24"])assert.ok(runner.includes(x),x);
 assert.ok(!runner.includes('base.update_stats'));
});
test('series 79 logs view sensitivity, clipping and autonomous state',()=>{
 for(const x of ['rgb_sha256','unique_rgb_frames','changed_rgb_values','normal_feature_max_std','normal_clipped_fraction','state_sha256_before_delay','autonomous_predictions.csv'])assert.ok(runner.includes(x),x);
});
test('series 79 BAT reuses the app environment',()=>{
 assert.ok(bat.includes('workspace\\.venv-two-flies\\Scripts\\python.exe'));assert.ok(bat.includes('79_frozen_view_stress_map.py'));assert.ok(!bat.toLowerCase().includes('pip install'));
});
