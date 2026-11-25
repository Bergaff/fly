#!/usr/bin/env python3
"""Series103: official FlyGym observer-eye bridge preflight for two bodies."""
from __future__ import annotations
import argparse,hashlib,json,os,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
RESULT102=HERE.parent/'reports'/'frozen89e-flygym-replication-user-result.json';RESULT102_SHA='33795d582e9ac528304018300dc14c67db066d3452e1760df2bb74c9aef9a643'
ROOT=Path('workspace/runs/ideas/i-observational/flygym-interbody-vision-preflight')
DT=.0005;FRAME_DT=.04;FRAMES=49;KP=18.;KD=.18;TORQUE_LIMIT=25.
MAPPED_DOF=('c_thorax-lf_coxa-pitch','lf_coxa-lf_trochanterfemur-pitch','lf_trochanterfemur-lf_tibia-pitch','c_thorax-rf_coxa-pitch','rf_coxa-rf_trochanterfemur-pitch','rf_trochanterfemur-rf_tibia-pitch')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def authorize():
 if sha(RESULT102)!=RESULT102_SHA:raise ValueError('Series102 genuine result изменён.')
 x=json.loads(RESULT102.read_text(encoding='utf8'))
 if x.get('status')!='completed' or x.get('primary',{}).get('passed') is not True or x.get('primary',{}).get('scientific_result') is not False:raise ValueError('Нужен точный Series102 replication pass.')
 return x
def resize_eye_pair(raw):
 raw=np.asarray(raw)
 if raw.ndim!=4 or raw.shape[0]!=2 or raw.shape[-1]!=3 or raw.dtype!=np.uint8:raise ValueError(f'Неожиданная raw vision shape/dtype: {raw.shape}/{raw.dtype}.')
 return np.stack([np.asarray(Image.fromarray(x).resize((96,64),Image.Resampling.BILINEAR),dtype=np.uint8) for x in raw])
def edge_history(images):
 im=np.asarray(images,np.float32)
 if im.ndim!=5 or im.shape[1:]!=(2,64,96,3):raise ValueError('Нужны RGB-кадры двух official eye cameras 96x64.')
 lum=im.mean(-1)/255.;gx=np.abs(np.diff(lum,axis=3,prepend=lum[:,:,:,:1]));gy=np.abs(np.diff(lum,axis=2,prepend=lum[:,:,:1,:]));edge=np.sqrt(gx*gx+gy*gy);n=len(edge);coarse=edge.reshape(n,2,4,16,6,16).mean(axis=(3,5)).reshape(n,48);crop=edge[:,:,8:56,12:84];fine=crop.reshape(n,2,6,8,12,6).mean(axis=(3,5)).reshape(n,144);vec=np.concatenate([coarse,fine],axis=1);return np.concatenate([vec[2-i:n-i] for i in range(3)],axis=1)
