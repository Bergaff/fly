#!/usr/bin/env python3
"""Arithmetic and provenance checks for the user-transcribed series 66 summary."""
from __future__ import annotations
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'experiments/reports/observe-delay-autonomous-replay-user-summary-extract.json'
d=json.loads(p.read_text(encoding='utf8')); rows=d['holdouts']; agg=d['aggregate']
assert d['transcription']['status']=='completed' and len(rows)==5
assert d['protocol']['training_episodes']==60094 and d['protocol']['internal_state_coefficients']==72
assert len({x['source_sha256'] for x in rows})==len({x['motion_sha256'] for x in rows})==5
for x in rows:
 assert math.isclose(x['normal_rmse_rad']-x['zero_rmse_rad'],x['normal_minus_zero_rmse_rad'],abs_tol=1e-15)
 assert set(x['normal_axis_rmse_rad'])==set(x['zero_axis_rmse_rad'])=={'left_x','left_y','left_z','right_x','right_y','right_z'}
assert math.isclose(sum(x['normal_minus_zero_rmse_rad'] for x in rows)/5,agg['primary_mean_normal_minus_zero_rmse_rad'],abs_tol=1e-15)
assert math.isclose(sum(x['normal_rmse_rad'] for x in rows)/5,agg['mean_normal_rmse_rad'],abs_tol=1e-15)
assert math.isclose(sum(x['zero_rmse_rad'] for x in rows)/5,agg['mean_zero_rmse_rad'],abs_tol=1e-15)
assert sum(x['normal_rmse_rad']<x['zero_rmse_rad'] for x in rows)==agg['normal_better_than_zero']==1
for name,value in agg['mean_control_rmse_rad'].items():
 assert math.isclose(sum(x['controls_rmse_rad'][name] for x in rows)/5,value,abs_tol=1e-15)
# Equal frame counts permit pooled per-axis RMSE from the five reported per-holdout RMSE values.
axis={}
for name in rows[0]['normal_axis_rmse_rad']:
 normal=math.sqrt(sum(x['normal_axis_rmse_rad'][name]**2 for x in rows)/5)
 zero=math.sqrt(sum(x['zero_axis_rmse_rad'][name]**2 for x in rows)/5)
 axis[name]=(normal,zero)
assert axis['left_y'][0]<axis['left_y'][1] and axis['right_y'][0]<axis['right_y'][1]
assert all(axis[name][0]>axis[name][1] for name in ('left_x','left_z','right_x','right_z'))
print('series 66 user result fixture passed')
