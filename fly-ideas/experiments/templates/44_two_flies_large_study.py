#!/usr/bin/env python3
"""Large, resumable factorial study of visual responses in a two-fly toy model."""
from __future__ import annotations
import argparse
import concurrent.futures as futures
import csv
import ctypes
import hashlib
import importlib.metadata
import importlib.util
import io
import itertools
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
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
ENGINE_SHA='2f7d4ed860abe2cd97aec19ce93012d608501fa85acbfd6ae7aec9b46d673290'
SCHEMA=1
CONDITIONS=('wings','stationary','occluded','reverse','tile_scramble','object_unmatched')
FREQUENCIES=(1,2,3,4,5,6)
PHASES=tuple(range(0,360,30))
DISTANCES=tuple(round(3.0+.4*i,1) for i in range(13))
OFFSETS=tuple(round(-2.4+.4*i,1) for i in range(13))
PLAN_SEED=20261106
FPS=50; FRAMES=100; WIDTH=96; HEIGHT=64; WORKERS=2
MIN_RAM=4*1024**3; MIN_DISK=5*1024**3; START_DISK=12*1024**3
ENGINE=None
_JOB_HANDLE=None


def utc():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def packed(**arrays):
    out=io.BytesIO();np.savez_compressed(out,**arrays);return out.getvalue()
def unpacked(blob):
    with np.load(io.BytesIO(blob),allow_pickle=False) as x:return {k:x[k].copy() for k in x.files}


def load_engine():
    p=HERE/'38_two_flies_observation.py'
    if sha(p)!=ENGINE_SHA:raise ValueError('Скрипт 38 изменён, работа остановлена до создания результатов.')
    spec=importlib.util.spec_from_file_location('large_study_engine',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def worker_init():
    global ENGINE
    if sys.platform=='win32':
        kernel=ctypes.windll.kernel32;kernel.GetCurrentProcess.restype=ctypes.c_void_p
        kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
        if not kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x00004000):raise OSError('Не удалось понизить приоритет процесса.')
    elif hasattr(os,'nice'):os.nice(10)
    ENGINE=load_engine()


def job_guard():
    """Kill spawned workers if the Windows parent is forcibly closed."""
    global _JOB_HANDLE
    if sys.platform!='win32':return
    from ctypes import wintypes
    class Basic(ctypes.Structure):
        _fields_=[('p1',ctypes.c_longlong),('p2',ctypes.c_longlong),('flags',wintypes.DWORD),('min',ctypes.c_size_t),('max',ctypes.c_size_t),('limit',wintypes.DWORD),('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('schedule',wintypes.DWORD)]
    class IO(ctypes.Structure):_fields_=[(x,ctypes.c_ulonglong) for x in ('r1','r2','r3','r4','r5','r6')]
    class Ext(ctypes.Structure):_fields_=[('basic',Basic),('io',IO),('pm',ctypes.c_size_t),('jm',ctypes.c_size_t),('pp',ctypes.c_size_t),('jp',ctypes.c_size_t)]
    k=ctypes.windll.kernel32;k.CreateJobObjectW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p];k.CreateJobObjectW.restype=ctypes.c_void_p
    k.SetInformationJobObject.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD];k.AssignProcessToJobObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
    k.GetCurrentProcess.restype=ctypes.c_void_p;k.CloseHandle.argtypes=[ctypes.c_void_p]
    job=k.CreateJobObjectW(None,None)
    if not job:raise OSError('Не удалось создать защитную группу процессов.')
    lim=Ext();lim.basic.flags=0x2000
    if not k.SetInformationJobObject(job,9,ctypes.byref(lim),ctypes.sizeof(lim)) or not k.AssignProcessToJobObject(job,k.GetCurrentProcess()):
        k.CloseHandle(job);raise OSError('Windows не разрешила защитную группу процессов; расчёт не запущен.')
    _JOB_HANDLE=job


def available_ram():
    if sys.platform=='win32':
        from ctypes import wintypes
        class Mem(ctypes.Structure):
            _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD)]+[(x,ctypes.c_ulonglong) for x in ('total','available','total_page','available_page','total_virtual','available_virtual','available_extended')]
        m=Mem();m.length=ctypes.sizeof(m)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)):raise OSError('Не удалось проверить свободную RAM.')
        return int(m.available)
    try:
        for line in Path('/proc/meminfo').read_text().splitlines():
            if line.startswith('MemAvailable:'):return int(line.split()[1])*1024
    except OSError:pass
    return None


