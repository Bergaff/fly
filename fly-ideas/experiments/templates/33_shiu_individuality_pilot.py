"""Изолированный пилот модельной индивидуальности v630; без автоматического запуска.

10 фиксированных вариантов весов × 3 seed при 50 Гц, одна симуляция за раз.
Контроли читаются из согласованного снимка общего набора; исходные базы не меняются.
"""
import argparse
import csv
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

SHARED_SHA='b3154763708c8f24ae63e2ba804da9e79b65ef7c962588f7261018cf8f84a08f'
VARIANTS=list(range(10))
SEEDS=[0,1,2]
VERSION='shiu-individuality-pilot-v1'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load_shared():
    path=Path(__file__).parent/'32_shiu_shared_study.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=SHARED_SHA:
        raise ValueError('Версия общего набора отличается; исходные файлы не изменены.')
    spec=importlib.util.spec_from_file_location('pilot_shared',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def stable_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def row_hash(variant,seed,left,right,sim_seconds,total_seconds,weight_sha):
    return stable_hash([variant,seed,left,right,float(sim_seconds).hex(),float(total_seconds).hex(),weight_sha])


def weights_for_variant(original,variant):
    import numpy as np
    # PCG64 is separate from Brian's global input RNG; generated once per variant.
    rng=np.random.Generator(np.random.PCG64(1000+variant))
    weights=rng.random(len(original),dtype=np.float64)
    weights*=0.1;weights+=0.95;weights*=original
    return weights


def memory_available():
    if os.name=='nt':
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong),('total_phys',ctypes.c_ulonglong),('available_phys',ctypes.c_ulonglong),('total_page',ctypes.c_ulonglong),('available_page',ctypes.c_ulonglong),('total_virtual',ctypes.c_ulonglong),('available_virtual',ctypes.c_ulonglong),('available_extended_virtual',ctypes.c_ulonglong)]
        status=MemoryStatus();status.length=ctypes.sizeof(status)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)): raise OSError('Не удалось определить свободную RAM.')
        return int(status.available_phys)
    try:
        import psutil
        available=psutil.virtual_memory().available
        for maximum,current in [('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory.current'),('/sys/fs/cgroup/memory/memory.limit_in_bytes','/sys/fs/cgroup/memory/memory.usage_in_bytes')]:
            try:
                limit=Path(maximum).read_text().strip();used=int(Path(current).read_text().strip())
                if limit!='max': available=min(available,max(0,int(limit)-used))
            except (OSError,ValueError): pass
        return int(available)
    except ImportError: raise ValueError('Для проверки свободной памяти нужен psutil.')


def check_memory():
    available=memory_available()
    if available<4*1024**3: raise MemoryError(f'Свободно {available/1024**3:.1f} ГиБ; перед новым повтором нужно не менее 4 ГиБ. Освободите память и продолжите позже.')
    print(f'Свободно RAM: {available/1024**3:.1f} ГиБ. Один процесс; проверка не гарантирует защиту от нехватки памяти.',flush=True)


def source_snapshot(shared,view,study,manifest,out):
    # Study lock protects snapshotting from a concurrent managed writer.
    with shared.lock(study):
        source=view.snapshot(study/shared.CONTROL_DIR,out/'source_snapshot.sqlite3')
    meta,rows=view.read_checked(out/'source_snapshot.sqlite3')
    if meta!=manifest['source_protocol'] or len(rows)!=30 or any(f!=50 or target!='' for f,target,*_ in rows) or sorted(r[2] for r in rows)!=list(range(30)):
        raise ValueError('Нужны все 30 проверенных контролей 50 Гц этого набора.')
    view.read_top(study/shared.TOP_DIR,meta)
    return source,meta,sorted(rows,key=lambda x:x[2])


def protocol(meta,rows,study_id):
    return {'kind':VERSION,'study_id':study_id,'source_protocol':meta,'control_rows_sha256':stable_hash(rows),
            'pilot_script_sha256':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
            'frequency_hz':50,'variant_ids':VARIANTS,'input_seeds':SEEDS,
            'weight_random_generator':'numpy.random.Generator(PCG64(1000+variant_id))',
            'factor':'independent uniform [0.95, 1.05) per connection; sign preserved',
            'duration_ms':1000,'dt_ms':0.1}


