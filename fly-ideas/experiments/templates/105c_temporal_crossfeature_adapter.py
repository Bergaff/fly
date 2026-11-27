#!/usr/bin/env python3
"""Series105C: train-only CV temporal cross-feature official-eye domain adapter."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER105AB=HERE/'105ab_official_eye_diagnostic_adaptation.py';RUNNER105AB_SHA='b070fff687dfcfd263c6868b59954283486dd84b5a4e07156816f333a13dae67'
RESULT105AB=HERE.parent/'reports'/'official-eye-diagnostic-adaptation-105ab-user-result.json';RESULT105AB_SHA='92715b54fde5fb259ce3947e35edf4f8ba178f659c5de01096546ca739af6a14'
ROOT=Path('workspace/runs/ideas/i-observational/temporal-crossfeature-adapter');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');RIDGES=(.01,.1,1.,10.,100.);TRAIN_REPS=10;VALID_REPS=3;TRAIN_N=30;VALID_N=9;CONTROLS=('crossfeature','diagonal','raw_frozen','neutral_visual','reversed_visual','zero_state','shuffled_state')
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
 if file_sha(RESULT105AB)!=RESULT105AB_SHA:raise ValueError('Exact Series105A+B result изменён.')
 result=json.loads(RESULT105AB.read_text(encoding='utf8'))
 if result.get('status')!='completed' or result.get('primary',{}).get('development_candidate') is not False or result.get('primary',{}).get('scientific_result') is not False:raise ValueError('Series105C требует exact completed105B no-go.')
 if result.get('protocol',{}).get('script_sha256')!=RUNNER105AB_SHA:raise ValueError('Series105A+B result не соответствует runner.')
 s105=load_module('series105c_source105ab',RUNNER105AB,RUNNER105AB_SHA);s104,s102,s103,result104=s105.authorize();return s105,s104,s102,s103,result,result104
def specs(m86):
 out=[]
 train_amp=(.62,.68,.74,.80,.86,.92,.98,.71,.83,.95);train_speed=(.70,.80,.90,1.,1.10,1.20,.76,.88,1.06,1.16)
 for rep in range(TRAIN_REPS):
  for ai,action in enumerate(ACTIONS):
   ident=1069+rep*3+ai;seed=105300+rep*10+ai;amp=train_amp[rep];speed=train_speed[(rep+ai)%TRAIN_REPS];out.append({'role':'crossfeature_train','id':ident,'replicate':rep+1,'action':action,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)})
 valid_amp=(.65,.85,.97);valid_speed=(.82,1.04,1.18)
 for rep in range(VALID_REPS):
  for ai,action in enumerate(ACTIONS):
   ident=1099+rep*3+ai;seed=105500+rep*10+ai;amp=valid_amp[rep];speed=valid_speed[(rep+ai)%VALID_REPS];out.append({'role':'crossfeature_validation','id':ident,'replicate':rep+1,'action':action,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)})
 return out
def prepare(s105,s104,s102,source,d_folder):
 s101,models,diag,diag_desc,old_items,old_desc,guards=s105.prepare(s104,s102,source,d_folder);m=models['m'];m88=m.load88();m87=m88.load87();m86=m87.load86();s89=s101.load89e();seen={x['motion_sha256'] for x in diag+old_items}
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:seen|={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 seen|=m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|models['m2'].authorize_b()|models['m3'].authorize_b2()|s89.authorize_d()
 items=[];desc=[]
 for x in specs(m86):
  h=s105.motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series105C motion пересекается с прежними или между splits.')
  item={**x,'motion_sha256':h};items.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'});seen.add(h)
 return s101,models,items,desc,guards
def fit_ridge(x,y,lam):
 x=np.asarray(x,float);y=np.asarray(y,float);xm=x.mean(0);ym=y.mean(0);xs=x.std(0);ys=y.std(0);xs[xs<1e-9]=1.;ys[ys<1e-9]=1.;zx=(x-xm)/xs;zy=(y-ym)/ys;w=np.linalg.solve(zx.T@zx+float(lam)*np.eye(zx.shape[1]),zx.T@zy);return {'official_mean':xm,'official_scale':xs,'synthetic_mean':ym,'synthetic_scale':ys,'weights':w,'ridge':float(lam)}
def apply(model,x):return ((np.asarray(x,float)-model['official_mean'])/model['official_scale']@model['weights'])*model['synthetic_scale']+model['synthetic_mean']
def cv_select(pairs):
 rows=[]
 for lam in RIDGES:
  errors=[]
  for fold in range(5):
   train=[p for p in pairs if (p['replicate']-1)%5!=fold];test=[p for p in pairs if (p['replicate']-1)%5==fold];model=fit_ridge([p['official_coeff'] for p in train],[p['synthetic_coeff'] for p in train],lam)
   for p in test:
    pred=apply(model,p['official_coeff']);scale=float(np.std(p['synthetic_coeff']))+1e-12;errors.append(float(np.sqrt(np.mean((pred-p['synthetic_coeff'])**2))/scale))
  rows.append({'ridge':float(lam),'mean_state_nrmse':float(np.mean(errors)),'fold_cases':len(errors)})
 selected=min(rows,key=lambda r:(r['mean_state_nrmse'],-r['ridge']));return rows,selected,fit_ridge([p['official_coeff'] for p in pairs],[p['synthetic_coeff'] for p in pairs],selected['ridge'])
def policy(s105,models,coeff):return s105.policy_from_coeff(models,np.asarray(coeff,float))
def validate(s105,s104,s103,models,bridge,item,cross,diagonal,neutral_coeff,progress,base,span):
 off=s105.capture_official(s104,s103,models,bridge,item,progress,base,span,f'105C validation {item["id"]}');cross_coeff=apply(cross,off['coeff']);cross_controls,probs=policy(s105,models,cross_coeff);diag_controls,_=policy(s105,models,s105.apply_adapter(diagonal,off['coeff']));neutral_controls,_=policy(s105,models,apply(cross,neutral_coeff));rev_coeff,_,_=s104.infer(models,off['images'][::-1].copy());rev_controls,_=policy(s105,models,apply(cross,rev_coeff));targets={'crossfeature':cross_controls['candidate'],'diagonal':diag_controls['candidate'],'raw_frozen':off['target'],'neutral_visual':neutral_controls['candidate'],'reversed_visual':rev_controls['candidate'],'zero_state':cross_controls['zero_state'],'shuffled_state':cross_controls['shuffled_state']};metrics={k:{'truth_rmse_rad':s105.rmse(v,off['truth']),'target_sha256':sha_bytes(np.asarray(v,dtype='<f8').tobytes())} for k,v in targets.items()}
 return {'id':item['id'],'action':item['action'],'predicted_action':ACTIONS[int(np.argmax(probs))],'probabilities':{a:float(probs[i]) for i,a in enumerate(ACTIONS)},'official_state_sha256':sha_bytes(np.asarray(off['coeff'],dtype='<f8').tobytes()),'crossfeature_state_sha256':sha_bytes(np.asarray(cross_coeff,dtype='<f8').tobytes()),'controls':metrics}
def decide(rows,fixture=False):
 n=len(rows);required=n if fixture else 6;correct=sum(r['predicted_action']==r['action'] for r in rows);wins={k:sum(r['controls']['crossfeature']['truth_rmse_rad']<r['controls'][k]['truth_rmse_rad'] for r in rows) for k in CONTROLS if k!='crossfeature'};means={k:float(np.mean([r['controls'][k]['truth_rmse_rad'] for r in rows])) for k in CONTROLS};distinct=all(r['controls']['crossfeature']['target_sha256']!=r['controls'][k]['target_sha256'] for r in rows for k in ('diagonal','neutral_visual','reversed_visual','zero_state','shuffled_state'));passed=correct>=required and all(wins[k]>=required for k in ('diagonal','raw_frozen','neutral_visual','reversed_visual','zero_state','shuffled_state')) and distinct and means['crossfeature']<means['diagonal'] and means['crossfeature']<means['raw_frozen'];return {'validation_cases':n,'required_action_correct':required,'required_control_wins':required,'action_correct':correct,'crossfeature_truth_wins':wins,'mean_truth_rmse_rad':means,'targets_distinct':distinct,'passed':passed,'development_candidate':passed,'scientific_result':False}
def fixture(temp,progress):
 rng=np.random.default_rng(1053);x=rng.normal(size=(TRAIN_N,72));w=np.eye(72)*.8+np.roll(np.eye(72),1,axis=1)*.4;y=x@w+.2;pairs=[{'replicate':i//3+1,'official_coeff':x[i],'synthetic_coeff':y[i]} for i in range(TRAIN_N)];cv,sel,cross=cv_select(pairs);diagonal=fit_diagonal(x,y);rows=[]
 for i,a in enumerate(ACTIONS*3):
  controls={k:{'truth_rmse_rad':.08 if k=='crossfeature'else.18+i*.001,'target_sha256':k+str(i)} for k in CONTROLS};rows.append({'id':1099+i,'action':a,'predicted_action':a,'controls':controls})
 np.savez_compressed(temp/'temporal_crossfeature_adapter.npz',**cross);progress('Fixture готова',.98,1,1);return rows,decide(rows,True),cv,sel,cross,diagonal,[]
def fit_diagonal(x,y):
 x=np.asarray(x,float);y=np.asarray(y,float);mx=x.mean(0);my=y.mean(0);xc=x-mx;yc=y-my;sx=np.sqrt(np.mean(xc*xc,axis=0));sy=np.sqrt(np.mean(yc*yc,axis=0));cov=np.mean(xc*yc,axis=0);corr=np.divide(cov,sx*sy,out=np.zeros_like(cov),where=(sx*sy)>1e-12);corr=np.clip(corr,-1,1);scale=np.divide(corr*sy,sx,out=np.zeros_like(corr),where=sx>1e-12);return {'official_mean':mx,'synthetic_mean':my,'scale':np.clip(scale,-3,3),'correlation':corr}
def run(source,d_folder,output_root=ROOT,fixture_mode=False,progress=lambda *x:None):
 s105,s104,s102,s103,result105,result104=authorize();root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('temporal_crossfeature_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();progress('Проверяются exact prerequisites',.01,0,1)
 if fixture_mode:desc=[]
 else:s101,models,items,desc,guards=prepare(s105,s104,s102,source,d_folder);views=[v for v in s101.views(False) if v['corner_id'] in s105.VIEWS]
 protocol={'schema':'temporal-crossfeature-official-eye-adapter-v1','mode':'fixture'if fixture_mode else'full','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner105ab_sha256':RUNNER105AB_SHA,'series105ab_result_sha256':RESULT105AB_SHA,'prior_outcomes':'Series104 and exact diagonal105B remain no-go','training_allowed':True,'adapter':'standardized full 72x72 ridge mixing axes and 12 temporal cosine coefficients','ridge_candidates':list(RIDGES),'ridge_selection':'five folds by replicate on train only; minimum paired synthetic-state NRMSE; tie chooses larger ridge','fit_uses_action_labels_or_trajectory_truth':False,'train_cases':TRAIN_N,'validation_cases':VALID_N,'motions':desc,'validation_used_for_fit_or_selection':False,'post_result_tuning':False,'controls':list(CONTROLS),'development_gate':'held action>=6/9; crossfeature truth-RMSE wins>=6/9 vs diagonal/raw/neutral/reversed/zero/shuffled; distinct; mean crossfeature below diagonal and raw. Pass only authorizes separate untouched physical Series106.'};save(folder/'protocol.json',protocol)
 if fixture_mode:rows,primary,cv,selected,cross,diagonal,pairs_clean=fixture(temp,progress)
 else:
  s101.worker_init(models['bundle'],models['s84v']);bridge=s103.Bridge();pairs=[];rows=[]
  try:
   train=[x for x in items if x['role']=='crossfeature_train'];valid=[x for x in items if x['role']=='crossfeature_validation']
   for i,item in enumerate(train):
    off=s105.capture_official(s104,s103,models,bridge,item,progress,.03+.57*i/len(train),.25/len(train),f'105C train official {item["id"]}');syn_coeff,_,view_hashes=s105.synthetic_reference(s101,models,item,views);pairs.append({'id':item['id'],'replicate':item['replicate'],'action':item['action'],'official_coeff':off['coeff'],'synthetic_coeff':syn_coeff,'official_state_sha256':sha_bytes(np.asarray(off['coeff'],dtype='<f8').tobytes()),'synthetic_state_sha256':sha_bytes(np.asarray(syn_coeff,dtype='<f8').tobytes()),'synthetic_views':view_hashes});progress(f'105C paired training {item["id"]}',.03+.57*(i+1)/len(train),i+1,len(train))
   cv,selected,cross=cv_select(pairs);diagonal=fit_diagonal([p['official_coeff'] for p in pairs],[p['synthetic_coeff'] for p in pairs]);np.savez_compressed(temp/'temporal_crossfeature_adapter.npz',**cross);neutral_n=len(np.asarray(valid[0]['angles_deg']));neutral_images,_=s104.capture(s103,bridge,np.zeros((neutral_n,6)),progress,.61,.04,'105C neutral visual');neutral_coeff,_,_=s104.infer(models,neutral_images)
   for i,item in enumerate(valid):rows.append(validate(s105,s104,s103,models,bridge,item,cross,diagonal,neutral_coeff,progress,.65+.31*i/len(valid),.31/len(valid)))
   primary=decide(rows,False);before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p) for p in before}or frozen_before!=s104.manifest(frozen_path):raise ValueError('Frozen sources изменились.')
  finally:bridge.close()
  pairs_clean=[{k:v for k,v in p.items() if k not in ('official_coeff','synthetic_coeff')} for p in pairs]
 report={'schema':'temporal-crossfeature-official-eye-adapter-result-v1','status':'fixture_completed'if fixture_mode else'completed','protocol':protocol,'series105ab_primary':result105['primary'],'model':{'sha256':file_sha(temp/'temporal_crossfeature_adapter.npz'),'shape':list(cross['weights'].shape),'cv':cv,'selected':selected,'training_pairs':pairs_clean},'primary':primary,'validation':rows,'limitations':['New train-only-selected temporal cross-feature engineering adapter; not a rescue or replication of Series104/105B.','Held validation is non-physical development evidence.','Pass cannot itself establish physical transfer and only authorizes separately frozen Series106.','No biological vision, FlyVis/FlyWire/connectome mapping, living animal, or mirror-neuron claim.']};save(temp/'summary.json',report)
 with(temp/'validation105c.csv').open('w',newline='',encoding='utf8')as f:
  flat=[{'id':r['id'],'action':r['action'],'predicted_action':r['predicted_action'],**{k+'_rmse':r['controls'][k]['truth_rmse_rad'] for k in CONTROLS}} for r in rows];w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
 (temp/'ИТОГ.txt').write_text('SERIES105C: TEMPORAL CROSS-FEATURE ADAPTER\n\nSeries104/105B остаются no-go.\n105C development gate: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\nНе biological и не physical confirmation result.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series105C: temporal cross-feature adapter');root.geometry('810x460+125+60');root.attributes('-topmost',True);status=tk.StringVar(value='Train-only CV temporal adapter; затем held validation');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series105C: temporal cross-feature domain adapter',font=('Arial',13,'bold'),pady=14).pack();tk.Label(root,text='30 paired train motions, train-only ridge CV, затем9 held validation motions.\nSeries104 и diagonal105B остаются no-go; physical rollouts здесь не выполняются.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=630,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать result89D и source84Z, затем запустить105C',padx=18,pady=9);button.pack(pady=14)
 def update(text,fraction,done,total):
  def apply():
   p=round(fraction*100,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.02:elapsed=time.time()-start[0];eta.set(f'Прошло {elapsed/60:.1f} мин · осталось примерно {elapsed*(1-fraction)/fraction/60:.1f} мин')
  root.after(0,apply)
 def begin():
  d=filedialog.askdirectory(title='Выберите завершённую result-папку Series89D',mustexist=True,initialdir=str(D_ROOT.resolve()if D_ROOT.exists()else Path.cwd()),parent=root)
  if not d:return
  source=filedialog.askdirectory(title='Выберите завершённую production Series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve()if SOURCE_ROOT.exists()else Path.cwd()),parent=root)
  if not source:return
  button.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(source,d,progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series105C','Training и held validation завершены.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-105C.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series105C',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.',a.output_root,True))
 elif a.source84z and a.result89d:print(run(a.source84z,a.result89d,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d.')
if __name__=='__main__':main()
