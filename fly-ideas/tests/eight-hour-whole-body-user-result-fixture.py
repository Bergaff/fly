#!/usr/bin/env python3
"""Recompute the published aggregates from the user-transcribed series 73 extract."""
import json, math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'experiments/reports/eight-hour-whole-body-observation-user-summary-extract.json').read_text(encoding='utf-8'))
assert data['status']=='completed'
assert data['active_training_seconds']>=28800
assert data['candidates']==data['accepted_candidates']==45226
assert len(data['per_test'])==10 and [x['test_id'] for x in data['per_test']]==list(range(81,91))
assert all(x['frames']==49 for x in data['per_test'])

def pooled(values,frames):
    return math.sqrt(sum(v*v*n for v,n in zip(values,frames))/sum(frames))

frames=[x['frames'] for x in data['per_test']]
for model in ('new','zero','training_mean'):
    got=pooled([x['rmse'][model] for x in data['per_test']],frames)
    assert math.isclose(got,data['pooled_rmse_rad_equivalent'][model],rel_tol=0,abs_tol=1e-15)

primary=data['primary']
assert primary['paired_wins_vs_zero']==sum(x['rmse']['new']<x['rmse']['zero'] for x in data['per_test'])==10
assert primary['paired_wins_vs_training_mean']==sum(x['rmse']['new']<x['rmse']['training_mean'] for x in data['per_test'])==10
assert primary['passed'] and data['pooled_rmse_rad_equivalent']['new']<data['pooled_rmse_rad_equivalent']['zero']

for axis,expected in data['derived']['axis'].items():
    for model in ('new','zero','training_mean'):
        got=pooled([x['axis_rmse'][axis][model] for x in data['per_test']],frames)
        assert math.isclose(got,expected['pooled_rmse'][model],rel_tol=0,abs_tol=1e-15)
    assert expected['paired_wins_new_vs_zero']==sum(x['axis_rmse'][axis]['new']<x['axis_rmse'][axis]['zero'] for x in data['per_test'])
    assert expected['paired_wins_new_vs_training_mean']==sum(x['axis_rmse'][axis]['new']<x['axis_rmse'][axis]['training_mean'] for x in data['per_test'])

assert data['derived']['axis']['left_foreleg']['paired_wins_new_vs_zero']==5
assert data['derived']['axis']['right_foreleg']['paired_wins_new_vs_zero']==5
assert not data['audit']['is_exhaustive'] and data['audit']['audited_count']==128
print('Series 73 user extract reproduces pooled, paired and per-axis conclusions.')
