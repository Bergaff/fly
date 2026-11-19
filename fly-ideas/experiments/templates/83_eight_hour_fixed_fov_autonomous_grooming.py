#!/usr/bin/env python3
"""Eight-hour fixed-FOV35 edge foreleg-grooming training followed by frozen autonomous replay.

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
import itertools
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
AXES = ('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
MIN_RAM = 4*1024**3
MIN_DISK = 2*1024**3
ROOT = Path('workspace/runs/ideas/i-observational/fixed-fov-autonomous-grooming-eight-hour')
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
    if hours != 8 or type(hours)!=int: raise ValueError('Серия 83 имеет ровно 8 часов активного обучения.')
    if fixture_limit is not None and (type(fixture_limit)!=int or not 2<=fixture_limit<=8):
        raise ValueError('Техническая проба ограничена 2–8 кандидатами.')
    return {'schema':'eight-hour-fixed-fov-autonomous-grooming-v1','mode':'fixture' if fixture_limit is not None else 'long',
            'budget_seconds':hours*3600,'fixture_limit':fixture_limit,'workers':2,'batch':2,
            'script_sha256':file_sha(__file__),'dependencies':{**proto.PIN,**PIN},
            'python':platform.python_version(),
            'versions':{p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},
            'source_sha256':source_sha,'labels':labels,
            'outputs':list(AXES),'command_units':'joint radians for three joints on each front leg',
            'training_generator':{'seed':8301,'view_seed':8303,'families':['piecewise5','piecewise9','harmonic','chirp'],'command_clip_deg_equivalent':[-55,55],'camera_resolution':[96,64],'camera_fov_deg':35,'feature_type':'pooled gradient-energy history','feature_dim':576,'view_sampling':'50% balanced 4D corners; 50% continuous interior','camera_side_range':[.14,.42],'camera_z_range':[.36,.56],'body_x_range':[3.82,4.18],'body_y_range':[-.32,.32],'camera_target':'head and forelegs','visual_guard':{'min_unique_frames':10,'min_changed_rgb_values':100,'min_feature_std':1e-4,'min_joint_changed_rgb_values':10}},
            'evaluation':{'motion_seed':8302,'holdouts':list(range(261,271)),'geometry_corners':16,'view_ranges':{'fov_deg':[35,35],'camera_side':[.14,.42],'camera_z':[.36,.56],'body_x':[3.82,4.18],'body_y':[-.32,.32]},'body_x_upper_safeguard':4.18,'state_coefficients':72,'delay_s':.5,'forbidden_replay_access':['observation RGB','teacher commands','saved framewise predictions']}, 
            'primary_rule':'on motions 261-270 x 16 corners: every axis normal below zero with >=70% case wins; combined below zero/shuffled/static/closed with >=70% wins; bodyX4.18 repeats axis rule; >=12/16 corners pass six-axis pooled-zero and >=7/10 wins; matched diagnostic is not primary'}


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


BROAD_STIM=None;BROAD_PILOT=None;BROAD_SCENE=None;BROAD_HOLD=None

class VisibleForelegGroomingScene:
    """Renderer-compatible nonzero ellipsoid forelegs; body and wings remain fixed."""
    def __init__(self,engine):
        import mujoco
        xml=engine.XML
        # Wings remain folded and fixed; replace their dynamic hinges with no joints.
        for side in ('left','right'):
            xml=xml.replace(f'<joint name="{side}_hinge" type="hinge" axis="1 0 0"/>','')
        marker='  </body>\n </body>\n</worldbody>'
        legs='  </body>\n  <body name="left_foreleg_proximal" pos="-0.48 0.22 -0.04">\n   <joint name="left_proximal" type="hinge" axis="1 0 0"/>\n   <geom name="demo_left_foreleg_proximal" type="ellipsoid" pos="-0.13 0.05 0.01" size="0.15 0.065 0.055" rgba="0.22 0.16 0.10 1"/>\n   <body name="left_foreleg_middle" pos="-0.25 0.10 0.02">\n    <joint name="left_middle" type="hinge" axis="0 1 0"/>\n    <geom name="demo_left_foreleg_middle" type="ellipsoid" pos="-0.11 -0.04 0.07" size="0.14 0.055 0.050" rgba="0.26 0.19 0.11 1"/>\n    <body name="left_foreleg_distal" pos="-0.22 -0.08 0.14">\n     <joint name="left_distal" type="hinge" axis="0 0 1"/>\n     <geom name="demo_left_foreleg_distal" type="ellipsoid" pos="-0.10 -0.06 0.01" size="0.13 0.045 0.040" rgba="0.30 0.21 0.12 1"/>\n    </body>\n   </body>\n  </body>\n  <body name="right_foreleg_proximal" pos="-0.48 -0.22 -0.04">\n   <joint name="right_proximal" type="hinge" axis="1 0 0"/>\n   <geom name="demo_right_foreleg_proximal" type="ellipsoid" pos="-0.13 -0.05 0.01" size="0.15 0.065 0.055" rgba="0.22 0.16 0.10 1"/>\n   <body name="right_foreleg_middle" pos="-0.25 -0.10 0.02">\n    <joint name="right_middle" type="hinge" axis="0 1 0"/>\n    <geom name="demo_right_foreleg_middle" type="ellipsoid" pos="-0.11 0.04 0.07" size="0.14 0.055 0.050" rgba="0.26 0.19 0.11 1"/>\n    <body name="right_foreleg_distal" pos="-0.22 0.08 0.14">\n     <joint name="right_distal" type="hinge" axis="0 0 1"/>\n     <geom name="demo_right_foreleg_distal" type="ellipsoid" pos="-0.10 0.06 0.01" size="0.13 0.045 0.040" rgba="0.30 0.21 0.12 1"/>\n    </body>\n   </body>\n  </body>\n </body>\n</worldbody>'
        if marker not in xml: raise ValueError('Не удалось добавить детальные передние лапы.')
        xml=xml.replace(marker,legs)
        self.mujoco=mujoco;self.engine=engine;self.model=mujoco.MjModel.from_xml_string(xml);self.data=mujoco.MjData(self.model)
        self.joints=[self.model.jnt_qposadr[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,n)] for n in AXES]
        self.body=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_BODY,'demonstrator')
        self.default_body=self.model.body_pos[self.body].copy()
        self.set_view({'fov_deg':35.0,'camera_side':0.20,'camera_z':0.42,'body_x':4.0,'body_y':0.0})
    def set_view(self,view):
        required=('fov_deg','camera_side','camera_z','body_x','body_y')
        if set(view)!=set(required) or not all(np.isfinite(float(view[k])) for k in required):raise ValueError('Неверная конфигурация камеры/корпуса.')
        fov=float(view['fov_deg']);side=float(view['camera_side']);z=float(view['camera_z'])
        if fov!=35. or not .10<=side<=.50 or not .30<=z<=.65:raise ValueError('Fixed-FOV35 view вне протокола.')
        self.cams=[self.engine.camera([.9,y,z],[3.25,float(view['body_y'])*.35,.48],96,64,fov=35.) for y in (side,-side)]
        self.model.body_pos[self.body]=[float(view['body_x']),float(view['body_y']),float(self.default_body[2])]
    def render(self,commands,distance=4.,offset=0.,view=None):
        del distance,offset
        if view is not None:self.set_view(view)
        commands=np.asarray(commands,float)
        if commands.ndim!=2 or commands.shape[1]!=6 or not np.isfinite(commands).all(): raise ValueError('Неверные команды передних лап.')
        images=[]
        for vec in commands:
            self.data.qpos[self.joints]=vec
            self.mujoco.mj_forward(self.model,self.data)
            images.append(np.stack([self.engine.render(self.model,self.data,c,True) for c in self.cams]))
        return np.stack(images)

def edge_history(images):
    """Fixed 96x64 two-eye gradient-energy history, 576 features."""
    im=np.asarray(images,np.float32)
    if im.dtype!=np.float32 or im.ndim!=5 or im.shape[1:]!=(2,64,96,3) or not 3<=len(im)<=251:
        raise ValueError('Нужны RGB-кадры двух камер 96x64.')
    lum=im.mean(-1)/255.;gx=np.abs(np.diff(lum,axis=3,prepend=lum[:,:,:,:1]));gy=np.abs(np.diff(lum,axis=2,prepend=lum[:,:,:1,:]));edge=np.sqrt(gx*gx+gy*gy);n=len(edge)
    vec=edge.reshape(n,2,8,8,12,8).mean(axis=(3,5)).reshape(n,192)
    return np.concatenate([vec[2-i:n-i] for i in range(3)],axis=1)

def visual_preflight(proto):
    """Block every long or resumed run unless moving joints visibly alter RGB/features."""
    engine=proto.load('visible_guard_engine','38_two_flies_observation.py')
    pilot=proto.load('visible_guard_pilot','47_two_flies_imitation_learning.py')
    scene=VisibleForelegGroomingScene(engine)
    _,degrees=broad_candidate(0);images=scene.render(degrees*np.pi/180)
    unique=len({frame.tobytes() for frame in images})
    changed=int(np.count_nonzero(images[1:]!=images[:-1]))
    features=edge_history(images);feature_std=float(np.max(np.std(features,axis=0)))
    joint_changed={}
    neutral=np.zeros((1,6),dtype=float);base_image=scene.render(neutral)[0]
    for j,axis in enumerate(AXES):
        command=neutral.copy();command[0,j]=np.pi/6
        joint_changed[axis]=int(np.count_nonzero(scene.render(command)[0]!=base_image))
    guard_views=[training_view(i) for i in range(4)]
    view_rgb=[scene.render(degrees*np.pi/180,view=v) for v in guard_views]
    view_hashes=[sha(x.tobytes()) for x in view_rgb]
    result={'candidate_id':0,'unique_frames':unique,'changed_rgb_values':changed,'max_feature_std':feature_std,
            'joint_changed_rgb_values':joint_changed,'rgb_sha256':sha(images.tobytes()),'augmentation_views':guard_views,'augmentation_rgb_sha256':view_hashes}
    if len(set(view_hashes))!=len(view_hashes):raise ValueError('VISUAL GUARD: разные augmentation views дали одинаковый RGB.')
    if min(len({frame.tobytes() for frame in x}) for x in view_rgb)<10:raise ValueError('VISUAL GUARD: движение невидимо в augmentation view.')
    if unique<10:raise ValueError(f'VISUAL GUARD: только {unique} уникальных RGB кадров из 51.')
    if changed<100:raise ValueError(f'VISUAL GUARD: изменилось только {changed} RGB значений.')
    if not np.isfinite(feature_std) or feature_std<1e-4:raise ValueError(f'VISUAL GUARD: max feature std {feature_std:.3g} ниже 1e-4.')
    failed=[axis for axis,value in joint_changed.items() if value<10]
    if failed:raise ValueError('VISUAL GUARD: суставы не меняют RGB: '+', '.join(failed))
    return result


def broad_motion_hash(degrees):
    normalized=np.round((np.asarray(degrees,dtype=float)*np.pi/180)*180/np.pi,7);normalized[normalized==0]=0
    return hashlib.sha256(np.asarray(normalized,dtype='<f8').tobytes()).hexdigest()

def geometry_corners():
    values={'camera_side':(.14,.42),'camera_z':(.36,.56),'body_x':(3.82,4.18),'body_y':(-.32,.32)}
    return [{'corner_id':i+1,'view':{'fov_deg':35.,**{k:values[k][b] for k,b in zip(values,bits)}}} for i,bits in enumerate(itertools.product((0,1),repeat=4))]

def training_view(ident):
    """Half balanced exact corners, half deterministic continuous interior; FOV always 35."""
    if ident%2==0:return geometry_corners()[(ident//2)%16]['view'].copy()
    rng=np.random.default_rng(np.random.SeedSequence([8303,ident]))
    return {'fov_deg':35.,'camera_side':float(rng.uniform(.14,.42)),
            'camera_z':float(rng.uniform(.36,.56)),'body_x':float(rng.uniform(3.82,4.18)),
            'body_y':float(rng.uniform(-.32,.32))}

def broad_candidate(ident):
    if type(ident)!=int or not 0<=ident<2**32:raise ValueError('Неверный broad candidate id.')
    rng=np.random.default_rng(np.random.SeedSequence([8301,ident]));t=np.arange(51,dtype=float)/25;family=('piecewise5','piecewise9','harmonic','chirp')[ident%4]
    if family.startswith('piecewise'):
        count=5 if family=='piecewise5' else 9;knots=np.linspace(0,2,count);values=rng.integers(-55,56,size=(count,6)).astype(float);degrees=np.stack([np.interp(t,knots,values[:,j]) for j in range(6)],axis=1);parameters={'keyframes_deg':values.astype(int).tolist()}
    else:
        offset=rng.uniform(-12,12,6);amplitude=rng.uniform(18,48,6);phase=rng.uniform(0,2*np.pi,6)
        if family=='harmonic':
            frequency=rng.uniform(.4,3.2,6);degrees=offset+amplitude*np.sin(2*np.pi*t[:,None]*frequency+phase);parameters={'offset_deg':offset.tolist(),'amplitude_deg':amplitude.tolist(),'phase_rad':phase.tolist(),'frequency_hz':frequency.tolist()}
        else:
            f0=rng.uniform(.25,1.2,6);f1=rng.uniform(1.8,4.0,6);sweep=(f1-f0)/2;degrees=offset+amplitude*np.sin(phase+2*np.pi*(t[:,None]*f0+.5*t[:,None]**2*sweep));parameters={'offset_deg':offset.tolist(),'amplitude_deg':amplitude.tolist(),'phase_rad':phase.tolist(),'f0_hz':f0.tolist(),'f1_hz':f1.tolist()}
    # Opposed foreleg commands create a visible, repeatable grooming/rubbing bout.
    degrees[:,3]=-degrees[:,0]+.25*degrees[:,3]
    degrees[:,4]=degrees[:,1]+.25*degrees[:,4]
    degrees[:,5]=-degrees[:,2]+.25*degrees[:,5]
    before=degrees.copy();degrees=np.clip(before,-55,55);distance=4.;side=0.;spec={'protocol':'fixed-fov35-edge-foreleg-grooming-v1','sequence_id':ident,'generator_seed':[8301,ident],'family':family,'parameters':parameters,'foreleg_pattern':'three-joint opposed grooming with 0.25 independent perturbation','distance':distance,'side_offset':side,'view':training_view(ident),'clipped_values':int(np.count_nonzero(before!=degrees)),'sampled_motion_sha256':broad_motion_hash(degrees)};return spec,degrees

def worker_init(train,hold):
    del train
    global BROAD_STIM,BROAD_PILOT,BROAD_SCENE,BROAD_HOLD
    worker=load('55_user_wing_resume_prototype.py','broad_worker_proto');BROAD_STIM=worker.load('broad_worker_stim','53_long_user_wing_stimuli.py');studio=worker.load('broad_worker_studio','50_two_flies_wing_studio_pilot.py');BROAD_PILOT=worker.load('broad_worker_pilot','47_two_flies_imitation_learning.py');engine=worker.load('broad_worker_engine','38_two_flies_observation.py');BROAD_PILOT.lower_priority();BROAD_SCENE=VisibleForelegGroomingScene(engine);BROAD_HOLD=hold

def worker_generate(ident):
    spec,degrees=broad_candidate(ident)
    if spec['sampled_motion_sha256'] in BROAD_HOLD:return {'id':ident,'status':'rejected','frames':0,'motion_sha256':spec['sampled_motion_sha256'],'rgb_sha256':None,'spec':spec},None,None
    images=BROAD_SCENE.render(degrees*np.pi/180,distance=spec['distance'],offset=spec['side_offset'],view=spec['view']);x=edge_history(images);y=degrees[2:]*np.pi/180
    return {'id':ident,'status':'accepted','frames':len(y),'motion_sha256':spec['sampled_motion_sha256'],'rgb_sha256':sha(images.tobytes()),'spec':spec},x,y


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
    saved['visual_preflight']=visual_preflight(proto)
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
    if budget != 28800 or saved.get('mode')!=('fixture' if limit is not None else 'long'):
        raise ValueError('Неверный протокол серии.')
    expected=protocol(saved.get('source_sha256'),saved.get('labels'),budget//3600,limit,proto)
    current_guard=visual_preflight(proto)
    if saved.get('visual_preflight')!=current_guard:raise ValueError('VISUAL GUARD изменился; продолжение запрещено.')
    expected['visual_preflight']=current_guard
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


def overlap_sample_broad(tests,records,cap=128):
    accepted=[r for r in records if r['status']=='accepted'];count=min(len(accepted),cap);sample=accepted if count==len(accepted) else [accepted[i] for i in np.linspace(0,len(accepted)-1,count,dtype=int)]
    distances=[]
    for item in tests:
        y=np.asarray(item['angles_deg']);target=np.concatenate([y[2:],y[1:-1],y[:-2]],axis=1);distances.append(np.full(len(target),np.inf))
    for rec in sample:
        spec,degrees=broad_candidate(rec['id'])
        if rec['spec']!=spec or rec['motion_sha256']!=spec['sampled_motion_sha256']:raise ValueError('Broad audit record mismatch.')
        h=np.concatenate([degrees[2:],degrees[1:-1],degrees[:-2]],axis=1)
        for k,target in enumerate(distances):
            source=np.asarray(tests[k]['angles_deg']);q=np.concatenate([source[2:],source[1:-1],source[:-2]],axis=1)
            for start in range(0,len(q),16):
                block=q[start:start+16];d=np.sqrt(np.mean((block[:,None,:]-h[None,:,:])**2,axis=2)).min(axis=1);target[start:start+len(block)]=np.minimum(target[start:start+len(block)],d)
    return {'accepted_total':len(accepted),'audited_count':len(sample),'sample_ids':[r['id'] for r in sample],'is_exhaustive':len(sample)==len(accepted),'tests':[{'test_id':item['id'],'frames':len(d),'nearest_rms_deg':d,'under_0_001_deg':int(np.sum(d<.001)),'under_1_deg':int(np.sum(d<1)),'under_5_deg':int(np.sum(d<5))} for item,d in zip(tests,distances)]}


def save_json(path,obj): Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def output_manifest(folder):
    return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}


def prepared_holdouts():
    """Freeze five wide and five faster piecewise movements before training."""
    folder=ROOT/'prepared_holdouts_seed_8302';folder.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(8302);paths=[]
    for i in range(1,11):
        path=folder/f'holdout_{260+i:03d}.json';count=5 if i<=5 else 9
        values=rng.integers(-55,56,size=(count,6)).astype(int);values[:,3]=np.clip(-values[:,0]+np.rint(.25*values[:,3]).astype(int),-55,55);values[:,4]=np.clip(values[:,1]+np.rint(.25*values[:,4]).astype(int),-55,55);values[:,5]=np.clip(-values[:,2]+np.rint(.25*values[:,5]).astype(int),-55,55)
        obj={'schema':'fly-wings-trajectory-v1','semantic_schema':'fly-foreleg-grooming-six-joint-v1','channels':list(AXES),'fps':25,'duration_s':2,
             'keyframes':[{'t':2*j/(count-1),'angles_deg':values[j].tolist()} for j in range(count)]}
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


def cosine_basis(n,k=12):
    phase=(np.arange(n)+.5)/n
    return np.column_stack([np.ones(n)]+[np.cos(np.pi*j*phase) for j in range(1,k)])

def compress_replay(framewise):
    b=cosine_basis(len(framewise));state=np.linalg.lstsq(b,np.asarray(framewise),rcond=None)[0].T.reshape(-1)
    replay=np.clip(b@state.reshape(6,12).T,-np.pi*55/180,np.pi*55/180)
    return state,replay

def replay_metrics(truth,pred):
    e=np.asarray(pred)-np.asarray(truth)
    return {'rmse_rad':float(np.sqrt(np.mean(e*e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,j]**2))) for j,a in enumerate(AXES)}}

def contact_trace(scene,commands):
    import mujoco
    head=mujoco.mj_name2id(scene.model,mujoco.mjtObj.mjOBJ_GEOM,'demo_head')
    ids=[mujoco.mj_name2id(scene.model,mujoco.mjtObj.mjOBJ_GEOM,'demo_'+a.replace('_proximal','_foreleg_proximal').replace('_middle','_foreleg_middle').replace('_distal','_foreleg_distal')) for a in AXES]
    trace=np.zeros((len(commands),6),dtype=np.uint8)
    for i,vec in enumerate(commands):
        scene.data.qpos[scene.joints]=vec;mujoco.mj_forward(scene.model,scene.data)
        for k in range(scene.data.ncon):
            c=scene.data.contact[k]
            for j,g in enumerate(ids):
                if (c.geom1==head and c.geom2==g) or (c.geom2==head and c.geom1==g):trace[i,j]=1
    return trace

def contact_f1(truth,pred):
    t=np.asarray(truth,bool);p=np.asarray(pred,bool);tp=int(np.sum(t&p));fp=int(np.sum(~t&p));fn=int(np.sum(t&~p))
    precision=tp/(tp+fp) if tp+fp else 0.;recall=tp/(tp+fn) if tp+fn else 0.
    return 2*precision*recall/(precision+recall) if precision+recall else 0.

def evaluate(folder,state,saved,elapsed,proto,ev,stim,base,large):
    folder=Path(folder);out=folder/'result'
    if out.exists():verify_result(out,saved,state);return out
    train,tests=proto.split_from_sources(state['sources'],stim);labels={x['copy']:x for x in saved['labels']}
    mean,scale,intercept,weights=base.fit(state['stats']);new=ev.checked_model({'mean':mean,'scale':scale,'intercept':intercept,'weights':weights})
    engine=proto.load('fixed83_engine','38_two_flies_observation.py');scene=VisibleForelegGroomingScene(engine)
    accepted,records=sampled_records(folder/'study.sqlite3',len(train));audit=overlap_sample_broad(tests,records,cap=128)
    audit['accepted_total']=accepted;audit['is_exhaustive']=audit['audited_count']==accepted
    temp=folder/('evaluation_incomplete_'+uuid.uuid4().hex);temp.mkdir();np.savez_compressed(temp/'model_new.npz',**new)
    results=[];all_corners=geometry_corners();corners=[all_corners[0],all_corners[2]] if saved['mode']=='fixture' else all_corners
    for item,overlap in zip(tests,audit['tests']):
        free_check(large,folder,saved['mode']=='fixture');ident=item['id'];label=labels[f'test_{ident:03d}.json'];original=label.get('original_basename','')
        if label['role']!='new_test':continue
        display_id=int(original[8:11]);truth_full=item['angles_deg']*np.pi/180;truth=truth_full[2:]
        matched_images=scene.render(truth_full,view={'fov_deg':35.,'camera_side':.20,'camera_z':.42,'body_x':4.,'body_y':0.})
        matched_features=edge_history(matched_images);matched_framewise=np.clip((matched_features-new['mean'])/new['scale']@new['weights']+new['intercept'],-np.pi*55/180,np.pi*55/180);_,matched_replay=compress_replay(matched_framewise);matched_metrics=replay_metrics(truth,matched_replay)
        for corner in corners:
            cid=corner['corner_id'];view=corner['view'];images=scene.render(truth_full,view=view);features=edge_history(images);framewise=np.clip((features-new['mean'])/new['scale']@new['weights']+new['intercept'],-np.pi*55/180,np.pi*55/180);state_coeff,replayed=compress_replay(framewise)
            normal=replay_metrics(truth,replayed);rng=np.random.default_rng(np.random.SeedSequence([830000,display_id,cid]));controls={}
            for cname,cimages in {'shuffled':images[rng.permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)}.items():
                cf=edge_history(cimages);cp=np.clip((cf-new['mean'])/new['scale']@new['weights']+new['intercept'],-np.pi*55/180,np.pi*55/180);_,cr=compress_replay(cp);controls[cname]=replay_metrics(truth,cr)
            zero=replay_metrics(truth,np.zeros_like(truth));before=sha(np.asarray(state_coeff,dtype='<f8').tobytes());after=sha(np.asarray(state_coeff,dtype='<f8').tobytes())
            truth_contacts=contact_trace(scene,truth);normal_contacts=contact_trace(scene,replayed);zero_contacts=contact_trace(scene,np.zeros_like(truth))
            result={'test_id':display_id,'internal_test_id':ident,'corner_id':cid,'role':label['role'],'frames':len(truth),'view':view,'body_x_upper':view['body_x']==4.18,'matched':matched_metrics,'normal':normal,'zero':zero,'controls':controls,'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':before==after,'state_sha256_before_delay':before,'state_sha256_after_delay':after,'contacts':{'normal_f1':contact_f1(truth_contacts,normal_contacts),'zero_f1':contact_f1(truth_contacts,zero_contacts)},'overlap_under_0_001_deg':overlap['under_0_001_deg'],'overlap_under_1_deg':overlap['under_1_deg'],'overlap_under_5_deg':overlap['under_5_deg']}
            td=temp/f'test_{display_id:03d}'/f'corner_{cid:02d}';td.mkdir(parents=True);save_json(td/'metrics.json',result);save_json(td/'internal_state.json',{'coefficients':list(map(float,state_coeff)),'delay_s':.5,'updates_during_delay':0,'replay_inputs':['compressed coefficient state','replay phase'],'forbidden_inputs':['observation RGB','teacher commands','saved framewise predictions']})
            with (td/'autonomous_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
                w=csv.writer(f);w.writerow(['time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'autonomous_{a}_rad' for a in AXES]]);w.writerows([[float(t),*map(float,y),*map(float,q)] for t,y,q in zip(item['times'][2:],truth,replayed)])
            results.append(result)
        print(f'Проверено fixed-FOV35 движение {display_id} на {len(corners)} corners.',flush=True)
    primary_items=[r for r in results if r['role']=='new_test'];total=sum(r['frames'] for r in primary_items)
    def pooled(items,key,axis=None):
        count=sum(r['frames'] for r in items)
        return float(np.sqrt(sum(r['frames']*(r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad'])**2 for r in items)/count))
    pooled_metrics={k:pooled(primary_items,k) for k in ('normal','matched','zero')}
    for c in ('shuffled','static','closed'):pooled_metrics[c]=float(np.sqrt(sum(r['frames']*r['controls'][c]['rmse_rad']**2 for r in primary_items)/total))
    threshold=.70*len(primary_items);axes={}
    for axis in AXES:
        n=pooled(primary_items,'normal',axis);z=pooled(primary_items,'zero',axis);wins=sum(r['normal']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in primary_items);axes[axis]={'normal':n,'zero':z,'wins':wins,'cases':len(primary_items),'passed':n<z and wins>=threshold}
    combined_wins=sum(r['normal']['rmse_rad']<r['zero']['rmse_rad'] for r in primary_items);better=sum(pooled_metrics['normal']<pooled_metrics[c] for c in ('shuffled','static','closed'))
    upper=[r for r in primary_items if r['body_x_upper']];upper_axes={}
    for axis in AXES:
        n=pooled(upper,'normal',axis);z=pooled(upper,'zero',axis);wins=sum(r['normal']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in upper);upper_axes[axis]={'normal':n,'zero':z,'wins':wins,'cases':len(upper),'passed':n<z and wins>=.70*len(upper)}
    corner_results=[]
    for corner in corners:
        cid=corner['corner_id'];items=[r for r in primary_items if r['corner_id']==cid];ca={}
        for axis in AXES:
            n=pooled(items,'normal',axis);z=pooled(items,'zero',axis);wins=sum(r['normal']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in items);ca[axis]={'normal':n,'zero':z,'wins':wins,'passed':n<z and wins>=7}
        corner_results.append({'corner_id':cid,'view':items[0]['view'],'axes':ca,'passed':all(x['passed'] for x in ca.values())})
    corner_pass=sum(x['passed'] for x in corner_results);corner_required=2 if saved['mode']=='fixture' else 12
    primary={'axes':axes,'combined':{'pooled':pooled_metrics,'wins_vs_zero':combined_wins,'cases':len(primary_items),'better_than_controls':better},'body_x_upper_safeguard':{'value':4.18,'axes':upper_axes,'passed':all(x['passed'] for x in upper_axes.values())},'corner_results':corner_results,'corners_passed':corner_pass,'corners_required':corner_required,'passed':all(v['passed'] for v in axes.values()) and pooled_metrics['normal']<pooled_metrics['zero'] and combined_wins>=threshold and better==3 and all(v['passed'] for v in upper_axes.values()) and corner_pass>=corner_required}
    contacts={'mean_normal_f1':float(np.mean([r['contacts']['normal_f1'] for r in primary_items])),'mean_zero_f1':float(np.mean([r['contacts']['zero_f1'] for r in primary_items])),'normal_better':sum(r['contacts']['normal_f1']>r['contacts']['zero_f1'] for r in primary_items),'cases':len(primary_items)}
    report={'schema':'eight-hour-fixed-fov-autonomous-grooming-result-v1','status':'fixture_completed' if saved['mode']=='fixture' else 'completed','protocol_mode':saved['mode'],'active_training_seconds':elapsed,'candidates':state['next_id'],'accepted_candidates':accepted,'training_frames':state['stats']['n'],'new_model_sha256':file_sha(temp/'model_new.npz'),'primary':primary,'contact_summary':contacts,'audit':{'accepted_total':accepted,'audited_count':audit['audited_count'],'is_exhaustive':audit['is_exhaustive'],'sample_ids':audit['sample_ids']},'tests':results,'limitations':['Training uses fixed-FOV35 synthetic cameras, balanced geometry and supervised teacher angles.','Replay reconstructs the observed action from 72 coefficients; it does not invent a novel action.','Contacts follow kinematic qpos; there are no actuators, forces, muscles or closed-loop correction.','Synthetic model, not a biological brain or mirror-neuron evidence.']}
    save_json(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('\n'.join(['СЕРИЯ 83: 8 ЧАСОВ FIXED-FOV35 EDGE ОБУЧЕНИЯ И AUTONOMOUS REPLAY',f'Primary: {"ВЫПОЛНЕН" if primary["passed"] else "НЕ ВЫПОЛНЕН"}.',f'Pooled normal/matched/zero: {pooled_metrics["normal"]:.6f}/{pooled_metrics["matched"]:.6f}/{pooled_metrics["zero"]:.6f}.',f'Controls shuffled/static/closed: {pooled_metrics["shuffled"]:.6f}/{pooled_metrics["static"]:.6f}/{pooled_metrics["closed"]:.6f}.',f'Body X 4,18 safeguard: {"ВЫПОЛНЕН" if primary["body_x_upper_safeguard"]["passed"] else "НЕ ВЫПОЛНЕН"}.',f'Corners passed: {corner_pass}/{len(corners)}.',f'Contact F1 normal/zero: {contacts["mean_normal_f1"]:.6f}/{contacts["mean_zero_f1"]:.6f}.',*report['limitations']])+'\n',encoding='utf-8-sig')
    verify_pins(proto,saved);psha=sha(json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8'));save_json(temp/'complete.json',{'protocol_sha256':psha,'candidates':state['next_id'],'files':output_manifest(temp)});temp.rename(out);verify_result(out,saved,state);return out


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
                        expected,_=broad_candidate(ident)
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
        action=simpledialog.askinteger('Серия 83: fixed-FOV35 autonomous grooming','Ровно 8 часов: наблюдение видимых трёх суставов каждой передней лапы с обязательными RGB guards. Введите номер:\n1: начать новую серию\n2: продолжить серию\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
        if action is None:print('Выбор отменён.');return
        if action in (2,3):
            folder=filedialog.askdirectory(title='Выберите папку серии fixed_fov_autonomous_grooming_eight_hour_...',initialdir=initial(ROOT),parent=root)
            if not folder:print('Выбор отменён.');return
            if action==2:process(folder)
            else:request_pause(folder)
            return
        messagebox.showinfo('Предыдущая короткая проба','Выберите папку результата короткой пробы 51 для закрепления исходной конфигурации. Её wing-only модель не сравнивается с grooming-выходами. В папке нужны metadata.json, model_six_axes.npz и input. Старые данные не изменяются.',parent=root)
        previous=filedialog.askdirectory(title='Папка результата предыдущей пробы user_wing_learning_...',initialdir=initial(BASELINE_ROOT),parent=root)
        if not previous:print('Выбор отменён.');return
        fresh=prepared_holdouts()
        messagebox.showinfo('Десять проверочных движений закреплены','Программа создала или проверила десять новых grooming движений 261–270 с seed 8302. После обучения каждое проверяется на 16 fixed-FOV35 geometry corners, включая body X=4,18. Выбирать JSON вручную не нужно.',parent=root)
        answer=messagebox.askokcancel('Время обучения','Запустить ровно 8 часов активного обучения?\nПроверка десяти движений после обучения займёт дополнительное время.',parent=root)
        if not answer:print('Выбор отменён.');return
        hours=8
        messagebox.showinfo('Перед запуском','Используются 2 вычислительных процесса. Работа в Word может замедлиться. При свободной RAM меньше 4 ГиБ или месте на диске меньше 2 ГиБ расчёт остановится с сохранённой последней партией. Для паузы откройте этот BAT ещё раз и выберите 3.',parent=root)
        folder=ROOT/('fixed_fov_autonomous_grooming_eight_hour_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
        start(folder,previous,fresh,hours)
    finally:root.destroy()


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--choose',action='store_true');g.add_argument('--new');g.add_argument('--resume');g.add_argument('--pause')
    p.add_argument('--previous');p.add_argument('--fresh',nargs='+');p.add_argument('--hours',type=int,choices=(8,),default=8)
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
