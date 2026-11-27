#!/usr/bin/env python3
"""Validate extract and strict no-go of user series84X."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/lower-weighted-paired-view-user-summary-extract.json').read_text(encoding='utf8'))
assert d['source_file_sha256']=='540aff2d1237f77824811ba784f9a59011b446d347816f736188350cde73a9b7'
assert d['schema']=='lower-weighted-paired-view-result-v1' and d['status']=='completed'
assert d['protocol_mode']=='fixed_count' and d['completion_basis']=='committed_candidate_count'
assert (d['candidates'],d['accepted_candidates'],d['training_frames'])==(16384,16384,802816)
assert d['source84v_model_sha256']=='44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af'
assert d['candidate_model_sha256']=='fd12401a6cccdb17815c3f323553b38ffd22a17d541608a037dfa1813052acb5'
p=d['primary'];assert not p['passed']
rd=p['axes']['right_distal'];assert not rd['passed'];assert rd['candidate']>rd['source84v'];assert (rd['wins_vs_source84v'],rd['wins_vs_source84s'],rd['wins_vs_source84r'])==(81,131,124);assert rd['wins_vs_source84v']<96
assert all(x['passed'] for a,x in p['axes'].items() if a!='right_distal')
c=p['combined'];assert c['candidate']>c['source84v'] and c['candidate']<min(c[k] for k in ('source84s','source84r','zero','shuffled','static','closed'))
lr=p['lower_x_right_distal_comparator'];assert lr['passed'];assert lr['candidate']<min(lr[k] for k in ('source84v','source84s','source84r','zero'));assert (lr['wins_vs_zero'],lr['wins_vs_source84v'],lr['wins_vs_source84s'],lr['wins_vs_source84r'])==(73,53,66,68)
assert all(x['passed'] for x in p['body_x_safeguards']+p['camera_z_safeguards']);assert p['corners_passed']==16>=p['corners_required']==12
x=d['derived'];assert x['test_records']==160 and x['distinct_test_ids']==list(range(401,411)) and x['distinct_corner_ids']==list(range(1,17));assert x['state_unchanged_cases']==x['state_sha_match_cases']==160
assert x['candidate_case_wins']=={'zero':160,'source84v':71,'source84s':142,'source84r':128,'shuffled':160,'static':160,'closed':160}
u=x['upper_x_right_distal'];uw=x['upper_x_right_distal_wins'];assert u['candidate']>u['source84v'] and uw['vs_source84v']==28 and uw['vs_zero']==70
assert x['failed_corners']==[] and x['corner_axis_min_wins']['right_distal']==7
assert x['lower_x_right_distal_by_motion']['401']['wins_vs_source84v']==0 and x['lower_x_right_distal_by_motion']['405']['wins_vs_source84v']==1
assert x['overlap_totals']=={'overlap_under_0_001_deg':0,'overlap_under_1_deg':0,'overlap_under_5_deg':1264}
assert d['audit']['accepted_total']==16384 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive']
print('Series84X is internally consistent: lower-X target passes, but upper-X loss causes global right-distal and combined failures versus frozen84V; strict model-development no-go.')
