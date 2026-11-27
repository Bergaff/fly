#!/usr/bin/env python3
"""Fast invariants for series 69 encoder ablation."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'experiments/templates/69_matched_encoder_ablation.py';spec=importlib.util.spec_from_file_location('abl69',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);r=m.load67()
assert (m.COMPACT_UNITS,m.OBS_BASIS,m.CDIM,m.YDIM)==(24,10,240,72)
assert len(m.OLD_AND_REPLICATED)==10 and m.file_sha(m.RUNNER67)==m.RUNNER67_SHA
images=np.zeros((51,2,32,48,3),dtype=np.uint8);images[:,0,:,:,0]=np.arange(51)[:,None,None]
x,a=m.compact_encode(images,r);x2,a2=m.compact_encode(images.copy(),r);assert x.shape==(240,) and a.shape==(51,24);np.testing.assert_array_equal(x,x2);np.testing.assert_array_equal(a,a2)
_,degrees=r.piecewise_candidate(9);target=r.target_coeff(degrees*np.pi/180);state=m.empty_adam();xs=np.stack([x,-x]);ys=np.stack([target,-target]);before=np.mean((np.column_stack([xs,np.ones(2)])@state['w']-ys)**2)
for _ in range(100):m.update(state,xs,ys)
after=np.mean((np.column_stack([xs,np.ones(2)])@state['w']-ys)**2);assert after<before and state['step']==100 and state['seen']==200
blob=m.pack(state);restored=m.unpack(blob,m.sha(blob));np.testing.assert_array_equal(restored['w'],state['w'])
print('series 69 matched encoder ablation fixture passed')
