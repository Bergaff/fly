#!/usr/bin/env python3
"""Fast metric invariants for preregistered series 64."""
from __future__ import annotations
import importlib.util,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'experiments/templates/64_wing_context_invariant_replication.py'
spec=importlib.util.spec_from_file_location('rep64_fixture',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
truth=np.array([-.4,-.2,0,.2,.4]);control=np.array([-.3,-.1,.1,.1,.3]);invariant=np.array([-.35,-.15,.05,.15,.35])
c=mod.axis_metrics(truth,control);i=mod.axis_metrics(truth,invariant)
assert c['frames']==i['frames']==5
assert i['rmse_rad']<c['rmse_rad'] and i['sse_rad2']<c['sse_rad2']
assert c['opposite_sign_frames']==i['opposite_sign_frames']==0
assert math.isclose(c['rmse_rad'],math.sqrt(c['sse_rad2']/5),abs_tol=1e-15)
assert math.isclose(i['mean_error_rad'],float(np.mean(invariant-truth)),abs_tol=1e-15)
print('series 64 replication fixture passed')
