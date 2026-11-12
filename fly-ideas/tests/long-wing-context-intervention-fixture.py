"""Pure deterministic checks for series 61; no rendering or user data."""
import importlib.util
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
path=root/'experiments/templates/61_long_wing_context_intervention.py'
spec=importlib.util.spec_from_file_location('context61',path)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

rng=np.random.default_rng(611)
y=rng.uniform(-40,40,(51,6));original=y.copy()
items=mod.conditions(y,10)
assert len(items)==12
assert [x[0] for x in items[:2]]==['baseline','only_right_x']
assert np.array_equal(y,original)
assert all(np.array_equal(changed[:,3],original[:,3]) for _,_,_,changed in items)
assert np.array_equal(items[1][3][:,3],original[:,3])
assert np.count_nonzero(items[1][3][:,[0,1,2,4,5]])==0
for name,axis,delta,changed in items[2:]:
    index=mod.AXES.index(axis)
    assert index!=3 and abs(delta)==10
    assert all(np.array_equal(changed[:,j],original[:,j]) for j in range(6) if j!=index)
    assert np.allclose(changed[:,index],np.clip(original[:,index]+delta,-60,60))

# Five frames at 1.44, 1.48, 1.52, 1.56 and 1.60 seconds.
t=np.arange(2,51)/25
truth=np.linspace(-.5,.5,len(t));base=truth+.2;pred=base+.1
m=mod.segment_metrics(t,truth,pred,base)
assert m['frames']==5
assert abs(m['rmse_rad']-.3)<1e-12
assert abs(m['mae_rad']-.3)<1e-12
assert abs(m['mean_delta_from_baseline_rad']-.1)<1e-12
assert abs(m['max_abs_delta_from_baseline_rad']-.1)<1e-12

for bad in (0,21,float('nan')):
    try:mod.conditions(y,bad)
    except ValueError:pass
    else:raise AssertionError('invalid delta accepted')
print('context intervention fixture passed')
