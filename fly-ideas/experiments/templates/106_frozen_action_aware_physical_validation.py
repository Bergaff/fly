#!/usr/bin/env python3
"""Series106: frozen selected Series105D model on official-eye physical validation."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER105D=HERE/'105d_action_aware_temporal_tournament.py';RUNNER105D_SHA='8c39bfca87f3a11f59ac82cca721c58bb142094f7cd26bb1d4d6ae275ab23e45'
RESULT105D=HERE.parent/'reports'/'action-aware-temporal-tournament-105d-user-result.json';RESULT105D_SHA='59f8d54fbc7c062c068259d455484f643844f33092e655e195acb170cbfb9ad3'
MODEL105D_SHA='1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1'
ROOT=Path('workspace/runs/ideas/i-observational/action-aware-physical-validation');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact');T_ROOT=Path('workspace/runs/ideas/i-observational/action-aware-temporal-tournament')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');CONDITIONS=('candidate','neutral_visual','reversed_visual','zero_input','shuffled_visual','open_loop')
def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha_bytes(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load_module(name,path,expected):
 if file_sha(path)!=expected:raise ValueError(f'Закреплённый {path.name} изменился.')
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize():
 if file_sha(RESULT105D)!=RESULT105D_SHA:raise ValueError('Exact Series105D result изменён.')
 x=json.loads(RESULT105D.read_text(encoding='utf8'))
 if x.get('status')!='completed' or x.get('selected_model')!='temporal_action_experts' or x.get('selected_model_sha256')!=MODEL105D_SHA or x.get('primary',{}).get('development_candidate') is not True or x.get('primary',{}).get('scientific_result') is not False:raise ValueError('Series106 требует exact successful Series105D development result.')
 if x.get('protocol',{}).get('script_sha256')!=RUNNER105D_SHA:raise ValueError('Series105D result не соответствует runner.')
 s105d=load_module('series106_source105d',RUNNER105D,RUNNER105D_SHA);s105c,s105,s104,s102,s103,result105c,result105,result104=s105d.authorize();return s105d,s105c,s105,s104,s102,s103,x,result105c,result105
def load_linear(z,prefix):return {k:np.array(z[prefix+k],copy=True) for k in ('xm','xs','ym','ys','w')}
def load_selected(folder):
 p=Path(folder)/'selected_action_aware_model.npz'
 if file_sha(p)!=MODEL105D_SHA:raise ValueError('Нужен exact selected_action_aware_model.npz SHA1bbb15cd….')
 with np.load(p,allow_pickle=False)as z:
  expected={'model_name','kind','feature'}|{f'classifier_{k}'for k in ('xm','xs','ym','ys','w')}|{f'expert{i}_{k}'for i in range(3)for k in ('xm','xs','ym','ys','w')}
  if set(z.files)!=expected or str(z['model_name'].item())!='temporal_action_experts' or str(z['kind'].item())!='experts' or str(z['feature'].item())!='temp':raise ValueError('Selected Series105D model schema неверна.')
  model={'kind':'experts','feature':'temp','classifier':load_linear(z,'classifier_'),'experts':[load_linear(z,f'expert{i}_')for i in range(3)]}
 return p,model
def specs(m86):
 out=[]
 for rep in range(4):
  for ai,action in enumerate(ACTIONS):
   ident=1234+rep*3+ai;seed=106100+rep*10+ai;amp=(.64,.76,.89,.97)[rep];speed=(.74,.91,1.08,1.19)[(rep+ai)%4];out.append({'role':'physical_final','id':ident,'replicate':rep+1,'action':action,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)})
 return out
def hashes_in(x):
 out=set()
 if isinstance(x,dict):
  for k,v in x.items():out.add(v) if k=='motion_sha256'and isinstance(v,str)else out.update(hashes_in(v))
 elif isinstance(x,list):
  for v in x:out.update(hashes_in(v))
 return out
def prepare(s105d,s105c,s105,s104,s102,source,d_folder,result105d,result105c,result105):
 s101,models,old_items,old_desc,guards=s105d.prepare(s105c,s105,s104,s102,source,d_folder,result105c,result105);m=models['m'];m88=m.load88();m87=m88.load87();m86=m87.load86();s89=s101.load89e();seen=hashes_in(result105d)|hashes_in(result105c)|hashes_in(result105)
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)as db:seen|={x[0]for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 seen|=m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|models['m2'].authorize_b()|models['m3'].authorize_b2()|s89.authorize_d();items=[];desc=[]
 for x in specs(m86):
  h=s105.motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series106 motion пересекается с прежними outcomes.')
  item={**x,'motion_sha256':h};items.append(item);desc.append({k:v for k,v in item.items()if k!='angles_deg'});seen.add(h)
 return s101,models,items,desc,guards
def model_target(s105d,base,model,temp):
 coeff,logits=s105d.predict(model,np.asarray(temp,float));return s105d.decode(base,coeff,49),np.asarray(logits,float)
def capture_case(s105d,s104,s103,base,bridge,item,neutral_temp,model,progress,base_fraction,span):
 commands=np.asarray(item['angles_deg'],float)*np.pi/180;images,actual=s104.capture(s103,bridge,commands,progress,base_fraction,span*.35,f'Official-eye capture {item["id"]}');truth=np.asarray(actual[2:],float);edge=base['b'].edge_history(images);rng=np.random.default_rng(106000000+item['id']);perm=rng.permutation(len(images));temps={'candidate':s105d.temp_pool(edge),'neutral_visual':neutral_temp,'reversed_visual':s105d.temp_pool(base['b'].edge_history(images[::-1].copy())),'zero_input':np.zeros_like(neutral_temp),'shuffled_visual':s105d.temp_pool(base['b'].edge_history(images[perm].copy()))};targets={};logits=None
 for c,t in temps.items():targets[c],q=model_target(s105d,base,model,t);logits=q if c=='candidate'else logits
 targets['open_loop']=targets['candidate'];return truth,targets,logits
def safe(x):return x['finite']and x['minimum_thorax_z_mm']>=.15 and x['maximum_thorax_z_mm']<=2.5 and x['contact_frame_fraction']>0
def decide(rows,fixture=False):
 n=len(rows);required=n if fixture else 8;open_req=n if fixture else 10;action_req=n if fixture else 9;per_action_req=4 if fixture else 3;per_control_action=4 if fixture else 2;candidate=[r['controls']['candidate']for r in rows];wins={c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows)for c in CONDITIONS if c!='candidate'};by_action={a:{c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['action']==a)for c in ('neutral_visual','reversed_visual','zero_input','shuffled_visual')}for a in ACTIONS};correct=sum(r['predicted_action']==r['action']for r in rows);correct_by={a:sum(r['predicted_action']==a for r in rows if r['action']==a)for a in ACTIONS};tracking=float(np.mean([x['tracking_rmse_rad']for x in candidate]));means={c:float(np.mean([r['controls'][c]['truth_rmse_rad']for r in rows]))for c in CONDITIONS};distinct=all(r['target_hashes']['candidate']!=r['target_hashes'][c]for r in rows for c in ('neutral_visual','reversed_visual','zero_input','shuffled_visual'));passed=sum(safe(x)for x in candidate)==n and tracking<=.20 and correct>=action_req and all(correct_by[a]>=per_action_req for a in ACTIONS)and all(wins[c]>=required for c in ('neutral_visual','reversed_visual','zero_input','shuffled_visual'))and wins['open_loop']>=open_req and all(by_action[a][c]>=per_control_action for a in ACTIONS for c in by_action[a])and distinct;return {'cases':n,'required_control_wins':required,'required_open_loop_wins':open_req,'required_action_correct':action_req,'required_action_correct_per_class':per_action_req,'required_control_wins_per_class':per_control_action,'candidate_safe_cases':sum(safe(x)for x in candidate),'candidate_mean_tracking_rmse_rad':tracking,'action_correct':correct,'action_correct_by_class':correct_by,'candidate_truth_wins':wins,'candidate_truth_wins_by_class':by_action,'mean_truth_rmse_rad':means,'targets_distinct':distinct,'passed':passed,'physical_development_candidate':passed,'scientific_result':False}
def fixture_rows():
 rows=[]
 for rep in range(4):
  for ai,a in enumerate(ACTIONS):
   controls={c:{'finite':True,'tracking_rmse_rad':.04,'truth_rmse_rad':.06 if c=='candidate'else.20,'contact_frame_fraction':1.,'mean_contact_legs':4.,'max_actuator_force_norm':8.,'minimum_thorax_z_mm':.8,'maximum_thorax_z_mm':1.2,'energy_abs_work':1.,'torque_saturation_fraction':0.}for c in CONDITIONS};rows.append({'id':1234+rep*3+ai,'action':a,'predicted_action':a,'target_hashes':{c:c+str(rep)+str(ai)for c in CONDITIONS},'controls':controls})
 return rows
def run(source,d_folder,model_folder,output_root=ROOT,fixture=False,progress=lambda *x:None):
 s105d,s105c,s105,s104,s102,s103,result105d,result105c,result105=authorize();model_path,model=load_selected(model_folder)if not fixture else(Path(__file__),None);root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('action_aware_physical_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();progress('Проверяются exact model/prerequisites',.01,0,1)
 if fixture:desc=[];rows=fixture_rows();trace=[];primary=decide(rows,True)
 else:
  s101,base,items,desc,guards=prepare(s105d,s105c,s105,s104,s102,source,d_folder,result105d,result105c,result105);bridge=s103.Bridge();rows=[];trace=[]
  try:
   n=len(np.asarray(items[0]['angles_deg']));neutral_images,_=s104.capture(s103,bridge,np.zeros((n,6)),progress,.02,.05,'Neutral visual control');neutral_temp=s105d.temp_pool(base['b'].edge_history(neutral_images));total=len(items)*len(CONDITIONS);done=0
   for i,item in enumerate(items):
    truth,targets,logits=capture_case(s105d,s104,s103,base,bridge,item,neutral_temp,model,progress,.07+.25*i/len(items),.25/len(items));controls={}
    for c in CONDITIONS:
     metric=s104.rollout(s103,bridge,targets[c],truth,c=='open_loop');sample=metric.pop('sample');controls[c]=metric
     for fi,angles in enumerate(sample):trace.append({'id':item['id'],'action':item['action'],'condition':c,'frame':fi,**{s103.MAPPED_DOF[j]:float(angles[j])for j in range(6)}})
     done+=1;progress('Frozen model physical controls',.32+.64*done/total,done,total)
    hashes={c:sha_bytes(np.asarray(v,dtype='<f8').tobytes())for c,v in targets.items()};rows.append({'id':item['id'],'action':item['action'],'predicted_action':ACTIONS[int(np.argmax(logits))],'action_scores':{a:float(logits[j])for j,a in enumerate(ACTIONS)},'target_hashes':hashes,'controls':controls})
   before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p)for p in before}or frozen_before!=s104.manifest(frozen_path)or file_sha(model_path)!=MODEL105D_SHA:raise ValueError('Frozen sources/model изменились.')
   primary=decide(rows,False)
  finally:bridge.close()
 protocol={'schema':'frozen-action-aware-physical-validation-v1','mode':'fixture'if fixture else'full','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner105d_sha256':RUNNER105D_SHA,'series105d_result_sha256':RESULT105D_SHA,'selected_model_sha256':MODEL105D_SHA,'selected_model':'temporal_action_experts','training_allowed':False,'selection_allowed':False,'post_result_tuning':False,'motions':desc,'controls':list(CONDITIONS),'motor':'same official MOTOR bridge as Series104; candidate/visual/input controls closed-loop, open_loop has no q/dq feedback','primary_rule':'all12 candidate safe/contact; tracking<=0.20; action>=9/12 and>=3/4 each; candidate wins>=8/12 and>=2/4 each class vs neutral/reversed/zero/shuffled; open-loop>=10/12; targets distinct'};save(folder/'protocol.json',protocol);report={'schema':'frozen-action-aware-physical-validation-result-v1','status':'fixture_completed'if fixture else'completed','protocol':protocol,'series105d_primary':result105d['primary'],'primary':primary,'tests':rows,'limitations':['Frozen supervised Series105D model on official physical bodies; no training or selection in Series106.','Generated demonstrator actions and engineering six-DOF mapping, not biological behavior.','No FlyVis/FlyWire/connectome mapping, living animal, muscles, or mirror-neuron claim.']};save(temp/'summary.json',report)
 if trace:
  with(temp/'physical_trace.csv').open('w',newline='',encoding='utf8')as f:w=csv.DictWriter(f,fieldnames=list(trace[0]));w.writeheader();w.writerows(trace)
 (temp/'ИТОГ.txt').write_text('SERIES106: FROZEN ACTION-AWARE PHYSICAL VALIDATION\n\nPrimary: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\nEngineering physical validation, не biological result.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series106: frozen action-aware physical validation');root.geometry('830x480+110+55');root.attributes('-topmost',True);status=tk.StringVar(value='Выберите exact105D model и frozen source folders');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series106: frozen supervised model → official physical body',font=('Arial',13,'bold'),pady=14).pack();tk.Label(root,text='12 новых untouched motions ×6 physical conditions. Training/selection/tuning отсутствуют.\nНужна оригинальная result-папка105D с selected_action_aware_model.npz.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=630,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать model105D, result89D и source84Z, затем запустить',padx=18,pady=9);button.pack(pady=14)
 def update(text,fraction,done,total):
  def apply():
   p=round(fraction*100,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.02:elapsed=time.time()-start[0];eta.set(f'Прошло {elapsed/60:.1f} мин · осталось примерно {elapsed*(1-fraction)/fraction/60:.1f} мин')
  root.after(0,apply)
 def begin():
  model=filedialog.askdirectory(title='Выберите оригинальную result-папку Series105D',mustexist=True,initialdir=str(T_ROOT.resolve()if T_ROOT.exists()else Path.cwd()),parent=root)
  if not model:return
  d=filedialog.askdirectory(title='Выберите завершённую result-папку Series89D',mustexist=True,initialdir=str(D_ROOT.resolve()if D_ROOT.exists()else Path.cwd()),parent=root)
  if not d:return
  source=filedialog.askdirectory(title='Выберите production Series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve()if SOURCE_ROOT.exists()else Path.cwd()),parent=root)
  if not source:return
  button.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(source,d,model,progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series106','Physical validation завершён.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-106.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series106',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--model105d');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.','.',a.output_root,True))
 elif a.source84z and a.result89d and a.model105d:print(run(a.source84z,a.result89d,a.model105d,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d+model105d.')
if __name__=='__main__':main()
