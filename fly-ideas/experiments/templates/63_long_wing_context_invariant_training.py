#!/usr/bin/env python3
"""Series 63: paired control versus context-randomized wing training.

A completed series 59 supplies the frozen candidate plan and control sufficient
statistics. For a preregistered half of accepted generated candidates, this
runner replaces each original sample in a second model by a counterfactual
render: right_x is unchanged while five context axes come from a deterministic
training-only donor. The source series and holdout are never modified.
"""
from __future__ import annotations
import argparse,concurrent.futures,csv
from datetime import datetime,timezone
import hashlib,importlib.util,io,json,math,multiprocessing,os
from pathlib import Path
import shutil,sqlite3,sys,time,uuid
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER=HERE/'59_long_user_wing_learning.py'
RUNNER_SHA='5c700f4c72f3614c245ab34f2b7bf7f8469e3114cb46568556157a2b99e5ddcf'
ROOT=Path('workspace/runs/ideas/i-observational/wing-context-invariant')
SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/wing-user-long')
AXES=('left_x','left_y','left_z','right_x','right_y','right_z');TARGET=3;CONTEXT=(0,1,2,4,5)
DONOR_OFFSET=104729
MIN_RAM=4*1024**3;MIN_DISK=2*1024**3


def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def load_runner():
    if file_sha(RUNNER)!=RUNNER_SHA:raise ValueError('Закреплённый скрипт серии 59 изменился.')
    spec=importlib.util.spec_from_file_location('context_invariant_runner59',RUNNER);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def source_state(folder):
    runner=load_runner();proto,ev,pre,stim,ck,base,large=runner.dependencies();folder=Path(folder).resolve();db=folder/'study.sqlite3'
    saved,state,stage,seconds=runner.saved_state(db,proto,ck)
    if stage!='completed':raise ValueError('Нужна полностью завершённая серия 59.')
    runner.verify_result(folder/'result',saved,state)
    train,tests=proto.split_from_sources(state['sources'],stim)
    return runner,proto,ev,stim,ck,base,large,folder,db,saved,state,seconds,train,tests


def preregister(source,holdout_path,fixture_limit=None):
    runner,proto,ev,stim,ck,base,large,folder,db,saved,state,seconds,train,tests=source_state(source)
    holdout_path=Path(holdout_path)
    if not holdout_path.is_file() or holdout_path.stat().st_size>1024*1024:raise ValueError('Новый holdout отсутствует или слишком велик.')
    raw=holdout_path.read_bytes();obj=json.loads(raw.decode('utf-8-sig'));times,angles=stim.sample_trajectory(obj);motion=stim.motion_hash(angles)
    existing={item['motion_sha256'] for item in train+tests}
    if motion in existing:raise ValueError('Новый holdout полностью совпадает с уже использованным движением.')
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as conn:
        rows=conn.execute("SELECT id FROM candidates WHERE status='accepted' AND id>=? AND ((id-?) % 2)=1 ORDER BY id",(len(train),len(train))).fetchall()
    selected=[r[0] for r in rows]
    if not selected:raise ValueError('В серии 59 нет кандидатов для закреплённой половины замен.')
    if fixture_limit is not None:
        if type(fixture_limit)!=int or not 1<=fixture_limit<=min(8,len(selected)):raise ValueError('Fixture допускает 1–8 замен.')
        selected=selected[:fixture_limit]
    protocol={'schema':'wing-context-invariant-v1','mode':'fixture' if fixture_limit is not None else 'full',
      'script_sha256':file_sha(__file__),'runner59_sha256':RUNNER_SHA,'source_series':str(folder),
      'source_database_sha256':file_sha(db),'source_protocol_sha256':sha(canonical(saved).encode()),
      'source_candidates':state['next_id'],'source_training_frames':state['stats']['n'],'source_active_training_seconds':seconds,
      'train_count':len(train),'replacement_rule':'accepted generated candidates with (id-train_count)%2 == 1',
      'replacement_count':len(selected),'fixture_limit':fixture_limit,'donor_offset':DONOR_OFFSET,
      'target_axis':'right_x','context_axes':[AXES[i] for i in CONTEXT],'holdout_sha256':sha(raw),
      'holdout_motion_sha256':motion,'holdout_basename':holdout_path.name,'primary_metric':'right_x RMSE on every scored holdout frame',
      'secondary_metrics':['right_x MAE','right_x mean error','opposite-sign frames','fixed amplitude-bin RMSE'],
      'amplitude_bins_deg':[0,10,25,60],'workers':2}
    return protocol,raw,state['stats'],selected


