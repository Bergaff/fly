#!/usr/bin/env python3
"""Validate persistent extract and full preregistered go of user series84V."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/paired-view-distal-consistency-user-summary-extract.json').read_text(encoding='utf8'))
assert d['source_file_sha256']=='2097ca310cdaa9baa4f085883857ea58d826d8b0fb8460c8fc236f7d69db1ce3'
assert d['schema']=='paired-view-distal-consistency-result-v1' and d['status']=='completed' and d['protocol_mode']=='fixed_count'
assert d['completion_basis']=='committed_candidate_count' and d['candidates']==d['accepted_candidates']==16384 and d['training_frames']==802816
assert d['source84s_model_sha256']=='a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f'
assert d['source84r_model_sha256']=='1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c'
assert d['candidate_model_sha256']=='44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af'
p=d['primary'];assert p['passed'] and all(v['passed'] for v in p['axes'].values())
rd=p['axes']['right_distal'];assert rd['candidate']<rd['source84s']<rd['source84r']<rd['zero'];assert rd['wins_vs_zero']==144 and rd['wins_vs_source84s']==135 and rd['wins_vs_source84r']==140
assert all(v['candidate']<v['source84s'] and v['candidate']<v['source84r'] and v['candidate']<v['zero'] for v in p['axes'].values())
c=p['combined'];assert c['candidate']<c['source84s']<c['source84r']<c['zero'];assert all(c['candidate']<c[k] for k in ('shuffled','static','closed'))
lr=p['lower_x_right_distal_comparator'];assert lr['passed'] and lr['candidate']<lr['source84s']<lr['source84r']<lr['zero'];assert lr['wins_vs_zero']==69>=lr['required_vs_zero']==60;assert lr['wins_vs_source84s']==61>=lr['required_vs_each_source']==48;assert lr['wins_vs_source84r']==65
assert all(x['passed'] for x in p['body_x_safeguards']+p['camera_z_safeguards']);assert p['corners_passed']==16 and p['corners_required']==12 and all(x['passed'] for x in p['corner_results'])
x=d['derived'];assert x['test_records']==160 and x['distinct_test_ids']==list(range(361,371)) and x['distinct_corner_ids']==list(range(1,17)) and x['frames_per_case']=={'49':160}
assert x['state_unchanged_cases']==160 and x['empty_rgb_cases']==0 and x['min_unique_rgb_frames']==51 and x['min_changed_rgb_values']==28141
assert x['candidate_case_wins']=={'zero':160,'source84s':149,'source84r':150,'shuffled':160,'static':160,'closed':150}
assert min(x['corner_axis_min_wins'].values())==8
assert x['right_distal_by_motion']['361']=={'wins_vs_zero':5,'wins_vs_source84s':11,'wins_vs_source84r':14,'cases':16}
assert x['lower_x_right_distal_by_motion']['361']=={'wins_vs_zero':1,'wins_vs_source84s':6,'wins_vs_source84r':6,'cases':8}
ov=x['unique_motion_overlap'];assert sum(v['overlap_under_0_001_deg'] for v in ov.values())==0 and sum(v['overlap_under_1_deg'] for v in ov.values())==0 and sum(v['overlap_under_5_deg'] for v in ov.values())==108
assert d['audit']['accepted_total']==16384 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive']
print('Series84V is internally consistent: fixed16384 paired-view candidates completed and every dual-comparator, lower-X, X/Z, control and16/16 corner gate passed.')