class RunLock:
    def __init__(self,folder):self.path=folder/'run.lock';self.f=None
    def __enter__(self):
        self.f=self.path.open('a+b');self.f.seek(0,os.SEEK_END)
        if self.f.tell()==0:self.f.write(b'1');self.f.flush()
        self.f.seek(0)
        try:
            if os.name=='nt':
                import msvcrt;msvcrt.locking(self.f.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl;fcntl.flock(self.f,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.f.close();raise ValueError('Этот расчёт уже запущен. Вторую копию открывать нельзя.')
        return self
    def __exit__(self,*args):
        try:
            self.f.seek(0)
            if os.name=='nt':
                import msvcrt;msvcrt.locking(self.f.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl;fcntl.flock(self.f,fcntl.LOCK_UN)
        finally:self.f.close()


def plan(limit=None):
    grid=list(itertools.product(FREQUENCIES,PHASES,DISTANCES,OFFSETS))
    order=np.random.default_rng(PLAN_SEED).permutation(len(grid))
    if limit is not None:order=order[:limit]
    return [(int(i),*grid[int(i)]) for i in order]


def make_frames(freq,phase,distance,offset):
    engine=ENGINE
    obj='<body name="distractor" mocap="true" pos="3 0 0.55"><geom name="distractor_geom" type="ellipsoid" size="0.25 0.25 0.25" rgba="0.22 0.22 0.20 1"/></body>'
    xml=engine.XML.replace('</worldbody></mujoco>',obj+'</worldbody></mujoco>')
    if xml==engine.XML:raise ValueError('Не удалось добавить контрольный объект.')
    wing_model=mujoco.MjModel.from_xml_string(engine.XML);wing_data=mujoco.MjData(wing_model)
    object_model=mujoco.MjModel.from_xml_string(xml);object_data=mujoco.MjData(object_model)
    for model in (wing_model,object_model):
        body=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,'demonstrator');model.body_pos[body]=[distance,offset,.4]
    left=wing_model.jnt_qposadr[mujoco.mj_name2id(wing_model,mujoco.mjtObj.mjOBJ_JOINT,'left_hinge')]
    right=wing_model.jnt_qposadr[mujoco.mj_name2id(wing_model,mujoco.mjtObj.mjOBJ_JOINT,'right_hinge')]
    cams=[engine.camera([.85,y,.46],[4,0,.55],WIDTH,HEIGHT) for y in (.13,-.13)]
    def shot(model,data):return np.stack([engine.render(model,data,cam,True) for cam in cams])
    moving=[];objects=[]
    wing_data.qpos[left]=0;wing_data.qpos[right]=0;mujoco.mj_forward(wing_model,wing_data)
    still=shot(wing_model,wing_data)
    for k in range(FRAMES):
        t=k/FPS;sig=math.sin(2*math.pi*freq*t+math.radians(phase))
        wing_data.qpos[left]=.65*sig;wing_data.qpos[right]=-.65*sig;mujoco.mj_forward(wing_model,wing_data)
        object_data.mocap_pos[0]=[distance-.75,offset+.65*sig,.55];mujoco.mj_forward(object_model,object_data)
        moving.append(shot(wing_model,wing_data));objects.append(shot(object_model,object_data))
    return np.stack(moving),np.broadcast_to(still,(FRAMES,*still.shape)).copy(),np.stack(objects)


def tile_scramble(frames,seed):
    out=np.empty_like(frames);rng=np.random.default_rng(seed)
    for r in range(4):
        for c in range(4):
            hh=HEIGHT//4;ww=WIDTH//4;part=frames[:,:,r*hh:(r+1)*hh,c*ww:(c+1)*ww,:]
            out[:,:,r*hh:(r+1)*hh,c*ww:(c+1)*ww,:]=part.reshape(FRAMES,2,hh*ww,3)[:,:,rng.permutation(hh*ww),:].reshape(FRAMES,2,hh,ww,3)
    return out


def calculate(row):
    ident,freq,phase,distance,offset=row
    moving,static,obj=make_frames(freq,phase,distance,offset)
    conditions=(moving,static,np.full_like(moving,128),moving[::-1].copy(),tile_scramble(moving,PLAN_SEED+ident),obj)
    feats=[ENGINE.features(x) for x in conditions]
    err=float(np.max(np.abs(feats[0]-feats[4])))
    if err>1e-6:raise ValueError(f'Не совпали входы tile_scramble: {ident}, {err}')
    outputs=[]
    for name,frames,features in zip(CONDITIONS,conditions,feats):
        times,ids,drive=ENGINE.simulate(features,1/FPS,0)
        counts=np.bincount(ids,minlength=32)
        raw=packed(frames=frames,features=features,drive=drive,times_s=times,neuron_id=ids)
        outputs.append((name,int(len(ids)),float(features.mean()),counts.tolist(),features.mean(axis=0).tolist(),raw))
    return row,err,outputs,sha(__file__)


def setup_db(folder,protocol):
    with sqlite3.connect(folder/'study.sqlite3') as db:
        db.executescript('''PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL;
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE groups (id INTEGER PRIMARY KEY, frequency REAL NOT NULL, phase INTEGER NOT NULL, distance REAL NOT NULL, offset REAL NOT NULL, tile_error REAL NOT NULL, saved_utc TEXT NOT NULL);
        CREATE TABLE trials (group_id INTEGER NOT NULL, condition TEXT NOT NULL, spikes INTEGER NOT NULL, mean_input REAL NOT NULL, payload BLOB NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(group_id,condition), FOREIGN KEY(group_id) REFERENCES groups(id));
        CREATE TABLE neurons (group_id INTEGER NOT NULL, condition TEXT NOT NULL, neuron_id INTEGER NOT NULL, spikes INTEGER NOT NULL, mean_input REAL NOT NULL, PRIMARY KEY(group_id,condition,neuron_id), FOREIGN KEY(group_id,condition) REFERENCES trials(group_id,condition));''')
        db.execute('INSERT INTO metadata VALUES (?,?)',('protocol',json.dumps(protocol,ensure_ascii=False,sort_keys=True)))


def write_group(db,row,err,outputs):
    if tuple(x[0] for x in outputs)!=CONDITIONS:raise ValueError('Неполная группа условий.')
    ident,freq,phase,distance,offset=row
    with db:
        db.execute('INSERT INTO groups VALUES(?,?,?,?,?,?,?)',(ident,freq,phase,distance,offset,err,utc()))
        for name,spikes,mean,counts,features,payload in outputs:
            db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?)',(ident,name,spikes,mean,payload,hashlib.sha256(payload).hexdigest()))
            db.executemany('INSERT INTO neurons VALUES(?,?,?,?,?)',((ident,name,i,int(counts[i]),float(features[i])) for i in range(32)))


def write_csv_atomic(path,header,rows):
    temp=path.with_name(path.name+'.tmp')
    with temp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows);f.flush();os.fsync(f.fileno())
    os.replace(temp,path)


