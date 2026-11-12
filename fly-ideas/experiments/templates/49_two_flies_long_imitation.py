#!/usr/bin/env python3
"""Time-budgeted, checkpointed supervised imitation; separate from study 44."""
from __future__ import annotations
import argparse
import concurrent.futures as futures
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone

for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import numpy as np
import mujoco

HERE=Path(__file__).resolve().parent
TRAIN_HASH='ae56f491742eb5053ab0a13dc53f6cc906195ea173f8d1f555631d343fe27253'
HOLD_HASH='69c65f163bd082fc9d803a28ca81985d9a3e89fb7b14e3e8b9850a7712ec93e3'
LARGE_HASH='f90e6633c0115b9f3faf21aae3b1ecdfb6dbf29308ac4ad5e4dc588b1ec2e364'
ENGINE_HASH='2f7d4ed860abe2cd97aec19ce93012d608501fa85acbfd6ae7aec9b46d673290'
BUDGET=8*3600
TRAIN_LIMIT=500000
EVAL_COUNT=64
WORKERS=2
BATCH=8
SEED=20261107
MIN_RAM=4*1024**3
MIN_DISK=2*1024**3
DIM=576
FPSC=25
FRAMES=50
HIST=3
CLIP=.65
RIDGE=1.0
WORKER_ENGINE=None
WORKER_PILOT=None
PROGRESS_NEXT=0.0


def sha_bytes(data): return hashlib.sha256(data).hexdigest()
def sha(path): return sha_bytes(Path(path).read_bytes())
def utc(): return datetime.now(timezone.utc).isoformat()
def load(name,filename,digest):
    p=HERE/filename
    if sha(p)!=digest: raise ValueError(f'Скрипт {filename} изменён; безопасное продолжение невозможно.')
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def modules():
    pilot=load('long_pilot','47_two_flies_imitation_learning.py',TRAIN_HASH)
    hold=load('long_hold','48_two_flies_frozen_holdout.py',HOLD_HASH)
    large=load('long_lock','44_two_flies_large_study.py',LARGE_HASH)
    if sha(HERE/'38_two_flies_observation.py')!=ENGINE_HASH: raise ValueError('Движок 38 изменён.')
    return pilot,hold,large

def worker_init():
    global WORKER_ENGINE,WORKER_PILOT
    WORKER_PILOT=load('worker_pilot','47_two_flies_imitation_learning.py',TRAIN_HASH)
    WORKER_PILOT.lower_priority()
    WORKER_ENGINE=WORKER_PILOT.engine_load()

def spec_for(split, ident):
    # Separate deterministic random namespaces, each video belongs to one split.
    rng=np.random.default_rng(np.random.SeedSequence([SEED,0 if split=='train' else 1,ident]))
    shape= ('sine','harmonic','chirp')[ident%3] if split=='train' or ident<32 else 'asymmetric'
    freq=float(rng.uniform(.8,4.8 if split=='train' or ident<32 else 5.2))
    amp=float(rng.uniform(.25,.78 if split=='train' or ident<32 else .80))
    distance=float(rng.uniform(3.4 if split=='train' or ident<32 else 3.25,4.6 if split=='train' or ident<32 else 4.75))
    offset=float(rng.uniform(-.6 if split=='train' or ident<32 else -.7,.6 if split=='train' or ident<32 else .7))
    phase=float(rng.uniform(0,360))
    return dict(split=split,id=ident,shape=shape,frequency_hz=freq,phase_deg=phase,distance=distance,offset=offset,amplitude_rad=amp)

def target(spec):
    t=np.arange(FRAMES,dtype=np.float64)/FPSC
    theta=2*np.pi*spec['frequency_hz']*t+np.deg2rad(spec['phase_deg'])
    if spec['shape']=='chirp':theta+=np.pi*.45*t*t
    wave=np.sin(theta)
    if spec['shape']=='harmonic':wave=(wave+.25*np.sin(3*theta))/((7/6)*math.sqrt(7/12))
    if spec['shape']=='asymmetric':wave=(wave+.2*np.sin(2*theta))/1.2
    return spec['amplitude_rad']*wave

