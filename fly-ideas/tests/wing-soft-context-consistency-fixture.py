#!/usr/bin/env python3
"""Fast checkpoint and objective invariants for series 65."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'experiments/templates/65_wing_soft_context_consistency.py'
spec=importlib.util.spec_from_file_location('soft65_fixture',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.LAMBDA==0.1 and m.TARGET==3 and m.DIM==576
dxx=np.zeros((m.DIM,m.DIM));dxx[0,0]=3.5;dxx[0,1]=dxx[1,0]=.25;dxx[1,1]=2
blob=m.pack_delta(49,dxx);frames,restored=m.unpack_delta(blob,m.sha(blob))
assert frames==49;np.testing.assert_array_equal(restored,dxx)
# A positive-semidefinite consistency term reduces sensitivity in a simple
# two-feature analogue of the fixed linear solve.
cov=np.array([[2.,.2],[.2,1.5]]);delta=np.array([[1.,.1],[.1,.5]]);rhs=np.array([1.,-.5])
control=np.linalg.solve(cov+np.eye(2),rhs);soft=np.linalg.solve(cov+np.eye(2)+m.LAMBDA*delta,rhs)
assert soft@delta@soft < control@delta@control
print('series 65 soft-consistency fixture passed')
