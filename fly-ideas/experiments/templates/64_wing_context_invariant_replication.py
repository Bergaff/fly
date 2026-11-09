#!/usr/bin/env python3
"""Series 64: preregistered five-holdout replication of frozen series-63 models."""
from __future__ import annotations
import argparse,csv
from datetime import datetime,timezone
import hashlib,importlib.util,io,json,math,os
from pathlib import Path
import sys,uuid
import numpy as np

HERE=Path(__file__).resolve().parent
SERIES63=HERE/'63_long_wing_context_invariant_training.py'
SERIES63_SHA='a14ce9046f82bd704984990eb7bfc7eea9b7cd5e837240379b1cf1d8e501b3e1'
ROOT=Path('workspace/runs/ideas/i-observational/wing-context-replication')
SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/wing-context-invariant')
AXES=('left_x','left_y','left_z','right_x','right_y','right_z');TARGET=3


def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def load63():
    if file_sha(SERIES63)!=SERIES63_SHA:raise ValueError('Закреплённый скрипт серии 63 изменился.')
    spec=importlib.util.spec_from_file_location('replication_series63',SERIES63);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod


def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}
def verify_source(folder):
    ci=load63();runner=ci.load_runner();proto,ev,pre,stim,ck,base,large=runner.dependencies();folder=Path(folder).resolve()
    _,db,protocol,old_holdout,state=ci.read_state(folder,ck)
    if state['stage']!='completed':raise ValueError('Нужна полностью завершённая серия 63.')
    result=folder/'result';complete_path=result/'complete.json';summary_path=result/'summary.json'
    if not complete_path.is_file() or not summary_path.is_file():raise ValueError('Результат серии 63 неполный.')
    complete=json.loads(complete_path.read_text(encoding='utf-8'));summary=json.loads(summary_path.read_text(encoding='utf-8-sig'))
    if complete.get('protocol_sha256')!=sha(canonical(protocol).encode()) or complete.get('files')!=output_manifest(result):raise ValueError('Контрольные суммы результата серии 63 не совпадают.')
    if summary.get('status') not in ('completed','fixture_completed') or summary.get('protocol')!=protocol:raise ValueError('Summary серии 63 не соответствует протоколу.')
    control_path=result/'model_control.npz';invariant_path=result/'model_context_invariant.npz'
    if file_sha(control_path)!=summary.get('control_model_sha256') or file_sha(invariant_path)!=summary.get('context_invariant_model_sha256'):raise ValueError('SHA моделей серии 63 не совпадает.')
    with np.load(control_path,allow_pickle=False) as z:control=ev.checked_model({k:z[k] for k in z.files})
    with np.load(invariant_path,allow_pickle=False) as z:invariant=ev.checked_model({k:z[k] for k in z.files})
    source59=ci.source_state(protocol['source_series']);train,tests=source59[12],source59[13]
    blocked={x['motion_sha256'] for x in train+tests}|{protocol['holdout_motion_sha256']}
    return ci,runner,proto,ev,stim,folder,result,protocol,summary,control,invariant,blocked


def freeze_inputs(paths,stim,blocked):
    if len(paths)!=5:raise ValueError('Нужно выбрать ровно пять новых JSON.')
    frozen=[];seen=set(blocked)
    for index,path in enumerate(paths,1):
        path=Path(path)
        if not path.is_file() or path.stat().st_size>1024*1024:raise ValueError(f'Holdout {index} отсутствует или слишком велик.')
        raw=path.read_bytes();obj=json.loads(raw.decode('utf-8-sig'));times,degrees=stim.sample_trajectory(obj);motion=stim.motion_hash(degrees)
        if motion in seen:raise ValueError(f'Holdout {index} полностью совпадает с прежним или другим движением.')
        seen.add(motion);frozen.append({'index':index,'raw':raw,'obj':obj,'times':times,'angles_deg':degrees,'byte_sha256':sha(raw),'motion_sha256':motion,'original_basename':path.name})
    return frozen


def axis_metrics(truth,pred):
    e=np.asarray(pred)-np.asarray(truth)
    return {'frames':len(e),'sse_rad2':float(np.sum(e*e)),'rmse_rad':float(np.sqrt(np.mean(e*e))),'mae_rad':float(np.mean(np.abs(e))),'mean_error_rad':float(np.mean(e)),'opposite_sign_frames':int(np.sum((np.asarray(pred)*np.asarray(truth)<0)&(np.asarray(truth)!=0)))}