def generate(split,ident):
    if WORKER_ENGINE is None:worker_init()
    m=WORKER_ENGINE;pilot=WORKER_PILOT;sp=spec_for(split,ident); y=target(sp)
    model=mujoco.MjModel.from_xml_string(m.XML);data=mujoco.MjData(model)
    model.body_pos[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,'demonstrator')]=[sp['distance'],sp['offset'],.4]
    l=model.jnt_qposadr[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,'left_hinge')]
    r=model.jnt_qposadr[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,'right_hinge')]
    cams=[m.camera([.85,v,.46],[4,0,.55],pilot.WIDTH,pilot.HEIGHT) for v in (.13,-.13)]
    images=[]
    for a in y:
        data.qpos[l]=a;data.qpos[r]=-a;mujoco.mj_forward(model,data)
        images.append(np.stack([m.render(model,data,c,True) for c in cams]))
    images=np.stack(images);x=pilot.history(images);truth=y[HIST-1:]
    return sp,x,truth,sha_bytes(images.tobytes()),sha_bytes(y.tobytes()), images if split=='test' else None

def empty_stats():return dict(n=np.array(0,dtype=np.int64),sx=np.zeros(DIM),sx2=np.zeros(DIM),sy=np.array(0.,dtype=np.float64),sxy=np.zeros(DIM),sxx=np.zeros((DIM,DIM)))
def pack(stats):
    mem=io.BytesIO();np.savez_compressed(mem,**stats);return mem.getvalue()
def unpack(blob,digest):
    if sha_bytes(blob)!=digest:raise ValueError('Контрольная сумма накопленных данных не совпадает.')
    with np.load(io.BytesIO(blob),allow_pickle=False) as z:
        st={k:np.asarray(z[k]).copy() for k in ('n','sx','sx2','sy','sxy','sxx')}
    if st['n'].shape!=() or int(st['n'])<0 or st['sx'].shape!=(DIM,) or st['sx2'].shape!=(DIM,) or st['sxy'].shape!=(DIM,) or st['sxx'].shape!=(DIM,DIM) or st['sy'].shape!=() or any(not np.isfinite(v).all() for v in st.values()):raise ValueError('Некорректные накопленные данные обучения.')
    return st

def add_stats(stats,x,y):
    if x.shape!=(FRAMES-HIST+1,DIM) or y.shape!=(FRAMES-HIST+1,) or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Некорректные входы или метки.')
    stats['n']+=len(y);stats['sx']+=x.sum(axis=0);stats['sx2']+=np.square(x).sum(axis=0);stats['sy']+=y.sum();stats['sxy']+=x.T@y;stats['sxx']+=x.T@x

def fit_stats(stats):
    n=int(stats['n'])
    if n<2:raise ValueError('Недостаточно обучающих кадров для оценки.')
    mean=stats['sx']/n; var=np.maximum(stats['sx2']/n-mean*mean,0);scale=np.sqrt(var);scale[scale<1e-6]=1.0
    ym=float(stats['sy']/n);cov=(stats['sxx']/n-np.outer(mean,mean))/np.outer(scale,scale)
    rhs=(stats['sxy']/n-mean*ym)/scale
    weights=np.linalg.solve(cov+RIDGE*np.eye(DIM),rhs)
    if not np.isfinite(weights).all():raise ValueError('Не удалось получить конечные веса.')
    return mean,scale,ym,weights

