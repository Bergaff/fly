#!/usr/bin/env python3
"""Validate extract and strict near-miss no-go of user series84W."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];d=json.loads((ROOT/'experiments/reports/frozen-paired-view-replication-user-summary-extract.json').read_text(encoding='utf8'))
assert d['source_file_sha256']=='1fa95757de83b09218987bf7c8ef89e49029a3620c3c39de7f82211d170c910b'
assert d['schema']=='frozen-paired-view-replication-result-v1' and d['status']=='completed'
q=d['protocol'];assert q['mode']=='full' and q['motion_seed']==8428 and q['geometry_corners']==16 and not q['training_allowed'];assert [x['id'] for x in q['holdouts']]==list(range(381,391))
assert q['runner84v_sha256']=='05a0cdd4696af5b8901a1d34a205db8a286264f518cb54e93d1e0b9f9e9e4a52';assert q['source84v_model_sha256']=='44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af'
p=d['primary'];assert not p['passed'] and all(x['passed'] for x in p['axes'].values());rd=p['axes']['right_distal'];assert rd['candidate']<rd['source84s']<rd['source84r']<rd['zero'];assert (rd['wins_vs_zero'],rd['wins_vs_source84s'],rd['wins_vs_source84r'])==(124,129,131)
c=p['combined'];assert c['candidate']<c['source84s']<c['source84r']<c['zero'] and all(c['candidate']<c[k] for k in ('shuffled','static','closed'))
lr=p['lower_x_right_distal_comparator'];assert not lr['passed'];assert lr['candidate']<lr['source84s']<lr['source84r']<lr['zero'];assert lr['wins_vs_zero']==59<lr['required_vs_zero']==60;assert lr['wins_vs_source84s']==60>=lr['required_vs_each_source']==48 and lr['wins_vs_source84r']==64
assert not p['body_x_safeguards'][0]['passed'] and p['body_x_safeguards'][1]['passed'];assert all(x['passed'] for x in p['camera_z_safeguards']);assert p['corners_passed']==14>=p['corners_required']==12
x=d['derived'];assert x['test_records']==160 and x['distinct_test_ids']==list(range(381,391)) and x['distinct_corner_ids']==list(range(1,17));assert x['state_unchanged_cases']==160 and x['empty_rgb_cases']==0 and x['min_changed_rgb_values']==25486
assert x['candidate_case_wins']=={'zero':160,'source84s':146,'source84r':149,'shuffled':160,'static':160,'closed':160};assert x['failed_corners']==[9,13] and x['corner_axis_min_wins']['right_distal']==6
assert x['lower_x_right_distal_by_motion']['382']=={'wins_vs_zero':1,'wins_vs_source84s':2,'wins_vs_source84r':2,'cases':8};assert x['lower_x_right_distal_by_motion']['388']=={'wins_vs_zero':1,'wins_vs_source84s':7,'wins_vs_source84r':6,'cases':8}
ov=x['unique_motion_overlap'];assert sum(v['under_0_001_deg'] for v in ov.values())==0 and sum(v['under_1_deg'] for v in ov.values())==0 and sum(v['under_5_deg'] for v in ov.values())==122
assert d['audit']['accepted_total']==16384 and d['audit']['audited_count']==128 and not d['audit']['is_exhaustive'];assert d['source84v_primary']['passed']
print('Series84W is internally consistent: global dual-comparator effects replicate, but lower-X right-distal absolute wins are59/80 below60/80; strict replication no-go.')
