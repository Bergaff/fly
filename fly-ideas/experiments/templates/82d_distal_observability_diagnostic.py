#!/usr/bin/env python3
"""Series 82D: short distal observability and representation-component diagnostic."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER82=HERE/'82_high_resolution_distal_prototype.py'
RUNNER82_SHA='175b8ee1ef63a2e045fb62bff84bdfc345c05d8285f170397e033424ba3d96b1'
ROOT=Path('workspace/runs/ideas/i-observational/distal-observability-diagnostic')
REPS=('standard48_level','high96_level','high96_edge','high96_level_edge')
DISTAL=('left_distal','right_distal');DISTAL_INDEX={'left_distal':2,'right_distal':5}
TRAIN_EPISODES=320;EVAL_MOTIONS=6;PERTURB_DEG=10.

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}
def load82():
 if file_sha(RUNNER82)!=RUNNER82_SHA:raise ValueError('Закреплённый runner серии 82 изменился.')
 s=importlib.util.spec_from_file_location('distal82d_base',RUNNER82);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def high_components(images):
 im=np.asarray(images,np.float32);lum=im.mean(-1)/255.;gx=np.abs(np.diff(lum,axis=3,prepend=lum[:,:,:,:1]));gy=np.abs(np.diff(lum,axis=2,prepend=lum[:,:,:1,:]));edge=np.sqrt(gx*gx+gy*gy)
 def pool(a):
  n,e,h,w=a.shape
  if (h,w)!=(64,96):raise ValueError('High-resolution RGB имеет неверный размер.')
  return a.reshape(n,e,8,8,12,8).mean(axis=(3,5)).reshape(n,-1)
 def history(v):return np.concatenate([v[2-i:len(v)-i] for i in range(3)],axis=1)
 return history(pool(lum)),history(pool(edge))

def representation_features(base,lo,hi):
 level,edge=high_components(hi)
 return {'standard48_level':base.ev.feature_history(lo),'high96_level':level,'high96_edge':edge,'high96_level_edge':np.concatenate([level.reshape(len(level),3,192),edge.reshape(len(edge),3,192)],axis=2).reshape(len(level),1152)}

def model_metrics(base,truth,pred):
 result=base.metrics(truth,pred)
 for axis,index in DISTAL_INDEX.items():
  y=truth[:,index];p=pred[:,index];mask=np.abs(y)>=np.deg2rad(5);den=float(y@y)
  result['axis_rmse_rad'][axis]=float(np.sqrt(np.mean((p-y)**2)))
  result.setdefault('distal_diagnostics',{})[axis]={'gain_through_origin':float((y@p)/den) if den>0 else 0.,'correlation':float(np.corrcoef(y,p)[0,1]) if np.std(y)>0 and np.std(p)>0 else 0.,'mean_bias_rad':float(np.mean(p-y)),'prediction_rms_rad':float(np.sqrt(np.mean(p*p))),'target_rms_rad':float(np.sqrt(np.mean(y*y))),'sign_agreement_over_5deg':float(np.mean(np.sign(p[mask])==np.sign(y[mask]))) if mask.any() else None,'sign_frames_over_5deg':int(mask.sum())}
 return result

def visibility_probe(base,scene,held,fixture=False):
 _,_,deg=base.motion(8224,299,9);commands=deg*np.pi/180;rows=[]
 probe_cells=held[:2] if fixture else held
 for cid,c in enumerate(probe_cells,1):
  lo0=base.render(scene,commands,c['view'],48,32);hi0=base.render(scene,commands,c['view'],96,64);f0=representation_features(base,lo0,hi0)
  for axis,index in DISTAL_INDEX.items():
   moved=commands.copy();moved[:,index]=np.clip(moved[:,index]+np.deg2rad(PERTURB_DEG),-np.deg2rad(55),np.deg2rad(55));lo=base.render(scene,moved,c['view'],48,32);hi=base.render(scene,moved,c['view'],96,64);ff=representation_features(base,lo,hi)
   changed48=np.count_nonzero(lo!=lo0,axis=(1,2,3,4));changed96=np.count_nonzero(hi!=hi0,axis=(1,2,3,4))
   feature_rms={name:float(np.sqrt(np.mean((ff[name]-f0[name])**2))) for name in REPS}
   visible=bool(float(np.median(changed48))>=20 and feature_rms['standard48_level']>=1e-4)
   rows.append({'cell_id':cid,'corner_bits':c['corner_bits'],'view':c['view'],'axis':axis,'perturb_deg':PERTURB_DEG,'median_changed_rgb48':float(np.median(changed48)),'median_changed_rgb96':float(np.median(changed96)),'feature_delta_rms':feature_rms,'visible_standard_guard':visible})
 return rows

def route_report(records,visibility,fixture):
 cases=len(records);models={}
 for name in REPS:
  axes={}
  for axis in DISTAL:
   rmse=float(np.sqrt(np.mean([r[name]['axis_rmse_rad'][axis]**2 for r in records])));zero=float(np.sqrt(np.mean([r['zero']['axis_rmse_rad'][axis]**2 for r in records])));standard=float(np.sqrt(np.mean([r['standard48_level']['axis_rmse_rad'][axis]**2 for r in records])));wins=sum(r[name]['axis_rmse_rad'][axis]<r['standard48_level']['axis_rmse_rad'][axis] for r in records);axes[axis]={'rmse':rmse,'zero':zero,'standard48':standard,'wins_vs_standard48':wins,'cases':cases,'below_zero':rmse<zero}
  models[name]={'axes':axes,'both_distal_below_zero':all(x['below_zero'] for x in axes.values())}
 by_fov={}
 for fov in (30,70):
  cells={x['cell_id'] for x in visibility if int(x['view']['fov_deg'])==fov and x['visible_standard_guard']}
  by_fov[str(fov)]={'visible_cell_axis_pairs':sum(1 for x in visibility if int(x['view']['fov_deg'])==fov and x['visible_standard_guard']),'total_cell_axis_pairs':sum(1 for x in visibility if int(x['view']['fov_deg'])==fov),'cells_with_both_distal_visible':sum(all(any(x['cell_id']==cid and x['axis']==a and x['visible_standard_guard'] for x in visibility) for a in DISTAL) for cid in cells)}
 visible_axes={a:sum(x['axis']==a and x['visible_standard_guard'] for x in visibility) for a in DISTAL};required=2 if fixture else 12;visibility_ok=all(v>=required for v in visible_axes.values())
 candidates=[n for n in REPS[1:] if models[n]['both_distal_below_zero'] and all(models[n]['axes'][a]['wins_vs_standard48']>=.60*cases for a in DISTAL)]
 if not visibility_ok:route='geometry_or_occlusion'
 elif candidates:route='new_representation_prototype'
 else:route='decoder_or_temporal_model'
 return {'models':models,'visibility':{'visible_cells_per_axis':visible_axes,'required_per_axis':required,'passed':visibility_ok,'by_fov':by_fov},'candidate_representations':candidates,'route':route,'authorizes_series83':False}

def run(output_root=ROOT,fixture=False):
 b=load82();m=b.load78();proto,ev,*_=m.dependencies();b.ev=ev;episodes=8 if fixture else TRAIN_EPISODES;eval_motions=2 if fixture else EVAL_MOTIONS;root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('distal_observability_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result.tmp';temp.mkdir();scene=m.VisibleForelegGroomingScene(proto.load('distal82d_engine','38_two_flies_observation.py'))
 protocol={'schema':'distal-observability-diagnostic-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner82_sha256':RUNNER82_SHA,'mode':'fixture' if fixture else 'diagnostic','training_episodes':episodes,'training_motion_seed':8201,'training_view_seed':8203,'evaluation_motion_seed':8222,'evaluation_motion_ids':[221,221+eval_motions-1],'representations':{'standard48_level':576,'high96_level':576,'high96_edge':576,'high96_level_edge':1152},'visibility_probe':{'motion_seed':8224,'motion_id':299,'perturb_deg':PERTURB_DEG,'guard':'median changed RGB48 >=20 and standard feature delta RMS >=1e-4; >=12/16 cells per distal axis'},'routing_rule':'failed visibility -> geometry/occlusion; adequate visibility plus representation both distal<zero and >=60% wins vs standard -> new representation prototype; otherwise decoder/temporal model','authorizes_long_training':False,'scientific_result':False};save_json(folder/'protocol.json',protocol)
 train={name:[] for name in REPS};targets=[];training=[]
 for ident in range(episodes):
  spec,t,deg=b.motion(8201,ident,5 if ident%2==0 else 9);view=b.train_view(ident);lo=b.render(scene,deg*np.pi/180,view,48,32);hi=b.render(scene,deg*np.pi/180,view,96,64);features=representation_features(b,lo,hi)
  for name in REPS:train[name].append(features[name])
  targets.append(deg[2:]*np.pi/180);training.append({'id':ident,'motion':spec,'view':view,'rgb48_sha256':sha(lo.tobytes()),'rgb96_sha256':sha(hi.tobytes()),'unique48':len({x.tobytes() for x in lo}),'unique96':len({x.tobytes() for x in hi}),'feature_max_std':{n:float(np.max(np.std(x,0))) for n,x in features.items()}});print(f'Distal diagnostic training {ident+1}/{episodes}.',flush=True)
 models={name:b.fit(train[name],targets) for name in REPS}
 for name,model in models.items():np.savez_compressed(temp/f'model_{name}.npz',**model)
 held=b.corners(1);records=[];rows=[]
 for mid in range(eval_motions):
  motion_id=221+mid;spec,t,deg=b.motion(8222,motion_id,5 if mid<eval_motions//2 else 9);truth=deg[2:]*np.pi/180
  for cid,c in enumerate(held,1):
   lo=b.render(scene,deg*np.pi/180,c['view'],48,32);hi=b.render(scene,deg*np.pi/180,c['view'],96,64);features=representation_features(b,lo,hi);pred={n:b.predict(models[n],features[n]) for n in REPS};rec={'motion_id':motion_id,'motion':spec,'cell_id':cid,'corner_bits':c['corner_bits'],'view':c['view']}
   for name in REPS:rec[name]=model_metrics(b,truth,pred[name])
   rec['zero']=b.metrics(truth,np.zeros_like(truth));records.append(rec)
   for frame,(tv,y) in enumerate(zip(t[2:],truth)):
    rows.append([cid,motion_id,frame,float(tv),*map(float,y),*[float(v) for n in REPS for v in pred[n][frame]]])
  print(f'Distal diagnostic evaluation {mid+1}/{eval_motions}.',flush=True)
 visibility=visibility_probe(b,scene,held,fixture);routing=route_report(records,visibility,fixture);report={'schema':'distal-observability-diagnostic-result-v1','status':'fixture_completed' if fixture else 'completed','protocol':protocol,'routing':routing,'training_diagnostics':training,'visibility_records':visibility,'records':records,'limitations':['Short supervised engineering diagnostic, not a long-run scientific result.','Representation comparison separates level and edge channels but still uses one linear ridge decoder class.','Visibility perturbation is synthetic +10 degrees and does not prove biological observability.','No replay, contacts, actuators, biological brain or mirror-neuron claim.']};save_json(temp/'summary.json',report)
 with (temp/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['cell_id','motion_id','frame','time_s',*[f'teacher_{a}' for a in b.AXES],*[f'{n}_{a}' for n in REPS for a in b.AXES]]);w.writerows(rows)
 lines=['СЕРИЯ 82D: DISTAL OBSERVABILITY DIAGNOSTIC',f'Режим: {report["status"]}.',f'Маршрут следующего short prototype: {routing["route"]}.','Серия 83 разрешена: НЕТ.',f'Visibility passed: {"ДА" if routing["visibility"]["passed"] else "НЕТ"}.',f'Visible cells L/R: {routing["visibility"]["visible_cells_per_axis"]["left_distal"]}/{routing["visibility"]["visible_cells_per_axis"]["right_distal"]}.',f'Candidate representations: {", ".join(routing["candidate_representations"]) or "нет"}.']
  
 (temp/'ИТОГ.txt').write_text('\n'.join(lines+report['limitations'])+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(json.dumps(protocol,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),'files':output_manifest(temp)});temp.rename(folder/'result')
 if os.name=='nt':
  try:os.startfile(str(folder/'result'))
  except OSError:pass
 print('Готово:',folder/'result');return folder

def choose():
 import tkinter as tk
 from tkinter import messagebox
 r=tk.Tk();r.withdraw();r.attributes('-topmost',True)
 try:
  if messagebox.askokcancel('Серия 82D','Запустить короткую distal visibility и feature-component диагностику?',parent=r):return run()
 finally:r.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true',help=argparse.SUPPRESS);a=p.parse_args();return choose() if a.choose else run(a.output_root,a.fixture)
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА СЕРИИ 82D: {type(exc).__name__}: {exc}',file=sys.stderr,flush=True);sys.exit(1)
