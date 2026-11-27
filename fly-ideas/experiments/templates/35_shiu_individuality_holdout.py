"""Независимые по номерам seed повторы 10 фиксированных вариантов v630.

Новая база: исходные 100 повторов и контроли только читаются через снимки.
План сравнения фиксируется в метаданных новой базы до первого повтора.
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

EXTENSION_SHA='7ea53ad2e18f038f18c2ef77f5d86d372a414968a2f3816944c2cb43329ebc71'
NEW_SEEDS=list(range(10,20))
MODE='shiu-individuality-holdout-10seed-v1'


def load_extension():
    path=Path(__file__).parent/'34_shiu_individuality_extension.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=EXTENSION_SHA:
        raise ValueError('Код прежнего продолжения изменён. Проверка остановлена.')
    spec=importlib.util.spec_from_file_location('previous_individuality_extension',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def average_ranks(values):
    # Ascending ranks; tied values receive their mean rank.
    return [1+sum(x<v for x in values)+(sum(x==v for x in values)-1)/2 for v in values]


def correlation(a,b):
    ma=statistics.mean(a);mb=statistics.mean(b)
    aa=sum((x-ma)**2 for x in a);bb=sum((x-mb)**2 for x in b)
    if not aa or not bb: return None
    return sum((x-ma)*(y-mb) for x,y in zip(a,b))/math.sqrt(aa*bb)


def load_previous(pilot,extension,shared,view,base_dir,old_protocol,out):
    old_rows=extension.original_snapshot(pilot,shared,view,base_dir,old_protocol,out)
    previous=extension.extension_dir(base_dir,False)
    source=previous/'extension.sqlite3'
    if source.is_symlink() or not source.is_file(): raise ValueError('База продолжения на 10 seed отсутствует или является ссылкой.')
    with shared.lock(previous): view.snapshot(source,out/'extension.sqlite3')
    protocol=extension.make_protocol(pilot,old_protocol,old_rows)
    db=extension.open_extension(pilot,out,protocol,old_rows,False)
    try:
        rows=db.execute('SELECT variant,seed,left_count,right_count,sim_seconds,total_seconds,weight_sha256,digest FROM trials ORDER BY variant,seed').fetchall()
    finally: db.close()
    if len(rows)!=70 or {(r[0],r[1]) for r in rows}!={(v,s) for v in pilot.VARIANTS for s in extension.NEW_SEEDS}:
        raise ValueError('Для проверки нужны все 70 проверенных повторов продолжения на 10 seed.')
    return sorted(old_rows+rows)


def make_protocol(pilot,old_protocol,previous):
    left=[statistics.mean(r[2] for r in previous if r[0]==v) for v in pilot.VARIANTS]
    right=[statistics.mean(r[3] for r in previous if r[0]==v) for v in pilot.VARIANTS]
    return {'kind':MODE,'study_id':old_protocol['study_id'],'original_pilot_protocol':old_protocol,
            'previous_rows_sha256':pilot.stable_hash(previous),
            'holdout_script_sha256':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
            'discovery_seeds':list(range(10)),'holdout_seeds':NEW_SEEDS,'variant_ids':pilot.VARIANTS,
            'discovery_left_means_hz':left,'discovery_left_average_ranks_low_first':average_ranks(left),
            'discovery_right_means_hz':right,
            'analysis_plan':{'primary':'Spearman correlation of left MN9 variant means, discovery seed 0-9 vs holdout seed 10-19; average ranks for ties',
                             'secondary':'Pearson correlation of left means, Spearman of right means, difference of left means variant 10 minus variant 9',
                             'interpretation':'descriptive; no significance test or success threshold; variant pair selected after discovery',
                             'evaluation':'only after all 100 holdout trials are complete'}}


def open_db(pilot,folder,protocol,previous,create):
    path=folder/'holdout.sqlite3'
    if path.is_symlink(): raise ValueError('База проверки не должна быть ссылкой.')
    exists=path.is_file()
    if not exists and not create: raise ValueError('Проверка ещё не запущена.')
    db=sqlite3.connect(path,timeout=30);db.execute('PRAGMA synchronous=FULL')
    try:
        if not exists:
            db.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE trials(variant INTEGER NOT NULL,seed INTEGER NOT NULL,left_count INTEGER NOT NULL,right_count INTEGER NOT NULL,sim_seconds REAL NOT NULL,total_seconds REAL NOT NULL,weight_sha256 TEXT NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(variant,seed));')
            db.execute('INSERT INTO metadata VALUES(?,?)',('protocol',json.dumps(protocol,ensure_ascii=False,sort_keys=True)));db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('База проверки повреждена.')
        rec=db.execute('SELECT value FROM metadata WHERE key=?',('protocol',)).fetchall()
        if len(rec)!=1 or json.loads(rec[0][0])!=protocol: raise ValueError('Прежние данные или план изменились; продолжение остановлено.')
        hashes={r[0]:r[6] for r in previous}
        rows=db.execute('SELECT variant,seed,left_count,right_count,sim_seconds,total_seconds,weight_sha256,digest FROM trials').fetchall()
        for v,s,l,r,sim,total,w,d in rows:
            if (v not in pilot.VARIANTS or s not in NEW_SEEDS or type(l)!=int or type(r)!=int or not 0<=l<=10000 or not 0<=r<=10000 or
                not all(isinstance(x,(int,float)) and math.isfinite(x) and x>=0 for x in (sim,total)) or
                w!=hashes[v] or d!=pilot.row_hash(v,s,l,r,sim,total,w)):
                raise ValueError('Найден повреждённый повтор или несовпадение весов; проверка остановлена.')
        return db
    except Exception: db.close();raise


def report(pilot,view,out,controls,previous,rows,status,protocol):
    rows=sorted(rows); complete=len(rows)==100
    by_variant={v:[r for r in rows if r[0]==v] for v in pilot.VARIANTS}
    ranks=protocol['discovery_left_average_ranks_low_first']
    new_left=[statistics.mean(r[2] for r in by_variant[v]) if by_variant[v] else None for v in pilot.VARIANTS]
    new_right=[statistics.mean(r[3] for r in by_variant[v]) if by_variant[v] else None for v in pilot.VARIANTS]
    new_ranks=average_ranks(new_left) if complete else [None]*10
    data=[{'variant':v+1,'weight_seed':1000+v,'holdout_trials':len(by_variant[v]),
           'discovery_left_mean_hz':protocol['discovery_left_means_hz'][v], 'discovery_left_rank':ranks[v],
           'holdout_left_mean_hz':new_left[v] if new_left[v] is not None else '',
           'holdout_left_rank':new_ranks[v] if complete else '',
           'discovery_right_mean_hz':protocol['discovery_right_means_hz'][v],
           'holdout_right_mean_hz':new_right[v] if new_right[v] is not None else ''} for v in pilot.VARIANTS]
    pilot.write_csv(out/'variants_holdout.csv',list(data[0]),data)
    pilot.write_csv(out/'trials_holdout.csv',['variant','weight_seed','input_seed','left_count','right_count','simulation_seconds','network_and_simulation_seconds','weight_sha256'],
        [{'variant':v+1,'weight_seed':1000+v,'input_seed':s,'left_count':l,'right_count':r,'simulation_seconds':sim,'network_and_simulation_seconds':total,'weight_sha256':w} for v,s,l,r,sim,total,w,_ in rows])
    pilot.write_csv(out/'controls_holdout.csv',['seed','left_count','right_count'],[{'seed':r[2],'left_count':r[3],'right_count':r[4]} for r in controls if r[2] in NEW_SEEDS])
    view.atomic_json(out/'frozen_plan.json',protocol)
    text=['ПРОВЕРКА ПОРЯДКА МОДЕЛЬНЫХ ВАРИАНТОВ НА НОВЫХ SEED',
          f'Состояние: {status}; исходные повторы 100/100; новые {len(rows)}/100.',
          'План: 10 прежних вариантов, 50 Гц, 1 с, новые seed 10–19. Старые базы не изменяются.',
          'Основная описательная метрика: Спирмен для средних левого MN9 по вариантам, seed 0–9 против 10–19; одинаковым значениям присваивается средний ранг.',
          'Дополнительно: Пирсон для левого MN9, Спирмен для правого и разность средних левого MN9 вариантов 10 и 9.',
          'Никакой порог успеха или тест значимости заранее не задан. Пара 9 и 10 выбрана после просмотра исходных результатов.',
          '', 'Вариант | новых | исходное среднее слева | новое среднее слева']
    for x in data:
        val=f"{x['holdout_left_mean_hz']:.2f}" if x['holdout_trials'] else 'нет данных'
        text.append(f"{x['variant']:>7} | {x['holdout_trials']}/10 | {x['discovery_left_mean_hz']:.2f} | {val}")
    metrics={}
    if complete:
        metrics={'left_spearman':correlation(ranks,new_ranks),
                 'left_pearson':correlation(protocol['discovery_left_means_hz'],new_left),
                 'right_spearman':correlation(average_ranks(protocol['discovery_right_means_hz']),average_ranks(new_right)),
                 'left_mean_difference_variant_10_minus_9':new_left[9]-new_left[8]}
        fmt=lambda x: 'не определена (нет разброса)' if x is None else f'{x:.3f}'
        text.extend(['',f"Спирмен слева: {fmt(metrics['left_spearman'])}; Пирсон слева: {fmt(metrics['left_pearson'])}.",
                     f"Спирмен справа: {fmt(metrics['right_spearman'])}.",
                     f"Вариант 10 минус вариант 9, левый MN9 на новых seed: {metrics['left_mean_difference_variant_10_minus_9']:.2f} Гц."])
    else:
        text.extend(['','Сравнение порядка и итоговые метрики появятся только после 100/100 новых повторов.',
                     'Промежуточные средние имеют разное число seed и не годятся для сравнения порядка.'])
    text.extend(['','Ограничения: варианты искусственные, это не животные и не поведение; одна частота, один коннектом.',
                 'Новые номера seed не гарантируют одинаковые входные спайковые времена между вариантами.',
                 'План фиксируется локально до новых расчётов, но не является независимой внешней регистрацией.',
                 'Описательные результаты не доказывают статистическую значимость или устойчивый биологический фенотип.'])
    (out/'report.txt').write_text('\n'.join(text)+'\n',encoding='utf8')
    files=['report.txt','frozen_plan.json','variants_holdout.csv','trials_holdout.csv','controls_holdout.csv','source_snapshot.sqlite3','pilot.sqlite3','extension.sqlite3']
    if (out/'holdout_snapshot.sqlite3').is_file(): files.append('holdout_snapshot.sqlite3')
    view.atomic_json(out/'summary.json',{'status':status,'mode':MODE,'study_id':protocol['study_id'],'previous_trials':len(previous),
        'new_completed':len(rows),'new_planned':100,'metrics':metrics,'previous_rows_sha256':protocol['previous_rows_sha256'],'files':files})
    print('\n'.join(text),flush=True)


def execute(pilot,extension,shared,view,module,study,manifest,out,stage):
    _,meta,controls=pilot.source_snapshot(shared,view,study,manifest,out)
    old_protocol=pilot.protocol(meta,controls,study.name)
    base_dir=pilot.pilot_dir(Path(os.environ['FLY_SHIU_SHARED_ROOT']),study.name)
    previous=load_previous(pilot,extension,shared,view,base_dir,old_protocol,out)
    protocol=make_protocol(pilot,old_protocol,previous)
    if stage=='holdout-plan': report(pilot,view,out,controls,previous,[],'plan_ready',protocol);return
    folder=base_dir/'holdout_10seeds_v1'
    if stage=='holdout-run': folder.mkdir(exist_ok=True)
    if folder.is_symlink() or not folder.is_dir(): raise ValueError('Проверка ещё не создана или её папка является ссылкой.')
    with shared.lock(folder):
        db=open_db(pilot,folder,protocol,previous,stage=='holdout-run')
        try:
            if stage=='holdout-run':
                have={(v,s) for v,s in db.execute('SELECT variant,seed FROM trials')}
                print(f'Отдельная база проверки: {folder}; сохранено {len(have)}/100.',flush=True)
                stop=out/'stop.request'
                if len(have)<100 and not stop.exists():
                    pilot.check_memory();lesion,base,data=module.validate_simulation(meta,study/shared.TOP_DIR)
                    hashes={r[0]:r[6] for r in previous}
                    for v in pilot.VARIANTS:
                        if stop.exists(): break
                        remaining=[s for s in NEW_SEEDS if (v,s) not in have]
                        if not remaining: continue
                        pilot.check_memory();weights=pilot.weights_for_variant(data['weights'],v)
                        weight_sha=hashlib.sha256(memoryview(weights).cast('B')).hexdigest()
                        if weight_sha!=hashes[v]: raise ValueError(f'Веса варианта {v+1} не совпали с исходными. Проверка остановлена.')
                        altered=dict(data);altered['weights']=weights
                        for seed in remaining:
                            if stop.exists(): break
                            pilot.check_memory();print(f'Вариант {v+1}/10, seed {seed}: новый повтор {len(have)+1}/100.',flush=True)
                            start=time.perf_counter();left,right,sim=module.run_trial(lesion,base,altered,[],seed);total=round(time.perf_counter()-start,3)
                            db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?,?)',(v,seed,left,right,sim,total,weight_sha,pilot.row_hash(v,seed,left,right,sim,total,weight_sha)));db.commit();have.add((v,seed))
                            view.atomic_json(out/'progress.json',{'new_completed':len(have),'new_total':100,'variant':v+1,'seed':seed})
                            print(f'Сохранено новых {len(have)}/100: MN9 {left}/{right}, сеть и симуляция {total:.1f} с.',flush=True)
                        del altered,weights
            rows=db.execute('SELECT variant,seed,left_count,right_count,sim_seconds,total_seconds,weight_sha256,digest FROM trials ORDER BY variant,seed').fetchall()
            with sqlite3.connect(out/'holdout_snapshot.sqlite3') as copy: db.backup(copy)
            status='complete' if len(rows)==100 else 'stopped' if stage=='holdout-run' and (out/'stop.request').exists() else 'partial'
            report(pilot,view,out,controls,previous,rows,status,protocol)
        finally: db.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['holdout-plan','holdout-run','holdout-review'],required=True);parser.add_argument('--study',required=True);args=parser.parse_args()
    out=Path(os.environ['FLY_RUN_DIR']);out.mkdir(parents=True,exist_ok=True)
    try:
        extension=load_extension();pilot=extension.load_pilot();shared=pilot.load_shared();module,view=shared.modules()
        study=shared.study_path(os.environ['FLY_SHIU_SHARED_ROOT'],args.study);manifest=shared.read_manifest(study)
        execute(pilot,extension,shared,view,module,study,manifest,out,args.stage);return 0
    except Exception as exc:
        out.joinpath('summary.json').write_text(json.dumps({'status':'error','mode':args.stage,'error':f'{type(exc).__name__}: {exc}','files':['progress.json'] if (out/'progress.json').exists() else []},ensure_ascii=False,indent=2),encoding='utf8')
        print(traceback.format_exc(),file=sys.stderr,flush=True);return 1

if __name__=='__main__':sys.exit(main())
