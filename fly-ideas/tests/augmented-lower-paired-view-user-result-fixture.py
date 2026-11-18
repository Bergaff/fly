#!/usr/bin/env python3
"""Validate extract and strict no-go of user series84Y."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/augmented-lower-paired-view-user-summary-extract.json').read_text(encoding='utf8'))
assert d['source_file_sha256']=='bb5ed966f0eae0870246287aeb7962e498d237306d2a34ff06527e7292b2d671'
assert d['schema']=='lower-augmented-paired-view-result-v1' and d['status']=='completed'
assert d['protocol_mode']=='fixed_count' and d['completion_basis']=='committed_candidate_count'
assert (d['candidates'],d['accepted_candidates'],d['training_frames'])==(20480,20480,1003520)
assert d['source84v_model_sha256']=='44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af'
assert d['candidate_model_sha256']=='92a26360e994a70efced86ac1b5f9157ddafb63d78488ba387233304c59f6bf0'
p=d['primary'];assert not p['passed']
rd=p['axes']['right_distal'];assert not rd['passed'] and rd['candidate']>rd['source84v'];assert (rd['wins_vs_zero'],rd['wins_vs_source84v'],rd['wins_vs_source84s'],rd['wins_vs_source84r'])==(146,53,149,136);assert rd['wins_vs_source84v']<96
assert all(x['passed'] for a,x in p['axes'].items() if a!='right_distal')
c=p['combined'];assert c['candidate']>c['source84v'] and c['candidate']<min(c[k] for k in ('source84s','source84r','zero','shuffled','static','closed'))
lr=p['lower_x_right_distal_comparator'];assert not lr['passed'] and lr['candidate']>lr['source84v'];assert (lr['wins_vs_zero'],lr['wins_vs_source84v'],lr['wins_vs_source84s'],lr['wins_vs_source84r'])==(73,43,74,68);assert lr['wins_vs_source84v']<lr['required_vs_each_source']==48
assert not p['body_x_safeguards'][0]['passed'] and p['body_x_safeguards'][1]['passed'];assert all(x['passed'] for x in p['camera_z_safeguards']);assert p['corners_passed']==16>=p['corners_required']==12
x=d['derived'];assert x['test_records']==160 and x['distinct_test_ids']==list(range(411,421)) and x['distinct_corner_ids']==list(range(1,17));assert x['state_unchanged_cases']==x['state_sha_match_cases']==160
assert x['candidate_case_wins']=={'zero':160,'source84v':67,'source84s':155,'source84r':148,'shuffled':160,'static':160,'closed':160}
u=x['upper_x_right_distal'];uw=x['upper_x_right_distal_wins'];assert u['candidate']>u['source84v'] and uw['vs_source84v']==10 and uw['vs_zero']==73
assert x['failed_corners']==[] and x['corner_axis_min_wins']['right_distal']==9
assert x['lower_x_right_distal_by_motion']['417']['wins_vs_source84v']==0 and x['lower_x_right_distal_by_motion']['414']['wins_vs_source84v']==1
assert x['overlap_totals']=={'overlap_under_0_001_deg':0,'overlap_under_1_deg':0,'overlap_under_5_deg':1680}
assert d['audit']['accepted_total']==20480 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive']
print('Series84Y is internally consistent: augmentation misses frozen84V globally and in lower-X; strict model-development no-go.')
