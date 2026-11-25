#!/usr/bin/env python3
"""Series101: frozen89E state/policy adapter to two official FlyGym bodies."""
from __future__ import annotations
import argparse,concurrent.futures,csv,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER89E=HERE/'89e_frozen_routing_margin_replication.py';RUNNER89E_SHA='06e41e7ec789514f4ee8bbd06365b9b51a4570e24f5b1451890795d066c5e1bf'
GO89E=HERE.parent/'reports'/'frozen-routing-margin-replication-89e-user-summary-extract.json';GO89E_SHA='fc4d84ff7f7f97bbbe4570a0b5ac727c2a1700a37e773aaae3ca9b8fb9859686'
BODY_GO=HERE.parent/'reports'/'flygym-two-body-preflight-user-result.json';BODY_GO_SHA='dea1acc516f5f42950f8199555d0633e66d307f2aeaf27306e5ddcb4b0e11892'
ROOT=Path('workspace/runs/ideas/i-observational/frozen89e-flygym-adapter');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');CONDITIONS=('candidate','zero_state','shuffled_state','shared_lesion','open_loop')
MAPPED_DOF=('c_thorax-lf_coxa-pitch','lf_coxa-lf_trochanterfemur-pitch','lf_trochanterfemur-lf_tibia-pitch','c_thorax-rf_coxa-pitch','rf_coxa-rf_trochanterfemur-pitch','rf_trochanterfemur-rf_tibia-pitch')
DT=.0005;FRAME_DT=.04;MAX_OFFSET=.35;KP=18.;KD=.18;TORQUE_LIMIT=25.;WORK=None

