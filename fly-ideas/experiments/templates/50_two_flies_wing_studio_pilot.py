#!/usr/bin/env python3
"""Small supervised six-axis pilot for saved Wing Studio trajectories, not a biological model."""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, importlib.metadata, json, math, os, platform, sys, uuid
from datetime import datetime
from pathlib import Path
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'): os.environ[k]='1'
import numpy as np
import mujoco
from PIL import Image

HERE=Path(__file__).resolve().parent
ENGINE_SHA='2f7d4ed860abe2cd97aec19ce93012d608501fa85acbfd6ae7aec9b46d673290'
PILOT_SHA='ae56f491742eb5053ab0a13dc53f6cc906195ea173f8d1f555631d343fe27253'
FPS=25
CHANNELS=('left_x','left_y','left_z','right_x','right_y','right_z')
LIMIT_DEG=60
SEED=20261108

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(name,path,expected):
    if sha(path)!=expected:raise ValueError(f'Исходный скрипт {path.name} изменён; пилот не запущен.')
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def validate(obj):
    if not isinstance(obj,dict) or obj.get('schema')!='fly-wings-trajectory-v1' or obj.get('fps')!=FPS:raise ValueError('Нужна траектория редактора крыльев версии 1 (25 кадров/с).')
    duration=obj.get('duration_s');frames=obj.get('keyframes')
    def real(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
    if not real(duration) or not .5<=duration<=10 or abs(round(duration*FPS)-duration*FPS)>1e-7 or not isinstance(frames,list) or not 2<=len(frames)<=200:raise ValueError('Длительность должна быть 0,52–10 с, кратной 0,04 с; необходимо 2–200 ключевых кадров.')
    times=[]
    for f in frames:
        if not isinstance(f,dict) or not real(f.get('t')) or not isinstance(f.get('angles_deg'),list) or len(f['angles_deg'])!=6:raise ValueError('Некорректный ключевой кадр.')
        if any(not real(x) or abs(x)>LIMIT_DEG for x in f['angles_deg']):raise ValueError('Каждый угол должен быть конечным числом в диапазоне ±60°.')
        times.append(float(f['t']))
    if abs(times[0])>1e-9 or abs(times[-1]-duration)>1e-9 or any(t2-t1<1e-6 for t1,t2 in zip(times,times[1:])):raise ValueError('Кадры должны строго возрастать от 0 до длительности.')
    return obj

def sample(obj):
    validate(obj); count=int(round(obj['duration_s']*FPS))+1
    times=np.arange(count,dtype=float)/FPS # includes exact final position
    xp=np.array([f['t'] for f in obj['keyframes']],dtype=float)
    angles=np.array([f['angles_deg'] for f in obj['keyframes']],dtype=float)
    y=np.stack([np.interp(times,xp,angles[:,i]) for i in range(6)],axis=1)*np.pi/180
    return times,y

def random_angles(split,ident):
    rng=np.random.default_rng(np.random.SeedSequence([SEED,0 if split=='train' else 1,ident]))
    t=np.arange(50)/FPS
    if split=='train':
        a=rng.uniform(.2,.6,6); f=rng.uniform(.4,3.0,6); phase=rng.uniform(0,2*np.pi,6)
        base=rng.uniform(-.2,.2,6)
        y=base+ a*np.sin(2*np.pi*t[:,None]*f+phase)
    else:
        # Different family from training; no user trajectory used for fitting.
        x=np.linspace(0,1.96,7); ys=rng.uniform(-.7,.7,(7,6)); y=np.stack([np.interp(t,x,ys[:,j]) for j in range(6)],axis=1)
    return t,np.clip(y,-.9,.9)

class Scene:
    def __init__(self,engine):
        xml=engine.XML
        for side in ('left','right'):
            old=f'<joint name="{side}_hinge" type="hinge" axis="1 0 0"/>'
            new=''.join(f'<joint name="{side}_{label}" type="hinge" axis="{axis}"/>' for label,axis in [('x','1 0 0'),('y','0 1 0'),('z','0 0 1')])
            if old not in xml:raise ValueError('Не удалось собрать сцену с 6 осями.')
            xml=xml.replace(old,new)
        self.engine=engine;self.model=mujoco.MjModel.from_xml_string(xml);self.data=mujoco.MjData(self.model)
        self.body=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_BODY,'demonstrator')
        self.joints=[self.model.jnt_qposadr[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,name)] for name in CHANNELS]
        self.cams=[engine.camera([.85,y,.46],[4,0,.55],48,32) for y in (.13,-.13)]
    def render(self,angles,distance=4.,offset=0.):
        self.model.body_pos[self.body]=[distance,offset,.4];images=[]
        for vec in angles:
            self.data.qpos[self.joints]=vec;mujoco.mj_forward(self.model,self.data)
            images.append(np.stack([self.engine.render(self.model,self.data,c,True) for c in self.cams]))
        return np.stack(images)

