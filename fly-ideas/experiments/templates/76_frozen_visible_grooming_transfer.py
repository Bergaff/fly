#!/usr/bin/env python3
"""Series 76: frozen series-75 transfer across view, occlusion and temporal controls."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,os,platform,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER75=HERE/'75_eight_hour_visible_foreleg_grooming.py'
RUNNER75_SHA='415fe9a89543a7a120a50b6b891e56d61a466b7f64ba8105a34a17d322467416'
ROOT=Path('workspace/runs/ideas/i-observational/frozen-visible-grooming-transfer')
SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/visible-foreleg-grooming-eight-hour')
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
CONDITIONS=('matched','fov50','fov65','lateral_camera','body_shift','one_eye','distal_mask','temporal_shuffle')

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def load75():
 if file_sha(RUNNER75)!=RUNNER75_SHA:raise ValueError('Закреплённый runner серии 75 изменился.')
 spec=importlib.util.spec_from_file_location('frozen_visible75',RUNNER75);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def source75(folder,allow_fixture=False):
 m=load75();proto,ev,pre,stim,ck,base,large=m.dependencies();folder=Path(folder).resolve();db=folder/'study.sqlite3'
 saved,state,stage,_=m.saved_state(db,proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая серия 75.')
 out=folder/'result';m.verify_result(out,saved,state);summary=json.loads((out/'summary.json').read_text(encoding='utf8'))
 expected='fixture_completed' if allow_fixture else 'completed'
 if summary.get('status')!=expected:raise ValueError('Источник не является завершённой серией 75 требуемого режима.')
 model_path=out/'model_new.npz'
 if file_sha(model_path)!=summary.get('new_model_sha256'):raise ValueError('SHA frozen модели серии 75 не совпадает.')
 with np.load(model_path,allow_pickle=False) as z:model=ev.checked_model({k:z[k] for k in z.files})
 return m,proto,ev,large,folder,saved,state,summary,model

def holdout(ident):
 if type(ident)!=int or not 101<=ident<=110:raise ValueError('Holdout серии 76 должен быть 101–110.')
 rng=np.random.default_rng(np.random.SeedSequence([7602,ident]));t=np.arange(51,dtype=float)/25;count=5 if ident<=105 else 9;knots=np.linspace(0,2,count);values=rng.integers(-55,56,size=(count,6)).astype(float)
 values[:,3]=np.clip(-values[:,0]+np.rint(.25*values[:,3]),-55,55);values[:,4]=np.clip(values[:,1]+np.rint(.25*values[:,4]),-55,55);values[:,5]=np.clip(-values[:,2]+np.rint(.25*values[:,5]),-55,55)
 degrees=np.stack([np.interp(t,knots,values[:,j]) for j in range(6)],axis=1)
 return {'test_id':ident,'seed':[7602,ident],'family':f'piecewise{count}','keyframes_deg':values.astype(int).tolist(),'motion_sha256':sha(np.asarray(degrees,dtype='<f8').tobytes())},t,degrees

def scene_for(m,proto,condition):
 import mujoco
 engine=proto.load(f'transfer_engine_{condition}','38_two_flies_observation.py');scene=m.VisibleForelegGroomingScene(engine)
 if condition in ('fov50','fov65'):
  fov=50 if condition=='fov50' else 65;scene.cams=[engine.camera([.9,y,.42],[3.25,0,.48],48,32,fov=fov) for y in (.20,-.20)]
 elif condition=='lateral_camera':scene.cams=[engine.camera([.9,y,.50],[3.25,0,.48],48,32,fov=35) for y in (.38,-.38)]
 elif condition=='body_shift':
  body=mujoco.mj_name2id(scene.model,mujoco.mjtObj.mjOBJ_BODY,'demonstrator');scene.model.body_pos[body]=[4,.30,.4]
 return scene

def render_condition(m,proto,condition,degrees,ident):
 base='matched' if condition in ('one_eye','distal_mask','temporal_shuffle') else condition
 images=scene_for(m,proto,base).render(degrees*np.pi/180)
 if condition=='one_eye':images[:,1]=0
 elif condition=='distal_mask':images[:,:,7:25,15:39]=0
 elif condition=='temporal_shuffle':images=images[np.random.default_rng(760000+ident).permutation(len(images))].copy()
 return images

def metrics(truth,pred):
 e=np.asarray(pred)-np.asarray(truth);return {'rmse_rad':float(np.sqrt(np.mean(e*e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)}}
def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}

def run(source,output_root=ROOT,allow_fixture_source=False):
 m,proto,ev,large,source,saved,state,source_summary,model=source75(source,allow_fixture_source)
 source_before={p.relative_to(source):file_sha(p) for p in source.rglob('*') if p.is_file()}
 output_root=Path(output_root);output_root.mkdir(parents=True,exist_ok=True);folder=output_root/('frozen_visible_transfer_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result.tmp';temp.mkdir()
 protocol={'schema':'frozen-visible-grooming-transfer-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner75_sha256':RUNNER75_SHA,'source_series75':str(source),'source_protocol_sha256':sha(canonical(saved).encode()),'source_model_sha256':source_summary['new_model_sha256'],'mode':'fixture' if allow_fixture_source else 'full','holdout_seed':7602,'holdouts':list(range(101,111)),'conditions':list(CONDITIONS),'no_retraining':True,'primary_rule':'matched: each axis pooled new below zero and >=7/10 wins; geometric transfer: each axis pooled new below zero in at least 2/4 fov50,fov65,lateral_camera,body_shift conditions'};save_json(folder/'protocol.json',protocol)
 rows=[]
 for ident in range(101,111):
  spec,t,degrees=holdout(ident);truth=degrees[2:]*np.pi/180;item={'test_id':ident,'spec':spec,'frames':49,'conditions':{}}
  td=temp/f'test_{ident:03d}';td.mkdir()
  for condition in CONDITIONS:
   images=render_condition(m,proto,condition,degrees,ident);x=ev.feature_history(images);pred=np.clip((x-model['mean'])/model['scale']@model['weights']+model['intercept'],-np.pi*55/180,np.pi*55/180);item['conditions'][condition]=metrics(truth,pred)
   if condition=='matched':
    with (td/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
     w=csv.writer(f);w.writerow(['time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'predicted_{a}_rad' for a in AXES]]);w.writerows([[float(tv),*map(float,y),*map(float,q)] for tv,y,q in zip(t[2:],truth,pred)])
    np.savez_compressed(td/'matched_observation.npz',eye_rgb=images,times_s=t)
  item['zero']=metrics(truth,np.zeros_like(truth));rows.append(item);save_json(td/'metrics.json',item);print(f'Frozen transfer {ident-100}/10.',flush=True)
 primary={'matched':{},'geometric_transfer':{},'passed':True};geometric=('fov50','fov65','lateral_camera','body_shift')
 for axis in AXES:
  j=AXES.index(axis);zero=float(np.sqrt(np.mean([r['zero']['axis_rmse_rad'][axis]**2 for r in rows])));matched=float(np.sqrt(np.mean([r['conditions']['matched']['axis_rmse_rad'][axis]**2 for r in rows])));wins=sum(r['conditions']['matched']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in rows);mpass=matched<zero and wins>=7
  cond={c:{'pooled_rmse_rad':float(np.sqrt(np.mean([r['conditions'][c]['axis_rmse_rad'][axis]**2 for r in rows])))} for c in geometric};better=sum(v['pooled_rmse_rad']<zero for v in cond.values());gpass=better>=2
  primary['matched'][axis]={'new':matched,'zero':zero,'wins':wins,'passed':mpass};primary['geometric_transfer'][axis]={'conditions':cond,'better_than_zero_conditions':better,'passed':gpass};primary['passed']&=mpass and gpass
 report={'schema':'frozen-visible-grooming-transfer-result-v1','status':'fixture_completed' if allow_fixture_source else 'completed','protocol':protocol,'primary':primary,'tests':rows,'limitations':['Frozen synthetic model; no retraining.','View changes are hand-designed and do not represent natural fly vision.','Temporal shuffle and masks are diagnostic controls, not biological interventions.']};save_json(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('\n'.join(['СЕРИЯ 76: FROZEN TRANSFER VISIBLE GROOMING',f'Primary: {"ВЫПОЛНЕН" if primary["passed"] else "НЕ ВЫПОЛНЕН"}.','Модель серии 75 не переобучалась.',*report['limitations']])+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(canonical(protocol).encode()),'files':output_manifest(temp)});temp.rename(folder/'result')
 if source_before!={p.relative_to(source):file_sha(p) for p in source.rglob('*') if p.is_file()}:raise ValueError('Frozen source изменилась во время transfer.')
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
  messagebox.showinfo('Frozen transfer','Модель не переобучается. Автоматически проверяются holdout 101–110 в восьми условиях.',parent=root);return run(source)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--allow-fixture-source',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:return choose()
 if not a.source:p.error('Нужен --source или --choose.')
 return run(a.source,a.output_root,a.allow_fixture_source)
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА СЕРИИ 76: {type(exc).__name__}: {exc}\nFrozen source не изменялась.',file=sys.stderr,flush=True);raise
