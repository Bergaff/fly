#!/usr/bin/env python3
"""Supervised pilot trained on user trajectories, with separate user holdout."""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, importlib.metadata, json, math, os, platform, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[key]='1'
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
STUDIO_SHA='768b3c6b940e803b120340012c069794c7bb7292dcd81c0db0f81fca987ac6ed'
ENGINE_SHA='2f7d4ed860abe2cd97aec19ce93012d608501fa85acbfd6ae7aec9b46d673290'
PILOT_SHA='ae56f491742eb5053ab0a13dc53f6cc906195ea173f8d1f555631d343fe27253'
CHANNELS=('left_x','left_y','left_z','right_x','right_y','right_z')
DIM=576
MAX_TRAIN=50
MAX_TEST=20
RIDGE=1.0

def sha_bytes(v):return hashlib.sha256(v).hexdigest()
def sha(path):return sha_bytes(Path(path).read_bytes())
def load(name,path,digest):
    if sha(path)!=digest:raise ValueError(f'Закреплённый файл {path.name} изменён. Запуск остановлен.')
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def read_inputs(paths,studio,role):
    items=[]
    for path in paths:
        path=Path(path)
        if path.stat().st_size>1024*1024:raise ValueError('Файл траектории больше 1 МиБ.')
        source=path.read_bytes()
        if len(source)>1024*1024:raise ValueError('Файл траектории больше 1 МиБ.')
        obj=studio.validate(json.loads(source.decode('utf-8-sig')))
        t,y=studio.sample(obj)
        # Identical sampled motion cannot cross or be duplicated within the split.
        normalized=np.round(y*180/np.pi,7);normalized[normalized==0]=0
        canonical=np.asarray(normalized,dtype='<f8').tobytes()
        items.append({'name':Path(path).name,'source':source,'obj':obj,'times':t,'angles':y,'source_sha256':sha_bytes(source),'sampled_motion_sha256':sha_bytes(canonical),'role':role})
    return items

def prepare_inputs(training,tests,studio):
    if not 2<=len(training)<=MAX_TRAIN:raise ValueError(f'Выберите от 2 до {MAX_TRAIN} обучающих траекторий.')
    if not 1<=len(tests)<=MAX_TEST:raise ValueError(f'Выберите от 1 до {MAX_TEST} отдельных проверочных траекторий.')
    train=read_inputs(training,studio,'train');test=read_inputs(tests,studio,'test')
    seen={}
    for item in train+test:
        key=item['sampled_motion_sha256']
        if key in seen:raise ValueError(f'Совпадают движения в файлах «{seen[key]}» и «{item["name"]}» на 25 кадрах/с. Выберите разные траектории; одинаковые последовательности нельзя использовать дважды.')
        seen[key]=item['name']
    return train,test

def empty_stats():return {'n':0,'sx':np.zeros(DIM),'sx2':np.zeros(DIM),'sy':np.zeros(6),'sxy':np.zeros((DIM,6)),'sxx':np.zeros((DIM,DIM))}
def update_stats(stats,x,y):
    if x.ndim!=2 or x.shape[1]!=DIM or y.shape!=(x.shape[0],6) or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Повреждены признаки или метки.')
    stats['n']+=len(y);stats['sx']+=x.sum(axis=0);stats['sx2']+=(x*x).sum(axis=0);stats['sy']+=y.sum(axis=0);stats['sxy']+=x.T@y;stats['sxx']+=x.T@x

def fit(stats):
    n=stats['n']
    if n<2:raise ValueError('Недостаточно данных для обучения.')
    mean=stats['sx']/n;scale=np.sqrt(np.maximum(stats['sx2']/n-mean*mean,0));scale[scale<1e-6]=1
    intercept=stats['sy']/n
    cov=(stats['sxx']/n-np.outer(mean,mean))/np.outer(scale,scale)
    rhs=(stats['sxy']/n-np.outer(mean,intercept))/scale[:,None]
    weights=np.linalg.solve(cov+RIDGE*np.eye(DIM),rhs)
    if any(not np.isfinite(x).all() for x in (mean,scale,intercept,weights)):raise ValueError('Модель содержит неконечные значения.')
    return mean,scale,intercept,weights

