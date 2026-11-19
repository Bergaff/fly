"""Short cross-process integration on artificial examples, not a user study."""
import csv
import importlib.util
import json
import os
import signal
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import numpy as np

root = Path(__file__).resolve().parents[1]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
base = load('fixture_base', root/'experiments/templates/51_two_flies_user_trajectory_learning.py')
ck = load('fixture_checkpoint', root/'experiments/templates/54_user_wing_checkpoint.py')
script = root/'experiments/templates/58_user_wing_integrated_prototype.py'
examples = root/'experiments/examples/wing-user-training'
train = [examples/'train-a.json', examples/'train-b.json']; oldtest = examples/'test-a.json'
before_originals = {p: p.read_bytes() for p in train+[oldtest]}
env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')

def run(*args, ok=True):
    result = subprocess.run([sys.executable, str(script), *map(str,args)], cwd=root, env=env,
                            capture_output=True, text=True, timeout=90)
    if ok and result.returncode != 0: raise AssertionError(result.stdout+'\n'+result.stderr)
    if not ok and result.returncode == 0: raise AssertionError('invalid run accepted')
    return result

def state(folder):
    with sqlite3.connect(folder/'integrated.sqlite3') as db:
        proto = json.loads(db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()[0])
        candidates = db.execute('SELECT id,status,frames,spec,motion_sha256,rgb_sha256 FROM candidates ORDER BY id').fetchall()
    return ck.open_verified(folder/'integrated.sqlite3', proto), candidates