def create(folder,protocol,holdout,control_stats,ck):
    folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir(exist_ok=False);db=folder/'study.sqlite3'
    blob=ck.pack_stats(control_stats);text=canonical(protocol)
    with sqlite3.connect(db) as conn:
        conn.execute('PRAGMA journal_mode=DELETE');conn.execute('PRAGMA synchronous=FULL')
        conn.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
        conn.execute('CREATE TABLE sources (name TEXT PRIMARY KEY,payload BLOB NOT NULL,sha256 TEXT NOT NULL)')
        conn.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1),next_index INTEGER NOT NULL,elapsed REAL NOT NULL,stats BLOB NOT NULL,stats_sha256 TEXT NOT NULL,stage TEXT NOT NULL)')
        conn.execute('CREATE TABLE replacements (position INTEGER PRIMARY KEY,candidate_id INTEGER UNIQUE NOT NULL,donor_id INTEGER NOT NULL,original_rgb_sha256 TEXT NOT NULL,counterfactual_rgb_sha256 TEXT NOT NULL,counterfactual_motion_sha256 TEXT NOT NULL)')
        conn.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','wing-context-invariant-checkpoint-v1'),('protocol',text),('protocol_sha256',sha(text.encode()))])
        conn.execute('INSERT INTO sources VALUES (?,?,?)',('holdout.json',holdout,sha(holdout)))
        conn.execute("INSERT INTO state VALUES (1,0,0,?,?, 'training')",(blob,sha(blob)))
    return db


def read_state(folder,ck):
    folder=Path(folder).resolve();db=folder/'study.sqlite3'
    if not db.is_file():raise ValueError('Не найдена база серии 63.')
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as conn:
        if conn.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError('SQLite не прошла quick_check.')
        meta=dict(conn.execute('SELECT key,value FROM metadata').fetchall());row=conn.execute('SELECT next_index,elapsed,stats,stats_sha256,stage FROM state WHERE id=1').fetchone()
        source=conn.execute("SELECT payload,sha256 FROM sources WHERE name='holdout.json'").fetchone();count=conn.execute('SELECT COUNT(*) FROM replacements').fetchone()[0]
    if set(meta)!={'schema','protocol','protocol_sha256'} or meta['schema']!='wing-context-invariant-checkpoint-v1' or sha(meta['protocol'].encode())!=meta['protocol_sha256']:raise ValueError('Повреждён протокол серии 63.')
    protocol=json.loads(meta['protocol']);expected={**protocol,'script_sha256':file_sha(__file__),'runner59_sha256':RUNNER_SHA}
    if canonical(expected)!=meta['protocol']:raise ValueError('Скрипт или протокол серии 63 изменился.')
    if not row or row[4] not in ('training','evaluation','completed') or row[0]!=count or not 0<=row[0]<=protocol['replacement_count'] or not math.isfinite(row[1]) or row[1]<0:raise ValueError('Повреждено состояние серии 63.')
    if not source or sha(source[0])!=source[1] or source[1]!=protocol['holdout_sha256']:raise ValueError('SHA закреплённого holdout не совпадает.')
    stats=ck.unpack_stats(row[2],row[3]);return folder,db,protocol,bytes(source[0]),{'next_index':row[0],'elapsed':row[1],'stats':stats,'stage':row[4]}


