#!/usr/bin/env python3
"""Series108: exact Series105D base plus Series107 repair on new physical cases."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER107=HERE/'107_grooming_temporal_order_repair.py';RUNNER107_SHA='822502bfc8a54d1511768f6922cf42429d17635f955ca142d0ea613acb2a2a20'
RESULT107=HERE.parent/'reports'/'grooming-temporal-order-repair-107-user-result.json';RESULT107_SHA='6628a5f4d6655f926507e7b39591ea14208e8f4d4240dbec22bf5f86b211a5b6'
BASE_SHA='1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1';ADAPTER_SHA='4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57'
ROOT=Path('workspace/runs/ideas/i-observational/frozen-grooming-repair-physical');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact');MODEL_ROOT=Path('workspace/runs/ideas/i-observational/action-aware-temporal-tournament');ADAPTER_ROOT=Path('workspace/runs/ideas/i-observational/grooming-temporal-order-repair')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');CONDITIONS=('candidate','neutral_visual','reversed_visual','zero_input','shuffled_visual','open_loop')
def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha_bytes(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return{str(p.relative_to(folder)).replace('\\','/'):file_sha(p)for p in sorted(Path(folder).rglob('*'))if p.is_file()and p.name!='complete.json'}
def load_module(name,path,sha):
 if file_sha(path)!=sha:raise ValueError(f'Закреплённый {path.name} изменился.')
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize():
 if file_sha(RESULT107)!=RESULT107_SHA:raise ValueError('Exact genuine Series107 result изменён.')
 r=json.loads(RESULT107.read_text(encoding='utf8'));p=r.get('primary',{})
 if r.get('status')!='completed'or r.get('protocol',{}).get('script_sha256')!=RUNNER107_SHA or r.get('selected_adapter')!='global_linear_q00'or r.get('selected_adapter_sha256')!=ADAPTER_SHA or p.get('development_candidate')is not True or p.get('scientific_result')is not False or p.get('truth_wins_by_action',{}).get('head_directed_grooming',{}).get('shuffled_visual')!=6:raise ValueError('Series108 требует exact successful Series107 result.')
 s107=load_module('series108_source107',RUNNER107,RUNNER107_SHA);deps=s107.authorize();return(s107,*deps,r)
def resolve(folder,name,sha):
 folder=Path(folder);candidates=(folder/name,folder/'result'/name);p=next((x for x in candidates if x.is_file()),None)
 if p is None:raise FileNotFoundError(f'Не найден {name}. Выберите папку запуска или её result. Проверено: '+', '.join(str(x)for x in candidates))
 actual=file_sha(p)
 if actual!=sha:raise ValueError(f'Неверный {name}: SHA-256 {actual}; требуется {sha}.')
 return p
def load_adapter(folder):
 p=resolve(folder,'selected_grooming_repair_adapter.npz',ADAPTER_SHA)
 with np.load(p,allow_pickle=False)as z:
  required={'adapter_name','base_model_sha256','key','per_action','thresholds','fit0_xm','fit0_xs','fit0_w'}
  if set(z.files)!=required or str(z['adapter_name'].item())!='global_linear_q00'or str(z['base_model_sha256'].item())!=BASE_SHA or str(z['key'].item())!='diag'or bool(z['per_action'].item())is not False:raise ValueError('Selected Series107 adapter schema неверна.')
  det={'name':'global_linear_q00','key':'diag','per_action':False,'thresholds':np.array(z['thresholds'],copy=True),'fits':[{'xm':np.array(z['fit0_xm'],copy=True),'xs':np.array(z['fit0_xs'],copy=True),'w':np.array(z['fit0_w'],copy=True)}]}
 return p,det
def hashes_in(x):
 out=set()
 if isinstance(x,dict):
  for k,v in x.items():out.add(v)if k=='motion_sha256'and isinstance(v,str)else out.update(hashes_in(v))
 elif isinstance(x,list):
  for v in x:out.update(hashes_in(v))
 return out
def specs(m86):
 out=[]
 for rep in range(6):
  for ai,a in enumerate(ACTIONS):
   ident=1342+rep*3+ai;seed=108100+rep*10+ai;amp=(.62,.69,.77,.85,.92,.98)[rep];speed=(.72,.84,.96,1.08,1.16,1.22)[(rep+ai)%6];out.append({'role':'physical_final','id':ident,'replicate':rep+1,'action':a,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(a,seed,amp,speed)})
 return out
def prepare(s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r107,r106,r105d,r105c,r105):
 s101,models,_,_,guards=s107.prepare(s106,s105d,s105c,s105,s104,s102,source,d_folder,r106,r105d,r105c,r105);m=models['m'];m86=m.load88().load87().load86();seen=hashes_in(r107)|hashes_in(r106)|hashes_in(r105d)|hashes_in(r105c)|hashes_in(r105)
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)as db:seen|={z[0]for z in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items=[];desc=[]
 for x in specs(m86):
  h=s105.motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series108 motion пересекается с прежними outcomes.')
  q={**x,'motion_sha256':h};items.append(q);desc.append({k:v for k,v in q.items()if k!='angles_deg'});seen.add(h)
 return s101,models,items,desc,guards
def target(s107,s105d,base,model,det,temp,d,ai,n):
 coeff,_=s105d.predict(model,temp);zero,_=s105d.predict(model,np.zeros_like(temp));ok=False if d is None else s107.valid(det,d,ai);return s105d.decode(base,coeff if ok else zero,n),ok
def capture_case(s107,s105d,s104,s103,base,bridge,item,neutral,model,det,progress,fraction):
 cmd=np.asarray(item['angles_deg'],float)*np.pi/180;images,actual=s104.capture(s103,bridge,cmd,progress,max(.02,fraction-.006),.006,f'Frozen repaired physical capture {item["id"]}');truth=np.asarray(actual[2:],float);edge=base['b'].edge_history(images);rng=np.random.default_rng(108000000+item['id']);perm=rng.permutation(len(images));edges={'candidate':edge,'reversed_visual':base['b'].edge_history(images[::-1].copy()),'shuffled_visual':base['b'].edge_history(images[perm].copy())};temp=s105d.temp_pool(edge);_,logits=s105d.predict(model,temp);ai=int(np.argmax(logits));targets={};accepted={}
 for c in ('candidate','reversed_visual','shuffled_visual'):
  t=s105d.temp_pool(edges[c]);d=s107.diag(edges[c]);targets[c],accepted[c]=target(s107,s105d,base,model,det,t,d,ai,len(truth))
 targets['neutral_visual'],accepted['neutral_visual']=target(s107,s105d,base,model,det,neutral['temp'],neutral['diag'],ai,len(truth));targets['zero_input'],accepted['zero_input']=target(s107,s105d,base,model,det,np.zeros_like(temp),None,ai,len(truth));targets['open_loop']=targets['candidate'];accepted['open_loop']=accepted['candidate'];return truth,targets,accepted,logits
def safe(x):return x['finite']and x['minimum_thorax_z_mm']>=.15 and x['maximum_thorax_z_mm']<=2.5 and x['contact_frame_fraction']>0
def decide(rows,fixture=False):
 n=len(rows);overall=n if fixture else 12;open_req=n if fixture else 15;action_req=n if fixture else 15;action_each=6 if fixture else 5;per_control=6 if fixture else 3;reject_req=n if fixture else 15;reject_each=6 if fixture else 4;cand=[r['controls']['candidate']for r in rows];wins={c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows)for c in CONDITIONS if c!='candidate'};by={a:{c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['action']==a)for c in ('neutral_visual','reversed_visual','zero_input','shuffled_visual')}for a in ACTIONS};correct=sum(r['predicted_action']==r['action']for r in rows);correct_by={a:sum(r['predicted_action']==a for r in rows if r['action']==a)for a in ACTIONS};kept=sum(r['validity_accepted']['candidate']for r in rows);rejected=sum(not(r['validity_accepted']['shuffled_visual'])for r in rows);rejected_by={a:sum(not(r['validity_accepted']['shuffled_visual'])for r in rows if r['action']==a)for a in ACTIONS};tracking=float(np.mean([x['tracking_rmse_rad']for x in cand]));means={c:float(np.mean([r['controls'][c]['truth_rmse_rad']for r in rows]))for c in CONDITIONS};distinct=all(r['target_hashes']['candidate']!=r['target_hashes'][c]for r in rows for c in ('neutral_visual','reversed_visual','zero_input','shuffled_visual'));passed=sum(safe(x)for x in cand)==n and tracking<=.20 and kept==n and rejected>=reject_req and all(rejected_by[a]>=reject_each for a in ACTIONS)and correct>=action_req and all(correct_by[a]>=action_each for a in ACTIONS)and all(wins[c]>=overall for c in ('neutral_visual','reversed_visual','zero_input','shuffled_visual'))and wins['open_loop']>=open_req and all(by[a][c]>=per_control for a in ACTIONS for c in by[a])and distinct;return{'cases':n,'required_control_wins':overall,'required_open_loop_wins':open_req,'required_action_correct':action_req,'required_action_correct_per_class':action_each,'required_control_wins_per_class':per_control,'required_shuffled_rejections':reject_req,'required_shuffled_rejections_per_class':reject_each,'candidate_safe_cases':sum(safe(x)for x in cand),'candidate_mean_tracking_rmse_rad':tracking,'candidate_validity_kept':kept,'shuffled_validity_rejected':rejected,'shuffled_rejected_by_class':rejected_by,'action_correct':correct,'action_correct_by_class':correct_by,'candidate_truth_wins':wins,'candidate_truth_wins_by_class':by,'mean_truth_rmse_rad':means,'targets_distinct':distinct,'passed':passed,'physical_development_candidate':passed,'scientific_result':False}
def fixture_rows():
 rows=[]
 for rep in range(6):
  for ai,a in enumerate(ACTIONS):
   controls={c:{'finite':True,'tracking_rmse_rad':.05,'truth_rmse_rad':.06 if c=='candidate'else.2,'contact_frame_fraction':1.,'mean_contact_legs':4.,'max_actuator_force_norm':8.,'minimum_thorax_z_mm':.8,'maximum_thorax_z_mm':1.2,'energy_abs_work':1.,'torque_saturation_fraction':0.}for c in CONDITIONS};rows.append({'id':1342+rep*3+ai,'action':a,'predicted_action':a,'validity_accepted':{c:c not in('zero_input','shuffled_visual')for c in CONDITIONS},'target_hashes':{c:c+str(rep)+str(ai)for c in CONDITIONS},'controls':controls})
 return rows
def run(source,d_folder,model_folder,adapter_folder,output_root=ROOT,fixture=False,progress=lambda*x:None):
 s107,s106,s105d,s105c,s105,s104,s102,s103,r105d,r105c,r105,r106,r107=authorize();model_path,model=s106.load_selected(model_folder)if not fixture else(Path(__file__),None);adapter_path,det=load_adapter(adapter_folder)if not fixture else(Path(__file__),None);root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('frozen_grooming_physical_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();progress('Проверяются exact base+adapter',.01,0,1)
 if fixture:desc=[];rows=fixture_rows();trace=[];primary=decide(rows,True)
 else:
  s101,base,items,desc,guards=prepare(s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r107,r106,r105d,r105c,r105);s101.worker_init(base['bundle'],base['s84v']);bridge=s103.Bridge();rows=[];trace=[]
  try:
   n=len(np.asarray(items[0]['angles_deg']));images,_=s104.capture(s103,bridge,np.zeros((n,6)),progress,.015,.015,'Neutral repaired-policy control');edge=base['b'].edge_history(images);neutral={'temp':s105d.temp_pool(edge),'diag':s107.diag(edge)};total=len(items)*len(CONDITIONS);done=0
   for i,item in enumerate(items):
    truth,targets,accepted,logits=capture_case(s107,s105d,s104,s103,base,bridge,item,neutral,model,det,progress,.03+.25*(i+1)/len(items));controls={}
    for c in CONDITIONS:
     metric=s104.rollout(s103,bridge,targets[c],truth,c=='open_loop');sample=metric.pop('sample');controls[c]=metric
     for fi,angles in enumerate(sample):trace.append({'id':item['id'],'action':item['action'],'condition':c,'frame':fi,**{s103.MAPPED_DOF[j]:float(angles[j])for j in range(6)}})
     done+=1;progress('Frozen repaired physical controls',.28+.68*done/total,done,total)
    hashes={c:sha_bytes(np.asarray(v,dtype='<f8').tobytes())for c,v in targets.items()};rows.append({'id':item['id'],'action':item['action'],'predicted_action':ACTIONS[int(np.argmax(logits))],'validity_accepted':accepted,'target_hashes':hashes,'controls':controls})
   before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p)for p in before}or frozen_before!=s104.manifest(frozen_path)or file_sha(model_path)!=BASE_SHA or file_sha(adapter_path)!=ADAPTER_SHA:raise ValueError('Frozen sources/base/adapter изменились.')
   primary=decide(rows,False)
  finally:bridge.close()
 protocol={'schema':'frozen-grooming-repair-physical-v1','mode':'fixture'if fixture else'full','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner107_sha256':RUNNER107_SHA,'series107_result_sha256':RESULT107_SHA,'base_model_sha256':BASE_SHA,'adapter_sha256':ADAPTER_SHA,'adapter_name':'global_linear_q00','training_allowed':False,'selection_allowed':False,'post_result_tuning':False,'motions':desc,'conditions':list(CONDITIONS),'primary_rule':'all18 safe/contact/tracking<=.20/candidate accepted; action>=15 and>=5/class; shuffled rejected>=15 and>=4/class; wins>=12 and>=3/class vs input controls; open-loop>=15; distinct'};save(folder/'protocol.json',protocol);report={'schema':'frozen-grooming-repair-physical-result-v1','status':'fixture_completed'if fixture else'completed','protocol':protocol,'series107_primary':r107['primary'],'primary':primary,'tests':rows,'limitations':['Exact supervised Series105D base plus Series107 validity adapter; no Series108 fit or selection.','Generated demonstrator actions and engineering six-DOF mapping, not biological behavior.','No FlyVis/FlyWire/connectome mapping, living animal, muscles or mirror-neuron claim.']};save(temp/'summary.json',report)
 if trace:
  with(temp/'physical_trace.csv').open('w',newline='',encoding='utf8')as f:w=csv.DictWriter(f,fieldnames=list(trace[0]));w.writeheader();w.writerows(trace)
 (temp/'ИТОГ.txt').write_text('SERIES108: FROZEN GROOMING REPAIR PHYSICAL VALIDATION\n\nPrimary: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\nEngineering physical validation, not biological result.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series108: frozen repaired grooming physical validation');root.geometry('860x510+90+40');root.attributes('-topmost',True);status=tk.StringVar(value='Выберите exact base, adapter и frozen source folders');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series108: решающий physical test ремонта груминга',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='18 новых untouched motions ×6 physical conditions =108 rollouts.\nBase и adapter exact-load; training/selection/tuning отсутствуют.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=670,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать base105D, adapter107, result89D, source84Z и запустить',padx=18,pady=9);button.pack(pady=14)
 def update(text,fraction,done,total):
  def apply():
   p=round(100*fraction,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.02:e=time.time()-start[0];eta.set(f'Прошло {e/60:.1f} мин · осталось примерно {e*(1-fraction)/fraction/60:.1f} мин')
  root.after(0,apply)
 def begin():
  model=filedialog.askdirectory(title='Выберите папку запуска Series105D или её result',mustexist=True,initialdir=str(MODEL_ROOT.resolve()if MODEL_ROOT.exists()else Path.cwd()),parent=root)
  if not model:return
  adapter=filedialog.askdirectory(title='Выберите папку запуска Series107 или её result',mustexist=True,initialdir=str(ADAPTER_ROOT.resolve()if ADAPTER_ROOT.exists()else Path.cwd()),parent=root)
  if not adapter:return
  d=filedialog.askdirectory(title='Выберите завершённую result89D',mustexist=True,initialdir=str(D_ROOT.resolve()if D_ROOT.exists()else Path.cwd()),parent=root)
  if not d:return
  source=filedialog.askdirectory(title='Выберите production source84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve()if SOURCE_ROOT.exists()else Path.cwd()),parent=root)
  if not source:return
  button.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(source,d,model,adapter,progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series108','Physical validation завершён.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-108.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series108',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--model105d');p.add_argument('--adapter107');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.','.','.',a.output_root,True))
 elif all((a.source84z,a.result89d,a.model105d,a.adapter107)):print(run(a.source84z,a.result89d,a.model105d,a.adapter107,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d+model105d+adapter107.')
if __name__=='__main__':main()
