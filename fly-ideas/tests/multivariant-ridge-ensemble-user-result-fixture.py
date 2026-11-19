#!/usr/bin/env python3
"""Validate development selection and untouched-final go of user series84Z."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/multivariant-ridge-ensemble-user-summary-extract.json').read_text(encoding='utf8'))
assert d['source_file_sha256']=='19f9d1c37edc15570a58eefc0239bf54b817bd6bada9f72dfbf8975aac714671'
assert d['schema']=='multivariant-ridge-ensemble-result-v1' and d['status']=='completed'
assert d['protocol_mode']=='fixed_count' and d['completion_basis']=='committed_candidate_count'
assert (d['candidates'],d['accepted_candidates'],d['training_frames'])==(16384,16384,802816)
assert d['source84v_model_sha256']=='44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af'
assert d['selected_variant']=='ridge_0175' and d['selected_model_sha256']=='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0'
dev=d['development'];assert dev['motions']==list(range(421,431));assert not any(x['passed'] for x in dev['decisions'].values())
keys=dev['selection_keys'];assert keys['ridge_0175']==[0,5,1.48125,-2.9527904445179867,0];assert max(keys,key=lambda k:tuple(keys[k]))=='ridge_0175'
dr=dev['decisions']['ridge_0175']['axes']['right_distal'];dl=dev['decisions']['ridge_0175']['lower_x_right_distal_comparator'];assert (dr['wins_vs_source84v'],dl['wins_vs_source84v'])==(121,58);assert not dl['passed'] and dl['wins_vs_zero']==55<60
p=d['primary'];assert p['passed'] and all(x['passed'] for x in p['axes'].values())
rd=p['axes']['right_distal'];assert rd['candidate']<rd['source84v']<rd['source84s']<rd['source84r']<rd['zero'];assert (rd['wins_vs_zero'],rd['wins_vs_source84v'],rd['wins_vs_source84s'],rd['wins_vs_source84r'])==(139,149,143,149)
lr=p['lower_x_right_distal_comparator'];assert lr['passed'] and lr['candidate']<lr['source84v'];assert (lr['wins_vs_zero'],lr['wins_vs_source84v'],lr['wins_vs_source84s'],lr['wins_vs_source84r'])==(68,77,71,76)
c=p['combined'];assert c['candidate']<min(c[k] for k in ('source84v','source84s','source84r','zero','shuffled','static','closed'))
assert all(x['passed'] for x in p['body_x_safeguards']+p['camera_z_safeguards']);assert p['corners_passed']==16>=p['corners_required']==12
x=d['derived'];assert x['test_records']==160 and x['distinct_test_ids']==list(range(431,441)) and x['distinct_corner_ids']==list(range(1,17));assert x['state_unchanged_cases']==x['state_sha_match_cases']==160
assert x['candidate_case_wins']=={'zero':160,'source84v':142,'source84s':155,'source84r':157,'shuffled':160,'static':160,'closed':160}
u=x['upper_x_right_distal'];uw=x['upper_x_right_distal_wins'];assert u['candidate']<u['source84v'] and (uw['vs_zero'],uw['vs_source84v'],uw['vs_source84s'],uw['vs_source84r'])==(71,72,72,73)
assert x['failed_corners']==[] and x['corner_axis_min_wins']['right_distal']==8
assert x['overlap_totals']=={'overlap_under_0_001_deg':0,'overlap_under_1_deg':0,'overlap_under_5_deg':1456}
assert d['audit']['accepted_total']==16384 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive']
print('Series84Z is internally consistent: ridge_0175 selected on development and passes every preregistered untouched-final gate; model-development go, frozen replication still required.')
