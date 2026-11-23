#!/usr/bin/env python3
"""Stage92: four-hour complex development benchmark after Stage91 no-go."""
from __future__ import annotations
import argparse,concurrent.futures,ctypes,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,time,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
STAGE91=HERE/'91_connectome_advantage_stage1.py';STAGE91_SHA='dde8ea3ddd8e1641b5709080163132b23caf729298e9ca821bbadab3a7695a29'
ROOT=Path('workspace/runs/ideas/i-connectome-advantage/stage-2-complex-development')
TARGET_WALL_SECONDS=4*3600
MODELS=('structured96','shuffled96','dense96');BUDGETS=(5,30)
SCENARIOS=(
 ('clean',.12,0,.0),('view_high',.45,0,.0),('occlusion',.28,0,.0),
 ('lesion10',.28,10,.0),('lesion25',.28,24,.0),('state_noise',.28,0,.08),('combined_harsh',.48,24,.08),
)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(path,value):
 path=Path(path);data=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n';last=None
 for attempt in range(8):
  temp=path.parent/f'.{path.name}.{os.getpid()}.{time.time_ns()}.tmp'
  try:
   temp.write_text(data,encoding='utf-8');os.replace(temp,path);return
  except PermissionError as exc:
   last=exc
   try:temp.unlink(missing_ok=True)
   except OSError:pass
   time.sleep(min(.1*(attempt+1),1.0))
 raise last if last else OSError('Не удалось сохранить '+str(path))
def save_checkpoint(path,value):
 try:save(path,value);return True
 except PermissionError as exc:
  data=json.dumps(value,ensure_ascii=False,indent=2)+'\n';fallback=Path(path).with_name('INCOMPLETE-FALLBACK.json')
  try:Path(path).write_text(data,encoding='utf-8');return True
  except OSError:pass
  try:fallback.write_text(data,encoding='utf-8')
  except OSError:pass
  print('ПРЕДУПРЕЖДЕНИЕ: Windows временно заблокировал checkpoint JSON. SQLite уже сохранена; расчёт продолжается. '+str(exc),flush=True);return False
def remove_checkpoint(folder):
 for name in ('INCOMPLETE.json','INCOMPLETE-FALLBACK.json'):
  path=Path(folder)/name
  for attempt in range(10):
   try:path.unlink(missing_ok=True);break
   except PermissionError:time.sleep(min(.1*(attempt+1),.5))
def stage91():
 if sha(STAGE91)!=STAGE91_SHA:raise ValueError('Закреплённый Stage91 runner изменился.')
 spec=importlib.util.spec_from_file_location('connectome_stage91',STAGE91);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def console_guard():
 result={'platform':os.name,'disabled':False}
 if os.name!='nt':return result
 kernel=ctypes.windll.kernel32;handle=kernel.GetStdHandle(-10);mode=ctypes.c_uint()
 if handle in (0,-1) or not kernel.GetConsoleMode(handle,ctypes.byref(mode)):raise OSError('Не удалось прочитать режим консоли.')
 result['before']=int(mode.value);quick=0x0040;extended=0x0080;new=(mode.value|extended)&~quick
 if not kernel.SetConsoleMode(handle,new):raise OSError('Не удалось отключить QuickEdit.')
 verify=ctypes.c_uint();kernel.GetConsoleMode(handle,ctypes.byref(verify));result.update(after=int(verify.value),disabled=not bool(verify.value&quick))
 return result

def prototypes():
 t=np.linspace(0,1,6,endpoint=False)
 return np.array([
  np.stack((np.sin(2*np.pi*t),-np.sin(2*np.pi*t),.12*np.ones(6),np.zeros(6),np.zeros(6),np.zeros(6)),1),
  np.stack((.55+.25*np.sin(2*np.pi*t),.55-.25*np.sin(2*np.pi*t),.35+.12*np.cos(2*np.pi*t),.08*np.sin(2*np.pi*t),np.zeros(6),np.zeros(6)),1),
  np.stack((.35*np.sin(np.pi*t),.35*np.sin(np.pi*t),np.zeros(6),np.zeros(6),np.sin(np.pi*t),.12*np.sin(np.pi*t)),1),
 ],dtype=np.float64)

