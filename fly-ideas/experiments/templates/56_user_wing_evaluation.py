#!/usr/bin/env python3
"""Evaluation primitives for a future long study, not a user-facing runner.

The caller must select/freeze test sets, retain model/source provenance, and
write outputs atomically. Sampling overlap cannot prove a test is independent.
"""
from __future__ import annotations
import hashlib
import io
import json
import math
import zipfile
from pathlib import Path
import numpy as np

DIM=576
AXES=('left_x','left_y','left_z','right_x','right_y','right_z')
MAX_ARCHIVE=32*1024*1024
MAX_UNPACKED=64*1024*1024


def checked_model(model):
    if set(model)!={'mean','scale','intercept','weights'}:raise ValueError('Некорректный набор массивов модели.')
    out={k:np.asarray(v,dtype=np.float64).copy() for k,v in model.items()}
    for key,shape in {'mean':(DIM,),'scale':(DIM,),'intercept':(6,),'weights':(DIM,6)}.items():
        if out[key].shape!=shape or not np.isfinite(out[key]).all():raise ValueError(f'Некорректный массив {key}.')
    if np.any(out['scale']<=0):raise ValueError('Масштаб модели должен быть положительным.')
    return out


def load_series51_model(folder):
    """Verify a completed 51 model against metadata; never mutate input files."""
    folder=Path(folder);p=folder/'metadata.json';q=folder/'model_six_axes.npz'
    if (folder/'INCOMPLETE.txt').exists() or not p.is_file() or p.stat().st_size>1024*1024 or not q.is_file() or q.stat().st_size>MAX_ARCHIVE:
        raise ValueError('Не найдена завершённая модель 51 и её метаданные.')
    meta=json.loads(p.read_text(encoding='utf-8-sig'));raw=q.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if meta.get('status')!='completed' or meta.get('model_sha256')!=digest or meta.get('fps')!=25 or meta.get('history_frames')!=3 or meta.get('camera_resolution')!=[48,32]:
        raise ValueError('Модель 51 или её SHA не согласуются с метаданными.')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if sum(item.file_size for item in z.infolist())>MAX_UNPACKED:raise ValueError('Архив модели слишком велик.')
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:model=checked_model({k:z[k] for k in z.files})
    return model,digest


def feature_history(images):
    images=np.asarray(images)
    if images.dtype!=np.uint8 or images.ndim!=5 or images.shape[1:]!=(2,32,48,3) or not 3<=len(images)<=251:
        raise ValueError('Нужны RGB-кадры двух условных камер 48×32.')
    n=len(images);lum=images.astype(np.float64).mean(axis=-1)/255.0
    vectors=lum.reshape(n,2,8,4,12,4).mean(axis=(3,5)).reshape(n,192)
    return np.concatenate([vectors[2-i:n-i] for i in range(3)],axis=1)


def predict(model,x):
    model=checked_model(model);x=np.asarray(x,dtype=float)
    if x.ndim!=2 or x.shape[1]!=DIM or not np.isfinite(x).all():raise ValueError('Некорректные визуальные признаки.')
    return np.clip((x-model['mean'])/model['scale']@model['weights']+model['intercept'],-math.pi/3,math.pi/3)


def compare_models(images,teacher_rad,old_model,new_model):
    """Same held-out frames; teacher is only for scoring, never prediction."""
    teacher=np.asarray(teacher_rad,dtype=float)
    if teacher.shape!=(len(images),6) or not np.isfinite(teacher).all():raise ValueError('Некорректные углы учителя.')
    old_model=checked_model(old_model);new_model=checked_model(new_model);history=feature_history(images);truth=teacher[2:]
    preds={'old':predict(old_model,history),'new':predict(new_model,history),
           'zero':np.zeros_like(truth),'training_mean':np.broadcast_to(new_model['intercept'],truth.shape).copy()}
    metrics={}
    for name,p in preds.items():
        err=p-truth
        metrics[name]={'rmse_rad':float(np.sqrt(np.mean(err*err))),'mae_rad':float(np.mean(np.abs(err))),
                       'axis_rmse_rad':{c:float(np.sqrt(np.mean(err[:,i]**2))) for i,c in enumerate(AXES)},
                       'axis_mae_rad':{c:float(np.mean(np.abs(err[:,i]))) for i,c in enumerate(AXES)}}
    return {'teacher_rad':truth.copy(),'predictions':preds,'metrics':metrics}


def overlap_sample(stim,train,tests,records,cap=128):
    """Nearest angle histories from a deterministic, explicitly limited sample.

    Includes accepted original sequences, then evenly samples other accepted IDs.
    Does not modify any train/test/model input. A sampled audit can detect a match
    but cannot prove its absence among unsampled training variants.
    """
    if not train or not tests or type(cap)!=int or cap<len(train) or cap>1024:raise ValueError('Некорректные входы или размер аудита.')
    if not isinstance(records,list) or any(not isinstance(r,dict) or type(r.get('id'))!=int or r['id']<0 or r.get('status') not in ('accepted','rejected') for r in records):
        raise ValueError('Некорректный журнал движений.')
    ids=[r['id'] for r in records]
    if ids!=sorted(set(ids)):raise ValueError('Журнал должен содержать уникальные возрастающие номера.')
    accepted=[r for r in records if r['status']=='accepted']
    if not accepted:raise ValueError('Нет принятых движений.')
    originals=[r for r in accepted if r['id']<len(train)];other=[r for r in accepted if r['id']>=len(train)]
    count=min(len(other),cap-len(originals))
    if count==len(other):chosen=other
    elif count==0:chosen=[]
    else:chosen=[other[i] for i in np.linspace(0,len(other)-1,count,dtype=int)]
    sample=sorted(originals+chosen,key=lambda r:r['id'])
    test_hist=[];distances=[]
    for item in tests:
        y=np.asarray(item['angles_deg'],dtype=float);t=np.asarray(item['times'],dtype=float)
        if t.ndim!=1 or y.shape!=(len(t),6) or len(t)<3 or not np.isfinite(y).all() or not np.isfinite(t).all():raise ValueError('Некорректная проверочная траектория.')
        test_hist.append(np.concatenate([y[2:],y[1:-1],y[:-2]],axis=1));distances.append(np.full(len(y)-2,np.inf))
    for rec in sample:
        spec,degrees=stim.candidate(train,rec['id'])
        if rec.get('motion_sha256')!=spec['sampled_motion_sha256'] or rec.get('spec')!=spec:raise ValueError('Журнал не соответствует восстановленному движению.')
        h=np.concatenate([degrees[2:],degrees[1:-1],degrees[:-2]],axis=1)
        for k,target in enumerate(test_hist):
            # Bound memory even for 20 tests of the maximum 10-second duration.
            for start in range(0,len(target),16):
                block=target[start:start+16];d=np.sqrt(np.mean((block[:,None,:]-h[None,:,:])**2,axis=2)).min(axis=1)
                distances[k][start:start+len(block)]=np.minimum(distances[k][start:start+len(block)],d)
    results=[]
    for item,d in zip(tests,distances):
        results.append({'test_id':item['id'],'frames':len(d),'nearest_rms_deg':d,
                        'under_0_001_deg':int(np.sum(d<.001)),'under_1_deg':int(np.sum(d<1)),
                        'under_5_deg':int(np.sum(d<5))})
    return {'accepted_total':len(accepted),'audited_count':len(sample),'sample_ids':[r['id'] for r in sample],
            'is_exhaustive':len(sample)==len(accepted),'tests':results}
