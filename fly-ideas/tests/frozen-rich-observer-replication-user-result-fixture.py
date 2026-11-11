#!/usr/bin/env python3
"""Arithmetic checks for the user-transcribed series 68 frozen replication."""
from __future__ import annotations
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];d=json.loads((ROOT/'experiments/reports/frozen-rich-observer-replication-user-summary-extract.json').read_text(encoding='utf8'));rows=d['holdouts'];agg=d['aggregate'];means=agg['mean_rmse_rad'];names=('normal','zero','static','shuffled','reversed','closed')
assert d['transcription']['status']=='completed' and len(rows)==5 and d['protocol']['source_training_episodes']==60000
assert len({r['source_sha256'] for r in rows})==len({r['motion_sha256'] for r in rows})==5
for name in names:assert math.isclose(sum(r[name] for r in rows)/5,means[name],abs_tol=1e-15)
for name in names[1:]:assert math.isclose(means['normal']-means[name],agg['normal_minus_control_rmse_rad'][name],abs_tol=1e-15)
assert agg['primary_pass'] is True and agg['normal_better_than_zero']==agg['normal_better_than_each_primary_control']==5
assert all(r['normal']<r[name] for r in rows for name in names[1:])
for i,name in enumerate(d['axis_order']):
 normal=math.sqrt(sum(r['normal_axis'][i]**2 for r in rows)/5);zero=math.sqrt(sum(r['zero_axis'][i]**2 for r in rows)/5);assert normal<zero,(name,normal,zero)
assert d['protocol']['source_model_sha256']=='6c2eb4a1a6f111ad8d6184ca0778e2934ae3a538d33075961ba65bc9f3fd9f96'
print('series 68 frozen replication user result fixture passed')
