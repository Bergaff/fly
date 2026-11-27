#!/usr/bin/env python3
"""Exact 2^5 zeroing factorial for right_x context in a completed series 59.

All 32 subsets of the five non-target axes are rerendered with frozen models.
This is read-only computational attribution, not retraining or biological proof.
"""
from __future__ import annotations
import argparse,csv
from datetime import datetime,timezone
import hashlib,importlib.util,io,json,math,os
from pathlib import Path
import sys,uuid
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
CONTEXT_SCRIPT=HERE/'61_long_wing_context_intervention.py'
CONTEXT_SHA='227574975196c984228e0cf5c5351ae16445c84618e04537b6fc6880a6270a01'
ROOT=Path('workspace/runs/ideas/i-observational/wing-context-factorial')
AXES=('left_x','left_y','left_z','right_x','right_y','right_z')
CONTEXT=(0,1,2,4,5);TARGET=3;SEGMENT=(1.44,1.60)


def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def load_context():
    if file_sha(CONTEXT_SCRIPT)!=CONTEXT_SHA:raise ValueError('Закреплённый скрипт серии 61 изменился.')
    spec=importlib.util.spec_from_file_location('factorial_context61',CONTEXT_SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def subsets(original_deg):
    y=np.asarray(original_deg,dtype=float)
    if y.ndim!=2 or y.shape[1]!=6 or len(y)<3 or not np.isfinite(y).all():raise ValueError('Некорректная траектория.')
    out=[]
    for mask in range(1<<len(CONTEXT)):
        changed=y.copy();zeroed=[]
        for bit,axis in enumerate(CONTEXT):
            if mask&(1<<bit):changed[:,axis]=0;zeroed.append(AXES[axis])
        name='baseline' if mask==0 else ('only_right_x' if mask==31 else 'zero_'+'_'.join(zeroed))
        if not np.array_equal(changed[:,TARGET],y[:,TARGET]):raise AssertionError('right_x изменён.')
        out.append({'mask':mask,'condition':name,'zeroed_axes':zeroed,'angles_deg':changed})
    return out


def metrics(times,truth,pred,baseline,start=None,end=None):
    t=np.asarray(times);truth=np.asarray(truth);pred=np.asarray(pred);baseline=np.asarray(baseline)
    mask=np.ones(len(t),dtype=bool) if start is None else (t>=start-1e-9)&(t<=end+1e-9)
    if not np.any(mask) or any(x.shape!=t.shape for x in (truth,pred,baseline)):raise ValueError('Некорректный диапазон метрики.')
    err=pred[mask]-truth[mask];delta=pred[mask]-baseline[mask]
    return {'frames':int(mask.sum()),'sse_rad2':float(np.sum(err*err)),'rmse_rad':float(np.sqrt(np.mean(err*err))),
      'mae_rad':float(np.mean(np.abs(err))),'mean_prediction_rad':float(np.mean(pred[mask])),
      'mean_delta_from_baseline_rad':float(np.mean(delta)),'max_abs_delta_from_baseline_rad':float(np.max(np.abs(delta))),
      'opposite_sign_frames':int(np.sum((pred[mask]*truth[mask]<0)&(truth[mask]!=0)))}


def shapley(values):
    """Exact five-player Shapley allocation; values maps all masks to a scalar."""
    n=len(CONTEXT)
    if set(values)!=set(range(1<<n)):raise ValueError('Нужны значения всех 32 подмножеств.')
    result=[]
    for bit,axis in enumerate(CONTEXT):
        total=0.0
        for mask in range(1<<n):
            if mask&(1<<bit):continue
            size=mask.bit_count();weight=math.factorial(size)*math.factorial(n-size-1)/math.factorial(n)
            total+=weight*(values[mask|(1<<bit)]-values[mask])
        result.append({'axis':AXES[axis],'value':float(total)})
    if abs(sum(x['value'] for x in result)-(values[31]-values[0]))>1e-10:raise AssertionError('Ошибка суммы Shapley.')
    return result


def run(folder,test_id=None,output_root=ROOT):
    ctx=load_context();runner=ctx.load_runner();folder=Path(folder).resolve()
    proto,ev,base,saved,state,tests,labels,available,elapsed=ctx.completed_state(folder,runner)
    if test_id is None:test_id=available[0]
    if type(test_id)!=int or test_id not in available:raise ValueError(f'Нужен номер new_test из списка: {available}.')
    item=next(x for x in tests if x['id']==test_id);name=f'test_{test_id:03d}.json';result=folder/'result'
    runner.verify_result(result,saved,state)
    with np.load(io.BytesIO(state['sources']['baseline_model.npz']),allow_pickle=False) as z:old=ev.checked_model({k:z[k] for k in z.files})
    new_path=result/'model_new.npz';saved_summary=json.loads((result/'summary.json').read_text(encoding='utf-8-sig'))
    if file_sha(new_path)!=saved_summary['new_model_sha256']:raise ValueError('SHA новой модели не совпадает со сводкой.')
    with np.load(new_path,allow_pickle=False) as z:new=ev.checked_model({k:z[k] for k in z.files})
    studio=proto.load('factorial_studio','50_two_flies_wing_studio_pilot.py');engine=proto.load('factorial_engine','38_two_flies_observation.py')
    scene=studio.Scene(engine);variants=subsets(item['angles_deg']);eval_times=np.asarray(item['times'][2:]);truth=item['angles_deg'][2:,TARGET]*np.pi/180
    records=[];baseline=None
    for index,v in enumerate(variants):
        images=scene.render(v['angles_deg']*np.pi/180);features=ev.feature_history(images)
        old_pred=ev.predict(old,features)[:,TARGET];new_pred=ev.predict(new,features)[:,TARGET]
        if v['mask']==0:baseline=(old_pred.copy(),new_pred.copy())
        records.append({**v,'old':old_pred,'new':new_pred});print(f'Комбинация {index+1}/32: {v["condition"]}',flush=True)
    # Refuse attribution unless unchanged rendering exactly reproduces saved baseline.
    with (result/f'test_{test_id:03d}'/'predictions.csv').open(encoding='utf-8-sig',newline='') as f:original=list(csv.DictReader(f))
    try:
        original_t=np.asarray([float(r['time_s']) for r in original]);original_old=np.asarray([float(r['old_right_x_rad']) for r in original]);original_new=np.asarray([float(r['new_right_x_rad']) for r in original])
    except (KeyError,TypeError,ValueError) as exc:raise ValueError('Исходный predictions.csv имеет неверный формат.') from exc
    if len(original)!=len(eval_times) or not np.allclose(original_t,eval_times,rtol=0,atol=1e-12) or not np.allclose(original_old,baseline[0],rtol=0,atol=1e-12) or not np.allclose(original_new,baseline[1],rtol=0,atol=1e-12):
        raise ValueError('Baseline не совпал с сохранёнными предсказаниями.')
    output_root=Path(output_root).resolve()
    if output_root==folder or output_root.is_relative_to(folder):raise ValueError('Результат должен находиться вне исходной серии 59.')
    output_root.mkdir(parents=True,exist_ok=True);out=output_root/('wing_factorial_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);out.mkdir()
    metric_rows=[];prediction_rows=[]
    for r in records:
        r['metrics']={}
        for model,pred,basepred in (('old',r['old'],baseline[0]),('new',r['new'],baseline[1])):
            r['metrics'][model]={'all_frames':metrics(eval_times,truth,pred,basepred),'segment':metrics(eval_times,truth,pred,basepred,*SEGMENT)}
        for scope in ('all_frames','segment'):
            metric_rows.append([r['mask'],r['condition'],';'.join(r['zeroed_axes']),scope,
              *[r['metrics'][model][scope][key] for model in ('old','new') for key in ('frames','rmse_rad','mae_rad','sse_rad2','mean_prediction_rad','mean_delta_from_baseline_rad','max_abs_delta_from_baseline_rad','opposite_sign_frames')]])
        for k,t in enumerate(eval_times):prediction_rows.append([r['mask'],r['condition'],';'.join(r['zeroed_axes']),float(t),*map(float,r['angles_deg'][k+2]),float(truth[k]),float(r['old'][k]),float(r['new'][k])])
    metric_header=['mask','condition','zeroed_axes','scope']+[f'{model}_{key}' for model in ('old','new') for key in ('frames','rmse_rad','mae_rad','sse_rad2','mean_prediction_rad','mean_delta_from_baseline_rad','max_abs_delta_from_baseline_rad','opposite_sign_frames')]
    with (out/'condition_metrics.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(metric_header);w.writerows(metric_rows)
    with (out/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['mask','condition','zeroed_axes','time_s',*[f'input_{a}_deg' for a in AXES],'teacher_right_x_rad','old_right_x_rad','new_right_x_rad']);w.writerows(prediction_rows)
    attributions={}
    for model in ('old','new'):
        attributions[model]={}
        for scope in ('all_frames','segment'):
            # Positive SSE value means that zeroing the axis helps prediction.
            sse={r['mask']:records[0]['metrics'][model][scope]['sse_rad2']-r['metrics'][model][scope]['sse_rad2'] for r in records}
            shift={r['mask']:r['metrics'][model][scope]['mean_delta_from_baseline_rad'] for r in records}
            attributions[model][scope]={'sse_reduction_shapley_rad2':shapley(sse),'mean_prediction_shift_shapley_rad':shapley(shift),
              'total_sse_reduction_rad2':sse[31],'total_mean_prediction_shift_rad':shift[31]}
    compact=[{'mask':r['mask'],'condition':r['condition'],'zeroed_axes':r['zeroed_axes'],'metrics':r['metrics']} for r in records]
    report={'schema':'wing-context-factorial-v1','created_utc':datetime.now(timezone.utc).isoformat(),'source_series_basename':folder.name,
      'source_test_id':test_id,'source_role':labels[name]['role'],'source_protocol_sha256':sha(json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()),
      'baseline_model_sha256':sha(state['sources']['baseline_model.npz']),'new_model_sha256':file_sha(new_path),'source_trajectory_sha256':sha(state['sources'][name]),
      'target_axis':'right_x','context_axes':[AXES[x] for x in CONTEXT],'segment_s':list(SEGMENT),'active_training_seconds':elapsed,
      'conditions':compact,'shapley':attributions,'limitations':['Все 32 условия используют замороженные модели; это не обучение.','Обнуление осей может создавать движения вне обучающего распределения.','Shapley распределяет вычислительный эффект по выбранной игре обнуления; это не биологическая причинность.','Участок 1,44–1,60 с и target right_x выбраны после просмотра серии 59.','Условные камеры и supervised ridge не доказывают зеркальные нейроны или автономное воспроизведение.']}
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    seg=attributions['new']['segment'];full=attributions['new']['all_frames'];ranked=sorted(seg['sse_reduction_shapley_rad2'],key=lambda x:abs(x['value']),reverse=True)
    base_seg=records[0]['metrics']['new']['segment'];all_seg=records[-1]['metrics']['new']['segment'];base_full=records[0]['metrics']['new']['all_frames'];all_full=records[-1]['metrics']['new']['all_frames']
    lines=['ПОЛНЫЙ ФАКТОРНЫЙ КОНТРОЛЬ КОНТЕКСТА RIGHT_X','',f'Источник: серия 59, test_{test_id:03d}. Модели заморожены; исходная серия не изменялась.',
      'Проверены все 32 комбинации обнуления left_x, left_y, left_z, right_y, right_z при неизменном right_x.',
      f'Участок {SEGMENT[0]:.2f}–{SEGMENT[1]:.2f} с, новая модель RMSE baseline / all-zero: {base_seg["rmse_rad"]:.6f} / {all_seg["rmse_rad"]:.6f} рад.',
      f'Все 49 кадров, новая модель RMSE baseline / all-zero: {base_full["rmse_rad"]:.6f} / {all_full["rmse_rad"]:.6f} рад.','',
      'Ось | Shapley уменьшения SSE на участке, рад² | Shapley среднего сдвига, рад |']
    shift={x['axis']:x['value'] for x in seg['mean_prediction_shift_shapley_rad']}
    for x in ranked:lines.append(f"{x['axis']} | {x['value']:+.6f} | {shift[x['axis']]:+.6f} |")
    lines+=['',f'Сумма вкладов SSE: {seg["total_sse_reduction_rad2"]:+.6f} рад²; сумма среднего сдвига: {seg["total_mean_prediction_shift_rad"]:+.6f} рад.',
      f'Наибольший абсолютный Shapley-вклад участка: {ranked[0]["axis"]}.','Полная таблица условий: condition_metrics.csv; покадровые прогнозы: predictions.csv.','',*report['limitations']]
    (out/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    manifest={p.name:file_sha(p) for p in sorted(out.iterdir()) if p.is_file()};(out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
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
        initial=Path('workspace/runs/ideas/i-observational/wing-user-long');initial=initial.resolve() if initial.exists() else Path.cwd()
        folder=filedialog.askdirectory(title='Выберите завершённую папку wing_user_long_...',initialdir=str(initial),parent=root)
        if not folder:print('Выбор отменён.',flush=True);return 0
        ctx=load_context();runner=ctx.load_runner();state=ctx.completed_state(folder,runner);available=state[7]
        test_id=simpledialog.askinteger('Новая проверка',f'Номера new_test: {available}\nВведите номер:',initialvalue=available[0],minvalue=min(available),maxvalue=max(available),parent=root)
        if test_id is None:print('Выбор отменён.',flush=True);return 0
        if test_id not in available:raise ValueError(f'Допустимы только new_test: {available}.')
        messagebox.showinfo('Факторный расчёт','Будут проверены 32 комбинации обнуления контекстных осей. Модели не переобучаются, серия 59 не изменяется. Расчёт дольше серии 61.',parent=root)
        out=run(folder,test_id);messagebox.showinfo('Готово',f'Пришлите текст:\n{out / "ОТЧЕТ.txt"}',parent=root);return 0
    finally:root.destroy()


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--choose',action='store_true');g.add_argument('--series')
    p.add_argument('--test-id',type=int);p.add_argument('--output-root');a=p.parse_args()
    if a.choose:
        if a.test_id is not None or a.output_root is not None:p.error('--choose не принимает дополнительные параметры.')
        return choose()
    return run(a.series,a.test_id,a.output_root or ROOT)

if __name__=='__main__':
    try:sys.exit(main() or 0)
    except Exception as exc:print(f'ОШИБКА ФАКТОРНОГО РАСЧЁТА: {type(exc).__name__}: {exc}\nИсходная серия не изменялась.',file=sys.stderr,flush=True);sys.exit(1)
