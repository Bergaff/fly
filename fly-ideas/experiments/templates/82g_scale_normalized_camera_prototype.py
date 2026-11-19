#!/usr/bin/env python3
"""Series 82G: short FOV-normalized and tracked-camera geometry prototype."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,itertools,json,os,sys,uuid
from datetime import datetime,timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER82=HERE/'82_high_resolution_distal_prototype.py'
RUNNER82_SHA='175b8ee1ef63a2e045fb62bff84bdfc345c05d8285f170397e033424ba3d96b1'
ROOT=Path('workspace/runs/ideas/i-observational/scale-normalized-camera-prototype')
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
DISTAL=('left_distal','right_distal');SAFE=('left_proximal','left_middle','right_proximal','right_middle')
REPS=('variable_edge','fov35_edge','tracked35_edge');TRAIN_EPISODES=320;EVAL_MOTIONS=6;FIXED_FOV=35.;PERTURB_DEG=10.
LIMITS={'fov_deg':(30.,70.),'camera_side':(.14,.42),'camera_z':(.36,.56),'body_x':(3.82,4.18),'body_y':(-.32,.32)}

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}
def load82():
 if file_sha(RUNNER82)!=RUNNER82_SHA:raise ValueError('Закреплённый runner серии 82 изменился.')
 s=importlib.util.spec_from_file_location('geometry82g_base',RUNNER82);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def corners(parity):return [{'corner_bits':list(bits),'view':{k:LIMITS[k][b] for k,b in zip(LIMITS,bits)}} for bits in itertools.product((0,1),repeat=5) if sum(bits)%2==parity]
def train_view(ident):
 even=corners(0)
 if ident%2==0:return {'kind':'balanced_even_corner','corner_bits':even[(ident//2)%16]['corner_bits'],**even[(ident//2)%16]['view']}
 rng=np.random.default_rng(np.random.SeedSequence([8243,ident]));return {'kind':'uniform_interior',**{k:float(rng.uniform(*LIMITS[k])) for k in LIMITS}}
def render_variable(base,scene,commands,view):return base.render(scene,commands,view,96,64)
def render_fov35(base,scene,commands,view):
 fixed=dict(view);fixed['fov_deg']=FIXED_FOV;return base.render(scene,commands,fixed,96,64)
def render_tracked(scene,commands,view):
 dx=view['body_x']-4.;dy=view['body_y'];scene.cams=[scene.engine.camera([.9+dx,dy+y,.42],[3.25+dx,dy,.48],96,64,fov=FIXED_FOV) for y in (.20,-.20)];scene.model.body_pos[scene.body]=[view['body_x'],dy,float(scene.default_body[2])];return scene.render(commands)
def edge_features(images):
 im=np.asarray(images,np.float32);lum=im.mean(-1)/255.;gx=np.abs(np.diff(lum,axis=3,prepend=lum[:,:,:,:1]));gy=np.abs(np.diff(lum,axis=2,prepend=lum[:,:,:1,:]));edge=np.sqrt(gx*gx+gy*gy);n,e,h,w=edge.shape
 if (h,w)!=(64,96):raise ValueError('RGB имеет неверный размер для geometry prototype.')
 vec=edge.reshape(n,e,8,8,12,8).mean(axis=(3,5)).reshape(n,-1)
 return np.concatenate([vec[2-i:n-i] for i in range(3)],axis=1)
def render_all(base,scene,commands,view):return {'variable_edge':render_variable(base,scene,commands,view),'fov35_edge':render_fov35(base,scene,commands,view),'tracked35_edge':render_tracked(scene,commands,view)}
def metrics(base,y,p):return base.metrics(y,p)
def pooled(records,key,axis=None):return float(np.sqrt(np.mean([(r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad'])**2 for r in records])))

def visibility_probe(base,scene,held,fixture=False):
 _,_,deg=base.motion(8244,399,9);commands=deg*np.pi/180;rows=[];probe=held[:2] if fixture else held
 for cid,c in enumerate(probe,1):
  original=render_all(base,scene,commands,c['view'])
  original_features={k:edge_features(v) for k,v in original.items()}
  for axis,index in (('left_distal',2),('right_distal',5)):
   moved=commands.copy();moved[:,index]=np.clip(moved[:,index]+np.deg2rad(PERTURB_DEG),-np.deg2rad(55),np.deg2rad(55));changed=render_all(base,scene,moved,c['view']);geometry={}
   for name in REPS:
    counts=np.count_nonzero(changed[name]!=original[name],axis=(1,2,3,4));delta=float(np.sqrt(np.mean((edge_features(changed[name])-original_features[name])**2)));geometry[name]={'median_changed_rgb':float(np.median(counts)),'feature_delta_rms':delta,'visible':bool(float(np.median(counts))>=40 and delta>=1e-4)}
   rows.append({'cell_id':cid,'corner_bits':c['corner_bits'],'view':c['view'],'axis':axis,'perturb_deg':PERTURB_DEG,'geometry':geometry})
 return rows

def run(output_root=ROOT,fixture=False):
 b=load82();m=b.load78();proto,*_=m.dependencies();episodes=8 if fixture else TRAIN_EPISODES;eval_motions=2 if fixture else EVAL_MOTIONS;root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('scale_normalized_geometry_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result.tmp';temp.mkdir();scene=m.VisibleForelegGroomingScene(proto.load('geometry82g_engine','38_two_flies_observation.py'))
 protocol={'schema':'scale-normalized-camera-prototype-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner82_sha256':RUNNER82_SHA,'mode':'fixture' if fixture else 'prototype','training_episodes':episodes,'training_motion_seed':8241,'training_view_seed':8243,'evaluation_motion_seed':8242,'evaluation_motion_ids':[241,240+eval_motions],'representations':{'variable_edge':{'resolution':[96,64],'fov':'variable 30-70','features':576},'fov35_edge':{'resolution':[96,64],'fov':35,'other_geometry':'original view','features':576},'tracked35_edge':{'resolution':[96,64],'fov':35,'other_geometry':'body-relative fixed rig','features':576,'diagnostic_only':True}},'same_motion_view_labels':True,'primary_candidate':'fov35_edge','tracked_camera_can_rescue_primary':False,'visibility_guard':'for fov35: median changed RGB96 >=40 and edge delta RMS >=1e-4 in >=12/16 cells per distal axis','go_rule':'fov35 both distal below variable/zero with >=60% wins; safe axes below zero and <=5% worse variable; combined below variable/zero; original FOV30/FOV70 groups <=2% worse variable; >=12/16 corners both distal improve; visibility guard passes','authorizes_series83_only_on_full_fov35_go':True,'scientific_result':False};save_json(folder/'protocol.json',protocol)
 train={n:[] for n in REPS};targets=[];training=[]
 for ident in range(episodes):
  spec,t,deg=b.motion(8241,ident,5 if ident%2==0 else 9);view=train_view(ident);images=render_all(b,scene,deg*np.pi/180,view);features={n:edge_features(images[n]) for n in REPS}
  for n in REPS:train[n].append(features[n])
  targets.append(deg[2:]*np.pi/180);training.append({'id':ident,'motion':spec,'view':view,'rgb_sha256':{n:sha(images[n].tobytes()) for n in REPS},'unique_frames':{n:len({x.tobytes() for x in images[n]}) for n in REPS},'feature_max_std':{n:float(np.max(np.std(features[n],0))) for n in REPS}});print(f'Geometry training {ident+1}/{episodes}.',flush=True)
 models={n:b.fit(train[n],targets) for n in REPS}
 for n,model in models.items():np.savez_compressed(temp/f'model_{n}.npz',**model)
 records=[];rows=[];held=corners(1)
 for mid in range(eval_motions):
  motion_id=241+mid;spec,t,deg=b.motion(8242,motion_id,5 if mid<eval_motions//2 else 9);truth=deg[2:]*np.pi/180
  for cid,c in enumerate(held,1):
   images=render_all(b,scene,deg*np.pi/180,c['view']);features={n:edge_features(images[n]) for n in REPS};pred={n:b.predict(models[n],features[n]) for n in REPS};rec={'motion_id':motion_id,'motion':spec,'cell_id':cid,'corner_bits':c['corner_bits'],'view':c['view']}
   for n in REPS:rec[n]=metrics(b,truth,pred[n])
   rec['zero']=metrics(b,truth,np.zeros_like(truth));records.append(rec)
   rows.extend([[cid,motion_id,frame,float(tv),*map(float,y),*[float(v) for n in REPS for v in pred[n][frame]]] for frame,(tv,y) in enumerate(zip(t[2:],truth))])
  print(f'Geometry evaluation {mid+1}/{eval_motions}.',flush=True)
 visibility=visibility_probe(b,scene,held,fixture);cases=len(records);axes={}
 for axis in AXES:
  var=pooled(records,'variable_edge',axis);fov=pooled(records,'fov35_edge',axis);tracked=pooled(records,'tracked35_edge',axis);zero=pooled(records,'zero',axis);wins=sum(r['fov35_edge']['axis_rmse_rad'][axis]<r['variable_edge']['axis_rmse_rad'][axis] for r in records);passed=(fov<var and fov<zero and wins>=.60*cases) if axis in DISTAL else (fov<zero and fov<=1.05*var);axes[axis]={'variable_edge':var,'fov35_edge':fov,'tracked35_edge':tracked,'zero':zero,'fov35_wins_vs_variable':wins,'cases':cases,'passed':passed}
 combined={n:pooled(records,n) for n in (*REPS,'zero')};fov_groups={}
 for original_fov in (30,70):
  rs=[r for r in records if r['view']['fov_deg']==original_fov];var=pooled(rs,'variable_edge');fixed=pooled(rs,'fov35_edge');fov_groups[str(original_fov)]={'variable_edge':var,'fov35_edge':fixed,'passed':fixed<=1.02*var}
 cells=[]
 for cid,c in enumerate(held,1):
  rs=[r for r in records if r['cell_id']==cid];di={a:pooled(rs,'fov35_edge',a)<pooled(rs,'variable_edge',a) for a in DISTAL};cells.append({'cell_id':cid,'corner_bits':c['corner_bits'],'view':c['view'],'distal_improved':di,'both_distal_improved':all(di.values())})
 required=2 if fixture else 12;visible={a:sum(x['axis']==a and x['geometry']['fov35_edge']['visible'] for x in visibility) for a in DISTAL};visibility_pass=all(v>=required for v in visible.values());cell_pass=sum(x['both_distal_improved'] for x in cells)
 go=all(v['passed'] for v in axes.values()) and combined['fov35_edge']<combined['variable_edge'] and combined['fov35_edge']<combined['zero'] and all(x['passed'] for x in fov_groups.values()) and cell_pass>=12 and visibility_pass
 report={'schema':'scale-normalized-camera-prototype-result-v1','status':'fixture_completed' if fixture else 'completed','protocol':protocol,'go_for_revised_long_training':go,'axes':axes,'combined':combined,'original_fov_safeguards':fov_groups,'held_corners_both_distal_improved':cell_pass,'held_corners_total':16,'visibility':{'visible_cells_per_axis':visible,'required_per_axis':required,'passed':visibility_pass},'training_diagnostics':training,'visibility_records':visibility,'cell_results':cells,'records':records,'limitations':['Short supervised geometry ablation, not a scientific long-run result.','Fixed-FOV camera changes observation geometry; tracked camera is diagnostic only and cannot rescue primary.','Camera stabilization uses simulator body pose to position the sensor, but the decoder receives pixels only.','No replay, contacts, actuators, biological brain or mirror-neuron claim.']};save_json(temp/'summary.json',report)
 with (temp/'predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['cell_id','motion_id','frame','time_s',*[f'teacher_{a}' for a in AXES],*[f'{n}_{a}' for n in REPS for a in AXES]]);w.writerows(rows)
 lines=['СЕРИЯ 82G: SCALE-NORMALIZED CAMERA PROTOTYPE',f'Режим: {report["status"]}.',f'Go for revised long training: {"ДА" if go else "НЕТ"}.',f'Combined variable/fov35/tracked/zero: {combined["variable_edge"]:.6f}/{combined["fov35_edge"]:.6f}/{combined["tracked35_edge"]:.6f}/{combined["zero"]:.6f}.',f'Distal L variable/fov35/zero: {axes["left_distal"]["variable_edge"]:.6f}/{axes["left_distal"]["fov35_edge"]:.6f}/{axes["left_distal"]["zero"]:.6f}.',f'Distal R variable/fov35/zero: {axes["right_distal"]["variable_edge"]:.6f}/{axes["right_distal"]["fov35_edge"]:.6f}/{axes["right_distal"]["zero"]:.6f}.',f'Held corners both distal improved: {cell_pass}/16.',f'FOV35 visibility L/R: {visible["left_distal"]}/{visible["right_distal"]}.']
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
  if messagebox.askokcancel('Серия 82G','Запустить короткий fixed-FOV geometry prototype?',parent=r):return run()
 finally:r.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true',help=argparse.SUPPRESS);a=p.parse_args();return choose() if a.choose else run(a.output_root,a.fixture)
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА СЕРИИ 82G: {type(exc).__name__}: {exc}',file=sys.stderr,flush=True);sys.exit(1)
