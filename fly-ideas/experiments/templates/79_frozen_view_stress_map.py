#!/usr/bin/env python3
"""Series 79: read-only geometric stress map of the frozen series-78 model."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,itertools,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER78=HERE/'78_eight_hour_view_robust_autonomous_grooming.py'
RUNNER78_SHA='886a2683073b0d8322cf195c88d6904424c8578a52c566420fe4da5684216caa'
ROOT=Path('workspace/runs/ideas/i-observational/frozen-view-stress-map')
SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/view-robust-autonomous-grooming-eight-hour')
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
MATCHED={'fov_deg':35.,'camera_side':.20,'camera_z':.42,'body_x':4.,'body_y':0.}
CORE_LIMITS={'fov_deg':(30.,70.),'camera_side':(.14,.42),'camera_z':(.36,.56),'body_x':(3.82,4.18),'body_y':(-.32,.32)}
EVAL_LIMITS={'fov_deg':(28.,72.),'camera_side':(.12,.46),'camera_z':(.34,.59),'body_x':(3.76,4.24),'body_y':(-.38,.38)}
SWEEPS={'fov_deg':[20,25,28,30,35,40,50,60,70,72,75], 'camera_side':[.08,.12,.14,.20,.32,.42,.46,.50], 'camera_z':[.28,.34,.36,.42,.56,.59,.65], 'body_x':[3.60,3.76,3.82,4.,4.18,4.24,4.40], 'body_y':[-.60,-.45,-.38,-.32,0.,.32,.38,.45,.60]}
POSTHOC_PROBES=[
 {'fov_deg':71.54015111625927,'camera_side':.18786318132127813,'camera_z':.4867552277178486,'body_x':4.117513838318502,'body_y':-.3597732892872945},
 {'fov_deg':69.97206780732671,'camera_side':.22002676857804493,'camera_z':.5117833051768443,'body_x':3.7769149634221892,'body_y':.3195634247321193},
]

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}
def load78():
 if file_sha(RUNNER78)!=RUNNER78_SHA:raise ValueError('Закреплённый runner серии 78 изменился.')
 spec=importlib.util.spec_from_file_location('stress78',RUNNER78);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def source78(folder,allow_fixture=False):
 m=load78();proto,ev,pre,stim,ck,base,large=m.dependencies();folder=Path(folder).resolve();saved,state,stage,_=m.saved_state(folder/'study.sqlite3',proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая серия 78.')
 out=folder/'result';m.verify_result(out,saved,state);summary=json.loads((out/'summary.json').read_text(encoding='utf8'))
 expected='fixture_completed' if allow_fixture else 'completed'
 if summary.get('status')!=expected or summary.get('schema')!='eight-hour-view-robust-autonomous-grooming-result-v1':raise ValueError('Источник не является завершённой серией 78 требуемого режима.')
 model_path=out/'model_new.npz'
 if file_sha(model_path)!=summary.get('new_model_sha256'):raise ValueError('SHA frozen модели серии 78 не совпадает.')
 with np.load(model_path,allow_pickle=False) as z:model=ev.checked_model({k:z[k] for k in z.files})
 return m,proto,ev,folder,saved,state,summary,model

def holdout(ident):
 if type(ident)!=int or not 161<=ident<=164:raise ValueError('Holdout серии 79 должен быть 161–164.')
 rng=np.random.default_rng(np.random.SeedSequence([7902,ident]));t=np.arange(51,dtype=float)/25;count=5 if ident<=162 else 9;knots=np.linspace(0,2,count);values=rng.integers(-55,56,size=(count,6)).astype(float)
 values[:,3]=np.clip(-values[:,0]+np.rint(.25*values[:,3]),-55,55);values[:,4]=np.clip(values[:,1]+np.rint(.25*values[:,4]),-55,55);values[:,5]=np.clip(-values[:,2]+np.rint(.25*values[:,5]),-55,55)
 degrees=np.stack([np.interp(t,knots,values[:,j]) for j in range(6)],axis=1)
 return {'test_id':ident,'seed':[7902,ident],'family':f'piecewise{count}','keyframes_deg':values.astype(int).tolist(),'motion_sha256':sha(np.asarray(degrees,dtype='<f8').tobytes())},t,degrees

def view_key(view):return tuple(round(float(view[k]),12) for k in MATCHED)
def region(view,posthoc=False):
 if posthoc:return 'posthoc_series78_failure_probe'
 if all(CORE_LIMITS[k][0]<=view[k]<=CORE_LIMITS[k][1] for k in MATCHED):return 'training_envelope'
 if all(EVAL_LIMITS[k][0]<=view[k]<=EVAL_LIMITS[k][1] for k in MATCHED):return 'evaluation_envelope'
 return 'outside_envelope'
def grid():
 cells=[];seen=set()
 def add(name,view,kind,posthoc=False):
  view={k:float(view[k]) for k in MATCHED};key=view_key(view)
  if key in seen:return
  seen.add(key);cells.append({'cell_id':len(cells)+1,'name':name,'kind':kind,'region':region(view,posthoc),'view':view,'posthoc_inspired':posthoc})
 add('matched',MATCHED,'reference')
 for parameter,values in SWEEPS.items():
  for value in values:v=dict(MATCHED);v[parameter]=value;add(f'{parameter}_{value:g}',v,'one_factor')
 for i,values in enumerate(itertools.product(*[(CORE_LIMITS[k][0],CORE_LIMITS[k][1]) for k in MATCHED])):add(f'core_corner_{i+1:02d}',dict(zip(MATCHED,values)),'core_corner')
 for i,values in enumerate(itertools.product(*[(EVAL_LIMITS[k][0],EVAL_LIMITS[k][1]) for k in MATCHED])):add(f'eval_corner_{i+1:02d}',dict(zip(MATCHED,values)),'evaluation_corner')
 for i,v in enumerate(POSTHOC_PROBES):add(f'posthoc_probe_{i+1}',v,'posthoc_probe',True)
 return cells

def render_view(scene,commands,view):
 """Render the preregistered stress range, including values outside runner78's training guard."""
 if set(view)!=set(MATCHED) or not all(np.isfinite(float(view[k])) for k in MATCHED):raise ValueError('Неверная stress view.')
 fov=float(view['fov_deg']);side=float(view['camera_side']);z=float(view['camera_z'])
 if not 15<=fov<=85 or not .05<=side<=.55 or not .25<=z<=.70 or not 3.5<=view['body_x']<=4.5 or not -.7<=view['body_y']<=.7:raise ValueError('Stress view вне закреплённой безопасной области.')
 scene.cams=[scene.engine.camera([.9,y,z],[3.25,float(view['body_y'])*.35,.48],48,32,fov=fov) for y in (side,-side)]
 scene.model.body_pos[scene.body]=[float(view['body_x']),float(view['body_y']),float(scene.default_body[2])]
 return scene.render(commands)

