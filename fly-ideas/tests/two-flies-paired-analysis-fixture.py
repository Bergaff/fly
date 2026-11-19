import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import numpy as np

root=Path(__file__).resolve().parents[1]
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,root/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
study=load('study44','experiments/templates/44_two_flies_large_study.py')
analysis=load('analysis45','experiments/templates/45_two_flies_paired_analysis.py')

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory() as td:
    folder=Path(td)/'study';folder.mkdir()
    study.setup_db(folder,study.protocol(3,True))
    db=sqlite3.connect(folder/'study.sqlite3')
    for g in range(2):
        events={'wings':[(0,.010),(0,.020),(1,.030)],'reverse':([(0,.010),(0,.020),(0,.040),(1,.031)] if g==0 else [(0,.010),(1,.031)]),'tile_scramble':[(0,.010),(0,.020),(1,.030)]}
        outputs=[]
        for name in study.CONDITIONS:
            pairs=events.get(name,events['wings']); ids=np.array([i for i,t in pairs],dtype=int); times=np.array([t for i,t in pairs]); features=np.zeros((100,32),dtype=np.float32)
            raw=study.packed(times_s=times,neuron_id=ids,features=features)
            outputs.append((name,len(ids),0,np.bincount(ids,minlength=32).tolist(),[0.]*32,raw))
        study.write_group(db,(g,1.,0,3.,0.),0.,outputs)
    db.close(); before=digest(folder/'study.sqlite3')
    out=analysis.analyze(folder)
    assert digest(folder/'study.sqlite3')==before
    data=json.loads((out/'summary.json').read_text(encoding='utf8'))
    assert not data['expected_group_count_reached'] and data['groups_analyzed']==2
    r=data['controls']['reverse']; t=data['controls']['tile_scramble']
    assert r['count_difference_sum']==0 and r['groups_identical_times']==0 and r['different_neuron_pairs']==4
    assert t['groups_identical_times']==2 and t['groups_identical_counts']==2
    with (out/'groups.csv').open(encoding='utf-8-sig') as f:
        rows=list(csv.DictReader(f)); assert len(rows)==4
        a=next(x for x in rows if x['group_id']=='0' and x['control']=='reverse')
        assert int(a['unmatched_spike_events'])==3 and int(a['neurons_different_times'])==2
    with (out/'neuron_pairs.csv').open(encoding='utf-8-sig') as f:
        pairs=list(csv.DictReader(f)); assert len(pairs)==128
        cell=next(x for x in pairs if x['group_id']=='0' and x['control']=='reverse' and x['neuron_id']=='1')
        assert cell['count_diff_control_minus_wings']=='0' and cell['unmatched_spike_events']=='2'
    assert not (out/'INCOMPLETE.txt').exists()
    with study.RunLock(folder):
        p=subprocess.run([os.sys.executable,str(root/'experiments/templates/45_two_flies_paired_analysis.py'),'--folder',str(folder)],capture_output=True,text=True)
        assert p.returncode!=0 and 'Вторую копию' in p.stderr
    db=sqlite3.connect(folder/'study.sqlite3');db.execute("UPDATE trials SET sha256='bad' WHERE group_id=1 AND condition='reverse'");db.commit();db.close(); corrupt=digest(folder/'study.sqlite3')
    try:analysis.analyze(folder)
    except ValueError as e:assert 'контрольная сумма' in str(e)
    else:raise AssertionError('corrupt payload hash not caught')
    assert digest(folder/'study.sqlite3')==corrupt
    assert any((p/'INCOMPLETE.txt').exists() for p in folder.glob('paired_analysis_*'))
    # Real small study groups, not synthetic inputs.
    actual=Path(td)/'actual';actual.mkdir();study.setup_db(actual,study.protocol(2,True));db=sqlite3.connect(actual/'study.sqlite3');study.worker_init()
    for row in study.plan(2):
        r,err,outputs,_=study.calculate(row);study.write_group(db,r,err,outputs)
    db.close();before=digest(actual/'study.sqlite3');out=analysis.analyze(actual)
    assert digest(actual/'study.sqlite3')==before
    result=json.loads((out/'summary.json').read_text(encoding='utf8'))
    assert result['groups_analyzed']==2 and result['expected_group_count_reached']
    assert result['controls']['tile_scramble']['groups_identical_times']==2
    print('paired analyzer fixture OK')
