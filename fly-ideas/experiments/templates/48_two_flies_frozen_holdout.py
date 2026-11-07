#!/usr/bin/env python3
"""Fixed holdout evaluation of a saved experiment 47 model. No training."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import importlib.util
import io
import itertools
import json
import math
import os
from pathlib import Path
import platform
import sys
import uuid
from datetime import datetime, timezone

for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
import numpy as np
import mujoco
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
TRAINING_SHA = 'ae56f491742eb5053ab0a13dc53f6cc906195ea173f8d1f555631d343fe27253'
PROTOCOL = HERE.parent/'reports/two-flies-frozen-holdout-protocol-2026-11-07.md'
SEED = 2026110701
HARMONIC_MAX = (7/6)*math.sqrt(7/12)


def load_pilot():
    path = HERE/'47_two_flies_imitation_learning.py'
    if hashlib.sha256(path.read_bytes()).hexdigest() != TRAINING_SHA:
        raise ValueError('Файл обучения 47 отличается от закреплённого протокола; проверка остановлена.')
    spec = importlib.util.spec_from_file_location('frozen_imitation_pilot', path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def fixed_plan():
    return list(itertools.product(('sine','harmonic'), (1.25,2.75), (15,105), (3.6,4.4), (-0.2,0.6), (0.45,0.80)))


def load_model(path, pilot):
    path = Path(path).resolve()
    if path.name.lower() != 'model.npz' or not path.is_file():
        raise ValueError('Выберите model.npz завершённого основного пилота 47.')
    folder = path.parent
    if (folder/'INCOMPLETE.txt').exists(): raise ValueError('Папка с моделью помечена INCOMPLETE.txt.')
    meta_path = folder/'metadata.json'
    if not meta_path.is_file(): raise ValueError('Рядом с model.npz нет metadata.json пилота.')
    meta_bytes = meta_path.read_bytes()
    metadata = json.loads(meta_bytes.decode('utf-8-sig'))
    if metadata.get('status') != 'completed' or metadata.get('mode') != 'full_pilot':
        raise ValueError('Нужна модель завершённого основного пилота, не тестового малого набора.')
    expected = {'script_sha256': TRAINING_SHA, 'engine_sha256':pilot.ENGINE_HASH, 'fps':pilot.FPS,
                'frames_per_sequence':pilot.FRAMES, 'history_frames':pilot.HISTORY, 'train_sequences':36, 'test_sequences':8,
                'train_samples':1728, 'test_samples':384, 'amplitude_rad':pilot.AMPLITUDE,
                'frame_shape':[2,pilot.HEIGHT,pilot.WIDTH,3], 'ridge':pilot.RIDGE, 'seed':pilot.SEED}
    for key, value in expected.items():
        if metadata.get(key) != value: raise ValueError(f'Метаданные модели не соответствуют пилоту 47: {key}.')
    raw = path.read_bytes()
    with np.load(io.BytesIO(raw), allow_pickle=False) as z:
        keys = ('mean','scale','intercept','weights','initial_weights')
        if not all(k in z for k in keys): raise ValueError('В model.npz отсутствуют нужные параметры.')
        model = {k: np.asarray(z[k]).copy() for k in keys}
    dimension = pilot.HISTORY * 2 * (pilot.HEIGHT // 4) * (pilot.WIDTH // 4)
    for k in ('mean','scale','weights','initial_weights'):
        if model[k].shape != (dimension,) or not np.issubdtype(model[k].dtype, np.floating) or not np.isfinite(model[k]).all():
            raise ValueError(f'Некорректный параметр модели: {k}.')
    if model['intercept'].shape != () or not np.issubdtype(model['intercept'].dtype, np.floating) or not np.isfinite(model['intercept']).all() or np.any(model['scale'] <= 0):
        raise ValueError('Некорректный сдвиг или масштаб модели.')
    model['intercept'] = float(model['intercept'])
    return path, raw, meta_bytes, metadata, model


def angles(spec, pilot):
    shape, freq, phase, _, _, amplitude = spec
    theta = 2 * np.pi * freq * np.arange(pilot.FRAMES) / pilot.FPS + np.deg2rad(phase)
    wave = np.sin(theta)
    if shape == 'harmonic': wave = (wave + 0.25*np.sin(3*theta))/HARMONIC_MAX
    elif shape != 'sine': raise ValueError('Неизвестная траектория.')
    return amplitude * wave


class Scene:
    def __init__(self, pilot):
        self.m = pilot; self.engine = pilot.engine_load()
        self.model = mujoco.MjModel.from_xml_string(self.engine.XML); self.data = mujoco.MjData(self.model)
        self.body = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, 'demonstrator')
        self.left = self.model.jnt_qposadr[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,'left_hinge')]
        self.right = self.model.jnt_qposadr[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,'right_hinge')]
        self.cams = [self.engine.camera([.85,y,.46],[4,0,.55],pilot.WIDTH,pilot.HEIGHT) for y in (.13,-.13)]
        self.cache = {}

    def sequence(self, spec):
        _, _, _, distance, offset, _ = spec
        target = angles(spec,self.m); images = []
        for a in target:
            key = (distance,offset,round(float(a),12))
            if key not in self.cache:
                self.model.body_pos[self.body] = [distance,offset,.4]
                self.data.qpos[self.left], self.data.qpos[self.right] = a, -a
                mujoco.mj_forward(self.model,self.data)
                self.cache[key] = np.stack([self.engine.render(self.model,self.data,c,True) for c in self.cams])
            images.append(self.cache[key])
        return np.stack(images), target


def preview(engine, target, predicted, spec, path, pilot):
    xml = engine.XML
    for side,y in [('left','0.75'),('right','-0.75')]:
        original = f'<geom name="observer_{side}_wing" type="ellipsoid" pos="-0.1 {y} 0.20" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/>'
        repl = f'<body name="observer_{side}_joint_body" pos="-0.1 {y} 0.20"><joint name="observer_{side}_hinge" type="hinge" axis="1 0 0"/><geom name="observer_{side}_wing" type="ellipsoid" size="0.62 0.70 0.045" rgba="0.62 0.68 0.62 1"/></body>'
        if original not in xml: raise ValueError('Не удалось собрать визуализацию наблюдателя.')
        xml = xml.replace(original,repl)
    model = mujoco.MjModel.from_xml_string(xml); data = mujoco.MjData(model)
    model.body_pos[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,'demonstrator')] = [spec[3],spec[4],.4]
    def jid(name): return model.jnt_qposadr[mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_JOINT,name)]
    dl,dr,ol,orr = [jid(x) for x in ('left_hinge','right_hinge','observer_left_hinge','observer_right_hinge')]
    cam=engine.camera([6,-9,5],[2,0,.4],240,160,55); images=[]
    for a,p in zip(target,predicted):
        data.qpos[dl],data.qpos[dr],data.qpos[ol],data.qpos[orr] = a,-a,p,-p
        mujoco.mj_forward(model,data)
        im=Image.fromarray(engine.render(model,data,cam)); d=ImageDraw.Draw(im)
        d.rectangle((0,0,239,17),fill=(220,220,210)); d.text((3,3),'OBSERVER LEFT / TEACHER RIGHT',fill=(20,20,20)); images.append(im)
    images[0].save(path,save_all=True,append_images=images[1:],duration=round(1000/pilot.FPS),loop=0,optimize=False)


def aggregate_scores(pilot, records):
    ys = np.concatenate([x['target'] for x in records])
    result = {}
    for name in ('trained','untrained','zero','occluded','shuffled','clip_floor'):
        pred = np.concatenate([x['predictions'][name] for x in records])
        result[name] = pilot.metrics(ys,pred)
    return result


def evaluate(model_path, output_root):
    pilot = load_pilot()
    path, model_bytes, meta_bytes, model_metadata, model = load_model(model_path,pilot)
    specs = fixed_plan()
    root = Path(output_root).resolve(); root.mkdir(parents=True,exist_ok=True)
    out = root/('frozen_holdout_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
    out.mkdir(); (out/'INCOMPLETE.txt').write_text('Проверка выполняется или прервана; результат не завершён.\n',encoding='utf-8')
    (out/'frozen_model.npz').write_bytes(model_bytes)
    (out/'source_metadata.json').write_bytes(meta_bytes)
    scene = Scene(pilot); records=[]; images_all=[]; target_all=[]
    for seq_id,spec in enumerate(specs):
        shape,freq,phase,distance,offset,amplitude = spec
        print(f'Проверка {seq_id+1}/{len(specs)}: {shape}, {freq} Гц, фаза {phase}, расстояние {distance}, смещение {offset}, амплитуда {amplitude}',flush=True)
        images, target = scene.sequence(spec)
        y = target[pilot.HISTORY-1:]
        order = np.random.default_rng(SEED+seq_id).permutation(pilot.FRAMES)
        mean,scale,intercept,w,initial = (model[x] for x in ('mean','scale','intercept','weights','initial_weights'))
        preds = {'trained':pilot.predict(images,mean,scale,intercept,w),
                 'untrained':pilot.predict(images,mean,scale,0.0,initial),
                 'zero':np.zeros_like(y),
                 'occluded':pilot.predict(np.full_like(images,128),mean,scale,intercept,w),
                 'shuffled':pilot.predict(images[order],mean,scale,intercept,w),
                 'clip_floor':np.clip(y,-pilot.AMPLITUDE,pilot.AMPLITUDE)}
        records.append({'id':seq_id,'spec':spec,'target':y,'predictions':preds})
        images_all.append(images);target_all.append(target)
    np.savez_compressed(out/'visual_sequences.npz',images=np.stack(images_all),teacher_angle=np.stack(target_all))
    seqrows=[];predrows=[]
    for record in records:
        seq_id=record['id']; spec=record['spec']; y=record['target']; preds=record['predictions']
        for name in ('trained','untrained','zero','occluded','shuffled','clip_floor'):
            met=pilot.metrics(y,preds[name]); seqrows.append((seq_id,*spec,name,len(y),met['rmse_rad'],met['mae_rad'],met['correlation']))
        for i in range(len(y)):
            frame=i+pilot.HISTORY-1
            predrows.append((seq_id,*spec,frame,frame/pilot.FPS,y[i],*(preds[k][i] for k in ('trained','untrained','zero','occluded','shuffled','clip_floor'))))
    pilot.csv_write(out/'sequence_metrics.csv',['sequence_id','trajectory','frequency_hz','phase_deg','distance','offset','amplitude_rad','condition','frames','rmse_rad','mae_rad','correlation'],seqrows)
    pilot.csv_write(out/'predictions.csv',['sequence_id','trajectory','frequency_hz','phase_deg','distance','offset','amplitude_rad','frame','time_s','teacher_angle_rad','trained_angle_rad','untrained_angle_rad','zero_angle_rad','occluded_angle_rad','shuffled_angle_rad','clip_floor_angle_rad'],predrows)
    scores=aggregate_scores(pilot,records)
    wins=ties=losses=0
    for r in records:
        trained=pilot.metrics(r['target'],r['predictions']['trained'])['rmse_rad']; zero=pilot.metrics(r['target'],r['predictions']['zero'])['rmse_rad']
        if abs(trained-zero)<1e-12:ties+=1
        elif trained<zero:wins+=1
        else:losses+=1
    breakdown=[]
    for index, group_name in [(0,'trajectory'),(3,'distance'),(4,'offset'),(5,'amplitude_rad')]:
        for val in dict.fromkeys(r['spec'][index] for r in records):
            group=[r for r in records if r['spec'][index]==val]; summary=aggregate_scores(pilot,group)
            for cond,metric in summary.items():
                breakdown.append((group_name,val,cond,len(group),len(group)*len(group[0]['target']),metric['rmse_rad'],metric['mae_rad'],metric['correlation']))
    pilot.csv_write(out/'breakdown.csv',['dimension','value','condition','sequences','frames','rmse_rad','mae_rad','correlation'],breakdown)
    first=records[0]
    preview(scene.engine,first['target'],first['predictions']['trained'],first['spec'],out/'comparison.gif',pilot)
    # First plan item is amplitude .45 and fits pilot's plot scale of +/-0.65.
    pilot.plot_sequence(first['target'],first['predictions']['trained'],out/'comparison.png')
    metadata={'status':'completed','protocol':'two-flies-frozen-holdout-protocol-2026-11-07.md','protocol_sha256':hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
              'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'training_script_sha256':TRAINING_SHA,'engine_sha256':pilot.ENGINE_HASH,
              'source_model_path':str(path),'source_model_sha256':hashlib.sha256(model_bytes).hexdigest(),'source_metadata_sha256':hashlib.sha256(meta_bytes).hexdigest(),
              'python':platform.python_version(),'versions':{p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},'seed':SEED,'count':len(records),'frames_per_sequence':pilot.FRAMES,'scored_frames_per_sequence':pilot.FRAMES-pilot.HISTORY+1,'scores':scores,
              'sequences_vs_zero':{'better':wins,'equal':ties,'worse':losses},'output_clip_rad':pilot.AMPLITUDE,'pose_cache_round_digits':12,
              'limits':['Frozen supervised image-to-angle model; no retraining, test labels are for scoring only.', 'Model is clipped at +/-0.65 rad; clip_floor is a target-dependent theoretical lower bound, not a predictor.', 'Fixed synthetic periodic stimuli; cases and frames are not independent animals.', 'File provenance is self-reported metadata; no verification of original training data.', 'Simultaneous kinematic wing command, not autonomous replay after video ends or evidence of mirror neurons.', 'Gray input is out of distribution and the shuffle control is not a matched moving-object control.']}
    (out/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    labels=[('trained','Замороженная обученная модель'),('untrained','Начальные случайные веса'),('zero','Постоянный нулевой угол'),('occluded','Серое поле'),('shuffled','Перемешанные кадры'),('clip_floor','Теоретическая нижняя граница из-за ограничения угла')]
    lines=['ПРОВЕРКА ЗАМОРОЖЕННОЙ МОДЕЛИ НА НОВЫХ ДВИЖЕНИЯХ',f'Модель: {path}',f'SHA-256 модели: {metadata["source_model_sha256"]}',f'Последовательностей: {len(records)}, оцениваемых кадров: {len(predrows)}.', 'Веса и нормализация из model.npz не обучались повторно.', 'Новые частоты, фазы, расстояния, смещения, амплитуды и два типа траектории. Результаты описательные, не биологические повторы.', '', 'Общая ошибка RMSE и MAE в радианах (меньше лучше):']
    for k,label in labels:
        v=scores[k]; lines.append(f'{label}: RMSE {v["rmse_rad"]:.6f}; MAE {v["mae_rad"]:.6f}')
    lines.extend([f'Отдельные последовательности: модель лучше неподвижного нуля {wins}, равно {ties}, хуже {losses} из {len(records)}.', '', 'Разбивка обученной модели и нуля:'])
    for dimension in ('trajectory','distance','offset','amplitude_rad'):
        for val in dict.fromkeys(r[1] for r in breakdown if r[0]==dimension):
            item={row[2]:row for row in breakdown if row[0]==dimension and row[1]==val}
            lines.append(f'{dimension} = {val}: модель RMSE {item["trained"][5]:.6f}; ноль {item["zero"][5]:.6f}; ограничение {item["clip_floor"][5]:.6f}')
    lines.extend(['', 'Модель 47 не может выдавать угол за пределами ±0,65 рад; амплитуда 0,80 может превышать предел. Нижняя граница рассчитывается по эталону и не является предсказателем.',
                  'comparison.gif и comparison.png показывают только первую заранее выбранную последовательность, не среднее.',
                  'sequence_metrics.csv: каждая последовательность; breakdown.csv: группы; predictions.csv: покадровые значения; visual_sequences.npz: исходные изображения и метки.',
                  'frozen_model.npz: копия исходной модели; metadata.json: план, SHA и ограничения. Метаданные не доказывают происхождение обучающих данных.',
                  'Модель воспроизводит команду во время просмотра, не после выключения входа; это не доказательство зеркальных нейронов или поведения живых мух.'])
    (out/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    (out/'INCOMPLETE.txt').unlink(); print('\n'.join(lines)); print('\nРезультаты:',out,flush=True)
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model');p.add_argument('--output',default='workspace/runs/ideas/i-observational/imitation-holdout');a=p.parse_args()
    if not a.model:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
        initial=Path('workspace/runs/ideas/i-observational/imitation-learning').resolve()
        try:a.model=filedialog.askopenfilename(title='Выберите model.npz из вашей папки imitation_...',initialdir=str(initial),filetypes=[('Модель NPZ','*.npz'),('Все файлы','*.*')])
        finally:root.destroy()
        if not a.model: print('Выбор отменён.');return
    pilot=load_pilot();pilot.lower_priority()
    out=evaluate(a.model,a.output)
    if os.name=='nt':
        try:os.startfile(str(out))
        except OSError as exc:print('Не удалось открыть папку автоматически:',exc)


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(f'ОШИБКА: {type(exc).__name__}: {exc}\nИсходная модель и база не изменены. Папка с INCOMPLETE.txt не является готовым результатом.',file=sys.stderr,flush=True)
        sys.exit(1)
