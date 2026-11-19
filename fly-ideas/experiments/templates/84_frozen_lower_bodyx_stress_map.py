#!/usr/bin/env python3
"""Series 84: read-only lower-body-X stress map of frozen series-83 model."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,itertools,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER83=HERE/'83_eight_hour_fixed_fov_autonomous_grooming.py'
RUNNER83_SHA='dac7ea443081aad92faed5c0986066a617fcd2e61735b9292d1979dc6a8fb931'
ROOT=Path('workspace/runs/ideas/i-observational/frozen-lower-bodyx-stress-map')
SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/fixed-fov-autonomous-grooming-eight-hour')
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
X_VALUES=(3.70,3.76,3.82,3.88,4.00,4.12,4.18,4.24,4.30)
CORE_X=(3.82,4.18);SIDES=(.14,.42);ZS=(.36,.56);YS=(-.32,.32)
FAILED_MOTIONS=(261,262,263,265,266,269);FAILED_CORNERS=(1,5,6,9,13,14)

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}
def load83():
 if file_sha(RUNNER83)!=RUNNER83_SHA:raise ValueError('Закреплённый runner серии 83 изменился.')
 spec=importlib.util.spec_from_file_location('stress84_source83',RUNNER83);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def source83(folder,allow_fixture=False):
 m=load83();proto,ev,pre,stim,ck,base,large=m.dependencies();folder=Path(folder).resolve();saved,state,stage,_=m.saved_state(folder/'study.sqlite3',proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая серия 83.')
 out=folder/'result';m.verify_result(out,saved,state);summary=json.loads((out/'summary.json').read_text(encoding='utf8'));expected='fixture_completed' if allow_fixture else 'completed'
 if summary.get('status')!=expected or summary.get('schema')!='eight-hour-fixed-fov-autonomous-grooming-result-v1':raise ValueError('Источник не является завершённой серией 83 требуемого режима.')
 model_path=out/'model_new.npz'
 if file_sha(model_path)!=summary.get('new_model_sha256'):raise ValueError('SHA frozen модели серии 83 не совпадает.')
 with np.load(model_path,allow_pickle=False) as z:model=ev.checked_model({k:z[k] for k in z.files})
 train,tests=proto.split_from_sources(state['sources'],stim);labels={x['copy']:x for x in saved['labels']};source_tests={}
 for item in tests:
  label=labels[f'test_{item["id"]:03d}.json'];name=label.get('original_basename','')
  if label['role']=='new_test' and name.startswith('holdout_'):source_tests[int(name[8:11])]=item
 return m,proto,ev,folder,saved,state,summary,model,source_tests

def new_motion(ident):
 if type(ident)!=int or not 281<=ident<=286:raise ValueError('Новый holdout серии 84 должен быть 281–286.')
 rng=np.random.default_rng(np.random.SeedSequence([8402,ident]));t=np.arange(51,dtype=float)/25;count=5 if ident<=283 else 9;knots=np.linspace(0,2,count);v=rng.integers(-55,56,size=(count,6)).astype(float);v[:,3]=np.clip(-v[:,0]+np.rint(.25*v[:,3]),-55,55);v[:,4]=np.clip(v[:,1]+np.rint(.25*v[:,4]),-55,55);v[:,5]=np.clip(-v[:,2]+np.rint(.25*v[:,5]),-55,55);deg=np.stack([np.interp(t,knots,v[:,j]) for j in range(6)],1)
 return {'test_id':ident,'seed':[8402,ident],'family':f'piecewise{count}','keyframes_deg':v.astype(int).tolist(),'motion_sha256':sha(np.asarray(deg,dtype='<f8').tobytes())},t,deg

def grid():
 cells=[]
 for x,side,z,y in itertools.product(X_VALUES,SIDES,ZS,YS):
  view={'fov_deg':35.,'camera_side':side,'camera_z':z,'body_x':x,'body_y':y};kind='core_corner' if x in CORE_X else 'body_x_neighbor';cells.append({'cell_id':len(cells)+1,'name':f'x{x:.2f}_s{side:.2f}_z{z:.2f}_y{y:+.2f}','kind':kind,'view':view})
 return cells

def metrics(truth,pred):
 e=np.asarray(pred)-np.asarray(truth);return {'rmse_rad':float(np.sqrt(np.mean(e*e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)}}
def predictions(m,images,model,ident,cell_id):
 variants={'normal':images,'shuffled':images[np.random.default_rng(np.random.SeedSequence([8403,ident,cell_id])).permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)};out={}
 for name,im in variants.items():
  x=m.edge_history(im);raw=(x-model['mean'])/model['scale']@model['weights']+model['intercept'];frame=np.clip(raw,-np.pi*55/180,np.pi*55/180);state,replay=m.compress_replay(frame);out[name]={'prediction':replay,'state':state,'clipped_fraction':float(np.mean(np.abs(raw)>=np.pi*55/180)),'feature_max_std':float(np.max(np.std(x,0)))}
 return out
def pooled(records,key,axis=None):
 vals=[r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad'] for r in records];return float(np.sqrt(np.mean(np.square(vals))))
def summarize_cell(cell,records,required_wins):
 axes={}
 for a in AXES:
  n=pooled(records,'normal',a);z=pooled(records,'zero',a);wins=sum(r['normal']['axis_rmse_rad'][a]<r['zero']['axis_rmse_rad'][a] for r in records);axes[a]={'normal':n,'zero':z,'wins':wins,'cases':len(records),'passed':n<z and wins>=required_wins}
 n=pooled(records,'normal');z=pooled(records,'zero');controls={k:float(np.sqrt(np.mean([r['controls'][k]['rmse_rad']**2 for r in records]))) for k in ('shuffled','static','closed')};passed=all(x['passed'] for x in axes.values())
 return {**cell,'normal':n,'zero':z,'controls':controls,'axes':axes,'passed':passed}

def run(source,output_root=ROOT,allow_fixture_source=False):
 m,proto,ev,source,saved,state,source_summary,model,source_tests=source83(source,allow_fixture_source);before={p.relative_to(source):file_sha(p) for p in source.rglob('*') if p.is_file()};all_cells=grid();cells=[all_cells[i] for i in (0,16,48,71)] if allow_fixture_source else all_cells;new_ids=(281,282) if allow_fixture_source else tuple(range(281,287))
 output_root=Path(output_root);output_root.mkdir(parents=True,exist_ok=True);folder=output_root/('frozen_lower_bodyx_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result.tmp';temp.mkdir()
 protocol={'schema':'frozen-lower-bodyx-stress-map-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner83_sha256':RUNNER83_SHA,'source_series83':str(source),'source_protocol_sha256':sha(canonical(saved).encode()),'source_model_sha256':source_summary['new_model_sha256'],'mode':'fixture' if allow_fixture_source else 'full','new_motion_seed':8402,'new_motions':list(new_ids),'x_values':list(X_VALUES),'geometry_factors':{'camera_side':list(SIDES),'camera_z':list(ZS),'body_y':list(YS),'fov_deg':35},'cells':cells,'no_retraining':True,'state_coefficients':72,'delay_s':.5,'exact_failed_probe_motions':list(FAILED_MOTIONS),'exact_failed_probe_corners':list(FAILED_CORNERS),'primary_subset':'new motions x 16 core corners at bodyX3.82/4.18 only','primary_rule':'every axis pooled normal<zero and >=70% wins; combined below zero/shuffled/static/closed; bodyX3.82 repeats axis rule; >=12/16 core cells pass every axis pooled<zero and >=5/6 wins'};save_json(folder/'protocol.json',protocol)
 scene=m.VisibleForelegGroomingScene(proto.load('stress84_engine','38_two_flies_observation.py'));records=[];rows=[]
 for cell in cells:
  for ident in new_ids:
   spec,t,deg=new_motion(ident);truth=deg[2:]*np.pi/180;images=scene.render(deg*np.pi/180,view=cell['view']);pred=predictions(m,images,model,ident,cell['cell_id']);zero=np.zeros_like(truth);state_sha=sha(np.asarray(pred['normal']['state'],dtype='<f8').tobytes());rec={'cell_id':cell['cell_id'],'cell_name':cell['name'],'kind':cell['kind'],'view':cell['view'],'test_id':ident,'spec':spec,'frames':49,'normal':metrics(truth,pred['normal']['prediction']),'zero':metrics(truth,zero),'controls':{k:metrics(truth,pred[k]['prediction']) for k in ('shuffled','static','closed')},'diagnostics':{'rgb_sha256':sha(images.tobytes()),'unique_rgb_frames':len({x.tobytes() for x in images}),'changed_rgb_values':int(np.count_nonzero(images[1:]!=images[:-1])),'normal_feature_max_std':pred['normal']['feature_max_std'],'normal_clipped_fraction':pred['normal']['clipped_fraction']},'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':True,'state_sha256_before_delay':state_sha,'state_sha256_after_delay':state_sha};records.append(rec);rows.extend([[cell['cell_id'],cell['name'],ident,float(tv),*map(float,y),*map(float,q)] for tv,y,q in zip(t[2:],truth,pred['normal']['prediction'])])
  print(f'Stress cell {cell["cell_id"]}/{len(all_cells)}: {cell["name"]}.',flush=True)
 # Exact source-failure probes are diagnostic and must reproduce source83 normal metrics/state.
 source_lookup={(r['test_id'],r['corner_id']):r for r in source_summary['tests']};probe_records=[];corner_lookup={c['corner_id']:c for c in m.geometry_corners()}
 desired=[(mid,cid) for mid in FAILED_MOTIONS for cid in FAILED_CORNERS];available=[x for x in desired if x in source_lookup and x[0] in source_tests]
 if not allow_fixture_source and available!=desired:raise ValueError(f'Источник 83 не содержит все exact failed probes: {len(available)}/{len(desired)}.')
 for mid,cid in available:
  item=source_tests[mid];truth_full=item['angles_deg']*np.pi/180;truth=truth_full[2:];view=corner_lookup[cid]['view'];images=scene.render(truth_full,view=view);pred=predictions(m,images,model,mid,cid);normal=metrics(truth,pred['normal']['prediction']);state_sha=sha(np.asarray(pred['normal']['state'],dtype='<f8').tobytes());old=source_lookup[(mid,cid)];metric_match=canonical(normal)==canonical(old['normal']);state_match=state_sha==old['state_sha256_before_delay']
  if not metric_match or not state_match:raise ValueError(f'Frozen reproduction mismatch for motion {mid}, corner {cid}.')
  probe_records.append({'test_id':mid,'corner_id':cid,'view':view,'normal':normal,'zero':metrics(truth,np.zeros_like(truth)),'source_metric_match':metric_match,'source_state_match':state_match,'state_sha256':state_sha})
 core_cells=[c for c in cells if c['kind']=='core_corner'];core_ids={c['cell_id'] for c in core_cells};core=[r for r in records if r['cell_id'] in core_ids];threshold=.70*len(core);axes={}
 for a in AXES:
  n=pooled(core,'normal',a);z=pooled(core,'zero',a);wins=sum(r['normal']['axis_rmse_rad'][a]<r['zero']['axis_rmse_rad'][a] for r in core);axes[a]={'normal':n,'zero':z,'wins':wins,'cases':len(core),'passed':n<z and wins>=threshold}
 combined={'normal':pooled(core,'normal'),'zero':pooled(core,'zero')}
 for k in ('shuffled','static','closed'):combined[k]=float(np.sqrt(np.mean([r['controls'][k]['rmse_rad']**2 for r in core])))
 lower=[r for r in core if r['view']['body_x']==3.82];lower_axes={}
 for a in AXES:
  n=pooled(lower,'normal',a);z=pooled(lower,'zero',a);wins=sum(r['normal']['axis_rmse_rad'][a]<r['zero']['axis_rmse_rad'][a] for r in lower);lower_axes[a]={'normal':n,'zero':z,'wins':wins,'cases':len(lower),'passed':n<z and wins>=.70*len(lower)}
 required_wins=2 if allow_fixture_source else 5;cell_summaries=[summarize_cell(c,[r for r in records if r['cell_id']==c['cell_id']],required_wins) for c in cells];core_summary=[c for c in cell_summaries if c['kind']=='core_corner'];cells_passed=sum(c['passed'] for c in core_summary);cells_required=2 if allow_fixture_source else 12
 primary={'axes':axes,'combined':combined,'body_x_lower_safeguard':{'value':3.82,'axes':lower_axes,'passed':all(x['passed'] for x in lower_axes.values())},'core_cells_passed':cells_passed,'core_cells_total':len(core_summary),'core_cells_required':cells_required,'passed':all(x['passed'] for x in axes.values()) and combined['normal']<combined['zero'] and all(combined['normal']<combined[k] for k in ('shuffled','static','closed')) and all(x['passed'] for x in lower_axes.values()) and cells_passed>=cells_required}
 x_summary=[]
 for x in X_VALUES:
  rs=[r for r in records if r['view']['body_x']==x]
  if not rs:continue
  x_summary.append({'body_x':x,'cases':len(rs),'normal':pooled(rs,'normal'),'zero':pooled(rs,'zero'),'axes':{a:{'normal':pooled(rs,'normal',a),'zero':pooled(rs,'zero',a),'wins':sum(r['normal']['axis_rmse_rad'][a]<r['zero']['axis_rmse_rad'][a] for r in rs)} for a in AXES}})
 report={'schema':'frozen-lower-bodyx-stress-map-result-v1','status':'fixture_completed' if allow_fixture_source else 'completed','protocol':protocol,'primary':primary,'x_summary':x_summary,'cells':cell_summaries,'exact_failed_probes':probe_records,'records':records,'limitations':['Frozen read-only stress map; no retraining or model selection.','Exact failed-motion probes are diagnostic and excluded from primary.','Body-X sweep maps one synthetic geometry family, not natural vision.','Replay reconstructs observed action; contacts and actuator dynamics are not evaluated.']};save_json(temp/'summary.json',report)
 with (temp/'stress_cells.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['cell_id','name','kind','body_x','side','z','y','normal','zero','passed']);w.writerows([[c['cell_id'],c['name'],c['kind'],c['view']['body_x'],c['view']['camera_side'],c['view']['camera_z'],c['view']['body_y'],c['normal'],c['zero'],c['passed']] for c in cell_summaries])
 with (temp/'autonomous_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['cell_id','cell_name','test_id','time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'autonomous_{a}_rad' for a in AXES]]);w.writerows(rows)
 (temp/'ИТОГ.txt').write_text('\n'.join(['СЕРИЯ 84: FROZEN LOWER-BODY-X STRESS MAP',f'Primary: {"ВЫПОЛНЕН" if primary["passed"] else "НЕ ВЫПОЛНЕН"}.',f'Core cells passed: {cells_passed}/{len(core_summary)}.',f'Core normal/zero: {combined["normal"]:.6f}/{combined["zero"]:.6f}.',f'Body X 3,82 safeguard: {"ВЫПОЛНЕН" if primary["body_x_lower_safeguard"]["passed"] else "НЕ ВЫПОЛНЕН"}.',f'Exact source probes reproduced: {len(probe_records)}/{len(available)}.','Модель серии 83 не переобучалась.',*report['limitations']])+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(canonical(protocol).encode()),'files':output_manifest(temp)});temp.rename(folder/'result')
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
  source=filedialog.askdirectory(title='Выберите завершённую серию 83 fixed_fov_autonomous_grooming_eight_hour_...',initialdir=str(SOURCE_ROOT.resolve()) if SOURCE_ROOT.exists() else str(Path.cwd()),parent=root)
  if not source:return
  messagebox.showinfo('Frozen series 84',f'Модель не переобучается. Новые motions 281–286 проверяются на {len(grid())} cells; exact failed probes серии83 воспроизводятся отдельно.',parent=root);return run(source)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--allow-fixture-source',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:return choose()
 if not a.source:p.error('Нужен --source или --choose.')
 return run(a.source,a.output_root,a.allow_fixture_source)
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА СЕРИИ 84: {type(exc).__name__}: {exc}\nFrozen source не изменялась.',file=sys.stderr,flush=True);sys.exit(1)
