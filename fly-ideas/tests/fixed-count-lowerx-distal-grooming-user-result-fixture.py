#!/usr/bin/env python3
"""Validate persistent extract and full preregistered go of user series84S."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/fixed-count-lowerx-distal-grooming-user-summary-extract.json').read_text(encoding='utf8'))
assert d['source_file_sha256']=='7af53f0d91ab9d12da61d7d0c5f4d209e6e1cd47647ab9c0568dad1943dbc126'
assert d['status']=='completed' and d['protocol_mode']=='fixed_count'
assert d['completion_basis']=='committed_candidate_count'
assert d['candidates']==d['accepted_candidates']==16384
assert d['training_frames']==802816==16384*49
assert d['source84r_model_sha256']=='1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c'
assert d['candidate_model_sha256']=='a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f'
t=d['training_timing'];assert t['batches']==8192 and t['timed_candidates']==16384 and t['missing_candidates']==0
assert t['coordinator_wall_seconds_sum']>0 and t['worker_cpu_seconds_sum']>0
p=d['primary'];assert p['passed']
assert all(x['passed'] for x in p['axes'].values())
assert p['axes']['right_distal']['wins_vs_zero']==147 and p['axes']['right_distal']['wins_vs_source84r']==100
assert p['combined']['candidate']<p['combined']['source84r']<p['combined']['zero']
assert all(p['combined']['candidate']<p['combined'][k] for k in ('shuffled','static','closed'))
assert all(x['passed'] for x in p['body_x_safeguards']+p['camera_z_safeguards'])
assert p['corners_passed']==16 and p['corners_required']==12
assert all(x['passed'] for x in p['corner_results'])
lr=p['lower_x_right_distal_comparator'];assert lr['passed']
assert lr['candidate']<lr['source84r']<lr['zero']
assert lr['wins_vs_zero']==73>=lr['required_vs_zero']==60
assert lr['wins_vs_source84r']==62>=lr['required_vs_source84r']==48
x=d['derived'];assert x['test_records']==160 and x['distinct_test_ids']==list(range(321,331)) and x['distinct_corner_ids']==list(range(1,17))
assert x['state_unchanged_cases']==160 and x['empty_rgb_cases']==0 and x['min_changed_rgb_values']>0
assert x['candidate_case_wins']=={'zero':160,'source84r':104,'shuffled':160,'static':160,'closed':146}
assert min(x['corner_axis_min_wins'].values())>=8
assert x['lower_x_right_distal_by_motion']['327']=={'wins_vs_zero':8,'wins_vs_source84r':3}
overlap=x['unique_motion_overlap'];assert sum(v['under_0_001_deg'] for v in overlap.values())==0 and sum(v['under_1_deg'] for v in overlap.values())==0 and sum(v['under_5_deg'] for v in overlap.values())==96
assert d['audit']['accepted_total']==16384 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive']
print('Series84S is internally consistent: fixed16384 candidates completed and every global, comparator, lower-X, X/Z, control and16/16 corner gate passed.')
