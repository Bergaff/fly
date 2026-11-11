#!/usr/bin/env python3
"""Series 68: frozen series-67 replication on five new matched movements."""
from __future__ import annotations
import argparse,csv
from datetime import datetime,timezone
import hashlib,importlib.util,json,math,os
from pathlib import Path
import shutil,sys,uuid
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER67=HERE/'67_piecewise_rich_observer_replay.py';RUNNER67_SHA='9e2e362e16e9d01fef1e293a246e5c7da10922b05b7c6710c5f838c14ed37832'
ROOT=Path('workspace/runs/ideas/i-observational/piecewise-rich-replication');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/piecewise-rich-replay')
AXES=('left_x','left_y','left_z','right_x','right_y','right_z')
# Completed series-67 battery 31-35. Earlier exclusions are supplied by the pinned runner.
SERIES67_HOLDOUT_MOTIONS=frozenset({'577c5bd1a8df428718522ab24287b3aebd7db2a3228d33ffde59c7c373fe7e14','801605e32df2374217b6e2a58be8554db3d1cf02ba17a30e4c39e4aabf9761e9','e2088980df2382fde184d0b9a5d052fa57658ba22e2b064aac25ab4afaeccfc4','47545738bfe5cdb0444b41424617478845f4d52f62f43f86910c4ba87d849400','75c93df56bce3034de6166a3d6025448ed76cbc70e48e8c1dc0716f61879894e'})

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def load67():
 if file_sha(RUNNER67)!=RUNNER67_SHA:raise ValueError('Закреплённый runner серии 67 изменился.')
 spec=importlib.util.spec_from_file_location('frozen_rich67',RUNNER67);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def source67(folder,allow_fixture=False):
 m=load67();folder,db,p,state=m.read_state(folder)
 if state['stage']!='completed':raise ValueError('Нужна завершённая серия 67.')
 out=m.verify_output(folder/'result');summary=json.loads((out/'summary.json').read_text(encoding='utf8'))
 expected_status='fixture_completed' if allow_fixture else 'completed'
 if summary.get('status')!=expected_status or (not allow_fixture and (summary.get('training_episodes')!=60000 or summary.get('aggregate',{}).get('primary_pass') is not True)):raise ValueError('Источник не является полным успешным результатом серии 67.')
 model_path=out/'autonomous_model.npz'
 if file_sha(model_path)!=summary.get('model_sha256'):raise ValueError('SHA замороженной модели серии 67 не совпадает.')
 with np.load(model_path,allow_pickle=False) as z:
  if set(z.files)!={'weights','projection'}:raise ValueError('Некорректный архив модели серии 67.')
  weights=np.array(z['weights'],dtype=float,copy=True);projection=np.array(z['projection'],dtype=float,copy=True)
 if weights.shape!=(m.XDIM+1,m.YDIM) or projection.shape!=m.PROJECTION.shape or not np.array_equal(projection,m.PROJECTION):raise ValueError('Размеры или projection замороженной модели не совпадают.')
 src=m.source_state(p['source_series59']);runner,proto,stim,large,source59,db59,saved59,state59=src;train59,test59=proto.split_from_sources(state59['sources'],stim)
 blocked=set(m.PRIOR_HOLDOUT_MOTIONS)|set(SERIES67_HOLDOUT_MOTIONS)|{x['motion_sha256'] for x in train59+test59}
 return m,folder,p,state,summary,weights,src,blocked

def freeze(paths,stim,blocked):
 if len(paths)!=5:raise ValueError('Нужно ровно пять новых JSON для репликации.')
 out=[];seen=set(blocked);expected=np.arange(5)*.5
 for i,path in enumerate(paths,1):
  path=Path(path)
  if not path.is_file() or path.stat().st_size>1024*1024:raise ValueError(f'Holdout {i} отсутствует или слишком велик.')
  raw=path.read_bytes();obj=json.loads(raw.decode('utf-8-sig'));times,degrees=stim.sample_trajectory(obj);key=np.asarray([x['t'] for x in obj.get('keyframes',[])],dtype=float)
  if obj.get('duration_s')!=2 or key.shape!=(5,) or not np.allclose(key,expected,rtol=0,atol=1e-9):raise ValueError('Нужны движения кнопки random: 2 с, точки 0/0,5/1/1,5/2 с.')
  motion=stim.motion_hash(degrees)
  if motion in seen:raise ValueError(f'Holdout {i} совпадает с прежним или другим движением.')
  seen.add(motion);out.append({'index':i,'path':path,'raw':raw,'obj':obj,'times':times,'angles_deg':degrees,'source_sha256':sha(raw),'motion_sha256':motion,'basename':path.name})
 return out