def metrics(y,p):
    error=p-y
    return {'rmse_rad':float(np.sqrt(np.mean(error*error))),'mae_rad':float(np.mean(np.abs(error)))}
def scores(y,p,intercept):
    zero=np.zeros_like(y);constant=np.broadcast_to(intercept,y.shape)
    return {'new':metrics(y,p),'zero':metrics(y,zero),'training_mean':metrics(y,constant),
      'axis_new':{c:metrics(y[:,i],p[:,i]) for i,c in enumerate(CHANNELS)},
      'axis_zero':{c:metrics(y[:,i],zero[:,i]) for i,c in enumerate(CHANNELS)},
      'axis_training_mean':{c:metrics(y[:,i],constant[:,i]) for i,c in enumerate(CHANNELS)}}
def save_json(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def save_csv(path,header,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)

def save_views(folder,images,times,pilot,raw,normalized):
    np.savez_compressed(folder/'observer_vision.npz',eye_rgb=images,times_s=times)
    # Values used directly by the fitted model, saved without GIF conversion.
    luminance=pilot.visual_vectors(images)
    np.savez_compressed(folder/'model_inputs.npz',frame_luminance=luminance,raw_history=raw,normalized_history=normalized,times_s=times[2:])
    vision=[Image.fromarray(np.concatenate([frame[0],frame[1]],axis=1)).resize((384,128),Image.Resampling.NEAREST) for frame in images]
    vision[0].save(folder/'observer_vision.gif',save_all=True,append_images=vision[1:],duration=40,loop=0)
    # Current grayscale frame only, before model normalization; temporal history is in the NPZ.
    lum=luminance.reshape(len(images),2,8,12)
    feature_images=[Image.fromarray(np.uint8(np.rint(np.clip(np.concatenate([frame[0],frame[1]],axis=1),0,1)*255))).resize((384,128),Image.Resampling.NEAREST) for frame in lum]
    feature_images[0].save(folder/'observer_model_input.gif',save_all=True,append_images=feature_images[1:],duration=40,loop=0)

def run(training,tests,base):
    studio=load('user_studio_50',HERE/'50_two_flies_wing_studio_pilot.py',STUDIO_SHA)
    pilot=studio.load('user_visual_47',HERE/'47_two_flies_imitation_learning.py',PILOT_SHA)
    engine=studio.load('user_engine_38',HERE/'38_two_flies_observation.py',ENGINE_SHA)
    # All validation and byte snapshots happen before creating any run folder.
    train,test=prepare_inputs(training,tests,studio);pilot.lower_priority();scene=studio.Scene(engine)
    base=Path(base);base.mkdir(parents=True,exist_ok=True)
    out=base/('user_wing_learning_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);out.mkdir()
    (out/'INCOMPLETE.txt').write_text('Расчёт выполняется или прерван. Не считать результаты завершёнными.\n',encoding='utf8')
    src=out/'input';src.mkdir()
    manifest=[]
    for role,items in (('train',train),('test',test)):
        for i,item in enumerate(items,1):
            name=f'{role}_{i:03}.json';(src/name).write_bytes(item['source'])
            manifest.append({'role':role,'id':i,'copy':'input/'+name,'original_basename':item['name'],'source_sha256':item['source_sha256'],'sampled_motion_sha256':item['sampled_motion_sha256'],'frames':len(item['times']),'duration_s':item['obj']['duration_s']})
    save_json(out/'input_manifest.json',{'schema':'wing-user-inputs-v1','motion_hash':'SHA-256 float64 little-endian sampled degrees rounded to 7 decimals; −0 normalized','inputs':manifest})
    stats=empty_stats()
    for i,item in enumerate(train,1):
        images=scene.render(item['angles']);x=pilot.history(images);update_stats(stats,x,item['angles'][2:])
        manifest[i-1]['eye_rgb_sha256']=sha_bytes(images.tobytes());manifest[i-1]['history_sha256']=sha_bytes(np.asarray(x,dtype='<f8').tobytes())
        print(f'Обучение на ваших траекториях: {i}/{len(train)}',flush=True)
    mean,scale,intercept,weights=fit(stats)
    np.savez_compressed(out/'model_six_axes.npz',mean=mean,scale=scale,intercept=intercept,weights=weights)
    # Fit uses only training features and labels; test files were parsed earlier for validation and duplicate checks.
    test_arrays=[];all_y=[];all_p=[];summary=[]
    for i,item in enumerate(test,1):
        images=scene.render(item['angles']);raw=pilot.history(images);z=(raw-mean)/scale
        pred=np.clip(z@weights+intercept,-math.pi/3,math.pi/3);truth=item['angles'][2:]
        all_y.append(truth);all_p.append(pred);individual=scores(truth,pred,intercept)
        folder=out/f'test_{i:03}';folder.mkdir();save_views(folder,images,item['times'],pilot,raw,z)
        save_csv(folder/'user_predictions.csv',['time_s',*[f'teacher_{c}_rad' for c in CHANNELS],*[f'predicted_{c}_rad' for c in CHANNELS]], ((float(item['times'][k+2]),*map(float,truth[k]),*map(float,pred[k])) for k in range(len(truth))))
        test_arrays.append((item,folder,pred,individual))
        summary.append([i,len(truth),individual['new']['rmse_rad'],individual['zero']['rmse_rad'],individual['training_mean']['rmse_rad'],*[individual['axis_new'][c]['rmse_rad'] for c in CHANNELS]])
        manifest[len(train)+i-1]['eye_rgb_sha256']=sha_bytes(images.tobytes());manifest[len(train)+i-1]['history_sha256']=sha_bytes(np.asarray(raw,dtype='<f8').tobytes())
        print(f'Проверка на отдельных траекториях: {i}/{len(test)}',flush=True)
    truth=np.concatenate(all_y);pred=np.concatenate(all_p);overall=scores(truth,pred,intercept)
    limitations=['User-defined trajectories are supervised examples with explicit angles, not natural or unsupervised learning.',
        'Kinematic ellipsoids and two simple ray-cast cameras, not a real fly retina, muscles or brain.',
        'The split blocks identical sampled whole sequences; similar motions and shared poses can still occur.',
        'User-selected test set may be chosen after seeing results, so it is not a preregistered blind evaluation.',
        'Replay buffers predictions computed while observing, not autonomous action generation.',
        'Held-out aggregate weights frames, not sequences; one moving camera position and no biological replicates.']
    method='supervised linear ridge trained only on user train trajectories, 3 frames of two coarse simulated eyes; replay buffers predictions'
    for item,folder,p,individual in test_arrays:
        p_deg=p*180/np.pi
        result={'schema':'fly-wings-result-v1','fps':25,'duration_s':item['obj']['duration_s'],'trajectory':item['obj'],
            'samples':[{'t':float(t),'teacher_deg':list(map(float,y*180/np.pi)),'prediction_deg':None if k<2 else list(map(float,p_deg[k-2]))} for k,(t,y) in enumerate(zip(item['times'],item['angles']))],
            'method':method,'user_metrics':individual,'holdout_metrics':overall,'holdout_label':'Все проверочные траектории пользователя','limitations':limitations}
        save_json(folder/'playback.json',result)
    save_csv(out/'test_metrics.csv',['test_id','frames','rmse_model_rad','rmse_zero_rad','rmse_training_mean_rad',*[f'rmse_{c}_rad' for c in CHANNELS]],summary)
    save_json(out/'input_manifest.json',{'schema':'wing-user-inputs-v1','motion_hash':'SHA-256 float64 little-endian sampled degrees rounded to 7 decimals; −0 normalized','inputs':manifest})
    lines=['ОБУЧЕНИЕ НА ТРАЕКТОРИЯХ ПОЛЬЗОВАТЕЛЯ: КОРОТКАЯ ПРОБА',f'Обучающих файлов: {len(train)}; отдельных проверочных: {len(test)}; обучающих кадров: {stats["n"]}; проверочных кадров: {len(truth)}.',
       'Ни одна проверочная последовательность не использовалась для обучения.',
       f'Все проверочные кадры: RMSE модель / ноль / средний угол обучения, рад: {overall["new"]["rmse_rad"]:.6f} / {overall["zero"]["rmse_rad"]:.6f} / {overall["training_mean"]["rmse_rad"]:.6f}',
       'По осям: модель / ноль / средний угол обучения, рад:']
    lines += [f'{c}: {overall["axis_new"][c]["rmse_rad"]:.6f} / {overall["axis_zero"][c]["rmse_rad"]:.6f} / {overall["axis_training_mean"][c]["rmse_rad"]:.6f}' for c in CHANNELS]
    lines += ['', 'Результат по каждому движению: test_metrics.csv; кадры и playback.json находятся в папках test_001 и далее.',
      'observer_vision.gif показывает увеличенные приближённые изображения глаз, observer_vision.npz хранит исходные RGB-кадры.',
      'observer_model_input.gif показывает блоки яркости до нормировки; model_inputs.npz хранит точно использованную историю и нормированные признаки.',
      'Это синтетические глаза и кинематическая сцена, не реальное зрение, мозг или биомеханика мухи.',
      'Учительские углы доступны в обучении. Воспроизведение после показа использует буфер прогнозов, не автономную генерацию.',
      'Повторы одной и той же полной последовательности отклоняются; похожие движения и общие позы могут остаться. Пользователь выбирает проверку, это не слепой биологический тест.',
      'Общий показатель взвешен по кадрам, поэтому длинные последовательности влияют сильнее. Больше обучение не гарантирует улучшения.',
      'Это короткая проба, не возобновляемая восьмичасовая серия.']
    (out/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    meta={'status':'completed','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(__file__),'studio_sha256':STUDIO_SHA,'engine_sha256':ENGINE_SHA,'pilot_sha256':PILOT_SHA,
       'python':platform.python_version(),'versions':{p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},
       'train_sequences':len(train),'test_sequences':len(test),'train_frames':stats['n'],'test_frames':len(truth),'fps':25,'camera_resolution':[48,32],'history_frames':3,'ridge':RIDGE,
       'model_sha256':sha(out/'model_six_axes.npz'),'manifest_sha256':sha(out/'input_manifest.json'),'method':method,'holdout_metrics':overall,'limitations':limitations}
    save_json(out/'metadata.json',meta);(out/'INCOMPLETE.txt').unlink()
    print('\n'.join(lines));print('Результаты:',out,flush=True)
    if os.name=='nt':
        try:os.startfile(str(out))
        except OSError:pass
    return out

def choose():
    import tkinter as tk
    from tkinter import filedialog, messagebox
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:
        messagebox.showinfo('Обучающие траектории','Сначала выберите не менее двух разных JSON для обучения. Несколько файлов: удерживайте Ctrl.',parent=root)
        train=list(filedialog.askopenfilenames(title='Для ОБУЧЕНИЯ: выберите от 2 JSON, удерживая Ctrl',filetypes=[('Траектория JSON','*.json')],parent=root))
        if not train:return [],[]
        messagebox.showinfo('Проверочные траектории','Теперь выберите другие JSON для проверки. Не выбирайте файлы обучения.',parent=root)
        test=list(filedialog.askopenfilenames(title='Для ПРОВЕРКИ: выберите другие JSON',filetypes=[('Траектория JSON','*.json')],initialdir=str(Path(train[0]).parent),parent=root))
        return train,test
    finally:root.destroy()

def main():
    p=argparse.ArgumentParser();p.add_argument('--train',nargs='+');p.add_argument('--test',nargs='+');p.add_argument('--choose',action='store_true');p.add_argument('--output',default='workspace/runs/ideas/i-observational/wing-studio-user-learning');a=p.parse_args()
    if a.choose and (a.train or a.test):p.error('Нельзя одновременно указать файлы и --choose.')
    if a.choose:
        train,test=choose()
        if not train or not test:print('Выбор отменён; расчёт не начат.');return
    else:
        if not a.train or not a.test:p.error('Нужны --train и --test или --choose.')
        train,test=a.train,a.test
    run(train,test,a.output)
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(f'ОШИБКА: {type(e).__name__}: {e}. Старые результаты и исходные файлы не изменены. Папка с INCOMPLETE.txt не считается завершённой.',file=sys.stderr);sys.exit(1)
