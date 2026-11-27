"""Продолжение пилота v630: 10 прежних вариантов × seed 3–9.

70 новых повторов в отдельной базе; исходный пилот и контроли не меняются.
"""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sqlite3
import statistics
import sys
import time
import traceback

PILOT_SHA='857c8428d7daee57304cffe35daa6330c0a18a70c6ca631df9b569c8f0731fc0'
NEW_SEEDS=list(range(3,10))
ALL_SEEDS=list(range(10))
MODE='shiu-individuality-10seed-v1'


def load_pilot():
    path=Path(__file__).parent/'33_shiu_individuality_pilot.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=PILOT_SHA:
        raise ValueError('Код исходного пилота изменён. Продолжение остановлено.')
    spec=importlib.util.spec_from_file_location('individuality_pilot_original',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def original_snapshot(pilot,shared,view,base_dir,old_protocol,out):
    source=base_dir/'pilot.sqlite3'
    if source.is_symlink() or not source.is_file(): raise ValueError('Исходная база пилота не найдена или является ссылкой.')
    # The copied SQLite file is validated; the original is never opened for writing.
    with shared.lock(base_dir): view.snapshot(source,out/'pilot.sqlite3')
    db=pilot.open_db(out,old_protocol,False)
    try:
        rows=db.execute('SELECT variant,seed,left_count,right_count,sim_seconds,total_seconds,weight_sha256,digest FROM trials ORDER BY variant,seed').fetchall()
    finally: db.close()
    expected={(v,s) for v in pilot.VARIANTS for s in pilot.SEEDS}
    if len(rows)!=30 or {(r[0],r[1]) for r in rows}!=expected:
        raise ValueError('Для продолжения нужны все 30 проверенных повторов исходного пилота.')
    return rows


def make_protocol(pilot,old_protocol,old_rows):
    return {'kind':MODE,'study_id':old_protocol['study_id'],'original_pilot_protocol':old_protocol,
            'original_rows_sha256':pilot.stable_hash(old_rows),
            'extension_script_sha256':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
            'new_seeds':NEW_SEEDS,'all_seeds':ALL_SEEDS,'variant_ids':pilot.VARIANTS}


def extension_dir(base_dir,create):
    folder=base_dir/'extension_10seeds_v1'
    if create: folder.mkdir(exist_ok=True)
    if folder.is_symlink() or not folder.is_dir(): raise ValueError('Продолжение ещё не создано или его папка является ссылкой.')
    return folder


def open_extension(pilot,folder,protocol,old_rows,create):
    path=folder/'extension.sqlite3'
    if path.is_symlink(): raise ValueError('База продолжения не должна быть ссылкой.')
    exists=path.is_file()
    if not exists and not create: raise ValueError('Продолжение ещё не запущено.')
    db=sqlite3.connect(path,timeout=30);db.execute('PRAGMA synchronous=FULL')
    try:
        if not exists:
            db.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE trials(variant INTEGER NOT NULL,seed INTEGER NOT NULL,left_count INTEGER NOT NULL,right_count INTEGER NOT NULL,sim_seconds REAL NOT NULL,total_seconds REAL NOT NULL,weight_sha256 TEXT NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(variant,seed));')
            db.execute('INSERT INTO metadata VALUES(?,?)',('protocol',json.dumps(protocol,ensure_ascii=False,sort_keys=True)));db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('База продолжения повреждена.')
        rec=db.execute('SELECT value FROM metadata WHERE key=?',('protocol',)).fetchall()
        if len(rec)!=1 or json.loads(rec[0][0])!=protocol: raise ValueError('Данные или протокол изменились; продолжение заблокировано.')
        old_hashes={r[0]:r[6] for r in old_rows}
        rows=db.execute('SELECT variant,seed,left_count,right_count,sim_seconds,total_seconds,weight_sha256,digest FROM trials').fetchall()
        for v,s,l,r,sim,total,w,digest in rows:
            if (v not in pilot.VARIANTS or s not in NEW_SEEDS or type(l)!=int or type(r)!=int or not 0<=l<=10000 or not 0<=r<=10000 or
                not all(isinstance(x,(int,float)) and math.isfinite(x) and x>=0 for x in (sim,total)) or
                w!=old_hashes[v] or digest!=pilot.row_hash(v,s,l,r,sim,total,w)):
                raise ValueError('Найден повреждённый повтор или несовпадение весов; продолжение заблокировано.')
        return db
    except Exception: db.close();raise


def report(pilot,view,out,controls,old_rows,new_rows,status,protocol):
    all_rows=sorted(old_rows+new_rows);control={r[2]:r for r in controls}
    grouped={v:[] for v in pilot.VARIANTS}
    for row in all_rows: grouped[row[0]].append(row)
    result=[]
    for v in pilot.VARIANTS:
        rows=grouped[v];left=[r[2] for r in rows];right=[r[3] for r in rows]
        result.append({'variant':v+1,'weight_seed':1000+v,'trials':len(rows),'expected':10,'complete':len(rows)==10,
          'left_mean_hz':statistics.mean(left),'left_sd_hz':statistics.stdev(left) if len(left)>1 else '',
          'left_min_hz':min(left),'left_max_hz':max(left),
          'right_mean_hz':statistics.mean(right),'right_sd_hz':statistics.stdev(right) if len(right)>1 else '',
          'right_min_hz':min(right),'right_max_hz':max(right),
          'left_mean_difference_same_seed_control':statistics.mean(r[2]-control[r[1]][3] for r in rows),
          'right_mean_difference_same_seed_control':statistics.mean(r[3]-control[r[1]][4] for r in rows)})
    pilot.write_csv(out/'variants_10seed.csv',list(result[0]),result)
    pilot.write_csv(out/'trials_10seed.csv',['variant','weight_seed','input_seed','left_count','right_count','origin','simulation_seconds','network_and_simulation_seconds','weight_sha256'],
      [{'variant':v+1,'weight_seed':1000+v,'input_seed':s,'left_count':l,'right_count':r,'origin':'pilot' if s<3 else 'extension',
        'simulation_seconds':sim,'network_and_simulation_seconds':total,'weight_sha256':w} for v,s,l,r,sim,total,w,_ in all_rows])
    pilot.write_csv(out/'controls.csv',['seed','left_count','right_count','included_in_10seed_comparison'],
      [{'seed':r[2],'left_count':r[3],'right_count':r[4],'included_in_10seed_comparison':r[2] in ALL_SEEDS} for r in controls])
    matched=[control[s] for s in ALL_SEEDS];left_control=statistics.mean(r[3] for r in matched);right_control=statistics.mean(r[4] for r in matched)
    text=['ПРОДОЛЖЕНИЕ ПИЛОТА МОДЕЛЬНОЙ ИНДИВИДУАЛЬНОСТИ',
          f'Состояние: {status}. Прежние повторы: 30/30; новые seed 3–9: {len(new_rows)}/70.',
          '10 фиксированных вариантов, 50 Гц, 1 секунда; план по 10 seed на вариант.',
          f'Контроль на seed 0–9: левый {left_control:.2f} Гц, правый {right_control:.2f} Гц.',
          'Для незавершённых вариантов средние рассчитаны только по имеющимся seed; сравнение вариантов неполное.',
          '', 'Вариант | повторов | левый MN9, среднее | правый MN9, среднее']
    for x in result: text.append(f"{x['variant']:>7} | {x['trials']}/10 | {x['left_mean_hz']:.2f} | {x['right_mean_hz']:.2f}")
    complete=[x for x in result if x['complete']]
    if len(complete)>=2:
        text.extend(['',f"Разброс средних левого MN9 между завершёнными вариантами: SD {statistics.stdev(x['left_mean_hz'] for x in complete):.2f} Гц (n={len(complete)}).",
                     f"Среднее SD повторов левого MN9 внутри этих вариантов: {statistics.mean(x['left_sd_hz'] for x in complete):.2f} Гц.",
                     'Эти описательные SD относятся к разным величинам и не являются оценкой доли индивидуальности.'])
    text.extend(['','Ограничения: модельные варианты, одна частота и 10 seed, а не животные или поведение.',
                 'Общие seed не гарантируют идентичные входные спайковые времена. Биологическая реалистичность ±5% не установлена.',
                 'Результаты не являются проверкой значимости или доказательством устойчивого фенотипа.'])
    (out/'report.txt').write_text('\n'.join(text)+'\n',encoding='utf8')
    images=[]
    if all_rows:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig,ax=plt.subplots(figsize=(8,4))
            for x in result:
                rows=grouped[x['variant']-1]
                ax.scatter([x['variant']]*len(rows),[r[2] for r in rows],color='#65766c',s=14)
                if x['complete']: ax.plot(x['variant'],x['left_mean_hz'],marker='_',color='#514b44',markersize=13)
            ax.axhline(left_control,color='#9a5848',linestyle='--',label='контроль: среднее seed 0–9')
            ax.set(xlabel='Фиксированный вариант модели',ylabel='Левый MN9, спайков за 1 с',title='Пилот: до 10 входных seed')
            ax.set_xticks(range(1,11));ax.legend();fig.tight_layout();fig.savefig(out/'variants_10seed.png',dpi=140);plt.close(fig);images.append('variants_10seed.png')
        except ImportError: pass
    files=['report.txt','variants_10seed.csv','trials_10seed.csv','controls.csv','source_snapshot.sqlite3','pilot.sqlite3']+(['extension_snapshot.sqlite3'] if (out/'extension_snapshot.sqlite3').is_file() else [])+images
    summary={'status':status,'mode':MODE,'study_id':protocol['study_id'],'previous_trials':len(old_rows),'new_completed':len(new_rows),
             'new_planned':70,'total_trials':len(all_rows),'total_planned':100,'complete_variants':len(complete),
             'original_rows_sha256':protocol['original_rows_sha256'],'files':files,
             'caveat':'Искусственные модельные варианты не являются животными; совпадение seed не доказывает совпадения входов.'}
    view.atomic_json(out/'summary.json',summary);print('\n'.join(text),flush=True)


def execute(pilot,shared,view,module,study,manifest,out,stage):
    _,meta,controls=pilot.source_snapshot(shared,view,study,manifest,out)
    original_protocol=pilot.protocol(meta,controls,study.name)
    base_dir=pilot.pilot_dir(Path(os.environ['FLY_SHIU_SHARED_ROOT']),study.name)
    old_rows=original_snapshot(pilot,shared,view,base_dir,original_protocol,out)
    p=make_protocol(pilot,original_protocol,old_rows)
    if stage=='extend-plan':
        report(pilot,view,out,controls,old_rows,[],'plan_ready',p);return
    folder=extension_dir(base_dir,stage=='extend-run')
    with shared.lock(folder):
        db=open_extension(pilot,folder,p,old_rows,create=stage=='extend-run')
        try:
            if stage=='extend-run':
                have={(v,s) for v,s in db.execute('SELECT variant,seed FROM trials')}
                print(f'Отдельная база продолжения: {folder}; новых сохранено {len(have)}/70.',flush=True)
                stop=out/'stop.request'
                if len(have)<70 and not stop.exists():
                    pilot.check_memory();lesion,base,data=module.validate_simulation(meta,study/shared.TOP_DIR)
                    hashes={row[0]:row[6] for row in old_rows}
                    for v in pilot.VARIANTS:
                        if stop.exists(): break
                        remaining=[s for s in NEW_SEEDS if (v,s) not in have]
                        if not remaining: continue
                        pilot.check_memory();weights=pilot.weights_for_variant(data['weights'],v)
                        weight_sha=hashlib.sha256(memoryview(weights).cast('B')).hexdigest()
                        if weight_sha!=hashes[v]: raise ValueError(f'Веса варианта {v+1} не совпали с исходным пилотом. Продолжение остановлено.')
                        altered=dict(data);altered['weights']=weights
                        for seed in remaining:
                            if stop.exists(): break
                            pilot.check_memory();print(f'Вариант {v+1}/10, seed {seed}: новый повтор {len(have)+1}/70.',flush=True)
                            start=time.perf_counter();left,right,sim=module.run_trial(lesion,base,altered,[],seed);total=round(time.perf_counter()-start,3)
                            db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?,?)',(v,seed,left,right,sim,total,weight_sha,pilot.row_hash(v,seed,left,right,sim,total,weight_sha)));db.commit();have.add((v,seed))
                            view.atomic_json(out/'progress.json',{'new_completed':len(have),'new_total':70,'variant':v+1,'seed':seed})
                            print(f'Сохранено новых {len(have)}/70: MN9 {left}/{right}, сеть и симуляция {total:.1f} с.',flush=True)
                        del altered,weights
            rows=db.execute('SELECT variant,seed,left_count,right_count,sim_seconds,total_seconds,weight_sha256,digest FROM trials ORDER BY variant,seed').fetchall()
            with sqlite3.connect(out/'extension_snapshot.sqlite3') as copy: db.backup(copy)
            status='complete' if len(rows)==70 else 'stopped' if stage=='extend-run' and (out/'stop.request').exists() else 'partial'
            report(pilot,view,out,controls,old_rows,rows,status,p)
        finally: db.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['extend-plan','extend-run','extend-review'],required=True);parser.add_argument('--study',required=True);args=parser.parse_args()
    out=Path(os.environ['FLY_RUN_DIR']);out.mkdir(parents=True,exist_ok=True)
    try:
        pilot=load_pilot();shared=pilot.load_shared();module,view=shared.modules()
        study=shared.study_path(os.environ['FLY_SHIU_SHARED_ROOT'],args.study);manifest=shared.read_manifest(study)
        execute(pilot,shared,view,module,study,manifest,out,args.stage);return 0
    except Exception as exc:
        out.joinpath('summary.json').write_text(json.dumps({'status':'error','mode':args.stage,'error':f'{type(exc).__name__}: {exc}','files':['progress.json'] if (out/'progress.json').exists() else []},ensure_ascii=False,indent=2),encoding='utf8')
        print(traceback.format_exc(),file=sys.stderr,flush=True);return 1

if __name__=='__main__':sys.exit(main())