def export_summary(db,folder):
    rows=list(db.execute('SELECT condition,COUNT(*),AVG(spikes),MIN(spikes),MAX(spikes),AVG(mean_input) FROM trials GROUP BY condition ORDER BY condition'))
    write_csv_atomic(folder/'conditions_summary.csv',['condition','completed_groups','mean_spikes','min_spikes','max_spikes','mean_motion_abs_diff'],rows)
    rows=db.execute('''SELECT a.condition,a.neuron_id,COUNT(*),AVG(a.spikes),AVG(b.spikes),AVG(a.spikes-b.spikes),AVG(a.mean_input),AVG(b.mean_input)
    FROM neurons a JOIN neurons b ON a.group_id=b.group_id AND a.neuron_id=b.neuron_id AND b.condition='wings'
    GROUP BY a.condition,a.neuron_id ORDER BY a.condition,a.neuron_id''')
    write_csv_atomic(folder/'neuron_comparison.csv',['condition','neuron_id','completed_groups','mean_spikes','mean_wings_spikes','mean_paired_spike_difference','mean_visual_input','mean_wings_visual_input'],rows)
    rows=db.execute("""SELECT g.frequency,t.condition,COUNT(*),AVG(t.spikes),AVG(t.mean_input),SUM(CASE WHEN w.mean_input>1e-8 THEN 1 ELSE 0 END)
        FROM trials t JOIN groups g ON g.id=t.group_id JOIN trials w ON w.group_id=t.group_id AND w.condition='wings'
        GROUP BY g.frequency,t.condition ORDER BY g.frequency,t.condition""")
    write_csv_atomic(folder/'conditions_by_frequency.csv',['frequency_hz','condition','completed_groups','mean_spikes','mean_visual_input','groups_with_wings_motion_above_1e-8'],rows)
    rows=db.execute("""SELECT g.frequency,a.condition,a.neuron_id,COUNT(*),AVG(a.spikes),AVG(b.spikes),AVG(a.spikes-b.spikes),AVG(a.mean_input),AVG(b.mean_input)
        FROM neurons a JOIN neurons b ON a.group_id=b.group_id AND a.neuron_id=b.neuron_id AND b.condition='wings'
        JOIN groups g ON g.id=a.group_id GROUP BY g.frequency,a.condition,a.neuron_id ORDER BY g.frequency,a.condition,a.neuron_id""")
    write_csv_atomic(folder/'neurons_by_frequency.csv',['frequency_hz','condition','neuron_id','completed_groups','mean_spikes','mean_wings_spikes','mean_paired_spike_difference','mean_visual_input','mean_wings_visual_input'],rows)
    rows=db.execute("""SELECT a.condition,a.neuron_id,COUNT(*),AVG(a.spikes),AVG(b.spikes),AVG(a.spikes-b.spikes),AVG(a.mean_input),AVG(b.mean_input)
        FROM neurons a JOIN neurons b ON a.group_id=b.group_id AND a.neuron_id=b.neuron_id AND b.condition='wings'
        JOIN trials w ON w.group_id=a.group_id AND w.condition='wings' WHERE w.mean_input>1e-8
        GROUP BY a.condition,a.neuron_id ORDER BY a.condition,a.neuron_id""")
    write_csv_atomic(folder/'neurons_nonzero_wing_motion.csv',['condition','neuron_id','completed_groups','mean_spikes','mean_wings_spikes','mean_paired_spike_difference','mean_visual_input','mean_wings_visual_input'],rows)
    rows=db.execute('''SELECT g.id,g.frequency,g.phase,g.distance,g.offset,t.condition,t.spikes,t.mean_input,g.tile_error
    FROM trials t JOIN groups g ON g.id=t.group_id ORDER BY g.id,t.condition''')
    write_csv_atomic(folder/'trials_summary.csv',['group_id','frequency_hz','phase_deg','distance','offset','condition','spikes','mean_motion_abs_diff','tile_max_feature_error'],rows)


