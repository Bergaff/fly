"""Short multiprocess integration tests, not a 4–8 hour study."""
import importlib.util
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1];script=root/'experiments/templates/55_user_wing_resume_prototype.py'
spec=importlib.util.spec_from_file_location('cp_fixture',root/'experiments/templates/54_user_wing_checkpoint.py');ck=importlib.util.module_from_spec(spec);spec.loader.exec_module(ck)
examples=root/'experiments/examples/wing-user-training'
train=[examples/'train-a.json',examples/'train-b.json'];test=[examples/'test-a.json']

def run(*args,ok=True,timeout=90):
    p=subprocess.run([sys.executable,str(script),*map(str,args)],cwd=root,capture_output=True,text=True,timeout=timeout)
    assert (p.returncode==0)==ok,(p.stdout,p.stderr)
    return p

def state(path):
    with sqlite3.connect(path/'prototype.sqlite3') as db:protocol=json.loads(db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()[0])
    return ck.open_verified(path/'prototype.sqlite3',protocol)

def log(path):
    with sqlite3.connect(path/'prototype.sqlite3') as db:return db.execute('SELECT id,status,frames,spec,motion_sha256,rgb_sha256 FROM candidates ORDER BY id').fetchall()

before={p:p.read_bytes() for p in train+test}
with tempfile.TemporaryDirectory() as td:
    temp=Path(td);paused=temp/'пауза';full=temp/'непрерывно'
    p=run('--new',paused,'--train',*train,'--test',*test,'--limit',6,'--batches',1)
    assert '"status": "prototype_paused"' in p.stdout and state(paused)['next_id']==2 and state(paused)['stats']['n']==98
    p=run('--resume',paused);assert '"status": "prototype_completed"' in p.stdout and state(paused)['next_id']==6
    p=run('--new',full,'--train',*train,'--test',*test,'--limit',6)
    assert '"status": "prototype_completed"' in p.stdout and state(full)['stats']['n']==294
    assert log(paused)==log(full)
    for k,v in state(paused)['stats'].items():np.testing.assert_array_equal(v,state(full)['stats'][k])
    again=run('--resume',paused);assert '"status": "prototype_completed"' in again.stdout and log(paused)==log(full)
    # Concurrent runs on the same folder are rejected by the OS lock.
    lockspec=importlib.util.spec_from_file_location('lock_module',root/'experiments/templates/44_two_flies_large_study.py');lock=importlib.util.module_from_spec(lockspec);lockspec.loader.exec_module(lock)
    with lock.RunLock(paused):
        second=run('--resume',paused,ok=False)
        assert 'уже запущен' in second.stderr
    assert log(paused)==log(full)
    # An independent test selection cannot affect training unless an exact candidate is rejected.
    another=temp/'different_test.json';obj=json.loads(test[0].read_text());obj['keyframes'][1]['angles_deg'][0]-=5;another.write_text(json.dumps(obj),encoding='utf8')
    changed=temp/'changed_test';run('--new',changed,'--train',*train,'--test',another,'--limit',6)
    assert log(full)==log(changed)
    for k,v in state(changed)['stats'].items():np.testing.assert_array_equal(v,state(full)['stats'][k])
    # Exact duplicate is refused before creating a run directory.
    dup=temp/'duplicate';run('--new',dup,'--train',*train,'--test',train[0],ok=False);assert not dup.exists()
    # Exact guard rejects attempts to use production-sized runs.
    too_long=temp/'not_long';run('--new',too_long,'--train',*train,'--test',*test,'--limit',9,ok=False);assert not too_long.exists()
    if os.name!='nt':
        # Kill the full parent process after a committed batch and restart in a new process.
        killed=temp/'killed';p=subprocess.Popen([sys.executable,str(script),'--new',str(killed),'--train',*map(str,train),'--test',*map(str,test),'--limit','6'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        found=False
        while True:
            line=p.stdout.readline()
            if not line:break
            if line.startswith('CHECKPOINT 2/6'):found=True;break
        assert found,'checkpoint not observed before process exited'
        os.killpg(p.pid,signal.SIGKILL);p.communicate(timeout=30)
        before_rows=log(killed);assert len(before_rows)>=2
        run('--resume',killed);assert log(killed)==log(full)
        for k,v in state(killed)['stats'].items():np.testing.assert_array_equal(v,state(full)['stats'][k])
    # Tampered protocol / checkpoint blocks resume.
    with sqlite3.connect(paused/'prototype.sqlite3') as db:db.execute("UPDATE state SET stats_sha256=?",('0'*64,))
    failure=run('--resume',paused,ok=False);assert 'SHA статистик' in failure.stderr
assert all(p.read_bytes()==data for p,data in before.items())
print('Short two-worker prototype: resume, kill, deterministic logs and holdout separation verified.')