def free_check(large,folder,fixture):
    if fixture:return
    ram=large.available_ram()
    if ram is None:raise OSError('Не удалось измерить свободную RAM.')
    if ram<MIN_RAM:raise MemoryError(f'Свободно {ram/1024**3:.2f} ГиБ RAM, нужно не менее 4 ГиБ. Последняя партия сохранена.')
    if shutil.disk_usage(folder).free<MIN_DISK:raise OSError('Свободно менее 2 ГиБ на диске. Последняя партия сохранена.')


def donor_context(recipient,donor):
    a=np.asarray(recipient,dtype=float);b=np.asarray(donor,dtype=float)
    if a.ndim!=2 or b.ndim!=2 or a.shape[1]!=6 or b.shape[1]!=6 or len(a)<3 or len(b)<3:raise ValueError('Некорректные движения для контрфакта.')
    out=a.copy();ua=np.linspace(0,1,len(a));ub=np.linspace(0,1,len(b))
    for axis in CONTEXT:out[:,axis]=np.interp(ua,ub,b[:,axis])
    if not np.array_equal(out[:,TARGET],a[:,TARGET]):raise AssertionError('Контрфакт изменил right_x.')
    return out


WORKER=None
def worker_init(train,blocked_motions):
    global WORKER
    runner=load_runner();proto,ev,pre,stim,ck,base,large=runner.dependencies();studio=proto.load('ci_worker_studio','50_two_flies_wing_studio_pilot.py');engine=proto.load('ci_worker_engine','38_two_flies_observation.py');pilot=proto.load('ci_worker_pilot','47_two_flies_imitation_learning.py')
    pilot.lower_priority();WORKER=(stim,base,studio.Scene(engine),pilot,train,set(blocked_motions))
def worker_replace(ident):
    stim,base,scene,pilot,train,blocked=WORKER
    spec,degrees=stim.candidate(train,ident);donor_id=ident+DONOR_OFFSET
    for _ in range(32):
        donor_spec,donor=stim.candidate(train,donor_id)
        if donor_spec['sampled_motion_sha256'] not in blocked:
            cf=donor_context(degrees,donor);cf_motion=stim.motion_hash(cf)
            if cf_motion not in blocked:break
        donor_id+=1
    else:raise ValueError('Не найден донор, отличный от проверочных движений.')
    original_images=scene.render(degrees*np.pi/180,distance=spec['distance'],offset=spec['side_offset']);cf_images=scene.render(cf*np.pi/180,distance=spec['distance'],offset=spec['side_offset'])
    x0=pilot.history(original_images);y0=degrees[2:]*np.pi/180;x1=pilot.history(cf_images);y1=cf[2:]*np.pi/180
    return {'candidate_id':ident,'donor_id':donor_id,'original_rgb_sha256':sha(original_images.tobytes()),'counterfactual_rgb_sha256':sha(cf_images.tobytes()),'counterfactual_motion_sha256':cf_motion},x0,y0,x1,y1


def apply_replace(stats,base,x0,y0,x1,y1):
    before=stats['n'];minus=base.empty_stats();base.update_stats(minus,x0,y0);plus=base.empty_stats();base.update_stats(plus,x1,y1)
    if minus['n']!=plus['n']:raise ValueError('Число кадров контрфакта изменилось.')
    for key in ('sx','sx2','sy','sxy','sxx'):stats[key]+=plus[key]-minus[key]
    if stats['n']!=before:raise AssertionError('Замена изменила число обучающих кадров.')


def commit_batch(db,protocol,expected,records,stats,elapsed,ck):
    blob=ck.pack_stats(stats)
    with sqlite3.connect(db,timeout=30) as conn:
        conn.execute('PRAGMA synchronous=FULL');current=conn.execute('SELECT next_index,elapsed,stage FROM state WHERE id=1').fetchone()
        if current[0]!=expected or current[2]!='training' or elapsed<current[1]:raise ValueError('Контрольная точка изменилась.')
        conn.executemany('INSERT INTO replacements VALUES (?,?,?,?,?,?)',[(expected+i,r['candidate_id'],r['donor_id'],r['original_rgb_sha256'],r['counterfactual_rgb_sha256'],r['counterfactual_motion_sha256']) for i,r in enumerate(records)])
        conn.execute('UPDATE state SET next_index=?,elapsed=?,stats=?,stats_sha256=? WHERE id=1',(expected+len(records),elapsed,blob,sha(blob)))


