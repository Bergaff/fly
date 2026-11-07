"""Новый общий набор: топ-200, собственные контроли и выборочные лезии.

Старые пользовательские базы не ищутся и не меняются. Тяжёлые симуляции
только при явном --stage singles или --stage all. SQLite сохраняется после
каждого повтора, промежуточные резервные снимки не перезаписываются.
"""
import argparse
import contextlib
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time
import traceback
import uuid

SELECTED_SHA='a78976c5ba9002862aad4f34fcf8140501de7b880ccf1790886987ace6ba91c7'
MAGIC='fly-shiu-v630-shared-1'
TOP_DIR='01_top200'
CONTROL_DIR='02_controls_50Hz'
SELECTED_DIR='03_selected_lesions'
BACKUP_DIR='04_backups'
REPORT_DIR='05_reports'


def modules():
    path=Path(__file__).parent/'31_shiu_selected_lesions.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=SELECTED_SHA: raise ValueError('Проверочный скрипт выборочных лезий изменён.')
    spec=importlib.util.spec_from_file_location('selected_reference',path)
    study=importlib.util.module_from_spec(spec);spec.loader.exec_module(study)
    return study,study.overview()


def code_hash(): return hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def valid_folder(path):
    if path.is_symlink() or not path.is_dir(): raise ValueError(f'Нужна обычная папка, не ссылка: {path}')
    return path


def study_path(root,study_id):
    if not study_id or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in study_id) or len(study_id)>100:
        raise ValueError('Недопустимое имя общего набора.')
    root=valid_folder(Path(root))
    path=valid_folder(root/study_id)
    if path.resolve().parent!=root.resolve(): raise ValueError('Папка набора находится вне общего хранилища.')
    return path


@contextlib.contextmanager
def lock(study):
    path=study/'.study.lock'
    if path.is_symlink(): raise ValueError('Файл блокировки не должен быть ссылкой.')
    f=path.open('a+b')
    try:
        f.seek(0,os.SEEK_END)
        if f.tell()==0: f.write(b'0');f.flush()
        f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as e: raise ValueError('Этот общий набор уже используется в другом процессе. Дождитесь его завершения.') from e
        try: yield
        finally:
            f.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    finally: f.close()


def read_manifest(study):
    path=study/'manifest.json'
    if path.is_symlink() or not path.is_file(): raise ValueError('Манифест набора отсутствует или является ссылкой.')
    manifest=json.loads(path.read_text(encoding='utf8'))
    if manifest.get('kind')!=MAGIC or manifest.get('id')!=study.name or manifest.get('script_sha256')!=code_hash() or manifest.get('selected_sha256')!=SELECTED_SHA:
        raise ValueError('Версия общего набора или его кода не совпадает. Исходные данные не изменены.')
    for name in (TOP_DIR,CONTROL_DIR,SELECTED_DIR,BACKUP_DIR,REPORT_DIR): valid_folder(study/name)
    return manifest


def metadata(view,lesion,top,base,hashes,folder,data):
    import numpy as np
    import brian2 as b2
    candidates,active=lesion.validate_top(top,base,data,hashes,folder)
    meta={'schema':1,'connection_sha256':hashes['connections']['sha256'],'neuron_sha256':hashes['neurons']['sha256'],
          'top_script_sha256':view.TOP_SHA,'base_sha256':view.BASE_SHA,'lesion_script_sha256':view.LESION_SHA,
          'top_checkpoint_sha256':view.digest(folder/'checkpoint.json'),'top_csv_sha256':view.digest(folder/'top200.csv'),
          'python':sys.version.split()[0],'brian2':b2.__version__,'numpy':np.__version__,'candidates':candidates,
          'frequencies_hz':view.FREQS,'seeds':view.SEEDS,'side':'right','duration_ms':1000,'dt_ms':0.1}
    if meta['connection_sha256']!=view.CONNECTION_SHA or meta['neuron_sha256']!=view.NEURON_SHA: raise ValueError('Исходные файлы не совпадают с проверенной v630.')
    return meta,active