class Bridge:
 def __init__(self):
  from importlib.metadata import version
  import flygym,mujoco
  from flygym.anatomy import AxisOrder,JointPreset,ActuatedDOFPreset,Skeleton
  from flygym.compose.fly import NeuroMechFly,ActuatorType
  from flygym.compose.pose import KinematicPosePreset
  from flygym.compose.world import FlatGroundWorld
  from flygym.simulation import Simulation
  from flygym.utils.math import Rotation3D
  if version('flygym')!='2.1.1':raise ValueError('Нужен exact FlyGym2.1.1.')
  self.versions={'flygym':version('flygym'),'mujoco':mujoco.__version__};self.ActuatorType=ActuatorType;axis=AxisOrder.YAW_PITCH_ROLL;sk=Skeleton(axis_order=axis,joint_preset=JointPreset.LEGS_ONLY);pose=KinematicPosePreset.NEUTRAL.get_pose_by_axis_order(axis);self.flies=[]
  for name in ('demonstrator','observer'):
   fly=NeuroMechFly(name=name);fly.add_joints(sk,neutral_pose=pose);dofs=fly.skeleton.get_actuated_dofs_from_preset(ActuatedDOFPreset.LEGS_ACTIVE_ONLY);fly.add_actuators(dofs,ActuatorType.MOTOR,neutral_input=None,forcelimited=True,forcerange=(-TORQUE_LIMIT,TORQUE_LIMIT));fly.add_leg_adhesion(gain=1.);self.flies.append(fly)
  self.flies[1].add_vision(draw_sensor_markers=False)
  world=FlatGroundWorld(name='series103_world');world.add_fly(self.flies[0],[-1.6,0,.7],Rotation3D('quat',[1,0,0,0]));world.add_fly(self.flies[1],[1.6,0,.7],Rotation3D('quat',[0,0,0,1]));self.sim=Simulation(world,timestep=DT);self.sim.reset();self.sim.step();self.names=('demonstrator','observer');self.actuated=[f.get_actuated_jointdofs_order(ActuatorType.MOTOR) for f in self.flies];self.all_dofs=[f.get_jointdofs_order() for f in self.flies];self.neutral=[np.array([pose.joint_angles_lookup_rad[d.name] for d in x]) for x in self.actuated];self.map_idx=[[next(i for i,d in enumerate(x) if d.name==name) for name in MAPPED_DOF] for x in self.actuated];self.q_idx=[[self.all_dofs[k].index(self.actuated[k][i]) for i in range(len(self.actuated[k]))] for k in (0,1)]
 def episode(self,moving,progress,base_fraction):
  sim=self.sim;sim.reset();sim.step();t=np.linspace(0,2*np.pi,FRAMES);ph=np.arange(6)*np.pi/5;traj=.24*np.sin(t[:,None]+ph[None,:]) if moving else np.zeros((FRAMES,6));desired=[]
  for k in (0,1):
   x=np.tile(self.neutral[k],(FRAMES,1));
   if k==0:x[:,self.map_idx[k]]+=traj
   desired.append(x)
  images=[];samples=[];forces=[];contacts=[];steps=(FRAMES-1)*round(FRAME_DT/DT)+1
  for n in range(steps):
   phase=n*DT/FRAME_DT;i=min(int(phase),FRAMES-2);alpha=min(phase-i,1.)
   for k,name in enumerate(self.names):
    target=(1-alpha)*desired[k][i]+alpha*desired[k][i+1];vel=(desired[k][i+1]-desired[k][i])/FRAME_DT;q=sim.get_joint_angles(name)[self.q_idx[k]];dq=sim.get_joint_velocities(name)[self.q_idx[k]];u=np.clip(KP*(target-q)+KD*(vel-dq),-TORQUE_LIMIT,TORQUE_LIMIT);sim.set_actuator_inputs(name,self.ActuatorType.MOTOR,u);sim.set_leg_adhesion_states(name,np.ones(6,dtype=bool))
   sim.step()
   if n%round(FRAME_DT/DT)==0:
    images.append(resize_eye_pair(sim.get_raw_vision('observer')));q=sim.get_joint_angles('demonstrator')[self.q_idx[0]];samples.append(q[self.map_idx[0]]-self.neutral[0][self.map_idx[0]]);forces.append(float(np.linalg.norm(sim.get_actuator_forces('demonstrator',self.ActuatorType.MOTOR))));found,*_=sim.get_ground_contact_info('observer');contacts.append(int(np.count_nonzero(found>.5)));progress('Official observer-eye frames: '+('moving' if moving else'neutral control'),base_fraction+.38*len(images)/FRAMES,len(images),FRAMES)
  return np.asarray(images),np.asarray(samples),{'max_force_norm':max(forces),'observer_contact_frame_fraction':float(np.mean(np.asarray(contacts)>0))}
 def close(self):
  if self.sim.eye_renderer is not None:self.sim.eye_renderer.close()
def decision(moving,neutral,samples,physical,versions):
 fm=edge_history(moving);fn=edge_history(neutral);rgb_delta=float(np.mean(np.abs(moving.astype(float)-neutral.astype(float))));edge_delta=float(np.mean(np.abs(fm-fn)));response=float(np.max(np.abs(samples)));checks={'flygym_2_1_1':versions['flygym']=='2.1.1','frames_49x2x64x96x3':moving.shape==(FRAMES,2,64,96,3) and neutral.shape==(FRAMES,2,64,96,3),'features_47x576':fm.shape==(47,576) and fn.shape==(47,576),'finite_nonconstant':bool(np.isfinite(fm).all() and np.std(moving)>1.),'interbody_rgb_delta':rgb_delta>=.05,'interbody_edge_delta':edge_delta>=1e-5,'demonstrator_response':response>=.03,'real_force_and_contact':physical['max_force_norm']>0 and physical['observer_contact_frame_fraction']>0};return {'checks':checks,'metrics':{'moving_shape':list(moving.shape),'feature_shape':list(fm.shape),'paired_rgb_mean_abs_delta_uint8':rgb_delta,'paired_edge_mean_abs_delta':edge_delta,'demonstrator_max_mapped_response_rad':response,**physical},'passed':all(checks.values()),'scientific_result':False}
