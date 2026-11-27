#!/usr/bin/env python3
"""Series 81: bounded raw-vs-gated-multiscale representation ablation; not a long study."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,itertools,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np
from PIL import Image

HERE=Path(__file__).resolve().parent
RUNNER78=HERE/'78_eight_hour_view_robust_autonomous_grooming.py';RUNNER78_SHA='886a2683073b0d8322cf195c88d6904424c8578a52c566420fe4da5684216caa'
ROOT=Path('workspace/runs/ideas/i-observational/multiscale-gated-view-prototype')
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal');OUTER=('left_proximal','left_distal','right_proximal','right_distal');MIDDLE=('left_middle','right_middle')
LIMITS={'fov_deg':(30.,70.),'camera_side':(.14,.42),'camera_z':(.36,.56),'body_x':(3.82,4.18),'body_y':(-.32,.32)}
MATCHED={'fov_deg':35.,'camera_side':.20,'camera_z':.42,'body_x':4.,'body_y':0.}
TRAIN_EPISODES=320;EVAL_MOTIONS=6;FOREGROUND_THRESHOLD=105;PADDING=2

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}
def load78():
 if file_sha(RUNNER78)!=RUNNER78_SHA:raise ValueError('Закреплённый runner серии 78 изменился.')
 s=importlib.util.spec_from_file_location('canonical80_base',RUNNER78);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def corners(parity):
 out=[]
 for bits in itertools.product((0,1),repeat=5):
  if sum(bits)%2!=parity:continue
  out.append({'corner_bits':list(bits),'view':{k:LIMITS[k][b] for k,b in zip(LIMITS,bits)}})
 return out

def motion(seed,ident,count):
 rng=np.random.default_rng(np.random.SeedSequence([seed,ident]));t=np.arange(51,dtype=float)/25;knots=np.linspace(0,2,count);values=rng.integers(-55,56,size=(count,6)).astype(float)
 values[:,3]=np.clip(-values[:,0]+np.rint(.25*values[:,3]),-55,55);values[:,4]=np.clip(values[:,1]+np.rint(.25*values[:,4]),-55,55);values[:,5]=np.clip(-values[:,2]+np.rint(.25*values[:,5]),-55,55);degrees=np.stack([np.interp(t,knots,values[:,j]) for j in range(6)],axis=1)
 return {'seed':[seed,ident],'id':ident,'family':f'piecewise{count}','motion_sha256':sha(np.asarray(degrees,dtype='<f8').tobytes())},t,degrees

def train_view(ident):
 even=corners(0)
 if ident%2==0:return {'kind':'balanced_even_corner','corner_bits':even[(ident//2)%len(even)]['corner_bits'],**even[(ident//2)%len(even)]['view']}
 rng=np.random.default_rng(np.random.SeedSequence([8003,ident]));return {'kind':'uniform_interior',**{k:float(rng.uniform(*LIMITS[k])) for k in LIMITS}}

def render(scene,commands,view):
 scene.cams=[scene.engine.camera([.9,y,view['camera_z']],[3.25,view['body_y']*.35,.48],48,32,fov=view['fov_deg']) for y in (view['camera_side'],-view['camera_side'])];scene.model.body_pos[scene.body]=[view['body_x'],view['body_y'],float(scene.default_body[2])];return scene.render(commands)

def canonicalize(images):
 """Sequence-level, image-only foreground crop; no camera/body metadata is used."""
 images=np.asarray(images,np.uint8);out=np.empty_like(images);eyes=[]
 for eye in range(images.shape[1]):
  lum=images[:,eye].astype(np.float32).mean(axis=-1);mask=np.any(lum<FOREGROUND_THRESHOLD,axis=0);ys,xs=np.where(mask)
  if len(xs)<12:raise ValueError('CANONICAL GUARD: foreground mask слишком мал.')
  y0=max(0,int(ys.min())-PADDING);y1=min(images.shape[2],int(ys.max())+PADDING+1);x0=max(0,int(xs.min())-PADDING);x1=min(images.shape[3],int(xs.max())+PADDING+1)
  if y1-y0<4 or x1-x0<4:raise ValueError('CANONICAL GUARD: crop вырожден.')
  for i in range(len(images)):out[i,eye]=np.asarray(Image.fromarray(images[i,eye,y0:y1,x0:x1]).resize((48,32),Image.Resampling.BILINEAR),dtype=np.uint8)
  eyes.append({'eye':eye,'bbox_xyxy':[x0,y0,x1,y1],'foreground_pixels':int(mask.sum()),'touches_border':bool(x0==0 or y0==0 or x1==48 or y1==32)})
 return out,eyes

def metrics(truth,pred):
 e=np.asarray(pred)-np.asarray(truth);return {'rmse_rad':float(np.sqrt(np.mean(e*e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)}}
def multiscale_features(raw,canonical,eyes):
 """Always preserve raw; canonical eye channels are zeroed when their union crop touches a border."""
 raw=np.asarray(raw,float);gated=np.asarray(canonical,float).copy();valid=np.array([not e['touches_border'] for e in eyes],dtype=float)
 if raw.shape!=gated.shape or raw.ndim!=2 or raw.shape[1]!=576:raise ValueError('Неверная feature history.')
 for history in range(3):
  for eye in range(2):gated[:,history*192+eye*96:history*192+(eye+1)*96]*=valid[eye]
 flags=np.broadcast_to(valid,(len(raw),2))
 return np.concatenate([raw,gated,flags],axis=1)

def fit(xs,ys):
 dim=xs[0].shape[1];n=0;sx=np.zeros(dim);sx2=np.zeros(dim);sy=np.zeros(6);sxy=np.zeros((dim,6));sxx=np.zeros((dim,dim))
 for x,y in zip(xs,ys):
  if x.shape[1]!=dim or y.shape!=(len(x),6):raise ValueError('Неверная training batch.')
  n+=len(x);sx+=x.sum(0);sx2+=(x*x).sum(0);sy+=y.sum(0);sxy+=x.T@y;sxx+=x.T@x
 mean=sx/n;scale=np.sqrt(np.maximum(sx2/n-mean*mean,0));scale[scale<1e-6]=1.;intercept=sy/n;cov=(sxx/n-np.outer(mean,mean))/np.outer(scale,scale);rhs=(sxy/n-np.outer(mean,intercept))/scale[:,None];weights=np.linalg.solve(cov+np.eye(dim),rhs)
 if any(not np.isfinite(a).all() for a in (mean,scale,intercept,weights)):raise ValueError('Модель содержит неконечные значения.')
 return {'mean':mean,'scale':scale,'intercept':intercept,'weights':weights,'samples':n,'feature_dim':dim}
def predict(model,x):return np.clip((x-model['mean'])/model['scale']@model['weights']+model['intercept'],-np.pi*55/180,np.pi*55/180)
def pooled(records,key,axis=None):
 vals=[r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad'] for r in records];return float(np.sqrt(np.mean(np.square(vals))))

def run(output_root=ROOT,fixture=False):
 m=load78();proto,ev,pre,stim,ck,base,large=m.dependencies();episodes=8 if fixture else TRAIN_EPISODES;eval_motions=2 if fixture else EVAL_MOTIONS
 output_root=Path(output_root);output_root.mkdir(parents=True,exist_ok=True);folder=output_root/('multiscale_gated_prototype_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result.tmp';temp.mkdir();scene=m.VisibleForelegGroomingScene(proto.load('multiscale81_engine','38_two_flies_observation.py'))
 protocol={'schema':'multiscale-gated-view-prototype-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner78_sha256':RUNNER78_SHA,'mode':'fixture' if fixture else 'prototype','training_episodes':episodes,'training_motion_seed':8001,'training_view_seed':8003,'training_views':'50% balanced even-parity core corners; 50% continuous uniform interior','evaluation_motion_seed':8002,'evaluation_motions':eval_motions,'evaluation_views':'16 held-out odd-parity core corners','representation':{'raw_features':576,'gated_canonical_features':576,'border_valid_flags':2,'total_features':1154,'raw_always_preserved':True},'canonicalization':{'uses_metadata':False,'sequence_union_foreground_threshold':FOREGROUND_THRESHOLD,'padding_px':PADDING,'resize':[48,32],'interpolation':'bilinear','gate':'canonical eye features zeroed when union foreground crop touches any image border'},'same_stream_raw_vs_multiscale':True,'go_rule':'each outer axis multiscale pooled below raw and zero with >=60% case wins; middle multiscale below zero and no more than 10% worse raw; combined multiscale below raw/zero; FOV30 and FOV70 combined each no worse raw; >=12/16 held corners improve every outer axis','scientific_result':False};save_json(folder/'protocol.json',protocol)
 raw_x=[];multiscale_x=[];targets=[];train_diag=[]
 for ident in range(episodes):
  spec,t,degrees=motion(8001,ident,5 if ident%2==0 else 9);view=train_view(ident);images=render(scene,degrees*np.pi/180,view);canon,diag=canonicalize(images);rx=ev.feature_history(images);cx=ev.feature_history(canon);raw_x.append(rx);multiscale_x.append(multiscale_features(rx,cx,diag));targets.append(degrees[2:]*np.pi/180);train_diag.append({'id':ident,'motion':spec,'view':view,'raw_rgb_sha256':sha(images.tobytes()),'canonical_rgb_sha256':sha(canon.tobytes()),'canonical_eyes':diag});print(f'Prototype training {ident+1}/{episodes}.',flush=True)
 raw_model=fit(raw_x,targets);multiscale_model=fit(multiscale_x,targets);np.savez_compressed(temp/'model_raw.npz',**raw_model);np.savez_compressed(temp/'model_multiscale.npz',**multiscale_model)
 records=[];rows=[];feature_pairs=[];held=corners(1)
 for mid in range(eval_motions):
  spec,t,degrees=motion(8002,181+mid,5 if mid<eval_motions//2 else 9);truth=degrees[2:]*np.pi/180;matched_images=render(scene,degrees*np.pi/180,MATCHED);matched_canon,_=canonicalize(matched_images);matched_raw_features=ev.feature_history(matched_images);matched_canon_features=ev.feature_history(matched_canon)
  for cid,cell in enumerate(held,1):
   images=render(scene,degrees*np.pi/180,cell['view']);canon,diag=canonicalize(images);rx=ev.feature_history(images);cx=ev.feature_history(canon);mx=multiscale_features(rx,cx,diag);rp=predict(raw_model,rx);mp=predict(multiscale_model,mx);rec={'motion_id':181+mid,'motion':spec,'cell_id':cid,'corner_bits':cell['corner_bits'],'view':cell['view'],'raw':metrics(truth,rp),'multiscale':metrics(truth,mp),'zero':metrics(truth,np.zeros_like(truth)),'raw_feature_distance_to_matched':float(np.sqrt(np.mean((rx-matched_raw_features)**2))),'canonical_feature_distance_to_matched':float(np.sqrt(np.mean((cx-matched_canon_features)**2))),'valid_canonical_eyes':sum(not e['touches_border'] for e in diag),'raw_unique_frames':len({x.tobytes() for x in images}),'canonical_unique_frames':len({x.tobytes() for x in canon}),'canonical_eyes':diag};records.append(rec);feature_pairs.append((rec['raw_feature_distance_to_matched'],rec['canonical_feature_distance_to_matched']))
   rows.extend([[cid,181+mid,float(tv),*map(float,y),*map(float,a),*map(float,b)] for tv,y,a,b in zip(t[2:],truth,rp,mp)])
  print(f'Prototype evaluation motion {mid+1}/{eval_motions}.',flush=True)
 axes={};cases=len(records)
 for a in AXES:
  raw=pooled(records,'raw',a);multi=pooled(records,'multiscale',a);zero=pooled(records,'zero',a);wins=sum(r['multiscale']['axis_rmse_rad'][a]<r['raw']['axis_rmse_rad'][a] for r in records);passed=(multi<raw and multi<zero and wins>=.60*cases) if a in OUTER else (multi<zero and multi<=1.10*raw);axes[a]={'raw':raw,'multiscale':multi,'zero':zero,'wins_vs_raw':wins,'cases':cases,'passed':passed}
 cell_results=[]
 for cid,cell in enumerate(held,1):
  rs=[r for r in records if r['cell_id']==cid];outer={a:pooled(rs,'multiscale',a)<pooled(rs,'raw',a) for a in OUTER};cell_results.append({'cell_id':cid,'corner_bits':cell['corner_bits'],'view':cell['view'],'outer_improved':outer,'all_outer_improved':all(outer.values())})
 combined={k:pooled(records,k) for k in ('raw','multiscale','zero')};fd={'raw':float(np.mean([x for x,_ in feature_pairs])),'canonical':float(np.mean([y for _,y in feature_pairs]))};fov_safeguards={}
 for fov in (30.,70.):
  rs=[r for r in records if r['view']['fov_deg']==fov];fov_safeguards[str(int(fov))]={'raw':pooled(rs,'raw'),'multiscale':pooled(rs,'multiscale'),'passed':pooled(rs,'multiscale')<=pooled(rs,'raw')+1e-12}
 cells_pass=sum(c['all_outer_improved'] for c in cell_results);go=all(x['passed'] for x in axes.values()) and combined['multiscale']<combined['raw'] and combined['multiscale']<combined['zero'] and all(x['passed'] for x in fov_safeguards.values()) and cells_pass>=12
 report={'schema':'multiscale-gated-view-prototype-result-v1','status':'fixture_completed' if fixture else 'completed','protocol':protocol,'go_for_long_training':go,'axes':axes,'combined':combined,'fov_safeguards':fov_safeguards,'feature_view_distance_diagnostic':fd,'held_corners_outer_improved':cells_pass,'held_corners_total':len(held),'training_diagnostics':train_diag,'cell_results':cell_results,'records':records,'limitations':['Short supervised representation ablation, not a scientific long-run result.','Raw features are always preserved; canonical eye features are gated only by image-derived border validity.','Raw and multiscale models use the same balanced stream, isolating the added representation.','No autonomous replay, contacts, actuators, biological brain or mirror-neuron claim.']};save_json(temp/'summary.json',report)
 with (temp/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['cell_id','motion_id','time_s',*[f'teacher_{a}' for a in AXES],*[f'raw_{a}' for a in AXES],*[f'multiscale_{a}' for a in AXES]]);w.writerows(rows)
 (temp/'ИТОГ.txt').write_text('\n'.join(['СЕРИЯ 81: RAW + GATED CANONICAL MULTISCALE PROTOTYPE',f'Режим: {report["status"]}.',f'Go for long training: {"ДА" if go else "НЕТ"}.',f'Combined raw/multiscale/zero: {combined["raw"]:.6f}/{combined["multiscale"]:.6f}/{combined["zero"]:.6f}.',f'FOV30 raw/multiscale: {fov_safeguards["30"]["raw"]:.6f}/{fov_safeguards["30"]["multiscale"]:.6f}.',f'FOV70 raw/multiscale: {fov_safeguards["70"]["raw"]:.6f}/{fov_safeguards["70"]["multiscale"]:.6f}.',f'Held corners all outer improved: {cells_pass}/{len(held)}.',*report['limitations']])+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(json.dumps(protocol,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),'files':output_manifest(temp)});temp.rename(folder/'result')
 if os.name=='nt':
  try:os.startfile(str(folder/'result'))
  except OSError:pass
 print('Готово:',folder/'result');return folder

def choose():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
 try:
  if not messagebox.askokcancel('Серия 81','Короткий raw-vs-gated-multiscale prototype без восьмичасового расчёта. Запустить?',parent=root):return
  return run()
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:return choose()
 return run(a.output_root,a.fixture)
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА СЕРИИ 81: {type(exc).__name__}: {exc}',file=sys.stderr,flush=True);sys.exit(1)
