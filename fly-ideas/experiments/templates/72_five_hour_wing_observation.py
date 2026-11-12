#!/usr/bin/env python3
"""Long supervised wing study: 4/8 hours, separate test inputs, SQLite resume.

Fixture mode is explicitly limited to 2–8 candidates and is not a long study.
The model uses teacher angles and artificial cameras, not biological neurons.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import csv
from datetime import datetime
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import multiprocessing
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sys
import time
import uuid
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
import numpy as np

HERE = Path(__file__).resolve().parent
PIN = {
    '55_user_wing_resume_prototype.py': '81e491eb489c46b4729440763ebb2f1590b532bc31fd438917206cdfabd8148e',
    '56_user_wing_evaluation.py': 'b4378b1ed9b63a5ebf863915dd67fbdc1a9252bd34691a9fdc255a8002bd84f5',
    '57_user_wing_preflight.py': '9395171ff29f134ddfe1c9afa84049b817f9658d203253edfd08a645556f0b2e',
    '58_user_wing_integrated_prototype.py': 'bcde7eafeff57831d908f8a002e3559e4be21f6701331fe8f792dd2ca2c540b7',
}
AXES = ('left_x','left_y','left_z','right_x','right_y','right_z')
MIN_RAM = 4*1024**3
MIN_DISK = 2*1024**3
ROOT = Path('workspace/runs/ideas/i-observational/wing-user-five-hour')
BASELINE_ROOT = Path('workspace/runs/ideas/i-observational/wing-studio-user-learning')


def sha(data): return hashlib.sha256(data).hexdigest()
def file_sha(path): return sha(Path(path).read_bytes())
def load(filename, name):
    path=HERE/filename
    if file_sha(path)!=PIN[filename]: raise ValueError(f'Закреплённый файл {filename} изменился.')
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def dependencies():
    proto=load('55_user_wing_resume_prototype.py','long_proto')
    ev=load('56_user_wing_evaluation.py','long_eval')
    pre=load('57_user_wing_preflight.py','long_preflight')
    stim,ck,base,large=proto.modules()
    return proto,ev,pre,stim,ck,base,large


def protocol(source_sha, labels, hours, fixture_limit, proto):
    if hours != 5 or type(hours)!=int: raise ValueError('Серия 72 имеет ровно 5 часов активного обучения.')
    if fixture_limit is not None and (type(fixture_limit)!=int or not 2<=fixture_limit<=8):
        raise ValueError('Техническая проба ограничена 2–8 кандидатами.')
    return {'schema':'five-hour-wing-observation-v1','mode':'fixture' if fixture_limit is not None else 'long',
            'budget_seconds':hours*3600,'fixture_limit':fixture_limit,'workers':2,'batch':2,
            'script_sha256':file_sha(__file__),'dependencies':{**proto.PIN,**PIN},
            'python':platform.python_version(),
            'versions':{p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},
            'source_sha256':source_sha,'labels':labels}


def verify_pins(proto, saved):
    if file_sha(__file__)!=saved['script_sha256']: raise ValueError('Скрипт серии изменён; продолжение остановлено.')
    for name, expected in {**proto.PIN,**PIN}.items():
        if file_sha(HERE/name)!=expected: raise ValueError(f'Скрипт {name} изменён; партия не сохранена.')


def free_check(large, folder, fixture):
    if fixture: return  # Only the explicitly marked, 2–8-candidate developer fixture.
    ram=large.available_ram()
    if ram is None: raise OSError('Не удалось измерить свободную RAM. Расчёт не продолжен.')
    if ram<MIN_RAM: raise MemoryError(f'Свободно {ram/1024**3:.2f} ГиБ RAM, нужно не менее 4 ГиБ. Последняя партия сохранена.')
    free=shutil.disk_usage(folder).free
    if free<MIN_DISK: raise OSError(f'Свободно {free/1024**3:.2f} ГиБ на диске, нужно не менее 2 ГиБ. Последняя партия сохранена.')


WORKER=None
def worker_init(train, hold):
    global WORKER
    WORKER=load('55_user_wing_resume_prototype.py','long_worker_proto')
    WORKER.worker_init(train, hold)
def worker_generate(ident): return WORKER.generate(ident)


def get_phase(dbpath):
    with sqlite3.connect(Path(dbpath).resolve().as_uri()+'?mode=ro',uri=True,timeout=30) as db:
        rows=db.execute('SELECT stage,training_seconds FROM run_phase WHERE id=1').fetchall()
        count=db.execute('SELECT COUNT(*) FROM run_phase').fetchone()[0]
    if len(rows)!=1 or count!=1 or rows[0][0] not in ('training','evaluation','completed'):
        raise ValueError('Повреждён этап расчёта.')
    seconds=rows[0][1]
    if not isinstance(seconds,(int,float)) or not np.isfinite(seconds) or seconds<0: raise ValueError('Повреждено активное время.')
    return rows[0][0],float(seconds)


def set_phase(dbpath, old, new, seconds):
    with sqlite3.connect(dbpath,timeout=30) as db:
        db.execute('PRAGMA synchronous=FULL')
        changed=db.execute('UPDATE run_phase SET stage=?,training_seconds=? WHERE id=1 AND stage=?',(new,float(seconds),old)).rowcount
        if changed!=1: raise ValueError('Этап расчёта изменился. Запись остановлена.')


def start(folder, previous, fresh, hours, fixture_limit=None, max_batches=None):
    proto,ev,pre,stim,ck,base,large=dependencies()
    if max_batches is not None and (fixture_limit is None or type(max_batches)!=int or not 1<=max_batches<=4):
        raise ValueError('Ограничение партий доступно только техническому тесту.')
    snap=pre.prepare(previous,fresh)
    proto.split_from_sources(snap['sources'],stim)
    saved=protocol(snap['source_sha256'],snap['labels'],hours,fixture_limit,proto)
    folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True)
    free_check(large,folder.parent,fixture_limit is not None)
    folder.mkdir(exist_ok=False)
    ck.create(folder/'study.sqlite3',saved,snap['sources'])
    with sqlite3.connect(folder/'study.sqlite3') as db:
        db.execute('PRAGMA synchronous=FULL')
        db.execute("CREATE TABLE run_phase (id INTEGER PRIMARY KEY CHECK(id=1), stage TEXT NOT NULL, training_seconds REAL NOT NULL)")
        db.execute("INSERT INTO run_phase VALUES (1,'training',0)")
    print('Папка новой серии:',folder.resolve(),flush=True)
    process(folder,max_batches)


def saved_state(dbpath, proto, ck):
    with sqlite3.connect(Path(dbpath).resolve().as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()
    if not row: raise ValueError('Не найден протокол серии.')
    saved=json.loads(row[0]);budget=saved.get('budget_seconds');limit=saved.get('fixture_limit')
    if budget != 18000 or saved.get('mode')!=('fixture' if limit is not None else 'long'):
        raise ValueError('Неверный протокол серии.')
    expected=protocol(saved.get('source_sha256'),saved.get('labels'),budget//3600,limit,proto)
    state=ck.open_verified(dbpath,expected)
    stage,phase_seconds=get_phase(dbpath)
    if stage=='training' and phase_seconds!=0: raise ValueError('Неверное время незавершённого обучения.')
    if stage!='training' and phase_seconds<state['elapsed']: raise ValueError('Время этапов не согласовано.')
    if stage!='training' and saved['mode']=='long' and phase_seconds<budget: raise ValueError('Обучение завершилось раньше протокола.')
    if stage!='training' and saved['mode']=='fixture' and state['next_id']!=limit: raise ValueError('Неверный предел технической пробы.')
    return saved,state,stage,phase_seconds


def sampled_records(dbpath, train_count):
    # IDs only are held in RAM; load at most 128 full records.
    with sqlite3.connect(Path(dbpath).resolve().as_uri()+'?mode=ro',uri=True) as db:
        ids=[r[0] for r in db.execute("SELECT id FROM candidates WHERE status='accepted' ORDER BY id")]
        originals=[i for i in ids if i<train_count]; other=[i for i in ids if i>=train_count]
        n=min(len(other),128-len(originals))
        chosen=originals+(other if n==len(other) else [other[i] for i in np.linspace(0,len(other)-1,n,dtype=int)])
        if not chosen: raise ValueError('Нет принятых движений.')
        marks=','.join('?' for _ in chosen)
        rows=db.execute(f'SELECT id,status,spec,motion_sha256 FROM candidates WHERE id IN ({marks}) ORDER BY id',chosen).fetchall()
    return len(ids),[{'id':i,'status':status,'spec':json.loads(spec),'motion_sha256':motion} for i,status,spec,motion in rows]


def save_json(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def output_manifest(folder):
    return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}


def prepared_holdouts():
    """Create the fixed five-movement battery before training; never overwrite it."""
    folder=ROOT/'prepared_holdouts_seed_7202';folder.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(7202);paths=[]
    for i in range(1,6):
        path=folder/f'holdout_{70+i:03d}.json'
        obj={'schema':'fly-wings-trajectory-v1','fps':25,'duration_s':2,
             'keyframes':[{'t':j*.5,'angles_deg':rng.integers(-45,46,size=6).astype(int).tolist()} for j in range(5)]}
        raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode('utf8')
        if path.exists() and path.read_bytes()!=raw:raise ValueError(f'Закреплённый holdout изменён: {path}')
        if not path.exists():path.write_bytes(raw)
        paths.append(str(path.resolve()))
    return paths


def verify_result(out, saved, state):
    marker=Path(out)/'complete.json'
    if not marker.is_file() or marker.stat().st_size>1024*1024: raise ValueError('Папка результата неполная; она не перезаписывается.')
    complete=json.loads(marker.read_text(encoding='utf-8-sig'))
    expected_protocol=sha(json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8'))
    if complete.get('protocol_sha256')!=expected_protocol or complete.get('candidates')!=state['next_id']:
        raise ValueError('Результат не соответствует контрольной точке.')
    hashes=complete.get('files')
    if not isinstance(hashes,dict) or output_manifest(Path(out))!=hashes: raise ValueError('Контрольные суммы результата не совпадают.')
    return complete


def evaluate(folder,state,saved,elapsed,proto,ev,stim,base,large):
    folder=Path(folder);out=folder/'result'
    if out.exists():
        verify_result(out,saved,state)
        return out
    train,tests=proto.split_from_sources(state['sources'],stim)
    labels={x['copy']:x for x in saved['labels']}
    with np.load(io.BytesIO(state['sources']['baseline_model.npz']),allow_pickle=False) as model:
        old=ev.checked_model({k:model[k] for k in model.files})
    mean,scale,intercept,weights=base.fit(state['stats'])
    new=ev.checked_model({'mean':mean,'scale':scale,'intercept':intercept,'weights':weights})
    studio=proto.load('long_studio','50_two_flies_wing_studio_pilot.py')
    engine=proto.load('long_engine','38_two_flies_observation.py')
    pilot=proto.load('long_pilot','47_two_flies_imitation_learning.py')
    scene=studio.Scene(engine)
    accepted,records=sampled_records(folder/'study.sqlite3',len(train))
    audit=ev.overlap_sample(stim,train,tests,records,cap=128)
    audit['accepted_total']=accepted;audit['is_exhaustive']=audit['audited_count']==accepted
    temp=folder/('evaluation_incomplete_'+uuid.uuid4().hex);temp.mkdir()
    np.savez_compressed(temp/'model_new.npz',**new)
    summary=[]
    for item,overlap in zip(tests,audit['tests']):
        free_check(large,folder,saved['mode']=='fixture')
        ident=item['id'];name=f'test_{ident:03d}.json';label=labels[name]
        obj=json.loads(state['sources'][name].decode('utf-8-sig'))
        truth=item['angles_deg']*np.pi/180;images=scene.render(truth)
        compared=ev.compare_models(images,truth,old,new);newpred=compared['predictions']['new']
        td=temp/f'test_{ident:03d}';td.mkdir()
        with (td/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['time_s']+[f'teacher_{a}_rad' for a in AXES]+
                [f'{model}_{a}_rad' for model in ('old','new','zero','training_mean') for a in AXES])
            for k,t in enumerate(item['times'][2:]):
                w.writerow([float(t),*map(float,compared['teacher_rad'][k]),
                            *(float(v) for model in ('old','new','zero','training_mean') for v in compared['predictions'][model][k])])
        raw=ev.feature_history(images)
        base.save_views(td,images,item['times'],pilot,raw,(raw-mean)/scale)
        scores=base.scores(truth[2:],newpred,intercept)
        playback={'schema':'fly-wings-result-v1','fps':25,'duration_s':obj['duration_s'],'trajectory':obj,
                  'samples':[{'t':float(t),'teacher_deg':list(map(float,degrees)),
                              'prediction_deg':None if k<2 else list(map(float,newpred[k-2]*180/np.pi))}
                             for k,(t,degrees) in enumerate(zip(item['times'],item['angles_deg']))],
                  'method':'supervised ridge; predictions recorded during observation, then replayed',
                  'user_metrics':scores,'holdout_metrics':scores,'holdout_label':'Эта проверочная траектория',
                  'limitations':['Искусственные глаза и кинематика, не биологическое зрение.',
                                 'Playback воспроизводит записанные прогнозы, не автономную генерацию.']}
        save_json(td/'playback.json',playback)
        result={'test_id':ident,'role':label['role'],'frames':len(truth)-2,'metrics':compared['metrics'],
                'overlap_under_0_001_deg':overlap['under_0_001_deg'],
                'overlap_under_1_deg':overlap['under_1_deg'],'overlap_under_5_deg':overlap['under_5_deg']}
        save_json(td/'metrics.json',result);summary.append(result)
        print(f'Проверено движение {ident}/{len(tests)}.',flush=True)
    status='fixture_completed' if saved['mode']=='fixture' else 'completed'
    report={'status':status,'protocol_mode':saved['mode'],'active_training_seconds':elapsed,
            'candidates':state['next_id'],'accepted_candidates':accepted,'training_frames':state['stats']['n'],
            'baseline_model_sha256':sha(state['sources']['baseline_model.npz']),
            'new_model_sha256':file_sha(temp/'model_new.npz'),
            'audit':{'accepted_total':accepted,'audited_count':audit['audited_count'],
                     'is_exhaustive':audit['is_exhaustive'],'sample_ids':audit['sample_ids']},'tests':summary,
            'limitations':['Учительские углы используются при обучении; это supervised ridge, не обучение нейронов.',
                           'Искусственные глаза и кинематическая сцена, не реальная муха или её мозг.',
                           'Прежний тест регрессионный; новый выбран пользователем и может быть похож на обучение.',
                           'Выборочный аудит сравнивает только углы, не зрительные входы; он может пропустить совпадение.',
                           'Playback записывает предсказания во время показа, а не автономно создаёт движение.']}
    save_json(temp/'summary.json',report)
    lines=['ДЛИТЕЛЬНОЕ ОБУЧЕНИЕ НА ТРАЕКТОРИЯХ КРЫЛЬЕВ',
           f'Режим: {status}; активное время обучения: {elapsed/3600:.4f} ч.',
           f'Кандидатов: {state["next_id"]}; принято: {accepted}; обучающих кадров: {state["stats"]["n"]}.',
           f'Проверка похожести углов: {audit["audited_count"]} из {accepted} принятых движений; полная: {audit["is_exhaustive"]}.',
           'RMSE, рад: старая модель / новая модель / ноль / средний угол обучения.']
    for item in summary:
        m=item['metrics']; lines.append(f'Тест {item["test_id"]} ({item["role"]}), кадров {item["frames"]}: '+ ' / '.join(f'{m[k]["rmse_rad"]:.6f}' for k in ('old','new','zero','training_mean')))
        for axis in AXES:
            lines.append('  '+axis+': '+' / '.join(f'{m[k]["axis_rmse_rad"][axis]:.6f}' for k in ('old','new','zero','training_mean')))
        lines.append(f'  Близкие угловые истории в выбранной выборке (<0,001° / <1° / <5°): {item["overlap_under_0_001_deg"]} / {item["overlap_under_1_deg"]} / {item["overlap_under_5_deg"]} из {item["frames"]} кадров.')
    lines+=['','Покадровые данные и playback.json находятся в папках test_001 и далее.',*report['limitations']]
    (temp/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    verify_pins(proto,saved)
    psha=sha(json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8'))
    save_json(temp/'complete.json',{'protocol_sha256':psha,'candidates':state['next_id'],'files':output_manifest(temp)})
    if out.exists(): raise ValueError('Результат уже существует; перезапись запрещена.')
    temp.rename(out)
    verify_result(out,saved,state)
    return out


def process(folder,max_batches=None):
    proto,ev,pre,stim,ck,base,large=dependencies()
    folder=Path(folder).resolve();dbpath=folder/'study.sqlite3'
    if not dbpath.is_file(): raise ValueError('В папке нет базы этой серии study.sqlite3.')
    large.job_guard()
    with large.RunLock(folder):
        saved,state,stage,seconds=saved_state(dbpath,proto,ck)
        if max_batches is not None and (saved['mode']!='fixture' or type(max_batches)!=int or not 1<=max_batches<=4):
            raise ValueError('Предел партий доступен только техническому тесту.')
        if stage=='completed':
            verify_result(folder/'result',saved,state);print('Серия уже завершена:',folder/'result',flush=True);return
        free_check(large,folder,saved['mode']=='fixture')
        train,tests=proto.split_from_sources(state['sources'],stim);hold={x['motion_sha256'] for x in tests}
        done=state['next_id'];stats=state['stats'];prior=state['elapsed'];batches=0;started=time.monotonic()
        print(f'Папка: {folder}\nСохранено {done} кандидатов, активное обучение {prior/3600:.3f} ч.',flush=True)
        if stage=='training':
            with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),
                                                        initializer=worker_init,initargs=(train,hold)) as pool:
                while True:
                    pause=folder/'pause.request'
                    if pause.exists():
                        try:pause.unlink()
                        except OSError as exc:print('Запрос паузы не удалён:',exc,flush=True)
                        print('Пауза: последняя партия сохранена. Продолжите через тот же BAT.',flush=True);return
                    current=prior+time.monotonic()-started
                    finished=(done>=saved['fixture_limit']) if saved['mode']=='fixture' else (current>=saved['budget_seconds'])
                    if finished:
                        if stats['n']<2: raise ValueError('Нет достаточных обучающих кадров.')
                        verify_pins(proto,saved);set_phase(dbpath,'training','evaluation',current)
                        seconds=current;stage='evaluation';break
                    if max_batches is not None and batches>=max_batches:
                        print('Техническая проба остановлена после сохранения партии.',flush=True);return
                    free_check(large,folder,saved['mode']=='fixture')
                    if done>=2**32-2: raise ValueError('Достигнут предел генератора кандидатов; расчёт остановлен.')
                    end=min(done+2,saved['fixture_limit']) if saved['mode']=='fixture' else done+2
                    ids=list(range(done,end));generated=list(pool.map(worker_generate,ids));records=[]
                    for ident,(rec,x,y) in zip(ids,generated):
                        expected,_=stim.candidate(train,ident)
                        if rec['id']!=ident or rec['spec']!=expected or rec['motion_sha256']!=expected['sampled_motion_sha256']:
                            raise ValueError('Кандидат не соответствует протоколу.')
                        rejected=rec['motion_sha256'] in hold
                        if rejected!=(rec['status']=='rejected'):raise ValueError('Ошибка блокировки проверочного движения.')
                        if not rejected:
                            if x is None or y is None or x.shape!=(rec['frames'],576) or y.shape!=(rec['frames'],6): raise ValueError('Неверная партия.')
                            base.update_stats(stats,x,y)
                        elif x is not None or y is not None: raise ValueError('Отклонённый кандидат передал кадры.')
                        records.append(rec)
                    verify_pins(proto,saved)
                    ck.commit_batch(dbpath,saved,done,records,stats,prior+time.monotonic()-started)
                    done+=len(ids);batches+=1
                    print(f'Сохранено {done} кандидатов; активное время {(prior+time.monotonic()-started)/3600:.3f}/{saved["budget_seconds"]/3600:.0f} ч.',flush=True)
        if stage=='evaluation':
            free_check(large,folder,saved['mode']=='fixture')
            state=ck.open_verified(dbpath,saved)
            print('Обучение закончено. Начинается отдельная проверка, она займёт дополнительное время.',flush=True)
            out=evaluate(folder,state,saved,seconds,proto,ev,stim,base,large)
            set_phase(dbpath,'evaluation','completed',seconds)
            print('Готово. Результат:',out,flush=True)
            if os.name=='nt':
                try:os.startfile(str(out))
                except OSError as exc:print('Не удалось открыть папку результата:',exc,flush=True)


def request_pause(folder):
    proto,ev,pre,stim,ck,base,large=dependencies();folder=Path(folder).resolve();dbpath=folder/'study.sqlite3'
    if not dbpath.is_file():raise ValueError('Не найдена база этой серии.')
    try:
        with large.RunLock(folder):pass
    except ValueError:pass
    else:raise ValueError('Серия сейчас не работает. Запрос паузы не записан.')
    stage,_=get_phase(dbpath)
    if stage!='training':raise ValueError('Обучение уже закончено; пауза во время проверки недоступна.')
    try:
        with (folder/'pause.request').open('x',encoding='utf-8') as f:f.write('pause\n')
    except FileExistsError:print('Пауза уже запрошена.',flush=True);return
    print('Запрос записан. Текущая партия завершится и сохранится. Если обучение уже закончилось, проверка может начаться.',flush=True)


def choose():
    import tkinter as tk
    from tkinter import filedialog,messagebox,simpledialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    def initial(path):return str(path.resolve()) if path.exists() else str(Path.cwd())
    try:
        action=simpledialog.askinteger('Серия 72: пять часов наблюдения','Ровно 5 часов активного обучения. Введите номер:\n1: начать новую серию\n2: продолжить серию\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
        if action is None:print('Выбор отменён.');return
        if action in (2,3):
            folder=filedialog.askdirectory(title='Выберите папку серии wing_user_five_hour_...',initialdir=initial(ROOT),parent=root)
            if not folder:print('Выбор отменён.');return
            if action==2:process(folder)
            else:request_pause(folder)
            return
        messagebox.showinfo('Предыдущая короткая проба','Выберите папку результата короткой пробы 51. В ней должны находиться metadata.json, model_six_axes.npz и папка input. Старые данные изменяться не будут.',parent=root)
        previous=filedialog.askdirectory(title='Папка результата предыдущей пробы user_wing_learning_...',initialdir=initial(BASELINE_ROOT),parent=root)
        if not previous:print('Выбор отменён.');return
        fresh=prepared_holdouts()
        messagebox.showinfo('Пять проверочных движений закреплены','Программа создала или проверила пять фиксированных движений 71–75 с seed 7202. Они копируются в новую серию до обучения; выбирать JSON вручную не нужно.',parent=root)
        answer=messagebox.askokcancel('Время обучения','Запустить ровно 5 часов активного обучения?\nПроверка пяти движений после обучения займёт дополнительное время.',parent=root)
        if not answer:print('Выбор отменён.');return
        hours=5
        messagebox.showinfo('Перед запуском','Используются 2 вычислительных процесса. Работа в Word может замедлиться. При свободной RAM меньше 4 ГиБ или месте на диске меньше 2 ГиБ расчёт остановится с сохранённой последней партией. Для паузы откройте этот BAT ещё раз и выберите 3.',parent=root)
        folder=ROOT/('wing_user_five_hour_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
        start(folder,previous,fresh,hours)
    finally:root.destroy()


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--choose',action='store_true');g.add_argument('--new');g.add_argument('--resume');g.add_argument('--pause')
    p.add_argument('--previous');p.add_argument('--fresh',nargs='+');p.add_argument('--hours',type=int,choices=(5,),default=5)
    p.add_argument('--fixture-limit',type=int,help=argparse.SUPPRESS);p.add_argument('--batches',type=int,help=argparse.SUPPRESS)
    a=p.parse_args()
    if a.choose:
        if a.previous or a.fresh or a.fixture_limit is not None or a.batches is not None:p.error('При выборе окна другие данные не указываются.')
        choose()
    elif a.new:
        if not a.previous or not a.fresh:p.error('Нужны --previous и --fresh.')
        start(a.new,a.previous,a.fresh,a.hours,a.fixture_limit,a.batches)
    elif a.pause:
        if a.previous or a.fresh or a.fixture_limit is not None or a.batches is not None:p.error('Для паузы нужна только папка серии.')
        request_pause(a.pause)
    else:
        if a.previous or a.fresh or a.fixture_limit is not None:p.error('Для продолжения используются сохранённые входы.')
        process(a.resume,a.batches)


if __name__=='__main__':
    multiprocessing.freeze_support()
    try:main()
    except Exception as exc:
        print(f'ОШИБКА: {type(exc).__name__}: {exc}\nПредыдущие результаты не изменялись. Если база серии создана, последняя сохранённая партия остаётся в ней.',file=sys.stderr,flush=True)
        sys.exit(1)