def fixture_result():
 checks={k:True for k in ('flygym_2_1_1','frames_49x2x64x96x3','features_47x576','finite_nonconstant','interbody_rgb_delta','interbody_edge_delta','demonstrator_response','real_force_and_contact')};return {'checks':checks,'metrics':{'moving_shape':[49,2,64,96,3],'feature_shape':[47,576],'paired_rgb_mean_abs_delta_uint8':2.,'paired_edge_mean_abs_delta':.01,'demonstrator_max_mapped_response_rad':.2,'max_force_norm':8.,'observer_contact_frame_fraction':1.},'passed':True,'scientific_result':False}
def run(output_root=ROOT,fixture=False,progress=lambda *x:None):
 authorize();root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('flygym_interbody_vision_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);temp=folder/'result_incomplete';temp.mkdir(parents=True);progress('Проверяется Series102 authorization',.01,0,1)
 protocol={'schema':'flygym-interbody-vision-preflight-v1','mode':'fixture' if fixture else'full','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(__file__),'series102_result_sha256':RESULT102_SHA,'training_allowed':False,'selection_allowed':False,'official_api':'NeuroMechFly.add_vision + Simulation.get_raw_vision(observer)','eyes':'official left/right fisheye-corrected RGB resized deterministically to 96x64','paired_control':'same two bodies and observer; demonstrator moving versus neutral','thresholds':{'rgb_mean_abs_delta_uint8':.05,'edge_mean_abs_delta':1e-5,'demonstrator_response_rad':.03}};save(folder/'protocol.json',protocol)
 if fixture:primary=fixture_result()
 else:
  bridge=Bridge()
  try:moving,samples,physical=bridge.episode(True,progress,.04);neutral,_,_=bridge.episode(False,progress,.42);primary=decision(moving,neutral,samples,physical,bridge.versions);Image.fromarray(moving[0,0]).save(temp/'moving-first-left.png');Image.fromarray(moving[-1,0]).save(temp/'moving-last-left.png');Image.fromarray(neutral[-1,0]).save(temp/'neutral-last-left.png')
  finally:bridge.close()
 report={'schema':'flygym-interbody-vision-preflight-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':primary,'limitations':['Technical official-eye bridge preflight, not frozen89E policy evidence.','Deterministic resize to 96x64 is a declared coordinate adapter, not biological vision.','No FlyVis, connectome mapping, training, model selection, or living animal claim.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('SERIES103: OFFICIAL INTERBODY VISION PREFLIGHT\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\nTechnical bridge, не биологический результат.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Series103: official vision bridge');root.geometry('740x390+150+80');root.attributes('-topmost',True);status=tk.StringVar(value='Готов короткий preflight официального зрения между двумя телами');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series103: official FlyGym observer-eye bridge',font=('Arial',13,'bold'),pady=14).pack();tk.Label(root,text='Два official NeuroMechFly. Глаза observer сравнивают moving и neutral demonstrator.\nFrozen89E ещё не запускается; обучения и выбора модели нет.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=560,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Запустить короткий preflight',padx=18,pady=8);button.pack(pady=12)
 def update(text,fraction,done,total):
  def apply():
   p=round(fraction*100,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','));
   if start[0] and fraction>.02:elapsed=time.time()-start[0];eta.set(f'Прошло {elapsed/60:.1f} мин · осталось примерно {elapsed*(1-fraction)/fraction/60:.1f} мин')
  root.after(0,apply)
 def begin():
  button.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series103','Preflight завершён. Папка результата открыта.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-103.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series103',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run(a.output_root,True))
 else:print(run(a.output_root,False))
if __name__=='__main__':main()
