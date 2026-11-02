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
    calls.clear();code,complete,report=run('all','all',['--study',study_id]);assert code==0 and report['result']['completed']==510 and len(calls)==180
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
