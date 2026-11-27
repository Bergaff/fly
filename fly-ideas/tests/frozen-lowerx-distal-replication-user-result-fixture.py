#!/usr/bin/env python3
"""Validate persistent extract and preregistered no-go of user series84U."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/frozen-lowerx-distal-replication-user-summary-extract.json').read_text(encoding='utf8'))
assert d['source_file_sha256']=='5733dcfd2523285f8218a8cf4331fe0a5719e719c2c2bc3d5d97fde74e29f8fc'
assert d['schema']=='frozen-lowerx-distal-replication-result-v1' and d['status']=='completed'
q=d['protocol'];assert q['mode']=='full' and q['motion_seed']==8424 and q['geometry_corners']==16 and not q['training_allowed']
assert q['runner84s_sha256']=='67915637388a508b88c112ce9f39a0396fcc5a2ef9492928f402826809a8dcd2'
assert q['source84s_model_sha256']=='a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f'
assert q['source84r_model_sha256']=='1e90771b23de33d78a4794c1fea265601a62fb8778b89f6db2c074167070e02c'
assert [x['id'] for x in q['holdouts']]==list(range(341,351))
p=d['primary'];assert not p['passed']
assert [a for a,v in p['axes'].items() if not v['passed']]==['right_distal']
rd=p['axes']['right_distal'];assert rd['candidate']>rd['source84r'] and rd['candidate']<rd['zero'];assert rd['wins_vs_zero']==138 and rd['wins_vs_source84r']==77
assert all(p['axes'][a]['candidate']<p['axes'][a]['zero'] for a in p['axes'])
assert p['combined']['candidate']<p['combined']['source84r']<p['combined']['zero']
assert all(p['combined']['candidate']<p['combined'][k] for k in ('shuffled','static','closed'))
lr=p['lower_x_right_distal_comparator'];assert not lr['passed'];assert lr['candidate']<lr['source84r']<lr['zero'];assert lr['wins_vs_zero']==70>=lr['required_vs_zero']==60;assert lr['wins_vs_source84r']==44<lr['required_vs_source84r']==48
assert not p['body_x_safeguards'][0]['passed'] and p['body_x_safeguards'][1]['passed']
assert all(x['passed'] for x in p['camera_z_safeguards'])
assert p['corners_passed']==16 and p['corners_required']==12 and all(x['passed'] for x in p['corner_results'])
x=d['derived'];assert x['test_records']==160 and x['distinct_test_ids']==list(range(341,351)) and x['distinct_corner_ids']==list(range(1,17));assert x['frames_per_case']=={'49':160}
assert x['state_unchanged_cases']==160 and x['empty_rgb_cases']==0 and x['min_changed_rgb_values']==26872
assert x['candidate_case_wins']=={'zero':160,'source84r':78,'shuffled':160,'static':160,'closed':159}
assert min(x['corner_axis_min_wins'].values())==7
assert x['right_distal_by_motion']['344']=={'wins_vs_zero':15,'wins_vs_source84r':1,'cases':16}
assert x['right_distal_by_motion']['347']=={'wins_vs_zero':16,'wins_vs_source84r':1,'cases':16}
assert x['lower_x_right_distal_by_motion']['349']['wins_vs_source84r']==8
ov=x['unique_motion_overlap'];assert sum(v['under_0_001_deg'] for v in ov.values())==0 and sum(v['under_1_deg'] for v in ov.values())==0 and sum(v['under_5_deg'] for v in ov.values())==78
assert d['audit']['accepted_total']==16384 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive']
assert d['source84s_primary']['passed']
print('Series84U is internally consistent: absolute/control/corner signal remains, but global and lower-X right-distal frozen-comparator gates fail; replication no-go.')