def metrics(truth,pred):
 e=np.asarray(pred)-np.asarray(truth);return {'rmse_rad':float(np.sqrt(np.mean(e*e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)}}
def control_predictions(m,ev,images,model,ident,cell_id):
 variants={'normal':images,'shuffled':images[np.random.default_rng(np.random.SeedSequence([7903,ident,cell_id])).permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)};out={}
 for name,im in variants.items():
  x=ev.feature_history(im);raw=(x-model['mean'])/model['scale']@model['weights']+model['intercept'];clipped=np.clip(raw,-np.pi*55/180,np.pi*55/180);state,replay=m.compress_replay(clipped)
  out[name]={'prediction':replay,'state':state,'clipped_fraction':float(np.mean(np.abs(raw)>=np.pi*55/180)),'feature_max_std':float(np.max(np.std(x,axis=0)))}
 return out

def pooled(records,key,axis=None):
 vals=[(r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad']) for r in records];return float(np.sqrt(np.mean(np.square(vals))))

def run(source,output_root=ROOT,allow_fixture_source=False):
 m,proto,ev,source,saved,state,source_summary,model=source78(source,allow_fixture_source);before={p.relative_to(source):file_sha(p) for p in source.rglob('*') if p.is_file()};cells=grid()
 output_root=Path(output_root);output_root.mkdir(parents=True,exist_ok=True);folder=output_root/('frozen_view_stress_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result.tmp';temp.mkdir()
 protocol={'schema':'frozen-view-stress-map-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner78_sha256':RUNNER78_SHA,'source_series78':str(source),'source_protocol_sha256':sha(canonical(saved).encode()),'source_model_sha256':source_summary['new_model_sha256'],'mode':'fixture' if allow_fixture_source else 'full','holdout_seed':7902,'holdouts':list(range(161,165)),'cells':cells,'no_retraining':True,'state_coefficients':72,'delay_s':.5,'primary_subset':'32 core_corner cells only; matched and posthoc probes excluded','primary_rule':'for every axis pooled normal below zero and >=70% case wins; combined normal below zero and shuffled/static/closed; >=24/32 core cells pass six-axis pooled-by-motion rule'};save_json(folder/'protocol.json',protocol)
 all_records=[];prediction_rows=[];scene=m.VisibleForelegGroomingScene(proto.load('stress79_engine','38_two_flies_observation.py'))
 for cell in cells:
  cell_records=[]
  for ident in range(161,165):
   spec,t,degrees=holdout(ident);truth=degrees[2:]*np.pi/180;images=render_view(scene,degrees*np.pi/180,cell['view']);preds=control_predictions(m,ev,images,model,ident,cell['cell_id']);zero=np.zeros_like(truth);state_sha=sha(np.asarray(preds['normal']['state'],dtype='<f8').tobytes())
   rec={'cell_id':cell['cell_id'],'cell_name':cell['name'],'kind':cell['kind'],'region':cell['region'],'posthoc_inspired':cell['posthoc_inspired'],'view':cell['view'],'test_id':ident,'spec':spec,'frames':49,'normal':metrics(truth,preds['normal']['prediction']),'zero':metrics(truth,zero),'controls':{k:metrics(truth,preds[k]['prediction']) for k in ('shuffled','static','closed')},'diagnostics':{'rgb_sha256':sha(images.tobytes()),'unique_rgb_frames':len({x.tobytes() for x in images}),'changed_rgb_values':int(np.count_nonzero(images[1:]!=images[:-1])),'normal_feature_max_std':preds['normal']['feature_max_std'],'normal_clipped_fraction':preds['normal']['clipped_fraction']},'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':True,'state_sha256_before_delay':state_sha,'state_sha256_after_delay':state_sha};cell_records.append(rec);all_records.append(rec)
   prediction_rows.extend([[cell['cell_id'],cell['name'],ident,float(tv),*map(float,y),*map(float,q)] for tv,y,q in zip(t[2:],truth,preds['normal']['prediction'])])
  print(f'Stress cell {cell["cell_id"]}/{len(cells)}: {cell["name"]}.',flush=True)
 core_cells=[]
 for cell in [c for c in cells if c['kind']=='core_corner']:
  rs=[r for r in all_records if r['cell_id']==cell['cell_id']];axes={}
  for a in AXES:
   n=pooled(rs,'normal',a);z=pooled(rs,'zero',a);wins=sum(r['normal']['axis_rmse_rad'][a]<r['zero']['axis_rmse_rad'][a] for r in rs);axes[a]={'normal':n,'zero':z,'wins':wins,'passed':n<z and wins>=3}
  n=pooled(rs,'normal');z=pooled(rs,'zero');controls={k:float(np.sqrt(np.mean([r['controls'][k]['rmse_rad']**2 for r in rs]))) for k in ('shuffled','static','closed')};passed=all(v['passed'] for v in axes.values()) and n<z and all(n<controls[k] for k in controls);core_cells.append({'cell_id':cell['cell_id'],'name':cell['name'],'view':cell['view'],'normal':n,'zero':z,'controls':controls,'axes':axes,'passed':passed})
 core_ids={c['cell_id'] for c in core_cells};core=[r for r in all_records if r['cell_id'] in core_ids];axes={}
 for a in AXES:
  n=pooled(core,'normal',a);z=pooled(core,'zero',a);wins=sum(r['normal']['axis_rmse_rad'][a]<r['zero']['axis_rmse_rad'][a] for r in core);axes[a]={'normal':n,'zero':z,'wins':wins,'cases':len(core),'passed':n<z and wins>=.70*len(core)}
 combined={'normal':pooled(core,'normal'),'zero':pooled(core,'zero')}
 for k in ('shuffled','static','closed'):combined[k]=float(np.sqrt(np.mean([r['controls'][k]['rmse_rad']**2 for r in core])))
 passed_cells=sum(c['passed'] for c in core_cells);primary={'axes':axes,'combined':combined,'core_cells_passed':passed_cells,'core_cells_total':len(core_cells),'passed':all(v['passed'] for v in axes.values()) and combined['normal']<combined['zero'] and all(combined['normal']<combined[k] for k in ('shuffled','static','closed')) and passed_cells>=24}
 summary_cells=[]
 for cell in cells:
  rs=[r for r in all_records if r['cell_id']==cell['cell_id']];summary_cells.append({**cell,'normal':pooled(rs,'normal'),'zero':pooled(rs,'zero'),'shuffled':float(np.sqrt(np.mean([r['controls']['shuffled']['rmse_rad']**2 for r in rs]))),'static':float(np.sqrt(np.mean([r['controls']['static']['rmse_rad']**2 for r in rs]))),'closed':float(np.sqrt(np.mean([r['controls']['closed']['rmse_rad']**2 for r in rs]))),'clipped_fraction':float(np.mean([r['diagnostics']['normal_clipped_fraction'] for r in rs])),'all_axes_better_zero':all(pooled(rs,'normal',a)<pooled(rs,'zero',a) for a in AXES)})
 report={'schema':'frozen-view-stress-map-result-v1','status':'fixture_completed' if allow_fixture_source else 'completed','protocol':protocol,'primary':primary,'cells':summary_cells,'records':all_records,'limitations':['Frozen stress map; no retraining or model selection.','Posthoc probes repeat series-78 failure-inspired views and are excluded from primary.','Grid maps only a synthetic parameter family, not arbitrary natural vision.','Replay reconstructs observed action; contacts and actuator dynamics are not evaluated.']};save_json(temp/'summary.json',report)
 with (temp/'stress_cells.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['cell_id','name','kind','region','posthoc_inspired',*MATCHED,'normal','zero','shuffled','static','closed','clipped_fraction','all_axes_better_zero']);w.writeheader()
  for c in summary_cells:w.writerow({**{k:c[k] for k in ('cell_id','name','kind','region','posthoc_inspired','normal','zero','shuffled','static','closed','clipped_fraction','all_axes_better_zero')},**c['view']})
 with (temp/'autonomous_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['cell_id','cell_name','test_id','time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'autonomous_{a}_rad' for a in AXES]]);w.writerows(prediction_rows)
 (temp/'ИТОГ.txt').write_text('\n'.join(['СЕРИЯ 79: FROZEN VIEW STRESS MAP',f'Primary core envelope: {"ВЫПОЛНЕН" if primary["passed"] else "НЕ ВЫПОЛНЕН"}.',f'Core cells passed: {passed_cells}/{len(core_cells)}.',f'Core pooled normal/zero: {combined["normal"]:.6f}/{combined["zero"]:.6f}.','Модель серии 78 не переобучалась.',*report['limitations']])+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(canonical(protocol).encode()),'files':output_manifest(temp)});temp.rename(folder/'result')
 if before!={p.relative_to(source):file_sha(p) for p in source.rglob('*') if p.is_file()}:raise ValueError('Frozen source изменилась во время stress map.')
 if os.name=='nt':
  try:os.startfile(str(folder/'result'))
  except OSError:pass
 print('Готово:',folder/'result');return folder

def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
 try:
  source=filedialog.askdirectory(title='Выберите завершённую серию 78 view_robust_autonomous_grooming_eight_hour_...',initialdir=str(SOURCE_ROOT.resolve()) if SOURCE_ROOT.exists() else str(Path.cwd()),parent=root)
  if not source:return
  messagebox.showinfo('Frozen stress map',f'Модель не переобучается. Будут проверены 4 новых движения и {len(grid())} фиксированных view cells.',parent=root);return run(source)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--allow-fixture-source',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:return choose()
 if not a.source:p.error('Нужен --source или --choose.')
 return run(a.source,a.output_root,a.allow_fixture_source)
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА СЕРИИ 79: {type(exc).__name__}: {exc}\nFrozen source не изменялась.',file=sys.stderr,flush=True);sys.exit(1)
