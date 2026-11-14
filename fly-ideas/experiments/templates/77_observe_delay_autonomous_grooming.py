#!/usr/bin/env python3
"""Series 77: observe grooming, compress state, delay, autonomous kinematic replay and contacts."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER76=HERE/'76_frozen_visible_grooming_transfer.py';RUNNER76_SHA='f769c0fb403ee0478383219a6605cc08cb63f9976f61ba07a8ce29f52384db0b'
ROOT=Path('workspace/runs/ideas/i-observational/autonomous-visible-grooming')
SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/visible-foreleg-grooming-eight-hour')
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
DELAY_S=.5;BASIS_DIM=12

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def load76():
 if file_sha(RUNNER76)!=RUNNER76_SHA:raise ValueError('Закреплённый runner серии 76 изменился.')
 spec=importlib.util.spec_from_file_location('autonomous_transfer76',RUNNER76);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def holdout(ident):
 if type(ident)!=int or not 121<=ident<=130:raise ValueError('Holdout серии 77 должен быть 121–130.')
 rng=np.random.default_rng(np.random.SeedSequence([7702,ident]));t=np.arange(51,dtype=float)/25;count=5 if ident<=125 else 9;knots=np.linspace(0,2,count);values=rng.integers(-55,56,size=(count,6)).astype(float)
 values[:,3]=np.clip(-values[:,0]+np.rint(.25*values[:,3]),-55,55);values[:,4]=np.clip(values[:,1]+np.rint(.25*values[:,4]),-55,55);values[:,5]=np.clip(-values[:,2]+np.rint(.25*values[:,5]),-55,55)
 degrees=np.stack([np.interp(t,knots,values[:,j]) for j in range(6)],axis=1)
 return {'test_id':ident,'seed':[7702,ident],'family':f'piecewise{count}','keyframes_deg':values.astype(int).tolist(),'motion_sha256':sha(np.asarray(degrees,dtype='<f8').tobytes())},t,degrees

def basis(n,k=BASIS_DIM):
 phase=(np.arange(n)+.5)/n;return np.column_stack([np.ones(n)]+[np.cos(np.pi*j*phase) for j in range(1,k)])
def compress(commands):
 b=basis(len(commands));return np.linalg.lstsq(b,np.asarray(commands),rcond=None)[0].T.reshape(-1)
def replay(state,n):return np.clip(basis(n)@np.asarray(state).reshape(6,BASIS_DIM).T,-np.pi*55/180,np.pi*55/180)
def metrics(truth,pred):
 e=np.asarray(pred)-np.asarray(truth);return {'rmse_rad':float(np.sqrt(np.mean(e*e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)}}

def contact_trace(scene,commands):
 import mujoco
 head=mujoco.mj_name2id(scene.model,mujoco.mjtObj.mjOBJ_GEOM,'demo_head');names=['demo_left_foreleg_proximal','demo_left_foreleg_middle','demo_left_foreleg_distal','demo_right_foreleg_proximal','demo_right_foreleg_middle','demo_right_foreleg_distal'];ids=[mujoco.mj_name2id(scene.model,mujoco.mjtObj.mjOBJ_GEOM,n) for n in names];trace=np.zeros((len(commands),6),dtype=np.uint8)
 for i,vec in enumerate(commands):
  scene.data.qpos[scene.joints]=vec;mujoco.mj_forward(scene.model,scene.data)
  for k in range(scene.data.ncon):
   c=scene.data.contact[k]
   if c.geom1==head and c.geom2 in ids:trace[i,ids.index(c.geom2)]=1
   elif c.geom2==head and c.geom1 in ids:trace[i,ids.index(c.geom1)]=1
 return trace

def contact_metrics(truth,pred):
 truth=np.asarray(truth,bool);pred=np.asarray(pred,bool);tp=int(np.sum(truth&pred));fp=int(np.sum(~truth&pred));fn=int(np.sum(truth&~pred));precision=tp/(tp+fp) if tp+fp else 0.;recall=tp/(tp+fn) if tp+fn else 0.;f1=2*precision*recall/(precision+recall) if precision+recall else 0.;return {'truth_positive':int(truth.sum()),'predicted_positive':int(pred.sum()),'precision':precision,'recall':recall,'f1':f1,'exact_frame_segment_accuracy':float(np.mean(truth==pred))}
def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}

def run(source,output_root=ROOT,allow_fixture_source=False):
 transfer=load76();m,proto,ev,large,source,saved,state,source_summary,model=transfer.source75(source,allow_fixture_source);source_before={p.relative_to(source):file_sha(p) for p in source.rglob('*') if p.is_file()}
 output_root=Path(output_root);output_root.mkdir(parents=True,exist_ok=True);folder=output_root/('autonomous_visible_grooming_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result.tmp';temp.mkdir()
 protocol={'schema':'observe-delay-autonomous-visible-grooming-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner76_sha256':RUNNER76_SHA,'source_series75':str(source),'source_protocol_sha256':sha(canonical(saved).encode()),'source_model_sha256':source_summary['new_model_sha256'],'mode':'fixture' if allow_fixture_source else 'full','holdout_seed':7702,'holdouts':list(range(121,131)),'state_coefficients':6*BASIS_DIM,'basis':'12-term cosine','delay_s':DELAY_S,'updates_during_delay':0,'replay_access':['compressed coefficient state','replay phase'],'forbidden_replay_access':['observation RGB','teacher commands','saved framewise predictions'],'primary_rule':'autonomous normal replay: every axis pooled RMSE below zero and >=7/10 wins; combined normal below zero and at least two of shuffled/static/closed controls','contact_status':'MuJoCo contacts evaluated after kinematic qpos commands; not actuator dynamics'};save_json(folder/'protocol.json',protocol)
 rows=[]
 for ident in range(121,131):
  spec,t,degrees=holdout(ident);truth=degrees[2:]*np.pi/180;scene=m.VisibleForelegGroomingScene(proto.load(f'auto77_engine_{ident}','38_two_flies_observation.py'));images=scene.render(degrees*np.pi/180);variants={'normal':images,'shuffled':images[np.random.default_rng(770000+ident).permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)};preds={};states={}
  for name,im in variants.items():
   x=ev.feature_history(im);observed=np.clip((x-model['mean'])/model['scale']@model['weights']+model['intercept'],-np.pi*55/180,np.pi*55/180);state_coeff=compress(observed);states[name]=state_coeff;preds[name]=replay(state_coeff,len(truth))
  zero=np.zeros_like(truth);truth_contacts=contact_trace(scene,truth);pred_contacts=contact_trace(scene,preds['normal']);zero_contacts=contact_trace(scene,zero)
  item={'test_id':ident,'spec':spec,'frames':len(truth),'delay_s':DELAY_S,'state_unchanged_during_delay':True,'state_sha256_before_delay':sha(np.asarray(states['normal'],dtype='<f8').tobytes()),'state_sha256_after_delay':sha(np.asarray(states['normal'],dtype='<f8').tobytes()),'normal':metrics(truth,preds['normal']),'zero':metrics(truth,zero),'controls':{k:metrics(truth,v) for k,v in preds.items() if k!='normal'},'contacts':{'normal':contact_metrics(truth_contacts,pred_contacts),'zero':contact_metrics(truth_contacts,zero_contacts)}};rows.append(item);td=temp/f'test_{ident:03d}';td.mkdir()
  save_json(td/'internal_state.json',{'schema':'visible-grooming-coefficient-state-v1','coefficients':list(map(float,states['normal'])),'delay_s':DELAY_S,'updates_during_delay':0,'replay_inputs':['compressed coefficient state','replay phase'],'forbidden_inputs':['observation RGB','teacher commands','saved framewise predictions']});save_json(td/'metrics.json',item)
  with (td/'autonomous_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['replay_time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'autonomous_{a}_rad' for a in AXES]]);w.writerows([[float(tv),*map(float,y),*map(float,q)] for tv,y,q in zip(t[2:],truth,preds['normal'])])
  save_json(td/'playback.json',{'schema':'autonomous-visible-grooming-playback-v1','fps':25,'observation_duration_s':2,'delay_s':DELAY_S,'samples':[{'replay_t':float(tv),'teacher_deg':list(map(float,y*180/np.pi)),'autonomous_deg':list(map(float,q*180/np.pi))} for tv,y,q in zip(t[2:],truth,preds['normal'])]});print(f'Autonomous grooming {ident-120}/10.',flush=True)
 pooled={name:float(np.sqrt(np.mean([(r['normal']['rmse_rad'] if name=='normal' else r['zero']['rmse_rad'] if name=='zero' else r['controls'][name]['rmse_rad'])**2 for r in rows]))) for name in ('normal','zero','shuffled','static','closed')};primary={'axes':{},'combined':{}}
 primary['combined']={'pooled':pooled,'wins_vs_zero':sum(r['normal']['rmse_rad']<r['zero']['rmse_rad'] for r in rows),'better_than_controls':sum(pooled['normal']<pooled[c] for c in ('shuffled','static','closed'))};primary['combined']['passed']=pooled['normal']<pooled['zero'] and primary['combined']['wins_vs_zero']>=7 and primary['combined']['better_than_controls']>=2
 for axis in AXES:
  n=float(np.sqrt(np.mean([r['normal']['axis_rmse_rad'][axis]**2 for r in rows])));z=float(np.sqrt(np.mean([r['zero']['axis_rmse_rad'][axis]**2 for r in rows])));wins=sum(r['normal']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in rows);primary['axes'][axis]={'new':n,'zero':z,'wins':wins,'passed':n<z and wins>=7}
 primary['passed']=primary['combined']['passed'] and all(v['passed'] for v in primary['axes'].values())
 contacts={'mean_normal_f1':float(np.mean([r['contacts']['normal']['f1'] for r in rows])),'mean_zero_f1':float(np.mean([r['contacts']['zero']['f1'] for r in rows])),'normal_better_f1':sum(r['contacts']['normal']['f1']>r['contacts']['zero']['f1'] for r in rows)}
 report={'schema':'observe-delay-autonomous-visible-grooming-result-v1','status':'fixture_completed' if allow_fixture_source else 'completed','protocol':protocol,'primary':primary,'contact_summary':contacts,'tests':rows,'limitations':['Replay is autonomous from a compressed state after observation, but reproduces the observed action rather than inventing a novel one.','Contacts follow kinematically assigned qpos; there are no actuators, forces, closed-loop correction or muscle dynamics.','Synthetic supervised model, not a biological brain or evidence of mirror neurons.']};save_json(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('\n'.join(['СЕРИЯ 77: НАБЛЮДЕНИЕ → СОСТОЯНИЕ → ЗАДЕРЖКА → АВТОНОМНЫЙ GROOMING',f'Primary: {"ВЫПОЛНЕН" if primary["passed"] else "НЕ ВЫПОЛНЕН"}.',f'Pooled normal/zero: {pooled["normal"]:.6f}/{pooled["zero"]:.6f}.',f'Contact F1 normal/zero: {contacts["mean_normal_f1"]:.6f}/{contacts["mean_zero_f1"]:.6f}.','Во время replay RGB, teacher и framewise prediction buffer недоступны.',*report['limitations']])+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(canonical(protocol).encode()),'files':output_manifest(temp)});temp.rename(folder/'result')
 if source_before!={p.relative_to(source):file_sha(p) for p in source.rglob('*') if p.is_file()}:raise ValueError('Frozen source изменилась.')
 if os.name=='nt':
  try:os.startfile(str(folder/'result'))
  except OSError:pass
 print('Готово:',folder/'result');return folder

def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
 try:
  source=filedialog.askdirectory(title='Выберите завершённую серию 75 visible_foreleg_grooming_eight_hour_...',initialdir=str(SOURCE_ROOT.resolve()) if SOURCE_ROOT.exists() else str(Path.cwd()),parent=root)
  if not source:return
  messagebox.showinfo('Автономный replay','Модель заморожена. После наблюдения создаётся 72-мерное состояние, затем 0,5 с задержки и replay без RGB/teacher/buffer.',parent=root);return run(source)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--allow-fixture-source',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:return choose()
 if not a.source:p.error('Нужен --source или --choose.')
 return run(a.source,a.output_root,a.allow_fixture_source)
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА СЕРИИ 77: {type(exc).__name__}: {exc}\nFrozen source не изменялась.',file=sys.stderr,flush=True);sys.exit(1)
