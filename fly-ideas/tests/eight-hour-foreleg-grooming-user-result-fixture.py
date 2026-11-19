#!/usr/bin/env python3
"""Validate the transcribed series 74 result and the diagnosed stimulus failure."""
import json, math, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'experiments/reports/eight-hour-foreleg-grooming-user-summary-extract.json').read_text(encoding='utf-8'))
runner=(ROOT/'experiments/templates/74_eight_hour_foreleg_grooming_observation.py').read_text(encoding='utf-8')
renderer=(ROOT/'experiments/templates/38_two_flies_observation.py').read_text(encoding='utf-8')
assert data['status']=='completed' and data['active_training_seconds']>=28800
assert data['candidates']==data['accepted_candidates']==80794 and data['training_frames']==3958906
assert not data['primary_passed'] and data['scientific_validity']=='invalid_visual_stimulus'
assert math.isclose(data['pooled_rmse']['new'],data['pooled_rmse']['training_mean'],rel_tol=0,abs_tol=1e-15)
assert (1-data['pooled_rmse']['new']/data['pooled_rmse']['zero'])*100 < .011
assert sum(v['reported_passed'] for v in data['axes'].values())==2
assert data['axes']['left_distal']['new']>data['axes']['left_distal']['zero']
assert data['axes']['right_distal']['new']>data['axes']['right_distal']['zero']
diag=data['local_diagnostic']
assert diag['unique_rgb_frames']==1 and diag['changed_adjacent_rgb_values']==0 and diag['max_feature_std']<1e-12
assert len(diag['command_std_deg'])==6 and min(diag['command_std_deg'])>20
# The exact incompatible combination remains frozen in the completed runner.
assert runner.count('type=\"capsule\"')==6
assert 'o = ((origin - center) @ rot) / size' in renderer
assert 'd = (rays @ rot) / size' in renderer
assert data['audit']['under_5_deg']==93 and not data['audit']['is_exhaustive']
print('Series 74 extract and constant-RGB root cause are consistent.')
