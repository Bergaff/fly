import csv
import hashlib
import importlib.util
import json
import os
import signal
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch
import numpy as np

root=Path(__file__).resolve().parents[1]
script=root/'experiments/templates/49_two_flies_long_imitation.py'
pilot=root/'experiments/templates/47_two_flies_imitation_learning.py'
spec=importlib.util.spec_from_file_location('long_test',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def run(*args,timeout=90):
    p=subprocess.run([sys.executable,str(script),*map(str,args)],cwd=root,capture_output=True,text=True,timeout=timeout)
    assert p.returncode==0,(p.stdout,p.stderr)
    return p

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def csvrows(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

# Sufficient statistics reproduce the direct fit, without storing frames or labels in the model.
rng=np.random.default_rng(9);x=rng.normal(size=(96,m.DIM));y=rng.normal(size=96)
st=m.empty_stats();m.add_stats(st,x[:48],y[:48]);m.add_stats(st,x[48:],y[48:]);mean,scale,intercept,w=m.fit_stats(st)
pilot_module=m.load('fixture_pilot','47_two_flies_imitation_learning.py',m.TRAIN_HASH)
mean2,scale2,intercept2,w2,_=pilot_module.fit(x,y)
assert np.allclose(mean,mean2) and np.allclose(scale,scale2) and abs(intercept-intercept2)<1e-12 and np.allclose(w,w2,atol=1e-11)
assert m.spec_for('train',1)==m.spec_for('train',1) and m.spec_for('train',1)!=m.spec_for('test',1)
assert m.spec_for('test',32)['shape']=='asymmetric'
with tempfile.TemporaryDirectory() as temp:
    temp=Path(temp)
    proc=subprocess.run([sys.executable,str(pilot),'--output',str(temp/'pilot')],cwd=root,capture_output=True,text=True,timeout=120)
    assert proc.returncode==0,(proc.stdout,proc.stderr)
    model=next((temp/'pilot').glob('*/model.npz'));orig=digest(model)
    # Test graceful pause by requesting it while the first batch is running.
    folder=temp/'pause-resume'
    child=subprocess.Popen([sys.executable,str(script),'--new',str(folder),'--model',str(model),'--test-count','16'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    dbpath=folder/'study.sqlite3';ready=False
    for _ in range(600):
        if child.poll() is not None:break
        if dbpath.is_file():
            try:
                with sqlite3.connect(dbpath,timeout=.2) as db:
                    if db.execute('SELECT stage FROM state').fetchone():ready=True;break
            except sqlite3.Error:pass
        time.sleep(.02)
    assert ready,'database did not become ready'
    (folder/'pause.request').write_text('test',encoding='utf8')
    stdout,stderr=child.communicate(timeout=120)
    assert child.returncode==0,(stdout,stderr)
    with sqlite3.connect(dbpath) as db:
        done,stage=db.execute('SELECT completed,stage FROM state').fetchone()
    assert 0<=done<16 and stage=='training',(done,stage,stdout)
    assert not list(folder.glob('result_*'))
    run('--resume',folder,timeout=120)
    with sqlite3.connect(dbpath) as db:
        done,stage=db.execute('SELECT completed,stage FROM state').fetchone()
        assert done==16 and stage=='completed'
        assert db.execute('SELECT COUNT(*) FROM sequences').fetchone()[0]==16
        assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    assert digest(model)==orig
    result=next(folder.glob('result_*'));assert not (result/'INCOMPLETE.txt').exists()
    assert digest(result/'model_old.npz')==orig
    meta=json.loads((result/'metadata.json').read_text(encoding='utf8'))
    assert meta['training_sequences']==16 and meta['test_sequences']==4 and meta['protocol']['mode']=='test_subset'
    assert meta['active_training_seconds']>0
    rows=csvrows(result/'predictions.csv');seq=csvrows(result/'sequence_metrics.csv')
    assert len(rows)==4*48 and len(seq)==4*4
    assert len(csvrows(result/'training_log.csv'))==16
    assert (result/'comparison.gif').stat().st_size>0
    for name,column in [('new','new_angle_rad'),('old','old_angle_rad'),('zero','zero_angle_rad'),('clip_floor','clip_floor_angle_rad')]:
        rmse=np.sqrt(np.mean([(float(r[column])-float(r['teacher_angle_rad']))**2 for r in rows]))
        assert abs(rmse-meta['scores'][name]['rmse_rad'])<1e-12
    assert sum(meta['sequences_new_vs_old'].values())==4
    with np.load(result/'test_visual_sequences.npz',allow_pickle=False) as data:
        assert data['images'].shape==(4,50,2,32,48,3)
    run('--resume',folder)
    assert len(list(folder.glob('result_*')))==1
    # Dосрочное завершение сохраняет уже полученную партию и выполняет проверку.
    early=temp/'early'
    child2=subprocess.Popen([sys.executable,str(script),'--new',str(early),'--model',str(model),'--test-count','16'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    ep=early/'study.sqlite3';ready=False
    for _ in range(600):
        if child2.poll() is not None:break
        if ep.is_file():
            try:
                with sqlite3.connect(ep,timeout=.2) as db:
                    if db.execute('SELECT stage FROM state').fetchone():ready=True;break
            except sqlite3.Error:pass
        time.sleep(.02)
    assert ready
    (early/'finish.request').write_text('test',encoding='utf8')
    sout,serr=child2.communicate(timeout=120);assert child2.returncode==0,(sout,serr)
    with sqlite3.connect(ep) as db:
        n,stage=db.execute('SELECT completed,stage FROM state').fetchone()
    assert 0<n<16 and stage=='completed',(n,stage,sout)
    assert json.loads((next(early.glob('result_*'))/'metadata.json').read_text(encoding='utf8'))['training_sequences']==n
    # Non-interactive transient result lock retries automatically, without retrying SQLite errors.
    with patch.object(m,'eval_model',side_effect=[PermissionError('locked'),PermissionError('locked'),Path('ok')]) as attempt, patch.object(m.time,'sleep'):
        assert m.evaluate_with_retry(temp,None,None,None,None,None,None,0,None)==Path('ok')
        assert attempt.call_count==3
    if os.name != 'nt':
        # A hard termination after a committed batch resumes from SQLite once, not from scratch.
        crash=temp/'crash'
        child3=subprocess.Popen([sys.executable,str(script),'--new',str(crash),'--model',str(model),'--test-count','16'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
        cp=crash/'study.sqlite3';saved=0
        for _ in range(600):
            if child3.poll() is not None:break
            if cp.is_file():
                try:
                    with sqlite3.connect(cp,timeout=.2) as db:saved=db.execute('SELECT completed FROM state').fetchone()[0]
                    if saved>=8:break
                except (sqlite3.Error,TypeError):pass
            time.sleep(.02)
        assert saved==8,('no intermediate checkpoint',saved)
        os.killpg(child3.pid,signal.SIGKILL);child3.communicate(timeout=30)
        with sqlite3.connect(cp) as db:before=db.execute('SELECT id,images_sha256 FROM sequences ORDER BY id').fetchall()
        assert len(before)==8
        run('--resume',crash,timeout=120)
        with sqlite3.connect(cp) as db:
            after=db.execute('SELECT id,images_sha256 FROM sequences ORDER BY id').fetchall()
            assert after[:8]==before and len(after)==16
            assert db.execute('SELECT stage FROM state').fetchone()[0]=='completed'
    # SQLite/stat checksum detects tampering on resume, without overwriting data.
    with sqlite3.connect(dbpath) as db:db.execute('UPDATE state SET stats_sha256=?',('0'*64,))
    failed=subprocess.run([sys.executable,str(script),'--resume',str(folder)],cwd=root,capture_output=True,text=True,timeout=30)
    assert failed.returncode!=0 and 'Контрольная сумма' in failed.stderr
    # Progress permission failures are warnings, not errors that corrupt committed work.
    with patch.object(m.os,'replace',side_effect=PermissionError('blocked')):
        m.progress(temp,1,1.0,'training',16)
    assert not (temp/'progress.json').exists()
print('long imitation fixture: OK')
