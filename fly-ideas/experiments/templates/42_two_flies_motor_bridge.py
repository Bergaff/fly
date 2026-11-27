#!/usr/bin/env python3
"""A transparent, kinematic sensor-to-motor bridge; not imitation learning."""
from __future__ import annotations
import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
import numpy as np
import mujoco
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ENGINE_SHA = '2f7d4ed860abe2cd97aec19ce93012d608501fa85acbfd6ae7aec9b46d673290'
SOURCE_SHA = 'bdfdbc564bd8ffa3db2963ff0cfa3ab922ab59fd3708ed5c1212d686233c2993'
SOURCE_CONDITIONS = ('wing_stationary', 'wing_3hz_0deg', 'object_stationary', 'object_3hz_0deg')
MOTOR_HZ = 2.0  # Fixed independently of the demonstrated 3 Hz, not learned.
BACKGROUND_HZ = 12.5
SCALE_HZ = 20.0
MAX_ANGLE = .65


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok: raise ValueError(message)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_engine():
    base = HERE / '38_two_flies_observation.py'
    require(sha(base) == ENGINE_SHA, 'Скрипт 38 не соответствует закреплённой версии.')
    return load_module('motor_bridge_engine', base)


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def save_csv(path, columns, rows):
    with Path(path).open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f); writer.writerow(columns); writer.writerows(rows)


