#!/usr/bin/env python3
"""Series 82: short 48x32 level vs 96x64 level+edge distal-resolution ablation."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,itertools,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent;RUNNER78=HERE/'78_eight_hour_view_robust_autonomous_grooming.py';RUNNER78_SHA='886a2683073b0d8322cf195c88d6904424c8578a52c566420fe4da5684216caa'
ROOT=Path('workspace/runs/ideas/i-observational/high-resolution-distal-prototype')
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal');DISTAL=('left_distal','right_distal');SAFE=('left_proximal','left_middle','right_proximal','right_middle')
LIMITS={'fov_deg':(30.,70.),'camera_side':(.14,.42),'camera_z':(.36,.56),'body_x':(3.82,4.18),'body_y':(-.32,.32)};MATCHED={'fov_deg':35.,'camera_side':.20,'camera_z':.42,'body_x':4.,'body_y':0.}
TRAIN_EPISODES=320;EVAL_MOTIONS=6

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}
def load78():
 if file_sha(RUNNER78)!=RUNNER78_SHA:raise ValueError('Закреплённый runner серии 78 изменился.')
 s=importlib.util.spec_from_file_location('highres82_base',RUNNER78);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def corners(parity):
 return [{'corner_bits':list(bits),'view':{k:LIMITS[k][b] for k,b in zip(LIMITS,bits)}} for bits in itertools.product((0,1),repeat=5) if sum(bits)%2==parity]
def motion(seed,ident,count):
 rng=np.random.default_rng(np.random.SeedSequence([seed,ident]));t=np.arange(51,dtype=float)/25;knots=np.linspace(0,2,count);v=rng.integers(-55,56,size=(count,6)).astype(float);v[:,3]=np.clip(-v[:,0]+np.rint(.25*v[:,3]),-55,55);v[:,4]=np.clip(v[:,1]+np.rint(.25*v[:,4]),-55,55);v[:,5]=np.clip(-v[:,2]+np.rint(.25*v[:,5]),-55,55);deg=np.stack([np.interp(t,knots,v[:,j]) for j in range(6)],1);return {'seed':[seed,ident],'id':ident,'family':f'piecewise{count}','motion_sha256':sha(np.asarray(deg,dtype='<f8').tobytes())},t,deg
def train_view(ident):
 even=corners(0)
 if ident%2==0:return {'kind':'balanced_even_corner','corner_bits':even[(ident//2)%16]['corner_bits'],**even[(ident//2)%16]['view']}
 rng=np.random.default_rng(np.random.SeedSequence([8203,ident]));return {'kind':'uniform_interior',**{k:float(rng.uniform(*LIMITS[k])) for k in LIMITS}}
def render(scene,commands,view,width,height):
 scene.cams=[scene.engine.camera([.9,y,view['camera_z']],[3.25,view['body_y']*.35,.48],width,height,fov=view['fov_deg']) for y in (view['camera_side'],-view['camera_side'])];scene.model.body_pos[scene.body]=[view['body_x'],view['body_y'],float(scene.default_body[2])];return scene.render(commands)
def highres_features(images):
 im=np.asarray(images,np.float32);lum=im.mean(-1)/255.;gx=np.abs(np.diff(lum,axis=3,prepend=lum[:,:,:,:1]));gy=np.abs(np.diff(lum,axis=2,prepend=lum[:,:,:1,:]));edge=np.sqrt(gx*gx+gy*gy)
 def pool(a):
  n,e,h,w=a.shape
  if (h,w)!=(64,96):raise ValueError('High-resolution RGB имеет неверный размер.')
  return a.reshape(n,e,8,8,12,8).mean(axis=(3,5)).reshape(n,-1)
 vec=np.concatenate([pool(lum),pool(edge)],axis=1)
 return np.concatenate([vec[2-i:len(vec)-i] for i in range(3)],axis=1)
def fit(xs,ys):
 dim=xs[0].shape[1];n=0;sx=np.zeros(dim);sx2=np.zeros(dim);sy=np.zeros(6);sxy=np.zeros((dim,6));sxx=np.zeros((dim,dim))
 for x,y in zip(xs,ys):n+=len(x);sx+=x.sum(0);sx2+=(x*x).sum(0);sy+=y.sum(0);sxy+=x.T@y;sxx+=x.T@x
 mean=sx/n;scale=np.sqrt(np.maximum(sx2/n-mean*mean,0));scale[scale<1e-6]=1.;intercept=sy/n;cov=(sxx/n-np.outer(mean,mean))/np.outer(scale,scale);rhs=(sxy/n-np.outer(mean,intercept))/scale[:,None];weights=np.linalg.solve(cov+np.eye(dim),rhs)
 return {'mean':mean,'scale':scale,'intercept':intercept,'weights':weights,'samples':n,'feature_dim':dim}
def predict(model,x):return np.clip((x-model['mean'])/model['scale']@model['weights']+model['intercept'],-np.pi*55/180,np.pi*55/180)
def metrics(y,p):
 e=p-y;return {'rmse_rad':float(np.sqrt(np.mean(e*e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)}}
def pooled(rs,key,axis=None):return float(np.sqrt(np.mean([(r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad'])**2 for r in rs])))

def run(output_root=ROOT,fixture=False):
 m=load78();proto,ev,pre,stim,ck,base,large=m.dependencies();episodes=8 if fixture else TRAIN_EPISODES;eval_motions=2 if fixture else EVAL_MOTIONS;root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('high_resolution_distal_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result.tmp';temp.mkdir();scene=m.VisibleForelegGroomingScene(proto.load('highres82_engine','38_two_flies_observation.py'))
 protocol={'schema':'high-resolution-distal-prototype-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner78_sha256':RUNNER78_SHA,'mode':'fixture' if fixture else 'prototype','training_episodes':episodes,'training_motion_seed':8201,'training_view_seed':8203,'training_views':'50% balanced even-parity core corners; 50% uniform interior','evaluation_motion_seed':8202,'evaluation_motions':eval_motions,'evaluation_views':'16 held odd-parity core corners','baseline':{'resolution':[48,32],'features':576,'type':'level history'},'high_resolution':{'resolution':[96,64],'features':1152,'type':'coarse level plus high-resolution gradient-energy history'},'same_stream':True,'go_rule':'both distal highres below standard and zero with >=60% case wins; safe axes highres below zero and <=5% worse standard; combined highres below standard/zero; FOV30 and FOV70 <=2% worse standard; >=12/16 corners improve both distal','scientific_result':False};save_json(folder/'protocol.json',protocol)
 standard_x=[];high_x=[];targets=[];training=[]
 for ident in range(episodes):
  spec,t,deg=motion(8201,ident,5 if ident%2==0 else 9);view=train_view(ident);lo=render(scene,deg*np.pi/180,view,48,32);hi=render(scene,deg*np.pi/180,view,96,64);lx=ev.feature_history(lo);hx=highres_features(hi);standard_x.append(lx);high_x.append(hx);targets.append(deg[2:]*np.pi/180);training.append({'id':ident,'motion':spec,'view':view,'standard_rgb_sha256':sha(lo.tobytes()),'highres_rgb_sha256':sha(hi.tobytes()),'standard_unique_frames':len({x.tobytes() for x in lo}),'highres_unique_frames':len({x.tobytes() for x in hi}),'standard_feature_max_std':float(np.max(np.std(lx,0))),'highres_feature_max_std':float(np.max(np.std(hx,0)))});print(f'High-res training {ident+1}/{episodes}.',flush=True)
 standard=fit(standard_x,targets);high=fit(high_x,targets);np.savez_compressed(temp/'model_standard.npz',**standard);np.savez_compressed(temp/'model_highres.npz',**high)
 records=[];rows=[];held=corners(1)
 for mid in range(eval_motions):
  spec,t,deg=motion(8202,201+mid,5 if mid<eval_motions//2 else 9);truth=deg[2:]*np.pi/180
  for cid,c in enumerate(held,1):
   lo=render(scene,deg*np.pi/180,c['view'],48,32);hi=render(scene,deg*np.pi/180,c['view'],96,64);sp=predict(standard,ev.feature_history(lo));hp=predict(high,highres_features(hi));rec={'motion_id':201+mid,'motion':spec,'cell_id':cid,'corner_bits':c['corner_bits'],'view':c['view'],'standard':metrics(truth,sp),'highres':metrics(truth,hp),'zero':metrics(truth,np.zeros_like(truth)),'standard_unique_frames':len({x.tobytes() for x in lo}),'highres_unique_frames':len({x.tobytes() for x in hi})};records.append(rec);rows.extend([[cid,201+mid,float(tv),*map(float,y),*map(float,a),*map(float,b)] for tv,y,a,b in zip(t[2:],truth,sp,hp)])
  print(f'High-res evaluation {mid+1}/{eval_motions}.',flush=True)
 cases=len(records);axes={}
 for a in AXES:
  st=pooled(records,'standard',a);hr=pooled(records,'highres',a);z=pooled(records,'zero',a);wins=sum(r['highres']['axis_rmse_rad'][a]<r['standard']['axis_rmse_rad'][a] for r in records);passed=(hr<st and hr<z and wins>=.60*cases) if a in DISTAL else (hr<z and hr<=1.05*st);axes[a]={'standard':st,'highres':hr,'zero':z,'wins_vs_standard':wins,'cases':cases,'passed':passed}
 cells=[]
 for cid,c in enumerate(held,1):
  rs=[r for r in records if r['cell_id']==cid];di={a:pooled(rs,'highres',a)<pooled(rs,'standard',a) for a in DISTAL};cells.append({'cell_id':cid,'corner_bits':c['corner_bits'],'view':c['view'],'distal_improved':di,'both_distal_improved':all(di.values())})
 combined={k:pooled(records,k) for k in ('standard','highres','zero')};fov={}
 for value in (30.,70.):
  rs=[r for r in records if r['view']['fov_deg']==value];st=pooled(rs,'standard');hr=pooled(rs,'highres');fov[str(int(value))]={'standard':st,'highres':hr,'passed':hr<=1.02*st}
 cell_pass=sum(c['both_distal_improved'] for c in cells);go=all(v['passed'] for v in axes.values()) and combined['highres']<combined['standard'] and combined['highres']<combined['zero'] and all(v['passed'] for v in fov.values()) and cell_pass>=12
 report={'schema':'high-resolution-distal-prototype-result-v1','status':'fixture_completed' if fixture else 'completed','protocol':protocol,'go_for_long_training':go,'axes':axes,'combined':combined,'fov_safeguards':fov,'held_corners_both_distal_improved':cell_pass,'held_corners_total':16,'training_diagnostics':training,'cell_results':cells,'records':records,'limitations':['Short supervised resolution ablation, not a scientific long-run result.','High-resolution representation changes both sensor sampling and feature type by adding gradient energy.','Same stream isolates the complete high-resolution representation package, not each component.','No replay, contacts, actuators, biological brain or mirror-neuron claim.']};save_json(temp/'summary.json',report)
 with (temp/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['cell_id','motion_id','time_s',*[f'teacher_{a}' for a in AXES],*[f'standard_{a}' for a in AXES],*[f'highres_{a}' for a in AXES]]);w.writerows(rows)
 (temp/'ИТОГ.txt').write_text('\n'.join(['СЕРИЯ 82: HIGH-RESOLUTION DISTAL PROTOTYPE',f'Режим: {report["status"]}.',f'Go for long training: {"ДА" if go else "НЕТ"}.',f'Combined standard/highres/zero: {combined["standard"]:.6f}/{combined["highres"]:.6f}/{combined["zero"]:.6f}.',f'Distal L standard/highres: {axes["left_distal"]["standard"]:.6f}/{axes["left_distal"]["highres"]:.6f}.',f'Distal R standard/highres: {axes["right_distal"]["standard"]:.6f}/{axes["right_distal"]["highres"]:.6f}.',f'Held corners both distal improved: {cell_pass}/16.',*report['limitations']])+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(json.dumps(protocol,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),'files':output_manifest(temp)});temp.rename(folder/'result')
 if os.name=='nt':
  try:os.startfile(str(folder/'result'))
  except OSError:pass
 print('Готово:',folder/'result');return folder

def choose():
 import tkinter as tk
 from tkinter import messagebox
 r=tk.Tk();r.withdraw();r.attributes('-topmost',True)
 try:
  if messagebox.askokcancel('Серия 82','Короткий 48×32 против 96×64 distal prototype. Запустить?',parent=r):return run()
 finally:r.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true',help=argparse.SUPPRESS);a=p.parse_args();return choose() if a.choose else run(a.output_root,a.fixture)
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА СЕРИИ 82: {type(exc).__name__}: {exc}',file=sys.stderr,flush=True);sys.exit(1)
