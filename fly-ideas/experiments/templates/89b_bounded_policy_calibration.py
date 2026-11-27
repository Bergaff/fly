#!/usr/bin/env python3
"""Series89B: preregistered development of calibrated bounded embodied policy."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;RUNNER88=HERE/'88_actuator_bridge_prototype.py';RUNNER88_SHA='888778dd5771f740e142747f0bad2eb1cadff8147bf01c6b2fe480c6952daa30';NO_GO89=HERE.parent/'reports'/'closed-loop-embodied-validation-user-summary-extract.json';NO_GO89_SHA='8bc6a9b55621c984a7ba5dfd2977f33fe6f061354c5c3018a04c42b1fccf3d75';NO_GO89_SOURCE_SHA='0b44d61b58b374ac95037ba8a853e23b0c48a1b8510a0b0f4c323ebb509d1105'
ROOT=Path('workspace/runs/ideas/i-observational/bounded-policy-calibration');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal');PROFILES=('neutral','pose_offset','velocity_offset');CONDITIONS=('candidate','uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');LIMIT=np.deg2rad(55.);SOFT_LIMIT=.78*LIMIT;DT=.004;FRAME_DT=.04;TORQUE_LIMIT=.35;RIDGE=.08;WORK88=None
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load88():
 if file_sha(RUNNER88)!=RUNNER88_SHA:raise ValueError('Закреплённый runner88 изменился.')
 s=importlib.util.spec_from_file_location('series89b_source',RUNNER88);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize89():
 if file_sha(NO_GO89)!=NO_GO89_SHA:raise ValueError('Published series89 extract изменён.')
 d=json.loads(NO_GO89.read_text(encoding='utf8'));motions=d.get('protocol',{}).get('motions',[])
 if d.get('source_file_sha256')!=NO_GO89_SOURCE_SHA or d.get('reported_primary',{}).get('passed') is not False or [x.get('id') for x in motions]!=list(range(567,603)):raise ValueError('Series89 no-go identity не подтверждена.')
 return {x['motion_sha256'] for x in motions}
def specs(fixture=False):
 m86=load88().load87().load86();out=[]
 for role,start,reps,base in (('development',603,6,890300),('final',621,6,890400)):
  ident=start
  for rep in range(reps):
   for ai,action in enumerate(ACTIONS):
    amp=(.74,.87,1.)[(rep+ai)%3];speed=(.66,.94,1.22)[(2*rep+ai)%3];seed=base+10*rep+ai;out.append({'role':role,'id':ident,'replicate':rep+1,'action':action,'policy_seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 if fixture:return [x for x in out if x['id'] in (603,604,605,621,622,623)]
 return out
def held_views(role,fixture=False):
 count=4 if fixture else (8 if role=='development' else 12);offset=301 if role=='development' else 321;vals=[]
 for i in range(count):vals.append({'corner_id':offset+i,'view':{'fov_deg':35.,'camera_side':(.16,.24,.32,.40,.44)[(2*i+1)%5],'camera_z':(.36,.45,.54,.59)[(i+1)%4],'body_x':(3.90,3.98,4.06,4.10)[(3*i+1)%4],'body_y':(-.045,.015,.055)[(i+1)%3]}})
 return vals
def prepare(stim,labels,training_hashes,fixture=False):
 m88=load88();m87=m88.load87();m86=m87.load86();seen={x['motion_sha256'] for x in labels}|set(training_hashes)|m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|authorize89();out=[];desc=[]
 for x in specs(fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series89B motion совпал с training/disclosed motion.')
  seen.add(h);item={**x,'motion_sha256':h};out.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'})
 return out,desc
def policy_features(target):
 q=np.asarray(target,float);v=np.vstack((np.zeros((1,6)),np.diff(q,axis=0)));return np.column_stack((q,v,np.ones(len(q))))
def project_policy(q):
 q=SOFT_LIMIT*np.tanh(np.asarray(q,float)/SOFT_LIMIT);out=q.copy();slew=.11
 for i in range(1,len(out)):out[i]=out[i-1]+np.clip(out[i]-out[i-1],-slew,slew)
 return np.clip(out,-SOFT_LIMIT,SOFT_LIMIT)
def fit_calibrator(development):
 X=np.concatenate([policy_features(x['target']) for x in development]);Y=np.concatenate([x['truth'] for x in development]);mean=X[:,:12].mean(0);scale=X[:,:12].std(0);scale[scale<.02]=.02;Z=X.copy();Z[:,:12]=(Z[:,:12]-mean)/scale;reg=np.eye(13)*RIDGE;reg[-1,-1]=0;weights=np.linalg.solve(Z.T@Z+reg,Z.T@Y);raw=float(np.sqrt(np.mean((X[:,:6]-Y)**2)));cal=Z@weights;partial={'mean':mean,'scale':scale,'weights':weights};projected=np.concatenate([calibrate(x['target'],partial) for x in development]);return {'mean':mean,'scale':scale,'weights':weights,'ridge':RIDGE,'development_frames':len(X),'raw_rmse':raw,'calibrated_rmse':float(np.sqrt(np.mean((cal-Y)**2))),'projected_rmse':float(np.sqrt(np.mean((projected-Y)**2)))}
def calibrate(target,model):
 X=policy_features(target);X[:,:12]=(X[:,:12]-model['mean'])/model['scale'];return project_policy(X@model['weights'])
def contact_sensor(q):
 q=np.asarray(q);return np.exp(-((q[..., [0,3]]-q[..., [1,4]])/.42)**2-((q[..., [2,5]]-.35)/.55)**2)
def initial_state(profile,seed):
 rng=np.random.default_rng(seed);q=rng.normal(0,.004,6);dq=np.zeros(6);tilt=np.zeros(2)
 if profile=='pose_offset':q+=np.array([.10,-.08,.06,-.10,.08,-.06]);tilt[:]=[.07,-.05]
 elif profile=='velocity_offset':dq=np.array([.18,-.14,.12,-.18,.14,-.12]);tilt[:]=[-.05,.06]
 elif profile!='neutral':raise ValueError('Неизвестный initial profile.')
 return q,dq,tilt
def rollout(target,truth,seed,profile,closed_loop=True,barrier=True):
 target=np.asarray(target,float);truth=np.asarray(truth,float);q,dq,tilt=initial_state(profile,seed);dtilt=np.zeros(2);steps=(len(target)-1)*round(FRAME_DT/DT)+1;qs=[];torques=[];tilts=[];zs=[];disturb_at=int(.55*steps);disturb_end=disturb_at+round(.08/DT)
 for n in range(steps):
  phase=n*DT/FRAME_DT;i=min(int(phase),len(target)-2);a=min(phase-i,1.);des=(1-a)*target[i]+a*target[i+1];vel=(target[i+1]-target[i])/FRAME_DT;actual=contact_sensor(q);desired=contact_sensor(des)
  if closed_loop:u=1.65*(des-q)+.22*(vel-dq);u[[2,5]]+=.045*(desired-actual)
  else:u=.055*vel+.20*des
  if barrier:u-=1.2*np.sign(q)*np.maximum(np.abs(q)-.72*LIMIT,0)
  if disturb_at<=n<disturb_end:u+=np.array([.11,-.09,.07,-.11,.09,-.07])
  u=np.clip(u,-TORQUE_LIMIT,TORQUE_LIMIT);dq+=DT*((u-.045*dq)/.018);q+=DT*dq;hit=np.abs(q)>LIMIT
  if np.any(hit):q=np.clip(q,-LIMIT,LIMIT);dq[hit]*=-.08
  reaction=np.array([u[0]+u[1]+u[2]-u[3]-u[4]-u[5],u[0]-u[1]-u[3]+u[4]]);dtilt+=DT*(.025*reaction-2.8*tilt-.9*dtilt);tilt+=DT*dtilt;z=.40-.018*np.linalg.norm(tilt)-.002*np.sum(np.abs(q));qs.append(q.copy());torques.append(u.copy());tilts.append(tilt.copy());zs.append(z)
 idx=np.arange(len(target))*round(FRAME_DT/DT);sample=np.asarray(qs)[idx];tau=np.asarray(torques);vels=np.asarray([np.zeros(6),*np.diff(qs,axis=0)/DT]);errors=np.sqrt(np.mean((sample-target)**2,axis=1));df=round(disturb_at*DT/FRAME_DT);rf=round(disturb_end*DT/FRAME_DT);base=float(np.mean(errors[max(0,df-5):df]));after=np.where(errors[rf:]<=max(.08,1.5*base))[0];recovery=float(after[0]*FRAME_DT) if len(after) else None;return {'angle_rmse_truth':float(np.sqrt(np.mean((sample-truth)**2))),'target_tracking_rmse':float(np.sqrt(np.mean((sample-target)**2))),'contact_mae_truth':float(np.mean(np.abs(contact_sensor(sample)-contact_sensor(truth)))),'completion_ratio':float(np.mean(np.linalg.norm(sample,axis=1)>.08)),'recovery_s':recovery,'recovered':recovery is not None and recovery<=.40,'limit_violations':int(np.sum(np.abs(sample)>=LIMIT-1e-9)),'nan_count':int(np.size(sample)-np.isfinite(sample).sum()),'energy_abs_work':float(np.sum(np.abs(tau*vels))*DT),'max_abs_torque':float(np.max(np.abs(tau))),'max_tilt_rad':float(np.max(np.abs(tilts))),'minimum_body_z':float(np.min(zs)),'proprioception_feedback':closed_loop,'contact_feedback':closed_loop,'barrier_controller':barrier}
def worker_init(bundle,s84v):
 global WORK88
 WORK88=load88();WORK88.worker_init(bundle,s84v)
def worker_visual(arg):
 item,view=arg;row=WORK88.WORK87.worker_task((item,view));b=WORK88.WORK87.WORKER86.WORK['b'];shared=np.asarray(row.pop('_shared'));truth=np.asarray(row.pop('_execution'));row.pop('_private',None);coeff,target=b.compress_replay(shared);return {k:v for k,v in row.items() if k not in ('shared_observation','private_observation','execution_mode','zero','controls','population_sufficient')}|{'state_coefficients':72,'state_sha256':sha(np.asarray(coeff,dtype='<f8').tobytes()),'_coeff':coeff,'_target':target,'_truth':truth}
def controls_for(b,coeff,target,model):
 state=np.asarray(coeff).reshape(6,12);rng=np.random.default_rng(8905);sh=np.roll(state[rng.permutation(6)],2,axis=1);les=state.copy();les[[0,1]]=0;decode=lambda s:np.clip(b.cosine_basis(49)@s.T,-LIMIT,LIMIT)
 return {'candidate':calibrate(target,model),'uncalibrated':target,'zero_state':np.zeros_like(target),'shuffled_state':calibrate(decode(sh),model),'open_loop':calibrate(target,model),'shared_lesion':calibrate(decode(les),model)}
def decision(rows,fixture=False):
 trials=[t for r in rows for t in r['trials']];candidate=[t['controls']['candidate'] for t in trials];required=len(trials) if fixture else math.ceil(.90*len(trials));safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=TORQUE_LIMIT+1e-12 and x['energy_abs_work']<=4 and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30;safety=sum(safe(x) for x in candidate);recovered=sum(x['recovered'] for x in candidate);completed=sum(x['completion_ratio']>=.65 for x in candidate);names=('uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');wins={n:sum(t['controls']['candidate']['angle_rmse_truth']<t['controls'][n]['angle_rmse_truth'] for t in trials) for n in names};contact={n:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][n]['contact_mae_truth'] for t in trials) for n in names};means={n:{'angle_rmse_truth':float(np.mean([t['controls'][n]['angle_rmse_truth'] for t in trials])),'contact_mae_truth':float(np.mean([t['controls'][n]['contact_mae_truth'] for t in trials]))} for n in CONDITIONS};angle=all(wins[n]>=required for n in names);contact_gate=sum(contact[n]>=required for n in names)>=4;mean_margin=means['candidate']['angle_rmse_truth']<=.90*means['uncalibrated']['angle_rmse_truth'] and means['candidate']['angle_rmse_truth']<=.90*means['zero_state']['angle_rmse_truth'];passed=safety==len(trials) and recovered>=required and completed>=required and angle and contact_gate and mean_margin;return {'final_visual_cases':len(rows),'final_trials':len(trials),'required_trials':required,'candidate_safety_passed':safety,'candidate_recovered':recovered,'candidate_completed':completed,'candidate_angle_wins':wins,'candidate_contact_wins':contact,'means':means,'angle_gate_passed':angle,'contact_gate_passed':contact_gate,'mean_margin_passed':mean_margin,'passed':passed}
def run(source_folder,workers,output_root=ROOT,fixture=False):
 authorize89();m88=load88();m87=m88.load87();m86=m87.load86();s85=m86.load85();workers,count=s85.worker_choice(workers);print('1/6 Проверяются no-go89 identity и frozen84Z...',flush=True);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,fixture)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items,desc=prepare(stim,saved['labels'],training_hashes,fixture);dev=[x for x in items if x['role']=='development'];final=[x for x in items if x['role']=='final'];dv=held_views('development',fixture);fv=held_views('final',fixture);tasks=[(x,v) for x in dev for v in dv]+[(x,v) for x in final for v in fv];protocol={'schema':'bounded-policy-calibration-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner88_sha256':RUNNER88_SHA,'series89_nogo_extract_sha256':NO_GO89_SHA,'selected_model_sha256':file_sha(paths[1]),'development_training_allowed':True,'source84z_training_allowed':False,'motions':desc,'development_views':dv,'final_views':fv,'initial_profiles':list(PROFILES),'controls':list(CONDITIONS),'ridge':RIDGE,'soft_limit_rad':SOFT_LIMIT,'final_used_for_fit':False,'workers':count,'worker_choice':str(workers),'primary_rule':'all candidate safe; >=90% recover/complete; candidate angle beats every control >=90%; contact beats >=4/5 controls >=90%; mean angle <=0.90 uncalibrated and zero'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('bounded_policy_calibration_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/6 Запускается {len(tasks)} visual cases, workers={count}.',flush=True);visual=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(worker_visual,tasks),1):visual.append(row);print(f'  Visual cases {n}/{len(tasks)}',flush=True) if n%12==0 else None
 print('3/6 Calibrator fit только development stream...',flush=True);development=[{'target':r['_target'],'truth':r['_truth']} for r in visual if r['role']=='development'];model=fit_calibrator(development);np.savez_compressed(temp/'policy_calibrator.npz',mean=model['mean'],scale=model['scale'],weights=model['weights'],ridge=np.array([RIDGE]));model_meta={k:v for k,v in model.items() if k not in ('mean','scale','weights')}|{'sha256':file_sha(temp/'policy_calibrator.npz')};print('4/6 Final controls и embodied trials...',flush=True);rows=[]
 for row in [r for r in visual if r['role']=='final']:
  targets=controls_for(b,row['_coeff'],row['_target'],model);trials=[]
  for pi,profile in enumerate(PROFILES):
   controls={};seed=890000000+row['id']*1000+row['corner_id']*10+pi
   for name in CONDITIONS:controls[name]=rollout(targets[name],row['_truth'],seed,profile,name!='open_loop',name not in ('uncalibrated','zero_state'))
   trials.append({'initial_profile':profile,'initial_seed':seed,'controls':controls})
  clean={k:v for k,v in row.items() if not k.startswith('_')};clean['trials']=trials;rows.append(clean);td=temp/f'test_{row["id"]:03d}'/f'view_{row["corner_id"]:03d}';td.mkdir(parents=True);save(td/'metrics.json',clean)
 print('5/6 Проверяются frozen final gates...',flush=True);primary=decision(rows,fixture);report={'schema':'bounded-policy-calibration-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'calibrator':model_meta,'primary':primary,'tests':rows,'source84z_primary':summary['primary'],'limitations':['Supervised engineering calibration on synthetic development truth; not autonomous learning.','Reduced support surrogate and geometric contact proxy, not a complete body.','Final go only authorizes separate frozen89C replication, not series90.','No natural vision, muscles or biological neurons.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 89B: BOUNDED POLICY CALIBRATION\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 if manifest(folder/'result')!=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))['files']:raise ValueError('Manifest series89B повреждён.')
 print('6/6 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия89B: bounded policy calibration');root.geometry('760x380+170+90');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия89B: development calibration + untouched final\n360 visual cases; frozen source84Z.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать завершённую папку84Z и запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 folder=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not folder:root.destroy();return
 root.withdraw();root.update();result=run(folder,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия89B завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-89B.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 89B: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
 if os.name=='nt':
  try:os.startfile(str(path))
  except OSError:pass
 return path
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source84z');p.add_argument('--workers',default='6');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true',help=argparse.SUPPRESS);q=p.parse_args()
 if q.choose:choose()
 elif q.source84z:run(q.source84z,q.workers,q.output_root,q.fixture)
 else:p.error('Нужен --choose или --source84z.')
if __name__=='__main__':
 try:main()
 except Exception as exc:report=failure_report(exc);print(f'ОШИБКА: {type(exc).__name__}: {exc}\nОтчёт: {report.resolve()}',file=sys.stderr);sys.exit(1)