def protocol(count,testing=False):
    return dict(schema=SCHEMA,script_sha256=sha(__file__),engine_sha256=ENGINE_SHA,python=platform.python_version(),
        versions={x:importlib.metadata.version(x) for x in ('numpy','mujoco','brian2','pillow')},grid={'frequencies':FREQUENCIES,'phases_deg':PHASES,'distances':DISTANCES,'offsets':OFFSETS},
        total_groups=count,full_grid_groups=len(FREQUENCIES)*len(PHASES)*len(DISTANCES)*len(OFFSETS),test_subset=testing,plan_seed=PLAN_SEED,
        conditions=CONDITIONS,frames=FRAMES,fps=FPS,width=WIDTH,height=HEIGHT,network_seed=0,neural_dt_ms=1,workers=WORKERS,
        model='MuJoCo kinematic ellipsoids with ray-cast eyes; 32 independent toy LIF motion cells, NOT connectome or biological eyes',
        stimulus='demonstrator position (distance, offset, 0.4), wing angles +/-0.65*sin(2*pi*frequency*t+phase); object ellipsoid center (distance-0.75, offset+0.65*sin(...), 0.55), size (0.25,0.25,0.25); stationary wings at zero; arbitrary scene units',
        control_definitions={'wings':'moving wings','stationary':'wings held at zero','occluded':'moving wing scene with 128 gray to both eyes','reverse':'wing RGB frames in reverse time order','tile_scramble':'fixed within-tile permutation of wing RGB pixels per eye, shared over time','object_unmatched':'stationary wings and moving ellipsoid; not matched in retinal size/position/contrast'},
        limitations='No direction selectivity, learning, motor action, biomechanics, real neurons, or biological replicates. Object is not image-matched; initial neural state fixed. Grid values are model parameters, not fly wingbeat measurements.')