def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha_bytes(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load89e():
 if file_sha(RUNNER89E)!=RUNNER89E_SHA:raise ValueError('Закреплённый runner89E изменился.')
 s=importlib.util.spec_from_file_location('series101_source',RUNNER89E);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize():
 if file_sha(GO89E)!=GO89E_SHA:raise ValueError('Published frozen89E extract изменён.')
 if file_sha(BODY_GO)!=BODY_GO_SHA:raise ValueError('Series100 body-go result изменён.')
 e=json.loads(GO89E.read_text(encoding='utf8'));b=json.loads(BODY_GO.read_text(encoding='utf8'))
 if e.get('reported_primary',{}).get('passed') is not True or b.get('primary',{}).get('passed') is not True or b.get('metrics',{}).get('flygym_version')!='2.1.1':raise ValueError('Нужны точные go89E и body-go100.')
 return e,b
def worker_init(bundle,s84v):
 global WORK
 WORK=load89e();WORK.worker_init(bundle,s84v)
def worker_visual(arg):return WORK.worker_visual(arg)
def motion_specs(m86,fixture=False):
 out=[];ident=891
 for rep in range(2):
  for ai,action in enumerate(ACTIONS):
   seed=101010+rep*10+ai;amp=(.72,.92)[rep];speed=(.76,1.12)[(rep+ai)%2];out.append({'role':'adapter_final','id':ident,'replicate':rep+1,'action':action,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 return out[:3] if fixture else out
def views(fixture=False):
 values=[{'corner_id':801,'view':{'fov_deg':35.,'camera_side':.20,'camera_z':.42,'body_x':3.94,'body_y':-.03}},{'corner_id':802,'view':{'fov_deg':35.,'camera_side':.32,'camera_z':.52,'body_x':4.06,'body_y':.03}},{'corner_id':803,'view':{'fov_deg':35.,'camera_side':.40,'camera_z':.40,'body_x':4.08,'body_y':0.}},{'corner_id':804,'view':{'fov_deg':35.,'camera_side':.24,'camera_z':.56,'body_x':3.92,'body_y':.02}}]
 return values[:1] if fixture else values

def frozen_visual(source_folder,d_folder,workers,fixture,progress):
 s89=load89e();s89.authorize_d();md=s89.load_d();mc=md.load_c();m6=mc.load_b6();m5=m6.load_b5();m4=m5.load_b4();m3=m4.load_b3();m2=m3.load_b2();m=m2.load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();s85=m86.load85();workers,count=s85.worker_choice(workers)
 frozen_path,d_summary,angle,identity,common,experts,selections,standard,standard_selections,temp=s89.load_frozen(d_folder,fixture);frozen_before=manifest(frozen_path);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,fixture)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 seen={x['motion_sha256'] for x in saved['labels']}|training|m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|m2.authorize_b()|m3.authorize_b2()|s89.authorize_d()
 for old in s89.specs(False):seen.add(stim.motion_hash(np.asarray(old['angles_deg'],float)))
 items=[];desc=[]
 for x in motion_specs(m86,fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series101 motion совпал с disclosed/training motion.')
  seen.add(h);item={**x,'motion_sha256':h};items.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'})
 vv=views(fixture);tasks=[(x,v) for x in items for v in vv];progress('Frozen visual inference',.04,0,len(tasks));visual=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(worker_visual,tasks),1):visual.append(row);progress('Frozen visual inference',.04+.16*n/len(tasks),n,len(tasks))
 cases=[]
 for row in visual:
  targets,probs=md.controls_for(m3,m2,m,b,row['_coeff'],row['_target'],angle,identity,temp,common,float(d_summary['model']['common_selected']['lambda']),experts,selections,standard,standard_selections)
  cases.append({'id':row['id'],'corner_id':row['corner_id'],'action':row['action'],'truth':np.asarray(row['_truth'],float),'targets':{k:np.asarray(targets['candidate' if k=='open_loop' else k],float) for k in CONDITIONS},'predicted_action':ACTIONS[int(np.argmax(probs))],'state_sha256':sha_bytes(np.asarray(row['_coeff'],dtype='<f8').tobytes()),'target_hashes':{k:sha_bytes(np.asarray(targets['candidate' if k=='open_loop' else k],dtype='<f8').tobytes()) for k in CONDITIONS}})
 if before!={p:file_sha(p) for p in before} or frozen_before!=manifest(frozen_path):raise ValueError('Frozen sources изменились.')
 return cases,desc,vv,count,paths[1],frozen_path

class FlyGymBridge:
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
  self.np=np;self.ActuatorType=ActuatorType;axis=AxisOrder.YAW_PITCH_ROLL;sk=Skeleton(axis_order=axis,joint_preset=JointPreset.LEGS_ONLY);pose=KinematicPosePreset.NEUTRAL.get_pose_by_axis_order(axis);self.pose=pose;self.flies=[]
  for name in ('demonstrator','observer'):
   fly=NeuroMechFly(name=name);fly.add_joints(sk,neutral_pose=pose);dofs=fly.skeleton.get_actuated_dofs_from_preset(ActuatedDOFPreset.LEGS_ACTIVE_ONLY);fly.add_actuators(dofs,ActuatorType.MOTOR,neutral_input=None,forcelimited=True,forcerange=(-TORQUE_LIMIT,TORQUE_LIMIT));fly.add_leg_adhesion(gain=1.0);self.flies.append(fly)
  world=FlatGroundWorld(name='series101_world');world.add_fly(self.flies[0],[-1.6,0,.7],Rotation3D('quat',[1,0,0,0]));world.add_fly(self.flies[1],[1.6,0,.7],Rotation3D('quat',[0,0,0,1]));self.sim=Simulation(world,timestep=DT);self.sim.reset();self.sim.step();self.names=('demonstrator','observer');self.actuated=[f.get_actuated_jointdofs_order(ActuatorType.MOTOR) for f in self.flies];self.all_dofs=[f.get_jointdofs_order() for f in self.flies];self.neutral=[np.array([pose.joint_angles_lookup_rad[d.name] for d in x]) for x in self.actuated];self.map_idx=[[next(i for i,d in enumerate(x) if d.name==name) for name in MAPPED_DOF] for x in self.actuated];self.q_idx=[[self.all_dofs[k].index(self.actuated[k][i]) for i in range(len(self.actuated[k]))] for k in (0,1)];self.thorax=[[x.name for x in f.get_bodysegs_order()].index('c_thorax') for f in self.flies]
 def mapped(self,trajectory,k):
  out=np.tile(self.neutral[k],(len(trajectory),1));out[:,self.map_idx[k]]+=np.clip(np.asarray(trajectory),-MAX_OFFSET,MAX_OFFSET);return out
 def rollout(self,policy,truth,open_loop=False):
  sim=self.sim;sim.reset();sim.step();demo=self.mapped(truth,0);obs=self.mapped(policy,1);frames=len(policy);steps=(frames-1)*round(FRAME_DT/DT)+1;sample=[];contacts=[];forces=[];zs=[];finite=True;saturated=0;energy=0.;last_q=None
  for n in range(steps):
   phase=n*DT/FRAME_DT;i=min(int(phase),frames-2);alpha=min(phase-i,1.);desired=[(1-alpha)*demo[i]+alpha*demo[i+1],(1-alpha)*obs[i]+alpha*obs[i+1]];vel=[(demo[i+1]-demo[i])/FRAME_DT,(obs[i+1]-obs[i])/FRAME_DT]
   for k,name in enumerate(self.names):
    q=sim.get_joint_angles(name)[self.q_idx[k]];dq=sim.get_joint_velocities(name)[self.q_idx[k]]
    raw=KP*((desired[k]-self.neutral[k]) if (open_loop and k==1) else (desired[k]-q))+KD*(vel[k] if (open_loop and k==1) else (vel[k]-dq));saturated+=int(np.any(np.abs(raw)>TORQUE_LIMIT));u=np.clip(raw,-TORQUE_LIMIT,TORQUE_LIMIT);sim.set_actuator_inputs(name,self.ActuatorType.MOTOR,u);sim.set_leg_adhesion_states(name,np.ones(6,dtype=bool));energy+=float(np.sum(np.abs(u*dq))*DT)
   sim.step();finite&=bool(np.isfinite(sim.mj_data.qpos).all() and np.isfinite(sim.mj_data.qvel).all())
   if n%round(FRAME_DT/DT)==0:
    q=sim.get_joint_angles('observer')[self.q_idx[1]];sample.append(q[self.map_idx[1]]-self.neutral[1][self.map_idx[1]]);found,*_=sim.get_ground_contact_info('observer');contacts.append(int(np.count_nonzero(found>.5)));forces.append(float(np.linalg.norm(sim.get_actuator_forces('observer',self.ActuatorType.MOTOR))));zs.append(float(sim.get_body_positions('observer')[self.thorax[1],2]))
  sample=np.asarray(sample);truth_clip=np.clip(np.asarray(truth),-MAX_OFFSET,MAX_OFFSET);policy_clip=np.clip(np.asarray(policy),-MAX_OFFSET,MAX_OFFSET);return {'finite':finite,'tracking_rmse_rad':float(np.sqrt(np.mean((sample-policy_clip)**2))),'truth_rmse_rad':float(np.sqrt(np.mean((sample-truth_clip)**2))),'contact_frame_fraction':float(np.mean(np.asarray(contacts)>0)),'mean_contact_legs':float(np.mean(contacts)),'max_actuator_force_norm':max(forces),'minimum_thorax_z_mm':min(zs),'maximum_thorax_z_mm':max(zs),'energy_abs_work':energy,'torque_saturation_fraction':saturated/(steps*2),'sample':sample}

def fixture_physics(cases):
 rows=[]
 for c in cases:
  controls={}
  for j,name in enumerate(CONDITIONS):controls[name]={'finite':True,'tracking_rmse_rad':.04+.01*j,'truth_rmse_rad':.08 if name=='candidate' else .18+.01*j,'contact_frame_fraction':1.,'mean_contact_legs':3.,'max_actuator_force_norm':8.,'minimum_thorax_z_mm':.8,'maximum_thorax_z_mm':1.2,'energy_abs_work':1.,'torque_saturation_fraction':0.01}
  rows.append({'id':c['id'],'corner_id':c['corner_id'],'action':c['action'],'predicted_action':c['action'],'state_sha256':c['state_sha256'],'target_hashes':c['target_hashes'],'controls':controls})
 return rows,[]
def decision(rows,fixture=False):
 n=len(rows);required=n if fixture else math.ceil(.60*n);open_required=n if fixture else math.ceil(.80*n);candidate=[r['controls']['candidate'] for r in rows];safe=lambda x:x['finite'] and x['minimum_thorax_z_mm']>=.15 and x['maximum_thorax_z_mm']<=2.5 and x['contact_frame_fraction']>0
 safe_n=sum(safe(x) for x in candidate);tracking=float(np.mean([x['tracking_rmse_rad'] for x in candidate]));wins={name:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][name]['truth_rmse_rad'] for r in rows) for name in ('zero_state','shuffled_state','shared_lesion','open_loop')};distinct=all(r['target_hashes']['candidate']!=r['target_hashes'][k] for r in rows for k in ('zero_state','shuffled_state','shared_lesion'));passed=safe_n==n and tracking<=.20 and wins['zero_state']>=required and wins['shuffled_state']>=required and wins['open_loop']>=open_required and distinct;return {'cases':n,'required_state_wins':required,'required_open_loop_wins':open_required,'candidate_safe_cases':safe_n,'candidate_mean_tracking_rmse_rad':tracking,'candidate_truth_wins':wins,'state_controls_distinct':distinct,'passed':passed,'scientific_result':False}
