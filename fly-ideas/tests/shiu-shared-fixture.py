"""Общее хранилище, новый набор, безопасное продолжение и резервные копии."""
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main():
    root=Path(__file__).resolve().parents[1];templates=root/'experiments/templates';tmp=Path(sys.argv[1]);source=tmp/'external';source.mkdir()
    # Имеющаяся фикстура генерирует проверяемый полный топ-200 и маленькую сеть.
    fixture=root/'tests/shiu-lesions-fixture.py';prefix=fixture.read_text(encoding='utf8').split('# Маленький план для проверки транзакций')[0]
    saved_argv=sys.argv;sys.argv=['fixture',str(source)];scope={'__file__':str(fixture),'__name__':'fixture_prefix'}
    exec(compile(prefix,str(fixture),'exec'),scope);sys.argv=saved_argv
    base=scope['base'];top=scope['top'];lesion=scope['lesion'];folder=scope['folder'];hashes=scope['hashes'];data=scope['data']
    view=load('view',templates/'30_shiu_lesion_overview.py');module=load('module',templates/'31_shiu_selected_lesions.py');shared=load('shared',templates/'32_shiu_shared_study.py')
    view.reference=lambda:lesion;view.CONNECTION_SHA=hashes['connections']['sha256'];view.NEURON_SHA=hashes['neurons']['sha256']
    module.overview=lambda:view;shared.modules=lambda:(module,view)
    os.environ.update(FLY_SHIU_CONNECTIONS=str(scope['conn']),FLY_SHIU_NEURONS=str(scope['comp']),FLY_SHIU_SHARED_ROOT=str(tmp/'shared'))
    original={f.name:view.digest(f) for f in folder.iterdir() if f.is_file()}
    # Старые SQLite не анализируются и не меняются, даже если находятся рядом.
    old=tmp/'legacy.sqlite3';old.write_bytes(b'old user data');old_before=view.digest(old)
    def run(name,stage,params):
        out=tmp/name;out.mkdir();os.environ['FLY_RUN_DIR']=str(out);sys.argv=['shared','--stage',stage,*params]
        code=shared.main();return code,out,json.loads((out/'summary.json').read_text(encoding='utf8'))
    code,out,report=run('init','init',['--top-run',str(folder)])
    assert code==0 and report['status']=='ok' and report['mode']=='init'
    study=Path(report['study_path']);study_id=report['study_id'];manifest=shared.read_manifest(study)
    assert len(manifest['selected'])==10 and len(manifest['pairs'])==5
    assert view.digest(old)==old_before and all(view.digest(folder/n)==v for n,v in original.items())
    meta,rows=view.read_checked(study/shared.CONTROL_DIR/'lesions.sqlite3');assert rows==[]
    code,_,plan=run('plan','plan',['--study',study_id]);assert code==0 and plan['result']['total']==510 and plan['result']['existing_controls']==0
    assert not (study/shared.SELECTED_DIR/'selected_lesions.sqlite3').exists()
    # Один настоящий повтор Brian2 на маленькой сети, затем имитация прерывания.
    actual_trial=module.run_trial;actual_calls=[]
    def one_real(_l,_b,_d,targets,seed):
        actual_calls.append((tuple(targets),seed))
        if len(actual_calls)>1: raise RuntimeError('stop after real trial')
        return actual_trial(_l,_b,_d,targets,seed)
    module.run_trial=one_real
    code,_,error=run('real-once','singles',['--study',study_id]);assert code==1 and 'stop after real trial' in error['error']
    assert len(view.read_checked(study/shared.CONTROL_DIR/'lesions.sqlite3')[1])==1
    # Оставшиеся данные синтетические, чтобы не запускать 510 сетевых симуляций.
    calls=[];stop=[True]
    module.validate_simulation=lambda *_:(lesion,base,data)
    def fake(_l,_b,_d,targets,seed):
        calls.append((tuple(targets),seed))
        if stop[0] and len(calls)==35: raise RuntimeError('planned interruption')
        return (100+seed%3-10*len(targets)+(5 if len(targets)==2 else 0),50+seed%3-5*len(targets),1.0)
    module.run_trial=fake
    code,_,error=run('interrupt','singles',['--study',study_id]);assert code==1 and 'planned interruption' in error['error']
    _,control_rows=view.read_checked(study/shared.CONTROL_DIR/'lesions.sqlite3');assert len(control_rows)==30
    with sqlite3.connect(study/shared.SELECTED_DIR/'selected_lesions.sqlite3') as db: assert db.execute('SELECT COUNT(*) FROM trials').fetchone()[0]==35
    # Аварийная остановка во время незакоммиченной записи должна откатываться SQLite.
    import subprocess
    control_path=study/shared.CONTROL_DIR/'lesions.sqlite3'
    crash="import sqlite3,os,sys; c=sqlite3.connect(sys.argv[1]); c.execute('BEGIN IMMEDIATE'); c.execute('UPDATE trials SET left_count=999 WHERE seed=0'); os._exit(0)"
    subprocess.run([sys.executable,'-c',crash,str(control_path)],check=True)
    assert shared.checked_controls(study,manifest,view)[1]==control_rows
    assert len(list((study/shared.BACKUP_DIR).glob('controls*.sqlite3')))>=3
    stop[0]=False;calls.clear();code,_,report=run('resume','singles',['--study',study_id]);assert code==0 and report['result']['completed']==330 and len(calls)==295
    code,_,report=run('individuality','individuality',['--study',study_id]);assert code==0 and report['result']['included_trials']==30
    # Изолированный новый пилот: план не симулирует, прерывание и продолжение не трогают общий набор.
    import numpy as np
    pilot=load('individuality_pilot',templates/'33_shiu_individuality_pilot.py');pilot.check_memory=lambda:None
    control_path=study/shared.CONTROL_DIR/'lesions.sqlite3';selected_path=study/shared.SELECTED_DIR/'selected_lesions.sqlite3'
    protected=(view.digest(control_path),view.digest(selected_path));original_weights=data['weights'].copy()
    def pilot_run(name,stage):
        output=tmp/name;output.mkdir();pilot.execute(shared,view,module,study,manifest,output,stage);return output
    calls.clear();plan_out=pilot_run('pilot-plan','pilot-plan');assert not calls
    assert json.loads((plan_out/'summary.json').read_text(encoding='utf8'))['status']=='plan_ready'
    assert not (tmp/'shiu-v630-individuality').exists()
    first=pilot.weights_for_variant(original_weights,0);again=pilot.weights_for_variant(original_weights,0);second=pilot.weights_for_variant(original_weights,1)
    assert np.array_equal(first,again) and not np.array_equal(first,second)
    assert np.all(np.sign(first)==np.sign(original_weights)) and np.all((first/original_weights>=.95)&(first/original_weights<1.05))
    attempted=[]
    def interrupted(l,b,d,targets,seed):
        attempted.append((d['weights'].copy(),seed))
        if len(attempted)>1: raise RuntimeError('pilot interrupted')
        return actual_trial(l,b,d,targets,seed)
    module.run_trial=interrupted
    try: pilot_run('pilot-interrupt','pilot-run');raise AssertionError('interruption not raised')
    except RuntimeError as e: assert str(e)=='pilot interrupted'
    pilot_db=tmp/'shiu-v630-individuality'/study_id/'pilot.sqlite3'
    with sqlite3.connect(pilot_db) as db: assert db.execute('SELECT count(*) FROM trials').fetchone()[0]==1
    assert np.array_equal(attempted[0][0],attempted[1][0])
    stopped=tmp/'pilot-stop';stopped.mkdir();(stopped/'stop.request').write_text('stop',encoding='utf8')
    calls.clear();module.run_trial=fake;pilot.execute(shared,view,module,study,manifest,stopped,'pilot-run')
    assert not calls and json.loads((stopped/'summary.json').read_text(encoding='utf8'))['status']=='stopped'
    calls.clear();out_pilot=pilot_run('pilot-resume','pilot-run')
    info=json.loads((out_pilot/'summary.json').read_text(encoding='utf8'))
    assert info['status']=='complete' and info['completed']==30 and len(calls)==29 and 'report.txt' in info['files']
    with sqlite3.connect(out_pilot/'pilot_snapshot.sqlite3') as snap: assert snap.execute('SELECT count(*) FROM trials').fetchone()[0]==30
    assert np.array_equal(data['weights'],original_weights)
    assert (view.digest(control_path),view.digest(selected_path))==protected
    calls.clear();pilot_run('pilot-repeat','pilot-run');assert not calls
    calls.clear();pilot_run('pilot-review','pilot-review');assert not calls
    with sqlite3.connect(pilot_db) as db:
        saved=db.execute('SELECT value FROM metadata WHERE key="protocol"').fetchone()[0];meta_p=json.loads(saved)
    altered=dict(meta_p);altered['control_rows_sha256']='0'*64
    try: pilot.open_db(pilot_db.parent,altered,False);raise AssertionError('mismatched protocol accepted')
    except ValueError as e: assert 'Протокол' in str(e)
    assert (view.digest(control_path),view.digest(selected_path))==protected
    # Следующие семь seed используют те же веса и 30 старых результатов без изменения исходной базы.
    extension=load('individuality_extension',templates/'34_shiu_individuality_extension.py')
    assert extension.load_pilot().sha(templates/'33_shiu_individuality_pilot.py')==extension.PILOT_SHA
    original_pilot_hash=view.digest(pilot_db)
    def ext_run(name,stage):
        output=tmp/name;output.mkdir();extension.execute(pilot,shared,view,module,study,manifest,output,stage);return output
    calls.clear();out_plan=ext_run('ext-plan','extend-plan');assert not calls
    planned=json.loads((out_plan/'summary.json').read_text(encoding='utf8'))
    assert planned['previous_trials']==30 and planned['new_completed']==0 and planned['new_planned']==70
    assert not (pilot_db.parent/'extension_10seeds_v1').exists()
    bad_data=dict(data);bad_data['weights']=data['weights'].copy();bad_data['weights'][0]+=1
    module.validate_simulation=lambda *_:(lesion,base,bad_data)
    calls.clear();module.run_trial=fake
    try: ext_run('ext-bad-weights','extend-run');raise AssertionError('changed weights accepted')
    except ValueError as e: assert 'Веса варианта' in str(e)
    assert not calls
    module.validate_simulation=lambda *_:(lesion,base,data)
    ext_attempted=[]
    def interrupt_extension(l,b,d,targets,seed):
        ext_attempted.append((d['weights'].copy(),seed))
        if len(ext_attempted)>1: raise RuntimeError('extension interrupted')
        return actual_trial(l,b,d,targets,seed)
    module.run_trial=interrupt_extension
    try: ext_run('ext-interrupt','extend-run');raise AssertionError('interruption not raised')
    except RuntimeError as e: assert str(e)=='extension interrupted'
    ext_db=pilot_db.parent/'extension_10seeds_v1'/'extension.sqlite3'
    with sqlite3.connect(ext_db) as db: assert db.execute('SELECT count(*) FROM trials').fetchone()[0]==1
    assert ext_attempted[0][1]==3 and np.array_equal(ext_attempted[0][0],attempted[0][0])
    stopped=tmp/'ext-stop';stopped.mkdir();(stopped/'stop.request').write_text('stop',encoding='utf8')
    calls.clear();module.run_trial=fake;extension.execute(pilot,shared,view,module,study,manifest,stopped,'extend-run')
    assert not calls and json.loads((stopped/'summary.json').read_text(encoding='utf8'))['status']=='stopped'
    calls.clear();out_ext=ext_run('ext-resume','extend-run')
    ext_info=json.loads((out_ext/'summary.json').read_text(encoding='utf8'))
    assert ext_info['status']=='complete' and ext_info['new_completed']==70 and ext_info['total_trials']==100 and len(calls)==69
    with sqlite3.connect(out_ext/'extension_snapshot.sqlite3') as db: assert db.execute('SELECT count(*) FROM trials').fetchone()[0]==70
    import csv
    with (out_ext/'variants_10seed.csv').open(encoding='utf-8-sig',newline='') as f: variants=list(csv.DictReader(f))
    assert len(variants)==10 and all(v['trials']=='10' and v['complete']=='True' for v in variants)
    with (out_ext/'trials_10seed.csv').open(encoding='utf-8-sig',newline='') as f: trials=list(csv.DictReader(f))
    assert len(trials)==100 and sum(t['origin']=='pilot' for t in trials)==30
    assert view.digest(pilot_db)==original_pilot_hash and (view.digest(control_path),view.digest(selected_path))==protected
    calls.clear();ext_run('ext-repeat','extend-run');assert not calls
    calls.clear();ext_run('ext-review','extend-review');assert not calls
    # Новая серия фиксирует план на основе прежних 100 до запуска, без записи в старые базы.
    holdout=load('individuality_holdout',templates/'35_shiu_individuality_holdout.py')
    assert holdout.load_extension().PILOT_SHA==extension.PILOT_SHA
    assert holdout.average_ranks([3,1,1,4])==[3,1.5,1.5,4]
    assert abs(holdout.correlation([1,2,3],[3,2,1])+1)<1e-12
    assert holdout.correlation([1,1,1],[1,2,3]) is None
    def hold_run(name,stage):
        output=tmp/name;output.mkdir();holdout.execute(pilot,extension,shared,view,module,study,manifest,output,stage);return output
    with sqlite3.connect(ext_db) as db:
        missing=db.execute('SELECT * FROM trials WHERE variant=9 AND seed=9').fetchone()
        db.execute('DELETE FROM trials WHERE variant=9 AND seed=9');db.commit()
    try: hold_run('holdout-incomplete-prior','holdout-plan');raise AssertionError('incomplete previous extension accepted')
    except ValueError as e: assert '70' in str(e)
    with sqlite3.connect(ext_db) as db: db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?,?)',missing);db.commit()
    ext_before=view.digest(ext_db)
    calls.clear();out_hplan=hold_run('holdout-plan','holdout-plan');assert not calls
    hp=json.loads((out_hplan/'summary.json').read_text(encoding='utf8'))
    frozen=json.loads((out_hplan/'frozen_plan.json').read_text(encoding='utf8'))
    assert hp['previous_trials']==100 and hp['new_planned']==100 and hp['new_completed']==0 and hp['status']=='plan_ready'
    assert frozen['holdout_seeds']==list(range(10,20)) and not (pilot_db.parent/'holdout_10seeds_v1').exists()
    bad_data=dict(data);bad_data['weights']=data['weights'].copy();bad_data['weights'][0]+=1
    module.validate_simulation=lambda *_:(lesion,base,bad_data);calls.clear();module.run_trial=fake
    try: hold_run('holdout-bad-weights','holdout-run');raise AssertionError('changed weights accepted')
    except ValueError as e: assert 'Веса варианта' in str(e)
    assert not calls
    module.validate_simulation=lambda *_:(lesion,base,data)
    h_attempt=[]
    def interrupt_holdout(l,b,d,targets,seed):
        h_attempt.append(seed)
        if len(h_attempt)>1: raise RuntimeError('holdout interrupted')
        return actual_trial(l,b,d,targets,seed)
    module.run_trial=interrupt_holdout
    try: hold_run('holdout-interrupt','holdout-run');raise AssertionError('interruption not raised')
    except RuntimeError as e: assert str(e)=='holdout interrupted'
    hold_db=pilot_db.parent/'holdout_10seeds_v1'/'holdout.sqlite3'
    with sqlite3.connect(hold_db) as db:
        assert db.execute('SELECT count(*) FROM trials').fetchone()[0]==1
        assert json.loads(db.execute('SELECT value FROM metadata WHERE key="protocol"').fetchone()[0])==frozen
    stopped=tmp/'holdout-stop';stopped.mkdir();(stopped/'stop.request').write_text('stop',encoding='utf8')
    calls.clear();module.run_trial=fake;holdout.execute(pilot,extension,shared,view,module,study,manifest,stopped,'holdout-run')
    stopped_info=json.loads((stopped/'summary.json').read_text(encoding='utf8'))
    assert not calls and stopped_info['status']=='stopped' and stopped_info['new_completed']==1 and stopped_info['metrics']=={}
    calls.clear();out_h=hold_run('holdout-resume','holdout-run')
    hi=json.loads((out_h/'summary.json').read_text(encoding='utf8'))
    assert hi['status']=='complete' and hi['new_completed']==100 and len(calls)==99 and 'left_spearman' in hi['metrics']
    with sqlite3.connect(hold_db) as db:
        combinations=db.execute('SELECT variant,seed FROM trials').fetchall()
        assert set(combinations)=={(v,s) for v in range(10) for s in range(10,20)}
    with (out_h/'trials_holdout.csv').open(encoding='utf-8-sig',newline='') as f: assert len(list(csv.DictReader(f)))==100
    assert json.loads((out_h/'frozen_plan.json').read_text(encoding='utf8'))==frozen
    # Известный обратный порядок и нулевой разброс: точные метрики и обработка неопределённой корреляции.
    synthetic=tmp/'holdout-metrics';synthetic.mkdir()
    test_protocol=dict(frozen,discovery_left_means_hz=list(range(1,11)),discovery_left_average_ranks_low_first=list(range(1,11)),discovery_right_means_hz=[1]*10)
    synthetic_rows=[(v,seed,10-v,1,1.,1.,'hash','digest') for v in range(10) for seed in range(10,20)]
    holdout.report(pilot,view,synthetic,[],[None]*100,synthetic_rows,'complete',test_protocol)
    metrics=json.loads((synthetic/'summary.json').read_text(encoding='utf8'))['metrics']
    assert abs(metrics['left_spearman']+1)<1e-12 and abs(metrics['left_pearson']+1)<1e-12
    assert metrics['right_spearman'] is None and metrics['left_mean_difference_variant_10_minus_9']==-1
    assert view.digest(ext_db)==ext_before and view.digest(pilot_db)==original_pilot_hash and (view.digest(control_path),view.digest(selected_path))==protected
    calls.clear();hold_run('holdout-repeat','holdout-run');hold_run('holdout-review','holdout-review');assert not calls
    with sqlite3.connect(hold_db) as db: db.execute('UPDATE trials SET left_count=left_count+1 WHERE variant=0 AND seed=10');db.commit()
    try: hold_run('holdout-corrupt','holdout-review');raise AssertionError('corrupted holdout accepted')
    except ValueError as e: assert 'повреждённый' in str(e)
    assert view.digest(ext_db)==ext_before and view.digest(pilot_db)==original_pilot_hash
    # Повреждение строки запрещает обзор; исходный пилот не меняется.
    with sqlite3.connect(ext_db) as db: db.execute('UPDATE trials SET left_count=left_count+1 WHERE variant=0 AND seed=3');db.commit()
    try: ext_run('ext-corrupt','extend-review');raise AssertionError('corrupted row accepted')
    except ValueError as e: assert 'повреждённый' in str(e)
    try: hold_run('holdout-bad-prior','holdout-plan');raise AssertionError('corrupted previous extension accepted')
    except ValueError as e: assert 'повреждённый' in str(e)
    assert view.digest(pilot_db)==original_pilot_hash and (view.digest(control_path),view.digest(selected_path))==protected
    calls.clear();module.run_trial=fake;code,complete,report=run('all','all',['--study',study_id]);assert code==0 and report['result']['completed']==510 and len(calls)==180
    assert (complete/'selected_conditions.csv').is_file() and (complete/'pair_interactions.csv').is_file()
    assert (Path(report['shared_report'])/'selected_conditions.csv').is_file() and (Path(report['shared_report'])/'summary.json').is_file()
    selected_path=study/shared.SELECTED_DIR/'selected_lesions.sqlite3';before=view.digest(selected_path)
    code,review,report=run('review','review',['--study',study_id]);assert code==0 and view.digest(selected_path)==before
    assert (review/'selected_conditions.csv').is_file()
    backups=list((study/shared.BACKUP_DIR).glob('selected*.sqlite3'));assert len(backups)>=48
    with sqlite3.connect(backups[-1].resolve().as_uri()+'?mode=ro',uri=True) as db: assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    calls.clear();code,_,report=run('repeat','all',['--study',study_id]);assert code==0 and not calls and report['result']['completed']==510
    assert view.digest(old)==old_before and all(view.digest(folder/n)==v for n,v in original.items())
    # Межпроцессная блокировка не позволяет двум экземплярам менять общий набор.
    with shared.lock(study):
        try:
            with shared.lock(study): raise AssertionError('второй процесс получил блокировку')
        except ValueError as e: assert 'уже используется' in str(e)
    # Совпадающие имена не перезаписываются; создаётся второй независимый набор.
    code,_,second=run('second','init',['--top-run',str(folder)]);assert code==0 and second['study_id']!=study_id
    assert view.read_checked(Path(second['study_path'])/shared.CONTROL_DIR/'lesions.sqlite3')[1]==[]
    # Испорченная общая копия топ-200 останавливает новый запуск до симуляции.
    copied_top=study/shared.TOP_DIR/'top200.csv';saved=copied_top.read_bytes();copied_top.write_bytes(saved+b'corruption')
    calls.clear();code,_,report=run('corrupt','singles',['--study',study_id]);assert code==1 and not calls and 'не совпадает' in report['error'].lower()
    copied_top.write_bytes(saved);assert view.digest(selected_path)==before
    # Изменение идентификатора или кода не позволяет менять чужие файлы.
    try: shared.study_path(tmp/'shared','../escape');raise AssertionError('выход из папки разрешён')
    except ValueError: pass
    print('shared fresh study, coherent resume, immutable backups, isolation, lock: ok')

if __name__=='__main__':main()
