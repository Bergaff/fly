#!/usr/bin/env python3
"""Series89B2: preregistered contact-aware bounded-policy development."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;RUNNER_B=HERE/'89b_bounded_policy_calibration.py';RUNNER_B_SHA='99e0ccd01e9ae0ba27d61c4391e6cdff675793c8b10cbea41a4237a5b398a920';NO_GO_B=HERE.parent/'reports'/'bounded-policy-calibration-89b-user-summary-extract.json';NO_GO_B_SHA='ad8405c5bab7511bafaa0c0fbfee44cfa3c357cdcabdb70cca8e196a01ab75e8';NO_GO_B_SOURCE_SHA='f4351c05599a059090310452857887da096fbff79699c407ec4bf1c8a8028664'
ROOT=Path('workspace/runs/ideas/i-observational/contact-aware-policy');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');PROFILES=('neutral','pose_offset','velocity_offset');CONDITIONS=('candidate','angle_only','uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');CONTACT_RIDGE=.08;LAMBDAS=(0.,.25,.5,1.,2.,4.);WORKB=None
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load_b():
 if file_sha(RUNNER_B)!=RUNNER_B_SHA:raise ValueError('Закреплённый runner89B изменился.')
 s=importlib.util.spec_from_file_location('series89b2_source',RUNNER_B);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize_b():
 if file_sha(NO_GO_B)!=NO_GO_B_SHA:raise ValueError('Published series89B extract изменён.')
 d=json.loads(NO_GO_B.read_text(encoding='utf8'));motions=d.get('protocol',{}).get('motions',[])
 if d.get('source_file_sha256')!=NO_GO_B_SOURCE_SHA or d.get('reported_primary',{}).get('passed') is not False or [x.get('id') for x in motions]!=list(range(603,639)):raise ValueError('Series89B no-go identity не подтверждена.')
 return {x['motion_sha256'] for x in motions}
def specs(fixture=False):
 m86=load_b().load88().load87().load86();out=[]
 for role,start,base in (('development',639,890500),('final',657,890600)):
  ident=start
  for rep in range(6):
   for ai,action in enumerate(ACTIONS):
    amp=(.72,.86,1.)[(2*rep+ai)%3];speed=(.64,.92,1.20)[(rep+ai)%3];seed=base+10*rep+ai;out.append({'role':role,'id':ident,'replicate':rep+1,'action':action,'contact_seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 return [x for x in out if x['id'] in (639,640,641,657,658,659)] if fixture else out
def held_views(role,fixture=False):
 count=4 if fixture else (8 if role=='development' else 12);offset=401 if role=='development' else 421;vals=[]
 for i in range(count):vals.append({'corner_id':offset+i,'view':{'fov_deg':35.,'camera_side':(.15,.23,.31,.39,.45)[(3*i+1)%5],'camera_z':(.35,.44,.53,.60)[(2*i+1)%4],'body_x':(3.89,3.97,4.05,4.11)[(i+2)%4],'body_y':(-.055,.005,.05)[(2*i+1)%3]}})
 return vals
def prepare(stim,labels,training_hashes,fixture=False):
 m=load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();seen={x['motion_sha256'] for x in labels}|set(training_hashes)|m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|authorize_b();out=[];desc=[]
 for x in specs(fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series89B2 motion совпал с training/disclosed motion.')
  seen.add(h);item={**x,'motion_sha256':h};out.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'})
 return out,desc
def standardized_features(m,target,angle_model):
 X=m.policy_features(target);X[:,:12]=(X[:,:12]-angle_model['mean'])/angle_model['scale'];return X
def fit_contact_model(m,development,angle_model):
 X=np.concatenate([standardized_features(m,x['target'],angle_model) for x in development]);Y=np.concatenate([m.contact_sensor(x['truth']) for x in development]);reg=np.eye(13)*CONTACT_RIDGE;reg[-1,-1]=0;weights=np.linalg.solve(X.T@X+reg,X.T@Y);return {'weights':weights,'ridge':CONTACT_RIDGE,'fit_mae':float(np.mean(np.abs(np.clip(X@weights,.02,.98)-Y)))}
def contact_adjust(m,base,desired,lam):
 q=np.array(base,copy=True);desired=np.clip(np.asarray(desired),.02,.98)
 for _ in range(12):
  c=m.contact_sensor(q);grad=2*(q-base)
  for side,(p,mid,dist) in enumerate(((0,1,2),(3,4,5))):
   delta=q[:,p]-q[:,mid];end=q[:,dist]-.35;common=2*lam*(c[:,side]-desired[:,side]);dc_p=c[:,side]*(-2*delta/.42**2);dc_d=c[:,side]*(-2*end/.55**2);grad[:,p]+=common*dc_p;grad[:,mid]-=common*dc_p;grad[:,dist]+=common*dc_d
  q-=.02*grad
 q=np.clip(q,-m.SOFT_LIMIT,m.SOFT_LIMIT)
 for i in range(1,len(q)):q[i]=q[i-1]+np.clip(q[i]-q[i-1],-.11,.11)
 return q
def contact_policy(m,target,angle_model,contact_model,lam):
 base=m.calibrate(target,angle_model);desired=np.clip(standardized_features(m,target,angle_model)@contact_model['weights'],.02,.98);return contact_adjust(m,base,desired,lam)
def fit_models(m,development):
 angle=m.fit_calibrator(development);contact=fit_contact_model(m,development,angle);truth=np.concatenate([x['truth'] for x in development]);truth_contact=m.contact_sensor(truth);candidates=[]
 for lam in LAMBDAS:
  q=np.concatenate([contact_policy(m,x['target'],angle,contact,lam) for x in development]);ar=float(np.sqrt(np.mean((q-truth)**2)));cm=float(np.mean(np.abs(m.contact_sensor(q)-truth_contact)));score=ar+.75*cm;candidates.append({'lambda':lam,'angle_rmse':ar,'contact_mae':cm,'score':score})
 eligible=[x for x in candidates if x['angle_rmse']<=1.05*angle['projected_rmse']];selected=min(eligible or candidates,key=lambda x:(x['score'],x['lambda']));return angle,contact,candidates,selected
def worker_init(bundle,s84v):
 global WORKB
 WORKB=load_b();WORKB.worker_init(bundle,s84v)
def worker_visual(arg):return WORKB.worker_visual(arg)
def controls_for(m,b,coeff,target,angle,contact,lam):
 state=np.asarray(coeff).reshape(6,12);rng=np.random.default_rng(8907);sh=np.roll(state[rng.permutation(6)],4,axis=1);les=state.copy();les[[0,1]]=0;decode=lambda s:np.clip(b.cosine_basis(49)@s.T,-m.LIMIT,m.LIMIT);candidate=contact_policy(m,target,angle,contact,lam)
 return {'candidate':candidate,'angle_only':m.calibrate(target,angle),'uncalibrated':target,'zero_state':np.zeros_like(target),'shuffled_state':contact_policy(m,decode(sh),angle,contact,lam),'open_loop':candidate,'shared_lesion':contact_policy(m,decode(les),angle,contact,lam)}
def decision(rows,fixture=False):
 trials=[t for r in rows for t in r['trials']];candidate=[t['controls']['candidate'] for t in trials];required=len(trials) if fixture else math.ceil(.90*len(trials));m=load_b();safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=m.TORQUE_LIMIT+1e-12 and x['energy_abs_work']<=4 and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30;safety=sum(safe(x) for x in candidate);recovered=sum(x['recovered'] for x in candidate);completed=sum(x['completion_ratio']>=.65 for x in candidate);angle_names=('uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');contact_names=('angle_only',)+angle_names;angle={n:sum(t['controls']['candidate']['angle_rmse_truth']<t['controls'][n]['angle_rmse_truth'] for t in trials) for n in angle_names};contact={n:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][n]['contact_mae_truth'] for t in trials) for n in contact_names};means={n:{'angle_rmse_truth':float(np.mean([t['controls'][n]['angle_rmse_truth'] for t in trials])),'contact_mae_truth':float(np.mean([t['controls'][n]['contact_mae_truth'] for t in trials]))} for n in CONDITIONS};angle_gate=all(angle[n]>=required for n in angle_names) and means['candidate']['angle_rmse_truth']<=1.05*means['angle_only']['angle_rmse_truth'];contact_gate=contact['angle_only']>=required and sum(contact[n]>=required for n in contact_names)>=4;passed=safety==len(trials) and recovered>=required and completed>=required and angle_gate and contact_gate;return {'final_visual_cases':len(rows),'final_trials':len(trials),'required_trials':required,'candidate_safety_passed':safety,'candidate_recovered':recovered,'candidate_completed':completed,'candidate_angle_wins':angle,'candidate_contact_wins':contact,'means':means,'angle_gate_passed':angle_gate,'contact_gate_passed':contact_gate,'passed':passed}
def run(source_folder,workers,output_root=ROOT,fixture=False):
 authorize_b();m=load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();s85=m86.load85();workers,count=s85.worker_choice(workers);print('1/6 Проверяются no-go89B и frozen84Z...',flush=True);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,fixture)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items,desc=prepare(stim,saved['labels'],training_hashes,fixture);dev=[x for x in items if x['role']=='development'];final=[x for x in items if x['role']=='final'];dv=held_views('development',fixture);fv=held_views('final',fixture);tasks=[(x,v) for x in dev for v in dv]+[(x,v) for x in final for v in fv];protocol={'schema':'contact-aware-policy-development-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner89b_sha256':RUNNER_B_SHA,'series89b_nogo_extract_sha256':NO_GO_B_SHA,'selected_model_sha256':file_sha(paths[1]),'development_training_allowed':True,'source84z_training_allowed':False,'motions':desc,'development_views':dv,'final_views':fv,'initial_profiles':list(PROFILES),'controls':list(CONDITIONS),'lambda_candidates':list(LAMBDAS),'contact_ridge':CONTACT_RIDGE,'selection_score':'development angle_rmse +0.75 contact_mae; angle<=1.05 angle-only projected','final_used_for_fit':False,'workers':count,'worker_choice':str(workers),'primary_rule':'all safe; >=90% recover/complete and angle wins every non-angle-only control; candidate angle<=1.05 angle-only; contact beats angle-only>=90% and >=4/6 controls'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('contact_aware_policy_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/6 Запускается {len(tasks)} visual cases, workers={count}.',flush=True);visual=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(worker_visual,tasks),1):visual.append(row);print(f'  Visual cases {n}/{len(tasks)}',flush=True) if n%12==0 else None
 print('3/6 Fit angle+contact models только development...',flush=True);development=[{'target':r['_target'],'truth':r['_truth']} for r in visual if r['role']=='development'];angle,contact,candidates,selected=fit_models(m,development);np.savez_compressed(temp/'contact_policy_model.npz',mean=angle['mean'],scale=angle['scale'],angle_weights=angle['weights'],contact_weights=contact['weights'],selected_lambda=np.array([selected['lambda']]));model_meta={'angle':{k:v for k,v in angle.items() if k not in ('mean','scale','weights')},'contact_fit_mae':contact['fit_mae'],'lambda_candidates':candidates,'selected':selected,'sha256':file_sha(temp/'contact_policy_model.npz')};print('4/6 Untouched final controls...',flush=True);rows=[]
 for row in [r for r in visual if r['role']=='final']:
  targets=controls_for(m,b,row['_coeff'],row['_target'],angle,contact,selected['lambda']);trials=[]
  for pi,profile in enumerate(PROFILES):
   seed=891000000+row['id']*1000+row['corner_id']*10+pi;controls={}
   for name in CONDITIONS:controls[name]=m.rollout(targets[name],row['_truth'],seed,profile,name!='open_loop',name not in ('uncalibrated','zero_state'))
   trials.append({'initial_profile':profile,'initial_seed':seed,'controls':controls})
  clean={k:v for k,v in row.items() if not k.startswith('_')};clean['trials']=trials;rows.append(clean);td=temp/f'test_{row["id"]:03d}'/f'view_{row["corner_id"]:03d}';td.mkdir(parents=True);save(td/'metrics.json',clean)
 print('5/6 Проверяются contact-aware final gates...',flush=True);primary=decision(rows,fixture);report={'schema':'contact-aware-policy-development-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'model':model_meta,'primary':primary,'tests':rows,'source84z_primary':summary['primary'],'limitations':['Supervised synthetic contact and angle truth development, not autonomous learning.','Reduced support surrogate and geometric contact proxy, not physical collision force.','Go only authorizes separate frozen89C replication; series90 remains blocked.','No natural vision, complete body, muscles or biological neurons.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 89B2: CONTACT-AWARE POLICY\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 if manifest(folder/'result')!=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))['files']:raise ValueError('Manifest series89B2 повреждён.')
 print('6/6 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия89B2: contact-aware policy');root.geometry('770x390+165+85');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия89B2: contact-aware development + untouched final\n360 visual cases; frozen source84Z.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать завершённую папку84Z и запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 folder=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not folder:root.destroy();return
 root.withdraw();root.update();result=run(folder,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия89B2 завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-89B2.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 89B2: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
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
