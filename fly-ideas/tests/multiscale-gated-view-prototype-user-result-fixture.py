#!/usr/bin/env python3
"""Validate the series 81 no-go and gating diagnostics."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/multiscale-gated-view-prototype-user-summary-extract.json').read_text(encoding='utf-8'))
assert d['status']=='completed' and d['protocol']['mode']=='prototype' and not d['protocol']['scientific_result']
assert d['source_file_sha256']=='ef7e8b70532c6a6a7d87d44ffd7e0c7efd590e848bb36be01349b320238e3f08'
assert not d['go_for_long_training'] and d['held_corners_outer_improved']==4 and d['held_corners_total']==16
assert d['combined']['multiscale']<d['combined']['raw']<d['combined']['zero']
assert d['fov_safeguards']['30']['passed'] and d['fov_safeguards']['70']['passed']
assert all(d['axes'][a]['passed'] for a in ('left_proximal','left_middle','right_proximal','right_middle'))
assert not d['axes']['left_distal']['passed'] and not d['axes']['right_distal']['passed']
assert d['axes']['left_distal']['multiscale']>d['axes']['left_distal']['raw']
assert d['axes']['right_distal']['multiscale']>d['axes']['right_distal']['raw'] and d['axes']['right_distal']['multiscale']>d['axes']['right_distal']['zero']
g=d['derived']['valid_eye_groups'];assert g['0']['cases']==48 and g['2']['cases']==42 and g['1']['cases']==6
assert g['2']['multiscale_rmse']<g['2']['raw_rmse'] and g['0']['multiscale_rmse']<g['0']['raw_rmse']
assert len(d['cells'])==16 and sum(c['all_outer_improved'] for c in d['cells'])==4
print('Series 81 gate safeguards pass, distal axes fail, and no-go is consistent.')