def metrics(y,p):
    e=p-y
    return {'rmse_rad':float(np.sqrt(np.mean(e*e))), 'mae_rad':float(np.mean(np.abs(e)))}
def write_csv(path,header,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(header);w.writerows(rows)

def run(path,base,train_count=48,eval_count=8):
    if not 2<=train_count<=1000 or not 1<=eval_count<=100:raise ValueError('Недопустимый размер пробы.')
    p=Path(path);source=p.read_bytes()
    if len(source)>1024*1024:raise ValueError('Файл траектории слишком большой.')
    obj=validate(json.loads(source.decode('utf-8-sig')));user_t,user_y=sample(obj)
    pilot=load('studio_pilot47',HERE/'47_two_flies_imitation_learning.py',PILOT_SHA);engine=load('studio_engine38',HERE/'38_two_flies_observation.py',ENGINE_SHA);pilot.lower_priority()
    scene=Scene(engine);base=Path(base);base.mkdir(parents=True,exist_ok=True)
    out=base/('wing_pilot_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);out.mkdir()
    (out/'INCOMPLETE.txt').write_text('Проба выполняется либо прервана.\n',encoding='utf8')
    (out/'trajectory.json').write_bytes(source)
    train_x=[];train_y=[]
    for i in range(train_count):
        _,y=random_angles('train',i);images=scene.render(y);train_x.append(pilot.history(images));train_y.append(y[2:]);print(f'Обучение: {i+1}/{train_count}',flush=True)
    x=np.concatenate(train_x);y=np.concatenate(train_y);mean=x.mean(0);scale=x.std(0);scale[scale<1e-6]=1
    z=(x-mean)/scale;intercept=y.mean(0);weights=np.linalg.solve(z.T@z/len(z)+np.eye(z.shape[1]), z.T@(y-intercept)/len(z))
    np.savez_compressed(out/'model_six_axes.npz',mean=mean,scale=scale,intercept=intercept,weights=weights)
    def predict(im):return np.clip((pilot.history(im)-mean)/scale@weights+intercept,-math.pi/3,math.pi/3)
    rows=[];hold_y=[];hold_p=[]
    for i in range(eval_count):
        t,truth=random_angles('test',i);pred=predict(scene.render(truth));hold_y.append(truth[2:]);hold_p.append(pred)
        rows.append((i,*[metrics(truth[2:,j],pred[:,j])['rmse_rad'] for j in range(6)],metrics(truth[2:],pred)['rmse_rad']))
        print(f'Независимые от обучения синтетические примеры: {i+1}/{eval_count}',flush=True)
    write_csv(out/'holdout_metrics.csv',['sequence_id',*CHANNELS,'all_axes'],rows)
    user_im=scene.render(user_y);user_pred=predict(user_im);true=user_y[2:];zero=np.zeros_like(true)
    # The GIF is an enlarged, palette-quantized illustration of the actual eye frames.
    eye_gif=[Image.fromarray(np.concatenate([frame[0],frame[1]],axis=1)).resize((384,128),Image.Resampling.NEAREST) for frame in user_im]
    eye_gif[0].save(out/'observer_vision.gif',save_all=True,append_images=eye_gif[1:],duration=40,loop=0)
    np.savez_compressed(out/'observer_vision.npz',eye_rgb=user_im,times_s=user_t)

    p_deg=user_pred*180/np.pi;all_pred=[[float(v) for v in row] for row in p_deg]
    result={'schema':'fly-wings-result-v1','fps':FPS,'duration_s':obj['duration_s'],'trajectory':obj,
            'samples':[{'t':float(t),'teacher_deg':list(map(float,y*180/np.pi)),'prediction_deg':None if i<2 else all_pred[i-2]} for i,(t,y) in enumerate(zip(user_t,user_y))],
            'method':'supervised six-output linear ridge, 3 visual frames; replay stores predictions, not a learned generative memory',
            'user_metrics':{'new':metrics(true,user_pred),'zero':metrics(true,zero),'axis_new':{c:metrics(true[:,i],user_pred[:,i]) for i,c in enumerate(CHANNELS)},'axis_zero':{c:metrics(true[:,i],zero[:,i]) for i,c in enumerate(CHANNELS)}},
            'holdout_metrics':{'new':metrics(np.concatenate(hold_y),np.concatenate(hold_p)),'zero':metrics(np.concatenate(hold_y),np.zeros_like(np.concatenate(hold_y))), 'axis_new':{c:metrics(np.concatenate(hold_y)[:,i],np.concatenate(hold_p)[:,i]) for i,c in enumerate(CHANNELS)}, 'axis_zero':{c:metrics(np.concatenate(hold_y)[:,i],np.zeros_like(np.concatenate(hold_y)[:,i])) for i,c in enumerate(CHANNELS)}},
            'limitations':['Toy kinematic ellipsoids, not realistic fly physics or a brain.', 'Explicit teacher angles used during training; no LIF spikes.', 'Replay is buffered predicted commands, not autonomous novel action generation.', 'User-edited trajectory may have been chosen after examining other results; not a blind biological test.', 'Different wing rotations can be visually ambiguous from two coarse views.', 'No old model comparison: old model has one mirrored output, not six independent axes.']}
    (out/'playback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    write_csv(out/'user_predictions.csv',['time_s',*[f'teacher_{c}_rad' for c in CHANNELS],*[f'predicted_{c}_rad' for c in CHANNELS]], ((float(user_t[i+2]),*map(float,true[i]),*map(float,user_pred[i])) for i in range(len(true))))
    h=result['holdout_metrics'];u=result['user_metrics']
    lines=['ПРОБА ОБУЧЕНИЯ 6 ОСЕЙ КРЫЛЬЕВ',f'Обучающих последовательностей: {train_count}; отдельных синтетических проверочных: {eval_count}.',f'Проверочные формы отличаются от обучающих. RMSE модель / неподвижные, рад: {h["new"]["rmse_rad"]:.6f} / {h["zero"]["rmse_rad"]:.6f}',f'Ваша траектория не использовалась для обучения. RMSE модель / неподвижные, рад: {u["new"]["rmse_rad"]:.6f} / {u["zero"]["rmse_rad"]:.6f}', 'По осям, RMSE модели (рад):']
    lines += [f'{c}: модель {u["axis_new"][c]["rmse_rad"]:.6f} / неподвижная {u["axis_zero"][c]["rmse_rad"]:.6f}' for c in CHANNELS]
    lines += ['', 'Сцена и крылья кинематические, обучение по явным углам учителя. Это не модель мозга и не доказательство зеркальных нейронов.', 'Повтор после показа воспроизводит сохранённые прогнозы, не является автономной генерацией движения.', 'Старая модель из 49 не сопоставляется: она управляет одним зеркальным углом, а не шестью независимыми осями.', 'Откройте playback.json во вкладке Крылья, чтобы увидеть рассчитанную вторую муху.', 'Проверка синтетическая, не биологический повтор. Короткая исследовательская проба, не полное обучение любым движениям.']
    (out/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    meta={'status':'completed','source_trajectory_sha256':hashlib.sha256(source).hexdigest(),'script_sha256':sha(__file__),'engine_sha256':ENGINE_SHA,'pilot_sha256':PILOT_SHA,'train_sequences':train_count,'test_sequences':eval_count,'seed':SEED,'camera_resolution':[48,32],'frame_rate_hz':FPS,'history_frames':3,'ridge':1.0,'output_clip_deg':60,'python':platform.python_version(),'versions':{p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},'model_sha256':sha(out/'model_six_axes.npz'),'method':result['method'],'limitations':result['limitations']}
    (out/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    (out/'INCOMPLETE.txt').unlink();print('\n'.join(lines));print('Результаты:',out,flush=True)
    if os.name=='nt':
        try:os.startfile(str(out))
        except OSError:pass
    return out

def choose():
    import tkinter as tk
    from tkinter import filedialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:return filedialog.askopenfilename(title='Выберите сохранённую траекторию из вкладки Крылья',filetypes=[('Траектория JSON','*.json')])
    finally:root.destroy()

def main():
    p=argparse.ArgumentParser();p.add_argument('--trajectory');p.add_argument('--choose',action='store_true');p.add_argument('--output',default='workspace/runs/ideas/i-observational/wing-studio');p.add_argument('--train-count',type=int,default=48);p.add_argument('--eval-count',type=int,default=8);a=p.parse_args()
    if bool(a.trajectory)==bool(a.choose):p.error('Выберите файл или используйте --choose.')
    path=a.trajectory or choose()
    if path:run(path,a.output,a.train_count,a.eval_count)
    else:print('Выбор отменён.')
if __name__=='__main__':
    try:main()
    except Exception as e:
        print(f'ОШИБКА: {type(e).__name__}: {e}. Папки с INCOMPLETE.txt не являются результатом.',file=sys.stderr);sys.exit(1)