def dataset(seed,per_class,severity):
 rng=np.random.default_rng(seed);base=prototypes();xs=[];ys=[];labels=[]
 for first in range(3):
  for second in range(3):
   label=first*3+second
   for _ in range(per_class):
    amp1,amp2=rng.uniform(.45,1.25,2);sequence=np.concatenate((base[first]*amp1,base[second]*amp2),0)
    shift=int(rng.integers(-2,3));sequence=np.roll(sequence,shift,axis=0);mix=np.eye(6)+rng.normal(0,severity,(6,6))/np.sqrt(6);observed=sequence@mix+rng.normal(0,.025+severity*.04,sequence.shape)
    if severity>=.25:
     for _ in range(1+int(severity>.4)):observed[int(rng.integers(0,12)),int(rng.integers(0,6))]=0
    target=np.concatenate((np.eye(9)[label],(base[first]*amp1).mean(0),(base[second]*amp2).mean(0)))
    xs.append(observed.reshape(-1));ys.append(target);labels.append(label)
 return np.asarray(xs),np.asarray(ys),np.asarray(labels)

def evaluate(model,x,y,labels,lesion_count,state_noise,seed):
 w,b,v,c=model;hidden=np.tanh(x@w+b);rng=np.random.default_rng(seed)
 if state_noise: hidden=hidden+rng.normal(0,state_noise,hidden.shape)
 if lesion_count: hidden[:,rng.choice(96,lesion_count,replace=False)]=0
 pred=hidden@v+c
 return float(np.mean(np.argmax(pred[:,:9],1)==labels)),float(np.sqrt(np.mean((pred[:,9:]-y[:,9:])**2)))

def replicate(task):
 ident,fixture=task;start_cpu=time.process_time();s=stage91();train_cache={};models={};rows=[]
 masks=s.masks(920000+ident,72,96)
 for budget in BUDGETS:
  x,y,labels=dataset(921000+ident*10+budget,budget,.08);mean=x.mean(0);std=np.maximum(x.std(0),1e-6);x=(x-mean)/std;train_cache[budget]=(mean,std)
  for index,name in enumerate(MODELS):models[(budget,name)]=s.train_model(x,y,masks[name],922000+ident*100+budget*3+index,10 if fixture else 220)
 for budget in BUDGETS:
  mean,std=train_cache[budget]
  for scenario,severity,lesion,noise in SCENARIOS:
   x,y,labels=dataset(923000+ident*100+budget*7+int(severity*100),8 if fixture else 50,severity);x=(x-mean)/std
   for index,name in enumerate(MODELS):
    acc,rmse=evaluate(models[(budget,name)],x,y,labels,lesion,noise,924000+ident*1000+budget*10+index)
    rows.append((ident,budget,scenario,name,acc,rmse))
 harsh={(b,m):(a,r) for _,b,sn,m,a,r in rows if sn=='combined_harsh'};dual=0;total=0
 for budget in BUDGETS:
  sa,sr=harsh[(budget,'structured96')];qa,qr=harsh[(budget,'shuffled96')];dual+=int(sa>qa and sr<qr);total+=1
 return {'replicate':ident,'cpu_seconds':time.process_time()-start_cpu,'rows':rows,'harsh_dual_wins':dual,'harsh_comparisons':total}

def schema(db):
 db.executescript('PRAGMA journal_mode=WAL;CREATE TABLE IF NOT EXISTS replicates(id INTEGER PRIMARY KEY,cpu_seconds REAL NOT NULL,harsh_dual_wins INTEGER NOT NULL,harsh_comparisons INTEGER NOT NULL);CREATE TABLE IF NOT EXISTS metrics(replicate INTEGER,budget INTEGER,scenario TEXT,model TEXT,accuracy REAL,rmse REAL,PRIMARY KEY(replicate,budget,scenario,model));')
def commit_result(db,result):
 db.execute('INSERT OR REPLACE INTO replicates VALUES(?,?,?,?)',(result['replicate'],result['cpu_seconds'],result['harsh_dual_wins'],result['harsh_comparisons']));db.executemany('INSERT OR REPLACE INTO metrics VALUES(?,?,?,?,?,?)',result['rows']);db.commit()
