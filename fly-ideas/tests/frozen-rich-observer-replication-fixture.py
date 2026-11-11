#!/usr/bin/env python3
"""Fast static and arithmetic checks for series 68."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];path=ROOT/'experiments/templates/68_frozen_rich_observer_replication.py'
spec=importlib.util.spec_from_file_location('rep68_fixture',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.file_sha(m.RUNNER67)==m.RUNNER67_SHA
assert len(m.SERIES67_HOLDOUT_MOTIONS)==5
assert '577c5bd1a8df428718522ab24287b3aebd7db2a3228d33ffde59c7c373fe7e14' in m.SERIES67_HOLDOUT_MOTIONS
truth=np.array([[0.,1.,-1.,.5,-.5,.25],[1.,0.,-.5,.25,-.25,0.]])
score=m.metrics(truth,np.zeros_like(truth));assert score['frames']==2 and set(score['axis_rmse_rad'])==set(m.AXES)
assert np.isclose(score['rmse_rad'],np.sqrt(np.mean(truth**2)))
text=path.read_text(encoding='utf8');assert 'proto.worker_init([],set())' in text and 'm.predict(weights,x)' in text and 'm.replay_from_state(coeff,len(truth))' in text
assert 'adam_update' not in text
print('series 68 frozen replication fixture passed')
