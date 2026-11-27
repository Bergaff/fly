#!/usr/bin/env python3
"""Series89B4: preregistered head-aware soft action-mixture contact development."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;RUNNER_B3=HERE/'89b3_action_conditional_contact.py';RUNNER_B3_SHA='b6252829d81ea92c106554f8413cae6b842868c06f69b18fdcd99e5d512ef259';RUNNER_B2=HERE/'89b2_contact_aware_policy.py';RUNNER_B2_SHA='ec46c681834c4dc13c30d66f07616546809c2f3b29242e134b7f0a004d95f1a3';MODEL84Z_SHA='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0';NO_GO_B3=HERE.parent/'reports'/'action-conditional-contact-89b3-user-summary-extract.json';NO_GO_B3_SHA='99e07b32e0bd6f9bf7fe0c1ad7761db4973f74d9fd4c21d9c37ba009c4164bae';NO_GO_B3_SOURCE_SHA='dd16e35af84f5fe40d5319a9cc2720637639d51f7ac1c442af06cfd632bcccfb'
ROOT=Path('workspace/runs/ideas/i-observational/head-identity-contact');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');PROFILES=('neutral','pose_offset','velocity_offset');CONDITIONS=('candidate','angle_only','common_contact','hard_expert','oracle_expert','uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');IDENTITY_RIDGES=(.01,.1,1.,10.);TEMPERATURES=(.25,.5,1.,2.);EXPERT_LAMBDAS=(0.,.25,.5,1.,2.,4.,8.);WORK=None
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load_b3():
 if file_sha(RUNNER_B3)!=RUNNER_B3_SHA or file_sha(RUNNER_B2)!=RUNNER_B2_SHA:raise ValueError('Закреплённый runner89B3/89B2 изменился.')
 s=importlib.util.spec_from_file_location('series89b4_source',RUNNER_B3);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize_b3():
 if file_sha(NO_GO_B3)!=NO_GO_B3_SHA:raise ValueError('Published series89B3 extract изменён.')
 d=json.loads(NO_GO_B3.read_text(encoding='utf8'));motions=d.get('protocol',{}).get('motions',[])
 if d.get('source_file_sha256')!=NO_GO_B3_SOURCE_SHA or d.get('reported_primary',{}).get('passed') is not False or [x.get('id') for x in motions]!=list(range(675,711)):raise ValueError('Series89B3 no-go identity не подтверждена.')
 return {x['motion_sha256'] for x in motions}
def specs(fixture=False):
 m86=load_b3().load_b2().load_b().load88().load87().load86();out=[]
 for role,start,base in (('development',711,890900),('final',729,891000)):
  ident=start
  for rep in range(6):
   for ai,action in enumerate(ACTIONS):
    amp=(.68,.84,1.)[(rep+ai)%3];speed=(.60,.88,1.16)[(rep+2*ai)%3];seed=base+10*rep+ai;out.append({'role':role,'id':ident,'replicate':rep+1,'action':action,'head_seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 return [x for x in out if x['id'] in (711,712,713,729,730,731)] if fixture else out
def held_views(role,fixture=False):
 count=4 if fixture else (8 if role=='development' else 12);offset=601 if role=='development' else 621;vals=[]
 for i in range(count):vals.append({'corner_id':offset+i,'view':{'fov_deg':35.,'camera_side':(.18,.26,.34,.40,.42)[(i+3)%5],'camera_z':(.38,.47,.56,.57)[(2*i+1)%4],'body_x':(3.92,4.,4.08,4.085)[(3*i+2)%4],'body_y':(-.04,.02,.04)[(i+1)%3]}})
 return vals
def prepare(stim,labels,training_hashes,fixture=False):
 m3=load_b3();m2=m3.load_b2();m=m2.load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();seen={x['motion_sha256'] for x in labels}|set(training_hashes)|m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|m2.authorize_b()|m3.authorize_b2()|authorize_b3();out=[];desc=[]
 for x in specs(fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series89B4 motion совпал с training/disclosed motion.')
  seen.add(h);item={**x,'motion_sha256':h};out.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'})
 return out,desc
def identity_features(target):
 q=np.asarray(target);v=np.diff(q,axis=0);return np.concatenate((q.mean(0),q.std(0),np.sqrt(np.mean(v*v,axis=0)),q.min(0),q.max(0)))
def fit_identity(rows,ridge):
 X=np.stack([identity_features(x['target']) for x in rows]);mean=X.mean(0);scale=X.std(0);scale[scale<.02]=.02;Z=np.column_stack(((X-mean)/scale,np.ones(len(X))));Y=np.zeros((len(rows),3))
 for i,x in enumerate(rows):Y[i,ACTIONS.index(x['action'])]=1
 reg=np.eye(31)*ridge;reg[-1,-1]=0;weights=np.linalg.solve(Z.T@Z+reg,Z.T@Y);return {'mean':mean,'scale':scale,'weights':weights,'ridge':ridge}
def action_probabilities(target,model,temperature):
 z=np.r_[((identity_features(target)-model['mean'])/model['scale']),1.]@model['weights'];z=(z-np.max(z))/temperature;p=np.exp(z);return p/p.sum()
def select_identity(rows):
 groups=sorted({x['id'] for x in rows});scores=[]
 for ridge in IDENTITY_RIDGES:
  correct=0
  for ident in groups:
   train=[x for x in rows if x['id']!=ident];test=[x for x in rows if x['id']==ident];model=fit_identity(train,ridge)
   correct+=sum(ACTIONS[int(np.argmax(action_probabilities(x['target'],model,1.)))]==x['action'] for x in test)
  scores.append({'ridge':ridge,'grouped_cv_correct':correct,'cases':len(rows)})
 selected=max(scores,key=lambda x:(x['grouped_cv_correct'],-x['ridge']));return fit_identity(rows,selected['ridge']),scores,selected
def select_lambda(m2,m,rows,angle,contact,weight):
 truth=np.concatenate([x['truth'] for x in rows]);tc=m.contact_sensor(truth);cand=[]
 for lam in EXPERT_LAMBDAS:
  q=np.concatenate([m2.contact_policy(m,x['target'],angle,contact,lam) for x in rows]);ar=float(np.sqrt(np.mean((q-truth)**2)));cm=float(np.mean(np.abs(m.contact_sensor(q)-tc)));cand.append({'lambda':lam,'angle_rmse':ar,'contact_mae':cm,'score':ar+weight*cm})
 eligible=[x for x in cand if x['angle_rmse']<=1.05*angle['projected_rmse']];return cand,min(eligible or cand,key=lambda x:(x['score'],x['lambda']))
def expert_policies(m2,m,target,angle,experts,selections):return [m2.contact_policy(m,target,angle,experts[a],selections[a]['selected']['lambda']) for a in ACTIONS]
def mixture_policy(target,identity,temp,policies):
 probs=action_probabilities(target,identity,temp);return sum(probs[i]*policies[i] for i in range(3)),probs
def fit_models(m3,m2,m,development):
 angle=m.fit_calibrator(development);identity,cv,identity_selected=select_identity(development);common=m2.fit_contact_model(m,development,angle);common_candidates,common_selected=select_lambda(m2,m,development,angle,common,.75);experts={};selections={}
 for action in ACTIONS:
  rows=[x for x in development if x['action']==action];model=m2.fit_contact_model(m,rows,angle);weight=1.5 if action=='head_directed_grooming' else .75;candidates,selected=select_lambda(m2,m,rows,angle,model,weight);experts[action]=model;selections[action]={'contact_weight':weight,'candidates':candidates,'selected':selected}
 truth=np.concatenate([x['truth'] for x in development]);tc=m.contact_sensor(truth);temps=[]
 for temp in TEMPERATURES:
  q=[]
  for x in development:
   mix,_=mixture_policy(x['target'],identity,temp,expert_policies(m2,m,x['target'],angle,experts,selections));q.append(mix)
  q=np.concatenate(q);ar=float(np.sqrt(np.mean((q-truth)**2)));cm=float(np.mean(np.abs(m.contact_sensor(q)-tc)));temps.append({'temperature':temp,'angle_rmse':ar,'contact_mae':cm,'score':ar+cm})
 eligible=[x for x in temps if x['angle_rmse']<=1.05*angle['projected_rmse']];temp_selected=min(eligible or temps,key=lambda x:(x['score'],x['temperature']));return angle,identity,cv,identity_selected,common,common_selected,experts,selections,temps,temp_selected,common_candidates
def worker_init(bundle,s84v):
 global WORK
 WORK=load_b3();WORK.worker_init(bundle,s84v)
def worker_visual(arg):return WORK.worker_visual(arg)
def inferred_policies(m3,m2,m,target,angle,identity,temp,common,common_lam,experts,selections):
 policies=expert_policies(m2,m,target,angle,experts,selections);candidate,probs=mixture_policy(target,identity,temp,policies);hard=policies[int(np.argmax(probs))];common_q=m2.contact_policy(m,target,angle,common,common_lam);return candidate,hard,common_q,probs
def controls_for(m3,m2,m,b,coeff,target,angle,identity,temp,common,common_lam,experts,selections):
 candidate,hard,common_q,probs=inferred_policies(m3,m2,m,target,angle,identity,temp,common,common_lam,experts,selections);state=np.asarray(coeff).reshape(6,12);rng=np.random.default_rng(8911);sh=np.roll(state[rng.permutation(6)],6,axis=1);les=state.copy();les[[0,1]]=0;decode=lambda s:np.clip(b.cosine_basis(49)@s.T,-m.LIMIT,m.LIMIT);sp,_,_,_=inferred_policies(m3,m2,m,decode(sh),angle,identity,temp,common,common_lam,experts,selections);lp,_,_,_=inferred_policies(m3,m2,m,decode(les),angle,identity,temp,common,common_lam,experts,selections)
 return {'candidate':candidate,'angle_only':m.calibrate(target,angle),'common_contact':common_q,'hard_expert':hard,'uncalibrated':target,'zero_state':np.zeros_like(target),'shuffled_state':sp,'open_loop':candidate,'shared_lesion':lp},probs
def decision(rows,fixture=False):
 trials=[t for r in rows for t in r['trials']];candidate=[t['controls']['candidate'] for t in trials];required=len(trials) if fixture else math.ceil(.90*len(trials));identity_required=len(rows) if fixture else math.ceil(.90*len(rows));identity_correct=sum(r['predicted_action']==r['action'] for r in rows);m=load_b3().load_b2().load_b();safe=lambda x:x['nan_count']==0 and x['limit_violations']==0 and x['max_abs_torque']<=m.TORQUE_LIMIT+1e-12 and x['energy_abs_work']<=4 and x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30;safety=sum(safe(x) for x in candidate);recovered=sum(x['recovered'] for x in candidate);completed=sum(x['completion_ratio']>=.65 for x in candidate);an=('uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');cn=('angle_only','common_contact','hard_expert','oracle_expert')+an;aw={n:sum(t['controls']['candidate']['angle_rmse_truth']<t['controls'][n]['angle_rmse_truth'] for t in trials) for n in an};cw={n:sum(t['controls']['candidate']['contact_mae_truth']<t['controls'][n]['contact_mae_truth'] for t in trials) for n in cn};means={n:{'angle_rmse_truth':float(np.mean([t['controls'][n]['angle_rmse_truth'] for t in trials])),'contact_mae_truth':float(np.mean([t['controls'][n]['contact_mae_truth'] for t in trials]))} for n in CONDITIONS};angle=all(aw[n]>=required for n in an) and means['candidate']['angle_rmse_truth']<=1.05*means['angle_only']['angle_rmse_truth'];contact=cw['angle_only']>=required and cw['common_contact']>=required and sum(cw[n]>=required for n in cn)>=6 and means['candidate']['contact_mae_truth']<=means['hard_expert']['contact_mae_truth'] and means['candidate']['contact_mae_truth']<=means['oracle_expert']['contact_mae_truth']+.02;passed=identity_correct>=identity_required and safety==len(trials) and recovered>=required and completed>=required and angle and contact;return {'final_visual_cases':len(rows),'final_trials':len(trials),'required_trials':required,'identity_correct':identity_correct,'identity_required':identity_required,'candidate_safety_passed':safety,'candidate_recovered':recovered,'candidate_completed':completed,'candidate_angle_wins':aw,'candidate_contact_wins':cw,'means':means,'angle_gate_passed':angle,'contact_gate_passed':contact,'passed':passed}
def run(source_folder,workers,output_root=ROOT,fixture=False):
 authorize_b3();m3=load_b3();m2=m3.load_b2();m=m2.load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();s85=m86.load85();workers,count=s85.worker_choice(workers);print('1/6 Проверяются no-go89B3 и frozen84Z...',flush=True);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,fixture)
 if not fixture and file_sha(paths[1])!=MODEL84Z_SHA:raise ValueError('Frozen model84Z identity изменена.')
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items,desc=prepare(stim,saved['labels'],training_hashes,fixture);dev=[x for x in items if x['role']=='development'];final=[x for x in items if x['role']=='final'];dv=held_views('development',fixture);fv=held_views('final',fixture);tasks=[(x,v) for x in dev for v in dv]+[(x,v) for x in final for v in fv];protocol={'schema':'head-identity-contact-development-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner89b3_sha256':RUNNER_B3_SHA,'runner89b2_sha256':RUNNER_B2_SHA,'series89b3_nogo_extract_sha256':NO_GO_B3_SHA,'series89b3_upload_sha256':NO_GO_B3_SOURCE_SHA,'frozen84z_model_sha256':MODEL84Z_SHA,'selected_model_sha256':file_sha(paths[1]),'development_training_allowed':True,'source84z_training_allowed':False,'motions':desc,'development_views':dv,'final_views':fv,'initial_profiles':list(PROFILES),'controls':list(CONDITIONS),'identity_ridges':list(IDENTITY_RIDGES),'temperatures':list(TEMPERATURES),'expert_lambdas':list(EXPERT_LAMBDAS),'candidate_inference_uses_truth_action':False,'oracle_control_uses_truth_action':True,'final_used_for_fit':False,'workers':count,'worker_choice':str(workers),'primary_rule':'identity>=90%; all safe; recover/complete>=90%; angle; contact beats angle-only/common>=90% and >=6/9; candidate mean<=hard and <=oracle+0.02'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('head_identity_contact_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/6 Запускается {len(tasks)} visual cases, workers={count}.',flush=True);visual=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(worker_visual,tasks),1):visual.append(row);print(f'  Visual cases {n}/{len(tasks)}',flush=True) if n%12==0 else None
 print('3/6 Grouped-CV identity, head-weighted experts и temperature selection...',flush=True);development=[{'id':r['id'],'target':r['_target'],'truth':r['_truth'],'action':r['action']} for r in visual if r['role']=='development'];angle,identity,cv,identity_selected,common,common_selected,experts,selections,temps,temp_selected,common_candidates=fit_models(m3,m2,m,development);np.savez_compressed(temp/'head_contact_model.npz',angle_mean=angle['mean'],angle_scale=angle['scale'],angle_weights=angle['weights'],identity_mean=identity['mean'],identity_scale=identity['scale'],identity_weights=identity['weights'],common_contact=common['weights'],expert_contacts=np.stack([experts[a]['weights'] for a in ACTIONS]),expert_lambdas=np.array([selections[a]['selected']['lambda'] for a in ACTIONS]),temperature=np.array([temp_selected['temperature']]));model_meta={'angle':{k:v for k,v in angle.items() if k not in ('mean','scale','weights')},'identity_cv':cv,'identity_selected':identity_selected,'common_selected':common_selected,'common_candidates':common_candidates,'expert_selections':selections,'temperature_candidates':temps,'temperature_selected':temp_selected,'sha256':file_sha(temp/'head_contact_model.npz')};print('4/6 Untouched final controls...',flush=True);rows=[]
 for row in [r for r in visual if r['role']=='final']:
  targets,probs=controls_for(m3,m2,m,b,row['_coeff'],row['_target'],angle,identity,temp_selected['temperature'],common,common_selected['lambda'],experts,selections);targets['oracle_expert']=expert_policies(m2,m,row['_target'],angle,experts,selections)[ACTIONS.index(row['action'])];trials=[]
  for pi,profile in enumerate(PROFILES):
   seed=893000000+row['id']*1000+row['corner_id']*10+pi;controls={}
   for name in CONDITIONS:controls[name]=m.rollout(targets[name],row['_truth'],seed,profile,name!='open_loop',name not in ('uncalibrated','zero_state'))
   trials.append({'initial_profile':profile,'initial_seed':seed,'controls':controls})
  pred=ACTIONS[int(np.argmax(probs))];clean={k:v for k,v in row.items() if not k.startswith('_')};clean.update({'predicted_action':pred,'action_probabilities':{a:float(probs[i]) for i,a in enumerate(ACTIONS)},'oracle_control_only_uses_truth_action':True,'trials':trials});rows.append(clean);td=temp/f'test_{row["id"]:03d}'/f'view_{row["corner_id"]:03d}';td.mkdir(parents=True);save(td/'metrics.json',clean)
 print('5/6 Проверяются identity, oracle gap и final gates...',flush=True);primary=decision(rows,fixture);report={'schema':'head-identity-contact-development-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'model':model_meta,'primary':primary,'tests':rows,'source84z_primary':summary['primary'],'limitations':['Development experts use synthetic action/contact labels; candidate inference uses probabilities, not true action.','Oracle expert is diagnostic only and does use final truth action.','Reduced support surrogate and geometric proxy, not collision force.','Go only authorizes frozen89C; series90 remains blocked.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 89B4: HEAD IDENTITY + CONTACT\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 if manifest(folder/'result')!=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))['files']:raise ValueError('Manifest series89B4 повреждён.')
 print('6/6 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия89B4: head identity and contact');root.geometry('790x410+155+75');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия89B4: soft action mixture, head contact и untouched final\n360 visual cases; frozen source84Z.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать завершённую папку84Z и запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 folder=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not folder:root.destroy();return
 root.withdraw();root.update();result=run(folder,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия89B4 завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-89B4.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 89B4: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
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