def selected_ids(source_db,train_count,limit):
    with sqlite3.connect(Path(source_db).resolve().as_uri()+'?mode=ro',uri=True) as conn:ids=[r[0] for r in conn.execute("SELECT id FROM candidates WHERE status='accepted' AND id>=? AND ((id-?) % 2)=1 ORDER BY id",(train_count,train_count))]
    return ids[:limit]


def axis_metrics(truth,pred):
    e=np.asarray(pred)-np.asarray(truth);truth=np.asarray(truth)
    return {'frames':len(e),'rmse_rad':float(np.sqrt(np.mean(e*e))),'mae_rad':float(np.mean(np.abs(e))),'mean_error_rad':float(np.mean(e)),
      'opposite_sign_frames':int(np.sum((pred*truth<0)&(truth!=0)))}
def binned_metrics(truth,pred):
    deg=np.abs(np.asarray(truth))*180/np.pi;edges=(0,10,25,60);out=[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        mask=(deg>=lo)&(deg<(hi+1e-12 if hi==60 else hi));out.append({'abs_target_deg':[lo,hi],'metrics':axis_metrics(np.asarray(truth)[mask],np.asarray(pred)[mask]) if np.any(mask) else None})
    return out


def model_from_stats(stats,base,ev):
    mean,scale,intercept,weights=base.fit(stats);return ev.checked_model({'mean':mean,'scale':scale,'intercept':intercept,'weights':weights})

def model_sha(model):
    mem=io.BytesIO();np.savez_compressed(mem,**model);return sha(mem.getvalue())


def evaluate(folder,protocol,holdout,state,source,runner,proto,ev,stim,ck,base,large,train,tests):
    out=folder/'result'
    if out.exists():
        complete=json.loads((out/'complete.json').read_text(encoding='utf-8'));files={str(p.relative_to(out)).replace('\\','/'):file_sha(p) for p in out.rglob('*') if p.is_file() and p.name!='complete.json'}
        if complete.get('files')!=files or complete.get('protocol_sha256')!=sha(canonical(protocol).encode()):raise ValueError('Контрольные суммы результата не совпадают.')
        return out
    control=model_from_stats(source[10]['stats'],base,ev);invariant=model_from_stats(state['stats'],base,ev)
    saved_new=source[7]/'result'/'model_new.npz'
    with np.load(saved_new,allow_pickle=False) as z:saved_model=ev.checked_model({k:z[k] for k in z.files})
    for key in control:
        if not np.allclose(control[key],saved_model[key],rtol=0,atol=1e-12):raise ValueError('Контрольная модель не воспроизвела модель серии 59.')
    studio=proto.load('ci_eval_studio','50_two_flies_wing_studio_pilot.py');engine=proto.load('ci_eval_engine','38_two_flies_observation.py');scene=studio.Scene(engine)
    hold_obj=json.loads(holdout.decode('utf-8-sig'));hold_times,hold_deg=stim.sample_trajectory(hold_obj)
    eval_items=[{'role':'preregistered_holdout','times':hold_times,'angles_deg':hold_deg,'source':'holdout.json'}]
    # Existing series 59 tests are diagnostic regression only and follow the primary holdout.
    eval_items.extend({'role':'diagnostic_regression','times':x['times'],'angles_deg':x['angles_deg'],'source':f'test_{x["id"]:03d}.json'} for x in tests)
    temp=folder/('evaluation_incomplete_'+uuid.uuid4().hex);temp.mkdir();np.savez_compressed(temp/'model_control.npz',**control);np.savez_compressed(temp/'model_context_invariant.npz',**invariant)
    summaries=[]
    for index,item in enumerate(eval_items):
        images=scene.render(item['angles_deg']*np.pi/180);features=ev.feature_history(images);truth=item['angles_deg'][2:]*np.pi/180
        pc=ev.predict(control,features);pi=ev.predict(invariant,features);t=truth[:,TARGET];c=pc[:,TARGET];v=pi[:,TARGET]
        result={'test_index':index,'role':item['role'],'source':item['source'],'frames':len(t),'right_x':{'control':axis_metrics(t,c),'context_invariant':axis_metrics(t,v)},
          'fixed_amplitude_bins':{'control':binned_metrics(t,c),'context_invariant':binned_metrics(t,v)}}
        result['right_x']['rmse_change_percent']=100*(result['right_x']['context_invariant']['rmse_rad']/result['right_x']['control']['rmse_rad']-1)
        summaries.append(result);td=temp/f'test_{index:03d}';td.mkdir()
        with (td/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'{m}_{a}_rad' for m in ('control','context_invariant') for a in AXES]])
            for k,tv in enumerate(item['times'][2:]):w.writerow([float(tv),*map(float,truth[k]),*map(float,pc[k]),*map(float,pi[k])])
        if index==0:
            for name,pred in (('control',pc),('context_invariant',pi)):
                playback={'schema':'fly-wings-result-v1','fps':25,'duration_s':hold_obj['duration_s'],'trajectory':hold_obj,
                  'samples':[{'t':float(tv),'teacher_deg':list(map(float,degrees)),'prediction_deg':None if k<2 else list(map(float,pred[k-2]*180/np.pi))} for k,(tv,degrees) in enumerate(zip(item['times'],item['angles_deg']))],
                  'method':f'series 63 supervised ridge: {name}; predictions recorded on preregistered holdout',
                  'limitations':['Буфер сохранённых прогнозов, не автономная генерация.','Условные камеры и кинематика, не биологическое зрение.']}
                save_json(td/f'playback-{name}.json',playback)
        save_json(td/'metrics.json',result)
    primary=summaries[0];report={'schema':'wing-context-invariant-result-v1','created_utc':datetime.now(timezone.utc).isoformat(),'status':'fixture_completed' if protocol['mode']=='fixture' else 'completed',
      'protocol':protocol,'control_model_sha256':file_sha(temp/'model_control.npz'),'context_invariant_model_sha256':file_sha(temp/'model_context_invariant.npz'),
      'replacements_completed':state['next_index'],'training_frames_each_model':state['stats']['n'],'primary':primary,'tests':summaries,
      'limitations':['Holdout создан пользователем и закреплён до вычисления прогнозов, но это не слепой биологический эксперимент.','Контекстные оси взяты из детерминированных обучающих доноров; полученные сочетания могут быть вне распределения.','Обе модели имеют одинаковые target-распределение и число кадров; они различаются контекстом закреплённой половины вариантов.','Основной вывод относится только к right_x на новом holdout; test_001/test_002 являются диагностическими регрессиями.','Supervised ridge, условные камеры и кинематика не доказывают зеркальные нейроны или автономное воспроизведение.']}
    save_json(temp/'summary.json',report)
    p=primary['right_x'];lines=['СЕРИЯ 63: КОНТЕКСТ-ИНВАРИАНТНОЕ ОБУЧЕНИЕ RIGHT_X','',f'Новый holdout SHA-256: {protocol["holdout_sha256"]}',f'Заменено обучающих движений: {state["next_index"]}; кадров в каждой модели: {state["stats"]["n"]}.',
      'Основная метрика заранее закреплена: RMSE right_x на всех кадрах нового holdout.',f'Контроль / контекст-инвариантная RMSE: {p["control"]["rmse_rad"]:.6f} / {p["context_invariant"]["rmse_rad"]:.6f} рад.',f'Изменение RMSE: {p["rmse_change_percent"]:+.2f}%.',
      f'MAE: {p["control"]["mae_rad"]:.6f} / {p["context_invariant"]["mae_rad"]:.6f} рад.',f'Неправильный знак: {p["control"]["opposite_sign_frames"]} / {p["context_invariant"]["opposite_sign_frames"]} из {p["control"]["frames"]}.','',
      'Существующие test_001/test_002 записаны только как диагностические регрессии.','Подробности: summary.json и test_000/predictions.csv.','',*report['limitations']]
    (temp/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    files={str(p.relative_to(temp)).replace('\\','/'):file_sha(p) for p in temp.rglob('*') if p.is_file()};save_json(temp/'complete.json',{'protocol_sha256':sha(canonical(protocol).encode()),'files':files})
    temp.rename(out);return out


def process(folder,max_batches=None):
    runner=load_runner();proto,ev,pre,stim,ck,base,large=runner.dependencies();folder,db,protocol,holdout,state=read_state(folder,ck)
    source=source_state(protocol['source_series']);source_db=source[8]
    if file_sha(source_db)!=protocol['source_database_sha256'] or sha(canonical(source[9]).encode())!=protocol['source_protocol_sha256'] or source[10]['next_id']!=protocol['source_candidates']:raise ValueError('Исходная серия 59 изменилась.')
    ids=selected_ids(source_db,protocol['train_count'],protocol['replacement_count']);fixture=protocol['mode']=='fixture'
    if len(ids)!=protocol['replacement_count']:raise ValueError('Закреплённый список замен изменился.')
    large.job_guard()
    with large.RunLock(folder):
        if state['stage']=='completed':
            evaluate(folder,protocol,holdout,state,source,runner,proto,ev,stim,ck,base,large,source[12],source[13])
            print('Серия уже завершена:',folder/'result',flush=True);return
        free_check(large,folder,fixture);start=time.monotonic();prior=state['elapsed'];done=state['next_index'];stats=state['stats'];batches=0
        if state['stage']=='training':
            blocked={item['motion_sha256'] for item in source[13]}|{protocol['holdout_motion_sha256']}
            with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(source[12],blocked)) as pool:
                while done<len(ids):
                    pause=folder/'pause.request'
                    if pause.exists():pause.unlink();print('Пауза: последняя партия сохранена.',flush=True);return
                    if max_batches is not None and batches>=max_batches:print('Fixture остановлена после партии.',flush=True);return
                    free_check(large,folder,fixture);batch_ids=ids[done:done+2];generated=list(pool.map(worker_replace,batch_ids));records=[]
                    with sqlite3.connect(source_db.resolve().as_uri()+'?mode=ro',uri=True) as conn:expected=dict(conn.execute(f"SELECT id,rgb_sha256 FROM candidates WHERE id IN ({','.join('?' for _ in batch_ids)})",batch_ids))
                    for ident,(rec,x0,y0,x1,y1) in zip(batch_ids,generated):
                        if rec['candidate_id']!=ident or rec['original_rgb_sha256']!=expected.get(ident):raise ValueError('Исходный RGB кандидата не воспроизведён.')
                        apply_replace(stats,base,x0,y0,x1,y1);records.append(rec)
                    elapsed=prior+time.monotonic()-start;commit_batch(db,protocol,done,records,stats,elapsed,ck);done+=len(records);batches+=1
                    print(f'Сохранено замен {done}/{len(ids)}.',flush=True)
            with sqlite3.connect(db) as conn:conn.execute("UPDATE state SET stage='evaluation' WHERE id=1 AND stage='training'")
            folder,db,protocol,holdout,state=read_state(folder,ck)
        if state['stage']=='evaluation':
            print('Обучение закончено. Проверяется новый закреплённый holdout.',flush=True)
            out=evaluate(folder,protocol,holdout,state,source,runner,proto,ev,stim,ck,base,large,source[12],source[13])
            with sqlite3.connect(db) as conn:conn.execute("UPDATE state SET stage='completed' WHERE id=1 AND stage='evaluation'")
            print('Готово:',out,flush=True)
            if os.name=='nt':
                try:os.startfile(str(out))
                except OSError:pass