def pilot_dir(shared_root,study_id,create=False):
    # Separate from the shared study and its mutable databases.
    root=Path(shared_root).parent/'shiu-v630-individuality'
    if create: root.mkdir(exist_ok=True)
    if root.is_symlink() or not root.is_dir(): raise ValueError('Отдельная папка пилота отсутствует или является ссылкой.')
    folder=root/study_id
    if create: folder.mkdir(exist_ok=True)
    if folder.is_symlink() or not folder.is_dir(): raise ValueError('Пилот ещё не создан или его папка является ссылкой.')
    return folder


def open_db(folder,meta,create):
    path=folder/'pilot.sqlite3'
    if path.is_symlink(): raise ValueError('База пилота не должна быть ссылкой.')
    exists=path.is_file()
    if not exists and not create: raise ValueError('Пилот ещё не запущен.')
    db=sqlite3.connect(path,timeout=30);db.execute('PRAGMA synchronous=FULL')
    try:
        if not exists:
            db.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE trials(variant INTEGER NOT NULL,seed INTEGER NOT NULL,left_count INTEGER NOT NULL,right_count INTEGER NOT NULL,sim_seconds REAL NOT NULL,total_seconds REAL NOT NULL,weight_sha256 TEXT NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(variant,seed));')
            db.execute('INSERT INTO metadata VALUES(?,?)',('protocol',json.dumps(meta,ensure_ascii=False,sort_keys=True)));db.commit()
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('База пилота повреждена.')
        record=db.execute('SELECT value FROM metadata WHERE key=?',('protocol',)).fetchall()
        if len(record)!=1 or json.loads(record[0][0])!=meta: raise ValueError('Протокол или контроли изменились. Продолжение остановлено, база сохранена.')
        rows=db.execute('SELECT variant,seed,left_count,right_count,sim_seconds,total_seconds,weight_sha256,digest FROM trials').fetchall()
        hashes={}
        for v,s,l,r,sim,total,weight,check in rows:
            if (v not in VARIANTS or s not in SEEDS or type(l)!=int or type(r)!=int or not 0<=l<=10000 or not 0<=r<=10000 or
                not all(isinstance(x,(int,float)) and math.isfinite(x) and x>=0 for x in (sim,total)) or
                not isinstance(weight,str) or len(weight)!=64 or any(c not in '0123456789abcdef' for c in weight) or
                check!=row_hash(v,s,l,r,sim,total,weight) or (v in hashes and hashes[v]!=weight)):
                raise ValueError('Некорректный повтор пилота; продолжение остановлено.')
            hashes[v]=weight
        return db
    except Exception: db.close();raise


def write_csv(path,fields,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)


