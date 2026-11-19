#!/usr/bin/env python3
"""Fast mathematical invariants for series 66 autonomous replay."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'experiments/templates/66_long_observe_delay_autonomous_replay.py'
spec=importlib.util.spec_from_file_location('auto66_fixture',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert (m.OBS_UNITS,m.OBS_BASIS,m.OUT_BASIS,m.XDIM,m.YDIM)==(24,10,12,240,72)
assert len(m.PRIOR_HOLDOUT_MOTIONS)==6
assert '59c3778e3055e6bb18d09736541dcb4fd0a9b27fef2f0c52c365886398fc779d' in m.PRIOR_HOLDOUT_MOTIONS
seed_coeff=np.zeros((6,12));seed_coeff[:,0]=np.linspace(-.2,.2,6);seed_coeff[:,1:4]=np.arange(18).reshape(6,3)/200
angles=m.basis(51,12)@seed_coeff.T
coeff=m.target_coeff(angles);replay=m.decode(coeff,len(angles))
assert coeff.shape==(72,) and replay.shape==angles.shape
np.testing.assert_allclose(replay,angles,rtol=0,atol=1e-12)
images=np.zeros((51,2,32,48,3),dtype=np.uint8);images[:,0,:,:,0]=np.arange(51)[:,None,None]
x,a=m.encode(images);x2,a2=m.encode(images.copy())
assert x.shape==(240,) and a.shape==(51,24);np.testing.assert_array_equal(x,x2);np.testing.assert_array_equal(a,a2)
state=coeff.copy();before=m.sha(np.asarray(state,dtype='<f8').tobytes());after=m.sha(np.asarray(state,dtype='<f8').tobytes());assert before==after
print('series 66 autonomous replay fixture passed')
