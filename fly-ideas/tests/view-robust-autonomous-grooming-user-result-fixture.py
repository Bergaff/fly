#!/usr/bin/env python3
"""Validate the transcribed aggregate claims from the user series 78 summary."""
import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/view-robust-autonomous-grooming-user-summary-extract.json').read_text(encoding='utf-8'))
assert d['status']=='completed' and d['protocol_mode']=='long' and d['primary_passed']
assert d['active_training_seconds']>=28800 and d['accepted_candidates']==d['candidates']==44216
assert d['training_frames']==d['accepted_candidates']*49
assert len(d['axes'])==6
assert all(v['passed'] and v['normal']<v['zero'] and v['wins']>=7 for v in d['axes'].values())
def rms(xs):return math.sqrt(sum(x*x for x in xs)/len(xs))
p=d['combined_pooled_rmse']
assert math.isclose(rms([v['normal'] for v in d['axes'].values()]),p['normal'],abs_tol=1e-15)
assert math.isclose(rms([v['zero'] for v in d['axes'].values()]),p['zero'],abs_tol=1e-15)
assert p['matched']<p['normal']<p['shuffled']<p['zero']<p['static']<p['closed']
assert d['combined_wins_vs_zero']==9 and d['better_than_controls']==3
assert d['state_coefficients']==72 and d['delay_s']==.5 and d['state_unchanged_count']==10
c=d['contact_summary'];assert c['normal_better']==4 and c['equal']==6 and c['normal_worse']==0
assert c['mean_normal_f1']>c['mean_zero_f1']
a=d['audit'];assert not a['is_exhaustive'] and a['audited_count']==128<a['accepted_total']
assert a['overlap_under_0_001_deg']==a['overlap_under_1_deg']==0 and a['overlap_under_5_deg']==107
assert d['notable_tests']=={'normal_worse_than_zero':[146],'static_better_than_normal':[141]}
print('Series 78 six-axis transfer primary, controls, state and contact claims are consistent.')
