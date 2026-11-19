"""Transactional-checkpoint tests; no multi-hour run or Windows end-to-end."""
import hashlib
import concurrent.futures
import threading
import importlib.util
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
def load(name,p):
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('checkpoint54',root/'experiments/templates/54_user_wing_checkpoint.py')
old=load('wing51',root/'experiments/templates/51_two_flies_user_trajectory_learning.py')

def throws(fn, message):
    try:fn();raise AssertionError('operation unexpectedly succeeded')
    except ValueError as e:assert message in str(e),(message,str(e))

def add(stats,x,y):
    stats['n']+=len(y);stats['sx']+=x.sum(0);stats['sx2']+=(x*x).sum(0);stats['sy']+=y.sum(0);stats['sxy']+=x.T@y;stats['sxx']+=x.T@x

def record(ident,n):
    accepted=n>0
    return {'id':ident,'status':'accepted' if accepted else 'rejected','frames':n,'motion_sha256':hashlib.sha256(f'motion{ident}'.encode()).hexdigest(),
        'rgb_sha256':hashlib.sha256(f'rgb{ident}'.encode()).hexdigest() if accepted else None,'spec':{'id':ident,'value':ident/10}}

rng=np.random.default_rng(5);x=rng.normal(size=(34,m.DIM));y=rng.normal(size=(34,6))
with tempfile.TemporaryDirectory() as td:
    path=Path(td)/'путь'/'progress.sqlite3'
    missing=Path(td)/'missing.sqlite3'
    try:m.commit_batch(missing,{'source_sha256':{}},0,[record(0,0)],m.empty_stats(),0);raise AssertionError('missing database was created')
    except sqlite3.OperationalError:pass
    assert not missing.exists()
    sources={'model.npz':b'model','train_001.json':b'trajectory','test_001.json':b'holdout'}
    proto={'schema':'test-protocol','budget':14400,'source_sha256':{n:m.sha(v) for n,v in sources.items()}}
    m.create(path,proto,sources);original_files={n:bytes(v) for n,v in sources.items()}
    state=m.open_verified(path,proto);assert state['next_id']==0 and state['stats']['n']==0 and state['sources']==original_files
    try:m.create(path,proto,sources);raise AssertionError('overwrote database')
    except FileExistsError:pass
    assert m.open_verified(path,proto)['next_id']==0
    wrong=dict(proto,budget=28800);throws(lambda:m.open_verified(path,wrong),'Протокол')
    stats=m.empty_stats();add(stats,x[:15],y[:15]);m.commit_batch(path,proto,0,[record(0,15),record(1,0)],stats,3.2)
    recovered=m.open_verified(path,proto);assert recovered['next_id']==2 and recovered['elapsed']==3.2 and recovered['stats']['n']==15
    for key in m.SHAPES:np.testing.assert_array_equal(recovered['stats'][key],stats[key])
    throws(lambda:m.commit_batch(path,proto,0,[record(0,15)],stats,3.2),'устарела')
    throws(lambda:m.commit_batch(path,proto,2,[record(3,19)],stats,4),'последовательные')
    throws(lambda:m.commit_batch(path,proto,2,[record(2,19)],stats,4),'число кадров')
    assert m.open_verified(path,proto)['next_id']==2
    # Explicit rollback in SQLite on an insertion failure preserves both state and log.
    with sqlite3.connect(path) as db:db.execute("CREATE TRIGGER fail_candidate BEFORE INSERT ON candidates BEGIN SELECT RAISE(ABORT,'injected failure'); END")
    next_stats={k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in stats.items()};add(next_stats,x[15:],y[15:])
    try:m.commit_batch(path,proto,2,[record(2,19)],next_stats,5);raise AssertionError('failure ignored')
    except sqlite3.IntegrityError as e:assert 'injected failure' in str(e)
    assert m.open_verified(path,proto)['next_id']==2
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM candidates').fetchone()[0]==2;db.execute('DROP TRIGGER fail_candidate')
    m.commit_batch(path,proto,2,[record(2,19)],next_stats,5)
    resumed=m.open_verified(path,proto);assert resumed['next_id']==3 and resumed['stats']['n']==34
    direct=old.fit(resumed['stats']);pooled=old.empty_stats();old.update_stats(pooled,x,y);ref=old.fit(pooled)
    for a,b in zip(direct,ref):np.testing.assert_allclose(a,b,atol=1e-11)
    # Concurrent stale writers are serialized and exactly one may commit ID 3.
    after={k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in resumed['stats'].items()};add(after,x[:1],y[:1]);barrier=threading.Barrier(2)
    def race():
        barrier.wait(timeout=10)
        try:m.commit_batch(path,proto,3,[record(3,1)],after,6);return 'committed'
        except ValueError as e:assert 'устарела' in str(e);return 'stale'
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(lambda _:race(),range(2)))
    assert sorted(outcomes)==['committed','stale']; assert m.open_verified(path,proto)['next_id']==4
    # Terminate an uncommitted write: SQLite must expose the last committed state.
    if os.name!='nt':
        code='import sqlite3,sys,time; d=sqlite3.connect(sys.argv[1],isolation_level=None); d.execute("BEGIN IMMEDIATE"); d.execute("UPDATE state SET elapsed=999 WHERE id=1"); print("ready",flush=True); time.sleep(60)'
        child=subprocess.Popen([sys.executable,'-c',code,str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        assert child.stdout.readline().strip()=='ready';os.kill(child.pid,signal.SIGKILL);child.communicate(timeout=15)
        assert m.open_verified(path,proto)['elapsed']==6
    # Source and stats checksum mismatches are refused, with no attempted repair.
    with sqlite3.connect(path) as db:db.execute("UPDATE sources SET payload=? WHERE name='model.npz'",(b'changed',))
    throws(lambda:m.open_verified(path,proto),'SHA копии')
    # Altering both bytes and the DB digest still conflicts with the frozen protocol.
    with sqlite3.connect(path) as db:db.execute("UPDATE sources SET sha256=? WHERE name='model.npz'",(m.sha(b'changed'),))
    throws(lambda:m.open_verified(path,proto),'отличаются от протокола')
    with sqlite3.connect(path) as db:db.execute("UPDATE sources SET sha256=? WHERE name='model.npz'",(m.sha(sources['model.npz']),))
    with sqlite3.connect(path) as db:db.execute("UPDATE sources SET payload=? WHERE name='model.npz'",(sources['model.npz'],))
    with sqlite3.connect(path) as db:db.execute("UPDATE state SET stats_sha256=? WHERE id=1",('0'*64,))
    throws(lambda:m.open_verified(path,proto),'SHA статистик')
    assert sources==original_files
print('Checkpoint fixture passed: atomic batches, stale rejection, rollback, resume, corruption; not a long runner.')
