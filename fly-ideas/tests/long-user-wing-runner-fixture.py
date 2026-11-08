"""Short fixture mode tests; not a four-hour run or a Windows test."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
from unittest.mock import patch
import numpy as np

root=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
base=load('runner_base',root/'experiments/templates/51_two_flies_user_trajectory_learning.py')
runner=load('runner59',root/'experiments/templates/59_long_user_wing_learning.py')
ck=load('runner_checkpoint',root/'experiments/templates/54_user_wing_checkpoint.py')
script=root/'experiments/templates/59_long_user_wing_learning.py'
examples=root/'experiments/examples/wing-user-training'
train=[examples/'train-a.json',examples/'train-b.json'];oldtest=examples/'test-a.json'
before_originals={p:p.read_bytes() for p in train+[oldtest]}
env=dict(os.environ,OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')

def run(*args,ok=True):
    p=subprocess.run([sys.executable,str(script),*map(str,args)],cwd=root,env=env,capture_output=True,text=True,timeout=90)
    if ok and p.returncode!=0:raise AssertionError(p.stdout+'\n'+p.stderr)
    if not ok and p.returncode==0:raise AssertionError('invalid run accepted')
    return p

def state(folder):
    with sqlite3.connect(folder/'study.sqlite3') as db:
        proto=json.loads(db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()[0])
        rows=db.execute('SELECT id,status,frames,spec,motion_sha256,rgb_sha256 FROM candidates ORDER BY id').fetchall()
        phase=db.execute('SELECT stage,training_seconds FROM run_phase WHERE id=1').fetchone()
    return proto,ck.open_verified(folder/'study.sqlite3',proto),rows,phase

def raises(expected,fn):
    try:fn()
    except expected:return
    raise AssertionError('expected failure not raised')

class RAM:
    def __init__(self,value):self.value=value
    def available_ram(self):return self.value
with tempfile.TemporaryDirectory() as d:
    tmp=Path(d)
    with patch.object(runner.shutil,'disk_usage',return_value=type('D',(),{'free':runner.MIN_DISK})()):
        raises(MemoryError,lambda:runner.free_check(RAM(runner.MIN_RAM-1),tmp,False))
        raises(OSError,lambda:runner.free_check(RAM(None),tmp,False))
        runner.free_check(RAM(runner.MIN_RAM),tmp,False)
    with patch.object(runner.shutil,'disk_usage',return_value=type('D',(),{'free':runner.MIN_DISK-1})()):
        raises(OSError,lambda:runner.free_check(RAM(runner.MIN_RAM),tmp,False))
        runner.free_check(RAM(0),tmp,True)  # only bounded fixture mode bypasses limits
    baseline=base.run(train,[oldtest],tmp/'baseline')
    baseline_before={p.relative_to(baseline):p.read_bytes() for p in baseline.rglob('*') if p.is_file()}
    obj=json.loads(oldtest.read_text(encoding='utf-8'));obj['keyframes'][0]['angles_deg'][0]+=1
    fresh=tmp/'new_test.json';fresh.write_text(json.dumps(obj),encoding='utf-8');fresh_bytes=fresh.read_bytes()
    continuous=tmp/'continuous';resumed=tmp/'resumed'
    run('--new',continuous,'--previous',baseline,'--fresh',fresh,'--hours',4,'--fixture-limit',4)
    run('--new',resumed,'--previous',baseline,'--fresh',fresh,'--hours',4,'--fixture-limit',4,'--batches',1)
    proto,part,_,phase=state(resumed)
    assert phase[0]=='training' and part['next_id']==2 and part['sources']['test_002.json']==fresh_bytes
    fresh.write_text('{"broken":true}',encoding='utf-8')
    run('--resume',resumed)
    pa,a,ra,ph_a=state(continuous);pb,b,rb,ph_b=state(resumed)
    assert pa==pb and ra==rb and a['sources']==b['sources'] and ph_a[0]==ph_b[0]=='completed'
    assert a['stats']['n']==b['stats']['n']
    for key in ('sx','sx2','sy','sxy','sxx'):np.testing.assert_array_equal(a['stats'][key],b['stats'][key])
    summary=json.loads((resumed/'result/summary.json').read_text(encoding='utf-8'))
    assert summary['status']=='fixture_completed' and summary['protocol_mode']=='fixture'
    assert [x['role'] for x in summary['tests']]==['regression','new_test']
    assert summary['audit']['is_exhaustive'] and summary['audit']['accepted_total']==4
    with (baseline/'test_001/user_predictions.csv').open(encoding='utf-8-sig',newline='') as f:old=list(csv.DictReader(f))
    with (resumed/'result/test_001/predictions.csv').open(encoding='utf-8-sig',newline='') as f:paired=list(csv.DictReader(f))
    for axis in base.CHANNELS:
        np.testing.assert_allclose([float(row['old_'+axis+'_rad']) for row in paired],
                                   [float(row['predicted_'+axis+'_rad']) for row in old],atol=1e-12)
    playback_bytes=(resumed/'result/test_002/playback.json').read_bytes()
    playback=json.loads(playback_bytes)
    if os.environ.get('LONG_WING_FIXTURE_PLAYBACK'):
        Path(os.environ['LONG_WING_FIXTURE_PLAYBACK']).write_bytes(playback_bytes)
    assert playback['schema']=='fly-wings-result-v1' and len(playback['samples'])==51
    assert (resumed/'result/test_002/observer_vision.gif').exists()
    # Crash after publishing result but before final phase update: verify and finish without rewriting.
    before={p.relative_to(resumed/'result'):p.read_bytes() for p in (resumed/'result').rglob('*') if p.is_file()}
    with sqlite3.connect(resumed/'study.sqlite3') as db:db.execute("UPDATE run_phase SET stage='evaluation'")
    run('--resume',resumed)
    assert state(resumed)[3][0]=='completed'
    assert {p.relative_to(resumed/'result'):p.read_bytes() for p in (resumed/'result').rglob('*') if p.is_file()}==before
    # Corrupt output is detected and never overwritten.
    output=resumed/'result/ИТОГ.txt';original=output.read_bytes();output.write_bytes(original+b'bad')
    bad=run('--resume',resumed,ok=False);assert 'Контрольные суммы' in bad.stderr
    assert output.read_bytes()==original+b'bad';output.write_bytes(original)
    run('--resume',resumed)
    fresh.write_bytes(fresh_bytes)
    # Simulate a previously committed 4-hour counter to exercise the production
    # transition without waiting 4 hours. This is not a long-run measurement.
    simulated=tmp/'simulated-production-clock'
    run('--new',simulated,'--previous',baseline,'--fresh',fresh,'--hours',4,'--fixture-limit',4,'--batches',1)
    with sqlite3.connect(simulated/'study.sqlite3') as db:
        p=json.loads(db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()[0])
        p['mode']='long';p['fixture_limit']=None
        text=json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
        db.execute("UPDATE metadata SET value=? WHERE key='protocol'",(text,))
        db.execute("UPDATE metadata SET value=? WHERE key='protocol_sha256'",(runner.sha(text.encode('utf-8')),))
        db.execute('UPDATE state SET elapsed=? WHERE id=1',(14400.0,))
    with patch.object(runner,'free_check',lambda *args:None):
        runner.process(simulated)
    simulated_summary=json.loads((simulated/'result/summary.json').read_text(encoding='utf-8'))
    assert simulated_summary['status']=='completed' and simulated_summary['active_training_seconds']>=14400
    assert state(simulated)[3][0]=='completed' and state(simulated)[1]['next_id']==2
    paused=tmp/'paused'
    proc=subprocess.Popen([sys.executable,str(script),'--new',str(paused),'--previous',str(baseline),
                           '--fresh',str(fresh),'--fixture-limit','8'],cwd=root,env=env,
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        for line in proc.stdout:
            if 'Сохранено 2 кандидатов' in line:
                run('--pause',paused);break
        rest,_=proc.communicate(timeout=60)
        assert proc.returncode==0 and 'Пауза:' in rest,rest
    finally:
        if proc.poll() is None:proc.kill();proc.wait(timeout=30)
    assert 2<=state(paused)[1]['next_id']<8 and state(paused)[3][0]=='training'
    run('--pause',paused,ok=False)
    run('--resume',paused)
    assert state(paused)[1]['next_id']==8 and state(paused)[3][0]=='completed'
    if os.name=='posix':
        killed=tmp/'killed'
        proc=subprocess.Popen([sys.executable,str(script),'--new',str(killed),'--previous',str(baseline),
                               '--fresh',str(fresh),'--fixture-limit','4'],cwd=root,env=env,
                              stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
        try:
            for line in proc.stdout:
                if 'Сохранено 2 кандидатов' in line:os.killpg(proc.pid,signal.SIGKILL);break
            proc.wait(timeout=30);assert proc.returncode!=0
        finally:
            if proc.poll() is None:os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=30)
        run('--resume',killed)
        _,k,rk,pk=state(killed)
        assert rk==ra and pk[0]=='completed'
        for key in ('sx','sx2','sy','sxy','sxx'):np.testing.assert_array_equal(k['stats'][key],a['stats'][key])
    rejected=tmp/'reject'
    run('--new',rejected,'--previous',baseline,'--fresh',oldtest,'--fixture-limit',4,ok=False);assert not rejected.exists()
    run('--new',rejected,'--previous',baseline,'--fresh',fresh,'--fixture-limit',9,ok=False);assert not rejected.exists()
    assert {p.relative_to(baseline):p.read_bytes() for p in baseline.rglob('*') if p.is_file()}==baseline_before
assert all(p.read_bytes()==v for p,v in before_originals.items())
print('Bounded fixture: input freeze, resource guards, resume, pause, interruption and paired output passed.')
