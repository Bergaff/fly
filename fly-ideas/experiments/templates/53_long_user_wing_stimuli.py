#!/usr/bin/env python3
"""Deterministic stimulus generator for a future long user-wing study.

This is NOT a 4–8 hour runner. The caller must handle split validation,
checkpointing, limits, training, evaluation and user interaction.
"""
from __future__ import annotations
import hashlib
import json
import math
from pathlib import Path
import numpy as np

SEED = 20261108
FPS = 25
ANGLE_LIMIT_DEG = 60.0
PROTOCOL = 'wing-user-long-stimuli-v1'


def sample_trajectory(obj):
    """Validate and sample the same JSON trajectory format used by series 51."""
    if not isinstance(obj, dict) or obj.get('schema') != 'fly-wings-trajectory-v1' or obj.get('fps') != FPS:
        raise ValueError('Нужен JSON траектории редактора крыльев на 25 кадров/с.')
    duration, frames = obj.get('duration_s'), obj.get('keyframes')
    real = lambda x: isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
    if not real(duration) or not .5 <= duration <= 10 or abs(round(duration*FPS)-duration*FPS)>1e-7 or not isinstance(frames,list) or not 2 <= len(frames) <= 200:
        raise ValueError('Неверная длительность или число ключевых кадров.')
    times=[]; angles=[]
    for item in frames:
        if not isinstance(item,dict) or not real(item.get('t')) or not isinstance(item.get('angles_deg'),list) or len(item['angles_deg']) != 6 or any(not real(x) or abs(x)>ANGLE_LIMIT_DEG for x in item['angles_deg']):
            raise ValueError('Неверный ключевой кадр.')
        times.append(float(item['t'])); angles.append(item['angles_deg'])
    if abs(times[0])>1e-9 or abs(times[-1]-duration)>1e-9 or any(b-a<1e-6 for a,b in zip(times,times[1:])):
        raise ValueError('Время ключевых кадров должно строго возрастать от нуля до длительности.')
    t=np.arange(int(round(duration*FPS))+1,dtype=float)/FPS
    y=np.asarray(angles,dtype=float)
    return t, np.stack([np.interp(t,times,y[:,j]) for j in range(6)],axis=1)


def load_trajectory(path):
    path=Path(path)
    if not path.is_file() or path.stat().st_size>1024*1024:raise ValueError('Нет JSON траектории или файл больше 1 МиБ.')
    raw=path.read_bytes()
    return raw, *sample_trajectory(json.loads(raw.decode('utf-8-sig')))


def motion_hash(degrees):
    """Match the sampled-motion hash of series 51, including its rounding rule."""
    degrees=np.asarray(degrees,dtype=float)
    if degrees.ndim!=2 or degrees.shape[1]!=6 or not 3<=len(degrees)<=251 or not np.isfinite(degrees).all():raise ValueError('Некорректный массив движения.')
    # Series 51 samples degrees, converts to radians, then converts back to degrees.
    normalized=np.round((degrees*np.pi/180)*180/np.pi,7); normalized[normalized==0]=0
    return hashlib.sha256(np.asarray(normalized,dtype='<f8').tobytes()).hexdigest()


def prepare_split(train_paths, test_paths):
    """Reject exact sampled full-motion duplicates, including across splits."""
    if not 2<=len(train_paths)<=50 or not 1<=len(test_paths)<=20:raise ValueError('Нужно 2–50 обучающих и 1–20 проверочных траекторий.')
    train=[];test=[];seen={}
    for role,paths,output in (('train',train_paths,train),('test',test_paths,test)):
        for number,path in enumerate(paths,1):
            raw,t,angles=load_trajectory(path); digest=motion_hash(angles)
            if digest in seen:raise ValueError(f'Совпадает полное движение {role}_{number:03d} и {seen[digest]}.')
            seen[digest]=f'{role}_{number:03d}'
            output.append({'id':number,'source_sha256':hashlib.sha256(raw).hexdigest(),'motion_sha256':digest,'times':t,'angles_deg':angles})
    return train,test


def candidate(train, sequence_id):
    """Generate independently of holdout values: first originals, then variations.

    Time is linearly resampled, endpoint-held if the factor exceeds one.
    Pose clipping is explicit in metadata, as is camera-scene variation.
    """
    if not train or type(sequence_id) is not int or not 0 <= sequence_id < 2**32:
        raise ValueError('Неверный номер последовательности.')
    source_index=sequence_id % len(train); source=train[source_index]
    t=source['times']; base=source['angles_deg']
    if sequence_id < len(train):
        scale=np.ones(6);offset=np.zeros(6);rate=1.0;reverse=False;distance=4.0;side=0.0
    else:
        rng=np.random.default_rng(np.random.SeedSequence([SEED,sequence_id]))
        scale=rng.uniform(.85,1.15,size=6);offset=rng.uniform(-5,5,size=6)
        rate=float(rng.uniform(.8,1.2));reverse=bool(rng.integers(0,2))
        distance=float(rng.uniform(3.7,4.3));side=float(rng.uniform(-.3,.3))
    sample_time=np.minimum(t*rate,t[-1]);sample_time=t[-1]-sample_time if reverse else sample_time
    warped=np.stack([np.interp(sample_time,t,base[:,j]) for j in range(6)],axis=1)
    before_clip=warped*scale+offset
    degrees=np.clip(before_clip,-ANGLE_LIMIT_DEG,ANGLE_LIMIT_DEG)
    spec={'protocol':PROTOCOL,'sequence_id':sequence_id,'source_train_id':source['id'],
          'scale':scale.tolist(),'offset_deg':offset.tolist(),'time_factor':rate,'reversed':reverse,
          'distance':distance,'side_offset':side,'clipped_values':int(np.count_nonzero(before_clip!=degrees)),
          'sampled_motion_sha256':motion_hash(degrees)}
    return spec,degrees


def accepted_candidate(train, holdout_hashes, sequence_id):
    """Block exact held-out full motions; near-duplicates and shared poses remain."""
    spec,degrees=candidate(train,sequence_id)
    if spec['sampled_motion_sha256'] in holdout_hashes:return None
    return spec,degrees
