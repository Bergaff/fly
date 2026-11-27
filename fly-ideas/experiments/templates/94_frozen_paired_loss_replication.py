#!/usr/bin/env python3
"""Stage94: frozen replication of the Stage92 diagnosis-derived paired-loss correction."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,time,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
STAGE92=HERE/'92_complex_connectome_advantage.py';STAGE92_SHA='0dbbdcb91fff86ab059e975ded8c358dae345c1b6429795ead516faabe8c4439'
ROOT=Path('workspace/runs/ideas/i-connectome-advantage/stage-4-frozen-paired-loss')
MODELS=('structured96','shuffled96','dense96');BUDGETS=(5,30);TRAJECTORY_WEIGHT=4.0;FIXED_REPLICATES=2048
SCENARIOS=(('clean',.12,0,.0),('view_high',.45,0,.0),('occlusion',.28,0,.0),('lesion10',.28,10,.0),('lesion25',.28,24,.0),('state_noise',.28,0,.08),('combined_harsh',.48,24,.08))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stage92():
 if sha(STAGE92)!=STAGE92_SHA:raise ValueError('Закреплённый Stage92 runner изменился.')
 spec=importlib.util.spec_from_file_location('stage92_frozen_source',STAGE92);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def train_weighted(x,y,mask,seed,epochs):
 rng=np.random.default_rng(seed);n,d=x.shape;h=mask.shape[1];o=y.shape[1];fan=np.maximum(1,mask.sum(0));w=rng.normal(0,1,(d,h))/np.sqrt(fan)[None,:]*mask;b=np.zeros(h);v=rng.normal(0,.08,(h,o));c=np.zeros(o);params=[w,b,v,c];mom=[np.zeros_like(q) for q in params];vel=[np.zeros_like(q) for q in params];step=0
 for _ in range(epochs):
  for start in rng.permutation(np.arange(0,n,64)):
   ids=np.arange(start,min(start+64,n));xb=x[ids];yb=y[ids];hidden=np.tanh(xb@w+b);pred=hidden@v+c;delta=2*(pred-yb)/(len(ids)*o);delta[:,9:]*=TRAJECTORY_WEIGHT;dh=(delta@v.T)*(1-hidden**2);grads=[xb.T@dh*mask,dh.sum(0),hidden.T@delta,delta.sum(0)];step+=1
   for i,(parameter,grad) in enumerate(zip(params,grads)):
    mom[i]=.9*mom[i]+.1*grad;vel[i]=.999*vel[i]+.001*grad*grad;parameter-=.006*(mom[i]/(1-.9**step))/(np.sqrt(vel[i]/(1-.999**step))+1e-8)
  w*=mask
 return w,b,v,c

def replicate(task):
 ident,fixture=task;start=time.process_time();s=stage92();st=s.stage91();cache={};models={};rows=[];masks=st.masks(94000000+ident,72,96)
 for budget in BUDGETS:
  x,y,labels=s.dataset(94100000+ident*10+budget,budget,.08);mean=x.mean(0);std=np.maximum(x.std(0),1e-6);x=(x-mean)/std;cache[budget]=(mean,std);shared_train_seed=94200000+ident*100+budget*3
  for name in MODELS:models[(budget,name)]=train_weighted(x,y,masks[name],shared_train_seed,10 if fixture else 220)
 for budget in BUDGETS:
  mean,std=cache[budget]
  for scenario,severity,lesion,noise in SCENARIOS:
   x,y,labels=s.dataset(94300000+ident*100+budget*7+int(severity*100),8 if fixture else 50,severity);x=(x-mean)/std;shared_eval_seed=94400000+ident*1000+budget*10+sum(map(ord,scenario))
   for name in MODELS:
    acc,rmse=s.evaluate(models[(budget,name)],x,y,labels,lesion,noise,shared_eval_seed);rows.append((ident,budget,scenario,name,acc,rmse))
 return {'replicate':ident,'cpu_seconds':time.process_time()-start,'rows':rows}

def schema(db):db.executescript('PRAGMA journal_mode=WAL;CREATE TABLE IF NOT EXISTS replicates(id INTEGER PRIMARY KEY,cpu_seconds REAL NOT NULL);CREATE TABLE IF NOT EXISTS metrics(replicate INTEGER,budget INTEGER,scenario TEXT,model TEXT,accuracy REAL,rmse REAL,PRIMARY KEY(replicate,budget,scenario,model));')
def commit(db,result):db.execute('INSERT OR REPLACE INTO replicates VALUES(?,?)',(result['replicate'],result['cpu_seconds']));db.executemany('INSERT OR REPLACE INTO metrics VALUES(?,?,?,?,?,?)',result['rows']);db.commit()
def wilson_lower(k,n,z=1.959963984540054):
 p=k/n;den=1+z*z/n;return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den

def aggregate(db):
 groups={}
 for budget,scenario,model,acc,rmse,n in db.execute('SELECT budget,scenario,model,AVG(accuracy),AVG(rmse),COUNT(*) FROM metrics GROUP BY budget,scenario,model'):
  groups.setdefault(str(budget),{}).setdefault(scenario,{})[model]={'accuracy':acc,'rmse':rmse,'n':n}
 def dual(where,args=()):return db.execute("SELECT SUM(CASE WHEN s.accuracy>q.accuracy AND s.rmse<q.rmse THEN 1 ELSE 0 END),COUNT(*) FROM metrics s JOIN metrics q ON s.replicate=q.replicate AND s.budget=q.budget AND s.scenario=q.scenario WHERE s.model='structured96' AND q.model='shuffled96' "+where,args).fetchone()
 harsh=dual("AND s.scenario='combined_harsh'");overall=dual('');h=groups['5']['combined_harsh'];ss=h['structured96'];q=h['shuffled96'];gate={'harsh_fewshot_accuracy_margin':ss['accuracy']-q['accuracy'],'harsh_fewshot_rmse_ratio':ss['rmse']/q['rmse'],'harsh_dual_wins':harsh[0] or 0,'harsh_comparisons':harsh[1],'harsh_dual_rate':(harsh[0] or 0)/harsh[1],'harsh_wilson95_lower':wilson_lower(harsh[0] or 0,harsh[1]),'overall_dual_wins':overall[0] or 0,'overall_comparisons':overall[1],'overall_dual_rate':(overall[0] or 0)/overall[1],'overall_wilson95_lower':wilson_lower(overall[0] or 0,overall[1])}
 gate['frozen_pass']=gate['harsh_fewshot_accuracy_margin']>=.03 and gate['harsh_fewshot_rmse_ratio']<=.97 and gate['harsh_wilson95_lower']>=.60 and gate['overall_wilson95_lower']>=.55
 return groups,gate

def worker_choice(value):
 raw=str(value).lower().strip()
 if raw=='max':return 'max',max(1,os.cpu_count() or 1)
 n=int(raw)
 if n not in (2,4,6):raise ValueError('Workers должны быть2,4,6 или max.')
 return str(n),n

def latest_incomplete():
 if not ROOT.exists():return None
 found=[p for p in ROOT.glob('frozen_*') if (p/'protocol.json').exists() and (p/'study.sqlite3').exists() and not (p/'complete.json').exists()]
 return max(found,key=lambda p:p.stat().st_mtime) if found else None

def prepare(workers,fixture):
 s=stage92();label,count=worker_choice(workers);ROOT.mkdir(parents=True,exist_ok=True);folder=ROOT/('fixture' if fixture else'frozen_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(exist_ok=fixture);db=sqlite3.connect(folder/'study.sqlite3');schema(db);db.close();target=2 if fixture else FIXED_REPLICATES
 protocol={'schema':'stage94-frozen-paired-loss-v1','mode':'fixture' if fixture else'frozen_replication','biological_result':False,'source_stage92_sha256':STAGE92_SHA,'script_sha256':sha(__file__),'fixed_replicates':target,'workers':count,'worker_choice':label,'seed_namespace':'94000000-series; not Stage92 or disclosed 64/96-replicate development pilots','models':list(MODELS),'trajectory_loss_weight':TRAJECTORY_WEIGHT,'common_random_numbers':{'training_initialization':True,'minibatch_order':True,'lesion_indices':True,'state_noise':True},'budgets':list(BUDGETS),'scenarios':[list(x) for x in SCENARIOS],'frozen_gate':'few-shot harsh margin>=0.03; RMSE ratio<=0.97; harsh Wilson95 lower>=0.60; overall Wilson95 lower>=0.55','selection_disclosure':'weight4 and common-random-number correction selected after Stage92 diagnosis and disclosed bounded development pilots','limitations':['Frozen computational replication of an engineered candidate, not biological evidence.','96 units are software units, not neurons or FlyWire IDs.','No threshold may be weakened after results.']};s.save(folder/'protocol.json',protocol);s.save_checkpoint(folder/'INCOMPLETE.json',{'completed':0,'fixed_replicates':target,'worker_cpu_seconds':0});return folder

def execute(folder,progress=None):
 s=stage92();folder=Path(folder);protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'));target=protocol['fixed_replicates'];workers=protocol['workers'];fixture=protocol['mode']=='fixture';db=sqlite3.connect(folder/'study.sqlite3');schema(db);done={r[0] for r in db.execute('SELECT id FROM replicates')};remaining=[i for i in range(target) if i not in done]
 if progress:progress(len(done),target,0)
 with concurrent.futures.ProcessPoolExecutor(max_workers=min(workers,max(1,len(remaining))),mp_context=multiprocessing.get_context('spawn')) as pool:
  chunk=max(1,workers*4)
  for offset in range(0,len(remaining),chunk):
   futures=[pool.submit(replicate,(i,fixture)) for i in remaining[offset:offset+chunk]]
   for future in concurrent.futures.as_completed(futures):
    result=future.result();commit(db,result);done.add(result['replicate']);cpu=db.execute('SELECT COALESCE(SUM(cpu_seconds),0) FROM replicates').fetchone()[0];s.save_checkpoint(folder/'INCOMPLETE.json',{'completed':len(done),'fixed_replicates':target,'worker_cpu_seconds':cpu})
    if progress:progress(len(done),target,cpu)
 groups,gate=aggregate(db);cpu=db.execute('SELECT SUM(cpu_seconds) FROM replicates').fetchone()[0];db.close();summary={'schema':'stage94-frozen-paired-loss-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'completed_replicates':target,'worker_cpu_seconds':cpu,'aggregate':groups,'frozen_gate':gate,'interpretation':'computational_candidate_replicated' if gate['frozen_pass'] else'frozen_no_go'};s.save(folder/'summary.json',summary);lines=['STAGE94: FROZEN PAIRED-LOSS REPLICATION',f'Replicates: {target}; worker CPU: {cpu/3600:.3f} ч.',f'Frozen pass: {gate["frozen_pass"]}.',f'Few-shot harsh accuracy margin: {gate["harsh_fewshot_accuracy_margin"]:.6f}.',f'Few-shot harsh RMSE ratio: {gate["harsh_fewshot_rmse_ratio"]:.6f}.',f'Harsh dual: {gate["harsh_dual_wins"]}/{gate["harsh_comparisons"]}; Wilson lower {gate["harsh_wilson95_lower"]:.6f}.',f'Overall dual: {gate["overall_dual_wins"]}/{gate["overall_comparisons"]}; Wilson lower {gate["overall_wilson95_lower"]:.6f}.','Это artificial96 computational replication, не реальные нейроны и не FlyWire.'];(folder/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');s.save(folder/'complete.json',{'protocol_sha256':sha(folder/'protocol.json'),'summary_sha256':sha(folder/'summary.json'),'database_sha256':sha(folder/'study.sqlite3')});s.remove_checkpoint(folder);return folder

def choose():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Stage94: frozen paired-loss replication');root.geometry('780x420+140+90');root.attributes('-topmost',True);choice=tk.StringVar(value='6');started={'v':False};old=latest_incomplete()
 tk.Label(root,text='Frozen computational replication после диагностики Stage92.\nИсправление честности: одинаковые initialization, batch order, lesion и state-noise.\nTrajectory loss weight4 выбран только на раскрытом development pilot.\n2048 новых replicates; gate усилен нижней границей Wilson95.\nЭто artificial96, не нейроны и не FlyWire.',font=('Arial',11),padx=18,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for title,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=title,variable=choice,value=value).pack()
 def start():started['v']=True
 tk.Button(root,text='Продолжить frozen replication' if old else'Начать frozen replication',command=start,padx=20,pady=9).pack(pady=14)
 while not started['v']:
  try:root.update();time.sleep(.03)
  except tk.TclError:return
 folder=old if old else prepare(choice.get(),False)
 for widget in root.winfo_children():widget.destroy()
 root.protocol('WM_DELETE_WINDOW',lambda:None);label=tk.Label(root,text='Подготовка...',font=('Arial',13),padx=30,pady=50);label.pack();detail=tk.Label(root,text='',font=('Arial',10));detail.pack()
 def progress(done,total,cpu):label.config(text=f'Расчёт: {done}/{total}');detail.config(text=f'Worker CPU: {cpu/3600:.3f} ч.\nПрогресс сохранён в SQLite. Окно можно оставить в фоне.');root.update()
 try:result=execute(folder,progress)
 except Exception as exc:
  report=failure_report(exc);messagebox.showerror('Stage94 остановлен','Ошибка сохранена:\n'+str(report.resolve()),parent=root);os.startfile(str(report));root.destroy();return
 os.startfile(str(result));os.startfile(str(result/'ИТОГ.txt'));messagebox.showinfo('Stage94 завершён','Открыты папка и ИТОГ.txt.\n\n'+str(result.resolve()),parent=root);root.destroy()

def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-STAGE94.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('STAGE94: ОШИБКА\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');return path

def main():
 p=argparse.ArgumentParser();p.add_argument('--choose',action='store_true');p.add_argument('--workers',default='2');p.add_argument('--fixture',action='store_true');p.add_argument('--folder');a=p.parse_args()
 if a.choose:choose()
 elif a.folder:execute(Path(a.folder))
 else:execute(prepare(a.workers,a.fixture))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  report=failure_report(exc);print(f'ОШИБКА: {exc}\nОтчёт: {report.resolve()}',file=sys.stderr);raise SystemExit(1)