def validate_input_files(view,base,store_arrays):
    conn=base.input_file('FLY_SHIU_CONNECTIONS','.parquet');neurons=base.input_file('FLY_SHIU_NEURONS','.csv')
    hashes={'connections':base.fingerprint(conn),'neurons':base.fingerprint(neurons)}
    if any(hashes[k]['git_blob_sha1']!=v for k,v in base.EXPECTED.items()): raise ValueError('Выбраны не авторские файлы v630.')
    data=base.validate_inputs(conn,neurons,store_arrays)
    for key,p in [('connections',conn),('neurons',neurons)]:
        st=p.stat()
        if (st.st_size,st.st_mtime_ns)!=(hashes[key]['bytes'],hashes[key]['mtime_ns']): raise ValueError('Авторские данные изменились во время проверки.')
    return hashes,data


def create_study(root,top_source,view,selected_module):
    root=Path(root);root.mkdir(parents=True,exist_ok=True);valid_folder(root)
    lesion=view.reference();top=lesion.load_top();base=top.base_module()
    print('Проверяем авторские данные и копируем полный топ-200...',flush=True)
    hashes,data=validate_input_files(view,base,False)
    top_source=Path(top_source)
    if not top_source.is_dir(): raise ValueError('Выберите папку завершённого топ-200.')
    name='Study_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]
    study=root/name;study.mkdir()  # новая отдельная папка, существующие не перезаписываются
    for sub in (TOP_DIR,CONTROL_DIR,SELECTED_DIR,BACKUP_DIR,REPORT_DIR): (study/sub).mkdir()
    archive=study/TOP_DIR
    for filename in ['summary.json','checkpoint.json','top200.csv']+[f'counts_seed_{i:02d}.npy' for i in range(30)]:
        src=top_source/filename
        if not src.is_file(): raise ValueError('В папке топ-200 не найден файл: '+filename)
        with src.open('rb') as a,(archive/filename).open('xb') as b: shutil.copyfileobj(a,b,1024*1024)
    meta,active=metadata(view,lesion,top,base,hashes,archive,data)
    selected,pairs=selected_module.selection(meta,base)
    db=lesion.open_db(study/CONTROL_DIR,meta,None);db.close()
    manifest={'kind':MAGIC,'id':name,'label':'Лезии 50 Гц '+time.strftime('%Y-%m-%d %H:%M:%S')+' · '+name[-8:],
              'created_unix':time.time(),'script_sha256':code_hash(),'selected_sha256':SELECTED_SHA,
              'source_top_folder':str(top_source.resolve()),'source_protocol':meta,'active_neurons':active,
              'selected':selected,'pairs':pairs,'description':'Новый набор; прежние базы лезий не использованы.'}
    view.atomic_json(study/'manifest.json',manifest)
    return study,manifest


def selected_protocol(module,view,meta,selected,pairs):
    return {'schema':1,'source_protocol':meta,'selection_rule':'10 evenly spaced positions among top200 excluding stimulated RIGHT and both MN9; floor(i*(N-1)/9)',
            'selected':selected,'pairs':pairs,'conditions':module.conditions(selected,pairs),'frequency_hz':50,'seeds':view.SEEDS,
            'script_sha256':SELECTED_SHA,'overview_sha256':module.OVERVIEW_SHA}


def recover(path):
    if path.is_symlink() or not path.is_file(): raise ValueError('База общего набора отсутствует или является ссылкой: '+str(path))
    # После принудительной остановки SQLite может восстановить незавершённый журнал
    # только в управляемой нами базе, до проверки целостности и контрольных сумм.
    with sqlite3.connect(path,timeout=30) as db: db.execute('PRAGMA quick_check').fetchone()


def backup(db,study,label,completed):
    folder=valid_folder(study/BACKUP_DIR)
    path=folder/f'{label}_{completed:04d}_{time.strftime("%Y%m%d_%H%M%S")}_{uuid.uuid4().hex[:6]}.sqlite3'
    with path.open('xb'): pass
    try:
        with sqlite3.connect(path,timeout=30) as dest: db.backup(dest)
    except Exception:
        path.unlink(missing_ok=True);raise
    return path


def checked_controls(study,manifest,view):
    path=study/CONTROL_DIR/'lesions.sqlite3';recover(path)
    meta,rows=view.read_checked(path)
    if meta!=manifest['source_protocol'] or any(f!=50 or t!='' for f,t,*_ in rows): raise ValueError('Общая база контролей не соответствует этому набору.')
    return meta,rows


