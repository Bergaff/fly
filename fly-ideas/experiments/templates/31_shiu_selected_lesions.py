"""Выборочные исходящие лезии v630: 10 клеток, 5 пар, группа из 10.

По умолчанию только план. Симуляция запускается исключительно явным --stage.
База полных лезий открывается только для согласованного снимка. Новая база
отдельная, транзакционная, с проверкой версий и контрольных сумм при resume.
"""
# Portions adapted from Drosophila_brain_model/model.py (MIT License).
# Copyright (c) 2023 Philip Shiu and Nico Spiller
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the conditions that this notice and permission
# notice are included in all copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR ITS USE.
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
import traceback

OVERVIEW_SHA='881b0a654be06ec4b6fb295d5a0247591a4b54083f0cd7ffbe3a0358659c6638'
FREQUENCY=50
SEEDS=list(range(30))


def overview():
    path=Path(__file__).parent/'30_shiu_lesion_overview.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=OVERVIEW_SHA:
        raise ValueError('Скрипт проверки базы изменён; безопасный запуск остановлен.')
    spec=importlib.util.spec_from_file_location('overview_reference',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def selection(meta,base):
    exclude=set(base.RIGHT)|set(base.MN9.values())
    eligible=[x for x in meta['candidates'] if x not in exclude]
    if len(eligible)<10: raise ValueError('В топ-200 менее 10 подходящих клеток вне GRN и MN9.')
    # Десять позиций равномерно по рангу подходящих клеток, от первой до последней.
    selected=[eligible[(i*(len(eligible)-1))//9] for i in range(10)]
    pairs=[selected[i:i+2] for i in range(0,10,2)]
    return selected,pairs


def conditions(selected,pairs):
    result=[['control',[]]]
    result += [['single:'+x,[x]] for x in selected]
    result += [['pair:'+str(i+1),pair] for i,pair in enumerate(pairs)]
    return result+[['group:all10',selected]]


def hash_row(key,seed,left,right,seconds,origin):
    payload=json.dumps([key,seed,left,right,float(seconds).hex(),origin],separators=(',',':'),ensure_ascii=True)
    return hashlib.sha256(payload.encode('ascii')).hexdigest()


def open_selected(out,protocol,prior):
    dest=out/'selected_lesions.sqlite3'
    if prior:
        source=Path(prior).resolve()/'selected_lesions.sqlite3'
        if not source.is_file() or source==dest.resolve(): raise ValueError('Выберите другую папку с selected_lesions.sqlite3.')
        with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=30) as old,sqlite3.connect(dest,timeout=30) as copy: old.backup(copy)
    db=sqlite3.connect(dest,timeout=30);db.execute('PRAGMA synchronous=FULL')
    try:
        if prior:
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok': raise ValueError('База выборочных лезий повреждена.')
            items=db.execute('SELECT value FROM metadata WHERE key=?',('protocol',)).fetchall()
            if len(items)!=1 or json.loads(items[0][0])!=protocol: raise ValueError('Протокол выборочных лезий не совпадает с исходным; продолжение запрещено.')
            known={k for k,_ in protocol['conditions']};seen=set()
            for key,seed,l,r,seconds,origin,checksum in db.execute('SELECT condition,seed,left_count,right_count,wall_seconds,origin,digest FROM trials'):
                if (key,seed) in seen or key not in known or seed not in SEEDS or type(l)!=int or type(r)!=int or not 0<=l<=10000 or not 0<=r<=10000 or not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<0 or origin not in ('original','selected') or checksum!=hash_row(key,seed,l,r,seconds,origin):
                    raise ValueError('Некорректный повтор в базе выборочных лезий.')
                seen.add((key,seed))
        else:
            db.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);CREATE TABLE trials(condition TEXT NOT NULL,seed INTEGER NOT NULL,left_count INTEGER NOT NULL,right_count INTEGER NOT NULL,wall_seconds REAL NOT NULL,origin TEXT NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(condition,seed));')
            db.execute('INSERT INTO metadata VALUES(?,?)',('protocol',json.dumps(protocol,ensure_ascii=False,sort_keys=True)));db.commit()
        return db
    except Exception:
        db.close();raise


def validate_simulation(meta,top_folder):
    import numpy as np
    import brian2 as b2
    lesion=overview().reference();top=lesion.load_top();base=top.base_module()
    conn=base.input_file('FLY_SHIU_CONNECTIONS','.parquet');neurons=base.input_file('FLY_SHIU_NEURONS','.csv')
    hashes={'connections':base.fingerprint(conn),'neurons':base.fingerprint(neurons)}
    if any(hashes[k]['git_blob_sha1']!=v for k,v in base.EXPECTED.items()): raise ValueError('Исходные файлы не совпадают с авторской v630.')
    if (hashes['connections']['sha256']!=meta['connection_sha256'] or hashes['neurons']['sha256']!=meta['neuron_sha256'] or
        meta['python']!=sys.version.split()[0] or meta['numpy']!=np.__version__ or meta['brian2']!=b2.__version__):
        raise ValueError('Данные, Python, NumPy или Brian2 не совпадают с сохранённым расчётом.')
    data=base.validate_inputs(conn,neurons,True)
    for k,p in [('connections',conn),('neurons',neurons)]:
        st=p.stat()
        if (st.st_size,st.st_mtime_ns)!=(hashes[k]['bytes'],hashes[k]['mtime_ns']): raise ValueError('Исходные данные изменились во время проверки.')
    candidates,_=lesion.validate_top(top,base,data,hashes,Path(top_folder))
    if candidates!=meta['candidates']: raise ValueError('Проверенный рейтинг не совпадает с базой.')
    return lesion,base,data


def run_trial(lesion,base,data,targets,seed):
    if len(targets)<=1: return lesion.trial(base,data,FREQUENCY,seed,targets[0] if targets else '')
    # Эквивалент одиночной лезии 28: обнуляем исходящие веса каждой клетки.
    weights=data['weights'].copy()
    for target in targets: weights[data['pre']==data['lookup'][target]]=0
    altered=dict(data);altered['weights']=weights
    return lesion.trial(base,altered,FREQUENCY,seed,'')


def import_original(db,rows,selected):
    existing={(k,s):(l,r) for k,s,l,r in db.execute('SELECT condition,seed,left_count,right_count FROM trials')}
    imported=0
    for f,target,seed,left,right,seconds,_ in rows:
        if f!=FREQUENCY or (target and target not in selected): continue
        key='single:'+target if target else 'control'
        if (key,seed) in existing:
            if existing[(key,seed)]!=(left,right): raise ValueError('Сохранённый повтор не совпадает с исходной базой. Объединение запрещено.')
            continue
        origin='original';db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(key,seed,left,right,seconds,origin,hash_row(key,seed,left,right,seconds,origin)));imported+=1
    db.commit();return imported


