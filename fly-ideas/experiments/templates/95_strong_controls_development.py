#!/usr/bin/env python3
"""Stage95: four-hour development benchmark against stronger computational controls."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,time,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
STAGE92=HERE/'92_complex_connectome_advantage.py';STAGE92_SHA='0dbbdcb91fff86ab059e975ded8c358dae345c1b6429795ead516faabe8c4439'
ROOT=Path('workspace/runs/ideas/i-connectome-advantage/stage-5-strong-controls-development')
TARGET_WALL_SECONDS=4*3600;TRAJECTORY_WEIGHT=4.0
MODELS=('structured96','shuffled96','temporal96','learned_sparse96','rnn54','dense96');PRIMARY_CONTROLS=('shuffled96','temporal96','learned_sparse96','rnn54');BUDGETS=(5,30)
SCENARIOS=(('clean',.12,0,.0),('view_high',.45,0,.0),('occlusion',.28,0,.0),('lesion10',.28,10,.0),('lesion25',.28,24,.0),('state_noise',.28,0,.08),('combined_harsh',.48,24,.08))

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def stage92():
 if sha(STAGE92)!=STAGE92_SHA:raise ValueError('Закреплённый Stage92 runner изменился.')
 spec=importlib.util.spec_from_file_location('stage92_controls_source',STAGE92);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def temporal_mask():
 mask=np.zeros((72,96),dtype=np.float64)
 for unit in range(96):
  start=unit%9
  for t in range(start,start+4):mask[t*6:(t+1)*6,unit]=1
 return mask

def weighted_delta(pred,y):
 delta=2*(pred-y)/(len(y)*y.shape[1]);delta[:,9:]*=TRAJECTORY_WEIGHT;return delta

def train_static(x,y,mask,init_seed,order_seed,epochs,learned=False):
 init=np.random.default_rng(init_seed);order=np.random.default_rng(order_seed);n,d=x.shape;h=96;o=y.shape[1];active=2304
 current=np.ones((d,h)) if learned else mask.copy();fan=np.maximum(1,current.sum(0));w=init.normal(0,1,(d,h))/np.sqrt(fan)[None,:]*current;b=np.zeros(h);v=init.normal(0,.08,(h,o));c=np.zeros(o);params=[w,b,v,c];mom=[np.zeros_like(q) for q in params];vel=[np.zeros_like(q) for q in params];step=0;prune_epoch=max(1,epochs//5)
 for epoch in range(epochs):
  for start in order.permutation(np.arange(0,n,64)):
   ids=np.arange(start,min(start+64,n));xb=x[ids];yb=y[ids];hidden=np.tanh(xb@w+b);pred=hidden@v+c;delta=weighted_delta(pred,yb);dh=(delta@v.T)*(1-hidden**2);grads=[xb.T@dh*current,dh.sum(0),hidden.T@delta,delta.sum(0)];step+=1
   for i,(parameter,grad) in enumerate(zip(params,grads)):
    mom[i]=.9*mom[i]+.1*grad;vel[i]=.999*vel[i]+.001*grad*grad;parameter-=.006*(mom[i]/(1-.9**step))/(np.sqrt(vel[i]/(1-.999**step))+1e-8)
  if learned and epoch+1==prune_epoch:
   keep=np.argpartition(np.abs(w).ravel(),-active)[-active:];current=np.zeros(w.size);current[keep]=1;current=current.reshape(w.shape);w*=current;mom[0]*=current;vel[0]*=current
  w*=current
 return ('static',w,b,v,c,current)

def rnn_recurrent_mask():
 mask=np.ones((54,54),dtype=np.float64)
 for i in range(12):mask[i,i]=0
 return mask

def train_rnn(x,y,init_seed,order_seed,epochs):
 init=np.random.default_rng(init_seed);order=np.random.default_rng(order_seed);n=len(x);h=54;o=y.shape[1];rmask=rnn_recurrent_mask();wx=init.normal(0,1/np.sqrt(6),(6,h));wh=init.normal(0,1/np.sqrt(h),(h,h))*rmask;b=np.zeros(h);v=init.normal(0,.08,(h,o));c=np.zeros(o);params=[wx,wh,b,v,c];mom=[np.zeros_like(q) for q in params];vel=[np.zeros_like(q) for q in params];step=0;seq=x.reshape(n,12,6)
 for _ in range(epochs):
  for start in order.permutation(np.arange(0,n,64)):
   ids=np.arange(start,min(start+64,n));xb=seq[ids];yb=y[ids];states=[np.zeros((len(ids),h))]
   for t in range(12):states.append(np.tanh(xb[:,t]@wx+states[-1]@wh+b))
   pred=states[-1]@v+c;delta=weighted_delta(pred,yb);gv=states[-1].T@delta;gc=delta.sum(0);gwx=np.zeros_like(wx);gwh=np.zeros_like(wh);gb=np.zeros_like(b);dh=delta@v.T
   for t in range(11,-1,-1):
    dz=dh*(1-states[t+1]**2);gwx+=xb[:,t].T@dz;gwh+=states[t].T@dz;gb+=dz.sum(0);dh=dz@wh.T
   grads=[gwx,gwh*rmask,gb,gv,gc];step+=1
   for i,(parameter,grad) in enumerate(zip(params,grads)):
    mom[i]=.9*mom[i]+.1*grad;vel[i]=.999*vel[i]+.001*grad*grad;parameter-=.006*(mom[i]/(1-.9**step))/(np.sqrt(vel[i]/(1-.999**step))+1e-8)
   wh*=rmask
 return ('rnn',wx,wh,b,v,c,rmask)

def hidden_predict(model,x):
 if model[0]=='static':
  _,w,b,v,c,_=model;hidden=np.tanh(x@w+b);return hidden,hidden@v+c
 _,wx,wh,b,v,c,_=model;hidden=np.zeros((len(x),54));seq=x.reshape(len(x),12,6)
 for t in range(12):hidden=np.tanh(seq[:,t]@wx+hidden@wh+b)
 return hidden,hidden@v+c

def evaluate(model,x,y,labels,lesion_count,state_noise,seed):
 hidden,pred=hidden_predict(model,x);rng=np.random.default_rng(seed)
 if state_noise:hidden=hidden+rng.normal(0,state_noise,hidden.shape)
 if lesion_count:
  count=lesion_count if hidden.shape[1]==96 else max(1,round(lesion_count*hidden.shape[1]/96));hidden[:,rng.choice(hidden.shape[1],count,replace=False)]=0
 if state_noise or lesion_count:
  v=model[3] if model[0]=='static' else model[4];c=model[4] if model[0]=='static' else model[5];pred=hidden@v+c
 return float(np.mean(np.argmax(pred[:,:9],1)==labels)),float(np.sqrt(np.mean((pred[:,9:]-y[:,9:])**2)))

def replicate(task):
 ident,fixture=task;started=time.process_time();s=stage92();st=s.stage91();cache={};models={};rows=[];base=st.masks(95000000+ident,72,96);masks={'structured96':base['structured96'],'shuffled96':base['shuffled96'],'temporal96':temporal_mask(),'dense96':base['dense96']}
 for budget in BUDGETS:
  x,y,labels=s.dataset(95100000+ident*10+budget,budget,.08);mean=x.mean(0);std=np.maximum(x.std(0),1e-6);x=(x-mean)/std;cache[budget]=(mean,std);init_seed=95200000+ident*100+budget*3;order_seed=95250000+ident*100+budget*3;epochs=10 if fixture else 220
  for name in ('structured96','shuffled96','temporal96','dense96'):models[(budget,name)]=train_static(x,y,masks[name],init_seed,order_seed,epochs)
  models[(budget,'learned_sparse96')]=train_static(x,y,np.ones((72,96)),init_seed,order_seed,epochs,True);models[(budget,'rnn54')]=train_rnn(x,y,init_seed,order_seed,epochs)
 for budget in BUDGETS:
  mean,std=cache[budget]
  for scenario,severity,lesion,noise in SCENARIOS:
   x,y,labels=s.dataset(95300000+ident*100+budget*7+int(severity*100),8 if fixture else 50,severity);x=(x-mean)/std;eval_seed=95400000+ident*1000+budget*10+sum(map(ord,scenario))
   for name in MODELS:
    acc,rmse=evaluate(models[(budget,name)],x,y,labels,lesion,noise,eval_seed);rows.append((ident,budget,scenario,name,acc,rmse))
 return {'replicate':ident,'cpu_seconds':time.process_time()-started,'rows':rows}

def schema(db):db.executescript('PRAGMA journal_mode=WAL;CREATE TABLE IF NOT EXISTS replicates(id INTEGER PRIMARY KEY,cpu_seconds REAL NOT NULL);CREATE TABLE IF NOT EXISTS metrics(replicate INTEGER,budget INTEGER,scenario TEXT,model TEXT,accuracy REAL,rmse REAL,PRIMARY KEY(replicate,budget,scenario,model));')
def commit(db,result):db.execute('INSERT OR REPLACE INTO replicates VALUES(?,?)',(result['replicate'],result['cpu_seconds']));db.executemany('INSERT OR REPLACE INTO metrics VALUES(?,?,?,?,?,?)',result['rows']);db.commit()
def wilson_lower(k,n,z=1.959963984540054):
 p=k/n;den=1+z*z/n;return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den

def aggregate(db):
 groups={}
 for budget,scenario,model,acc,rmse,n in db.execute('SELECT budget,scenario,model,AVG(accuracy),AVG(rmse),COUNT(*) FROM metrics GROUP BY budget,scenario,model'):groups.setdefault(str(budget),{}).setdefault(scenario,{})[model]={'accuracy':acc,'rmse':rmse,'n':n}
 comparisons={}
 for control in PRIMARY_CONTROLS:
  def dual(extra,args=()):return db.execute("SELECT SUM(CASE WHEN s.accuracy>q.accuracy AND s.rmse<q.rmse THEN 1 ELSE 0 END),COUNT(*) FROM metrics s JOIN metrics q ON s.replicate=q.replicate AND s.budget=q.budget AND s.scenario=q.scenario WHERE s.model='structured96' AND q.model=? "+extra,(control,*args)).fetchone()
  harsh=dual("AND s.scenario='combined_harsh'");overall=dual('');h=groups['5']['combined_harsh'];ss=h['structured96'];q=h[control];comparisons[control]={'fewshot_harsh_accuracy_margin':ss['accuracy']-q['accuracy'],'fewshot_harsh_rmse_ratio':ss['rmse']/q['rmse'],'harsh_dual_wins':harsh[0] or 0,'harsh_comparisons':harsh[1],'harsh_wilson95_lower':wilson_lower(harsh[0] or 0,harsh[1]),'overall_dual_wins':overall[0] or 0,'overall_comparisons':overall[1],'overall_wilson95_lower':wilson_lower(overall[0] or 0,overall[1])}
 primary=comparisons['shuffled96'];retention=primary['fewshot_harsh_accuracy_margin']>=.03 and primary['fewshot_harsh_rmse_ratio']<=.97 and primary['harsh_wilson95_lower']>=.60 and primary['overall_wilson95_lower']>=.55;strong=all(v['fewshot_harsh_accuracy_margin']>0 and v['fewshot_harsh_rmse_ratio']<1 and v['harsh_wilson95_lower']>=.50 and v['overall_wilson95_lower']>=.50 for k,v in comparisons.items() if k!='shuffled96');gate={'retains_stage94_vs_shuffled':retention,'beats_every_strong_control':strong,'development_candidate':retention and strong,'comparisons':comparisons};return groups,gate

def worker_choice(value):
 raw=str(value).lower().strip()
 if raw=='max':return 'max',max(1,os.cpu_count() or 1)
 n=int(raw)
 if n not in (2,4,6):raise ValueError('Workers должны быть2,4,6 или max.')
 return str(n),n

def latest_incomplete():
 if not ROOT.exists():return None
 found=[p for p in ROOT.glob('controls_*') if (p/'protocol.json').exists() and (p/'study.sqlite3').exists() and not (p/'complete.json').exists()]
 return max(found,key=lambda p:p.stat().st_mtime) if found else None

def prepare(workers,fixture):
 s=stage92();label,count=worker_choice(workers);ROOT.mkdir(parents=True,exist_ok=True);folder=ROOT/('fixture' if fixture else'controls_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(exist_ok=fixture);db=sqlite3.connect(folder/'study.sqlite3');schema(db)
 calibration=replicate((-1,fixture));cpu=max(calibration['cpu_seconds'],.1);target=2 if fixture else min(50000,max(count*4,math.ceil(TARGET_WALL_SECONDS*count/cpu)));protocol={'schema':'stage95-strong-controls-development-v1','mode':'fixture' if fixture else 'four_hour_development','biological_result':False,'stage92_sha256':STAGE92_SHA,'script_sha256':sha(__file__),'target_wall_seconds':0 if fixture else TARGET_WALL_SECONDS,'calibration_cpu_seconds':cpu,'fixed_replicates':target,'workers':count,'worker_choice':label,'models':list(MODELS),'primary_controls':list(PRIMARY_CONTROLS),'parameter_counts':{'structured96':4437,'shuffled96':4437,'temporal96':4437,'learned_sparse96_final':4437,'rnn54':4437,'dense96':9045},'trajectory_loss_weight':TRAJECTORY_WEIGHT,'learned_sparse_disclosure':'dense warmup for20% epochs then magnitude-pruned to2304 input weights; final parameter matched but training compute advantaged','rnn_lesion_disclosure':'lesion fraction is matched; exact unit indices cannot match96-unit models','seed_namespace':'95000000-series; development and disclosed after run','gate':'retain Stage94 vs shuffled; for each temporal/learned-sparse/rnn: positive few-shot harsh accuracy margin, RMSE ratio<1, harsh and overall Wilson95 lower>=0.50','limitations':['Development selection only; any candidate needs new frozen seeds.','Engineered software architectures, not neurons or connectomes.','Learned sparse has extra dense-warmup compute and is a deliberately strong control.']};s.save(folder/'protocol.json',protocol);s.save_checkpoint(folder/'INCOMPLETE.json',{'completed':0,'fixed_replicates':target,'worker_cpu_seconds':0});db.close();return folder

def execute(folder,progress=None):
 s=stage92();folder=Path(folder);protocol=json.loads((folder/'protocol.json').read_text(encoding='utf-8'));target=protocol['fixed_replicates'];workers=protocol['workers'];fixture=protocol['mode']=='fixture';db=sqlite3.connect(folder/'study.sqlite3');schema(db);done={r[0] for r in db.execute('SELECT id FROM replicates')};remaining=[i for i in range(target) if i not in done];session_start=time.time();session_initial=len(done)
 if progress:progress(len(done),target,0,None)
 with concurrent.futures.ProcessPoolExecutor(max_workers=min(workers,max(1,len(remaining))),mp_context=multiprocessing.get_context('spawn')) as pool:
  for offset in range(0,len(remaining),max(1,workers*3)):
   futures=[pool.submit(replicate,(i,fixture)) for i in remaining[offset:offset+max(1,workers*3)]]
   for future in concurrent.futures.as_completed(futures):
    result=future.result();commit(db,result);done.add(result['replicate']);cpu=db.execute('SELECT COALESCE(SUM(cpu_seconds),0) FROM replicates').fetchone()[0];s.save_checkpoint(folder/'INCOMPLETE.json',{'completed':len(done),'fixed_replicates':target,'worker_cpu_seconds':cpu})
    if progress:
     session_completed=len(done)-session_initial;elapsed=max(time.time()-session_start,.001);eta=(target-len(done))*elapsed/session_completed if session_completed else None;progress(len(done),target,cpu,eta)
 groups,gate=aggregate(db);cpu=db.execute('SELECT SUM(cpu_seconds) FROM replicates').fetchone()[0];db.close();summary={'schema':'stage95-strong-controls-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'completed_replicates':target,'worker_cpu_seconds':cpu,'aggregate':groups,'development_gate':gate,'interpretation':'candidate_for_new_frozen_replication' if gate['development_candidate'] else'no_candidate'};s.save(folder/'summary.json',summary);lines=['STAGE95: STRONG CONTROLS DEVELOPMENT',f'Replicates: {target}; worker CPU: {cpu/3600:.3f} ч.',f'Retains Stage94 vs shuffled: {gate["retains_stage94_vs_shuffled"]}.',f'Beats every strong control: {gate["beats_every_strong_control"]}.',f'Development candidate: {gate["development_candidate"]}.']
 for name,v in gate['comparisons'].items():lines.append(f'{name}: margin {v["fewshot_harsh_accuracy_margin"]:.6f}; RMSE ratio {v["fewshot_harsh_rmse_ratio"]:.6f}; harsh lower {v["harsh_wilson95_lower"]:.6f}; overall lower {v["overall_wilson95_lower"]:.6f}.')
 lines.append('Development artificial architectures; любой candidate требует новой frozen replication.');(folder/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');s.save(folder/'complete.json',{'protocol_sha256':sha(folder/'protocol.json'),'summary_sha256':sha(folder/'summary.json'),'database_sha256':sha(folder/'study.sqlite3')});s.remove_checkpoint(folder);return folder

def choose():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Stage95: сильные controls, около4 часов');root.geometry('820x540+120+60');root.attributes('-topmost',True);choice=tk.StringVar(value='6');action={'v':None};old=latest_incomplete()
 tk.Label(root,text='Development benchmark против shuffled96, temporal96,\nlearned-sparse96 и parameter-matched RNN54.\nКалибровка заранее фиксирует число replicates примерно на4 часа.\nЭто artificial architectures; результат не является биологическим.',font=('Arial',11),padx=18,pady=18).pack();tk.Label(root,text='Workers для НОВОГО расчёта:',font=('Arial',10,'bold')).pack()
 worker_frame=tk.Frame(root);worker_frame.pack(pady=8)
 for title,value,key in [('2','2','2'),('4','4','4'),('6','6','6'),('Максимум','max','m')]:
  tk.Radiobutton(worker_frame,text=title,variable=choice,value=value,indicatoron=False,width=11,pady=7).pack(side='left',padx=4);root.bind(key,lambda event,v=value:choice.set(v))
 tk.Label(root,text='Можно выбрать workers клавишами 2, 4, 6 или M.',font=('Arial',9)).pack()
 buttons=tk.Frame(root);buttons.pack(pady=18)
 if old:tk.Button(buttons,text='Продолжить незавершённый расчёт',command=lambda:action.update(v='continue'),padx=18,pady=10).pack(side='left',padx=7)
 tk.Button(buttons,text='Начать новый расчёт',command=lambda:action.update(v='new'),padx=18,pady=10).pack(side='left',padx=7)
 while action['v'] is None:
  try:root.update();time.sleep(.03)
  except tk.TclError:return
 if action['v']=='continue':folder=old
 else:
  for widget in root.winfo_children():widget.destroy()
  tk.Label(root,text='Калибровка нового расчёта...\nОна не входит в научный результат.',font=('Arial',13),padx=30,pady=70).pack();root.update();folder=prepare(choice.get(),False)
 for widget in root.winfo_children():widget.destroy()
 root.protocol('WM_DELETE_WINDOW',lambda:None);label=tk.Label(root,text='Подготовка...',font=('Arial',14,'bold'),padx=30,pady=35);label.pack();percent=tk.Label(root,text='0,00%',font=('Arial',20));percent.pack();detail=tk.Label(root,text='',font=('Arial',10),justify='center');detail.pack(pady=14)
 def progress(done,total,cpu,eta):
  value=100*done/total if total else 0;percent.config(text=f'{value:.2f}%'.replace('.',','));label.config(text=f'Расчёт: {done}/{total}')
  if eta is None:eta_text='Примерное время окончания: оценивается после первого replicate.'
  else:
   finish=datetime.fromtimestamp(time.time()+eta).strftime('%Y-%m-%d %H:%M');hours=int(eta//3600);minutes=int((eta%3600)//60);eta_text=f'Осталось примерно: {hours} ч {minutes} мин.\nПримерное окончание: {finish}.'
  detail.config(text=f'Worker CPU: {cpu/3600:.3f} ч.\n{eta_text}\nSQLite checkpoint сохранён.');root.update()
 try:result=execute(folder,progress)
 except Exception as exc:
  report=failure_report(exc);messagebox.showerror('Stage95 остановлен','Ошибка сохранена:\n'+str(report.resolve()),parent=root);os.startfile(str(report));root.destroy();return
 os.startfile(str(result));os.startfile(str(result/'ИТОГ.txt'));messagebox.showinfo('Stage95 завершён','Открыты папка и ИТОГ.txt.\n\n'+str(result.resolve()),parent=root);root.destroy()

def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-STAGE95.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('STAGE95: ОШИБКА\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');return path

def main():
 p=argparse.ArgumentParser();p.add_argument('--choose',action='store_true');p.add_argument('--workers',default='2');p.add_argument('--fixture',action='store_true');p.add_argument('--folder');a=p.parse_args()
 if a.choose:choose()
 elif a.folder:execute(Path(a.folder))
 else:execute(prepare(a.workers,a.fixture))
if __name__=='__main__':
 try:main()
 except Exception as exc:
  report=failure_report(exc);print(f'ОШИБКА: {exc}\nОтчёт: {report.resolve()}',file=sys.stderr);raise SystemExit(1)