def report(out,view,meta,controls,rows,status):
    rows=sorted(rows);by_variant={v:[] for v in VARIANTS}
    for v,s,l,r,sim,total,weight,_ in rows: by_variant[v].append((s,l,r,sim,total,weight))
    controls_by_seed={x[2]:x for x in controls};matched=[controls_by_seed[s] for s in SEEDS]
    summary=[]
    for v in VARIANTS:
        trials=by_variant[v];left=[x[1] for x in trials];right=[x[2] for x in trials]
        differences_left=[x[1]-controls_by_seed[x[0]][3] for x in trials]
        differences_right=[x[2]-controls_by_seed[x[0]][4] for x in trials]
        summary.append({'variant':v+1,'weight_seed':1000+v,'trials':len(trials),'complete':len(trials)==len(SEEDS),
            'left_mean_hz':statistics.mean(left) if left else '', 'left_sd_hz':statistics.stdev(left) if len(left)>1 else '',
            'right_mean_hz':statistics.mean(right) if right else '', 'right_sd_hz':statistics.stdev(right) if len(right)>1 else '',
            'left_mean_difference_vs_same_seed_control':statistics.mean(differences_left) if trials else '',
            'right_mean_difference_vs_same_seed_control':statistics.mean(differences_right) if trials else ''})
    write_csv(out/'variants.csv',list(summary[0]),summary)
    write_csv(out/'pilot_trials.csv',['variant','weight_seed','input_seed','left_count','right_count','simulation_seconds','network_and_simulation_seconds','weight_sha256'],
              [{'variant':v+1,'weight_seed':1000+v,'input_seed':s,'left_count':l,'right_count':r,'simulation_seconds':sim,'network_and_simulation_seconds':total,'weight_sha256':w} for v,s,l,r,sim,total,w,_ in rows])
    write_csv(out/'controls.csv',['seed','left_count','right_count'],[{'seed':r[2],'left_count':r[3],'right_count':r[4]} for r in controls])
    complete=[x for x in summary if x['complete']]
    base_left=statistics.mean(r[3] for r in controls);base_right=statistics.mean(r[4] for r in controls)
    match_left=statistics.mean(r[3] for r in matched);match_right=statistics.mean(r[4] for r in matched)
    text=['ПИЛОТ МОДЕЛЬНОЙ ИНДИВИДУАЛЬНОСТИ',f'Состояние: {status}; готово {len(rows)}/30 новых повторов.',
          'Сеть v630, 50 Гц, 1 секунда. 10 фиксированных вариантов × 3 seed; контроль: прежние 30 повторов.',
          'Каждый вес умножен на независимый равномерный множитель от 0,95 до 1,05, знак сохраняется. 5% не калиброваны по биологическим данным.',
          f'Контроль, все 30: левый {base_left:.2f} ± {statistics.stdev(r[3] for r in controls):.2f} Гц, правый {base_right:.2f} ± {statistics.stdev(r[4] for r in controls):.2f} Гц (SD).',
          f'Контроль, seed 0–2: левый {match_left:.2f} Гц, правый {match_right:.2f} Гц.',
          '', 'Вариант | повторов | левый MN9, среднее | правый MN9, среднее']
    for x in summary:
        l=f"{x['left_mean_hz']:.2f}" if x['trials'] else 'нет данных';r=f"{x['right_mean_hz']:.2f}" if x['trials'] else 'нет данных'
        text.append(f"{x['variant']:>7} | {x['trials']}/3 | {l} | {r}")
    if len(complete)>=2:
        means=[x['left_mean_hz'] for x in complete]
        within=statistics.mean(x['left_sd_hz'] for x in complete)
        text.extend(['',f'Описательный разброс средних левого MN9 между завершёнными вариантами: SD {statistics.stdev(means):.2f} Гц (n={len(means)}).',
                     f'Среднее SD трёх повторов внутри этих вариантов: {within:.2f} Гц.',
                     'Это не оценка доли индивидуальности: всего три общих seed, межвариантные средние содержат шум; два SD относятся к разным величинам.'])
    text.extend(['','Ограничения: один коннектом, искусственные варианты, одна частота и три входных seed; это не животные и не поведение.',
                 'Совпадение seed само по себе не гарантирует одинаковых входных спайковых времён. Статистическая значимость и устойчивые фенотипы не установлены.',
                 'При остановке сохранённые повторы можно продолжить; повреждение или несовпадение протокола блокирует продолжение.'])
    (out/'report.txt').write_text('\n'.join(text)+'\n',encoding='utf8')
    images=[]
    if rows:
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            fig,ax=plt.subplots(figsize=(8,4))
            for x in summary:
                points=by_variant[x['variant']-1]
                if points: ax.scatter([x['variant']]*len(points),[p[1] for p in points],color='#65766c',s=18)
                if x['complete']: ax.plot(x['variant'],x['left_mean_hz'],marker='_',color='#514b44',markersize=13)
            ax.axhline(match_left,color='#9a5848',linestyle='--',label='контроль: среднее seed 0–2')
            ax.set(xlabel='Фиксированный вариант модели',ylabel='Левый MN9, спайков за 1 с',title='Варианты и повторные входы; пилот')
            ax.set_xticks(range(1,11));ax.legend();fig.tight_layout();fig.savefig(out/'variants.png',dpi=140);plt.close(fig);images.append('variants.png')
        except ImportError: pass
    files=['report.txt','variants.csv','pilot_trials.csv','controls.csv','source_snapshot.sqlite3']+(['pilot_snapshot.sqlite3'] if (out/'pilot_snapshot.sqlite3').is_file() else [])+images
    info={'status':status,'mode':'individuality_pilot','study_id':meta['study_id'],'completed':len(rows),'planned':30,
          'complete_variants':len(complete),'control_trials':30,'source_snapshot_sha256':sha(out/'source_snapshot.sqlite3'),
          'control_rows_sha256':meta['control_rows_sha256'],'files':files,
          'caveat':'Модельные варианты и три повтора не доказывают устойчивой индивидуальности животных.'}
    view.atomic_json(out/'summary.json',info)
    print('\n'.join(text),flush=True)