def aggregate(db,count):
 groups={}
 for budget,scenario,model,acc,rmse,n in db.execute('SELECT budget,scenario,model,AVG(accuracy),AVG(rmse),COUNT(*) FROM metrics GROUP BY budget,scenario,model'):
  groups.setdefault(str(budget),{}).setdefault(scenario,{})[model]={'accuracy':acc,'rmse':rmse,'n':n}
 harsh5=groups['5']['combined_harsh'];s=harsh5['structured96'];q=harsh5['shuffled96'];paired=db.execute('SELECT SUM(harsh_dual_wins),SUM(harsh_comparisons) FROM replicates').fetchone();overall=db.execute("SELECT SUM(CASE WHEN s.accuracy>q.accuracy AND s.rmse<q.rmse THEN 1 ELSE 0 END),COUNT(*) FROM metrics s JOIN metrics q ON s.replicate=q.replicate AND s.budget=q.budget AND s.scenario=q.scenario WHERE s.model='structured96' AND q.model='shuffled96'").fetchone()
 gate={'harsh_fewshot_accuracy_margin':s['accuracy']-q['accuracy'],'harsh_fewshot_rmse_ratio':s['rmse']/q['rmse'],'harsh_dual_wins':paired[0] or 0,'harsh_comparisons':paired[1] or 0,'overall_dual_wins':overall[0] or 0,'overall_comparisons':overall[1] or 0}
 gate['candidate_for_frozen_replication']=gate['harsh_fewshot_accuracy_margin']>=.03 and gate['harsh_fewshot_rmse_ratio']<=.97 and gate['harsh_dual_wins']>=math.ceil(.60*gate['harsh_comparisons']) and gate['overall_dual_wins']>=math.ceil(.55*gate['overall_comparisons'])
 return groups,gate

def worker_choice(value):
 raw=str(value).lower().strip()
 if raw=='max':return 'max',max(1,os.cpu_count() or 1)
 n=int(raw)
 if n not in (2,4,6):raise ValueError('Workers должны быть2,4,6 или max.')
 return str(n),n

def latest_incomplete():
 if not ROOT.exists():return None
 found=sorted((p for p in ROOT.glob('complex_*') if not (p/'complete.json').exists() and (p/'protocol.json').exists() and (p/'study.sqlite3').exists() and ((p/'INCOMPLETE.json').exists() or (p/'INCOMPLETE-FALLBACK.json').exists())),key=lambda p:p.stat().st_mtime,reverse=True)
 return found[0] if found else None