def start(folder,source,holdout,fixture_limit=None,max_batches=None):
    protocol,raw,stats,ids=preregister(source,holdout,fixture_limit);runner=load_runner();proto,ev,pre,stim,ck,base,large=runner.dependencies();free_check(large,Path(folder).parent,fixture_limit is not None);create(folder,protocol,raw,stats,ck);print('Holdout закреплён до прогнозов. SHA-256:',protocol['holdout_sha256'],flush=True);process(folder,max_batches)
def request_pause(folder):
    runner=load_runner();proto,ev,pre,stim,ck,base,large=runner.dependencies();folder=Path(folder).resolve()
    _,_,_,_,state=read_state(folder,ck)
    if state['stage']!='training':raise ValueError('Обучение уже закончено; пауза во время проверки недоступна.')
    try:
        with large.RunLock(folder):pass
    except ValueError:pass
    else:raise ValueError('Серия сейчас не работает.')
    try:(folder/'pause.request').write_text('pause\n',encoding='utf-8',errors='strict')
    except OSError as exc:raise ValueError(f'Не удалось записать паузу: {exc}') from exc
    print('Запрос паузы записан.',flush=True)


def choose():
    import tkinter as tk
    from tkinter import filedialog,messagebox,simpledialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    def initial(p):return str(p.resolve()) if p.exists() else str(Path.cwd())
    try:
        action=simpledialog.askinteger('Серия 63','Введите номер:\n1: начать\n2: продолжить\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
        if action is None:return
        if action in (2,3):
            folder=filedialog.askdirectory(title='Выберите папку wing_context_invariant_...',initialdir=initial(ROOT),parent=root)
            if not folder:return
            return process(folder) if action==2 else request_pause(folder)
        messagebox.showinfo('Исходная серия','Выберите завершённую папку серии 59 wing_user_long_.... Она будет только читаться.',parent=root)
        source=filedialog.askdirectory(title='Завершённая серия 59',initialdir=initial(SOURCE_ROOT),parent=root)
        if not source:return
        messagebox.showinfo('Новый holdout','Теперь выберите только что созданный новый JSON. Его SHA будет закреплён до вычисления прогнозов.',parent=root)
        holdout=filedialog.askopenfilename(title='Новый holdout JSON',filetypes=[('Траектория JSON','*.json')],parent=root)
        if not holdout:return
        messagebox.showinfo('Перед запуском','Будут воспроизведены и заменены контекстом около половины принятых вариантов серии 59. Два процесса, пониженный приоритет, пауза через повторный запуск BAT. Исходные файлы не изменяются. Время зависит от компьютера.',parent=root)
        folder=ROOT/('wing_context_invariant_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);start(folder,source,holdout)
    finally:root.destroy()


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--choose',action='store_true');g.add_argument('--new');g.add_argument('--resume');g.add_argument('--pause')
    p.add_argument('--source');p.add_argument('--holdout');p.add_argument('--fixture-limit',type=int,help=argparse.SUPPRESS);p.add_argument('--batches',type=int,help=argparse.SUPPRESS);a=p.parse_args()
    if a.choose:return choose()
    if a.new:
        if not a.source or not a.holdout:p.error('Нужны --source и --holdout.')
        return start(a.new,a.source,a.holdout,a.fixture_limit,a.batches)
    if a.resume:return process(a.resume,a.batches)
    return request_pause(a.pause)

if __name__=='__main__':
    multiprocessing.freeze_support()
    try:sys.exit(main() or 0)
    except Exception as exc:print(f'ОШИБКА СЕРИИ 63: {type(exc).__name__}: {exc}\nИсходная серия и holdout не изменялись; последняя партия сохранена.',file=sys.stderr,flush=True);sys.exit(1)
