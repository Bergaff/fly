"""Pure checks for all 32 subsets, metrics and exact Shapley allocation."""
import importlib.util
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];path=root/'experiments/templates/62_long_wing_context_factorial.py'
spec=importlib.util.spec_from_file_location('factorial62',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
y=np.arange(51*6,dtype=float).reshape(51,6)%41-20;original=y.copy();items=mod.subsets(y)
assert len(items)==32 and [x['mask'] for x in items]==list(range(32))
assert items[0]['condition']=='baseline' and items[-1]['condition']=='only_right_x'
assert np.array_equal(y,original)
for item in items:
    assert np.array_equal(item['angles_deg'][:,3],original[:,3])
    expected=[mod.AXES[axis] for bit,axis in enumerate(mod.CONTEXT) if item['mask']&(1<<bit)]
    assert item['zeroed_axes']==expected
    for axis in range(6):
        want=np.zeros(51) if axis in mod.CONTEXT and mod.AXES[axis] in expected else original[:,axis]
        assert np.array_equal(item['angles_deg'][:,axis],want)
# Additive game recovers exact per-axis coefficients; a pure five-way interaction is shared equally.
coeff=[1.5,-2,3,.25,4]
values={mask:sum(coeff[b] for b in range(5) if mask&(1<<b)) for mask in range(32)}
phi=mod.shapley(values);np.testing.assert_allclose([x['value'] for x in phi],coeff,atol=1e-14)
interaction={mask:(10.0 if mask==31 else 0.0) for mask in range(32)}
np.testing.assert_allclose([x['value'] for x in mod.shapley(interaction)],[2]*5,atol=1e-14)
t=np.arange(2,51)/25;truth=np.linspace(-.4,.4,49);base=truth+.2;pred=truth+.1
allm=mod.metrics(t,truth,pred,base);seg=mod.metrics(t,truth,pred,base,1.44,1.60)
assert allm['frames']==49 and seg['frames']==5
assert abs(allm['rmse_rad']-.1)<1e-12 and abs(seg['sse_rad2']-.05)<1e-12
assert abs(seg['mean_delta_from_baseline_rad']+.1)<1e-12
print('factorial context fixture passed')