def open_existing_selected(module,study,protocol,out):
    folder=study/SELECTED_DIR;path=folder/'selected_lesions.sqlite3'
    if not path.exists(): return module.open_selected(folder,protocol,None)
    recover(path)
    # Проверяем в отдельной копии функцией прежнего протокола; исходную не заменяем.
    check=out/'verify_selected';check.mkdir()
    valid=module.open_selected(check,protocol,folder);valid.close()
    db=sqlite3.connect(path,timeout=30);db.execute('PRAGMA synchronous=FULL');return db


def write_selection(view,out,meta,selected,top):
    view.write_csv(out/'selection.csv',['selection','root_id','rank_200hz','activity_200hz'],
                   [{'selection':i+1,'root_id':x,'rank_200hz':top[x]['rank'],'activity_200hz':top[x]['rate']} for i,x in enumerate(selected)])


def progress(view,out,study,stage,done,total,last):
    value={'stage':stage,'completed':done,'total':total,'last':last}
    view.atomic_json(out/'progress.json',value)
    view.atomic_json(study/'progress.json',value)


def publish_report(study,stage,out,view,report):
    folder=valid_folder(study/REPORT_DIR)
    destination=folder/(stage+'_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
    destination.mkdir()  # каждый отчёт новый, старые версии не перезаписываются
    report['shared_report']=str(destination)
    view.atomic_json(out/'summary.json',report)
    for source in out.iterdir():
        if source.is_file() and not source.is_symlink() and source.suffix.lower() in ('.json','.csv','.png','.sqlite3'):
            with source.open('rb') as a,(destination/source.name).open('xb') as b: shutil.copyfileobj(a,b,1024*1024)


def perform(study,manifest,stage,out,module,view):
    with lock(study):
        meta,rows=checked_controls(study,manifest,view)
        top=view.read_top(study/TOP_DIR,meta)
        base=view.reference().load_top().base_module();selected,pairs=module.selection(meta,base)
        if selected!=manifest['selected'] or pairs!=manifest['pairs']: raise ValueError('План набора не совпадает с сохранённым.')
        protocol=selected_protocol(module,view,meta,selected,pairs);write_selection(view,out,meta,selected,top)
        report={'status':'pending','mode':stage,'study_id':study.name,'study_path':str(study),
                'source_protocol':meta,'selected':selected,'pairs':pairs,
                'caveats':['Новый набор начат с нуля; прежние базы лезий не использованы.',
                           'Десять клеток равномерно по рангу топ-200, кроме стимулируемых GRN и MN9; это не случайная выборка мозга.',
                           'Пары соседствуют по рангу выборки, не обязательно анатомически связаны; группа включает все десять клеток.',
                           'Лезии обнуляют исходящие веса, а не собственные спайки нейронов.',
                           'Одинаковый seed не доказывает одинаковых входных времён. Это модельные повторы, а не животные.',
                           'Одна частота не заменяет полную классификацию и не доказывает биологической компенсации.'],
                'files':['selection.csv']}
        if stage=='plan':
            report.update(status='plan_ready',result={'controls':30,'singles':300,'pairs_and_group':180,'total':510,'existing_controls':len(rows)})
            publish_report(study,stage,out,view,report);print('План готов, симуляции не запускались.',flush=True);return 0
        if stage=='individuality':
            # Анализ использует собственный согласованный снимок и не меняет общую базу.
            report=view.analyze(study/CONTROL_DIR,out,study/TOP_DIR,'individuality')
            report['study_id']=study.name;report['study_path']=str(study);publish_report(study,stage,out,view,report)
            print('Обзор контролей готов.',flush=True);return 0
        db=None
        try:
            if stage in ('singles','all'):
                print('Проверяем данные, полный топ-200 и версии для симуляций...',flush=True)
                lesion,base,data=module.validate_simulation(meta,study/TOP_DIR)
                control_db=sqlite3.connect(study/CONTROL_DIR/'lesions.sqlite3',timeout=30);control_db.execute('PRAGMA synchronous=FULL')
                try:
                    existing={r[2] for r in rows};done=len(existing)
                    for seed in view.SEEDS:
                        if seed in existing: continue
                        print(f'Контроль 50 Гц: {done+1}/30, seed {seed}',flush=True)
                        l,r,seconds=module.run_trial(lesion,base,data,[],seed)
                        control_db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(50,'',seed,l,r,seconds,lesion.row_hash(50,'',seed,l,r,seconds)));control_db.commit()
                        done+=1;progress(view,out,study,'controls',done,30,{'seed':seed})
                        if done%10==0: backup(control_db,study,'controls',done)
                    backup(control_db,study,'controls_final',done)
                finally: control_db.close()
                meta,rows=checked_controls(study,manifest,view)
            selected_file=study/SELECTED_DIR/'selected_lesions.sqlite3'
            if stage=='review' and not selected_file.is_file(): raise ValueError('Выборочная база ещё не создана. Сначала запустите 10 клеток.')
            if stage=='review':
                recover(selected_file)
                snapshot_folder=out/'review_snapshot';snapshot_folder.mkdir()
                db=module.open_selected(snapshot_folder,protocol,study/SELECTED_DIR)
            else:
                db=open_existing_selected(module,study,protocol,out)
            imported=module.import_original(db,rows,selected)
            if stage in ('singles','all'):
                wanted=protocol['conditions'][:11] if stage=='singles' else protocol['conditions']
                have={(k,s) for k,s in db.execute('SELECT condition,seed FROM trials')};done=sum((k,s) in have for k,_ in wanted for s in view.SEEDS);total=len(wanted)*30
                print(f'Выборочный этап: сохранено {done} из {total}.',flush=True)
                for key,targets in wanted:
                    for seed in view.SEEDS:
                        if (key,seed) in have: continue
                        print(f'{done+1}/{total}: {key}, seed {seed}',flush=True)
                        l,r,seconds=module.run_trial(lesion,base,data,targets,seed);origin='selected'
                        db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(key,seed,l,r,seconds,origin,module.hash_row(key,seed,l,r,seconds,origin)));db.commit()
                        have.add((key,seed));done+=1;progress(view,out,study,stage,done,total,{'condition':key,'seed':seed})
                        if done%10==0: backup(db,study,'selected',done)
                backup(db,study,'selected_final',done)
            result=module.export_results(view,out,db,protocol,top)
            # Отдельный снимок для просмотра в пространстве идеи, не исходная база.
            with sqlite3.connect(out/'selected_lesions.sqlite3') as snapshot_db: db.backup(snapshot_db)
            report.update(status='ok',result={**result,'imported_original':imported},files=report['files']+['selected_lesions.sqlite3','selected_trials.csv','selected_conditions.csv','pair_interactions.csv','selected_activity.csv']+result['images']+(['progress.json'] if (out/'progress.json').exists() else []))
            publish_report(study,stage,out,view,report);print('Готово: '+str(out/'summary.json'),flush=True);return 0
        finally:
            if db is not None: db.close()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--stage',choices=['init','plan','singles','all','review','individuality'],required=True);p.add_argument('--top-run',default='');p.add_argument('--study',default='');args=p.parse_args()
    out=Path(os.environ['FLY_RUN_DIR']);out.mkdir(parents=True,exist_ok=True);root=Path(os.environ['FLY_SHIU_SHARED_ROOT']);module,view=modules()
    try:
        if args.stage=='init':
            if not args.top_run or args.study: raise ValueError('Для нового набора выберите папку полного топ-200.')
            study,manifest=create_study(root,args.top_run,view,module)
            view.atomic_json(out/'summary.json',{'status':'ok','mode':'init','study_id':study.name,'study_path':str(study),'selected':manifest['selected'],'pairs':manifest['pairs'],
                                                 'files':[],'caveats':['Старые базы лезий не использованы. Симуляции не запускались.']})
            print('Создан новый общий набор: '+str(study),flush=True);return 0
        if args.top_run or not args.study: raise ValueError('Сначала выберите общий набор.')
        study=study_path(root,args.study);manifest=read_manifest(study)
        return perform(study,manifest,args.stage,out,module,view)
    except Exception as exc:
        view.atomic_json(out/'summary.json',{'status':'error','mode':args.stage,'error':f'{type(exc).__name__}: {exc}','files':['progress.json'] if (out/'progress.json').exists() else []})
        print(traceback.format_exc(),file=sys.stderr,flush=True);return 1

if __name__=='__main__':sys.exit(main())
