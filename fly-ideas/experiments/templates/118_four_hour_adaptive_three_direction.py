#!/usr/bin/env python3
"""Series118: ~4 h adaptive development of all three digital directions, then frozen final."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,os,sqlite3,threading,time,traceback,uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from itertools import product
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;REPORTS=HERE.parent/'reports';ROOT=Path('workspace/runs/ideas/i-observational/adaptive-three-direction-118')
R117=REPORTS/'frozen-action-specific-mirror-117-user-result.json';R117_SHA='13679c5ff066d672595ae8562a4da83f758b8e22fb94054bdf051507c1458840'
MATRIX=REPORTS/'biological-digital-pipeline-116a-61x61.csv';MATRIX_SHA='03157b503d0271cb0991db524d45220bb8f49ce62e3ba171dc997ed7f3816150'
PATHS=REPORTS/'biological-digital-pipeline-116b-61x8.csv';PATHS_SHA='4186bb6fdbe0a0e81f8626469027976ade1d416ff0549af94b85fb1b07aa3ca1'
MANIFEST=REPORTS/'biological-digital-pipeline-116a-root-manifest.csv';MANIFEST_SHA='37c92d1d7b4bf75824ff1a214f8d3ece8de773990e90039bff9a9e88a2711288'
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');BUNDLE=24;DEV_FRAC=.80
PAUSE=threading.Event();DATA={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def read_matrix(path):
 with Path(path).open(encoding='utf8')as f:r=list(csv.reader(f));return r[0][1:],[z[0]for z in r[1:]],np.array([[float(v)for v in z[1:]]for z in r[1:]],float)
def normrows(x):return x/np.maximum(x.sum(1,keepdims=True),1e-15)
def cosine(a,b):
 a=a-a.mean();b=b-b.mean();return float(a@b/max(np.linalg.norm(a)*np.linalg.norm(b),1e-15))
def ranks(x):return np.argsort(np.argsort(x)).astype(float)
def corr(a,b):
 a=a-a.mean();b=b-b.mean();return float(a@b/max(np.linalg.norm(a)*np.linalg.norm(b),1e-15))
def fit(O,X,lam):
 mo=O.mean(0);mx=X.mean(0);A=O-mo;B=X-mx;M=np.linalg.solve(B.T@B+lam*np.eye(B.shape[1]),B.T@A);return mo,mx,M
def evaluate(O,X,y,model):
 mo,mx,M=model;A=O-mo;B=(X-mx)@M;n=len(y);S=np.array([[cosine(A[i],B[j])for j in range(n)]for i in range(n)]);pred=[max(range(3),key=lambda a:float(np.mean([S[i,j]for j in range(n)if y[j]==a])))for i in range(n)];same=np.mean([S[i,j]for i in range(n)for j in range(n)if y[i]==y[j]]);other=np.mean([S[i,j]for i in range(n)for j in range(n)if y[i]!=y[j]]);return float(same-other),sum(a==b for a,b in zip(pred,y))/n
def key(c):return f"a{c['alpha']:.3g}_b{c['beta']:.3g}_l{c['ridge']:.3g}_n{c['subset']}_d{c['derivative']:.3g}"
def initial_configs():return[{'alpha':a,'beta':b,'ridge':l,'subset':n,'derivative':d}for a,b,l,n,d in product((0,.25,.75),(0,.15,.5),(.001,.01,.1),(8,12,20),(.0,.3))]
def mutate(configs,generation):
 out=[];sizes=(8,12,20,32,61)
 for c in configs:
  i=sizes.index(c['subset'])
  for aa,bb,ll,nn,dd in((c['alpha']+.125,c['beta'],c['ridge'],c['subset'],c['derivative']),(max(0,c['alpha']-.125),c['beta']+.1,c['ridge'],c['subset'],c['derivative']),(c['alpha'],max(0,c['beta']-.1),c['ridge']*3,c['subset'],c['derivative']),(c['alpha'],c['beta'],c['ridge']/3,sizes[min(i+1,4)],min(.8,c['derivative']+.15)),(c['alpha'],c['beta']+.05,c['ridge'],sizes[max(i-1,0)],max(0,c['derivative']-.15))):out.append({'alpha':round(aa,6),'beta':round(bb,6),'ridge':round(max(1e-5,min(1.,ll)),8),'subset':nn,'derivative':round(dd,6)})
 uniq={key(c):c for c in out};return list(uniq.values())
def make_bundle(config,seed,bundle=BUNDLE):
 raw=DATA['raw'];P0=DATA['P'];W0=DATA['W'];priority=DATA['priority'];rng=np.random.default_rng(seed);A=[];B=[];C=[]
 for rep in range(bundle):
  # A: edge/bootstrap robustness of the real type map.
  noise=rng.lognormal(0,.08,raw.shape);boot=np.where(raw>0,raw*noise,0);W=normrows(np.log1p(boot));A.append(corr(ranks(raw.sum(1)),ranks(boot.sum(1))))
  Q=normrows(np.maximum((np.eye(61)+config['alpha']*W+config['beta']*(W@W))@P0,0));u,_,_=np.linalg.svd(Q,full_matrices=False);proto=normrows(np.abs(u[:,:3].T));proto=normrows(np.maximum(proto+proto@W,0));idx=np.array(priority[:config['subset']]);train=[];valid=[]
  for ai in range(3):
   for k in range(9):
    z=np.maximum(proto[ai]*(1+rng.normal(0,.16,61))+rng.uniform(0,.0015,61),0);z/=z.sum();dn=z@Q;o=z@W+z;e=dn@Q.T;e=e@W+e
    if config['derivative']>0:o=o+config['derivative']*(o-z);e=e+config['derivative']*(e-dn@Q.T)
    (train if k<6 else valid).append((o[idx],e[idx],ai,z))
  O=np.array([q[0]for q in train]);X=np.array([q[1]for q in train]);model=fit(O,X,config['ridge']);Ov=np.array([q[0]for q in valid]);Xv=np.array([q[1]for q in valid]);y=[q[2]for q in valid];margin,acc=evaluate(Ov,Xv,y,model)
  # Controls are independently fit where appropriate.
  paired=np.roll(O,6,axis=0);pm=fit(paired,X,config['ridge']);pair_margin,pair_acc=evaluate(Ov,Xv,y,pm)
  perm=rng.permutation(61);Qs=Q[perm];sO=[];sX=[]
  for o,e,ai,z in train:
   dn=z@Qs;ee=dn@Qs.T;ee=ee@W+ee;sO.append(o);sX.append(ee[idx])
  sm=fit(np.array(sO),np.array(sX),config['ridge']);sv=[]
  for o,e,ai,z in valid:
   dn=z@Qs;ee=dn@Qs.T;ee=ee@W+ee;sv.append(ee[idx])
  struct_margin,struct_acc=evaluate(Ov,np.array(sv),y,sm);ident_margin,ident_acc=evaluate(Ov,Xv[:,::-1],y,model)
  label_y=list(np.asarray(y)[rng.permutation(len(y))]);label_margin,label_acc=evaluate(Ov,Xv,label_y,model);zero_margin,zero_acc=evaluate(Ov,np.zeros_like(Xv),y,model)
  control=max(pair_margin,struct_margin,ident_margin,label_margin,zero_margin);adv=margin-control;B.append((acc,struct_acc));C.append((margin,adv,pair_margin,struct_margin,ident_margin,label_margin,zero_margin))
 return{'config':key(config),'seed':seed,'bundle':bundle,'a_mean':float(np.mean(A)),'a_min':float(np.min(A)),'b_acc':float(np.mean([x[0]for x in B])),'b_struct_acc':float(np.mean([x[1]for x in B])),'c_margin':float(np.mean([x[0]for x in C])),'c_advantage':float(np.mean([x[1]for x in C])),'c_win_rate':float(np.mean([x[1]>0 for x in C])),'c_pairing_margin':float(np.mean([x[2]for x in C])),'c_structure_margin':float(np.mean([x[3]for x in C])),'c_identity_margin':float(np.mean([x[4]for x in C])),'c_label_margin':float(np.mean([x[5]for x in C])),'c_zero_margin':float(np.mean([x[6]for x in C])),'score':float(np.mean(A)+np.mean([x[0]-x[1]for x in B])+np.mean([x[1]for x in C]))}
def schema(db):
 db.executescript('CREATE TABLE IF NOT EXISTS trials(phase TEXT,generation INTEGER,config TEXT,seed INTEGER,bundle INTEGER,a_mean REAL,a_min REAL,b_acc REAL,b_struct_acc REAL,c_margin REAL,c_advantage REAL,c_win_rate REAL,c_pairing_margin REAL,c_structure_margin REAL,c_identity_margin REAL,c_label_margin REAL,c_zero_margin REAL,score REAL);CREATE TABLE IF NOT EXISTS configs(config TEXT PRIMARY KEY,json TEXT);CREATE TABLE IF NOT EXISTS state(k TEXT PRIMARY KEY,v TEXT);');db.commit()
def putstate(db,k,v):db.execute('INSERT OR REPLACE INTO state VALUES(?,?)',(k,json.dumps(v)));db.commit()
def getstate(db,k,default=None):
 r=db.execute('SELECT v FROM state WHERE k=?',(k,)).fetchone();return json.loads(r[0])if r else default
def setup_data():
 for p,h in((R117,R117_SHA),(MATRIX,MATRIX_SHA),(PATHS,PATHS_SHA),(MANIFEST,MANIFEST_SHA)):
  if sha(p)!=h:raise ValueError(f'Exact input changed: {p.name}')
 cols,rows,raw=read_matrix(MATRIX);dns,prows,P=read_matrix(PATHS)
 if cols!=rows or rows!=prows or raw.shape!=(61,61)or P.shape!=(61,8):raise ValueError('Frozen dimensions changed.')
 r=json.loads(R117.read_text(encoding='utf8'));frozen=r['protocol']['frozen_candidate_types'];priority=[rows.index(t)for t in frozen]+[i for i in np.argsort(P.sum(1))[::-1]if i not in{rows.index(t)for t in frozen}];DATA.update(raw=raw,P=P,W=normrows(np.log1p(raw)),types=rows,dns=dns,priority=priority)
def summarize(db,phase,config=None):
 q='SELECT a_mean,a_min,b_acc,b_struct_acc,c_margin,c_advantage,c_win_rate,c_pairing_margin,c_structure_margin,c_identity_margin,c_label_margin,c_zero_margin,score FROM trials WHERE phase=?';args=[phase]
 if config:q+=' AND config=?';args.append(config)
 rows=db.execute(q,args).fetchall()
 if not rows:return None
 z=np.array(rows,float);return{'trial_bundles':len(rows),'bootstrap_replicates':int(sum(r[0]for r in db.execute('SELECT bundle FROM trials WHERE phase=?'+(' AND config=?'if config else''),args))),'a_stability_mean':float(z[:,0].mean()),'a_stability_min':float(z[:,1].min()),'b_accuracy':float(z[:,2].mean()),'b_shuffled_accuracy':float(z[:,3].mean()),'c_margin':float(z[:,4].mean()),'c_advantage':float(z[:,5].mean()),'c_win_rate':float(z[:,6].mean()),'controls':{'pairing_margin':float(z[:,7].mean()),'structure_margin':float(z[:,8].mean()),'identity_margin':float(z[:,9].mean()),'label_margin':float(z[:,10].mean()),'zero_margin':float(z[:,11].mean())},'score':float(z[:,12].mean())}
def best_configs(db,n=5):
 rows=db.execute("SELECT config,AVG(score) s,COUNT(*) n FROM trials WHERE phase='development' GROUP BY config ORDER BY s DESC").fetchall();return[r[0]for r in rows[:n]]
def execute(folder,hours,workers,fixture,progress):
 setup_data();db=sqlite3.connect(folder/'study.sqlite3');schema(db);target=6 if fixture else hours*3600;active=getstate(db,'active_seconds',0.0);phase=getstate(db,'phase','calibration');generation=getstate(db,'generation',0);started=time.monotonic();configs=initial_configs()
 for c in configs:db.execute('INSERT OR IGNORE INTO configs VALUES(?,?)',(key(c),json.dumps(c)));db.commit()
 def elapsed():return active+time.monotonic()-started
 if phase=='calibration':
  t=time.perf_counter();make_bundle(configs[0],118000000,2 if fixture else 4);sec=max(time.perf_counter()-t,.001);putstate(db,'seconds_per_bundle',sec*(BUNDLE/(2 if fixture else 4)));phase='development';putstate(db,'phase',phase)
 development_end=target*(.55 if fixture else DEV_FRAC)
 with ThreadPoolExecutor(max_workers=workers)as pool:
  while phase=='development'and elapsed()<development_end and not PAUSE.is_set():
   generation+=1
   if generation==1:current=configs[:min(len(configs),8 if fixture else 54)]
   else:
    top=[]
    for k in best_configs(db):
     row=db.execute('SELECT json FROM configs WHERE config=?',(k,)).fetchone();top.append(json.loads(row[0]))
    current=mutate(top,generation)[:8 if fixture else 25]
   for c in current:db.execute('INSERT OR IGNORE INTO configs VALUES(?,?)',(key(c),json.dumps(c)))
   db.commit();seeds=[118100000+generation*10000+i for i in range(len(current))];results=list(pool.map(lambda q:make_bundle(q[0],q[1],2 if fixture else BUNDLE),zip(current,seeds)))
   for z in results:db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('development',generation,z['config'],z['seed'],z['bundle'],z['a_mean'],z['a_min'],z['b_acc'],z['b_struct_acc'],z['c_margin'],z['c_advantage'],z['c_win_rate'],z['c_pairing_margin'],z['c_structure_margin'],z['c_identity_margin'],z['c_label_margin'],z['c_zero_margin'],z['score']))
   db.commit();putstate(db,'generation',generation);progress('Adaptive A/B/C development',min(.8,elapsed()/target),generation,0)
  if phase=='development'and not PAUSE.is_set():
   frozen=best_configs(db,1)[0];putstate(db,'frozen_config',frozen);remaining=max(target-elapsed(),1);dev_done=db.execute("SELECT COUNT(*) FROM trials WHERE phase='development'").fetchone()[0];rate=dev_done/max(elapsed(),.001);putstate(db,'observed_bundles_per_second',rate);count=max(2 if fixture else workers*2,int(remaining*rate));count=min(count,8 if fixture else 200000);putstate(db,'final_bundles',count);phase='final';putstate(db,'phase',phase)
  if phase=='final'and not PAUSE.is_set():
   frozen=getstate(db,'frozen_config');cfg=json.loads(db.execute('SELECT json FROM configs WHERE config=?',(frozen,)).fetchone()[0]);total=getstate(db,'final_bundles');done=db.execute("SELECT COUNT(*) FROM trials WHERE phase='final'").fetchone()[0]
   while done<total and not PAUSE.is_set():
    batch=min(workers*2,total-done);seeds=[118900000+done+i for i in range(batch)];results=list(pool.map(lambda s:make_bundle(cfg,s,2 if fixture else BUNDLE),seeds))
    for z in results:db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',('final',generation,z['config'],z['seed'],z['bundle'],z['a_mean'],z['a_min'],z['b_acc'],z['b_struct_acc'],z['c_margin'],z['c_advantage'],z['c_win_rate'],z['c_pairing_margin'],z['c_structure_margin'],z['c_identity_margin'],z['c_label_margin'],z['c_zero_margin'],z['score']))
    db.commit();done+=batch;progress('Untouched frozen final',.8+.2*done/total,done,total)
   if done>=total:phase='completed';putstate(db,'phase',phase)
 active=elapsed();putstate(db,'active_seconds',active)
 if PAUSE.is_set():db.close();return None
 frozen=getstate(db,'frozen_config');dev=summarize(db,'development',frozen);final=summarize(db,'final',frozen);cfg=json.loads(db.execute('SELECT json FROM configs WHERE config=?',(frozen,)).fetchone()[0]);all_dev=summarize(db,'development');primary=bool(final and final['a_stability_mean']>=.9 and final['a_stability_min']>=.7 and final['b_accuracy']>=.9 and final['b_shuffled_accuracy']<=.75 and final['c_margin']>=.1 and final['c_advantage']>=.02 and final['c_win_rate']>=.8)
 result={'schema':'adaptive-three-direction-118-v1','status':'fixture_completed'if fixture else'completed','protocol':{'target_hours':hours,'workers':workers,'bundle_replicates':2 if fixture else BUNDLE,'development_fraction':.55 if fixture else DEV_FRAC,'adaptive_development_allowed':True,'untouched_final_adaptation_allowed':False,'source117_sha256':R117_SHA,'matrix_sha256':MATRIX_SHA,'paths_sha256':PATHS_SHA,'candidate_families':['path depth/mix','ridge','type subset','derivative feedback'],'primary_gate':'A mean>=.9,min>=.7; B acc>=.9, shuffled<=.75; C margin>=.1, advantage>=.02, win>=.8'},'active_wall_seconds':active,'development_generations':generation,'development_all':all_dev,'selected_config':cfg,'selected_development':dev,'final':final,'primary':{'all_three_directions_passed':primary,'a_structural_robustness_passed':bool(final and final['a_stability_mean']>=.9 and final['a_stability_min']>=.7),'b_dn_readout_passed':bool(final and final['b_accuracy']>=.9 and final['b_shuffled_accuracy']<=.75),'c_action_specific_mirror_passed':bool(final and final['c_margin']>=.1 and final['c_advantage']>=.02 and final['c_win_rate']>=.8),'biological_claim':False,'scientific_biological_result':False}}
 save(folder/'summary.json',result);(folder/'ИТОГ.txt').write_text('SERIES118 — ADAPTIVE THREE-DIRECTION LONG RUN\n\nA structural robustness: '+str(result['primary']['a_structural_robustness_passed'])+'\nB DN readout: '+str(result['primary']['b_dn_readout_passed'])+'\nC action-specific mirror: '+str(result['primary']['c_action_specific_mirror_passed'])+'\nAll three: '+str(primary)+'\nBiological claim: NO.\n',encoding='utf-8-sig');db.close();progress('Готово',1,1,1);return folder
def new_run(hours,workers,fixture,output_root,progress):
 root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('adaptive_three_direction_118_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();save(folder/'protocol_start.json',{'created_utc':datetime.now(timezone.utc).isoformat(),'hours':hours,'workers':workers,'fixture':fixture});return execute(folder,hours,workers,fixture,progress)
def latest_incomplete(root=ROOT):
 ds=sorted([p for p in Path(root).glob('adaptive_three_direction_118_*')if(p/'study.sqlite3').exists()],key=lambda p:p.stat().st_mtime,reverse=True)
 for p in ds:
  with sqlite3.connect(p/'study.sqlite3')as db:
   try:
    if getstate(db,'phase')!='completed':return p
   except sqlite3.Error:pass
 return None
def gui():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Series118: ~4 h adaptive A/B/C');root.geometry('900x540+70+35');root.attributes('-topmost',True);workers=tk.IntVar(value=min(6,os.cpu_count()or 2));status=tk.StringVar(value='Development адаптируется; untouched final не адаптируется');pct=tk.DoubleVar(value=0);eta=tk.StringVar(value='');running={'v':False};clock={'start':None}
 tk.Label(root,text='Series118 — около4 часов, все три направления',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='A bootstrap structural robustness · B DN readout tournament · C mirror specificity\nПервые80%: осознанный adaptive development; последние20%: frozen final.',justify='center').pack();f=tk.Frame(root);f.pack(pady=8);tk.Label(f,text='Workers:').pack(side='left');
 for n in(2,4,6,max(1,os.cpu_count()or 2)):tk.Radiobutton(f,text='Max'if n==(os.cpu_count()or 2)else str(n),variable=workers,value=n).pack(side='left')
 for hotkey,value in(('2',2),('4',4),('6',6),('m',max(1,os.cpu_count()or 2)),('M',max(1,os.cpu_count()or 2))):root.bind(hotkey,lambda _e,v=value:workers.set(v))
 tk.Label(root,textvariable=status,pady=8).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=720,state='disabled').pack();tk.Label(root,textvariable=eta).pack();buttons=tk.Frame(root);buttons.pack(pady=16)
 def update(t,v,d,total):
  elapsed=time.time()-clock['start']if clock['start']else 0;remaining=elapsed*(1-v)/v if v>.01 else 0;finish=time.strftime('%H:%M',time.localtime(time.time()+remaining))if remaining else'—';root.after(0,lambda:(status.set(t),pct.set(100*v),eta.set((f'Прогресс {100*v:.1f}% · {d}/{total}'if total else f'Generation {d}')+f' · осталось ~{remaining/60:.0f} мин · финиш ~{finish}')))
 def launch(cont):
  if running['v']:return
  PAUSE.clear();running['v']=True;clock['start']=time.time();start_new.config(state='disabled');resume.config(state='disabled')
  def work():
   try:
    folder=latest_incomplete()if cont else None;result=execute(folder,4,workers.get(),False,update)if folder else new_run(4,workers.get(),False,ROOT,update)
    def done():
     running['v']=False;start_new.config(state='normal');resume.config(state='normal');status.set('Пауза сохранена'if result is None else'Готово')
     if result and os.name=='nt':os.startfile(str(result.resolve()))
     if result:messagebox.showinfo('Series118',f'Расчёт завершён.\n{result.resolve()}',parent=root)
    root.after(0,done)
   except Exception as e:
    q=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-118.txt';q.parent.mkdir(parents=True,exist_ok=True);q.write_text(type(e).__name__+': '+str(e)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');root.after(0,lambda:(messagebox.showerror('Series118',f'{e}\n\n{q.resolve()}',parent=root),root.destroy()))
  threading.Thread(target=work,daemon=True).start()
 start_new=tk.Button(buttons,text='Начать новый ~4 ч',command=lambda:launch(False),padx=15,pady=8);start_new.pack(side='left',padx=5);resume=tk.Button(buttons,text='Продолжить',command=lambda:launch(True),padx=15,pady=8);resume.pack(side='left',padx=5);tk.Button(buttons,text='Пауза после batch',command=PAUSE.set,padx=15,pady=8).pack(side='left',padx=5);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--hours',type=float,default=4);p.add_argument('--workers',type=int,default=min(6,os.cpu_count()or 2));p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 else:print(new_run(.002 if a.fixture else a.hours,a.workers,a.fixture,a.output_root,lambda *_:None))
if __name__=='__main__':main()