def status(folder,state,done,total,started,reason='',initial=0):
    elapsed=max(0,time.monotonic()-started);rate=(done-initial)/elapsed if elapsed and done>initial else 0
    value=dict(state=state,completed_groups=done,total_groups=total,completed_trials=done*len(CONDITIONS),total_trials=total*len(CONDITIONS),session_elapsed_s=elapsed,estimated_remaining_s=(total-done)/rate if rate else None,reason=reason,updated_utc=utc())
    temp=folder/'progress.json.tmp';temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8');os.replace(temp,folder/'progress.json')


def run(folder,testing_count=None,resume=False):
    folder=Path(folder).resolve()
    load_engine();job_guard()
    if not resume:
        folder.mkdir(parents=True,exist_ok=False)
    if not (folder/'study.sqlite3').is_file() and resume:raise ValueError('Не найдена база study.sqlite3 в выбранной папке.')
    start=time.monotonic()
    with RunLock(folder):
        if not resume:
            total=len(plan(testing_count));setup_db(folder,protocol(total,testing_count is not None))
        db=sqlite3.connect(folder/'study.sqlite3',timeout=30);db.execute('PRAGMA foreign_keys=ON');db.execute('PRAGMA synchronous=FULL')
        try:
            entry=db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()
            if not entry:raise ValueError('Отсутствует протокол базы.')
            old=json.loads(entry[0]);total=old['total_groups']
            expected=protocol(total,old['test_subset'])
            if old!=json.loads(json.dumps(expected)):raise ValueError('Версия скрипта, библиотек или протокола изменилась; продолжение заблокировано.')
            if db.execute('PRAGMA quick_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchone():raise ValueError('База не прошла проверку целостности.')
            allrows=plan(total);done_ids={r[0] for r in db.execute('SELECT id FROM groups')}
            valid_ids={r[0] for r in allrows}
            if not done_ids<=valid_ids:raise ValueError('База содержит группы вне закреплённого плана.')
            bad=db.execute('SELECT g.id FROM groups g LEFT JOIN trials t ON t.group_id=g.id GROUP BY g.id HAVING COUNT(t.condition)!=?',(len(CONDITIONS),)).fetchone()
            if bad:raise ValueError('База содержит неполную группу; автоматическое продолжение запрещено.')
            if resume:
                expected_rows={row[0]:row for row in allrows}
                for actual in db.execute('SELECT id,frequency,phase,distance,offset FROM groups'):
                    if tuple(actual)!=tuple(expected_rows[actual[0]]):raise ValueError('Параметры группы не совпадают с планом.')
                for ident,name,payload,digest in db.execute('SELECT group_id,condition,payload,sha256 FROM trials'):
                    if name not in CONDITIONS or hashlib.sha256(payload).hexdigest()!=digest:raise ValueError(f'Повреждён сохранённый результат: {ident}/{name}.')
                bad_neurons=db.execute('SELECT t.group_id FROM trials t LEFT JOIN neurons n ON n.group_id=t.group_id AND n.condition=t.condition GROUP BY t.group_id,t.condition HAVING COUNT(n.neuron_id)!=32 OR SUM(n.spikes)!=t.spikes LIMIT 1').fetchone()
                if bad_neurons:raise ValueError('Неполные или повреждённые нейронные данные.')
            done=len(done_ids);initial=done;todo=iter(row for row in allrows if row[0] not in done_ids)
            if resume and (folder/'stop.request').exists():(folder/'stop.request').unlink()
            memory_floor=0 if old['test_subset'] else MIN_RAM
            free=available_ram();disk=shutil.disk_usage(folder).free
            if free is not None and free<memory_floor:raise MemoryError(f'Свободно {free/1024**3:.2f} ГиБ RAM, нужно не менее 4 ГиБ.')
            disk_floor=MIN_DISK if resume or old['test_subset'] else START_DISK
            if disk<disk_floor:raise OSError(f'Свободно {disk/1024**3:.2f} ГиБ на диске, нужно не менее {disk_floor/1024**3:.0f} ГиБ перед стартом.')
            status(folder,'running',done,total,start,initial=initial)
            print(f'Группы: {done}/{total}; условий в группе: {len(CONDITIONS)}; процессы: {WORKERS}.',flush=True)
            print('Оценка времени будет уточняться; 4–8 часов не гарантируются.',flush=True)
            pending={};stop_reason=''; exhausted=False
            with futures.ProcessPoolExecutor(max_workers=WORKERS,mp_context=mp.get_context('spawn'),initializer=worker_init) as pool:
                while pending or not exhausted:
                    if sha(__file__)!=old['script_sha256'] or sha(HERE/'38_two_flies_observation.py')!=ENGINE_SHA:
                        raise ValueError('Скрипт изменился во время расчёта; данные завершённых групп сохранены, новые группы не принимаются.')
                    if (folder/'stop.request').exists():stop_reason='Остановка по запросу пользователя.'
                    free=available_ram();disk=shutil.disk_usage(folder).free
                    if free is not None and free<memory_floor:stop_reason=f'Мало свободной RAM: {free/1024**3:.2f} ГиБ.'
                    if disk<MIN_DISK:stop_reason=f'Мало места на диске: {disk/1024**3:.2f} ГиБ.'
                    while not exhausted and not stop_reason and len(pending)<WORKERS:
                        try:r=next(todo)
                        except StopIteration:exhausted=True;break
                        pending[pool.submit(calculate,r)]=r
                    if not pending:break
                    ready,_=futures.wait(pending,timeout=1,return_when=futures.FIRST_COMPLETED)
                    for fut in ready:
                        expected_row=pending.pop(fut);r,err,outs,worker_sha=fut.result()
                        if worker_sha!=old['script_sha256'] or sha(__file__)!=old['script_sha256'] or sha(HERE/'38_two_flies_observation.py')!=ENGINE_SHA:
                            raise ValueError('Версия скрипта изменилась во время расчёта; группа не записана.')
                        if r!=expected_row:raise ValueError('Неверный идентификатор группы в результате.')
                        write_group(db,r,err,outs);done+=1
                        status(folder,'running',done,total,start,initial=initial)
                        if (done-initial)%250==0:export_summary(db,folder)
                        elapsed=time.monotonic()-start;speed=(done-initial)/elapsed if elapsed>0 else 0
                        eta=(total-done)/speed/3600 if speed>0 else 0
                        print(f'Группы {done}/{total}; условий {done*len(CONDITIONS)}/{total*len(CONDITIONS)}; оценка остатка {eta:.2f} ч; последний ID {r[0]}.',flush=True)
                    if stop_reason and not pending:break
            export_summary(db,folder)
            state='completed' if done==total else 'paused'
            status(folder,state,done,total,start,stop_reason,initial)
            print(f'{state.upper()}: {done}/{total}. Папка: {folder}',flush=True)
        except BaseException:
            try:status(folder,'interrupted',db.execute('SELECT COUNT(*) FROM groups').fetchone()[0],total if 'total' in locals() else 0,start,'Ошибка или прерывание; данные завершённых групп сохранены.')
            except Exception:pass
            raise
        finally:db.close()
    return folder


def scene_preview(group,path):
    # Overview of the original physical wings condition, not the altered eye inputs.
    frequency,phase,distance,offset=group;engine=load_engine()
    model=mujoco.MjModel.from_xml_string(engine.XML);data=mujoco.MjData(model)
    model.body_pos[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,'demonstrator')]=[distance,offset,.4]
    left=model.jnt_qposadr[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,'left_hinge')]
    right=model.jnt_qposadr[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,'right_hinge')]
    cam=engine.camera([distance*.55,-max(9,distance+4),6],[distance*.5,offset*.5,.4],300,200,55)
    images=[]
    for k in range(0,FRAMES,5):
        angle=.65*math.sin(2*math.pi*frequency*k/FPS+math.radians(phase))
        data.qpos[left]=angle;data.qpos[right]=-angle;mujoco.mj_forward(model,data)
        im=Image.fromarray(engine.render(model,data,cam));d=ImageDraw.Draw(im)
        d.rectangle((0,0,300,18),fill=(226,225,218));d.text((4,4),'WINGS SCENE / OBSERVER RESTS',fill=(25,25,25));images.append(im)
    images[0].save(path,save_all=True,append_images=images[1:],duration=100,loop=0,optimize=False)