def protocol(model_hash,testing=False,test_count=0):
    return dict(schema=1,script_sha256=sha(__file__),engine_sha256=ENGINE_HASH,pilot_sha256=TRAIN_HASH,holdout_sha256=HOLD_HASH,large_lock_sha256=LARGE_HASH,
        python=platform.python_version(),versions={p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},model_sha256=model_hash,
        mode='test_subset' if testing else 'full',seed=SEED,train_limit=test_count if testing else TRAIN_LIMIT,eval_count=4 if testing else EVAL_COUNT,
        budget_s=60 if testing else BUDGET,workers=WORKERS,batch=BATCH,frames=FRAMES,fps=FPSC,history=HIST,dimension=DIM,ridge=RIDGE,output_clip_rad=CLIP,
        inputs='current and two previous two-eye coarse grayscale images',training='supervised angles, ridge sufficient statistics',
        split='separate deterministic random namespaces per full sequence; first 32 test familiar shape, remaining asymmetric',
        limitations='Toy kinematic model, fixed amplitude clipping; no biological brain, no autonomous replay after viewing, explicit teacher labels, no matched-object control.')

def setup(folder,model_bytes,oldmeta,proto):
    db=sqlite3.connect(folder/'study.sqlite3',timeout=30)
    try:
        db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA synchronous=FULL')
        db.executescript('''CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),completed INTEGER NOT NULL,elapsed REAL NOT NULL,stage TEXT NOT NULL,stats BLOB NOT NULL,stats_sha256 TEXT NOT NULL);
        CREATE TABLE sequences(id INTEGER PRIMARY KEY,spec_json TEXT NOT NULL,images_sha256 TEXT NOT NULL,angles_sha256 TEXT NOT NULL);
        CREATE TABLE source_model(id INTEGER PRIMARY KEY CHECK(id=1),payload BLOB NOT NULL,metadata BLOB NOT NULL);''')
        blob=pack(empty_stats())
        with db:
            db.execute('INSERT INTO metadata VALUES (?,?)',('protocol',json.dumps(proto,ensure_ascii=False,sort_keys=True)))
            db.execute('INSERT INTO state VALUES(1,0,0,?,?,?)',('training',blob,sha_bytes(blob)))
            db.execute('INSERT INTO source_model VALUES(1,?,?)',(model_bytes,oldmeta))
    finally:db.close()

def verify(db,folder):
    if db.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError('SQLite не прошла quick_check.')
    p=json.loads(db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()[0]); oldblob,oldmeta=db.execute('SELECT payload,metadata FROM source_model WHERE id=1').fetchone()
    if sha_bytes(oldblob)!=p['model_sha256']:raise ValueError('Контрольная сумма исходной модели не совпадает.')
    expected=protocol(p['model_sha256'],p['mode']=='test_subset',p['train_limit'])
    if p!=expected:raise ValueError('Протокол, версия Python, библиотеки или скрипты изменились; продолжение остановлено.')
    done,elapsed,stage,blob,digest=db.execute('SELECT completed,elapsed,stage,stats,stats_sha256 FROM state WHERE id=1').fetchone()
    stats=unpack(blob,digest)
    count,mn,mx=db.execute('SELECT COUNT(*),MIN(id),MAX(id) FROM sequences').fetchone()
    if done<0 or done>p['train_limit'] or count!=done or (done and (mn!=0 or mx!=done-1)) or int(stats['n'])!=done*(FRAMES-HIST+1) or not math.isfinite(elapsed) or elapsed<0 or stage not in ('training','evaluation','completed'):
        raise ValueError('Контрольная точка не согласуется с журналом последовательностей.')
    return p,done,elapsed,stage,stats,oldblob,oldmeta

def progress(folder,done,elapsed,stage,total):
    # Optional status only; never claim that a failed write was persisted.
    global PROGRESS_NEXT
    if time.monotonic()<PROGRESS_NEXT and stage=='training':return
    tmp=folder/('progress_'+uuid.uuid4().hex+'.tmp')
    try:
        tmp.write_text(json.dumps(dict(completed_sequences=done,plan_limit=total,active_seconds=elapsed,state=stage,updated_utc=utc()),ensure_ascii=False,indent=2),encoding='utf-8')
        os.replace(tmp,folder/'progress.json')
        PROGRESS_NEXT=0.0
    except PermissionError:
        PROGRESS_NEXT=time.monotonic()+30
        print('Предупреждение: progress.json занят. Данные в SQLite, статус попробуем сохранить позже.',flush=True)
        try:tmp.unlink(missing_ok=True)
        except OSError:pass

