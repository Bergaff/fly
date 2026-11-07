"""Проверка снимков, выбора клеток, прерывания и объединения новых лезий."""
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main():
    import numpy as np
    root=Path(__file__).resolve().parents[1];tmp=Path(sys.argv[1]);templates=root/'experiments/templates'
    view=load('view',templates/'30_shiu_lesion_overview.py');study=load('study',templates/'31_shiu_selected_lesions.py')
    lesion=view.reference();base=lesion.load_top().base_module()
    # В числе кандидатов есть GRN и оба MN9; выборка не должна их содержать.
    candidates=list(dict.fromkeys(base.RIGHT[:2]+list(base.MN9.values())+[str(720575940000000000+i) for i in range(220)]))[:200]
    folder=tmp/'top';folder.mkdir();(folder/'checkpoint.json').write_text('checkpoint',encoding='utf8')
    with (folder/'top200.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['rank','root_id','mean_rate_hz','total_spikes_30_trials'])
        for i,c in enumerate(candidates): w.writerow([i+1,c,200-i,(200-i)*30])
    meta={'schema':1,'connection_sha256':view.CONNECTION_SHA,'neuron_sha256':view.NEURON_SHA,'top_script_sha256':view.TOP_SHA,'base_sha256':view.BASE_SHA,
          'lesion_script_sha256':view.LESION_SHA,'top_checkpoint_sha256':view.digest(folder/'checkpoint.json'),'top_csv_sha256':view.digest(folder/'top200.csv'),
          'python':sys.version.split()[0],'brian2':'2.9.0','numpy':np.__version__,'candidates':candidates,'frequencies_hz':view.FREQS,'seeds':view.SEEDS,'side':'right','duration_ms':1000,'dt_ms':.1}
    selected,pairs=study.selection(meta,base)
    assert len(selected)==10 and len(set(selected))==10 and len(pairs)==5
    assert not set(selected)&(set(base.RIGHT)|set(base.MN9.values()))
    ranks=[candidates.index(x)+1 for x in selected];assert ranks==sorted(ranks) and ranks[-1]==200
    source=tmp/'full';source.mkdir();db=lesion.open_db(source,meta,None)
    def insert(f,t,s,l,r):
        secs=1.0;db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(f,t,s,l,r,secs,lesion.row_hash(f,t,s,l,r,secs)))
    for s in range(30): insert(50,'',s,100+s%3,50+s%3)
    for s in range(5): insert(50,selected[0],s,90+s%3,45+s%3)
    insert(100,'',0,73,49);db.commit();db.close()
    source_hash=view.digest(source/'lesions.sqlite3')
    # Снимок активной базы содержит только завершённые транзакции.
    live=tmp/'live';live.mkdir();view.snapshot(source,live/'lesions.sqlite3')
    writer=sqlite3.connect(live/'lesions.sqlite3');writer.execute('BEGIN IMMEDIATE')
    writer.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(50,selected[0],5,95,50,1.0,lesion.row_hash(50,selected[0],5,95,50,1.0)))
    view.snapshot(live,tmp/'live-snapshot.sqlite3');assert len(view.read_checked(tmp/'live-snapshot.sqlite3')[1])==36
    writer.rollback();writer.close()
    out=tmp/'overview';r=view.analyze(source,out,folder,'lesions');assert r['result']['source_trials']==36
    with (out/'conditions.csv').open(encoding='utf-8-sig',newline='') as f: groups=list(csv.DictReader(f))
    partial=next(x for x in groups if x['target']==selected[0]);assert partial['trials']=='5' and partial['ratio_left']=='' and partial['left_le_80_percent']=='incomplete'
    assert (out/'activity_vs_lesion.csv').is_file() and view.digest(source/'lesions.sqlite3')==source_hash
    out=tmp/'individuality';r=view.analyze(source,out,folder,'individuality');assert r['result']['included_trials']==31
    with (out/'trials.csv').open(encoding='utf-8-sig',newline='') as f: assert all(x['target']=='control' for x in csv.DictReader(f))
    assert (out/'control_by_seed.png').is_file()
    # Нарушенный исходный список не принимается; настоящие файлы не меняются.
    original=(folder/'top200.csv').read_bytes();(folder/'top200.csv').write_bytes(original+b'bad')
    try: view.read_top(folder,meta);raise AssertionError('изменение топ-200 не замечено')
    except ValueError: pass
    (folder/'top200.csv').write_bytes(original)
    bad=tmp/'bad';bad.mkdir();view.snapshot(source,bad/'lesions.sqlite3')
    with sqlite3.connect(bad/'lesions.sqlite3') as db: db.execute('UPDATE trials SET left_count=left_count+1 WHERE seed=0')
    try: view.read_checked(bad/'lesions.sqlite3');raise AssertionError('подмена повтора не замечена')
    except ValueError: pass
    # Покрытие режима 31 без тяжёлой сети: значения заданы фикстурой, не научные данные.
    study.overview=lambda:view
    calls=[];interrupt=[False]
    def fake_trial(lesion,base,data,targets,seed):
        calls.append((tuple(targets),seed))
        if interrupt[0] and len(calls)>4: raise RuntimeError('synthetic interruption')
        n=len(targets);bonus=5 if n==2 else 0
        return (100+seed%3-10*n+bonus,50+seed%3-5*n,1.0)
    study.validate_simulation=lambda *_:(lesion,base,None)
    study.run_trial=fake_trial
    def run(name,stage,prior=None):
        out=tmp/name;out.mkdir();os.environ['FLY_RUN_DIR']=str(out)
        sys.argv=['study','--source',str(source),'--top-run',str(folder),'--stage',stage]+(['--resume-from',str(prior)] if prior else [])
        code=study.main();return out,code,json.loads((out/'summary.json').read_text(encoding='utf8'))
    plan,code,report=run('plan','plan');assert code==0 and report['status']=='plan_ready' and not calls
    assert report['result']['total_repeats']==510 and report['result']['original_reusable']==35
    interrupt[0]=True;part,code,report=run('interrupted','singles');assert code==1 and 'synthetic interruption' in report['error']
    with sqlite3.connect(part/'selected_lesions.sqlite3') as db: assert db.execute('SELECT count(*) FROM trials').fetchone()[0]==39
    partial_hash=view.digest(part/'selected_lesions.sqlite3');calls.clear();interrupt[0]=False
    single,code,report=run('single','singles',part);assert code==0 and report['result']['completed']==330 and len(calls)==291
    assert view.digest(part/'selected_lesions.sqlite3')==partial_hash
    single_hash=view.digest(single/'selected_lesions.sqlite3');calls.clear()
    complete,code,report=run('complete','all',single);assert code==0 and report['result']['completed']==510 and len(calls)==180
    assert view.digest(single/'selected_lesions.sqlite3')==single_hash and view.digest(source/'lesions.sqlite3')==source_hash
    with (complete/'pair_interactions.csv').open(encoding='utf-8-sig',newline='') as f:
        interactions=list(csv.DictReader(f));assert len(interactions)==5 and all(x['status']=='complete' and abs(float(x['interaction_hz'])-5)<1e-9 for x in interactions)
    assert (complete/'selected_activity.png').is_file() and (complete/'pair_interactions.png').is_file()
    calls.clear();review,code,report=run('review','review',complete);assert code==0 and report['result']['completed']==510 and not calls
    # Изменение сохранённого результата блокирует продолжение, не заменяя источник.
    corrupt=tmp/'corrupt';corrupt.mkdir();view.snapshot(source,corrupt/'lesions.sqlite3')
    with sqlite3.connect(complete/'selected_lesions.sqlite3') as src,sqlite3.connect(corrupt/'selected_lesions.sqlite3') as dst: src.backup(dst)
    with sqlite3.connect(corrupt/'selected_lesions.sqlite3') as db: db.execute('UPDATE trials SET left_count=left_count+1 WHERE condition="control" AND seed=0')
    _,code,report=run('bad-resume','review',corrupt);assert code==1 and 'Некорректный повтор' in report['error']
    # Групповая маска только обнуляет выходы заданных нейронов и не изменяет базовые веса.
    captured=[]
    class MockLesion:
        def trial(self,base,data,freq,seed,target): captured.append((data['weights'].copy(),target));return (1,2,3)
    data={'pre':np.array([0,1,1,2],dtype='int32'),'weights':np.array([7,-3,4,8],dtype='int32'),'lookup':{'a':1,'b':2}}
    study.run_trial=load('actual_study',templates/'31_shiu_selected_lesions.py').run_trial
    study.run_trial(MockLesion(),base,data,['a','b'],0)
    assert captured[0][0].tolist()==[7,0,0,0] and captured[0][1]=='' and data['weights'].tolist()==[7,-3,4,8]
    print('focused snapshot, planning, interruption, resume, pair interaction and group mask: ok')

if __name__=='__main__':main()
