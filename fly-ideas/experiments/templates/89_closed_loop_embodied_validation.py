#!/usr/bin/env python3
"""Series89: preregistered closed-loop surrogate embodied validation."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;RUNNER88=HERE/'88_actuator_bridge_prototype.py';RUNNER88_SHA='888778dd5771f740e142747f0bad2eb1cadff8147bf01c6b2fe480c6952daa30';GO88=HERE.parent/'reports'/'actuator-bridge-prototype-user-summary-extract.json';GO88_SHA='baa175ce7af1b20e7f37d9e24d3fb804620276b5f4073be6a15bd4a6ddd8e6e1';GO88_SOURCE_SHA='94fac84c12fb0049aada2dd5b04ac84da30d63808e6d0a45cd09d0c731780feb'
ROOT=Path('workspace/runs/ideas/i-observational/closed-loop-embodied-validation');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal');PROFILES=('neutral','pose_offset','velocity_offset');CONDITIONS=('normal','zero_state','shuffled_state','open_loop','shared_lesion');LIMIT=np.deg2rad(55.);DT=.004;FRAME_DT=.04;TORQUE_LIMIT=.35;WORK88=None
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
 s=importlib.util.spec_from_file_location('series89_source',RUNNER88);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize88():
 if file_sha(GO88)!=GO88_SHA:raise ValueError('Published series88 extract изменён.')
 d=json.loads(GO88.read_text(encoding='utf8'));motions=d.get('protocol',{}).get('motions',[])
 if d.get('source_file_sha256')!=GO88_SOURCE_SHA or not d.get('reported_primary',{}).get('passed') or [x.get('id') for x in motions]!=list(range(537,567)):raise ValueError('Series88 actuator go не подтверждён.')
 return {x['motion_sha256'] for x in motions}
def specs(fixture=False):
 m86=load88().load87().load86();out=[];ident=567
 for rep in range(12):
  for ai,action in enumerate(ACTIONS):
   amp=(.76,.88,1.)[(2*rep+ai)%3];speed=(.68,.96,1.24)[(rep+2*ai)%3];seed=890200+10*rep+ai;out.append({'role':'evaluation','id':ident,'replicate':rep+1,'action':action,'embodied_seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 return [x for x in out if x['id'] in (567,568,569)] if fixture else out
def views(fixture=False):
 vals=[]
 for i in range(12):vals.append({'corner_id':101+i,'view':{'fov_deg':35.,'camera_side':(.14,.22,.30,.38,.46)[i%5],'camera_z':(.34,.43,.52,.61)[(2*i)%4],'body_x':(3.88,3.96,4.04,4.12)[(3*i)%4],'body_y':(-.06,0.,.06)[i%3]}})
 return vals[:4] if fixture else vals
def prepare(stim,labels,training_hashes,fixture=False):
 m88=load88();m87=m88.load87();m86=m87.load86();seen={x['motion_sha256'] for x in labels}|set(training_hashes)|m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|authorize88();out=[];desc=[]
 for x in specs(fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series89 motion совпал с training/disclosed motion.')
  seen.add(h);item={**x,'motion_sha256':h};out.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'})
 return out,desc
def contact_sensor(q):
 q=np.asarray(q);return np.exp(-((q[..., [0,3]]-q[..., [1,4]])/.42)**2-((q[..., [2,5]]-.35)/.55)**2)
def decode_state(b,coeff):return np.clip(b.cosine_basis(49)@np.asarray(coeff).reshape(6,12).T,-LIMIT,LIMIT)
def control_targets(b,coeff,target):
 state=np.asarray(coeff).reshape(6,12);rng=np.random.default_rng(8904);perm=rng.permutation(6);shuffled=np.roll(state[perm],3,axis=1);lesion=state.copy();lesion[[0,1]]=0
 return {'normal':target,'zero_state':np.zeros_like(target),'shuffled_state':decode_state(b,shuffled),'open_loop':target,'shared_lesion':decode_state(b,lesion)}
def initial_state(profile,seed):
 rng=np.random.default_rng(seed);q=rng.normal(0,.004,6);dq=np.zeros(6);tilt=np.zeros(2)
 if profile=='pose_offset':q+=np.array([.10,-.08,.06,-.10,.08,-.06]);tilt[:]=[.07,-.05]
 elif profile=='velocity_offset':dq=np.array([.18,-.14,.12,-.18,.14,-.12]);tilt[:]=[-.05,.06]
 elif profile!='neutral':raise ValueError('Неизвестный initial profile.')
 return q,dq,tilt
def rollout(target,truth,seed,profile,closed_loop=True):
 """Bounded surrogate rollout; truth is used only after integration for evaluation."""
 target=np.clip(np.asarray(target,float),-LIMIT,LIMIT);truth=np.asarray(truth,float);q,dq,tilt=initial_state(profile,seed);dtilt=np.zeros(2);steps=(len(target)-1)*round(FRAME_DT/DT)+1;qs=[];torques=[];tilts=[];zs=[];saturated=0;disturb_at=int(.55*steps);disturb_end=disturb_at+round(.08/DT)
 for n in range(steps):
  phase=n*DT/FRAME_DT;i=min(int(phase),len(target)-2);a=min(phase-i,1.);des=(1-a)*target[i]+a*target[i+1];vel=(target[i+1]-target[i])/FRAME_DT;actual=contact_sensor(q);desired=contact_sensor(des)
  if closed_loop:u=1.65*(des-q)+.22*(vel-dq);u[[2,5]]+=.045*(desired-actual)
  else:u=.055*vel+.20*des
  if disturb_at<=n<disturb_end:u+=np.array([.11,-.09,.07,-.11,.09,-.07])
  saturated+=int(np.any(np.abs(u)>TORQUE_LIMIT));u=np.clip(u,-TORQUE_LIMIT,TORQUE_LIMIT);dq+=DT*((u-.045*dq)/.018);q+=DT*dq;hit=np.abs(q)>LIMIT
  if np.any(hit):q=np.clip(q,-LIMIT,LIMIT);dq[hit]*=-.08
  reaction=np.array([u[0]+u[1]+u[2]-u[3]-u[4]-u[5],u[0]-u[1]-u[3]+u[4]]);dtilt+=DT*(.025*reaction-2.8*tilt-.9*dtilt);tilt+=DT*dtilt;z=.40-.018*np.linalg.norm(tilt)-.002*np.sum(np.abs(q));qs.append(q.copy());torques.append(u.copy());tilts.append(tilt.copy());zs.append(z)
 idx=np.arange(len(target))*round(FRAME_DT/DT);sample=np.asarray(qs)[idx];tau=np.asarray(torques);vels=np.asarray([np.zeros(6),*np.diff(qs,axis=0)/DT]);errors=np.sqrt(np.mean((sample-target)**2,axis=1));disturb_frame=round(disturb_at*DT/FRAME_DT);recovery_frame=round(disturb_end*DT/FRAME_DT);baseline=float(np.mean(errors[max(0,disturb_frame-5):disturb_frame]));threshold=max(.08,1.5*baseline);after=np.where(errors[recovery_frame:]<=threshold)[0];recovery=float(after[0]*FRAME_DT) if len(after) else math.inf
 return {'angle_rmse_truth':float(np.sqrt(np.mean((sample-truth)**2))),'target_tracking_rmse':float(np.sqrt(np.mean((sample-target)**2))),'contact_mae_truth':float(np.mean(np.abs(contact_sensor(sample)-contact_sensor(truth)))),'completion_ratio':float(np.mean(np.linalg.norm(sample,axis=1)>.08)),'recovery_s':recovery,'recovered':recovery<=.40,'limit_violations':int(np.sum(np.abs(sample)>=LIMIT-1e-9)),'nan_count':int(np.size(sample)-np.isfinite(sample).sum()),'energy_abs_work':float(np.sum(np.abs(tau*vels))*DT),'torque_saturation_fraction':saturated/steps,'max_abs_torque':float(np.max(np.abs(tau))),'max_tilt_rad':float(np.max(np.abs(tilts))),'minimum_body_z':float(np.min(zs)),'proprioception_feedback':closed_loop,'contact_feedback':closed_loop}
def worker_init(bundle,s84v):
 global WORK88
 WORK88=load88();WORK88.worker_init(bundle,s84v)
def worker_task(arg):
 item,view=arg;row=WORK88.WORK87.worker_task((item,view));b=WORK88.WORK87.WORKER86.WORK['b'];shared=np.asarray(row.pop('_shared'));truth=np.asarray(row.pop('_execution'));row.pop('_private',None);coeff,target=b.compress_replay(shared);targets=control_targets(b,coeff,target);trials=[]
 for pi,profile in enumerate(PROFILES):
  controls={}
  for ci,name in enumerate(CONDITIONS):controls[name]=rollout(targets[name],truth,89000000+item['id']*1000+view['corner_id']*10+pi,profile,name!='open_loop')
  trials.append({'initial_profile':profile,'initial_seed':89000000+item['id']*1000+view['corner_id']*10+pi,'controls':controls})
 return {k:v for k,v in row.items() if k not in ('shared_observation','private_observation','execution_mode','zero','controls','population_sufficient')}|{'state_coefficients':72,'state_sha256':sha(np.asarray(coeff,dtype='<f8').tobytes()),'teacher_access_during_rollout':False,'rgb_access_during_rollout':False,'framewise_observer_buffer_access_during_rollout':False,'trials':trials}
def decision(rows,fixture=False):
 trials=[t for r in rows for t in r['trials']];normal=[t['controls']['normal'] for t in trials];required=len(trials) if fixture else math.ceil(.90*len(trials));safety=sum(x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=TORQUE_LIMIT+1e-12 and x['energy_abs_work']<=4. and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30 for x in normal);recovered=sum(x['recovered'] for x in normal);completed=sum(x['completion_ratio']>=.65 for x in normal);wins={name:sum(t['controls']['normal']['angle_rmse_truth']<t['controls'][name]['angle_rmse_truth'] for t in trials) for name in ('zero_state','shuffled_state','open_loop','shared_lesion')};contact_wins={name:sum(t['controls']['normal']['contact_mae_truth']<t['controls'][name]['contact_mae_truth'] for t in trials) for name in ('zero_state','shuffled_state','open_loop','shared_lesion')};means={name:{'angle_rmse_truth':float(np.mean([t['controls'][name]['angle_rmse_truth'] for t in trials])),'contact_mae_truth':float(np.mean([t['controls'][name]['contact_mae_truth'] for t in trials])),'energy_abs_work':float(np.mean([t['controls'][name]['energy_abs_work'] for t in trials]))} for name in CONDITIONS};angle_gate=all(wins[x]>=required for x in wins);contact_gate=sum(contact_wins[x]>=required for x in contact_wins)>=3;passed=safety==len(trials) and recovered>=required and completed>=required and angle_gate and contact_gate;return {'visual_cases':len(rows),'embodied_trials':len(trials),'required_trials':required,'normal_safety_passed':safety,'normal_recovered':recovered,'normal_completed':completed,'normal_angle_wins':wins,'normal_contact_wins':contact_wins,'means':means,'angle_gate_passed':angle_gate,'contact_gate_passed':contact_gate,'passed':passed}
def run(source_folder,workers,output_root=ROOT,fixture=False):
 authorize88();m88=load88();m87=m88.load87();m86=m87.load86();s85=m86.load85();workers,count=s85.worker_choice(workers);print('1/5 Проверяются actuator go88 и frozen84Z...',flush=True);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,fixture)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items,desc=prepare(stim,saved['labels'],training_hashes,fixture);held_views=views(fixture);tasks=[(x,v) for x in items for v in held_views];protocol={'schema':'closed-loop-embodied-validation-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner88_sha256':RUNNER88_SHA,'series88_extract_sha256':GO88_SHA,'selected_model_sha256':file_sha(paths[1]),'training_allowed':False,'motions':desc,'novel_views':held_views,'initial_profiles':list(PROFILES),'controls':list(CONDITIONS),'visual_cases':len(tasks),'embodied_trials':len(tasks)*len(PROFILES),'workers':count,'worker_choice':str(workers),'forbidden_rollout_access':['teacher trajectory','observation RGB','framewise observer prediction buffer'],'primary_rule':'all normal trials safe; >=90% recover and complete; normal angle beats every control in >=90%; normal contact beats >=3/4 controls in >=90%'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('closed_loop_embodied_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/5 Запускается {len(tasks)} visual cases, {len(tasks)*len(PROFILES)} embodied trials.',flush=True);rows=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(worker_task,tasks),1):rows.append(row);print(f'  Visual cases {n}/{len(tasks)}',flush=True) if n%len(held_views)==0 else None
 for row in rows:
  td=temp/f'test_{row["id"]:03d}'/f'view_{row["corner_id"]:03d}';td.mkdir(parents=True);save(td/'metrics.json',row)
 print('3/5 Проверяются angle, contact, stability, effort и recovery gates...',flush=True);primary=decision(rows,fixture);report={'schema':'closed-loop-embodied-validation-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':primary,'tests':rows,'source84z_primary':summary['primary'],'limitations':['Reduced six-joint actuator/support surrogate, not FlyGym, muscles or a complete free-standing fly body.','Contact objective is an engineered geometric proxy, not collision force.','Controls perturb the decoded engineered state; no natural vision or novel action invention.','Functional surrogate validation cannot establish biological mirror neurons.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 89: CLOSED-LOOP SURROGATE EMBODIED VALIDATION\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 if manifest(folder/'result')!=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))['files']:raise ValueError('Manifest series89 повреждён.')
 print('4/5 Source84Z неизменна.',flush=True);print('5/5 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия89: closed-loop validation');root.geometry('740x370+180+100');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия89: новые motions, views, initial poses и controls\n432 visual cases, 1296 embodied trials; frozen model84Z.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать завершённую папку84Z и запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 folder=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not folder:root.destroy();return
 root.withdraw();root.update();result=run(folder,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия89 завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-89.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 89: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
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
