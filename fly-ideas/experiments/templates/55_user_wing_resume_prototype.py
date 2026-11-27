#!/usr/bin/env python3
"""DEVELOPER FIXTURE ONLY: at most eight sequences, not a long-running tool.

Exercises series 53 generation and 54 SQLite checkpoints across processes.
No production resource controls, pause UI, old-model comparison or BAT yet.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import multiprocessing
import os
from pathlib import Path
import platform
import sqlite3
import sys
import time
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
PIN={
 '38_two_flies_observation.py':'2f7d4ed860abe2cd97aec19ce93012d608501fa85acbfd6ae7aec9b46d673290',
 '44_two_flies_large_study.py':'f90e6633c0115b9f3faf21aae3b1ecdfb6dbf29308ac4ad5e4dc588b1ec2e364',
 '47_two_flies_imitation_learning.py':'ae56f491742eb5053ab0a13dc53f6cc906195ea173f8d1f555631d343fe27253',
 '50_two_flies_wing_studio_pilot.py':'768b3c6b940e803b120340012c069794c7bb7292dcd81c0db0f81fca987ac6ed',
 '51_two_flies_user_trajectory_learning.py':'2c7e99c9d8f2b3b5a2d33ab119acf78b11b39cd4b079ac564747c62c5f86e5c6',
 '53_long_user_wing_stimuli.py':'c83be62e18636beaf82f343ce25eb8a67e01c1a97f2374b950793a2f19ca4f1b',
 '54_user_wing_checkpoint.py':'ac5d3ff333692e57739895fbe0600954ec00ce543d6a172d2636f34c4aa9b375',
}

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def load(name,filename):
    path=HERE/filename
    if file_sha(path)!=PIN[filename]:raise ValueError(f'Скрипт {filename} отличается от закреплённого.')
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def modules():
    for name,expected in PIN.items():
        if file_sha(HERE/name)!=expected:raise ValueError(f'Скрипт {name} отличается от закреплённого.')
    return (load('proto_stim','53_long_user_wing_stimuli.py'),load('proto_checkpoint','54_user_wing_checkpoint.py'),
            load('proto_base','51_two_flies_user_trajectory_learning.py'),load('proto_lock','44_two_flies_large_study.py'))

def make_protocol(sources,limit):
    return {'schema':'wing-resume-prototype-v1','mode':'developer-only','limit':limit,'workers':2,'batch':2,
        'script_sha256':file_sha(__file__),'dependency_sha256':PIN,
        'python':platform.python_version(),'versions':{p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},
        'source_sha256':{name:sha(raw) for name,raw in sorted(sources.items())}}

def split_from_sources(sources,stim):
    def group(prefix):
        keys=sorted(k for k in sources if k.startswith(prefix+'_') and k.endswith('.json'))
        result=[]
        for i,key in enumerate(keys,1):
            if key!=f'{prefix}_{i:03}.json':raise ValueError('Входы не имеют последовательных имён.')
            t,angles=stim.sample_trajectory(json.loads(sources[key].decode('utf-8-sig')))
            result.append({'id':i,'times':t,'angles_deg':angles,'motion_sha256':stim.motion_hash(angles)})
        return result
    train,test=group('train'),group('test')
    if not 2<=len(train)<=50 or not 1<=len(test)<=20:raise ValueError('Некорректное разделение источников.')
    hashes=[x['motion_sha256'] for x in train+test]
    if len(set(hashes))!=len(hashes):raise ValueError('Совпадают полные движения обучения и проверки.')
    return train,test

STIM=None;PILOT=None;SCENE=None;TRAIN=None;HOLD=None

def worker_init(train,hold):
    global STIM,PILOT,SCENE,TRAIN,HOLD
    STIM=load('worker_stim','53_long_user_wing_stimuli.py');studio=load('worker_studio','50_two_flies_wing_studio_pilot.py')
    PILOT=load('worker_pilot','47_two_flies_imitation_learning.py');engine=load('worker_engine','38_two_flies_observation.py')
    PILOT.lower_priority();SCENE=studio.Scene(engine);TRAIN=train;HOLD=hold

def generate(ident):
    spec,degrees=STIM.candidate(TRAIN,ident)
    if spec['sampled_motion_sha256'] in HOLD:
        return {'id':ident,'status':'rejected','frames':0,'motion_sha256':spec['sampled_motion_sha256'],'rgb_sha256':None,'spec':spec},None,None
    images=SCENE.render(degrees*np.pi/180,distance=spec['distance'],offset=spec['side_offset'])
    x=PILOT.history(images);y=degrees[2:]*np.pi/180
    return {'id':ident,'status':'accepted','frames':len(y),'motion_sha256':spec['sampled_motion_sha256'],'rgb_sha256':sha(images.tobytes()),'spec':spec},x,y

def process(folder,max_batches=None):
    stim,ck,base,large=modules();folder=Path(folder).resolve();dbpath=folder/'prototype.sqlite3'
    if not dbpath.is_file():raise ValueError('Нет базы прототипа.')
    large.job_guard()
    with large.RunLock(folder):
        with sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro',uri=True) as db:
            record=db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()
        if not record:raise ValueError('Нет протокола.')
        saved=json.loads(record[0]);limit=saved.get('limit')
        if type(limit)!=int or not 2<=limit<=8:raise ValueError('Этот прототип допускает только 2–8 последовательностей.')
        # Current software, exact versions, limit and saved source hashes must match.
        expected=make_protocol({},limit);expected['source_sha256']=saved.get('source_sha256')
        state=ck.open_verified(dbpath,expected);train,test=split_from_sources(state['sources'],stim);hold={x['motion_sha256'] for x in test}
        start=time.monotonic();elapsed=state['elapsed'];done=state['next_id'];stats=state['stats'];batches=0
        if done>limit:raise ValueError('Позиция выше лимита прототипа.')
        with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(train,hold)) as pool:
            while done<limit and (max_batches is None or batches<max_batches):
                ids=list(range(done,min(done+2,limit)));generated=list(pool.map(generate,ids));records=[]
                for ident,(rec,x,y) in zip(ids,generated):
                    expected_spec,_=stim.candidate(train,ident)
                    if rec['id']!=ident or rec['spec']!=expected_spec or rec['motion_sha256']!=expected_spec['sampled_motion_sha256']:
                        raise ValueError('Получен результат не из закреплённого плана.')
                    rejected=rec['motion_sha256'] in hold
                    if rejected!=(rec['status']=='rejected'):raise ValueError('Ошибка блокировки совпадения проверки и обучения.')
                    if not rejected:
                        if x is None or y is None or x.shape!=(rec['frames'],576) or y.shape!=(rec['frames'],6):raise ValueError('Некорректная партия.')
                        base.update_stats(stats,x,y)
                    elif x is not None or y is not None:raise ValueError('Проверочный кандидат не должен передавать кадры обучения.')
                    records.append(rec)
                # A changed script is never mixed into an existing checkpoint.
                for name,expected_hash in PIN.items():
                    if file_sha(HERE/name)!=expected_hash:raise ValueError('Закреплённый файл изменился, партия не сохранена.')
                if file_sha(__file__)!=saved['script_sha256']:raise ValueError('Прототип изменился, партия не сохранена.')
                ck.commit_batch(dbpath,saved,done,records,stats,elapsed+time.monotonic()-start)
                done+=len(ids);batches+=1
                print(f'CHECKPOINT {done}/{limit}',flush=True)
        if done<limit:
            print(json.dumps({'status':'prototype_paused','done':done,'frames':stats['n']},ensure_ascii=False),flush=True);return
        if stats['n']<2:raise ValueError('Недостаточно тренировочных кадров.')
        mean,scale,intercept,weights=base.fit(stats)
        studio=load('eval_studio','50_two_flies_wing_studio_pilot.py');pilot=load('eval_pilot','47_two_flies_imitation_learning.py')
        scene=studio.Scene(load('eval_engine','38_two_flies_observation.py'));report=[]
        for item in test:
            y=item['angles_deg']*np.pi/180;im=scene.render(y);x=pilot.history(im)
            pred=np.clip((x-mean)/scale@weights+intercept,-math.pi/3,math.pi/3)
            scores=base.scores(y[2:],pred,intercept);overlap=stim.assess_history_overlap(train,[item])[0]
            report.append({'test_id':item['id'],'frames':len(y)-2,'model_rmse':scores['new']['rmse_rad'],
              'zero_rmse':scores['zero']['rmse_rad'],'mean_rmse':scores['training_mean']['rmse_rad'],
              'overlap_original_train_under_1_deg':overlap['under_1_deg']})
        print(json.dumps({'status':'prototype_completed','done':done,'frames':stats['n'],'test':report},ensure_ascii=False),flush=True)

def start(folder,train_paths,test_paths,limit,max_batches=None):
    stim,ck,_,_=modules()
    if type(limit)!=int or not 2<=limit<=8:raise ValueError('Только локальная проба от 2 до 8 последовательностей.')
    # Parse and snapshot the selected files before creating the new folder.
    stim.prepare_split(train_paths,test_paths)
    sources={}
    for role,paths in (('train',train_paths),('test',test_paths)):
        for i,path in enumerate(paths,1):
            raw,t,angles=stim.load_trajectory(path)
            sources[f'{role}_{i:03}.json']=raw
    split_from_sources(sources,stim)
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    ck.create(folder/'prototype.sqlite3',make_protocol(sources,limit),sources)
    process(folder,max_batches)

def main():
    p=argparse.ArgumentParser(description='Только короткий прототип для разработчика; не длительная серия.')
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--new');g.add_argument('--resume')
    p.add_argument('--train',nargs='+');p.add_argument('--test',nargs='+');p.add_argument('--limit',type=int,default=6);p.add_argument('--batches',type=int)
    a=p.parse_args()
    if a.batches is not None and not 1<=a.batches<=4:p.error('Для прототипа допустимо 1–4 партии.')
    if a.new:
        if not a.train or not a.test:p.error('Нужны --train и --test.')
        start(a.new,a.train,a.test,a.limit,a.batches)
    else:
        if a.train or a.test:p.error('При продолжении используются только сохранённые копии.')
        process(a.resume,a.batches)

if __name__=='__main__':
    multiprocessing.freeze_support()
    try:main()
    except Exception as exc:
        print(f'ОШИБКА ПРОТОТИПА: {type(exc).__name__}: {exc}',file=sys.stderr,flush=True);sys.exit(1)