def run(source,d_folder,workers='6',output_root=ROOT,fixture=False,progress=lambda *x:None):
 authorize();root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('frozen89e_flygym_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);temp=folder/'result_incomplete';temp.mkdir(parents=True);progress('Проверяются frozen sources',.01,0,1)
 if fixture:
  cases=[{'id':891+i,'corner_id':801,'action':ACTIONS[i],'truth':np.zeros((49,6)),'targets':{k:np.zeros((49,6)) for k in CONDITIONS},'predicted_action':ACTIONS[i],'state_sha256':str(i),'target_hashes':{'candidate':'c'+str(i),'zero_state':'z'+str(i),'shuffled_state':'s'+str(i),'shared_lesion':'l'+str(i),'open_loop':'c'+str(i)}} for i in range(3)];desc=[];vv=views(True);count=1;model_path=Path(__file__);frozen_path=Path(__file__)
 else:cases,desc,vv,count,model_path,frozen_path=frozen_visual(source,d_folder,workers,fixture,progress)
 protocol={'schema':'frozen89e-flygym-adapter-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'created_utc':datetime.now(timezone.utc).isoformat(),'runner89e_sha256':RUNNER89E_SHA,'go89e_sha256':GO89E_SHA,'body_go100_sha256':BODY_GO_SHA,'training_allowed':False,'selection_allowed':False,'motions':desc,'views':vv,'workers':count,'mapped_dof':list(MAPPED_DOF),'mapping':'synthetic six axes are fixed unit-gain offsets from official neutral pose, clipped ±0.35rad','motor':{'type':'MuJoCo MOTOR','dt_s':DT,'frame_dt_s':FRAME_DT,'kp':KP,'kd':KD,'torque_limit':TORQUE_LIMIT},'controls':list(CONDITIONS),'open_loop_definition':'same candidate target, feedforward torque from neutral and target velocity; no q/dq feedback','primary_rule':'all candidate safe/contact; mean tracking<=0.20rad; candidate truth RMSE wins vs zero/shuffled>=60%, vs true open-loop>=80%; state target hashes distinct'};save(folder/'protocol.json',protocol)
 trace=[]
 if fixture:rows,trace=fixture_physics(cases)
 else:
  bridge=FlyGymBridge();rows=[];total=len(cases)*len(CONDITIONS);done=0
  for c in cases:
   controls={}
   for name in CONDITIONS:
    metric=bridge.rollout(c['targets'][name],c['truth'],name=='open_loop');sample=metric.pop('sample');controls[name]=metric
    for fi,angles in enumerate(sample):trace.append({'id':c['id'],'corner_id':c['corner_id'],'action':c['action'],'condition':name,'frame':fi,**{MAPPED_DOF[j]:float(angles[j]) for j in range(6)}})
    done+=1;progress('FlyGym physical controls',.20+.76*done/total,done,total)
   rows.append({'id':c['id'],'corner_id':c['corner_id'],'action':c['action'],'predicted_action':c['predicted_action'],'state_sha256':c['state_sha256'],'target_hashes':c['target_hashes'],'controls':controls})
 primary=decision(rows,fixture);report={'schema':'frozen89e-flygym-adapter-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':primary,'tests':rows,'limitations':['Development adapter prototype, not frozen biological evidence.','Fixed six-channel mapping controls only front-leg pitch DOFs; other36 actuators hold the official neutral pose.','Synthetic truth is used only for scoring and demonstrator command; observer candidate receives frozen89E-derived policy.','No FlyVis, connectome mapping, living animal, muscles, or claim of biological mirror neurons.']};save(temp/'summary.json',report)
 if trace:
  with (temp/'physical_trace.csv').open('w',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=list(trace[0]));w.writeheader();w.writerows(trace)
 (temp/'ИТОГ.txt').write_text('SERIES101: FROZEN89E → OFFICIAL FLYGYM\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\nDevelopment adapter, не биологический результат.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series101: frozen89E → FlyGym');root.geometry('760x430+150+80');root.attributes('-topmost',True);workers=tk.StringVar(value='6');status=tk.StringVar(value='Выберите frozen sources и запустите короткий adapter prototype');pct=tk.DoubleVar(value=0);eta=tk.StringVar(value='');start=[None]
 tk.Label(root,text='Series101: frozen89E → официальное тело FlyGym',font=('Arial',13,'bold'),pady=14).pack();tk.Label(root,text='24 frozen visual cases × 5 физических controls. Обучения нет.\nФиксированный mapping управляет шестью pitch DOF передних лап.',justify='center').pack();tk.Label(root,text='Workers для frozen visual phase:').pack(pady=(12,2));row=tk.Frame(root);row.pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(row,text=text,variable=workers,value=value).pack(side='left',padx=8)
 tk.Label(root,textvariable=status,pady=12).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=580,state='disabled').pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать result89D и source84Z, затем запустить',padx=18,pady=8);button.pack(pady=14)
 def update(text,fraction,done,total):
  def apply():
   status.set(text);pct.set(round(fraction*100,1))
   if start[0] and fraction>.02:
    elapsed=time.time()-start[0];remain=elapsed*(1-fraction)/fraction;eta.set(f'Прошло {elapsed/60:.1f} мин · осталось примерно {remain/60:.1f} мин')
  root.after(0,apply)
 def begin():
  d=filedialog.askdirectory(title='Выберите завершённую result-папку series89D',mustexist=True,initialdir=str(D_ROOT.resolve() if D_ROOT.exists() else Path.cwd()),parent=root)
  if not d:return
  source=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
  if not source:return
  button.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(source,d,workers.get(),progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series101','Расчёт завершён. Папка результата открыта.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-101.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    root.after(0,lambda:(messagebox.showerror('Series101',f'{exc}\n\nОтчёт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.bind('2',lambda e:workers.set('2'));root.bind('4',lambda e:workers.set('4'));root.bind('6',lambda e:workers.set('6'));root.bind('m',lambda e:workers.set('max'));root.bind('M',lambda e:workers.set('max'));root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--workers',default='6');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true');a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.', '.',a.workers,a.output_root,True))
 elif a.source84z and a.result89d:print(run(a.source84z,a.result89d,a.workers,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d.')
if __name__=='__main__':main()
