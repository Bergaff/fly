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
context=load('context61',root/'experiments/templates/61_long_wing_context_intervention.py')
factorial=load('factorial62',root/'experiments/templates/62_long_wing_context_factorial.py')
context_invariant=load('context_invariant63',root/'experiments/templates/63_long_wing_context_invariant_training.py')
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
    # Series 61 rerenders one-axis interventions and must not modify series 59.
    source_before={p.relative_to(resumed):p.read_bytes() for p in resumed.rglob('*') if p.is_file()}
    intervention=context.run(resumed,2,10,tmp/'context-output')
    intervention_summary=json.loads((intervention/'summary.json').read_text(encoding='utf-8'))
    assert intervention_summary['source_test_id']==2 and len(intervention_summary['conditions'])==12
    assert intervention_summary['conditions'][0]['condition']=='baseline'
    assert intervention_summary['conditions'][1]['condition']=='only_right_x'
    with (intervention/'predictions.csv').open(encoding='utf-8-sig',newline='') as f:intervention_rows=list(csv.DictReader(f))
    assert len(intervention_rows)==12*49
    assert {p.relative_to(resumed):p.read_bytes() for p in resumed.rglob('*') if p.is_file()}==source_before
    # Series 62 checks every zeroing subset and exact order-independent Shapley sums.
    factorial_out=factorial.run(resumed,2,tmp/'factorial-output')
    factorial_summary=json.loads((factorial_out/'summary.json').read_text(encoding='utf-8'))
    assert len(factorial_summary['conditions'])==32
    for model in ('old','new'):
        for scope in ('all_frames','segment'):
            attribution=factorial_summary['shapley'][model][scope]
            assert abs(sum(x['value'] for x in attribution['sse_reduction_shapley_rad2'])-attribution['total_sse_reduction_rad2'])<1e-10
            assert abs(sum(x['value'] for x in attribution['mean_prediction_shift_shapley_rad'])-attribution['total_mean_prediction_shift_rad'])<1e-10
    with (factorial_out/'predictions.csv').open(encoding='utf-8-sig',newline='') as f:factorial_rows=list(csv.DictReader(f))
    assert len(factorial_rows)==32*49
    assert {p.relative_to(resumed):p.read_bytes() for p in resumed.rglob('*') if p.is_file()}==source_before
    # Series 63 freezes a truly new holdout before predictions, replaces a fixed
    # training subset, and leaves the completed source series byte-identical.
    holdout_obj=json.loads(oldtest.read_text(encoding='utf-8'))
    holdout_obj['keyframes'][0]['angles_deg'][3]+=2
    holdout=tmp/'context-invariant-holdout.json';holdout.write_text(json.dumps(holdout_obj),encoding='utf-8')
    # The production output root is absent on the first Windows launch.
    ci_folder=tmp/'missing-context-invariant-root'/'context-invariant'
    ci_run=subprocess.run([sys.executable,str(root/'experiments/templates/63_long_wing_context_invariant_training.py'),
      '--new',str(ci_folder),'--source',str(resumed),'--holdout',str(holdout),'--fixture-limit','1'],
      cwd=root,env=env,capture_output=True,text=True,timeout=90)
    assert ci_run.returncode==0,ci_run.stdout+'\n'+ci_run.stderr
    ci_summary=json.loads((ci_folder/'result/summary.json').read_text(encoding='utf-8'))
    assert ci_summary['status']=='fixture_completed' and ci_summary['replacements_completed']==1
    assert ci_summary['protocol']['holdout_sha256']==context_invariant.file_sha(holdout)
    assert ci_summary['primary']['role']=='preregistered_holdout'
    assert ci_summary['primary']['right_x']['control']['frames']==49
    assert (ci_folder/'result/test_000/playback-control.json').exists()
    assert (ci_folder/'result/test_000/playback-context_invariant.json').exists()
    assert ci_summary['training_frames_each_model']==summary['training_frames']
    ci_repeat=subprocess.run([sys.executable,str(root/'experiments/templates/63_long_wing_context_invariant_training.py'),'--resume',str(ci_folder)],cwd=root,env=env,capture_output=True,text=True,timeout=30)
    assert ci_repeat.returncode==0 and 'уже завершена' in ci_repeat.stdout,ci_repeat.stdout+'\n'+ci_repeat.stderr
    assert {p.relative_to(resumed):p.read_bytes() for p in resumed.rglob('*') if p.is_file()}==source_before
    # Series 65 trains a soft consistency model without loading any new holdout.
    soft_folder=tmp/'missing-soft-root'/'soft-consistency'
    soft_run=subprocess.run([sys.executable,str(root/'experiments/templates/65_wing_soft_context_consistency.py'),'--new',str(soft_folder),'--source',str(ci_folder),'--fixture-limit','1'],cwd=root,env=env,capture_output=True,text=True,timeout=90)
    assert soft_run.returncode==0,soft_run.stdout+'\n'+soft_run.stderr
    soft_summary=json.loads((soft_folder/'result/summary.json').read_text(encoding='utf-8'))
    assert soft_summary['status']=='fixture_completed' and soft_summary['pairs_completed']==1
    assert soft_summary['primary_holdout_result'] is None
    assert soft_summary['diagnostics']['soft_mean_squared_pair_difference']<soft_summary['diagnostics']['control_mean_squared_pair_difference']
    with np.load(soft_folder/'result/model_control.npz',allow_pickle=False) as control_npz, np.load(soft_folder/'result/model_soft_consistency.npz',allow_pickle=False) as soft_npz:
        for axis in (0,1,2,4,5):np.testing.assert_array_equal(control_npz['weights'][:,axis],soft_npz['weights'][:,axis])
        assert not np.array_equal(control_npz['weights'][:,3],soft_npz['weights'][:,3])
    assert {p.relative_to(resumed):p.read_bytes() for p in resumed.rglob('*') if p.is_file()}==source_before
    # Series 64 freezes all five new files before the first prediction and only
    # evaluates the two already frozen series-63 models.
    replication_holdouts=[]
    for index in range(5):
        obj=json.loads(oldtest.read_text(encoding='utf-8'));obj['keyframes'][0]['angles_deg'][3]+=10+index
        path=tmp/f'replication-holdout-{index+1}.json';path.write_text(json.dumps(obj),encoding='utf-8');replication_holdouts.append(path)
    rep_root=tmp/'replication-output'
    rep_run=subprocess.run([sys.executable,str(root/'experiments/templates/64_wing_context_invariant_replication.py'),'--source',str(ci_folder),'--holdouts',*map(str,replication_holdouts),'--output-root',str(rep_root)],cwd=root,env=env,capture_output=True,text=True,timeout=90)
    assert rep_run.returncode==0,rep_run.stdout+'\n'+rep_run.stderr
    rep_folders=list(rep_root.glob('wing_context_replication_*'));assert len(rep_folders)==1
    rep_summary=json.loads((rep_folders[0]/'summary.json').read_text(encoding='utf-8'))
    assert rep_summary['status']=='completed' and rep_summary['aggregate']['holdouts']==5
    assert len(rep_summary['holdouts'])==5 and sum(x['frames'] for x in rep_summary['holdouts'])==245
    assert not (rep_folders[0]/'INCOMPLETE.txt').exists() and (rep_folders[0]/'complete.json').exists()
    assert {p.relative_to(resumed):p.read_bytes() for p in resumed.rglob('*') if p.is_file()}==source_before
    # Series 66 performs the full observation -> state -> delay -> autonomous
    # replay chain; fixture mode only limits training episodes, not holdouts.
    autonomous=tmp/'missing-autonomous-root'/'autonomous'
    auto_run=subprocess.run([sys.executable,str(root/'experiments/templates/66_long_observe_delay_autonomous_replay.py'),'--new',str(autonomous),'--source',str(resumed),'--holdouts',*map(str,replication_holdouts),'--fixture-limit','4'],cwd=root,env=env,capture_output=True,text=True,timeout=90)
    assert auto_run.returncode==0,auto_run.stdout+'\n'+auto_run.stderr
    auto_summary=json.loads((autonomous/'result/summary.json').read_text(encoding='utf-8'))
    assert auto_summary['status']=='fixture_completed' and auto_summary['training_episodes']==4
    assert len(auto_summary['holdouts'])==5 and auto_summary['protocol']['replay_access'].startswith('internal coefficient state')
    internal=json.loads((autonomous/'result/holdout_001/internal_state.json').read_text(encoding='utf-8'))
    assert internal['updates_during_delay']==0 and 'observation images' in internal['forbidden_replay_inputs']
    assert (autonomous/'result/holdout_001/observer_activity.csv').exists() and (autonomous/'result/holdout_001/playback.json').exists()
    assert {p.relative_to(resumed):p.read_bytes() for p in resumed.rglob('*') if p.is_file()}==source_before
    # Series 67 uses a fresh preregistered battery, matched independent random
    # piecewise training, level+delta features and resumable streaming Adam.
    rich_spec=importlib.util.spec_from_file_location('rich67',root/'experiments/templates/67_piecewise_rich_observer_replay.py');rich=importlib.util.module_from_spec(rich_spec);rich_spec.loader.exec_module(rich)
    rich_holdouts=[]
    for index in range(5):
        candidate,_=rich.piecewise_candidate(1000+index);obj={'schema':'fly-wings-trajectory-v1','fps':25,'duration_s':2,'keyframes':[{'t':i*.5,'angles_deg':angles} for i,angles in enumerate(candidate['keyframes_deg'])]};path=tmp/f'rich-holdout-{index+1}.json';path.write_text(json.dumps(obj),encoding='utf-8');rich_holdouts.append(path)
    rich_folder=tmp/'missing-rich-root'/'rich'
    rich_first=subprocess.run([sys.executable,str(root/'experiments/templates/67_piecewise_rich_observer_replay.py'),'--new',str(rich_folder),'--source',str(resumed),'--holdouts',*map(str,rich_holdouts),'--fixture-limit','4','--batches','1'],cwd=root,env=env,capture_output=True,text=True,timeout=120)
    assert rich_first.returncode==0,rich_first.stdout+'\n'+rich_first.stderr
    assert not (rich_folder/'result').exists()
    rich_resume=subprocess.run([sys.executable,str(root/'experiments/templates/67_piecewise_rich_observer_replay.py'),'--resume',str(rich_folder)],cwd=root,env=env,capture_output=True,text=True,timeout=120)
    assert rich_resume.returncode==0,rich_resume.stdout+'\n'+rich_resume.stderr
    rich_summary=json.loads((rich_folder/'result/summary.json').read_text(encoding='utf-8'))
    assert rich_summary['status']=='fixture_completed' and rich_summary['training_episodes']==4
    assert rich_summary['protocol']['observer']['feature_dimensions']==1920 and rich_summary['protocol']['replay_access'].startswith('internal coefficient state')
    assert set(rich_summary['aggregate']['normal_minus_control_rmse_rad'])=={'zero','static','shuffled','reversed','closed'}
    rich_internal=json.loads((rich_folder/'result/holdout_001/internal_state.json').read_text(encoding='utf-8'))
    assert rich_internal['updates_during_delay']==0 and 'observation images' in rich_internal['forbidden_replay_inputs']
    assert {p.relative_to(resumed):p.read_bytes() for p in resumed.rglob('*') if p.is_file()}==source_before
    # Series 68 freezes the series-67 model and evaluates five entirely new
    # matched movements without any optimizer or source mutation.
    frozen_before={p.relative_to(rich_folder):p.read_bytes() for p in rich_folder.rglob('*') if p.is_file()};rep68_holdouts=[]
    for index in range(5):
        candidate,_=rich.piecewise_candidate(2000+index);obj={'schema':'fly-wings-trajectory-v1','fps':25,'duration_s':2,'keyframes':[{'t':i*.5,'angles_deg':angles} for i,angles in enumerate(candidate['keyframes_deg'])]};path=tmp/f'rep68-holdout-{index+1}.json';path.write_text(json.dumps(obj),encoding='utf-8');rep68_holdouts.append(path)
    rep68_root=tmp/'rep68-output'
    rep68_run=subprocess.run([sys.executable,str(root/'experiments/templates/68_frozen_rich_observer_replication.py'),'--source',str(rich_folder),'--holdouts',*map(str,rep68_holdouts),'--output-root',str(rep68_root),'--allow-fixture-source'],cwd=root,env=env,capture_output=True,text=True,timeout=120)
    assert rep68_run.returncode==0,rep68_run.stdout+'\n'+rep68_run.stderr
    rep68_folders=list(rep68_root.glob('piecewise_rich_replication_*'));assert len(rep68_folders)==1
    rep68_summary=json.loads((rep68_folders[0]/'result/summary.json').read_text(encoding='utf-8'))
    assert rep68_summary['status']=='fixture_completed' and len(rep68_summary['holdouts'])==5
    assert rep68_summary['protocol']['source_model_sha256']==rich_summary['model_sha256']
    assert not (rep68_folders[0]/'INCOMPLETE.txt').exists() and (rep68_folders[0]/'result/complete.json').exists()
    assert {p.relative_to(rich_folder):p.read_bytes() for p in rich_folder.rglob('*') if p.is_file()}==frozen_before
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