with tempfile.TemporaryDirectory() as d:
    tmp=Path(d); baseline=base.run(train,[oldtest],tmp/'baseline')
    baseline_before={p.relative_to(baseline):p.read_bytes() for p in baseline.rglob('*') if p.is_file()}
    obj=json.loads(oldtest.read_text(encoding='utf-8')); obj['keyframes'][0]['angles_deg'][0] += 1
    fresh=tmp/'new_test.json'; fresh.write_text(json.dumps(obj),encoding='utf-8')
    original_fresh=fresh.read_bytes()
    continuous=tmp/'continuous'; resumed=tmp/'resumed'
    run('--new',continuous,'--previous',baseline,'--fresh',fresh,'--limit',4)
    first=run('--new',resumed,'--previous',baseline,'--fresh',fresh,'--limit',4,'--batches',1)
    assert 'ПРОТОТИП ОСТАНОВЛЕН' in first.stdout and not (resumed/'result').exists()
    part,_=state(resumed); assert part['next_id']==2 and part['sources']['test_002.json']==original_fresh
    # An evaluation error leaves only an incomplete attempt, never a published result.
    integrated=load('fixture_integrated',script)
    proto,ev,pre,stim,check,basemod,large=integrated.dependencies()
    with sqlite3.connect(resumed/'integrated.sqlite3') as db:
        saved=json.loads(db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()[0])
    def fail_compare(*args): raise RuntimeError('injected evaluation error')
    ev.compare_models=fail_compare
    try:
        integrated.evaluate(resumed,part,saved,proto,ev,stim,basemod)
        raise AssertionError('evaluation error not raised')
    except RuntimeError as exc:
        assert str(exc)=='injected evaluation error'
    assert not (resumed/'result').exists() and list(resumed.glob('evaluation_incomplete_*'))
    unchanged,_=state(resumed); assert unchanged['next_id']==part['next_id']
    if os.name == 'posix':
        killed=tmp/'killed'
        proc=subprocess.Popen([sys.executable,str(script),'--new',str(killed),'--previous',str(baseline),
                               '--fresh',str(fresh),'--limit','4'],cwd=root,env=env,stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,text=True,start_new_session=True)
        try:
            for line in proc.stdout:
                if 'сохранено 2/4' in line:
                    os.killpg(proc.pid,signal.SIGKILL)
                    break
            proc.wait(timeout=30)
            assert proc.returncode != 0
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait(timeout=30)
        run('--resume',killed)
        killed_state,killed_rows=state(killed)
        complete_state,complete_rows=state(continuous)
        assert killed_rows==complete_rows
        for k in ('sx','sx2','sy','sxy','sxx'):
            np.testing.assert_array_equal(killed_state['stats'][k],complete_state['stats'][k])
    # A separate process requests a real pause while the training process holds the lock.
    paused=tmp/'paused'
    proc=subprocess.Popen([sys.executable,str(script),'--new',str(paused),'--previous',str(baseline),
                           '--fresh',str(fresh),'--limit','8'],cwd=root,env=env,stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,text=True)
    try:
        for line in proc.stdout:
            if 'сохранено 2/8' in line:
                run('--pause',paused)
                break
        rest,_=proc.communicate(timeout=60)
        assert proc.returncode==0 and 'ПРОТОТИП НА ПАУЗЕ' in rest,rest
    finally:
        if proc.poll() is None:proc.kill();proc.wait(timeout=30)
    ps,_=state(paused)
    assert 2 <= ps['next_id'] < 8 and not (paused/'result').exists()
    assert not (paused/'pause.request').exists()
    run('--pause',paused,ok=False)  # paused is not actively running
    run('--resume',paused)
    assert state(paused)[0]['next_id']==8 and (paused/'result/summary.json').exists()
    # The original test is deliberately changed after freezing; continuation must not re-read it.
    fresh.write_text('{"damaged": true}',encoding='utf-8')
    run('--resume',resumed)
    a,ra=state(continuous);b,rb=state(resumed)
    assert ra==rb and a['next_id']==b['next_id']==4 and a['sources']==b['sources']
    for k in ('sx','sx2','sy','sxy','sxx'): np.testing.assert_array_equal(a['stats'][k],b['stats'][k])
    assert a['stats']['n']==b['stats']['n']
    sa=json.loads((continuous/'result/summary.json').read_text(encoding='utf-8'))
    sb=json.loads((resumed/'result/summary.json').read_text(encoding='utf-8'))
    assert sa['tests']==sb['tests'] and sa['audit']==sb['audit']
    assert [t['role'] for t in sa['tests']]==['regression','new_test']
    assert sa['audit']['is_exhaustive'] and sa['audit']['audited_count']==4
    with (baseline/'test_001/user_predictions.csv').open(encoding='utf-8-sig',newline='') as f: old=list(csv.DictReader(f))
    with (resumed/'result/test_001/predictions.csv').open(encoding='utf-8-sig',newline='') as f: paired=list(csv.DictReader(f))
    for axis in base.CHANNELS:
        np.testing.assert_allclose([float(row['old_'+axis+'_rad']) for row in paired],
                                   [float(row['predicted_'+axis+'_rad']) for row in old],atol=1e-12)
    with np.load(continuous/'result/model_new.npz',allow_pickle=False) as x, np.load(resumed/'result/model_new.npz',allow_pickle=False) as y:
        for key in x.files: np.testing.assert_array_equal(x[key],y[key])
    # Existing completed outputs are never overwritten when re-running the same folder.
    output_before={p.relative_to(resumed/'result'):p.read_bytes() for p in (resumed/'result').rglob('*') if p.is_file()}
    run('--resume',resumed)
    assert {p.relative_to(resumed/'result'):p.read_bytes() for p in (resumed/'result').rglob('*') if p.is_file()}==output_before
    # A full duplicate new test and an excessive limit are refused before creation.
    rejected=tmp/'reject'; run('--new',rejected,'--previous',baseline,'--fresh',oldtest,'--limit',4,ok=False)
    assert not rejected.exists()
    run('--new',rejected,'--previous',baseline,'--fresh',oldtest,'--limit',9,ok=False)
    assert not rejected.exists()
    run('--new',rejected,'--previous',baseline,'--fresh',oldtest,'--limit',4,'--batches',0,ok=False)
    assert not rejected.exists()
    assert {p.relative_to(baseline):p.read_bytes() for p in baseline.rglob('*') if p.is_file()}==baseline_before
assert all(p.read_bytes()==v for p,v in before_originals.items())
print('Integrated short study: baseline freeze, independent process restart, paired evaluation and source preservation verified.')