def load_source(source):
    source = Path(source).resolve()
    files = ['metadata.json', 'neuron_map.csv'] + [f'{name}/{filename}' for name in SOURCE_CONDITIONS for filename in ('scene.csv', 'vision.npz', 'spikes.csv')]
    for f in files:
        require((source/f).is_file(), f'Нет файла {f}. Выберите папку visual_controls_..., не папку условия.')
    digests = {f:sha(source/f) for f in files}
    meta = json.loads((source/'metadata.json').read_text(encoding='utf-8-sig'))
    require(meta.get('status') == 'completed' and meta.get('source_sha256') == SOURCE_SHA and meta.get('engine_sha256') == ENGINE_SHA, 'Поддерживается только завершённая серия 41 с исходной версией скриптов.')
    require(meta.get('duration_s') == 2.0 and meta.get('fps') == 50 and meta.get('seed') == 0 and meta.get('integration_dt_ms') == 1, 'Для этого пилота требуются исходные параметры: 2 с, 50 FPS, seed 0 и шаг сети 1 мс.')
    mapping = read_csv(source/'neuron_map.csv')
    require(len(mapping) == 32 and all(int(r['neuron_id']) == i and r['eye'] == ('left' if i < 16 else 'right') and int(r['tile_row']) == (i%16)//4 and int(r['tile_col']) == i%4 for i,r in enumerate(mapping)), 'Неожиданная карта нейронов.')
    engine = load_engine()
    conditions = {}
    for name in SOURCE_CONDITIONS:
        with np.load(source/name/'vision.npz', allow_pickle=False) as archive:
            frames = archive['neural_input'].copy()
            require(np.array_equal(frames,archive['scene_eyes']) and np.array_equal(archive['input_source_frame'],np.arange(100)), f'Неожиданный порядок кадров {name}.')
        require(frames.dtype == np.uint8 and frames.ndim == 5 and frames.shape[:2] == (100,2) and frames.shape[-1] == 3 and frames.shape[2]%4 == 0 and frames.shape[3]%4 == 0, f'Некорректная форма изображений {name}.')
        scene = read_csv(source/name/'scene.csv')
        require(len(scene)==100, f'Некорректное число кадров сцены {name}.')
        for k, row in enumerate(scene):
            t=k/50; signal=math.sin(2*math.pi*3*t)
            wing=.65*signal if name=='wing_3hz_0deg' else 0.
            obj = name.startswith('object_')
            y=.65*signal if name=='object_3hz_0deg' else 0.
            require(int(row['frame'])==k and abs(float(row['time_s'])-t)<1e-9 and abs(float(row['left_wing_rad'])-wing)<1e-8 and abs(float(row['right_wing_rad'])+wing)<1e-8 and int(row['object_present'])==int(obj), f'Сцена {name} не соответствует параметрам в строке {k}.')
            if obj:
                require(abs(float(row['object_x'])-3)<1e-9 and abs(float(row['object_y'])-y)<1e-8 and abs(float(row['object_z'])-.55)<1e-9, f'Некорректное положение объекта {name}.')
        spikes = read_csv(source/name/'spikes.csv')
        old_t = np.array([float(r['time_s']) for r in spikes]); old_id = np.array([int(r['neuron_id']) for r in spikes], dtype=int)
        t, ids, _ = engine.simulate(engine.features(frames),1/50,0)
        original_order = np.lexsort((old_id, old_t)); new_order = np.lexsort((ids,t))
        require(len(t)==len(old_t) and np.array_equal(ids[new_order],old_id[original_order]) and np.allclose(t[new_order],old_t[original_order],rtol=0,atol=1e-9), f'Не воспроизвелись спайки {name}; сравнение остановлено.')
        conditions[name] = dict(frames=frames,scene=scene,times=t,ids=ids)
        print(f'Проверены изображения, сцена и спайки: {name}', flush=True)
    require(all(sha(source/f)==value for f,value in digests.items()), 'Исходные файлы изменились во время проверки.')
    return source, engine, mapping, conditions, digests


def observer_xml(engine, with_object):
    xml=engine.XML
    for side,sgn in [('left',1),('right',-1)]:
        old=f'<geom name="observer_{side}_wing" type="ellipsoid" pos="-0.1 {sgn*.75:g} 0.20" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/>'
        # Original right coordinate is written as -0.75, left as 0.75.
        replacement=f'<body name="observer_{side}_wing_body" pos="-0.1 {sgn*.30:g} 0.20"><joint name="observer_{side}_hinge" type="hinge" axis="1 0 0"/><geom name="observer_{side}_wing" type="ellipsoid" pos="0 {sgn*.45:g} 0" size="0.62 0.70 0.045" rgba="0.30 0.52 0.59 1"/></body>'
        require(old in xml, f'Не найдена геометрия крыла наблюдателя: {side}.')
        xml=xml.replace(old,replacement)
    if with_object:
        obj='<body name="distractor" mocap="true" pos="3 0 0.55"><geom name="distractor_geom" type="ellipsoid" size="0.25 0.25 0.25" rgba="0.22 0.22 0.20 1"/></body>'
        xml=xml.replace('</worldbody></mujoco>',obj+'</worldbody></mujoco>')
    return xml


def make_timeline(scene, amplitude, fps=50):
    rows=[]
    # Before, observation and after. Observer is held at rest until after.
    for k in range(5*fps):
        t=k/fps
        if t<1:
            stage='before'; index=None; angle=0.
        elif t<3:
            stage='observe'; index=k-fps; angle=0.
        else:
            stage='after'; index=None; angle=amplitude*math.sin(2*math.pi*MOTOR_HZ*(t-3))
        template=scene[index] if index is not None else scene[0]
        left_demo=float(template['left_wing_rad']) if index is not None else 0.
        right_demo=float(template['right_wing_rad']) if index is not None else 0.
        obj=bool(int(template['object_present']))
        object_y=float(template['object_y']) if obj else ''
        rows.append((k,t,stage,left_demo,right_demo,int(obj),object_y,angle,-angle))
    return rows


def chart(rows,path):
    w,h=900,300; im=Image.new('RGB',(w,h),(237,234,225));d=ImageDraw.Draw(im)
    left,top,right,bottom=55,28,875,260
    def x(t): return left+(right-left)*t/5
    def y(v): return (top+bottom)/2-v*((bottom-top)/1.5)
    for t in (0,1,3,5):
        d.line((x(t),top,x(t),bottom),fill=(185,183,172),width=1)
        d.text((x(t)+3,8), {0:'BEFORE',1:'OBSERVE',3:'AFTER',5:'5 s'}[t],fill=(40,40,40))
    d.line((left,y(0),right,y(0)),fill=(140,140,132))
    d.text((left,278),'Demo wing',fill=(135,72,48));d.text((150,278),'Observer wing',fill=(30,75,100));d.text((280,278),'angle / rad; sample rate 50 Hz',fill=(60,60,60))
    for col,index in [((135,72,48),3),((30,75,100),7)]:
        points=[(x(r[1]),y(r[index])) for r in rows]
        d.line(points,fill=col,width=2)
    im.save(path)


def video(engine, scene, timeline, path, video_fps=25, width=240, height=160):
    with_object=bool(int(scene[0]['object_present']))
    model=mujoco.MjModel.from_xml_string(observer_xml(engine,with_object));data=mujoco.MjData(model)
    def joint(name):
        return model.jnt_qposadr[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,name)]
    dl,dr,ol,orr=[joint(x) for x in ('left_hinge','right_hinge','observer_left_hinge','observer_right_hinge')]
    cam=engine.camera([6,-9,5],[2,0,.4],width,height,55)
    frames=[]
    step=50//video_fps
    for row in timeline[::step]:
        _,_,stage,left,right,obj,y,obs_l,obs_r=row
        data.qpos[dl],data.qpos[dr],data.qpos[ol],data.qpos[orr]=left,right,obs_l,obs_r
        if obj: data.mocap_pos[0]=[3,float(y),.55]
        mujoco.mj_forward(model,data)
        image=Image.fromarray(engine.render(model,data,cam))
        result=Image.new('RGB',(width,height+36),(225,224,216));result.paste(image,(0,20))
        draw=ImageDraw.Draw(result)
        draw.text((5,4),{'before':'BEFORE','observe':'OBSERVE','after':'AFTER'}[stage],fill=(30,30,30))
        draw.text((5,height+22),'OBSERVER: BLUE WINGS',fill=(32,74,85))
        frames.append(result)
    frames[0].save(path,save_all=True,append_images=frames[1:],duration=round(1000/video_fps),loop=0,optimize=False)


def run(source, *, make_video=True, video_fps=25, video_width=240, video_height=160):
    require(video_fps in (10,25,50) and video_width>=48 and video_height>=32, 'Некорректные параметры визуализации.')
    source,engine,mapping,originals,digests=load_source(source)
    wing=originals['wing_3hz_0deg'];n=len(wing['frames'])
    perm=np.random.default_rng(20261106).permutation(n)
    cases=[('wings',wing,wing['frames'],False),('stationary',originals['wing_stationary'],originals['wing_stationary']['frames'],False),
           ('occluded',wing,np.full_like(wing['frames'],128),False),('shuffled',wing,wing['frames'][perm],False),
           ('object',originals['object_3hz_0deg'],originals['object_3hz_0deg']['frames'],False),('object_stationary',originals['object_stationary'],originals['object_stationary']['frames'],False),
           ('wings_readout_disabled',wing,wing['frames'],True)]
    dest=source/('motor_bridge_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);dest.mkdir()
    meta=dict(status='running',created_utc=datetime.now(timezone.utc).isoformat(),input_directory=str(source),input_sha256=digests,engine_sha256=ENGINE_SHA,source_series_sha256=SOURCE_SHA,script_sha256=sha(__file__),python=platform.python_version(),versions={p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},
        before_s=1,observation_s=2,after_s=2,neural_dt_ms=1,scene_fps=50,video_fps=video_fps if make_video else None,initial_seed=0,shuffle_seed=20261106,motor_frequency_hz=MOTOR_HZ,baseline_hz=BACKGROUND_HZ,score_scale_hz=SCALE_HZ,max_angle_rad=MAX_ANGLE,
        readout_rule='weight[i]=max(spike_count[i]/2-12.5,0)/20; score=clip(mean(weight),0,1); amplitude=0.65*score; disabled readout forces amplitude zero',
        motor_rule='before and observation: observer wing angles zero; after: left=amplitude*sin(2*pi*2*t), right=-left; 2 Hz is preprogrammed, not learned',
        limitations='Kinematic wings, no physics or motor dynamics; no learning of wing frequency, phase, or trajectory. Rule explicitly maps excess visual firing to preprogrammed movement; no post-action visual feedback, no anatomical mirror neurons or biological claim.')
    (dest/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    (dest/'scene_wings.xml').write_text(observer_xml(engine,False),encoding='utf-8')
    (dest/'scene_object.xml').write_text(observer_xml(engine,True),encoding='utf-8')
    summary=[]
    for name,stim,frames,disabled in cases:
        features=engine.features(frames)
        times,ids,drive=engine.simulate(features,1/50,0)
        counts=np.bincount(ids,minlength=32)
        rates=counts/2.
        weights=np.maximum(rates-BACKGROUND_HZ,0)/SCALE_HZ
        raw=float(np.clip(weights.mean(),0,1));score=0. if disabled else raw; amplitude=MAX_ANGLE*score
        timeline=make_timeline(stim['scene'],amplitude)
        before=np.array([r[7] for r in timeline if r[2]=='before']); after=np.array([r[7] for r in timeline if r[2]=='after'])
        sub=dest/name;sub.mkdir()
        np.savez_compressed(sub/'neural_input.npz',neural_input=frames,input_source_frame=perm if name=='shuffled' else np.arange(n))
        save_csv(sub/'observation_spikes.csv',['time_s','neuron_id'],((float(t),int(i)) for t,i in zip(times,ids)))
        save_csv(sub/'visual_input.csv',['frame','time_s','neuron_id','motion_abs_diff','drive'],((k,k/50,i,float(features[k,i]),float(drive[k,i])) for k in range(n) for i in range(32)))
        save_csv(sub/'neuron_weights.csv',['neuron_id','eye','tile_row','tile_col','spikes','rate_hz','background_hz','weight'],((i,mapping[i]['eye'],mapping[i]['tile_row'],mapping[i]['tile_col'],int(counts[i]),float(rates[i]),BACKGROUND_HZ,float(weights[i])) for i in range(32)))
        save_csv(sub/'motor_timeline.csv',['frame','time_s','stage','demo_left_wing_rad','demo_right_wing_rad','object_present','object_y','observer_left_wing_rad','observer_right_wing_rad'],timeline)
        chart(timeline,sub/'movement.png')
        if make_video: video(engine,stim['scene'],timeline,sub/'scene.gif',video_fps,video_width,video_height)
        result=dict(condition=name,observation_spikes=int(len(times)),mean_motion=float(features.mean()),raw_score=raw,readout_disabled=disabled,applied_score=score,programmed_motor_hz=MOTOR_HZ,observer_before_max_rad=float(np.max(np.abs(before))),observer_after_max_rad=float(np.max(np.abs(after))),observer_after_rms_rad=float(np.sqrt(np.mean(after*after))),programmed_amplitude_rad=amplitude)
        (sub/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        summary.append(result)
        print(f"{name}: {len(times)} спайков, сила выхода {score:.4f}, амплитуда {amplitude:.4f} рад",flush=True)
    save_csv(dest/'conditions_summary.csv',list(summary[0]),([row[k] for k in summary[0]] for row in summary))
    (dest/'report.txt').write_text('''ПИЛОТ: ЗРИТЕЛЬНЫЙ ВХОД И ДВИЖЕНИЕ КРЫЛЬЕВ НАБЛЮДАТЕЛЯ\n\nЭто не исследование обучения имитации. До показа 1 с и во время показа 2 с крылья наблюдателя программно неподвижны. Затем заданный осциллятор двигает крылья 2 секунды. Частота осциллятора 2 Гц жёстко задана и отличается от демонстратора 3 Гц; частота, фаза и форма движения не выучены. Положение и направление крыльев первой мухи не поступают в вычисление моторного выхода.\n\nИз 32 искусственных LIF во время просмотра рассчитываются средние частоты. Для каждого ID задан вес max(rate-12,5,0)/20. Усреднённый вес обрезается в диапазон 0–1 и умножается на 0,65 рад. Это специально запрограммированная связь визуальной активности с амплитудой, а не доказательство обучения или самостоятельного копирования. Фон 12,5 Гц, шкала и правило выбраны заранее для этой игрушечной модели. В случае wings_readout_disabled тот же визуальный вход подаётся на те же нейроны, но моторный выход принудительно нулевой. После просмотра нет нейронной записи или зрительной обратной связи; сохранены углы крыльев.\n\nstationary: неподвижные крылья; occluded: серая картинка; shuffled: перемешанные кадры одного 3-Гц показа, сам демонстратор в сцене не перемешан; object: движущийся посторонний эллипсоид; object_stationary: неподвижный объект. Объект и крылья не уравнены по изображению, перестановка меняет соседние разности кадров. Каждый случай начинается с одинаковых начальных состояний и пустых весов; это не независимые биологические повторы. До этапа AFTER крылья неподвижны по определению, поэтому появление движения после показа само по себе не доказывает обучение.\n\nВ каждой папке scene.gif показывает кинематическую сцену (метки BEFORE, OBSERVE, AFTER), movement.png показывает углы, motor_timeline.csv содержит все углы на сетке 50 Гц; observation_spikes.csv и visual_input.csv содержат вход и все спайки только во время просмотра. neuron_weights.csv раскрывает полный расчёт выхода каждого ID. В shuffled neural_input.npz содержит исходные индексы перестановки. scene.gif иллюстрирует сцену и не является изображением глаз. Сохранённые данные серии 41 не изменяются.\n\nНет динамики, контактов или доказанных зеркальных нейронов. Дальнейшее обучение необходимо проверять отдельно с моторной практикой, изоляцией демонстрации от скрытых команд, контролями и самостоятельным тестом без демонстратора.\n''',encoding='utf-8-sig')
    require(all(sha(source/f)==value for f,value in digests.items()), 'Исходные файлы изменились во время расчёта, результат неполон.')
    meta['status']='completed';meta['finished_utc']=datetime.now(timezone.utc).isoformat()
    (dest/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    print('RESULT_DIR='+str(dest),flush=True)
    return dest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',help='Папка завершённой серии visual_controls_...')
    p.add_argument('--choose',action='store_true')
    args=p.parse_args();source=args.run
    if args.choose:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
        source=filedialog.askdirectory(title='Выберите папку завершённой серии visual_controls_...',initialdir=str(Path('workspace/runs/ideas/i-observational/visual-controls').resolve()))
        root.destroy()
        if not source: print('Выбор отменён.');return
    if not source:p.error('Нужно указать --run или --choose')
    dest=run(source)
    if args.choose and os.name=='nt':os.startfile(str(dest))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(f'ОШИБКА: {exc}',file=sys.stderr,flush=True);sys.exit(1)