def metrics(truth,pred):
 e=np.asarray(pred)-np.asarray(truth);return {'frames':len(e),'rmse_rad':float(np.sqrt(np.mean(e*e))),'mae_rad':float(np.mean(np.abs(e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)}}
def verify_result(out):
 out=Path(out);manifest=json.loads((out/'complete.json').read_text(encoding='utf8'))
 for name,digest in manifest['files'].items():
  if file_sha(out/name)!=digest:raise ValueError('Контрольные суммы репликации не совпали.')
 return out

def run(source,holdouts,output_root=ROOT,allow_fixture_source=False):
 m,source,p67,state67,summary67,weights,src,blocked=source67(source,allow_fixture_source);runner,proto,stim,large,source59,db59,saved59,state59=src;items=freeze(holdouts,stim,blocked)
 output_root=Path(output_root);output_root.mkdir(parents=True,exist_ok=True);folder=output_root/('piecewise_rich_replication_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();(folder/'input').mkdir();(folder/'INCOMPLETE.txt').write_text('Расчёт не завершён.\n',encoding='utf8')
 for x in items:(folder/'input'/f'holdout_{x["index"]:03d}.json').write_bytes(x['raw'])
 protocol={'schema':'frozen-rich-observer-replication-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner67_sha256':RUNNER67_SHA,'source_series67':str(source),'source_series67_protocol_sha256':sha(canonical(p67).encode()),'source_model_sha256':summary67['model_sha256'],'source_training_episodes':summary67['training_episodes'],'mode':'fixture' if allow_fixture_source else 'full','holdouts':[{'index':x['index'],'copy':f'input/holdout_{x["index"]:03d}.json','basename':x['basename'],'source_sha256':x['source_sha256'],'motion_sha256':x['motion_sha256']} for x in items],'primary_rule':'frozen normal mean RMSE lower than zero, static, shuffled, and reversed; no retraining','replay_access':'frozen model creates 72 coefficient state; replay receives state and phase only'};save_json(folder/'protocol.json',protocol)
 try:
  proto.worker_init([],set());scene=proto.SCENE;temp=folder/'result.tmp';temp.mkdir();rows=[]
  for item in items:
   t=item['times'];deg=item['angles_deg'];truth=deg*np.pi/180;normal=scene.render(truth);rng=np.random.default_rng(670000+item['index']);order=rng.permutation(len(normal));variants={'normal':normal,'reversed':normal[::-1].copy(),'shuffled':normal[order].copy(),'static':np.repeat(normal[:1],len(normal),axis=0),'closed':np.zeros_like(normal)};preds={};states={};activity0=None;delta0=None
   for name,images in variants.items():
    x,activity,delta=m.encode(images);coeff=m.predict(weights,x);states[name]=coeff;preds[name]=m.replay_from_state(coeff,len(truth))
    if name=='normal':activity0=activity;delta0=delta
   zero=np.zeros_like(truth);result={'holdout_index':item['index'],'frames':len(truth),'normal':metrics(truth,preds['normal']),'zero':metrics(truth,zero),'controls':{k:metrics(truth,v) for k,v in preds.items() if k!='normal'},'internal_state_sha256':sha(np.asarray(states['normal'],dtype='<f8').tobytes()),'delay_s':m.DELAY_S,'state_unchanged_during_delay':True};rows.append(result);td=temp/f'holdout_{item["index"]:03d}';td.mkdir()
   with (td/'observer_activity.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['time_s',*[f'level_{i:03d}' for i in range(m.SPATIAL_UNITS)],*[f'delta_{i:03d}' for i in range(m.SPATIAL_UNITS)]]);w.writerows([[float(tv),*map(float,a),*map(float,d)] for tv,a,d in zip(t,activity0,delta0)])
   with (td/'autonomous_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['replay_time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'autonomous_{a}_rad' for a in AXES]]);w.writerows([[float(tv),*map(float,y),*map(float,q)] for tv,y,q in zip(t,truth,preds['normal'])])
   save_json(td/'internal_state.json',{'schema':'frozen-rich-observer-state-v1','coefficients':list(map(float,states['normal'])),'updates_during_delay':0,'delay_s':m.DELAY_S,'replay_inputs':['72 coefficient state','replay phase'],'forbidden_replay_inputs':['observation images','teacher angles','buffered predictions']});save_json(td/'metrics.json',result);save_json(td/'playback.json',{'schema':'fly-wings-result-v1','fps':25,'duration_s':2,'trajectory':item['obj'],'samples':[{'t':float(tv),'teacher_deg':list(map(float,y)),'prediction_deg':list(map(float,q*180/np.pi))} for tv,y,q in zip(t,deg,preds['normal'])],'method':'frozen series-67 rich observer -> state -> delay -> autonomous replay'});print(f'Репликация {item["index"]}/5.',flush=True)
  means={name:float(np.mean([r['normal']['rmse_rad'] if name=='normal' else r['zero']['rmse_rad'] if name=='zero' else r['controls'][name]['rmse_rad'] for r in rows])) for name in ('normal','zero','static','shuffled','reversed','closed')};diffs={name:means['normal']-means[name] for name in ('zero','static','shuffled','reversed','closed')};passed=all(diffs[name]<0 for name in ('zero','static','shuffled','reversed'));aggregate={'holdouts':5,'mean_rmse_rad':means,'normal_minus_control_rmse_rad':diffs,'normal_better_than_zero':sum(r['normal']['rmse_rad']<r['zero']['rmse_rad'] for r in rows),'normal_better_than_each_primary_control':sum(all(r['normal']['rmse_rad']<(r['zero']['rmse_rad'] if name=='zero' else r['controls'][name]['rmse_rad']) for name in ('zero','static','shuffled','reversed')) for r in rows),'primary_pass':passed}
  report={'schema':'frozen-rich-observer-replication-result-v1','created_utc':datetime.now(timezone.utc).isoformat(),'status':'fixture_completed' if allow_fixture_source else 'completed','protocol':protocol,'source_series67_aggregate':summary67['aggregate'],'aggregate':aggregate,'holdouts':rows,'limitations':['Замороженная synthetic модель; нового обучения нет.','Батарея matched по тому же общему генератору, но движения новые.','Observer units и cosine replay не являются мозгом, мышцами или доказательством зеркальных нейронов.']};save_json(temp/'summary.json',report);lines=['СЕРИЯ 68: ЗАМОРОЖЕННАЯ РЕПЛИКАЦИЯ СЕРИИ 67','',f'Средняя RMSE: {means}.',f'Normal минус контроли: {diffs}.',f'Normal лучше zero: {aggregate["normal_better_than_zero"]}/5.',f'Normal лучше всех primary-контролей отдельно: {aggregate["normal_better_than_each_primary_control"]}/5.',f'Составной primary пройден: {"ДА" if passed else "НЕТ"}.','','Модель серии 67 не переобучалась и не изменялась.',*report['limitations']];(temp/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');files={str(q.relative_to(temp)).replace('\\','/'):file_sha(q) for q in temp.rglob('*') if q.is_file()};save_json(temp/'complete.json',{'files':files});temp.rename(folder/'result');(folder/'INCOMPLETE.txt').unlink();verify_result(folder/'result');print('Готово:',folder/'result')
  if os.name=='nt':
   try:os.startfile(str(folder/'result'))
   except OSError:pass
  return folder
 except Exception:
  raise

def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
 try:
  source=filedialog.askdirectory(title='Завершённая успешная серия 67 piecewise_rich_replay_...',initialdir=str(SOURCE_ROOT.resolve()) if SOURCE_ROOT.exists() else str(Path.cwd()),parent=root)
  if not source:return
  messagebox.showinfo('Пять новых движений','Выберите пять НОВЫХ random JSON. Движения 31–35 повторять нельзя.',parent=root);hold=list(filedialog.askopenfilenames(title='Пять новых matched JSON',filetypes=[('Траектория JSON','*.json')],parent=root))
  if len(hold)!=5:raise ValueError(f'Выбрано {len(hold)}, нужно 5.')
  return run(source,hold)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source');p.add_argument('--holdouts',nargs='*');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--allow-fixture-source',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:return choose()
 if not a.source or len(a.holdouts or [])!=5:p.error('Нужны --source и ровно пять --holdouts.')
 return run(a.source,a.holdouts,a.output_root,a.allow_fixture_source)
if __name__=='__main__':
 try:sys.exit(0 if main() is not None else 0)
 except Exception as exc:print(f'ОШИБКА СЕРИИ 68: {type(exc).__name__}: {exc}\nЗамороженная модель и JSON не изменялись.',file=sys.stderr,flush=True);sys.exit(1)
