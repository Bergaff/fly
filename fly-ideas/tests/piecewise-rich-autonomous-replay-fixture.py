#!/usr/bin/env python3
"""Fast invariants for series 67 matched rich-observer replay."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'experiments/templates/67_piecewise_rich_observer_replay.py'
spec=importlib.util.spec_from_file_location('rich67_fixture',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert (m.SPATIAL_UNITS,m.OBS_BASIS,m.OUT_BASIS,m.XDIM,m.YDIM)==(96,10,12,1920,72)
a,d=m.piecewise_candidate(7);a2,d2=m.piecewise_candidate(7);assert a==a2;np.testing.assert_array_equal(d,d2)
assert d.shape==(51,6) and np.max(np.abs(np.asarray(a['keyframes_deg'])))<=45
assert len(m.PRIOR_HOLDOUT_MOTIONS)==11
images=np.zeros((51,2,32,48,3),dtype=np.uint8);images[:,0,:,:,0]=np.arange(51)[:,None,None]
x,activity,delta=m.encode(images);x2,activity2,delta2=m.encode(images.copy())
assert x.shape==(1920,) and activity.shape==delta.shape==(51,96);np.testing.assert_array_equal(x,x2);np.testing.assert_array_equal(activity,activity2);np.testing.assert_array_equal(delta,delta2);assert np.all(delta[0]==0)
coeff=m.target_coeff(d*np.pi/180);replay=m.replay_from_state(coeff,51);assert coeff.shape==(72,) and replay.shape==(51,6)
state=m.empty_adam();xs=np.stack([x,-x]);ys=np.stack([coeff,-coeff]);before=np.mean((np.column_stack([xs,np.ones(2)])@state['w']-ys)**2)
for _ in range(100):m.adam_update(state,xs,ys)
after=np.mean((np.column_stack([xs,np.ones(2)])@state['w']-ys)**2)
assert after<before and state['step']==100 and state['accepted']==200
blob=m.pack_state(state);restored=m.unpack_state(blob,m.sha(blob));np.testing.assert_array_equal(restored['w'],state['w'])
print('series 67 matched rich replay fixture passed')
