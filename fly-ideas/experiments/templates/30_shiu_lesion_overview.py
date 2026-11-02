"""Читаемый обзор контрольной базы лезий и контрольной вариабельности MN9.

Исходная база открывается только для чтения и копируется через SQLite backup.
Сетевых симуляций нет; неполные условия явно помечаются как неполные.
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
import traceback

LESION_SHA='fdedb0ac3c7b81692b44c6b5f07f2e2142e3af1617db179426de3b250b57dd93'
TOP_SHA='e630558dbb35e34d5af45bde417e1b91d36e2c6a7c4417e87be27fa2565b2f08'
BASE_SHA='b5f200a3e9472c9aa6318acab8b5fb928d23af3b458c2d43fc29909241e95711'
CONNECTION_SHA='94db8c650533bc36ffa3223f2e62325d5648b8d6bd31c3a4e1c804628c7557b3'
NEURON_SHA='e6b71e17671a9bdb05f55e4bc6774640a1418cb7a05125e0fc994ad40f9bfdfb'
FREQS=[50,60,70,80,90,100,110,120]
SEEDS=list(range(30))


def reference():
    path=Path(__file__).parent/'28_shiu_lesions_v630.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=LESION_SHA:
        raise ValueError('Неизвестная версия исходного скрипта лезий.')
    spec=importlib.util.spec_from_file_location('lesion_reference',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def atomic_json(path,value):
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def snapshot(source,destination):
    source=Path(source).resolve();destination=Path(destination).resolve()
    if source.is_dir(): source=source/'lesions.sqlite3'
    if not source.is_file(): raise ValueError('В выбранной папке нет lesions.sqlite3.')
    if source==destination or destination.exists(): raise ValueError('Снимок должен быть новым файлом, не исходной базой.')
    # Не использовать обычное копирование открытой базы: backup получает согласованный снимок.
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=30) as old,sqlite3.connect(destination,timeout=30) as copy:
        old.backup(copy)
    return source


def read_checked(path, expected_length=200):
    lesion=reference()
    with sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=30) as db:
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('Контрольная база повреждена.')
        records=db.execute('SELECT value FROM metadata WHERE key=?',('protocol',)).fetchall()
        if len(records)!=1: raise ValueError('В базе нет единственного протокола.')
        meta=json.loads(records[0][0]);candidates=meta.get('candidates')
        if (meta.get('schema')!=1 or meta.get('lesion_script_sha256')!=LESION_SHA or meta.get('top_script_sha256')!=TOP_SHA
            or meta.get('base_sha256')!=BASE_SHA or meta.get('connection_sha256')!=CONNECTION_SHA or meta.get('neuron_sha256')!=NEURON_SHA
            or meta.get('frequencies_hz')!=FREQS or meta.get('seeds')!=SEEDS
            or meta.get('side')!='right' or meta.get('duration_ms')!=1000 or meta.get('dt_ms')!=0.1
            or not isinstance(candidates,list) or len(candidates)!=expected_length or len(set(candidates))!=len(candidates)
            or any(not isinstance(v,str) or not v.isdigit() or v.startswith('0') for v in candidates)):
            raise ValueError('Протокол или список кандидатов не соответствуют проверенному расчёту лезий v630.')
        for name in ('connection_sha256','neuron_sha256','top_checkpoint_sha256','top_csv_sha256'):
            value=meta.get(name)
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('В протоколе отсутствует корректная контрольная сумма: '+name)
        rows=db.execute('SELECT frequency,target,seed,left_count,right_count,wall_seconds,digest FROM trials').fetchall()
    seen=set();allowed=set(candidates)|{''}
    for f,t,s,l,r,seconds,check in rows:
        key=(f,t,s)
        if (key in seen or f not in FREQS or t not in allowed or s not in SEEDS
            or type(l)!=int or type(r)!=int or not 0<=l<=10000 or not 0<=r<=10000
            or not isinstance(seconds,(float,int)) or not math.isfinite(seconds) or seconds<0
            or check!=lesion.row_hash(f,t,s,l,r,seconds)):
            raise ValueError('База содержит неправильный или повреждённый повтор.')
        seen.add(key)
    return meta,rows


def read_top(folder,meta):
    folder=Path(folder);csv_path=folder/'top200.csv';checkpoint=folder/'checkpoint.json'
    if digest(csv_path)!=meta['top_csv_sha256'] or digest(checkpoint)!=meta['top_checkpoint_sha256']:
        raise ValueError('Папка топ-200 не совпадает с контрольной базой лезий.')
    with csv_path.open(encoding='utf-8-sig',newline='') as f:
        r=csv.DictReader(f)
        if r.fieldnames!=['rank','root_id','mean_rate_hz','total_spikes_30_trials']: raise ValueError('Некорректная таблица топ-200.')
        items=list(r)
    if len(items)!=len(meta['candidates']): raise ValueError('Неверное количество записей топ-200.')
    result={}
    for i,row in enumerate(items):
        rate=float(row['mean_rate_hz']);count=int(row['total_spikes_30_trials'])
        if row['root_id']!=meta['candidates'][i] or row['rank']!=str(i+1) or count<0 or not math.isfinite(rate) or not math.isclose(rate,count/30,rel_tol=1e-12,abs_tol=1e-12):
            raise ValueError('Таблица топ-200 не соответствует сохранённому протоколу.')
        result[row['root_id']]={'rank':i+1,'rate':rate}
    return result


def write_csv(path,headers,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=headers,extrasaction='ignore');w.writeheader();w.writerows(rows)


def stats(values):
    return {'n':len(values),'mean':statistics.mean(values) if values else None,'sd':statistics.stdev(values) if len(values)>1 else None,
            'min':min(values) if values else None,'max':max(values) if values else None}


def aggregate(meta,rows,top):
    base=reference().load_top().base_module();groups={}
    for f,t,s,l,r,seconds,_ in rows: groups.setdefault((f,t),[]).append((s,l,r,seconds))
    result=[]
    for (freq,target),group in sorted(groups.items(),key=lambda x:(x[0][0],0 if not x[0][1] else meta['candidates'].index(x[0][1])+1)):
        left=stats([x[1] for x in group]);right=stats([x[2] for x in group]);control=groups.get((freq,''),[])
        correlation=None
        if len(group)>=3:
            try: correlation=statistics.correlation([x[1] for x in group],[x[2] for x in group])
            except statistics.StatisticsError: pass
        complete=len(group)==30 and len(control)==30
        control_left=statistics.mean(x[1] for x in control) if complete else None
        ratio=left['mean']/control_left if complete and control_left else None
        role='control' if not target else 'stimulated_grn' if target in base.RIGHT else 'mn9' if target in base.MN9.values() else 'other'
        rank=meta['candidates'].index(target)+1 if target else None
        result.append({'frequency_hz':freq,'target':target or 'control','role':role,'rank_200hz':rank,
                       'activity_200hz':top[target]['rate'] if target and top else None,
                       'trials':len(group),'expected_trials':30,'complete':len(group)==30,
                       'left_mean_hz':left['mean'],'left_sd_hz':left['sd'],'left_min_hz':left['min'],'left_max_hz':left['max'],
                       'right_mean_hz':right['mean'],'right_sd_hz':right['sd'],'right_min_hz':right['min'],'right_max_hz':right['max'],
                       'left_right_pearson':correlation,'control_trials':len(control),'ratio_left':ratio if target else None,
                       'left_le_80_percent':('yes' if ratio<=.8 else 'no') if target and ratio is not None else 'undefined' if target and complete and not control_left else 'incomplete' if target else ''})
    return result


def plot(rows,out,mode):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if mode=='individuality':
        controls=[r for r in rows if not r[1]]
        if not controls: return None
        freqs=sorted(set(r[0] for r in controls));freq=max(freqs,key=lambda x:sum(r[0]==x for r in controls))
        subset=sorted([r for r in controls if r[0]==freq],key=lambda x:x[2])
        fig,ax=plt.subplots(figsize=(8,3.6));ax.scatter([x[2]-.12 for x in subset],[x[3] for x in subset],s=18,label='левый MN9');ax.scatter([x[2]+.12 for x in subset],[x[4] for x in subset],s=18,label='правый MN9')
        ax.set(xlabel='seed (независимые повторы)',ylabel='Число спайков за 1 с',title=f'Контроль, {freq} Гц, n={len(subset)}');ax.legend();name='control_by_seed.png'
    else:
        available=[r for r in rows if r['role']!='control' and r['ratio_left'] is not None]
        if not available:return None
        freq=max(sorted(set(r['frequency_hz'] for r in available)),key=lambda f:sum(r['frequency_hz']==f for r in available))
        subset=[r for r in available if r['frequency_hz']==freq][:25]
        fig,ax=plt.subplots(figsize=(max(7,len(subset)*.48),4));ax.bar(range(len(subset)),[r['ratio_left']*100 for r in subset],color='#767e72');ax.axhline(80,color='#9a5848',linestyle='--',label='80% контроля')
        ax.set_xticks(range(len(subset)),[str(r['rank_200hz']) for r in subset]);ax.set(xlabel='Ранг нейрона в топ-200',ylabel='Левый MN9, % контроля',title=f'Полные серии, {freq} Гц (не более 25)');ax.legend();name='lesion_vs_control.png'
    fig.tight_layout();fig.savefig(out/name,dpi=140);plt.close(fig);return name


def analyze(source,out,top_folder=None,mode='lesions'):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    source=snapshot(source,out/'source_snapshot.sqlite3');meta,rows=read_checked(out/'source_snapshot.sqlite3')
    top=read_top(top_folder,meta) if top_folder else None
    groups=aggregate(meta,rows,top)
    raw=[{'frequency_hz':f,'target':t or 'control','seed':s,'left_count':l,'right_count':r,'wall_seconds':secs} for f,t,s,l,r,secs,_ in sorted(rows)]
    if mode=='individuality':
        raw=[r for r in raw if r['target']=='control'];groups=[r for r in groups if r['role']=='control']
    write_csv(out/'trials.csv',['frequency_hz','target','seed','left_count','right_count','wall_seconds'],raw)
    fields=['frequency_hz','target','role','rank_200hz','activity_200hz','trials','expected_trials','complete','left_mean_hz','left_sd_hz','left_min_hz','left_max_hz','right_mean_hz','right_sd_hz','right_min_hz','right_max_hz','left_right_pearson','control_trials','ratio_left','left_le_80_percent']
    write_csv(out/'conditions.csv',fields,groups)
    correlations=[]
    if mode=='lesions' and top:
        for freq in FREQS:
            eligible=[r for r in groups if r['frequency_hz']==freq and r['role']=='other' and r['ratio_left'] is not None]
            value=None
            if len(eligible)>=3:
                try: value=statistics.correlation([r['activity_200hz'] for r in eligible],[r['ratio_left'] for r in eligible])
                except statistics.StatisticsError: pass
            correlations.append({'frequency_hz':freq,'eligible_complete':len(eligible),'pearson_activity_vs_ratio':value})
        write_csv(out/'activity_vs_lesion.csv',['frequency_hz','eligible_complete','pearson_activity_vs_ratio'],correlations)
    files=['source_snapshot.sqlite3','trials.csv','conditions.csv']+(['activity_vs_lesion.csv'] if correlations else [])
    try:
        image=plot(rows if mode=='individuality' else groups,out,mode)
        if image: files.append(image)
    except ImportError: print('matplotlib не установлен; таблицы созданы без графика.',flush=True)
    report={'status':'ok','mode':mode,'source_database':str(source),'snapshot_sha256':digest(out/'source_snapshot.sqlite3'),
            'source_top_run':str(top_folder) if top_folder else None,'source_protocol':meta,
            'result':{'source_trials':len(rows),'included_trials':len(raw),'conditions':len(groups),'complete_conditions':sum(g['complete'] for g in groups)},
            'correlations':correlations,'files':files,
            'caveats':['Это согласованный снимок на момент чтения; текущий расчёт может идти дальше.',
                       'Отношение и порог выводятся только при полных 30 повторениях контроля и лезии для одной частоты.',
                       'Критерий на одной частоте не является итоговой классификацией по всем частотам.',
                       'Отбор 200 Гц не случайный; корреляции являются описательными и не доказывают причинность.',
                       'Одинаковый seed не доказывает идентичности входных спайковых времён.',
                       'Повторы являются псевдослучайными симуляциями одного коннектома, а не животными или устойчивыми индивидуальными фенотипами.']}
    atomic_json(out/'summary.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',required=True);p.add_argument('--top-run',default='');p.add_argument('--mode',choices=['lesions','individuality'],default='lesions');args=p.parse_args()
    out=Path(os.environ['FLY_RUN_DIR']);out.mkdir(parents=True,exist_ok=True)
    try:
        report=analyze(args.source,out,args.top_run or None,args.mode)
        print(f"Снимок проверен, повторов: {report['result']['source_trials']}. Отчёт: {out/'summary.json'}",flush=True);return 0
    except Exception as exc:
        atomic_json(out/'summary.json',{'status':'error','mode':args.mode,'error':f'{type(exc).__name__}: {exc}','files':[]})
        print(traceback.format_exc(),file=sys.stderr,flush=True);return 1

if __name__=='__main__': sys.exit(main())