def free_check(large,folder,testing):
    if testing:return
    ram=large.available_ram();disk=shutil.disk_usage(folder).free
    if ram is not None and ram<MIN_RAM:raise MemoryError(f'Свободно {ram/1024**3:.2f} ГиБ RAM, требуется не менее 4 ГиБ. Контрольная точка сохранена.')
    if disk<MIN_DISK:raise OSError(f'Свободно {disk/1024**3:.2f} ГиБ на диске, требуется не менее 2 ГиБ. Контрольная точка сохранена.')

def preview_scene(pilot,sp,truth,predicted,path):
    # Render a replay of already-computed predictions, not closed-loop simulation.
    engine=pilot.engine_load();xml=engine.XML
    for side,y in [('left','0.75'),('right','-0.75')]:
        original=f'<geom name="observer_{side}_wing" type="ellipsoid" pos="-0.1 {y} 0.20" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/>'
        replacement=f'<body name="observer_{side}_joint_body" pos="-0.1 {y} 0.20"><joint name="observer_{side}_hinge" type="hinge" axis="1 0 0"/><geom name="observer_{side}_wing" type="ellipsoid" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/></body>'
        if original not in xml:raise ValueError('Не удалось собрать визуализацию наблюдателя.')
        xml=xml.replace(original,replacement)
    model=mujoco.MjModel.from_xml_string(xml);data=mujoco.MjData(model)
    model.body_pos[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,'demonstrator')]=[sp['distance'],sp['offset'],.4]
    joints=[model.jnt_qposadr[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,n)] for n in ('left_hinge','right_hinge','observer_left_hinge','observer_right_hinge')]
    cam=engine.camera([6,-9,5],[2,0,.4],240,160,55);frames=[]
    for a,pred in zip(truth,predicted):
        data.qpos[joints]=[a,-a,pred,-pred];mujoco.mj_forward(model,data)
        image=pilot.Image.fromarray(engine.render(model,data,cam));draw=pilot.ImageDraw.Draw(image)
        draw.rectangle((0,0,239,17),fill=(220,220,210));draw.text((3,3),'OBSERVER LEFT / TEACHER RIGHT',fill=(20,20,20));frames.append(image)
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=round(1000/FPSC),loop=0,optimize=False)