def export_results(view,out,db,protocol,top):
    rows=db.execute('SELECT condition,seed,left_count,right_count,wall_seconds,origin FROM trials ORDER BY condition,seed').fetchall()
    groups={}
    for key,seed,left,right,seconds,origin in rows: groups.setdefault(key,[]).append((seed,left,right,seconds,origin))
    ctrl=groups.get('control',[]);control=statistics.mean(x[1] for x in ctrl) if len(ctrl)==30 else None
    totals={};out_rows=[]
    for key,targets in protocol['conditions']:
        values=groups.get(key,[]);n=len(values);left=statistics.mean(x[1] for x in values) if n else None;right=statistics.mean(x[2] for x in values) if n else None
        totals[key]=left if n==30 else None
        ratio=left/control if n==30 and control not in (None,0) and key!='control' else None
        out_rows.append({'condition':key,'targets':'|'.join(targets),'trials':n,'expected':30,'complete':n==30,'left_mean_hz':left,'left_sd_hz':statistics.stdev(x[1] for x in values) if n>1 else None,'right_mean_hz':right,'right_sd_hz':statistics.stdev(x[2] for x in values) if n>1 else None,'control_n':len(ctrl),'ratio_left':ratio,
                         'left_le_80_percent':'' if key=='control' else ('yes' if ratio<=.8 else 'no') if ratio is not None else 'undefined' if n==30 and control==0 else 'incomplete'})
    interactions=[]
    for i,pair in enumerate(protocol['pairs']):
        v=[totals.get('control'),totals.get('single:'+pair[0]),totals.get('single:'+pair[1]),totals.get('pair:'+str(i+1))]
        interactions.append({'pair':i+1,'target_a':pair[0],'target_b':pair[1],'interaction_hz':v[3]-v[1]-v[2]+v[0] if all(x is not None for x in v) else None,
                             'status':'complete' if all(x is not None for x in v) else 'incomplete'})
    view.write_csv(out/'selected_trials.csv',['condition','seed','left_count','right_count','wall_seconds','origin'],[dict(zip(['condition','seed','left_count','right_count','wall_seconds','origin'],r)) for r in rows])
    view.write_csv(out/'selected_conditions.csv',['condition','targets','trials','expected','complete','left_mean_hz','left_sd_hz','right_mean_hz','right_sd_hz','control_n','ratio_left','left_le_80_percent'],out_rows)
    view.write_csv(out/'pair_interactions.csv',['pair','target_a','target_b','interaction_hz','status'],interactions)
    points=[]
    for item in out_rows:
        if item['condition'].startswith('single:') and item['ratio_left'] is not None:
            target=item['targets'];points.append({'target':target,'rank_200hz':top[target]['rank'],'activity_200hz':top[target]['rate'],'ratio_left':item['ratio_left']})
    correlation=None
    if len(points)>=3:
        try: correlation=statistics.correlation([p['activity_200hz'] for p in points],[p['ratio_left'] for p in points])
        except statistics.StatisticsError: pass
    view.write_csv(out/'selected_activity.csv',['target','rank_200hz','activity_200hz','ratio_left'],points)
    images=[]
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        if points:
            fig,ax=plt.subplots(figsize=(6,4))
            ax.scatter([p['activity_200hz'] for p in points],[p['ratio_left']*100 for p in points],color='#65766c')
            for p in points: ax.annotate(str(p['rank_200hz']),(p['activity_200hz'],p['ratio_left']*100),fontsize=8)
            ax.axhline(80,color='#9a5848',linestyle='--');ax.set(xlabel='Активность при 200 Гц, Гц',ylabel='Левый MN9 при лезии, % контроля',title='Выборочные полные серии при 50 Гц')
            fig.tight_layout();fig.savefig(out/'selected_activity.png',dpi=140);plt.close(fig);images.append('selected_activity.png')
        complete_pairs=[x for x in interactions if x['status']=='complete']
        if complete_pairs:
            fig,ax=plt.subplots(figsize=(6,4));ax.bar([str(x['pair']) for x in complete_pairs],[x['interaction_hz'] for x in complete_pairs],color='#767e72');ax.axhline(0,color='#555555')
            ax.set(xlabel='Номер пары',ylabel='Неаддитивность ответа MN9, Гц',title='Парные лезии: модельное взаимодействие')
            fig.tight_layout();fig.savefig(out/'pair_interactions.png',dpi=140);plt.close(fig);images.append('pair_interactions.png')
    except Exception as exc: print(f'Таблицы сохранены; график недоступен: {exc}',flush=True)
    return {'completed':len(rows),'full_plan':len(protocol['conditions'])*30,'complete_conditions':sum(x['complete'] for x in out_rows),'activity_pairs':len(points),'activity_ratio_pearson':correlation,'images':images}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True);p.add_argument('--top-run',required=True)
    p.add_argument('--stage',choices=['plan','singles','all','review'],default='plan');p.add_argument('--resume-from',default='')
    args=p.parse_args();out=Path(os.environ['FLY_RUN_DIR']);out.mkdir(parents=True,exist_ok=True);view=overview();db=None
    try:
        if args.stage=='review' and not args.resume_from: raise ValueError('Для обзора нужна папка предыдущего выборочного расчёта.')
        print('Создаём согласованный снимок исходной базы...',flush=True)
        source=view.snapshot(args.source,out/'lesions_snapshot.sqlite3');meta,rows=view.read_checked(out/'lesions_snapshot.sqlite3');top=view.read_top(args.top_run,meta)
        base=view.reference().load_top().base_module();selected,pairs=selection(meta,base);plan=conditions(selected,pairs)
        protocol={'schema':1,'source_protocol':meta,'selection_rule':'10 evenly spaced positions among top200 excluding stimulated RIGHT and both MN9; floor(i*(N-1)/9)',
                  'selected':selected,'pairs':pairs,'conditions':plan,'frequency_hz':FREQUENCY,'seeds':SEEDS,
                  'script_sha256':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),'overview_sha256':OVERVIEW_SHA}
        view.write_csv(out/'selection.csv',['selection','root_id','rank_200hz','activity_200hz'],[{'selection':i+1,'root_id':x,'rank_200hz':top[x]['rank'],'activity_200hz':top[x]['rate']} for i,x in enumerate(selected)])
        report={'status':'pending','mode':args.stage,'source_database':str(source),'source_snapshot_sha256':view.digest(out/'lesions_snapshot.sqlite3'),'protocol':protocol,
                'caveats':['Выборка детерминированная и не случайна по мозгу; ранжирование выполнено при 200 Гц, лезии при 50 Гц.',
                'Пары соседствуют в этой выборке по рангу, а не по доказанной анатомической связи.',
                'Групповая лезия обнуляет выходы десяти клеток и не отключает их входы или собственные спайки.',
                'Парное взаимодействие = MN9(AB) - MN9(A) - MN9(B) + MN9(control), Гц; не является доказательством биологической компенсации.',
                'Seed не доказывает совпадения входных времён, симуляции не являются животными.',
                'Одна частота и одна выборка не заменяют полный план; топ-200 отобран по активности, а не случайно.'],
                'files':['lesions_snapshot.sqlite3','selection.csv']}
        if args.stage=='plan':
            existing={(f,t,s) for f,t,s,*_ in rows}
            reusable=sum((FREQUENCY,t,s) in existing for t in ['']+selected for s in SEEDS)
            report.update(status='plan_ready',result={'conditions':len(plan),'total_repeats':len(plan)*30,'original_reusable':reusable,'singles_plan':11*30,'pair_and_group_extra':6*30,'selected':selected,'pairs':pairs})
            view.atomic_json(out/'summary.json',report)
            print('План подготовлен. Симуляции не запускались.',flush=True);return 0
        db=open_selected(out,protocol,args.resume_from)
        imported=import_original(db,rows,selected)
        if args.stage in ('singles','all'):
            lesion,base,data=validate_simulation(meta,args.top_run)
            wanted=plan[:11] if args.stage=='singles' else plan
            have={(k,s) for k,s in db.execute('SELECT condition,seed FROM trials')}
            done=sum((k,s) in have for k,_ in wanted for s in SEEDS);total=len(wanted)*30
            print(f'План этапа: {total}; сохранено: {done}; импортировано из исходной базы: {imported}.',flush=True)
            for key,targets in wanted:
                for seed in SEEDS:
                    if (key,seed) in have: continue
                    print(f'{done+1}/{total}: {key}, seed {seed}',flush=True)
                    left,right,seconds=run_trial(lesion,base,data,targets,seed);origin='selected'
                    db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(key,seed,left,right,seconds,origin,hash_row(key,seed,left,right,seconds,origin)));db.commit()
                    done+=1;have.add((key,seed));view.atomic_json(out/'progress.json',{'stage':args.stage,'completed':done,'total':total,'last':{'condition':key,'seed':seed}})
        results=export_results(view,out,db,protocol,top)
        report.update(status='ok',result={**results,'imported_original':imported},files=report['files']+['selected_lesions.sqlite3','selected_trials.csv','selected_conditions.csv','pair_interactions.csv','selected_activity.csv']+results['images']+(['progress.json'] if (out/'progress.json').exists() else []))
        view.atomic_json(out/'summary.json',report);print('Готово: '+str(out/'summary.json'),flush=True);return 0
    except Exception as exc:
        view.atomic_json(out/'summary.json',{'status':'error','mode':args.stage,'error':f'{type(exc).__name__}: {exc}','files':[x for x in ('lesions_snapshot.sqlite3','selected_lesions.sqlite3','progress.json','selection.csv') if (out/x).exists()]})
        print(traceback.format_exc(),file=sys.stderr,flush=True);return 1
    finally:
        if db is not None: db.close()

if __name__=='__main__': sys.exit(main())