def export_group(folder,ident):
    folder=Path(folder).resolve();dbpath=folder/'study.sqlite3'
    if not dbpath.is_file():raise ValueError('В выбранной папке нет базы исследования.')
    db=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)
    try:
        group=db.execute('SELECT frequency,phase,distance,offset FROM groups WHERE id=?',(ident,)).fetchone()
        if not group:raise ValueError('Группа с таким ID не сохранена.')
        rows=db.execute('SELECT condition,payload,sha256 FROM trials WHERE group_id=? ORDER BY condition',(ident,)).fetchall()
        if len(rows)!=len(CONDITIONS) or any(hashlib.sha256(b).hexdigest()!=digest for _,b,digest in rows):raise ValueError('Неполная группа или повреждённые записи.')
        out=folder/('group_'+str(ident)+'_'+uuid.uuid4().hex[:8]);out.mkdir()
        scene_preview(group,out/'scene_wings.gif')
        (out/'parameters.json').write_text(json.dumps(dict(group_id=ident,frequency_hz=group[0],phase_deg=group[1],distance=group[2],offset=group[3]),indent=2),encoding='utf8')
        for name,blob,_ in rows:
            a=unpacked(blob);sub=out/name;sub.mkdir();(sub/'data.npz').write_bytes(blob)
            write_csv_atomic(sub/'spikes.csv',['time_s','neuron_id'],zip(a['times_s'].tolist(),a['neuron_id'].tolist()))
            write_csv_atomic(sub/'visual_input.csv',['frame','time_s','neuron_id','motion_abs_diff','drive'],((k,k/FPS,i,float(a['features'][k,i]),float(a['drive'][k,i])) for k in range(FRAMES) for i in range(32)))
            ims=[Image.fromarray(np.concatenate((fr[0],fr[1]),axis=1)) for fr in a['frames']]
            ims[0].save(sub/'observer_input.gif',save_all=True,append_images=ims[1:],duration=20,loop=0,optimize=False)
        return out
    finally:db.close()


