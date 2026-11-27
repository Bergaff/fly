#!/usr/bin/env python3
"""Validate the transcribed series 76 primary and derived combined RMSE."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'experiments/reports/frozen-visible-grooming-transfer-user-summary-extract.json').read_text(encoding='utf-8'))
assert data['status']=='completed' and data['no_retraining'] and not data['primary_passed']
axes=list(data['matched']);assert len(axes)==6
assert all(data['matched'][a]['passed'] and data['matched'][a]['wins']==10 for a in axes)
assert all(not data['geometric_transfer'][a]['passed'] and data['geometric_transfer'][a]['better_than_zero_conditions']<2 for a in axes)

def combined(values):return math.sqrt(sum(x*x for x in values)/len(values))
derived=data['derived_combined_pooled_rmse']
assert math.isclose(combined([data['matched'][a]['new'] for a in axes]),derived['matched'],abs_tol=1e-15)
assert math.isclose(combined([data['matched'][a]['zero'] for a in axes]),derived['zero'],abs_tol=1e-15)
for condition in ('fov50','fov65','lateral_camera','body_shift'):
 assert math.isclose(combined([data['geometric_transfer'][a][condition] for a in axes]),derived[condition],abs_tol=1e-15)
assert derived['matched']<derived['zero']<derived['fov50']
assert data['diagnostic_wins_vs_zero']=={'matched':10,'temporal_shuffle':4,'one_eye':0,'distal_mask':0}
print('Series 76 matched success and geometric-transfer failure are consistent.')
