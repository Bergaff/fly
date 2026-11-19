#!/usr/bin/env python3
"""Validate persistent extract and exact preregistered no-go of user series84R."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/distal-robust-grooming-user-summary-extract.json').read_text(encoding='utf8'))
assert d['source_file_sha256']=='f8fb2cd8a8caddaafc986a739ed724ed723f7a5f81dc370dc50114189fb0be22'
assert d['status']=='completed' and d['protocol_mode']=='long'
assert d['active_training_seconds']==34320.625 and d['budget_seconds']==28800
assert d['budget_overrun_seconds']==5520.625
assert d['candidates']==d['accepted_candidates']==1146 and d['training_frames']==56154==1146*49
assert d['source83_model_sha256']=='79ad0b29f904067d3b8ece3e81a395d66606ab7202015d5c47b254bfa484a9fd'
assert d['candidate_model_sha256']=='1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c'

x=d['derived'];p=d['primary']
assert x['test_records']==160
assert x['distinct_test_ids']==list(range(301,311)) and x['distinct_corner_ids']==list(range(1,17))
assert x['state_unchanged_cases']==160 and x['empty_rgb_cases']==0 and x['min_changed_rgb_values']>0
assert x['normal_case_wins']=={'zero':160,'source83':119,'shuffled':160,'static':160,'closed':155}
assert not p['passed']
assert all(row['passed'] for row in p['axes'].values())
assert p['combined']['candidate']<p['combined']['source83']<p['combined']['zero']
assert all(p['combined']['candidate']<p['combined'][k] for k in ('shuffled','static','closed'))
assert [row['passed'] for row in p['body_x_safeguards']]==[False,True]
assert p['body_x_safeguards'][0]['value']==3.82
bad=p['body_x_safeguards'][0]['axes']['right_distal']
assert bad['candidate']<bad['zero'] and bad['wins']==55 and not bad['passed']
assert all(row['passed'] for row in p['camera_z_safeguards'])
assert p['corners_passed']==13 and p['corners_required']==12

failed=d['failed_corners']
assert [row['corner_id'] for row in failed]==[1,2,6]
assert all(row['view']['body_x']==3.82 and row['view']['camera_side']==.14 for row in failed)
assert {a for row in failed for a,v in row['axes'].items() if not v['passed']}=={'left_distal','right_distal'}
assert all(v['candidate']<v['zero'] for row in failed for v in row['axes'].values() if not v['passed'])

assert x['core_motion_axis_wins_vs_zero']['304']['left_distal']==6
assert x['lower_x_right_distal_wins_by_motion']['304']==2
unique=x['unique_motion_overlap']
assert sum(v['under_0_001_deg'] for v in unique.values())==0
assert sum(v['under_1_deg'] for v in unique.values())==0
assert sum(v['under_5_deg'] for v in unique.values())==90
assert d['audit']['accepted_total']==1146 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive']
print('Series84R is internally consistent: all global, comparator, control, camera-Z and corner gates pass, but lower-X right distal is 55/80, so primary remains false.')
