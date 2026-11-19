#!/usr/bin/env python3
"""Read-only one-axis-at-a-time context intervention for a completed series 59.

This is model diagnostics, not training or a biological/causal experiment. It
keeps right_x unchanged and rerenders synthetic views after changing one of the
other five axes. Existing series files are verified and never modified.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import uuid
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER=HERE/'59_long_user_wing_learning.py'
RUNNER_SHA='5c700f4c72f3614c245ab34f2b7bf7f8469e3114cb46568556157a2b99e5ddcf'
ROOT=Path('workspace/runs/ideas/i-observational/wing-context-intervention')
AXES=('left_x','left_y','left_z','right_x','right_y','right_z')
TARGET=3
CONTEXT=(0,1,2,4,5)
DELTA_DEG=10.0
SEGMENT=(1.44,1.60)


def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())

def load_runner():
    if file_sha(RUNNER)!=RUNNER_SHA:raise ValueError('Закреплённый скрипт серии 59 изменился.')
    spec=importlib.util.spec_from_file_location('context_runner59',RUNNER)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def conditions(original_deg,delta_deg=DELTA_DEG):
    """Baseline, right_x isolation and symmetric one-axis interventions."""
    y=np.asarray(original_deg,dtype=float)
    if y.ndim!=2 or y.shape[1]!=6 or len(y)<3 or not np.isfinite(y).all():raise ValueError('Некорректная траектория.')
    if not isinstance(delta_deg,(int,float)) or isinstance(delta_deg,bool) or not np.isfinite(delta_deg) or not 0<delta_deg<=20:
        raise ValueError('Шаг изменения должен быть от 0 до 20 градусов.')
    out=[('baseline',None,0.0,y.copy())]
    isolated=np.zeros_like(y);isolated[:,TARGET]=y[:,TARGET]
    out.append(('only_right_x',None,0.0,isolated))
    for axis in CONTEXT:
        for sign,label in ((-1,'minus'),(1,'plus')):
            changed=y.copy();changed[:,axis]=np.clip(changed[:,axis]+sign*delta_deg,-60,60)
            out.append((f'{AXES[axis]}_{label}_{delta_deg:g}deg',AXES[axis],sign*float(delta_deg),changed))
    for name,_,_,changed in out:
        if not np.array_equal(changed[:,TARGET],y[:,TARGET]):raise AssertionError(f'right_x изменён в условии {name}.')
    return out


def segment_metrics(times,truth,pred,baseline_pred,start=SEGMENT[0],end=SEGMENT[1]):
    times=np.asarray(times,dtype=float);truth=np.asarray(truth,dtype=float);pred=np.asarray(pred,dtype=float);base=np.asarray(baseline_pred,dtype=float)
    mask=(times>=start-1e-9)&(times<=end+1e-9)
    if not np.any(mask) or truth.shape!=times.shape or pred.shape!=times.shape or base.shape!=times.shape:raise ValueError('Проблемный временной участок отсутствует.')
    err=pred[mask]-truth[mask]
    return {'frames':int(mask.sum()),'rmse_rad':float(np.sqrt(np.mean(err*err))),
            'mae_rad':float(np.mean(np.abs(err))),'mean_prediction_rad':float(np.mean(pred[mask])),
            'mean_delta_from_baseline_rad':float(np.mean(pred[mask]-base[mask])),
            'max_abs_delta_from_baseline_rad':float(np.max(np.abs(pred[mask]-base[mask])))}


def completed_state(folder,runner):
    folder=Path(folder).resolve();db=folder/'study.sqlite3'
    if not db.is_file():raise ValueError('В выбранной папке нет study.sqlite3 серии 59.')
    proto,ev,pre,stim,ck,base,large=runner.dependencies()
    saved,state,stage,elapsed=runner.saved_state(db,proto,ck)
    if stage!='completed':raise ValueError('Серия 59 ещё не завершена.')
    runner.verify_result(folder/'result',saved,state)
    train,tests=proto.split_from_sources(state['sources'],stim)
    labels={x['copy']:x for x in saved['labels']}
    available=[item['id'] for item in tests if labels[f"test_{item['id']:03d}.json"]['role']=='new_test']
    if not available:raise ValueError('В серии нет проверки с ролью new_test.')
    return (proto,ev,base,saved,state,tests,labels,available,elapsed)


def run(folder,test_id=None,delta_deg=DELTA_DEG,output_root=ROOT):
    runner=load_runner();folder=Path(folder).resolve()
    proto,ev,base,saved,state,tests,labels,available,elapsed=completed_state(folder,runner)
    if test_id is None:test_id=available[0]
    if type(test_id)!=int or test_id not in available:raise ValueError(f'Нужен номер новой проверки из списка: {available}.')
    item=next(x for x in tests if x['id']==test_id);name=f'test_{test_id:03d}.json'
    result=folder/'result';runner.verify_result(result,saved,state)
    with np.load(io.BytesIO(state['sources']['baseline_model.npz']),allow_pickle=False) as z:
        old=ev.checked_model({k:z[k] for k in z.files})
    new_path=result/'model_new.npz'
    if file_sha(new_path)!=json.loads((result/'summary.json').read_text(encoding='utf-8-sig'))['new_model_sha256']:
        raise ValueError('SHA новой модели не совпадает со сводкой.')
    with np.load(new_path,allow_pickle=False) as z:new=ev.checked_model({k:z[k] for k in z.files})
    studio=proto.load('context_studio','50_two_flies_wing_studio_pilot.py')
    engine=proto.load('context_engine','38_two_flies_observation.py')
    scene=studio.Scene(engine)
    variants=conditions(item['angles_deg'],delta_deg)
    computed=[];baseline=None;eval_times=np.asarray(item['times'][2:],dtype=float);truth=item['angles_deg'][2:,TARGET]*np.pi/180
    for index,(condition,axis,delta,angles_deg) in enumerate(variants):
        images=scene.render(angles_deg*np.pi/180)
        features=ev.feature_history(images)
        old_pred=ev.predict(old,features)[:,TARGET];new_pred=ev.predict(new,features)[:,TARGET]
        if index==0:baseline=(old_pred.copy(),new_pred.copy())
        computed.append({'condition':condition,'axis':axis,'delta_deg':delta,'angles_deg':angles_deg,
                         'old':old_pred,'new':new_pred})
        print(f'Условие {index+1}/{len(variants)}: {condition}',flush=True)
    # A byte-verified saved result is also checked numerically: the unchanged
    # baseline must reproduce the original time and right_x predictions.
    with (result/f'test_{test_id:03d}'/'predictions.csv').open(encoding='utf-8-sig',newline='') as f:
        original_rows=list(csv.DictReader(f))
    try:
        original_t=np.asarray([float(r['time_s']) for r in original_rows])
        original_old=np.asarray([float(r['old_right_x_rad']) for r in original_rows])
        original_new=np.asarray([float(r['new_right_x_rad']) for r in original_rows])
    except (KeyError,TypeError,ValueError) as exc:raise ValueError('Исходный predictions.csv имеет неверный формат.') from exc
    if (len(original_rows)!=len(eval_times) or not np.allclose(original_t,eval_times,rtol=0,atol=1e-12)
            or not np.allclose(original_old,baseline[0],rtol=0,atol=1e-12)
            or not np.allclose(original_new,baseline[1],rtol=0,atol=1e-12)):
        raise ValueError('Повторный baseline не совпал с сохранёнными предсказаниями; вмешательство остановлено.')
    output_root=Path(output_root).resolve()
    if output_root==folder or output_root.is_relative_to(folder):raise ValueError('Папка диагностики должна находиться вне исходной серии 59.')
    output_root.mkdir(parents=True,exist_ok=True)
    out=output_root/('wing_context_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);out.mkdir()
    rows=[];summary=[]
    for record in computed:
        oldm=segment_metrics(eval_times,truth,record['old'],baseline[0]);newm=segment_metrics(eval_times,truth,record['new'],baseline[1])
        summary.append({'condition':record['condition'],'changed_axis':record['axis'],'delta_deg':record['delta_deg'],'old':oldm,'new':newm})
        for k,t in enumerate(eval_times):
            input_deg=record['angles_deg'][k+2]
            rows.append([record['condition'],record['axis'] or '',record['delta_deg'],float(t),*map(float,input_deg),float(truth[k]),float(record['old'][k]),float(record['new'][k]),float(record['old'][k]-baseline[0][k]),float(record['new'][k]-baseline[1][k])])
    with (out/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['condition','changed_axis','delta_deg','time_s',*[f'input_{axis}_deg' for axis in AXES],'teacher_right_x_rad','old_right_x_rad','new_right_x_rad','old_delta_from_baseline_rad','new_delta_from_baseline_rad']);w.writerows(rows)
    provenance={'schema':'wing-context-intervention-v1','created_utc':datetime.now(timezone.utc).isoformat(),
        'source_series_basename':folder.name,'source_test_id':test_id,'source_role':labels[name]['role'],
        'source_protocol_sha256':sha(json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()),
        'baseline_model_sha256':sha(state['sources']['baseline_model.npz']),'new_model_sha256':file_sha(new_path),
        'source_trajectory_sha256':sha(state['sources'][name]),'delta_deg':float(delta_deg),'target_axis':'right_x',
        'segment_s':list(SEGMENT),'active_training_seconds':elapsed,'conditions':summary,
        'limitations':['Диагностика меняет искусственно отрисованные входы уже обученных моделей; модели не переобучаются.',
          'Сдвиг целой оси на ±10° и изоляция right_x могут создавать движения вне обучающего распределения.',
          'Результат показывает чувствительность вычислительной модели, но не биологическую причинность.',
          'Условные камеры и supervised ridge не доказывают зеркальные нейроны или автономное воспроизведение.']}
    (out/'summary.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    ranked=sorted(summary[2:],key=lambda x:abs(x['new']['mean_delta_from_baseline_rad']),reverse=True)
    lines=['КОНТРОЛЬ КОНТЕКСТНЫХ ОСЕЙ ДЛЯ RIGHT_X','',
      f'Источник: завершённая серия 59, новая проверка test_{test_id:03d}. Старые файлы не изменялись.',
      f'Целевой right_x одинаков во всех условиях. Участок: {SEGMENT[0]:.2f}–{SEGMENT[1]:.2f} с; шаг вмешательства: ±{delta_deg:g}°.',
      'Модели не переобучались. Для каждой контекстной оси изменялась только она; также проверено условие only_right_x.', '',
      'Условие | RMSE old | RMSE new | среднее изменение new относительно baseline, рад | максимум |',
      '--- | ---: | ---: | ---: | ---: |']
    for r in summary:
        lines.append(f"{r['condition']} | {r['old']['rmse_rad']:.6f} | {r['new']['rmse_rad']:.6f} | {r['new']['mean_delta_from_baseline_rad']:+.6f} | {r['new']['max_abs_delta_from_baseline_rad']:.6f} |")
    lines+=['','Наибольшая абсолютная средняя реакция новой модели среди одноосевых сдвигов: '+ranked[0]['condition']+'.',
      'Это ранжирование чувствительности модели на искусственных вмешательствах, не установленная причина исходной ошибки.','',*provenance['limitations']]
    (out/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    manifest={p.name:file_sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Готово:',out.resolve(),flush=True)
    if os.name=='nt':
        try:os.startfile(str(out))
        except OSError as exc:print('Не удалось открыть папку:',exc,flush=True)
    return out


def choose():
    import tkinter as tk
    from tkinter import filedialog,messagebox,simpledialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:
        folder=filedialog.askdirectory(title='Выберите завершённую папку wing_user_long_...',initialdir=str(Path('workspace/runs/ideas/i-observational/wing-user-long').resolve()),parent=root)
        if not folder:print('Выбор отменён.',flush=True);return 0
        runner=load_runner();*_,available,_=completed_state(folder,runner)
        default=available[0]
        test_id=simpledialog.askinteger('Новая проверка',f'Номера проверок new_test: {available}\nВведите номер для анализа:',initialvalue=default,minvalue=min(available),maxvalue=max(available),parent=root)
        if test_id is None:print('Выбор отменён.',flush=True);return 0
        if test_id not in available:raise ValueError(f'Номер {test_id} не имеет роли new_test; допустимы {available}.')
        messagebox.showinfo('Короткая диагностика','right_x останется неизменным. Остальные оси будут по одной сдвинуты на −10° и +10°; модели не переобучаются. Исходная серия не изменяется.',parent=root)
        out=run(folder,test_id)
        messagebox.showinfo('Готово',f'Отчёт сохранён:\n{out / "ОТЧЕТ.txt"}',parent=root);return 0
    finally:root.destroy()


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--choose',action='store_true');g.add_argument('--series')
    p.add_argument('--test-id',type=int);p.add_argument('--delta-deg',type=float,default=DELTA_DEG);p.add_argument('--output-root')
    a=p.parse_args()
    if a.choose:
        if a.test_id is not None or a.output_root is not None or a.delta_deg!=DELTA_DEG:p.error('--choose не принимает дополнительные параметры.')
        return choose()
    return run(a.series,a.test_id,a.delta_deg,a.output_root or ROOT)

if __name__=='__main__':
    try:sys.exit(main() or 0)
    except Exception as exc:
        print(f'ОШИБКА ДИАГНОСТИКИ: {type(exc).__name__}: {exc}\nИсходная серия не изменялась.',file=sys.stderr,flush=True);sys.exit(1)
