#!/usr/bin/env python3
"""Eight-hour supervised whole-body observation: wings, foreleg grooming and locomotion.

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
AXES = ('left_wing','right_wing','left_foreleg','right_foreleg','body_forward','body_lateral')
MIN_RAM = 4*1024**3
MIN_DISK = 2*1024**3
ROOT = Path('workspace/runs/ideas/i-observational/whole-body-broad-eight-hour')
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
    if hours != 8 or type(hours)!=int: raise ValueError('Серия 73 имеет ровно 8 часов активного обучения.')
    if fixture_limit is not None and (type(fixture_limit)!=int or not 2<=fixture_limit<=8):
        raise ValueError('Техническая проба ограничена 2–8 кандидатами.')
    return {'schema':'eight-hour-whole-body-observation-v2','mode':'fixture' if fixture_limit is not None else 'long',
            'budget_seconds':hours*3600,'fixture_limit':fixture_limit,'workers':2,'batch':2,
            'script_sha256':file_sha(__file__),'dependencies':{**proto.PIN,**PIN},
            'python':platform.python_version(),
            'versions':{p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},
            'source_sha256':source_sha,'labels':labels,
            'outputs':list(AXES),'command_units':'rad-equivalent; body commands render as planar displacement',
            'training_generator':{'seed':7301,'families':['piecewise5','piecewise9','harmonic','chirp'],'command_clip_deg_equivalent':[-55,55],'base_distance':4.0,'base_side_offset':0.0},
            'primary_rule':'on movements 81-90: pooled new RMSE below zero and training mean, with at least 7/10 paired wins against each'}


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

class WholeBodyScene:
    """Kinematic demonstrator with two wings, two forelegs and planar body motion."""
    def __init__(self,engine):
        import mujoco
        xml=engine.XML
        for side in ('left','right'):
            xml=xml.replace(f'<joint name="{side}_hinge" type="hinge" axis="1 0 0"/>',
                            f'<joint name="{side}_wing_cmd" type="hinge" axis="1 0 0"/>')
        marker='  </body>\n </body>\n</worldbody>'
        legs='  </body>\n  <body name="left_foreleg" pos="-0.48 0.22 -0.08">\n   <joint name="left_foreleg_cmd" type="hinge" axis="1 0 0"/>\n   <geom name="demo_left_foreleg" type="capsule" fromto="0 0 0 -0.52 0.12 -0.35" size="0.045" rgba="0.28 0.22 0.16 1"/>\n  </body>\n  <body name="right_foreleg" pos="-0.48 -0.22 -0.08">\n   <joint name="right_foreleg_cmd" type="hinge" axis="1 0 0"/>\n   <geom name="demo_right_foreleg" type="capsule" fromto="0 0 0 -0.52 -0.12 -0.35" size="0.045" rgba="0.28 0.22 0.16 1"/>\n  </body>\n </body>\n</worldbody>'
        if marker not in xml: raise ValueError('Не удалось добавить передние лапы в сцену.')
        xml=xml.replace(marker,legs)
        self.mujoco=mujoco;self.engine=engine;self.model=mujoco.MjModel.from_xml_string(xml);self.data=mujoco.MjData(self.model)
        self.body=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_BODY,'demonstrator')
        names=('left_wing_cmd','right_wing_cmd','left_foreleg_cmd','right_foreleg_cmd')
        self.joints=[self.model.jnt_qposadr[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,n)] for n in names]
        self.cams=[engine.camera([.85,y,.46],[4,0,.55],48,32) for y in (.13,-.13)]
    def render(self,commands,distance=4.,offset=0.):
        commands=np.asarray(commands,float)
        if commands.ndim!=2 or commands.shape[1]!=6 or not np.isfinite(commands).all(): raise ValueError('Неверные whole-body команды.')
        images=[]
        for vec in commands:
            self.data.qpos[self.joints]=vec[:4]
            self.model.body_pos[self.body]=[distance+.70*vec[4],offset+.70*vec[5],.4]
            self.mujoco.mj_forward(self.model,self.data)
            images.append(np.stack([self.engine.render(self.model,self.data,c,True) for c in self.cams]))
        return np.stack(images)

def broad_motion_hash(degrees):
    normalized=np.round((np.asarray(degrees,dtype=float)*np.pi/180)*180/np.pi,7);normalized[normalized==0]=0
    return hashlib.sha256(np.asarray(normalized,dtype='<f8').tobytes()).hexdigest()

def broad_candidate(ident):
    if type(ident)!=int or not 0<=ident<2**32:raise ValueError('Неверный broad candidate id.')
    rng=np.random.default_rng(np.random.SeedSequence([7301,ident]));t=np.arange(51,dtype=float)/25;family=('piecewise5','piecewise9','harmonic','chirp')[ident%4]
    if family.startswith('piecewise'):
        count=5 if family=='piecewise5' else 9;knots=np.linspace(0,2,count);values=rng.integers(-55,56,size=(count,6)).astype(float);degrees=np.stack([np.interp(t,knots,values[:,j]) for j in range(6)],axis=1);parameters={'keyframes_deg':values.astype(int).tolist()}
    else:
        offset=rng.uniform(-12,12,6);amplitude=rng.uniform(18,48,6);phase=rng.uniform(0,2*np.pi,6)
        if family=='harmonic':
            frequency=rng.uniform(.4,3.2,6);degrees=offset+amplitude*np.sin(2*np.pi*t[:,None]*frequency+phase);parameters={'offset_deg':offset.tolist(),'amplitude_deg':amplitude.tolist(),'phase_rad':phase.tolist(),'frequency_hz':frequency.tolist()}
        else:
            f0=rng.uniform(.25,1.2,6);f1=rng.uniform(1.8,4.0,6);sweep=(f1-f0)/2;degrees=offset+amplitude*np.sin(phase+2*np.pi*(t[:,None]*f0+.5*t[:,None]**2*sweep));parameters={'offset_deg':offset.tolist(),'amplitude_deg':amplitude.tolist(),'phase_rad':phase.tolist(),'f0_hz':f0.tolist(),'f1_hz':f1.tolist()}
    # Opposed foreleg commands create a visible, repeatable grooming/rubbing bout.
    degrees[:,3]=-degrees[:,2]+.15*degrees[:,3]
    before=degrees.copy();degrees=np.clip(before,-55,55);distance=4.;side=0.;spec={'protocol':'broad-whole-body-v2','sequence_id':ident,'generator_seed':[7301,ident],'family':family,'parameters':parameters,'foreleg_pattern':'opposed grooming: right=-left+0.15*independent','distance':distance,'side_offset':side,'clipped_values':int(np.count_nonzero(before!=degrees)),'sampled_motion_sha256':broad_motion_hash(degrees)};return spec,degrees

def worker_init(train,hold):
    del train
    global BROAD_STIM,BROAD_PILOT,BROAD_SCENE,BROAD_HOLD
    worker=load('55_user_wing_resume_prototype.py','broad_worker_proto');BROAD_STIM=worker.load('broad_worker_stim','53_long_user_wing_stimuli.py');studio=worker.load('broad_worker_studio','50_two_flies_wing_studio_pilot.py');BROAD_PILOT=worker.load('broad_worker_pilot','47_two_flies_imitation_learning.py');engine=worker.load('broad_worker_engine','38_two_flies_observation.py');BROAD_PILOT.lower_priority();BROAD_SCENE=WholeBodyScene(engine);BROAD_HOLD=hold

def worker_generate(ident):
    spec,degrees=broad_candidate(ident)
    if spec['sampled_motion_sha256'] in BROAD_HOLD:return {'id':ident,'status':'rejected','frames':0,'motion_sha256':spec['sampled_motion_sha256'],'rgb_sha256':None,'spec':spec},None,None
    images=BROAD_SCENE.render(degrees*np.pi/180,distance=spec['distance'],offset=spec['side_offset']);x=BROAD_PILOT.history(images);y=degrees[2:]*np.pi/180
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
    folder=ROOT/'prepared_holdouts_seed_7302';folder.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(7302);paths=[]
    for i in range(1,11):
        path=folder/f'holdout_{80+i:03d}.json';count=5 if i<=5 else 9
        values=rng.integers(-55,56,size=(count,6)).astype(int);values[:,3]=np.clip(-values[:,2]+np.rint(.15*values[:,3]).astype(int),-55,55)
        obj={'schema':'fly-wings-trajectory-v1','semantic_schema':'fly-whole-body-six-command-v1','channels':list(AXES),'fps':25,'duration_s':2,
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


def evaluate(folder,state,saved,elapsed,proto,ev,stim,base,large):
    folder=Path(folder);out=folder/'result'
    if out.exists():
        verify_result(out,saved,state)
        return out
    train,tests=proto.split_from_sources(state['sources'],stim)
    labels={x['copy']:x for x in saved['labels']}
    mean,scale,intercept,weights=base.fit(state['stats'])
    new=ev.checked_model({'mean':mean,'scale':scale,'intercept':intercept,'weights':weights})
    studio=proto.load('long_studio','50_two_flies_wing_studio_pilot.py')
    engine=proto.load('long_engine','38_two_flies_observation.py')
    pilot=proto.load('long_pilot','47_two_flies_imitation_learning.py')
    scene=WholeBodyScene(engine)
    accepted,records=sampled_records(folder/'study.sqlite3',len(train))
    audit=overlap_sample_broad(tests,records,cap=128)
    audit['accepted_total']=accepted;audit['is_exhaustive']=audit['audited_count']==accepted
    temp=folder/('evaluation_incomplete_'+uuid.uuid4().hex);temp.mkdir()
    np.savez_compressed(temp/'model_new.npz',**new)
    summary=[]
    for item,overlap in zip(tests,audit['tests']):
        free_check(large,folder,saved['mode']=='fixture')
        ident=item['id'];name=f'test_{ident:03d}.json';label=labels[name]
        original=label.get('original_basename','');display_id=int(original[8:11]) if original.startswith('holdout_') and original[8:11].isdigit() else ident
        obj=json.loads(state['sources'][name].decode('utf-8-sig'))
        truth=item['angles_deg']*np.pi/180;images=scene.render(truth)
        features=ev.feature_history(images);newpred=np.clip((features-new['mean'])/new['scale']@new['weights']+new['intercept'],-np.pi*55/180,np.pi*55/180)
        predictions={'new':newpred,'zero':np.zeros_like(newpred),'training_mean':np.broadcast_to(new['intercept'],newpred.shape)}
        metrics={name:{'rmse_rad':float(np.sqrt(np.mean((pred-truth[2:])**2))),'axis_rmse_rad':{axis:float(np.sqrt(np.mean((pred[:,j]-truth[2:,j])**2))) for j,axis in enumerate(AXES)}} for name,pred in predictions.items()}
        compared={'teacher_rad':truth[2:],'predictions':predictions,'metrics':metrics}
        td=temp/f'test_{ident:03d}';td.mkdir()
        with (td/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['time_s']+[f'teacher_{a}_rad' for a in AXES]+
                [f'{model}_{a}_rad' for model in ('new','zero','training_mean') for a in AXES])
            for k,t in enumerate(item['times'][2:]):
                w.writerow([float(t),*map(float,compared['teacher_rad'][k]),
                            *(float(v) for model in ('new','zero','training_mean') for v in compared['predictions'][model][k])])
        raw=ev.feature_history(images)
        base.save_views(td,images,item['times'],pilot,raw,(raw-mean)/scale)
        scores=base.scores(truth[2:],newpred,intercept)
        playback={'schema':'fly-whole-body-result-v1','fps':25,'duration_s':obj['duration_s'],'trajectory':obj,'channels':list(AXES),
                  'samples':[{'t':float(t),'teacher_deg':list(map(float,degrees)),
                              'prediction_deg':None if k<2 else list(map(float,newpred[k-2]*180/np.pi))}
                             for k,(t,degrees) in enumerate(zip(item['times'],item['angles_deg']))],
                  'method':'supervised ridge; predictions recorded during observation, then replayed',
                  'user_metrics':scores,'holdout_metrics':scores,'holdout_label':'Эта проверочная траектория',
                  'limitations':['Искусственные глаза и кинематика, не биологическое зрение.',
                                 'Playback воспроизводит записанные прогнозы, не автономную генерацию.']}
        save_json(td/'playback.json',playback)
        result={'test_id':display_id,'internal_test_id':ident,'role':label['role'],'frames':len(truth)-2,'metrics':compared['metrics'],
                'overlap_under_0_001_deg':overlap['under_0_001_deg'],
                'overlap_under_1_deg':overlap['under_1_deg'],'overlap_under_5_deg':overlap['under_5_deg']}
        save_json(td/'metrics.json',result);summary.append(result)
        print(f'Проверено движение {ident}/{len(tests)}.',flush=True)
    status='fixture_completed' if saved['mode']=='fixture' else 'completed'
    primary_items=[item for item in summary if item['role']=='new_test']
    if not primary_items: raise ValueError('Нет заранее закреплённых whole-body holdout.')
    total_frames=sum(item['frames'] for item in primary_items)
    pooled={name:float(np.sqrt(sum(item['frames']*item['metrics'][name]['rmse_rad']**2 for item in primary_items)/total_frames)) for name in ('new','zero','training_mean')}
    paired={name:sum(item['metrics']['new']['rmse_rad']<item['metrics'][name]['rmse_rad'] for item in primary_items) for name in ('zero','training_mean')}
    primary={'pooled_new_below_zero':pooled['new']<pooled['zero'],'pooled_new_below_training_mean':pooled['new']<pooled['training_mean'],
             'paired_wins_vs_zero':paired['zero'],'paired_wins_vs_training_mean':paired['training_mean'],'holdouts':len(primary_items)}
    primary['passed']=primary['pooled_new_below_zero'] and primary['pooled_new_below_training_mean'] and paired['zero']>=7 and paired['training_mean']>=7
    report={'status':status,'protocol_mode':saved['mode'],'active_training_seconds':elapsed,
            'candidates':state['next_id'],'accepted_candidates':accepted,'training_frames':state['stats']['n'],
            'baseline_source_sha256':sha(state['sources']['baseline_model.npz']),
            'new_model_sha256':file_sha(temp/'model_new.npz'),
            'pooled_rmse_rad_equivalent':pooled,'primary':primary,
            'audit':{'accepted_total':accepted,'audited_count':audit['audited_count'],
                     'is_exhaustive':audit['is_exhaustive'],'sample_ids':audit['sample_ids']},'tests':summary,
            'limitations':['Учительские углы используются при обучении; это supervised ridge, не обучение нейронов.',
                           'Искусственные глаза и кинематическая сцена, не реальная муха или её мозг.',
                           'Движения 81–90 зафиксированы seed 7302 до whole-body training и остаются синтетическими.',
                           'Шесть выходов: два крыла, две передние лапы и два направления корпуса; старая wing-only модель семантически несопоставима и не оценивается.',
                           'Выборочный аудит сравнивает только углы, не зрительные входы; он может пропустить совпадение.',
                           'Playback записывает предсказания во время показа, а не автономно создаёт движение.']}
    save_json(temp/'summary.json',report)
    lines=['ВОСЬМИЧАСОВОЕ ОБУЧЕНИЕ WHOLE-BODY НАБЛЮДЕНИЮ',
           f'Режим: {status}; активное время обучения: {elapsed/3600:.4f} ч.',
           f'Кандидатов: {state["next_id"]}; принято: {accepted}; обучающих кадров: {state["stats"]["n"]}.',
           f'Проверка похожести углов: {audit["audited_count"]} из {accepted} принятых движений; полная: {audit["is_exhaustive"]}.',
           'RMSE в rad-equivalent единицах: новая модель / ноль / средняя команда обучения.',
           f'Pooled: {pooled["new"]:.6f} / {pooled["zero"]:.6f} / {pooled["training_mean"]:.6f}.',
           f'Paired wins new: против нуля {paired["zero"]}/{len(primary_items)}; против средней {paired["training_mean"]}/{len(primary_items)}.',
           f'Основной критерий 7/10 и оба pooled сравнения: {"ВЫПОЛНЕН" if primary["passed"] else "НЕ ВЫПОЛНЕН"}.']
    for item in summary:
        m=item['metrics']; lines.append(f'Тест {item["test_id"]} ({item["role"]}), кадров {item["frames"]}: '+ ' / '.join(f'{m[k]["rmse_rad"]:.6f}' for k in ('new','zero','training_mean')))
        for axis in AXES:
            lines.append('  '+axis+': '+' / '.join(f'{m[k]["axis_rmse_rad"][axis]:.6f}' for k in ('new','zero','training_mean')))
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
        action=simpledialog.askinteger('Серия 73: восемь часов whole-body наблюдения','Ровно 8 часов: крылья, потирание передних лап и перемещение корпуса. Введите номер:\n1: начать новую серию\n2: продолжить серию\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
        if action is None:print('Выбор отменён.');return
        if action in (2,3):
            folder=filedialog.askdirectory(title='Выберите папку серии whole_body_broad_eight_hour_...',initialdir=initial(ROOT),parent=root)
            if not folder:print('Выбор отменён.');return
            if action==2:process(folder)
            else:request_pause(folder)
            return
        messagebox.showinfo('Предыдущая короткая проба','Выберите папку результата короткой пробы 51 для закрепления исходной конфигурации. Её wing-only модель не сравнивается с whole-body выходами. В папке нужны metadata.json, model_six_axes.npz и input. Старые данные не изменяются.',parent=root)
        previous=filedialog.askdirectory(title='Папка результата предыдущей пробы user_wing_learning_...',initialdir=initial(BASELINE_ROOT),parent=root)
        if not previous:print('Выбор отменён.');return
        fresh=prepared_holdouts()
        messagebox.showinfo('Десять проверочных движений закреплены','Программа создала или проверила десять фиксированных whole-body движений 81–90 с seed 7302. Они копируются в новую серию до обучения; выбирать JSON вручную не нужно.',parent=root)
        answer=messagebox.askokcancel('Время обучения','Запустить ровно 8 часов активного обучения?\nПроверка десяти движений после обучения займёт дополнительное время.',parent=root)
        if not answer:print('Выбор отменён.');return
        hours=8
        messagebox.showinfo('Перед запуском','Используются 2 вычислительных процесса. Работа в Word может замедлиться. При свободной RAM меньше 4 ГиБ или месте на диске меньше 2 ГиБ расчёт остановится с сохранённой последней партией. Для паузы откройте этот BAT ещё раз и выберите 3.',parent=root)
        folder=ROOT/('whole_body_broad_eight_hour_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
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
