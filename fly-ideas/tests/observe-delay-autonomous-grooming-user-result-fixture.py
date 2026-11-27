#!/usr/bin/env python3
"""Validate the transcribed scientific claims from the user series 77 summary."""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'experiments/reports/observe-delay-autonomous-grooming-user-summary-extract.json').read_text(encoding='utf-8'))
assert d['status']=='completed' and d['mode']=='full' and d['primary_passed']
assert d['holdouts']==list(range(121,131))
assert d['state_coefficients']==72 and d['state_unchanged_during_delay_count']==10
assert d['delay_s']==0.5
assert len(d['axes'])==6
assert all(v['passed'] and v['wins']==10 and v['normal']<v['zero'] for v in d['axes'].values())
pooled=d['combined_pooled_rmse']
assert pooled['normal']<pooled['shuffled']<pooled['zero']<pooled['static']<pooled['closed']
assert d['combined_wins_vs_zero']==10 and d['better_than_controls']==3
# Axis pooled values use all frames, so their equal-sized RMS reproduces combined pooled values.
def rms(xs): return math.sqrt(sum(x*x for x in xs)/len(xs))
assert math.isclose(rms([v['normal'] for v in d['axes'].values()]),pooled['normal'],abs_tol=1e-15)
assert math.isclose(rms([v['zero'] for v in d['axes'].values()]),pooled['zero'],abs_tol=1e-15)
c=d['contact_summary']
assert c['mean_normal_f1']>c['mean_zero_f1'] and c['normal_better_f1']==8
assert c['zero_better_test_ids']==[126,130]
assert set(d['forbidden_replay_access'])=={'observation RGB','teacher commands','saved framewise predictions'}
print('Series 77 primary, controls, immutable delay state and contact claims are consistent.')