def eval_model(folder,proto,stats,oldblob,oldmeta,pilot,pool,elapsed,db):
    # A new result folder is never overwritten. Interrupted exports remain marked.
    out=folder/('result_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);out.mkdir()
    (out/'INCOMPLETE.txt').write_text('Оценка выполняется или прервана.\n',encoding='utf8')
    mean,scale,intercept,w=fit_stats(stats)
    np.savez_compressed(out/'model_new.npz',mean=mean,scale=scale,intercept=intercept,weights=w)
    (out/'model_old.npz').write_bytes(oldblob);(out/'source_metadata.json').write_bytes(oldmeta)
    with np.load(io.BytesIO(oldblob),allow_pickle=False) as z:
        old={k:np.asarray(z[k]).copy() for k in ('mean','scale','intercept','weights')}
    records=[];seqrows=[];framerows=[];images_all=[];labels_all=[]; wins=ties=losses=0
    for ident,(sp,x,y,framehash,anglehash,images) in enumerate(pool.map(generate,['test']*proto['eval_count'],range(proto['eval_count']))):
        pred=np.clip((x-mean)/scale@w+intercept,-CLIP,CLIP)
        opred=np.clip((x-old['mean'])/old['scale']@old['weights']+float(old['intercept']),-CLIP,CLIP)
        zero=np.zeros_like(y);floor=np.clip(y,-CLIP,CLIP)
        values={'new':pred,'old':opred,'zero':zero,'clip_floor':floor}
        sc={k:pilot.metrics(y,v) for k,v in values.items()}
        delta=sc['new']['rmse_rad']-sc['old']['rmse_rad']
        if abs(delta)<1e-12:ties+=1
        elif delta<0:wins+=1
        else:losses+=1
        prefix=(ident,sp['shape'],sp['frequency_hz'],sp['phase_deg'],sp['distance'],sp['offset'],sp['amplitude_rad'])
        for k,v in sc.items():seqrows.append((*prefix,k,len(y),v['rmse_rad'],v['mae_rad'],v['correlation'],framehash,anglehash))
        for i in range(len(y)):framerows.append((*prefix,i+HIST-1,(i+HIST-1)/FPSC,float(y[i]),float(pred[i]),float(opred[i]),0.,float(floor[i])))
        records.append((sp,y,values));images_all.append(images);labels_all.append(target(sp))
        print(f'Проверено новых последовательностей: {ident+1}/{proto["eval_count"]}',flush=True)
    np.savez_compressed(out/'test_visual_sequences.npz',images=np.stack(images_all),teacher_angle=np.stack(labels_all))
    prefix=['sequence_id','shape','frequency_hz','phase_deg','distance','offset','amplitude_rad']
    pilot.csv_write(out/'training_log.csv',['sequence_id','spec_json','images_sha256','angles_sha256'],db.execute('SELECT id,spec_json,images_sha256,angles_sha256 FROM sequences ORDER BY id'))
    pilot.csv_write(out/'sequence_metrics.csv',prefix+['condition','frames','rmse_rad','mae_rad','correlation','images_sha256','angles_sha256'],seqrows)
    pilot.csv_write(out/'predictions.csv',prefix+['frame','time_s','teacher_angle_rad','new_angle_rad','old_angle_rad','zero_angle_rad','clip_floor_angle_rad'],framerows)
    scores={}
    ys=np.concatenate([x[1] for x in records])
    for k in ('new','old','zero','clip_floor'):scores[k]=pilot.metrics(ys,np.concatenate([x[2][k] for x in records]))
    breakdown=[]
    for shape in ('sine','harmonic','chirp','asymmetric'):
        group=[x for x in records if x[0]['shape']==shape]
        if not group:continue
        yy=np.concatenate([x[1] for x in group])
        for k in ('new','old','zero','clip_floor'):
            met=pilot.metrics(yy,np.concatenate([x[2][k] for x in group]));breakdown.append((shape,k,len(group),met['rmse_rad'],met['mae_rad']))
    pilot.csv_write(out/'breakdown.csv',['shape','condition','sequences','rmse_rad','mae_rad'],breakdown)
    pilot.plot_sequence(records[0][1],records[0][2]['new'],out/'comparison.png')
    preview_scene(pilot,records[0][0],records[0][1],records[0][2]['new'],out/'comparison.gif')
    result=dict(status='completed',protocol=proto,active_training_seconds=elapsed,training_sequences=int(stats['n'])//(FRAMES-HIST+1),test_sequences=len(records),scores=scores,sequences_new_vs_old={'better':wins,'equal':ties,'worse':losses},model_old_sha256=sha_bytes(oldblob),model_new_sha256=sha(out/'model_new.npz'),created_utc=utc(),limitations=['Supervised teacher-angle labels, not self-taught imitation.', 'Fixed ±0.65 rad output clip, error lower bound from target is not a predictor.', 'Sequence-disjoint seeded synthetic data, individual poses may repeat; no biological replication. The evaluation protocol has been run locally and is not blind confirmation.', 'New model fitted from sufficient statistics, source old model provenance based on metadata.', 'During observation only; no autonomous replay or biological mirror neuron claim. The GIF is a kinematic replay of computed angles, not closed-loop dynamics.', 'No matched moving-object control; comparisons are descriptive.'])
    (out/'metadata.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['БОЛЬШАЯ СЕРИЯ ОБУЧЕНИЯ ДВУХ МУХ',f'Режим: {proto["mode"]}; обучающих последовательностей: {result["training_sequences"]}; проверочных: {len(records)}.',f'Активное время обучения: {elapsed/3600:.3f} ч; лимит {proto["budget_s"]/3600:.2f} ч. Оценка и сохранение выполняются отдельно.', 'Обе модели получили одинаковый новый проверочный набор; нормализация новой модели вычислена только по обучению.', 'Общая RMSE / MAE, радианы (меньше лучше):']
    for k,label in [('new','Новая модель'),('old','Старая замороженная модель'),('zero','Неподвижные крылья'),('clip_floor','Теоретическая граница ограничения ±0,65 рад')]:
        lines.append(f'{label}: {scores[k]["rmse_rad"]:.6f} / {scores[k]["mae_rad"]:.6f}')
    lines.append(f'Новая против старой: лучше {wins}, равно {ties}, хуже {losses} последовательностей из {len(records)}.')
    lines.append('По формам (RMSE новая / старая / ноль):')
    for shape in ('sine','harmonic','chirp','asymmetric'):
        r={x[1]:x for x in breakdown if x[0]==shape}
        if r:lines.append(f'{shape} ({r["new"][2]}): {r["new"][3]:.6f} / {r["old"][3]:.6f} / {r["zero"][3]:.6f}')
    lines.extend(['','Обучение по явным меткам угла, команды только во время просмотра. Это искусственная кинематическая модель, не мозг мухи и не доказательство зеркальных нейронов.',
                  'Проверочные последовательности и генератор отделены от обучения; отдельные позы могут совпадать. Это не независимые животные или статистический тест.', 'Этот фиксированный проверочный набор уже запускался локально; проверка не является слепой.',
                  'Нижняя граница использует истинный угол и не является предсказателем; при амплитудах выше 0,65 ограничение может давать ошибку.',
                  'training_log.csv: параметры и хэши обучающих сцен; исходные обучающие кадры отдельно не сохраняются.', 'sequence_metrics.csv и predictions.csv: по последовательностям и кадрам; breakdown.csv: формы; test_visual_sequences.npz: проверочные кадры и метки.',
                  'model_new.npz и model_old.npz: веса; comparison.png и comparison.gif: заранее первая последовательность, не среднее.', 'GIF показывает кинематическое воспроизведение уже рассчитанных углов, а не физическую динамику или замкнутое управление. metadata.json: протокол и хэши.'])
    (out/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    (out/'INCOMPLETE.txt').unlink(); print('\n'.join(lines));print('Результаты:',out,flush=True)
    return out


def evaluate_with_retry(folder,p,stats,oldblob,oldmeta,pilot,pool,elapsed,db):
    attempts=0
    while True:
        try:return eval_model(folder,p,stats,oldblob,oldmeta,pilot,pool,elapsed,db)
        except PermissionError as exc:
            attempts+=1
            print(f'Файлы результата заняты: {exc}. Данные обучения в SQLite сохранены; незавершённые папки помечены INCOMPLETE.txt.',flush=True)
            if attempts<4:
                print('Повторная попытка через 2 секунды.',flush=True);time.sleep(2);continue
            if not sys.stdin.isatty():raise
            answer=input('Закройте программу, блокирующую файлы, и нажмите Enter для повтора; Q для выхода: ').strip().lower()
            if answer=='q':raise
            attempts=0


def train(folder,resume=False,model_path=None,testing=False,test_count=0):
    pilot,hold,large=modules();folder=Path(folder).resolve()
    if not resume:
        if not model_path:raise ValueError('Не выбрана старая модель model.npz.')
        source,raw,meta_bytes,_,_=hold.load_model(model_path,pilot)
        p=protocol(sha_bytes(raw),testing,test_count)
        folder.mkdir(parents=True,exist_ok=False)
    elif not (folder/'study.sqlite3').is_file():raise ValueError('В выбранной папке нет study.sqlite3 этой серии.')
    large.job_guard();pilot.lower_priority()
    with large.RunLock(folder):
        if not resume:setup(folder,raw,meta_bytes,p)
        db=sqlite3.connect(folder/'study.sqlite3',timeout=30)
        db.execute('PRAGMA synchronous=FULL')
        try:
            p,done,elapsed,stage,stats,oldblob,oldmeta=verify(db,folder)
            if stage=='completed':
                row=db.execute("SELECT value FROM metadata WHERE key='last_result'").fetchone()
                print('Серия уже завершена. Результат:',row[0] if row else folder,flush=True);return folder
            if resume:
                for name in ('pause.request',):
                    path=folder/name
                    if path.exists():path.unlink()
            print(f'Папка серии: {folder}\nОбучающих последовательностей сохранено: {done}; активное время: {elapsed/3600:.3f} ч.',flush=True)
            progress(folder,done,elapsed,stage,p['train_limit'])
            started=time.monotonic();prior=elapsed;initial_done=done;reported_speed=False
            with futures.ProcessPoolExecutor(max_workers=WORKERS,mp_context=mp.get_context('spawn'),initializer=worker_init) as pool:
                while stage=='training':
                    current=prior+time.monotonic()-started
                    if (folder/'pause.request').exists():
                        with db:db.execute('UPDATE state SET elapsed=? WHERE id=1',(current,))
                        print('Пауза: сохранённые последовательности останутся в базе. Продолжите через тот же BAT.',flush=True)
                        progress(folder,done,current,'paused',p['train_limit']);return folder
                    finish=(folder/'finish.request').exists() or current>=p['budget_s'] or done>=p['train_limit']
                    if finish and done==0:print('Невозможно завершить без обучающих последовательностей; сначала будет обработана одна партия.',flush=True);finish=False
                    if finish:
                        with db:db.execute('UPDATE state SET elapsed=?,stage=? WHERE id=1',(current,'evaluation'))
                        elapsed=current;stage='evaluation';progress(folder,done,current,stage,p['train_limit']);break
                    free_check(large,folder,p['mode']=='test_subset')
                    ids=list(range(done,min(done+BATCH,p['train_limit'])))
                    output=list(pool.map(generate,['train']*len(ids),ids))
                    if sha(__file__)!=p['script_sha256'] or sha(HERE/'38_two_flies_observation.py')!=ENGINE_HASH or sha(HERE/'47_two_flies_imitation_learning.py')!=TRAIN_HASH or sha(HERE/'48_two_flies_frozen_holdout.py')!=HOLD_HASH:
                        raise ValueError('Скрипт изменился во время работы; партия не сохранена.')
                    batch=[]
                    for ident,(sp,x,y,imhash,anglehash,images) in zip(ids,output):
                        if sp!=spec_for('train',ident) or images is not None:raise ValueError('Получена последовательность не из текущего плана.')
                        add_stats(stats,x,y);batch.append((ident,json.dumps(sp,sort_keys=True),imhash,anglehash))
                    blob=pack(stats);elapsed=prior+time.monotonic()-started
                    with db:
                        db.executemany('INSERT INTO sequences VALUES(?,?,?,?)',batch)
                        db.execute('UPDATE state SET completed=?,elapsed=?,stats=?,stats_sha256=? WHERE id=1',(ids[-1]+1,elapsed,blob,sha_bytes(blob)))
                    done=ids[-1]+1
                    progress(folder,done,elapsed,'training',p['train_limit'])
                    print(f'Сохранено {done} последовательностей; активное время {elapsed/3600:.3f}/{p["budget_s"]/3600:.1f} ч; предел {p["train_limit"]}.',flush=True)
                    if not reported_speed:
                        session=max(time.monotonic()-started,1e-9)
                        rate=(done-initial_done)/session
                        projected=min(p['train_limit'],done+int(rate*max(0,p['budget_s']-elapsed)))
                        print(f'Первая ориентировочная скорость: {rate*3600:.0f} последовательностей/ч; ориентир к пределу времени: {projected}. Это не гарантия.',flush=True)
                        reported_speed=True
                if stage=='evaluation':
                    free_check(large,folder,p['mode']=='test_subset')
                    print('Обучение завершено. Оценка начинается без переобучения; она может занять дополнительное время.',flush=True)
                    out=evaluate_with_retry(folder,p,stats,oldblob,oldmeta,pilot,pool,elapsed,db)
                    with db:
                        db.execute('UPDATE state SET stage=? WHERE id=1',('completed',))
                        db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',('last_result',str(out)))
                    progress(folder,done,elapsed,'completed',p['train_limit'])
                    if os.name=='nt':
                        try:os.startfile(str(out))
                        except OSError as exc:print('Не удалось открыть папку результата:',exc)
        finally:db.close()
    return folder


def choose_folder(title, initial):
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:return filedialog.askdirectory(title=title,initialdir=str(Path(initial).resolve()))
    finally:root.destroy()

def choose_model():
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:return filedialog.askopenfilename(title='Выберите model.npz завершённого пилота',initialdir=str(Path('workspace/runs/ideas/i-observational/imitation-learning').resolve()),filetypes=[('Модель NPZ','*.npz'),('Все файлы','*.*')])
    finally:root.destroy()

def request(folder,kind):
    _,_,large=modules();folder=Path(folder).resolve()
    if not (folder/'study.sqlite3').is_file():raise ValueError('Не найдена база серии обучения в выбранной папке.')
    # The same lock must be occupied by an active worker; existence of the file is not enough.
    active=False
    try:
        with large.RunLock(folder):pass
    except ValueError:active=True
    if not active:raise ValueError('Серия сейчас не работает. Запустите или продолжите её через RUN-TWO-FLIES-LONG-IMITATION.bat.')
    with sqlite3.connect((folder/'study.sqlite3').as_uri()+'?mode=ro',uri=True,timeout=30) as db:
        row=db.execute('SELECT stage FROM state WHERE id=1').fetchone()
    if not row or row[0]!='training':raise ValueError('Фаза обучения уже закончена: пауза или досрочное завершение сейчас недоступны.')
    (folder/(kind+'.request')).write_text(utc()+'\n',encoding='utf8')
    print('Запрос записан. Текущая партия будет завершена и сохранена.',flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--choose',action='store_true');group.add_argument('--new');group.add_argument('--resume');group.add_argument('--pause',action='store_true');group.add_argument('--finish',action='store_true')
    p.add_argument('--model');p.add_argument('--folder');p.add_argument('--test-count',type=int,help=argparse.SUPPRESS)
    args=p.parse_args();root=Path('workspace/runs/ideas/i-observational/imitation-long')
    if args.test_count is not None and (not args.new or not 1<=args.test_count<=16):p.error('test-count only for small new fixture runs')
    if args.pause or args.finish:
        folder=args.folder or choose_folder('Выберите папку imitation_long_...',root)
        if folder:request(folder,'pause' if args.pause else 'finish')
        else:print('Выбор отменён.')
        return
    if args.choose:
        import tkinter as tk
        from tkinter import messagebox
        window=tk.Tk();window.withdraw();window.attributes('-topmost',True)
        try:ans=messagebox.askyesnocancel('Большая серия обучения','Начать новую серию?\nДа: новая. Нет: продолжить. Отмена: выход.',parent=window)
        finally:window.destroy()
        if ans is None:print('Выбор отменён.');return
        if ans:
            model=choose_model()
            if not model:print('Выбор отменён.');return
            dest=root/('imitation_long_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);train(dest,model_path=model)
        else:
            selected=choose_folder('Выберите папку серии imitation_long_...',root)
            if selected:train(selected,resume=True)
            else:print('Выбор отменён.')
    elif args.new:train(args.new,model_path=args.model,testing=args.test_count is not None,test_count=args.test_count or 0)
    else:train(args.resume,resume=True)

if __name__=='__main__':
    mp.freeze_support()
    try:main()
    except Exception as exc:
        print(f'ОШИБКА: {type(exc).__name__}: {exc}\nСохранённые партии остаются в SQLite. Папки с INCOMPLETE.txt не являются готовыми результатами.',file=sys.stderr,flush=True)
        sys.exit(1)
