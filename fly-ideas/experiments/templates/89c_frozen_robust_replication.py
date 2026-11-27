#!/usr/bin/env python3
"""Series89C: frozen replication of the successful series89B6 robust policy."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;RUNNER_B6=HERE/'89b6_robust_foreleg_contact.py';RUNNER_B6_SHA='1d308cb1ff20a7f6934775c0da62df99bdf062b1fc5e1395328f4f94594c0cb6';GO_B6=HERE.parent/'reports'/'robust-foreleg-contact-89b6-user-summary-extract.json';GO_B6_SHA='887695914ce1099e84d9f431d487988a1475070dc56d22d1e48958ea1b90c0f6';GO_B6_SOURCE_SHA='f1c362073c81f505a28ada36306bf51160ec9f3051ad3997b123c4777dc2fcc2';MODEL_B6_SHA='b8beb562d5a623d31ae7094fedfdb57b6a844f5f361c04092c0a641a7f5534f1';MODEL84Z_SHA='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0'
ROOT=Path('workspace/runs/ideas/i-observational/frozen-robust-replication');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');B6_ROOT=Path('workspace/runs/ideas/i-observational/robust-foreleg-contact');ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');PROFILES=('neutral','pose_offset','velocity_offset');CONDITIONS=('candidate','standard_hard','soft_mixture','angle_only','common_contact','oracle_expert','uncalibrated','zero_state','shuffled_state','open_loop','shared_lesion');WORK=None
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load_b6():
 if file_sha(RUNNER_B6)!=RUNNER_B6_SHA:raise ValueError('Закреплённый runner89B6 изменился.')
 s=importlib.util.spec_from_file_location('series89c_source',RUNNER_B6);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize_b6():
 if file_sha(GO_B6)!=GO_B6_SHA:raise ValueError('Published series89B6 extract изменён.')
 d=json.loads(GO_B6.read_text(encoding='utf8'));motions=d.get('protocol',{}).get('motions',[])
 if d.get('source_file_sha256')!=GO_B6_SOURCE_SHA or d.get('reported_primary',{}).get('passed') is not True or [x.get('id') for x in motions]!=list(range(783,819)) or d.get('model',{}).get('sha256')!=MODEL_B6_SHA or d.get('model',{}).get('foreleg_boost_selected',{}).get('boost')!=4.0:raise ValueError('Series89B6 development-go identity не подтверждена.')
 return {x['motion_sha256'] for x in motions}
def normalize_b6(folder):
 p=Path(folder)
 if (p/'result'/'summary.json').is_file():p=p/'result'
 if not (p/'summary.json').is_file():raise ValueError('Выбрана не завершённая result-папка series89B6.')
 return p
def load_frozen(folder,fixture=False):
 p=normalize_b6(folder);summary=p/'summary.json';model=p/'robust_foreleg_model.npz';complete=p/'complete.json'
 if not model.is_file() or not complete.is_file():raise ValueError('В result89B6 нет frozen model/complete manifest.')
 if not fixture and file_sha(summary)!=GO_B6_SOURCE_SHA:raise ValueError('Нужен точный successful summary89B6.')
 if not fixture and file_sha(model)!=MODEL_B6_SHA:raise ValueError('Frozen model89B6 изменён.')
 if manifest(p)!=json.loads(complete.read_text(encoding='utf8'))['files']:raise ValueError('Manifest result89B6 повреждён.')
 d=json.loads(summary.read_text(encoding='utf8'))
 if not d.get('primary',{}).get('passed') or d.get('model',{}).get('foreleg_boost_selected',{}).get('boost')!=4.0:raise ValueError('Нужен full development go89B6 с boost4.')
 z=np.load(model,allow_pickle=False);required={'angle_mean','angle_scale','angle_weights','identity_mean','identity_scale','identity_weights','common_contact','expert_contacts','standard_expert_contacts','expert_lambdas','standard_expert_lambdas','foreleg_boost','temperature'}
 if set(z.files)!=required:raise ValueError('Состав frozen model89B6 изменён.')
 if float(z['foreleg_boost'][0])!=4.:raise ValueError('Frozen boost не равен4.')
 m6=load_b6();angle={'mean':z['angle_mean'],'scale':z['angle_scale'],'weights':z['angle_weights']};identity={'mean':z['identity_mean'],'scale':z['identity_scale'],'weights':z['identity_weights']};common={'weights':z['common_contact']};experts={a:{'weights':z['expert_contacts'][i]} for i,a in enumerate(ACTIONS)};standard={a:{'weights':z['standard_expert_contacts'][i]} for i,a in enumerate(ACTIONS)};selections={a:{'selected':{'lambda':float(z['expert_lambdas'][i])}} for i,a in enumerate(ACTIONS)};standard_selections={a:{'selected':{'lambda':float(z['standard_expert_lambdas'][i])}} for i,a in enumerate(ACTIONS)}
 return p,d,angle,identity,common,experts,selections,standard,standard_selections,float(z['temperature'][0])
def specs(fixture=False):
 m86=load_b6().load_b5().load_b4().load_b3().load_b2().load_b().load88().load87().load86();out=[];ident=819
 for rep in range(6):
  for ai,action in enumerate(ACTIONS):
   amp=(.68,.84,1.)[(rep+ai)%3];speed=(.60,.88,1.16)[(rep+2*ai)%3];seed=891500+10*rep+ai;out.append({'role':'frozen_final','id':ident,'replicate':rep+1,'action':action,'head_seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 return [x for x in out if x['id'] in (819,820,821)] if fixture else out
def held_views(fixture=False):
 count=4 if fixture else 12;vals=[]
 for i in range(count):vals.append({'corner_id':721+i,'view':{'fov_deg':35.,'camera_side':(.18,.26,.34,.40,.42)[(i+3)%5],'camera_z':(.38,.47,.56,.57)[(2*i+1)%4],'body_x':(3.92,4.,4.08,4.085)[(3*i+2)%4],'body_y':(-.04,.02,.04)[(i+1)%3]}})
 return vals
def prepare(stim,labels,training_hashes,fixture=False):
 m6=load_b6();m5=m6.load_b5();m4=m5.load_b4();m3=m4.load_b3();m2=m3.load_b2();m=m2.load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();seen={x['motion_sha256'] for x in labels}|set(training_hashes)|m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|m2.authorize_b()|m3.authorize_b2()|authorize_b6();out=[];desc=[]
 for x in specs(fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Frozen89C motion совпал с training/disclosed motion.')
  seen.add(h);item={**x,'motion_sha256':h};out.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'})
 return out,desc
def worker_init(bundle,s84v):
 global WORK
 WORK=load_b6();WORK.worker_init(bundle,s84v)
def worker_visual(arg):return WORK.worker_visual(arg)
def run(source_folder,b6_folder,workers,output_root=ROOT,fixture=False):
 authorize_b6();m6=load_b6();m5=m6.load_b5();m4=m5.load_b4();m3=m4.load_b3();m2=m3.load_b2();m=m2.load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();s85=m86.load85();workers,count=s85.worker_choice(workers);print('1/5 Проверяются development go89B6, frozen model и source84Z...',flush=True);frozen_path,b6_summary,angle,identity,common,experts,selections,standard,standard_selections,temp_value=load_frozen(b6_folder,fixture);frozen_before=manifest(frozen_path);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,fixture)
 if not fixture and file_sha(paths[1])!=MODEL84Z_SHA:raise ValueError('Frozen model84Z identity изменена.')
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items,desc=prepare(stim,saved['labels'],training_hashes,fixture);views=held_views(fixture);tasks=[(x,v) for x in items for v in views];protocol={'schema':'frozen-robust-replication-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner89b6_sha256':RUNNER_B6_SHA,'series89b6_go_extract_sha256':GO_B6_SHA,'series89b6_summary_sha256':GO_B6_SOURCE_SHA,'frozen89b6_model_sha256':MODEL_B6_SHA,'frozen84z_model_sha256':MODEL84Z_SHA,'selected_model_sha256':file_sha(paths[1]),'training_allowed':False,'selection_allowed':False,'candidate_inference_uses_truth_action':False,'oracle_control_uses_truth_action':True,'motions':desc,'views':views,'initial_profiles':list(PROFILES),'controls':list(CONDITIONS),'frozen_foreleg_boost':4.0,'frozen_thresholds':b6_summary['protocol']['primary_rule'],'workers':count,'worker_choice':str(workers),'primary_rule':'exact series89B6 identity/safety/angle/contact gates; no fit, selection, or threshold changes'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('frozen_robust_replication_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/5 Запускается {len(tasks)} frozen visual cases, workers={count}.',flush=True);visual=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(worker_visual,tasks),1):visual.append(row);print(f'  Visual cases {n}/{len(tasks)}',flush=True) if n%12==0 else None
 print('3/5 Выполняются неизменённые controls...',flush=True);rows=[]
 for row in visual:
  targets,probs=m6.controls_for(m3,m2,m,b,row['_coeff'],row['_target'],angle,identity,temp_value,common,float(b6_summary['model']['common_selected']['lambda']),experts,selections,standard,standard_selections);targets['oracle_expert']=m6.expert_policies(m2,m,row['_target'],angle,experts,selections)[ACTIONS.index(row['action'])];trials=[]
  for pi,profile in enumerate(PROFILES):
   seed=895000000+row['id']*1000+row['corner_id']*10+pi;controls={}
   for name in CONDITIONS:controls[name]=m.rollout(targets[name],row['_truth'],seed,profile,name!='open_loop',name not in ('uncalibrated','zero_state'))
   trials.append({'initial_profile':profile,'initial_seed':seed,'controls':controls})
  pred=ACTIONS[int(np.argmax(probs))];clean={k:v for k,v in row.items() if not k.startswith('_')};clean.update({'predicted_action':pred,'action_probabilities':{a:float(probs[i]) for i,a in enumerate(ACTIONS)},'oracle_control_only_uses_truth_action':True,'trials':trials});rows.append(clean);td=temp/f'test_{row["id"]:03d}'/f'view_{row["corner_id"]:03d}';td.mkdir(parents=True);save(td/'metrics.json',clean)
 print('4/5 Проверяются frozen gates...',flush=True);primary=m6.decision(rows,fixture);report={'schema':'frozen-robust-replication-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'frozen_model':{'sha256':MODEL_B6_SHA,'development_summary_sha256':GO_B6_SOURCE_SHA,'foreleg_boost':4.0},'primary':primary,'tests':rows,'source84z_primary':summary['primary'],'limitations':['Frozen replication uses synthetic action/contact truth only for scoring and oracle diagnostic.','Candidate inference does not receive true action.','Reduced support surrogate and geometric proxy, not collision force.','Series90 requires full89C go.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 89C: FROZEN ROBUST REPLICATION\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result')
 print('5/5 Проверяется неизменность sources...',flush=True)
 if before!={p:file_sha(p) for p in before} or frozen_before!=manifest(frozen_path):raise ValueError('Source84Z или frozen result89B6 изменились.')
 if manifest(folder/'result')!=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))['files']:raise ValueError('Manifest frozen89C повреждён.')
 print('Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия89C: frozen robust replication');root.geometry('790x430+155+75');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия89C: frozen replication без обучения и выбора\nMotions819–836,216 visual cases,648 trials.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать result89B6 и source84Z, затем запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 b6=filedialog.askdirectory(title='Выберите завершённую result-папку series89B6',mustexist=True,initialdir=str(B6_ROOT.resolve() if B6_ROOT.exists() else Path.cwd()),parent=root)
 if not b6:root.destroy();return
 source=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not source:root.destroy();return
 root.withdraw();root.update();result=run(source,b6,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия89C завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-89C.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 89C: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
 if os.name=='nt':
  try:os.startfile(str(path))
  except OSError:pass
 return path
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source84z');p.add_argument('--result89b6');p.add_argument('--workers',default='6');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true',help=argparse.SUPPRESS);q=p.parse_args()
 if q.choose:choose()
 elif q.source84z and q.result89b6:run(q.source84z,q.result89b6,q.workers,q.output_root,q.fixture)
 else:p.error('Нужен --choose или --source84z вместе с --result89b6.')
if __name__=='__main__':
 try:main()
 except Exception as exc:report=failure_report(exc);print(f'ОШИБКА: {type(exc).__name__}: {exc}\nОтчёт: {report.resolve()}',file=sys.stderr);sys.exit(1)