def prepare(workers,fixture):
 label,count=worker_choice(workers);ROOT.mkdir(parents=True,exist_ok=True);guard=console_guard();folder=ROOT/('fixture' if fixture else 'complex_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(exist_ok=fixture);db=sqlite3.connect(folder/'study.sqlite3');schema(db)
 print('Калибровка одного полного replicate...' if not fixture else'Bounded fixture...',flush=True);cal=replicate((-1,fixture));cpu=max(cal['cpu_seconds'],.05);target=2 if fixture else max(count*4,math.ceil(TARGET_WALL_SECONDS*count/cpu));target=min(target,2 if fixture else 50000)
 protocol={'schema':'complex-connectome-advantage-v1','mode':'fixture' if fixture else'four_hour_development','biological_result':False,'stage91_sha256':STAGE91_SHA,'script_sha256':sha(__file__),'target_wall_seconds':0 if fixture else TARGET_WALL_SECONDS,'calibration_cpu_seconds':cpu,'fixed_replicates':target,'workers':count,'worker_choice':label,'models':list(MODELS),'budgets_per_ordered_action_class':list(BUDGETS),'ordered_action_classes':9,'scenarios':[list(x) for x in SCENARIOS],'delay_s':.5,'delay_interpretation':'software latent state held without new sensory input; state_noise scenarios test corruption, not biological memory','development_gate':'budget5 combined_harsh: accuracy margin>=0.03, RMSE ratio<=0.97; harsh dual wins>=60%; all-condition dual wins>=55%','console_guard':guard,'limitations':['Development benchmark after disclosed Stage91 no-go; any selected candidate requires independent frozen replication.','96 units and masks are engineered, not biological neurons or FlyWire IDs.','Dense96 is unit-matched but not parameter-matched; shuffled96 is the primary parameter-matched control.','Calibration fixes replicate count before main results but runtime is approximate.']};save(folder/'protocol.json',protocol);save_checkpoint(folder/'INCOMPLETE.json',{'completed':0,'fixed_replicates':target,'worker_cpu_seconds':0});db.close();return folder

def execute(folder):
 protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'));target=protocol['fixed_replicates'];workers=protocol['workers'];fixture=protocol['mode']=='fixture';db=sqlite3.connect(folder/'study.sqlite3');schema(db);done={row[0] for row in db.execute('SELECT id FROM replicates')};remaining=[i for i in range(target) if i not in done];print(f'Комплексный анализ: готово {len(done)}/{target}, workers={workers}.',flush=True)
 with concurrent.futures.ProcessPoolExecutor(max_workers=min(workers,max(1,len(remaining))),mp_context=multiprocessing.get_context('spawn')) as pool:
  chunk_size=max(workers*4,1)
  for offset in range(0,len(remaining),chunk_size):
   futures={pool.submit(replicate,(ident,fixture)):ident for ident in remaining[offset:offset+chunk_size]}
   for future in concurrent.futures.as_completed(futures):
    result=future.result();commit_result(db,result);done.add(result['replicate']);cpu=db.execute('SELECT COALESCE(SUM(cpu_seconds),0) FROM replicates').fetchone()[0];save_checkpoint(folder/'INCOMPLETE.json',{'completed':len(done),'fixed_replicates':target,'worker_cpu_seconds':cpu});
    if len(done)%max(1,workers)==0 or len(done)==target:print(f'  replicates {len(done)}/{target}; worker CPU {cpu/3600:.2f} ч',flush=True)
 groups,gate=aggregate(db,target);cpu=db.execute('SELECT SUM(cpu_seconds) FROM replicates').fetchone()[0];db.close();summary={'schema':'complex-connectome-advantage-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'completed_replicates':target,'worker_cpu_seconds':cpu,'aggregate':groups,'development_gate':gate,'interpretation':'candidate_only_requires_frozen_replication' if gate['candidate_for_frozen_replication'] else'no_candidate'};save(folder/'summary.json',summary);lines=['КОМПЛЕКСНЫЙ CONNECTOME ADVANTAGE,4 ЧАСА',f'Replicates: {target}; worker CPU: {cpu/3600:.2f} ч.',f'Кандидат для frozen replication: {gate["candidate_for_frozen_replication"]}.',f'Few-shot harsh accuracy margin: {gate["harsh_fewshot_accuracy_margin"]:.6f}.',f'Few-shot harsh RMSE ratio: {gate["harsh_fewshot_rmse_ratio"]:.6f}.',f'Harsh dual wins: {gate["harsh_dual_wins"]}/{gate["harsh_comparisons"]}.',f'All-condition dual wins: {gate["overall_dual_wins"]}/{gate["overall_comparisons"]}.','Это development artificial96, не реальные нейроны. Даже go требует отдельной frozen replication.'];(folder/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');save(folder/'complete.json',{'protocol_sha256':sha(folder/'protocol.json'),'summary_sha256':sha(folder/'summary.json'),'database_sha256':sha(folder/'study.sqlite3')});remove_checkpoint(folder);print('Готово:',folder,flush=True);return folder

def choose():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Комплексный Connectome Advantage: около4 часов');root.geometry('760x390+150+100');root.attributes('-topmost',True);choice=tk.StringVar(value='6');go={'value':False}
 old=latest_incomplete();text='Комплексный development benchmark: ordered actions, few-shot5/30,\nновые ракурсы, окклюзия, state corruption, lesions10/25 и combined stress.\nВремя около4 часов; fixed count определяется калибровкой до основных результатов.\nЭто artificial96 и не разрешает FlyWire mapping.'
 tk.Label(root,text=text,font=('Arial',11),padx=18,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for title,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=title,variable=choice,value=value).pack(anchor='center')
 def start():go['value']=True;root.quit()
 label='Продолжить незавершённый расчёт' if old else'Начать новый расчёт примерно на4 часа';tk.Button(root,text=label,command=start,padx=20,pady=9).pack(pady=17);root.mainloop()
 if not go['value']:root.destroy();return
 root.withdraw();folder=old if old else prepare(choice.get(),False);result=execute(folder)
 if os.name=='nt':os.startfile(str(result));os.startfile(str(result/'ИТОГ.txt'))
 messagebox.showinfo('Расчёт завершён','Открыты папка результата и ИТОГ.txt.\n\n'+str(result.resolve()),parent=root);root.destroy()

def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-КОМПЛЕКСНЫЙ.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('КОМПЛЕКСНЫЙ АНАЛИЗ: ОШИБКА\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
 if os.name=='nt':
  try:os.startfile(str(path))
  except OSError:pass
 try:
  import tkinter as tk
  from tkinter import messagebox
  root=tk.Tk();root.withdraw();messagebox.showerror('Расчёт остановлен','Ошибка сохранена в копируемый файл:\n'+str(path.resolve()),parent=root);root.destroy()
 except Exception:pass
 return path

def main():
 p=argparse.ArgumentParser();p.add_argument('--choose',action='store_true');p.add_argument('--workers',default='6');p.add_argument('--fixture',action='store_true');p.add_argument('--folder');a=p.parse_args()
 if a.choose:choose()
 elif a.folder:execute(Path(a.folder))
 else:execute(prepare(a.workers,a.fixture))
if __name__=='__main__':
 try:main()
 except Exception as exc:report=failure_report(exc);print(f'ОШИБКА: {exc}\nОтчёт: {report.resolve()}',file=sys.stderr);sys.exit(1)