def run(source,holdouts,output_root=ROOT):
    ci,runner,proto,ev,stim,source_folder,source_result,source_protocol,source_summary,control,invariant,blocked=verify_source(source)
    items=freeze_inputs(holdouts,stim,blocked)
    protocol={'schema':'wing-context-replication-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'series63_script_sha256':SERIES63_SHA,
      'source_series63':str(source_folder),'source_series63_protocol_sha256':sha(canonical(source_protocol).encode()),'control_model_sha256':source_summary['control_model_sha256'],'context_invariant_model_sha256':source_summary['context_invariant_model_sha256'],
      'holdouts':[{'index':x['index'],'copy':f'input/holdout_{x["index"]:03d}.json','source_sha256':x['byte_sha256'],'motion_sha256':x['motion_sha256'],'original_basename':x['original_basename']} for x in items],
      'primary_metric':'mean across five holdouts of (context-invariant right_x RMSE - control right_x RMSE)','improvement_direction':'negative','secondary_metrics':['pooled right_x RMSE and SSE','mean paired MAE difference','total opposite-sign frames','pooled mean error'],'target_axis':'right_x','models_frozen':True}
    output_root=Path(output_root).resolve();output_root.mkdir(parents=True,exist_ok=True);out=output_root/('wing_context_replication_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);out.mkdir();(out/'input').mkdir();(out/'INCOMPLETE.txt').write_text('Серия 64 не завершена.\n',encoding='utf-8')
    save_json(out/'protocol.json',protocol)
    for item in items:(out/'input'/f'holdout_{item["index"]:03d}.json').write_bytes(item['raw'])
    # No prediction is computed before protocol and all five exact input copies exist.
    studio=proto.load('rep64_studio','50_two_flies_wing_studio_pilot.py');engine=proto.load('rep64_engine','38_two_flies_observation.py');scene=studio.Scene(engine)
    results=[];all_truth=[];all_control=[];all_invariant=[]
    for item in items:
        images=scene.render(item['angles_deg']*np.pi/180);features=ev.feature_history(images);truth=item['angles_deg'][2:]*np.pi/180;pc=ev.predict(control,features);pi=ev.predict(invariant,features)
        t=truth[:,TARGET];c=pc[:,TARGET];v=pi[:,TARGET];mc=axis_metrics(t,c);mi=axis_metrics(t,v)
        row={'holdout_index':item['index'],'frames':len(t),'source_sha256':item['byte_sha256'],'motion_sha256':item['motion_sha256'],'control':mc,'context_invariant':mi,'paired_rmse_difference_rad':mi['rmse_rad']-mc['rmse_rad'],'paired_mae_difference_rad':mi['mae_rad']-mc['mae_rad']}
        results.append(row);all_truth.append(t);all_control.append(c);all_invariant.append(v);td=out/f'holdout_{item["index"]:03d}';td.mkdir()
        with (td/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'{m}_{a}_rad' for m in ('control','context_invariant') for a in AXES]])
            for k,tv in enumerate(item['times'][2:]):w.writerow([float(tv),*map(float,truth[k]),*map(float,pc[k]),*map(float,pi[k])])
        for name,pred in (('control',pc),('context_invariant',pi)):
            playback={'schema':'fly-wings-result-v1','fps':25,'duration_s':item['obj']['duration_s'],'trajectory':item['obj'],'samples':[{'t':float(tv),'teacher_deg':list(map(float,degrees)),'prediction_deg':None if k<2 else list(map(float,pred[k-2]*180/np.pi))} for k,(tv,degrees) in enumerate(zip(item['times'],item['angles_deg']))],'method':f'frozen series 63 model: {name}; preregistered series 64 battery','limitations':['Сохранённые прогнозы, не автономная генерация.','Условные камеры, не биологическое зрение.']}
            save_json(td/f'playback-{name}.json',playback)
        save_json(td/'metrics.json',row);print(f'Проверено новое движение {item["index"]}/5.',flush=True)
    truth=np.concatenate(all_truth);pc=np.concatenate(all_control);pi=np.concatenate(all_invariant);pooled_c=axis_metrics(truth,pc);pooled_i=axis_metrics(truth,pi)
    differences=[x['paired_rmse_difference_rad'] for x in results];mae_differences=[x['paired_mae_difference_rad'] for x in results]
    aggregate={'holdouts':5,'frames':len(truth),'primary_mean_paired_rmse_difference_rad':float(np.mean(differences)),'holdouts_rmse_better':sum(x<0 for x in differences),'holdouts_rmse_worse':sum(x>0 for x in differences),'mean_paired_mae_difference_rad':float(np.mean(mae_differences)),'control_pooled':pooled_c,'context_invariant_pooled':pooled_i,'pooled_rmse_change_percent':100*(pooled_i['rmse_rad']/pooled_c['rmse_rad']-1)}
    report={'schema':'wing-context-replication-result-v1','created_utc':datetime.now(timezone.utc).isoformat(),'status':'completed','protocol':protocol,'aggregate':aggregate,'holdouts':results,'limitations':['Пять движений созданы пользователем и закреплены до прогнозов, но не являются слепым биологическим экспериментом.','Модели заморожены; серия 64 проверяет переносимость результата, а не выбирает новый метод.','Пять движений не являются биологическими повторами или доказательством зеркальных нейронов.']}
    save_json(out/'summary.json',report)
    direction='лучше' if aggregate['primary_mean_paired_rmse_difference_rad']<0 else 'хуже'
    lines=['СЕРИЯ 64: ПЯТЬ НОВЫХ HOLDOUT ДЛЯ ЗАМОРОЖЕННЫХ МОДЕЛЕЙ','',f'Основная средняя парная разность RMSE (инвариантная минус контроль): {aggregate["primary_mean_paired_rmse_difference_rad"]:+.6f} рад ({direction} при отрицательном значении).',f'По отдельным движениям RMSE лучше/хуже: {aggregate["holdouts_rmse_better"]}/{aggregate["holdouts_rmse_worse"]}.',f'Объединённая RMSE контроль / инвариантная: {pooled_c["rmse_rad"]:.6f} / {pooled_i["rmse_rad"]:.6f} рад ({aggregate["pooled_rmse_change_percent"]:+.2f}%).',f'Объединённая MAE: {pooled_c["mae_rad"]:.6f} / {pooled_i["mae_rad"]:.6f} рад.',f'Неправильный знак: {pooled_c["opposite_sign_frames"]} / {pooled_i["opposite_sign_frames"]} из {len(truth)}.','']
    for x in results:lines.append(f'Holdout {x["holdout_index"]}: RMSE {x["control"]["rmse_rad"]:.6f} / {x["context_invariant"]["rmse_rad"]:.6f}, разность {x["paired_rmse_difference_rad"]:+.6f} рад.')
    lines+=['','Подробности: summary.json и папки holdout_001…holdout_005.','',*report['limitations']];(out/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    (out/'INCOMPLETE.txt').unlink();save_json(out/'complete.json',{'protocol_sha256':sha(canonical(protocol).encode()),'files':output_manifest(out)})
    print('Готово:',out,flush=True)
    if os.name=='nt':
        try:os.startfile(str(out))
        except OSError:pass
    return out


def choose():
    import tkinter as tk
    from tkinter import filedialog,messagebox
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:
        initial=str(SOURCE_ROOT.resolve()) if SOURCE_ROOT.exists() else str(Path.cwd())
        messagebox.showinfo('Серия 64','Выберите завершённую папку wing_context_invariant_... серии 63.',parent=root)
        source=filedialog.askdirectory(title='Завершённая серия 63',initialdir=initial,parent=root)
        if not source:return
        messagebox.showinfo('Пять новых движений','Выберите ровно пять новых JSON одновременно, удерживая Ctrl. Все пять будут закреплены до первого прогноза.',parent=root)
        holdouts=list(filedialog.askopenfilenames(title='Ровно пять новых holdout JSON',filetypes=[('Траектория JSON','*.json')],parent=root))
        if not holdouts:return
        if len(holdouts)!=5:raise ValueError(f'Выбрано {len(holdouts)}, нужно ровно 5.')
        out=run(source,holdouts);messagebox.showinfo('Готово',f'Пришлите текст:\n{out / "ОТЧЕТ.txt"}\nи summary.json',parent=root)
    finally:root.destroy()


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--choose',action='store_true');g.add_argument('--source')
    p.add_argument('--holdouts',nargs='*');p.add_argument('--output-root');a=p.parse_args()
    if a.choose:
        if a.holdouts or a.output_root:p.error('--choose не принимает дополнительные параметры.')
        return choose()
    if len(a.holdouts or [])!=5:p.error('Нужно ровно пять --holdouts.')
    run(a.source,a.holdouts,a.output_root or ROOT)
    return 0

if __name__=='__main__':
    try:sys.exit(main() or 0)
    except Exception as exc:print(f'ОШИБКА СЕРИИ 64: {type(exc).__name__}: {exc}\nСерия 63 и новые JSON не изменялись.',file=sys.stderr,flush=True);sys.exit(1)
