#!/usr/bin/env python3
"""Validate the compact extract and blocking decision for user series 80."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/canonical-view-representation-prototype-user-summary-extract.json').read_text(encoding='utf-8'))
assert d['status']=='completed' and d['protocol']['mode']=='prototype' and not d['protocol']['scientific_result']
assert d['source_file_sha256']=='953131963d0b8a232e41bec5a1f8b5bf93fc916db39b6ca8bc6009b99e9462c9'
assert not d['go_for_long_training'] and d['held_corners_outer_improved']==5 and d['held_corners_total']==16
assert d['combined']['canonical']<d['combined']['raw']<d['combined']['zero']
assert d['feature_view_distance']['canonical']<d['feature_view_distance']['raw']
assert len(d['axes'])==6
assert all(not d['axes'][a]['passed'] for a in ('left_proximal','left_distal','right_proximal','right_distal'))
assert d['axes']['left_middle']['passed'] and d['axes']['right_middle']['passed']
assert all(d['axes'][a]['canonical']<d['axes'][a]['raw'] for a in ('left_proximal','left_distal','right_proximal','right_distal'))
assert all(d['axes'][a]['wins_vs_raw']<.60*d['axes'][a]['cases'] for a in ('left_proximal','left_distal','right_proximal','right_distal'))
der=d['derived'];assert der['fov30']['border_touch_eyes']==der['fov30']['eye_observations']==96
assert der['fov30']['canonical_rmse']>der['fov30']['raw_rmse'] and der['fov30']['canonical_feature_distance']>der['fov30']['raw_feature_distance']
assert der['fov70']['canonical_rmse']<der['fov70']['raw_rmse'] and der['fov70']['canonical_feature_distance']<der['fov70']['raw_feature_distance']
assert len(d['cells'])==16 and sum(c['all_outer_improved'] for c in d['cells'])==5
print('Series 80 small aggregate gain, FOV asymmetry and no-go decision are consistent.')