def choose_folder(title):
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:return filedialog.askdirectory(title=title,initialdir=str(Path('workspace/runs/ideas/i-observational/large-study').resolve()))
    finally:root.destroy()


def main():
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--choose',action='store_true');mode.add_argument('--new');mode.add_argument('--resume');mode.add_argument('--stop',action='store_true');mode.add_argument('--export',action='store_true')
    p.add_argument('--folder');p.add_argument('--group',type=int);p.add_argument('--test-count',type=int,help=argparse.SUPPRESS)
    a=p.parse_args()
    if a.test_count is not None and (not a.new or not 1<=a.test_count<=20):p.error('--test-count is only for small new fixture runs')
    if a.stop or a.export:
        selected=a.folder or choose_folder('Выберите папку large_two_flies_...')
        if not selected:print('Выбор отменён.');return
        folder=Path(selected)
        if not (folder/'study.sqlite3').is_file():raise ValueError('База исследования не найдена; ничего не изменено.')
        if a.stop:
            (folder/'stop.request').write_text('stop requested\n',encoding='utf8');print('Запрошена остановка после завершения текущих групп.');return
        ident=a.group if a.group is not None else int(input('Введите ID группы из trials_summary.csv: '))
        out=export_group(folder,ident);print('Данные группы:',out)
        if os.name=='nt':os.startfile(str(out))
        return
    if a.choose:
        from tkinter import messagebox
        import tkinter as tk
        root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
        try:answer=messagebox.askyesnocancel('Большая серия двух мух','Начать новый большой расчёт?\nДа: новый. Нет: продолжить существующий. Отмена: выход.',parent=root)
        finally:root.destroy()
        if answer is None:print('Отменено.');return
        if answer:
            parent=Path('workspace/runs/ideas/i-observational/large-study');parent.mkdir(parents=True,exist_ok=True)
            folder=parent/('large_two_flies_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);resume=False
        else:
            selected=choose_folder('Выберите существующую папку large_two_flies_...')
            if not selected:print('Отменено.');return
            folder=Path(selected);resume=True
    else:folder=Path(a.resume or a.new);resume=bool(a.resume)
    out=run(folder,a.test_count,resume)
    if a.choose and os.name=='nt':os.startfile(str(out))


if __name__=='__main__':
    mp.freeze_support()
    try:main()
    except Exception as e:print(f'ОШИБКА: {type(e).__name__}: {e}',file=sys.stderr,flush=True);sys.exit(1)
