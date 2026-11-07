"""Real-process pause, checkpoint/resume, export, integrity and numerical controls."""
import csv
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];SCRIPT=ROOT/'experiments/templates/44_two_flies_large_study.py'
env={**os.environ,'MUJOCO_GL':'disable','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
def call(*args):
    p=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=90)
    if p.returncode:raise AssertionError(p.stdout+'\n'+p.stderr)
    return p
def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'long-run'
    proc=subprocess.Popen([sys.executable,str(SCRIPT),'--new',str(path),'--test-count','8'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    deadline=time.monotonic()+40
    while time.monotonic()<deadline and not (path/'progress.json').exists() and proc.poll() is None:time.sleep(.1)
    assert (path/'progress.json').exists(),proc.communicate(timeout=10)
    lock_try=subprocess.run([sys.executable,str(SCRIPT),'--resume',str(path)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=20)
    assert lock_try.returncode!=0 and ('запущен' in lock_try.stderr or 'групп' in lock_try.stderr),lock_try.stderr
    call('--stop','--folder',path)
    out,err=proc.communicate(timeout=60)
    assert proc.returncode==0,out+'\n'+err
    progress=json.loads((path/'progress.json').read_text());assert progress['state']=='paused',progress
    assert 0<=progress['completed_groups']<8 and (path/'stop.request').exists()
    with sqlite3.connect(path/'study.sqlite3') as db:
        before=dict(db.execute('SELECT group_id||condition,sha256 FROM trials'))
    call('--resume',path)
    progress=json.loads((path/'progress.json').read_text());assert progress['state']=='completed' and progress['completed_groups']==8
    assert not (path/'stop.request').exists()
    with sqlite3.connect(path/'study.sqlite3') as db:
        meta=json.loads(db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()[0]);assert meta['test_subset'] and meta['total_groups']==8 and meta['full_grid_groups']==12168
        assert db.execute('SELECT COUNT(*) FROM trials').fetchone()[0]==48
        assert db.execute('SELECT COUNT(*) FROM neurons').fetchone()[0]==8*6*32
        after=dict(db.execute('SELECT group_id||condition,sha256 FROM trials'))
        assert all(after[k]==v for k,v in before.items())
        group=db.execute('SELECT id FROM groups ORDER BY id LIMIT 1').fetchone()[0]
        blobs={name:(data,digest) for name,data,digest in db.execute('SELECT condition,payload,sha256 FROM trials WHERE group_id=?',(group,))}
        for blob,digest in blobs.values():assert hashlib.sha256(blob).hexdigest()==digest
    summary=rows(path/'conditions_summary.csv');assert len(summary)==6 and all(int(x['completed_groups'])==8 for x in summary)
    assert len(rows(path/'neuron_comparison.csv'))==6*32 and len(rows(path/'trials_summary.csv'))==48
    call('--export','--folder',path,'--group',group)
    exported=list(path.glob('group_*'));assert len(exported)==1
    with Image.open(exported[0]/'scene_wings.gif') as im:
        assert sum((im.seek(k) or im.info.get('duration',0)) for k in range(im.n_frames))==2000
    with np.load(exported[0]/'wings/data.npz') as a,np.load(exported[0]/'tile_scramble/data.npz') as b,np.load(exported[0]/'reverse/data.npz') as rev:
        assert np.max(np.abs(a['features']-b['features']))<=1e-6
        assert np.array_equal(a['frames'][::-1],rev['frames'])
        assert len(a['times_s'])==len(a['neuron_id']) and a['features'].shape==(100,32)
    for sub in exported[0].iterdir():
        if sub.is_dir():
            assert len(rows(sub/'visual_input.csv'))==3200
            with Image.open(sub/'observer_input.gif') as im:
                duration=0
                for k in range(im.n_frames):im.seek(k);duration+=im.info.get('duration',0)
                assert duration==2000
    # Reopening a completed checkpoint neither duplicates nor mutates trials.
    call('--resume',path)
    with sqlite3.connect(path/'study.sqlite3') as db:
        assert dict(db.execute('SELECT group_id||condition,sha256 FROM trials'))==after
        row=db.execute('SELECT group_id,condition,payload FROM trials LIMIT 1').fetchone()
        db.execute('UPDATE trials SET payload=? WHERE group_id=? AND condition=?',(row[2]+b'x',row[0],row[1]));db.commit()
    failed=subprocess.run([sys.executable,str(SCRIPT),'--resume',str(path)],cwd=ROOT,env=env,text=True,capture_output=True,timeout=30)
    assert failed.returncode!=0 and 'Повреждён' in failed.stderr,failed.stderr
print('Large two-flies study fixture passed')
