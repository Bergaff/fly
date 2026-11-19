#!/usr/bin/env python3
"""Validate the user-transcribed series 75 result extract."""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'experiments/reports/eight-hour-visible-foreleg-grooming-user-summary-extract.json').read_text(encoding='utf-8'))
assert data['status']=='completed' and data['active_training_seconds']>=28800
assert data['candidates']==data['accepted_candidates']==54296
assert data['training_frames']==2660504 and data['primary_passed']
rows=data['per_test_combined'];assert [r['test_id'] for r in rows]==list(range(101,111))
for model in ('new','zero','training_mean'):
    pooled=math.sqrt(sum(r[model]**2 for r in rows)/len(rows))
    assert math.isclose(pooled,data['pooled_rmse'][model],rel_tol=0,abs_tol=1e-15)
assert sum(r['new']<r['zero'] for r in rows)==data['combined_wins']['vs_zero']==10
assert sum(r['new']<r['training_mean'] for r in rows)==data['combined_wins']['vs_training_mean']==10
expected=(1-data['pooled_rmse']['new']/data['pooled_rmse']['zero'])*100
assert math.isclose(expected,data['derived']['relative_reduction_vs_zero_percent'],rel_tol=0,abs_tol=1e-14)
assert set(data['axes'])=={'left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal'}
assert all(v['passed'] and v['new']<v['zero'] and v['new']<v['training_mean'] for v in data['axes'].values())
assert data['axes']['left_distal']['wins_vs_zero']==data['axes']['right_distal']['wins_vs_zero']==9
assert min(v['wins_vs_zero'] for v in data['axes'].values())>=7
assert not data['audit']['is_exhaustive'] and data['audit']['under_5_deg']==98
print('Series 75 pooled, paired, axis-primary and audit extract are consistent.')
