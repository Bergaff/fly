#!/usr/bin/env python3
"""Series102: frozen replication of the Series101 official FlyGym adapter."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER101=HERE/'101_frozen89e_flygym_adapter.py';RUNNER101_SHA='00063575a7b8f0c23d5bb319ec3776f1ac04c963a069755e2daf4d25e2613a17'
RESULT101=HERE.parent/'reports'/'frozen89e-flygym-adapter-user-result.json';RESULT101_SHA='9577d951090e4104326652a76ce31b387f82e13910cead1c4e2d477d9c3374ea'
ROOT=Path('workspace/runs/ideas/i-observational/frozen89e-flygym-replication');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');CONDITIONS=('candidate','zero_state','shuffled_state','shared_lesion','open_loop')
WORK=None

def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha_bytes(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load101():
 if file_sha(RUNNER101)!=RUNNER101_SHA:raise ValueError('Закреплённый runner101 изменился.')
 s=importlib.util.spec_from_file_location('series102_source101',RUNNER101);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize():
 if file_sha(RESULT101)!=RESULT101_SHA:raise ValueError('Series101 user result изменён.')
 x=json.loads(RESULT101.read_text(encoding='utf8'))
 if x.get('status')!='completed' or x.get('primary',{}).get('passed') is not True or x.get('primary',{}).get('scientific_result') is not False:raise ValueError('Нужен точный completed Series101 physical-adapter go.')
 if x.get('protocol',{}).get('script_sha256')!=RUNNER101_SHA:raise ValueError('Series101 result не соответствует закреплённому runner.')
 s101=load101();s101.authorize();return s101,x
def worker_init(s101,bundle,s84v):
 global WORK
 WORK=s101.load89e();WORK.worker_init(bundle,s84v)
def worker_visual(arg):return WORK.worker_visual(arg)
def motion_specs(m86,fixture=False):
 out=[];ident=897
 for rep in range(2):
  for ai,action in enumerate(ACTIONS):
   seed=102010+rep*10+ai;amp=(.66,.98)[rep];speed=(.68,1.20)[(rep+ai)%2]
   out.append({'role':'adapter_frozen_replication','id':ident,'replicate':rep+1,'action':action,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 return out[:3] if fixture else out
def views(fixture=False):
 values=[{'corner_id':805,'view':{'fov_deg':35.,'camera_side':.18,'camera_z':.46,'body_x':3.90,'body_y':-.05}},{'corner_id':806,'view':{'fov_deg':35.,'camera_side':.29,'camera_z':.58,'body_x':4.10,'body_y':.05}},{'corner_id':807,'view':{'fov_deg':35.,'camera_side':.43,'camera_z':.44,'body_x':4.12,'body_y':-.02}},{'corner_id':808,'view':{'fov_deg':35.,'camera_side':.22,'camera_z':.60,'body_x':3.88,'body_y':.04}}]
 return values[:1] if fixture else values

def frozen_visual(s101,source_folder,d_folder,fixture,progress):
 s89=s101.load89e();s89.authorize_d();md=s89.load_d();mc=md.load_c();m6=mc.load_b6();m5=m6.load_b5();m4=m5.load_b4();m3=m4.load_b3();m2=m3.load_b2();m=m2.load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();count=1
 frozen_path,d_summary,angle,identity,common,experts,selections,standard,standard_selections,temp=s89.load_frozen(d_folder,False);frozen_before=manifest(frozen_path);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,False)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 seen={x['motion_sha256'] for x in saved['labels']}|training|m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|m2.authorize_b()|m3.authorize_b2()|s89.authorize_d()
 for old in s89.specs(False):seen.add(stim.motion_hash(np.asarray(old['angles_deg'],float)))
 for old in s101.motion_specs(m86,False):seen.add(stim.motion_hash(np.asarray(old['angles_deg'],float)))
 items=[];desc=[]
 for x in motion_specs(m86,fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series102 motion совпал с training/disclosed/Series101 motion.')
  seen.add(h);item={**x,'motion_sha256':h};items.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'})
 vv=views(fixture);tasks=[(x,v) for x in items for v in vv];progress('Frozen replication visual inference: последовательный режим',.04,0,len(tasks));visual=[];worker_init(s101,bundle,s84v)
 for n,task in enumerate(tasks,1):visual.append(worker_visual(task));progress('Frozen replication visual inference: последовательный режим',.04+.16*n/len(tasks),n,len(tasks))
 cases=[]
 for row in visual:
  targets,probs=md.controls_for(m3,m2,m,b,row['_coeff'],row['_target'],angle,identity,temp,common,float(d_summary['model']['common_selected']['lambda']),experts,selections,standard,standard_selections)
  cases.append({'id':row['id'],'corner_id':row['corner_id'],'action':row['action'],'truth':np.asarray(row['_truth'],float),'targets':{k:np.asarray(targets['candidate' if k=='open_loop' else k],float) for k in CONDITIONS},'predicted_action':ACTIONS[int(np.argmax(probs))],'state_sha256':sha_bytes(np.asarray(row['_coeff'],dtype='<f8').tobytes()),'target_hashes':{k:sha_bytes(np.asarray(targets['candidate' if k=='open_loop' else k],dtype='<f8').tobytes()) for k in CONDITIONS}})
 if before!={p:file_sha(p) for p in before} or frozen_before!=manifest(frozen_path):raise ValueError('Frozen sources изменились.')
 return cases,desc,vv,count,paths[1],frozen_path

def fixture_cases():
 return [{'id':897+i,'corner_id':805,'action':ACTIONS[i],'truth':np.zeros((49,6)),'targets':{k:np.zeros((49,6)) for k in CONDITIONS},'predicted_action':ACTIONS[i],'state_sha256':str(i),'target_hashes':{'candidate':'c'+str(i),'zero_state':'z'+str(i),'shuffled_state':'s'+str(i),'shared_lesion':'l'+str(i),'open_loop':'c'+str(i)}} for i in range(3)]
def fixture_physics(cases):
 rows=[]
 for c in cases:
  controls={}
  for j,name in enumerate(CONDITIONS):controls[name]={'finite':True,'tracking_rmse_rad':.04+.01*j,'truth_rmse_rad':.08 if name=='candidate' else .18+.01*j,'contact_frame_fraction':1.,'mean_contact_legs':3.,'max_actuator_force_norm':8.,'minimum_thorax_z_mm':.8,'maximum_thorax_z_mm':1.2,'energy_abs_work':1.,'torque_saturation_fraction':.01}
  rows.append({'id':c['id'],'corner_id':c['corner_id'],'action':c['action'],'predicted_action':c['action'],'state_sha256':c['state_sha256'],'target_hashes':c['target_hashes'],'controls':controls})
 return rows,[]
def run(source,d_folder,output_root=ROOT,fixture=False,progress=lambda *x:None):
 s101,go101=authorize();root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('frozen89e_flygym_replication_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);temp=folder/'result_incomplete';temp.mkdir(parents=True);progress('Проверяются frozen prerequisites',.01,0,1)
 if fixture:cases=fixture_cases();desc=[];vv=views(True);count=1;model_path=RUNNER101;frozen_path=RESULT101
 else:cases,desc,vv,count,model_path,frozen_path=frozen_visual(s101,source,d_folder,False,progress)
 protocol={'schema':'frozen89e-flygym-replication-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'created_utc':datetime.now(timezone.utc).isoformat(),'series101_runner_sha256':RUNNER101_SHA,'series101_result_sha256':RESULT101_SHA,'training_allowed':False,'selection_allowed':False,'post_result_tuning_allowed':False,'motions':desc,'views':vv,'workers':count,'mapped_dof':list(s101.MAPPED_DOF),'mapping':'unchanged Series101 unit-gain offsets from official neutral pose, clipped ±0.35rad','motor':{'type':'MuJoCo MOTOR','dt_s':s101.DT,'frame_dt_s':s101.FRAME_DT,'kp':s101.KP,'kd':s101.KD,'torque_limit':s101.TORQUE_LIMIT},'controls':list(CONDITIONS),'open_loop_definition':'unchanged Series101: same candidate target, feedforward torque from neutral and target velocity; no q/dq feedback','primary_rule':'unchanged Series101: all candidate safe/contact; mean tracking<=0.20rad; candidate truth RMSE wins vs zero/shuffled>=60%, vs true open-loop>=80%; state target hashes distinct'};save(folder/'protocol.json',protocol)
 trace=[]
 if fixture:rows,trace=fixture_physics(cases)
 else:
  bridge=s101.FlyGymBridge();rows=[];total=len(cases)*len(CONDITIONS);done=0
  for c in cases:
   controls={}
   for name in CONDITIONS:
    metric=bridge.rollout(c['targets'][name],c['truth'],name=='open_loop');sample=metric.pop('sample');controls[name]=metric
    for fi,angles in enumerate(sample):trace.append({'id':c['id'],'corner_id':c['corner_id'],'action':c['action'],'condition':name,'frame':fi,**{s101.MAPPED_DOF[j]:float(angles[j]) for j in range(6)}})
    done+=1;progress('FlyGym frozen replication controls',.20+.76*done/total,done,total)
   rows.append({'id':c['id'],'corner_id':c['corner_id'],'action':c['action'],'predicted_action':c['predicted_action'],'state_sha256':c['state_sha256'],'target_hashes':c['target_hashes'],'controls':controls})
 primary=s101.decision(rows,fixture);report={'schema':'frozen89e-flygym-replication-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':primary,'tests':rows,'limitations':['Frozen physical-adapter replication, not training, selection, or biological evidence.','Series101 mapping, motor parameters, controls, thresholds, and gate are unchanged.','Synthetic truth is used only for scoring and demonstrator command; observer candidate receives frozen89E-derived policy.','No FlyVis, connectome mapping, living animal, muscles, or claim of biological mirror neurons.']};save(temp/'summary.json',report)
 if trace:
  with (temp/'physical_trace.csv').open('w',newline='',encoding='utf8') as f:w=csv.DictWriter(f,fieldnames=list(trace[0]));w.writeheader();w.writerows(trace)
 (temp/'ИТОГ.txt').write_text('SERIES102: FROZEN PHYSICAL-ADAPTER REPLICATION\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\nFrozen replication, не биологический результат.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series102: frozen FlyGym replication');root.geometry('760x420+150+80');root.attributes('-topmost',True);status=tk.StringVar(value='Выберите те же frozen sources и запустите независимую репликацию');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала расчёта');start=[None]
 tk.Label(root,text='Series102: frozen-репликация physical adapter',font=('Arial',13,'bold'),pady=14).pack();tk.Label(root,text='24 новых visual cases × 5 физических controls. Настройки Series101 не меняются.\nОбучения, выбора модели и настройки после результата нет.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=580,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack(pady=(4,0));tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать result89D и source84Z, затем запустить',padx=18,pady=8);button.pack(pady=12)
 def update(text,fraction,done,total):
  def apply():
   percent=round(fraction*100,1);status.set(text);pct.set(percent);overall.set(f'Общий прогресс: {percent:.1f}%'.replace('.',','))
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
    result=run(source,d,progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series102','Frozen-репликация завершена. Папка результата открыта.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-102.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series102',f'{exc}\n\nОтчёт автоматически открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true');a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.',a.output_root,True))
 elif a.source84z and a.result89d:print(run(a.source84z,a.result89d,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d.')
if __name__=='__main__':main()
