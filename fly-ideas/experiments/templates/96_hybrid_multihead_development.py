#!/usr/bin/env python3
"""Stage96: eight-hour exact-budget hybrid multi-head development benchmark."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,time,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
STAGE95=HERE/'95_strong_controls_development.py';STAGE95_SHA='58b74a79bf7f2edd9c589c579019d94bf4908354f2734628e575de4b1677425a'
ROOT=Path('workspace/runs/ideas/i-connectome-advantage/stage-6-hybrid-multihead-development')
TARGET_WALL_SECONDS=8*3600;BUDGETS=(5,30)
HYBRIDS=('hybrid_structured','hybrid_shuffled','hybrid_temporal','hybrid_learned');MONOLITHIC=('learned_sparse96','rnn54');MODELS=HYBRIDS+MONOLITHIC
SCENARIOS=(('clean',.12,0,.0),('view_high',.45,0,.0),('occlusion',.28,0,.0),('lesion10',.28,10,.0),('lesion25',.28,24,.0),('state_noise',.28,0,.08),('combined_harsh',.48,24,.08))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stage95():
 if sha(STAGE95)!=STAGE95_SHA:raise ValueError('Закреплённый Stage95 runner изменился.')
 spec=importlib.util.spec_from_file_location('stage95_hybrid_source',STAGE95);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def temporal_mask61():
 mask=np.zeros((72,61),dtype=np.float64)
 for unit in range(61):
  start=unit%9
  for t in range(start,start+4):mask[t*6:(t+1)*6,unit]=1
 return mask

def train_classifier(x,y,mask,init_seed,order_seed,epochs,learned=False):
 target=y[:,:9];init=np.random.default_rng(init_seed);order=np.random.default_rng(order_seed);n,d=x.shape;h=61;o=9;active=1464;current=np.ones((d,h)) if learned else mask.copy();fan=np.maximum(1,current.sum(0));w=init.normal(0,1,(d,h))/np.sqrt(fan)[None,:]*current;b=np.zeros(h);v=init.normal(0,.08,(h,o));c=np.zeros(o);params=[w,b,v,c];mom=[np.zeros_like(q) for q in params];vel=[np.zeros_like(q) for q in params];step=0;prune_epoch=max(1,epochs//5)
 for epoch in range(epochs):
  for start in order.permutation(np.arange(0,n,64)):
   ids=np.arange(start,min(start+64,n));xb=x[ids];yb=target[ids];hidden=np.tanh(xb@w+b);pred=hidden@v+c;delta=2*(pred-yb)/(len(ids)*o);dh=(delta@v.T)*(1-hidden**2);grads=[xb.T@dh*current,dh.sum(0),hidden.T@delta,delta.sum(0)];step+=1
   for i,(parameter,grad) in enumerate(zip(params,grads)):
    mom[i]=.9*mom[i]+.1*grad;vel[i]=.999*vel[i]+.001*grad*grad;parameter-=.006*(mom[i]/(1-.9**step))/(np.sqrt(vel[i]/(1-.999**step))+1e-8)
  if learned and epoch+1==prune_epoch:
   keep=np.argpartition(np.abs(w).ravel(),-active)[-active:];current=np.zeros(w.size);current[keep]=1;current=current.reshape(w.shape);w*=current;mom[0]*=current;vel[0]*=current
  w*=current
 return w,b,v,c,current

def rnn40_mask():
 mask=np.ones((40,40),dtype=np.float64)
 for i in range(18):mask[i,i]=0
 return mask

def train_trajectory(x,y,init_seed,order_seed,epochs):
 target=y[:,9:];init=np.random.default_rng(init_seed);order=np.random.default_rng(order_seed);n=len(x);h=40;o=12;rmask=rnn40_mask();wx=init.normal(0,1/np.sqrt(6),(6,h));wh=init.normal(0,1/np.sqrt(h),(h,h))*rmask;b=np.zeros(h);v=init.normal(0,.08,(h,o));c=np.zeros(o);params=[wx,wh,b,v,c];mom=[np.zeros_like(q) for q in params];vel=[np.zeros_like(q) for q in params];step=0;seq=x.reshape(n,12,6)
 for _ in range(epochs):
  for start in order.permutation(np.arange(0,n,64)):
   ids=np.arange(start,min(start+64,n));xb=seq[ids];yb=target[ids];states=[np.zeros((len(ids),h))]
   for t in range(12):states.append(np.tanh(xb[:,t]@wx+states[-1]@wh+b))
   pred=states[-1]@v+c;delta=2*(pred-yb)/(len(ids)*o);gv=states[-1].T@delta;gc=delta.sum(0);gwx=np.zeros_like(wx);gwh=np.zeros_like(wh);gb=np.zeros_like(b);dh=delta@v.T
   for t in range(11,-1,-1):dz=dh*(1-states[t+1]**2);gwx+=xb[:,t].T@dz;gwh+=states[t].T@dz;gb+=dz.sum(0);dh=dz@wh.T
   grads=[gwx,gwh*rmask,gb,gv,gc];step+=1
   for i,(parameter,grad) in enumerate(zip(params,grads)):
    mom[i]=.9*mom[i]+.1*grad;vel[i]=.999*vel[i]+.001*grad*grad;parameter-=.006*(mom[i]/(1-.9**step))/(np.sqrt(vel[i]/(1-.999**step))+1e-8)
   wh*=rmask
 return wx,wh,b,v,c,rmask

def hybrid_eval(classifier,trajectory,x,y,labels,lesion_count,state_noise,seed):
 w,b,v,c,_=classifier;class_hidden=np.tanh(x@w+b);class_pred=class_hidden@v+c;wx,wh,tb,tv,tc,_=trajectory;traj_hidden=np.zeros((len(x),40));seq=x.reshape(len(x),12,6)
 for t in range(12):traj_hidden=np.tanh(seq[:,t]@wx+traj_hidden@wh+tb)
 traj_pred=traj_hidden@tv+tc;rng=np.random.default_rng(seed)
 if state_noise:
  class_hidden+=rng.normal(0,state_noise,class_hidden.shape);traj_hidden+=rng.normal(0,state_noise,traj_hidden.shape)
 if lesion_count:
  total=max(1,round(lesion_count*101/96));class_count=round(total*61/101);traj_count=total-class_count
  if class_count:class_hidden[:,rng.choice(61,class_count,replace=False)]=0
  if traj_count:traj_hidden[:,rng.choice(40,traj_count,replace=False)]=0
 if state_noise or lesion_count:class_pred=class_hidden@v+c;traj_pred=traj_hidden@tv+tc
 return float(np.mean(np.argmax(class_pred,1)==labels)),float(np.sqrt(np.mean((traj_pred-y[:,9:])**2)))

def replicate(task):
 ident,fixture=task;s95=stage95();s=s95.stage92();st=s.stage91();started=time.process_time();cache={};models={};rows=[];small=st.masks(96000000+ident,72,61);large=st.masks(96050000+ident,72,96);class_masks={'hybrid_structured':small['structured96'],'hybrid_shuffled':small['shuffled96'],'hybrid_temporal':temporal_mask61()}
 for budget in BUDGETS:
  x,y,labels=s.dataset(96100000+ident*10+budget,budget,.08);mean=x.mean(0);std=np.maximum(x.std(0),1e-6);x=(x-mean)/std;cache[budget]=(mean,std);epochs=10 if fixture else 220;init_seed=96200000+ident*100+budget*3;order_seed=96250000+ident*100+budget*3
  trajectory=train_trajectory(x,y,init_seed+7,order_seed+7,epochs)
  for name in ('hybrid_structured','hybrid_shuffled','hybrid_temporal'):models[(budget,name)]=(train_classifier(x,y,class_masks[name],init_seed,order_seed,epochs),trajectory)
  models[(budget,'hybrid_learned')]=(train_classifier(x,y,np.ones((72,61)),init_seed,order_seed,epochs,True),trajectory)
  models[(budget,'learned_sparse96')]=s95.train_static(x,y,np.ones((72,96)),init_seed,order_seed,epochs,True);models[(budget,'rnn54')]=s95.train_rnn(x,y,init_seed,order_seed,epochs)
 for budget in BUDGETS:
  mean,std=cache[budget]
  for scenario,severity,lesion,noise in SCENARIOS:
   x,y,labels=s.dataset(96300000+ident*100+budget*7+int(severity*100),8 if fixture else 50,severity);x=(x-mean)/std;eval_seed=96400000+ident*1000+budget*10+sum(map(ord,scenario))
   for name in MODELS:
    model=models[(budget,name)];acc,rmse=hybrid_eval(*model,x,y,labels,lesion,noise,eval_seed) if name in HYBRIDS else s95.evaluate(model,x,y,labels,lesion,noise,eval_seed);rows.append((ident,budget,scenario,name,acc,rmse))
 return {'replicate':ident,'cpu_seconds':time.process_time()-started,'rows':rows}

def schema(db):db.executescript('PRAGMA journal_mode=WAL;CREATE TABLE IF NOT EXISTS replicates(id INTEGER PRIMARY KEY,cpu_seconds REAL NOT NULL);CREATE TABLE IF NOT EXISTS metrics(replicate INTEGER,budget INTEGER,scenario TEXT,model TEXT,accuracy REAL,rmse REAL,PRIMARY KEY(replicate,budget,scenario,model));')
def commit(db,result):db.execute('INSERT OR REPLACE INTO replicates VALUES(?,?)',(result['replicate'],result['cpu_seconds']));db.executemany('INSERT OR REPLACE INTO metrics VALUES(?,?,?,?,?,?)',result['rows']);db.commit()
def wilson_lower(k,n,z=1.959963984540054):
 p=k/n;den=1+z*z/n;return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den

def aggregate(db):
 groups={}
 for budget,scenario,model,acc,rmse,n in db.execute('SELECT budget,scenario,model,AVG(accuracy),AVG(rmse),COUNT(*) FROM metrics GROUP BY budget,scenario,model'):groups.setdefault(str(budget),{}).setdefault(scenario,{})[model]={'accuracy':acc,'rmse':rmse,'n':n}
 candidate='hybrid_structured';class_controls=('hybrid_shuffled','hybrid_temporal','hybrid_learned');classification={};joint={}
 def paired(control,metric,harsh):
  op='>' if metric=='accuracy' else '<';extra="AND s.scenario='combined_harsh'" if harsh else''
  return db.execute(f"SELECT SUM(CASE WHEN s.{metric}{op}q.{metric} THEN 1 ELSE 0 END),COUNT(*) FROM metrics s JOIN metrics q ON s.replicate=q.replicate AND s.budget=q.budget AND s.scenario=q.scenario WHERE s.model=? AND q.model=? {extra}",(candidate,control)).fetchone()
 for control in class_controls:
  h=groups['5']['combined_harsh'];harsh=paired(control,'accuracy',True);overall=paired(control,'accuracy',False);classification[control]={'fewshot_harsh_accuracy_margin':h[candidate]['accuracy']-h[control]['accuracy'],'harsh_accuracy_wilson95_lower':wilson_lower(harsh[0] or 0,harsh[1]),'overall_accuracy_wilson95_lower':wilson_lower(overall[0] or 0,overall[1])}
 for control in MONOLITHIC:
  h=groups['5']['combined_harsh'];rmse_h=paired(control,'rmse',True);rmse_o=paired(control,'rmse',False);dual_h=db.execute("SELECT SUM(CASE WHEN s.accuracy>q.accuracy AND s.rmse<q.rmse THEN 1 ELSE 0 END),COUNT(*) FROM metrics s JOIN metrics q ON s.replicate=q.replicate AND s.budget=q.budget AND s.scenario=q.scenario WHERE s.model=? AND q.model=? AND s.scenario='combined_harsh'",(candidate,control)).fetchone();dual_o=db.execute("SELECT SUM(CASE WHEN s.accuracy>q.accuracy AND s.rmse<q.rmse THEN 1 ELSE 0 END),COUNT(*) FROM metrics s JOIN metrics q ON s.replicate=q.replicate AND s.budget=q.budget AND s.scenario=q.scenario WHERE s.model=? AND q.model=?",(candidate,control)).fetchone();joint[control]={'fewshot_harsh_accuracy_margin':h[candidate]['accuracy']-h[control]['accuracy'],'fewshot_harsh_rmse_ratio':h[candidate]['rmse']/h[control]['rmse'],'harsh_rmse_wilson95_lower':wilson_lower(rmse_h[0] or 0,rmse_h[1]),'overall_rmse_wilson95_lower':wilson_lower(rmse_o[0] or 0,rmse_o[1]),'harsh_dual_wilson95_lower':wilson_lower(dual_h[0] or 0,dual_h[1]),'overall_dual_wilson95_lower':wilson_lower(dual_o[0] or 0,dual_o[1])}
 class_pass=classification['hybrid_shuffled']['fewshot_harsh_accuracy_margin']>=.02 and all(v['fewshot_harsh_accuracy_margin']>0 and v['harsh_accuracy_wilson95_lower']>=.55 and v['overall_accuracy_wilson95_lower']>=.55 for v in classification.values());joint_pass=all(v['fewshot_harsh_accuracy_margin']>0 and v['fewshot_harsh_rmse_ratio']<1 and v['harsh_rmse_wilson95_lower']>=.50 and v['overall_rmse_wilson95_lower']>=.50 and v['harsh_dual_wilson95_lower']>=.50 and v['overall_dual_wilson95_lower']>=.50 for v in joint.values());gate={'classification_branch_pass':class_pass,'joint_vs_monolithic_pass':joint_pass,'development_candidate':class_pass and joint_pass,'classification':classification,'joint':joint};return groups,gate

def worker_choice(value):
 raw=str(value).lower().strip()
 if raw=='max':return 'max',max(1,os.cpu_count() or 1)
 n=int(raw)
 if n not in (2,4,6):raise ValueError('Workers должны быть2,4,6 или max.')
 return str(n),n

def latest_incomplete():
 if not ROOT.exists():return None
 found=[p for p in ROOT.glob('hybrid_*') if (p/'protocol.json').exists() and (p/'study.sqlite3').exists() and not (p/'complete.json').exists()];return max(found,key=lambda p:p.stat().st_mtime) if found else None

def prepare(workers,fixture):
 s95=stage95();s=s95.stage92();label,count=worker_choice(workers);ROOT.mkdir(parents=True,exist_ok=True);folder=ROOT/('fixture' if fixture else 'hybrid_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(exist_ok=fixture);db=sqlite3.connect(folder/'study.sqlite3');schema(db);cal=replicate((-1,fixture));cpu=max(cal['cpu_seconds'],.1);target=2 if fixture else min(50000,max(count*4,math.ceil(TARGET_WALL_SECONDS*count/cpu)));protocol={'schema':'stage96-hybrid-multihead-development-v1','mode':'fixture' if fixture else 'eight_hour_development','biological_result':False,'stage95_sha256':STAGE95_SHA,'script_sha256':sha(__file__),'target_wall_seconds':0 if fixture else TARGET_WALL_SECONDS,'calibration_cpu_seconds':cpu,'fixed_replicates':target,'workers':count,'worker_choice':label,'models':list(MODELS),'parameter_count_each':4437,'hybrid_budget':{'classifier':'61-unit static branch,1464 input +61 bias +549 output +9 bias =2083','trajectory':'40-unit RNN,18 fixed recurrent zeros =2354','total':4437},'controls':['same-budget shuffled/temporal/learned classifier hybrids','monolithic learned_sparse96','monolithic rnn54'],'seed_namespace':'96000000-series; development','gate':'classification branch beats all hybrid controls; full hybrid beats learned_sparse96 and rnn54 on mean accuracy/RMSE and Wilson-lower paired RMSE/dual','limitations':['Development selection after disclosed Stage95; requires new frozen seeds if pass.','Task-specialized hybrid is engineered from observed tradeoff.','Software architectures only, not neurons or connectomes.']};s.save(folder/'protocol.json',protocol);s.save_checkpoint(folder/'INCOMPLETE.json',{'completed':0,'fixed_replicates':target,'worker_cpu_seconds':0});db.close();return folder

def execute(folder,progress=None):
 s=stage95().stage92();folder=Path(folder);protocol=json.loads((folder/'protocol.json').read_text());target=protocol['fixed_replicates'];workers=protocol['workers'];fixture=protocol['mode']=='fixture';db=sqlite3.connect(folder/'study.sqlite3');schema(db);done={r[0] for r in db.execute('SELECT id FROM replicates')};remaining=[i for i in range(target) if i not in done];session_start=time.time();session_initial=len(done)
 if progress:progress(len(done),target,0,None)
 with concurrent.futures.ProcessPoolExecutor(max_workers=min(workers,max(1,len(remaining))),mp_context=multiprocessing.get_context('spawn')) as pool:
  for offset in range(0,len(remaining),max(1,workers*3)):
   futures=[pool.submit(replicate,(i,fixture)) for i in remaining[offset:offset+max(1,workers*3)]]
   for future in concurrent.futures.as_completed(futures):
    result=future.result();commit(db,result);done.add(result['replicate']);cpu=db.execute('SELECT COALESCE(SUM(cpu_seconds),0) FROM replicates').fetchone()[0];s.save_checkpoint(folder/'INCOMPLETE.json',{'completed':len(done),'fixed_replicates':target,'worker_cpu_seconds':cpu})
    if progress:
     completed=len(done)-session_initial;eta=(target-len(done))*(time.time()-session_start)/completed if completed else None;progress(len(done),target,cpu,eta)
 groups,gate=aggregate(db);cpu=db.execute('SELECT SUM(cpu_seconds) FROM replicates').fetchone()[0];db.close();summary={'schema':'stage96-hybrid-multihead-result-v1','status':'fixture_completed' if fixture else 'completed','protocol':protocol,'completed_replicates':target,'worker_cpu_seconds':cpu,'aggregate':groups,'development_gate':gate,'interpretation':'candidate_for_frozen_replication' if gate['development_candidate'] else 'no_candidate'};s.save(folder/'summary.json',summary);lines=['STAGE96: HYBRID MULTI-HEAD DEVELOPMENT',f'Replicates: {target}; worker CPU: {cpu/3600:.3f} ч.',f'Classification branch pass: {gate["classification_branch_pass"]}.',f'Joint vs monolithic pass: {gate["joint_vs_monolithic_pass"]}.',f'Development candidate: {gate["development_candidate"]}.','Engineered development model; любой pass требует новой frozen replication.'];(folder/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');s.save(folder/'complete.json',{'protocol_sha256':sha(folder/'protocol.json'),'summary_sha256':sha(folder/'summary.json'),'database_sha256':sha(folder/'study.sqlite3')});s.remove_checkpoint(folder);return folder

def choose():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Stage96: hybrid multi-head, около8 часов');root.geometry('840x560+100+50');root.attributes('-topmost',True);choice=tk.StringVar(value='6');action={'v':None};old=latest_incomplete();tk.Label(root,text='Exact-budget4437 multi-head development: structured classifier + RNN trajectory.\nControls: shuffled/temporal/learned hybrids, learned-sparse96 и RNN54.\nКалибровка фиксирует count примерно на8 часов. Это не биологический результат.',font=('Arial',11),padx=18,pady=18).pack();tk.Label(root,text='Workers для НОВОГО расчёта:',font=('Arial',10,'bold')).pack();frame=tk.Frame(root);frame.pack(pady=8)
 for title,value,key in [('2','2','2'),('4','4','4'),('6','6','6'),('Максимум','max','m')]:tk.Radiobutton(frame,text=title,variable=choice,value=value,indicatoron=False,width=11,pady=7).pack(side='left',padx=4);root.bind(key,lambda event,v=value:choice.set(v))
 tk.Label(root,text='Клавиши выбора: 2, 4, 6 или M.',font=('Arial',9)).pack();buttons=tk.Frame(root);buttons.pack(pady=18)
 if old:tk.Button(buttons,text='Продолжить незавершённый расчёт',command=lambda:action.update(v='continue'),padx=18,pady=10).pack(side='left',padx=7)
 tk.Button(buttons,text='Начать новый расчёт',command=lambda:action.update(v='new'),padx=18,pady=10).pack(side='left',padx=7)
 while action['v'] is None:
  try:root.update();time.sleep(.03)
  except tk.TclError:return
 if action['v']=='continue':folder=old
 else:
  for widget in root.winfo_children():widget.destroy()
  tk.Label(root,text='Калибровка нового расчёта...\nОна не входит в результат.',font=('Arial',13),padx=30,pady=70).pack();root.update();folder=prepare(choice.get(),False)
 for widget in root.winfo_children():widget.destroy()
 root.protocol('WM_DELETE_WINDOW',lambda:None);label=tk.Label(root,text='Подготовка...',font=('Arial',14,'bold'),padx=30,pady=35);label.pack();percent=tk.Label(root,text='0,00%',font=('Arial',20));percent.pack();detail=tk.Label(root,text='',font=('Arial',10),justify='center');detail.pack(pady=14)
 def progress(done,total,cpu,eta):
  percent.config(text=f'{100*done/total:.2f}%'.replace('.',','));label.config(text=f'Расчёт: {done}/{total}')
  if eta is None:eta_text='Примерное время окончания: оценивается.'
  else:
   finish=datetime.fromtimestamp(time.time()+eta).strftime('%Y-%m-%d %H:%M');eta_text=f'Осталось примерно: {int(eta//3600)} ч {int((eta%3600)//60)} мин.\nПримерное окончание: {finish}.'
  detail.config(text=f'Worker CPU: {cpu/3600:.3f} ч.\n{eta_text}\nSQLite checkpoint сохранён.');root.update()
 try:result=execute(folder,progress)
 except Exception as exc:
  report=failure_report(exc);messagebox.showerror('Stage96 остановлен','Ошибка сохранена:\n'+str(report.resolve()),parent=root);os.startfile(str(report));root.destroy();return
 os.startfile(str(result));os.startfile(str(result/'ИТОГ.txt'));messagebox.showinfo('Stage96 завершён','Открыты папка и ИТОГ.txt.\n\n'+str(result.resolve()),parent=root);root.destroy()

def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-STAGE96.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('STAGE96: ОШИБКА\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');return path

def main():
 p=argparse.ArgumentParser();p.add_argument('--choose',action='store_true');p.add_argument('--workers',default='2');p.add_argument('--fixture',action='store_true');p.add_argument('--folder');a=p.parse_args()
 if a.choose:choose()
 elif a.folder:execute(Path(a.folder))
 else:execute(prepare(a.workers,a.fixture))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  report=failure_report(exc);print(f'ОШИБКА: {exc}\nОтчёт: {report.resolve()}',file=sys.stderr);raise SystemExit(1)
