#!/usr/bin/env python3
"""Fast invariants for series 63; full bounded E2E is in the runner fixture."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'experiments/templates/63_long_wing_context_invariant_training.py'
spec=importlib.util.spec_from_file_location('context_invariant_fixture',SCRIPT)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

recipient=np.array([
 [1,2,3,4,5,6],
 [2,3,4,5,6,7],
 [3,4,5,6,7,8],
 [4,5,6,7,8,9],
 [5,6,7,8,9,10],
],dtype=float)
donor=np.array([
 [-10,-20,-30,-40,-50,-60],
 [-20,-30,-40,-50,-60,-10],
 [-30,-40,-50,-60,-10,-20],
],dtype=float)
changed=module.donor_context(recipient,donor)
np.testing.assert_array_equal(changed[:,module.TARGET],recipient[:,module.TARGET])
for axis in module.CONTEXT:assert not np.array_equal(changed[:,axis],recipient[:,axis])
assert np.isfinite(changed).all() and changed.shape==recipient.shape

truth=np.deg2rad(np.array([0,5,10,24,25,60],dtype=float))
pred=truth+np.deg2rad(np.array([1,-1,2,-2,3,-3],dtype=float))
metrics=module.axis_metrics(truth,pred)
assert metrics['frames']==6 and metrics['opposite_sign_frames']==0
bins=module.binned_metrics(truth,pred)
assert [x['metrics']['frames'] if x['metrics'] else 0 for x in bins]==[2,2,2]

# Replacement updates preserve the exact target sample count.
class Base:
 @staticmethod
 def empty_stats():return {'n':0,'sx':np.zeros(2),'sx2':np.zeros(2),'sy':np.zeros(6),'sxy':np.zeros((2,6)),'sxx':np.zeros((2,2))}
 @staticmethod
 def update_stats(stats,x,y):
  stats['n']+=len(y);stats['sx']+=x.sum(0);stats['sx2']+=(x*x).sum(0);stats['sy']+=y.sum(0);stats['sxy']+=x.T@y;stats['sxx']+=x.T@x
x0=np.array([[1.,2.],[3.,4.]]);x1=np.array([[2.,1.],[4.,3.]])
y0=np.ones((2,6));y1=np.ones((2,6))*2
stats=Base.empty_stats();Base.update_stats(stats,x0,y0);before=stats['n']
module.apply_replace(stats,Base,x0,y0,x1,y1)
assert stats['n']==before
np.testing.assert_allclose(stats['sx'],x1.sum(0))
np.testing.assert_allclose(stats['sy'],y1.sum(0))
print('context-invariant fixture passed')
