#!/usr/bin/env python3
"""Validate the compact extract and preregistered interpretation of series 79."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/frozen-view-stress-map-user-summary-extract.json').read_text(encoding='utf-8'))
assert d['status']=='completed' and d['protocol']['mode']=='full' and d['protocol']['no_retraining']
assert d['source_file_sha256']=='444637533940d410bbde05d37abf19b7292c68e66069c82ccd6e3bfc2e15411e'
p=d['primary'];assert not p['passed'] and p['core_cells_passed']==9 and p['core_cells_total']==32
assert len(p['axes'])==6
assert p['axes']['left_middle']['passed'] and p['axes']['right_middle']['passed']
assert all(not p['axes'][a]['passed'] for a in ('left_proximal','left_distal','right_proximal','right_distal'))
assert p['combined']['normal']<p['combined']['zero']<p['combined']['shuffled']<p['combined']['static']<p['combined']['closed']
der=d['derived'];assert der['core_combined_better_zero_cells']==26 and der['core_all_axes_better_zero_cells']==11 and der['core_normal_below_all_controls_cells']==31
assert der['axis_failed_core_cells']=={'left_proximal':19,'left_middle':4,'left_distal':12,'right_proximal':17,'right_middle':1,'right_distal':12}
assert len(d['cells'])==104 and sum(c['kind']=='core_corner' for c in d['cells'])==32 and sum(c['kind']=='evaluation_corner' for c in d['cells'])==32
assert sum(c['posthoc_inspired'] for c in d['cells'])==2
matched=next(c for c in d['cells'] if c['name']=='matched');assert matched['normal']<matched['zero'] and matched['all_axes_better_zero']
f20=next(c for c in d['cells'] if c['name']=='fov_deg_20');assert f20['normal']>f20['zero'] and f20['clipped_fraction']>.68
z28=next(c for c in d['cells'] if c['name']=='camera_z_0.28');assert z28['normal']>z28['zero']
probes=[c for c in d['cells'] if c['posthoc_inspired']];assert all(c['all_axes_better_zero'] for c in probes)
print('Series 79 aggregate success and preregistered six-axis core failure are consistent.')
