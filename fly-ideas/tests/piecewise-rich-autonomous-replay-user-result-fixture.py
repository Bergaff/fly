#!/usr/bin/env python3
"""Arithmetic checks for the user-transcribed completed series 67 result."""
from __future__ import annotations
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=ROOT/'experiments/reports/piecewise-rich-autonomous-replay-user-summary-extract.json';d=json.loads(p.read_text(encoding='utf8'));rows=d['holdouts'];agg=d['aggregate'];names=('normal','zero','static','shuffled','reversed','closed')
assert d['transcription']['status']=='completed' and len(rows)==5
assert d['protocol']['training_episodes']==60000 and d['protocol']['optimizer_steps']==1875
assert len({r['source_sha256'] for r in rows})==len({r['motion_sha256'] for r in rows})==5
for name in names:assert math.isclose(sum(r[name] for r in rows)/5,agg['mean_rmse_rad'][name],abs_tol=1e-15)
for name in names[1:]:assert math.isclose(agg['mean_rmse_rad']['normal']-agg['mean_rmse_rad'][name],agg['normal_minus_control_rmse_rad'][name],abs_tol=1e-15)
assert agg['primary_pass'] is True and agg['normal_better_than_zero']==5
assert all(r['normal']<r[name] for r in rows for name in ('zero','static','shuffled','reversed','closed'))
axis=[]
for i,name in enumerate(d['axis_order']):
 normal=math.sqrt(sum(r['normal_axis'][i]**2 for r in rows)/5);zero=math.sqrt(sum(r['zero_axis'][i]**2 for r in rows)/5);axis.append((name,normal,zero))
assert all(normal<zero for _,normal,zero in axis)
print('series 67 user result fixture passed')
