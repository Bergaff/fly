#!/usr/bin/env python3
"""Validate the persistent extract of the user series84T accounting result."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/console-compute-accounting-user-summary-extract.json').read_text(encoding='utf8'))
assert d['source_file_sha256']=='0d4302c46b4eaf830fba0e528e4cf55193bd1414b24a5a3ab5a7edcacce1d56d'
assert d['status']=='completed'
p=d['protocol'];q=p['quick_edit_action']
assert p['script_sha256']=='fb9b532fdf9286561da0756364ecfdbb5e7e3e19238df1d1c4ad6488d0321859'
assert p['runner84r_sha256']=='d60f23d33185fde7c18e56ccf26a510166955ded4c5384ec0578ec67185cfd6d'
assert p['fixed_count_not_time_budget'] and not p['scientific_model_training']
assert q=={'platform':'nt','supported':True,'disabled':True,'mode_before':487,'mode_after':423,'quick_edit_before':True,'quick_edit_after':False}
assert d['candidate_count']==128 and d['frames']==6272==128*49
assert d['all_finite'] and d['unique_motion_hashes']==d['unique_rgb_hashes']==128
assert d['suspected_blocked_batches']==0
assert d['coordinator_wall_seconds']==77.40691250000009
assert d['worker_cpu_seconds_sum']==144.5 and d['worker_cpu_parallel_equivalent_seconds']==72.25
assert d['throughput_candidates_per_wall_hour']>5900
x=d['derived']
assert x['records']==128 and x['batches']==64
assert x['first_sequence_id']==900000 and x['last_sequence_id']==900127
assert x['frames_recomputed']==6272 and x['all_record_hashes_unique']
assert x['parallel_cpu_utilization']>.93
assert x['batch_wall_excluding_startup']['max']<1.25
assert x['max_wall_ratio_excluding_startup']<1.002
assert x['feature_max_std']['min']>0
assert d['largest_batch']['batch_index']==0 and d['largest_batch']['wall_seconds']>5
print('Series84T is internally consistent: QuickEdit was enabled then disabled, 128/128 fixed candidates completed, and no post-startup blocked batch was detected.')