def execute(shared,view,module,study,manifest,out,stage):
    _,meta,controls=source_snapshot(shared,view,study,manifest,out)
    p=protocol(meta,controls,study.name)
    if stage=='pilot-plan':
        report(out,view,p,controls,[],'plan_ready');return
    folder=pilot_dir(Path(os.environ['FLY_SHIU_SHARED_ROOT']),study.name,create=stage=='pilot-run')
    with shared.lock(folder):
        db=open_db(folder,p,create=stage=='pilot-run')
        try:
            if stage=='pilot-run':
                have={(v,s) for v,s in db.execute('SELECT variant,seed FROM trials')}
                print(f'Отдельная база пилота: {folder}; сохранено {len(have)}/30.',flush=True)
                stop_file=out/'stop.request'
                if len(have)<30 and not stop_file.exists():
                    check_memory()
                    lesion,base,data=module.validate_simulation(meta,study/shared.TOP_DIR)
                    for variant in VARIANTS:
                        if stop_file.exists(): break
                        remaining=[s for s in SEEDS if (variant,s) not in have]
                        if not remaining: continue
                        check_memory();weights=weights_for_variant(data['weights'],variant)
                        weight_sha=hashlib.sha256(memoryview(weights).cast('B')).hexdigest()
                        existing=db.execute('SELECT DISTINCT weight_sha256 FROM trials WHERE variant=?',(variant,)).fetchall()
                        if existing and existing!=[(weight_sha,)]: raise ValueError('Веса варианта изменились; продолжение остановлено.')
                        altered=dict(data);altered['weights']=weights
                        for seed in remaining:
                            if stop_file.exists(): break
                            check_memory();print(f'Вариант {variant+1}/10, seed {seed}: повтор {len(have)+1}/30.',flush=True)
                            started=time.perf_counter();left,right,sim=module.run_trial(lesion,base,altered,[],seed);total=round(time.perf_counter()-started,3)
                            row=(variant,seed,left,right,sim,total,weight_sha,row_hash(variant,seed,left,right,sim,total,weight_sha))
                            db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?,?)',row);db.commit();have.add((variant,seed))
                            view.atomic_json(out/'progress.json',{'completed':len(have),'total':30,'variant':variant+1,'seed':seed})
                            print(f'Сохранено {len(have)}/30: MN9 {left}/{right}, симуляция {sim:.1f} с, сеть и симуляция {total:.1f} с.',flush=True)
                        del altered,weights
            rows=db.execute('SELECT variant,seed,left_count,right_count,sim_seconds,total_seconds,weight_sha256,digest FROM trials').fetchall()
            with sqlite3.connect(out/'pilot_snapshot.sqlite3') as snapshot_db: db.backup(snapshot_db)
            status='complete' if len(rows)==30 else 'stopped' if stage=='pilot-run' and (out/'stop.request').exists() else 'partial'
            report(out,view,p,controls,rows,status)
        finally: db.close()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['pilot-plan','pilot-run','pilot-review'],required=True);parser.add_argument('--study',required=True);args=parser.parse_args()
    out=Path(os.environ['FLY_RUN_DIR']);out.mkdir(parents=True,exist_ok=True)
    try:
        shared=load_shared();module,view=shared.modules();study=shared.study_path(os.environ['FLY_SHIU_SHARED_ROOT'],args.study);manifest=shared.read_manifest(study)
        execute(shared,view,module,study,manifest,out,args.stage);return 0
    except Exception as exc:
        out.joinpath('summary.json').write_text(json.dumps({'status':'error','mode':args.stage,'error':f'{type(exc).__name__}: {exc}','files':['progress.json'] if (out/'progress.json').exists() else []},ensure_ascii=False,indent=2),encoding='utf8')
        print(traceback.format_exc(),file=sys.stderr,flush=True);return 1

if __name__=='__main__':sys.exit(main())
