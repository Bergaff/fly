#!/usr/bin/env python3
"""Series89B3: preregistered predicted-action conditional contact development."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;RUNNER_B2=HERE/'89b2_contact_aware_policy.py';RUNNER_B2_SHA='ec46c681834c4dc13c30d66f07616546809c2f3b29242e134b7f0a004d95f1a3';NO_GO_B2=HERE.parent/'reports'/'contact-aware-policy-89b2-user-summary-extract.json';NO_GO_B2_SHA='fc3de1d5264a08249d4cdb4a1db88b14d239737c6dc9b6fcb3e3a35d23122621';NO_GO_B2_SOURCE_SHA='6e3f9c224087bb2915034bf3017703a63afd8f2ad6e67966009a37faae2bb00b'
ROOT=Path('workspace/runs/ideas/i-observational/action-conditional-contact');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');PROFILES=('neutral','pose_offset','velocity_offset');CONDITIONS=('candidate','angle_only','common_contact','uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');WORK=None
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load_b2():
 if file_sha(RUNNER_B2)!=RUNNER_B2_SHA:raise ValueError('Закреплённый runner89B2 изменился.')
 s=importlib.util.spec_from_file_location('series89b3_source',RUNNER_B2);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize_b2():
 if file_sha(NO_GO_B2)!=NO_GO_B2_SHA:raise ValueError('Published series89B2 extract изменён.')
 d=json.loads(NO_GO_B2.read_text(encoding='utf8'));motions=d.get('protocol',{}).get('motions',[])
 if d.get('source_file_sha256')!=NO_GO_B2_SOURCE_SHA or d.get('reported_primary',{}).get('passed') is not False or [x.get('id') for x in motions]!=list(range(639,675)):raise ValueError('Series89B2 no-go identity не подтверждена.')
 return {x['motion_sha256'] for x in motions}
def specs(fixture=False):
 m86=load_b2().load_b().load88().load87().load86();out=[]
 for role,start,base in (('development',675,890700),('final',693,890800)):
  ident=start
  for rep in range(6):
   for ai,action in enumerate(ACTIONS):
    amp=(.70,.85,1.)[(rep+2*ai)%3];speed=(.62,.90,1.18)[(2*rep+ai)%3];seed=base+10*rep+ai;out.append({'role':role,'id':ident,'replicate':rep+1,'action':action,'conditional_seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 return [x for x in out if x['id'] in (675,676,677,693,694,695)] if fixture else out
def held_views(role,fixture=False):
 count=4 if fixture else (8 if role=='development' else 12);offset=501 if role=='development' else 521;vals=[]
 for i in range(count):vals.append({'corner_id':offset+i,'view':{'fov_deg':35.,'camera_side':(.17,.25,.33,.41,.43)[(2*i+3)%5],'camera_z':(.37,.46,.55,.58)[(3*i+1)%4],'body_x':(3.91,3.99,4.07,4.09)[(i+1)%4],'body_y':(-.05,.01,.045)[(i+2)%3]}})
 return vals
def prepare(stim,labels,training_hashes,fixture=False):
 m2=load_b2();m=m2.load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();seen={x['motion_sha256'] for x in labels}|set(training_hashes)|m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|m2.authorize_b()|authorize_b2();out=[];desc=[]
 for x in specs(fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series89B3 motion совпал с training/disclosed motion.')
  seen.add(h);item={**x,'motion_sha256':h};out.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'})
 return out,desc
def identity_features(target):
 q=np.asarray(target);v=np.diff(q,axis=0);return np.concatenate((q.mean(0),q.std(0),np.sqrt(np.mean(v*v,axis=0))))
def fit_identity(development):
 X=np.stack([identity_features(x['target']) for x in development]);mean=X.mean(0);scale=X.std(0);scale[scale<.02]=.02;Z=(X-mean)/scale;prototypes={a:Z[[x['action']==a for x in development]].mean(0) for a in ACTIONS};correct=sum(min(ACTIONS,key=lambda a:float(np.linalg.norm(z-prototypes[a])))==x['action'] for z,x in zip(Z,development));return {'mean':mean,'scale':scale,'prototypes':prototypes,'development_correct':correct,'development_cases':len(development)}
def predict_action(target,identity):
 z=(identity_features(target)-identity['mean'])/identity['scale'];return min(ACTIONS,key=lambda a:float(np.linalg.norm(z-identity['prototypes'][a])))
def select_lambda(m2,m,rows,angle,contact):
 truth=np.concatenate([x['truth'] for x in rows]);tc=m.contact_sensor(truth);candidates=[]
 for lam in m2.LAMBDAS:
  q=np.concatenate([m2.contact_policy(m,x['target'],angle,contact,lam) for x in rows]);ar=float(np.sqrt(np.mean((q-truth)**2)));cm=float(np.mean(np.abs(m.contact_sensor(q)-tc)));candidates.append({'lambda':lam,'angle_rmse':ar,'contact_mae':cm,'score':ar+.75*cm})
 eligible=[x for x in candidates if x['angle_rmse']<=1.05*angle['projected_rmse']];return candidates,min(eligible or candidates,key=lambda x:(x['score'],x['lambda']))
def fit_models(m2,m,development):
 angle=m.fit_calibrator(development);identity=fit_identity(development);common=m2.fit_contact_model(m,development,angle);common_candidates,common_selected=select_lambda(m2,m,development,angle,common);experts={};selections={}
 for action in ACTIONS:
  rows=[x for x in development if x['action']==action];model=m2.fit_contact_model(m,rows,angle);candidates,selected=select_lambda(m2,m,rows,angle,model);experts[action]=model;selections[action]={'candidates':candidates,'selected':selected}
 return angle,identity,common,common_selected,experts,selections,common_candidates
def worker_init(bundle,s84v):
 global WORK
 WORK=load_b2();WORK.worker_init(bundle,s84v)
def worker_visual(arg):return WORK.worker_visual(arg)
def policy_for(m2,m,target,angle,experts,selections,identity):
 action=predict_action(target,identity);model=experts[action];lam=selections[action]['selected']['lambda'];return m2.contact_policy(m,target,angle,model,lam),action
def controls_for(m2,m,b,coeff,target,angle,identity,common,common_lam,experts,selections):
 state=np.asarray(coeff).reshape(6,12);rng=np.random.default_rng(8909);sh=np.roll(state[rng.permutation(6)],5,axis=1);les=state.copy();les[[0,1]]=0;decode=lambda s:np.clip(b.cosine_basis(49)@s.T,-m.LIMIT,m.LIMIT);candidate,pred=policy_for(m2,m,target,angle,experts,selections,identity);sq=decode(sh);lq=decode(les);sp,_=policy_for(m2,m,sq,angle,experts,selections,identity);lp,_=policy_for(m2,m,lq,angle,experts,selections,identity)
 return {'candidate':candidate,'angle_only':m.calibrate(target,angle),'common_contact':m2.contact_policy(m,target,angle,common,common_lam),'uncalibrated':target,'zero_state':np.zeros_like(target),'shuffled_state':sp,'open_loop':candidate,'shared_lesion':lp},pred
def decision(rows,fixture=False):
 trials=[t for r in rows for t in r['trials']];candidate=[t['controls']['candidate'] for t in trials];required=len(trials) if fixture else math.ceil(.90*len(trials));identity_required=len(rows) if fixture else math.ceil(.90*len(rows));identity_correct=sum(r['predicted_action']==r['action'] for r in rows);m=load_b2().load_b();safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=m.TORQUE_LIMIT+1e-12 and x['energy_abs_work']<=4 and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30;safety=sum(safe(x) for x in candidate);recovered=sum(x['recovered'] for x in candidate);completed=sum(x['completion_ratio']>=.65 for x in candidate);an=('uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');cn=('angle_only','common_contact')+an;aw={n:sum(t['controls']['candidate']['angle_rmse_truth']<t['controls'][n]['angle_rmse_truth'] for t in trials) for n in an};cw={n:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][n]['contact_mae_truth'] for t in trials) for n in cn};means={n:{'angle_rmse_truth':float(np.mean([t['controls'][n]['angle_rmse_truth'] for t in trials])),'contact_mae_truth':float(np.mean([t['controls'][n]['contact_mae_truth'] for t in trials]))} for n in CONDITIONS};angle=all(aw[n]>=required for n in an) and means['candidate']['angle_rmse_truth']<=1.05*means['angle_only']['angle_rmse_truth'];contact=cw['angle_only']>=required and cw['common_contact']>=required and sum(cw[n]>=required for n in cn)>=5;passed=identity_correct>=identity_required and safety==len(trials) and recovered>=required and completed>=required and angle and contact;return {'final_visual_cases':len(rows),'final_trials':len(trials),'required_trials':required,'identity_correct':identity_correct,'identity_required':identity_required,'candidate_safety_passed':safety,'candidate_recovered':recovered,'candidate_completed':completed,'candidate_angle_wins':aw,'candidate_contact_wins':cw,'means':means,'angle_gate_passed':angle,'contact_gate_passed':contact,'passed':passed}
def run(source_folder,workers,output_root=ROOT,fixture=False):
 authorize_b2();m2=load_b2();m=m2.load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();s85=m86.load85();workers,count=s85.worker_choice(workers);print('1/6 Проверяются no-go89B2 и frozen84Z...',flush=True);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,fixture)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items,desc=prepare(stim,saved['labels'],training_hashes,fixture);dev=[x for x in items if x['role']=='development'];final=[x for x in items if x['role']=='final'];dv=held_views('development',fixture);fv=held_views('final',fixture);tasks=[(x,v) for x in dev for v in dv]+[(x,v) for x in final for v in fv];protocol={'schema':'action-conditional-contact-development-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner89b2_sha256':RUNNER_B2_SHA,'series89b2_nogo_extract_sha256':NO_GO_B2_SHA,'selected_model_sha256':file_sha(paths[1]),'development_training_allowed':True,'source84z_training_allowed':False,'motions':desc,'development_views':dv,'final_views':fv,'initial_profiles':list(PROFILES),'controls':list(CONDITIONS),'inference_action_source':'nearest development prototype from target summary; no truth action label','final_used_for_fit':False,'workers':count,'worker_choice':str(workers),'primary_rule':'identity>=90%; all safe; recovery/complete>=90%; angle controls>=90% and <=1.05 angle-only; contact beats angle-only and common>=90%, and >=5/7 controls'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('action_conditional_contact_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/6 Запускается {len(tasks)} visual cases, workers={count}.',flush=True);visual=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(worker_visual,tasks),1):visual.append(row);print(f'  Visual cases {n}/{len(tasks)}',flush=True) if n%12==0 else None
 print('3/6 Fit identity и action-conditional contact models только development...',flush=True);development=[{'target':r['_target'],'truth':r['_truth'],'action':r['action']} for r in visual if r['role']=='development'];angle,identity,common,common_selected,experts,selections,common_candidates=fit_models(m2,m,development);np.savez_compressed(temp/'action_contact_model.npz',angle_mean=angle['mean'],angle_scale=angle['scale'],angle_weights=angle['weights'],identity_mean=identity['mean'],identity_scale=identity['scale'],identity_prototypes=np.stack([identity['prototypes'][a] for a in ACTIONS]),common_contact=common['weights'],expert_contacts=np.stack([experts[a]['weights'] for a in ACTIONS]),expert_lambdas=np.array([selections[a]['selected']['lambda'] for a in ACTIONS]));model_meta={'angle':{k:v for k,v in angle.items() if k not in ('mean','scale','weights')},'identity_development_correct':identity['development_correct'],'identity_development_cases':identity['development_cases'],'common_selected':common_selected,'common_candidates':common_candidates,'expert_selections':selections,'sha256':file_sha(temp/'action_contact_model.npz')};print('4/6 Untouched final controls...',flush=True);rows=[]
 for row in [r for r in visual if r['role']=='final']:
  targets,pred=controls_for(m2,m,b,row['_coeff'],row['_target'],angle,identity,common,common_selected['lambda'],experts,selections);trials=[]
  for pi,profile in enumerate(PROFILES):
   seed=892000000+row['id']*1000+row['corner_id']*10+pi;controls={}
   for name in CONDITIONS:controls[name]=m.rollout(targets[name],row['_truth'],seed,profile,name!='open_loop',name not in ('uncalibrated','zero_state'))
   trials.append({'initial_profile':profile,'initial_seed':seed,'controls':controls})
  clean={k:v for k,v in row.items() if not k.startswith('_')};clean.update({'predicted_action':pred,'trials':trials});rows.append(clean);td=temp/f'test_{row["id"]:03d}'/f'view_{row["corner_id"]:03d}';td.mkdir(parents=True);save(td/'metrics.json',clean)
 print('5/6 Проверяются action identity и contact final gates...',flush=True);primary=decision(rows,fixture);report={'schema':'action-conditional-contact-development-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'model':model_meta,'primary':primary,'tests':rows,'source84z_primary':summary['primary'],'limitations':['Action experts use synthetic development labels; inference uses predicted, not true, action.','Reduced support surrogate and geometric contact proxy, not collision force.','Go only authorizes frozen89C replication; series90 remains blocked.','No natural vision, complete body, muscles or biological neurons.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 89B3: ACTION-CONDITIONAL CONTACT\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 if manifest(folder/'result')!=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))['files']:raise ValueError('Manifest series89B3 повреждён.')
 print('6/6 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия89B3: action-conditional contact');root.geometry('780x400+160+80');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия89B3: predicted-action contact experts + untouched final\n360 visual cases; frozen source84Z.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать завершённую папку84Z и запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 folder=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not folder:root.destroy();return
 root.withdraw();root.update();result=run(folder,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия89B3 завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-89B3.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 89B3: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
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
