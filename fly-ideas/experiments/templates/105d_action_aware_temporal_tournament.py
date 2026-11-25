#!/usr/bin/env python3
"""Series105D: long action-aware temporal model tournament on official-eye data."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER105C=HERE/'105c_temporal_crossfeature_adapter.py';RUNNER105C_SHA='60c74e44bca8c64ecc667e6eb8705f6163565cdd0509230ca8872d50ac4b206f'
RESULT105C=HERE.parent/'reports'/'temporal-crossfeature-adapter-105c-user-result.json';RESULT105C_SHA='d9f8c8400b4cff10ecc5b20132e06cb2ccb07f3cee3075d461a1c1622abcda39'
ROOT=Path('workspace/runs/ideas/i-observational/action-aware-temporal-tournament');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');SPLITS=(('train',30,1108,105700),('selection',6,1198,106100),('final',6,1216,106300));MODELS=('state_multitask_ridge','state_random_fourier','temporal_pool_ridge','temporal_action_experts');CONTROLS=('candidate','neutral_visual','reversed_visual','zero_input','shuffled_visual');EXPECTED_HOURS=15.;POOL_DIM=384;RFF_DIM=384
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
 if file_sha(RESULT105C)!=RESULT105C_SHA:raise ValueError('Exact Series105C result изменён.')
 result=json.loads(RESULT105C.read_text(encoding='utf8'))
 if result.get('status')!='completed' or result.get('primary',{}).get('development_candidate') is not False or result.get('primary',{}).get('scientific_result') is not False:raise ValueError('Series105D требует exact completed105C no-go.')
 if result.get('protocol',{}).get('script_sha256')!=RUNNER105C_SHA:raise ValueError('Series105C result не соответствует runner.')
 s105c=load_module('series105d_source105c',RUNNER105C,RUNNER105C_SHA);s105,s104,s102,s103,result105,result104=s105c.authorize();return s105c,s105,s104,s102,s103,result,result105,result104
def specs(m86):
 out=[]
 for role,reps,start,seed0 in SPLITS:
  for rep in range(reps):
   for ai,action in enumerate(ACTIONS):
    ident=start+rep*3+ai;seed=seed0+rep*10+ai;amp=.60+.38*((rep*7+ai*3)%17)/16;speed=.68+.56*((rep*5+ai*7)%19)/18;out.append({'role':role,'id':ident,'replicate':rep+1,'action':action,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)})
 return out
def hashes_in(x):
 out=set()
 if isinstance(x,dict):
  for k,v in x.items():
   if k=='motion_sha256'and isinstance(v,str):out.add(v)
   else:out|=hashes_in(v)
 elif isinstance(x,list):
  for v in x:out|=hashes_in(v)
 return out
def prepare(s105c,s105,s104,s102,source,d_folder,result105c,result105):
 s101,models,old_items,old_desc,guards=s105c.prepare(s105,s104,s102,source,d_folder);m=models['m'];m88=m.load88();m87=m88.load87();m86=m87.load86();s89=s101.load89e();seen=hashes_in(result105c)|hashes_in(result105)
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:seen|={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 seen|=m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|models['m2'].authorize_b()|models['m3'].authorize_b2()|s89.authorize_d()
 items=[];desc=[]
 for x in specs(m86):
  h=s105.motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series105D motion пересекается с прежними или между splits.')
  item={**x,'motion_sha256':h};items.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'});seen.add(h)
 return s101,models,items,desc,guards
def temp_pool(edge):
 edge=np.asarray(edge,float);n=len(edge);phase=(np.arange(n)+.5)/n;basis=np.column_stack([np.ones(n)]+[np.cos(np.pi*j*phase) for j in range(1,8)]);flat=(basis.T@edge/n).reshape(-1);rng=np.random.default_rng(105804);bins=rng.integers(0,POOL_DIM,size=len(flat));sign=rng.choice(np.array([-1.,1.]),size=len(flat));out=np.zeros(POOL_DIM);np.add.at(out,bins,flat*sign);return out/np.sqrt(len(flat)/POOL_DIM)
def truth_coeff(models,truth):
 b=models['b'].cosine_basis(len(truth));return np.linalg.lstsq(b,np.asarray(truth,float),rcond=None)[0].T.reshape(-1)
def case_features(s105,s104,s103,models,bridge,item,progress,fraction):
 commands=np.asarray(item['angles_deg'],float)*np.pi/180;images,actual=s104.capture(s103,bridge,commands,progress,max(.02,fraction-.003),.003,f'Official-eye dataset {item["id"]}');truth=np.asarray(actual[2:],float);coeff,_,_=s104.infer(models,images);edge=models['b'].edge_history(images);rev_coeff,_,_=s104.infer(models,images[::-1].copy());rev_edge=models['b'].edge_history(images[::-1].copy());rng=np.random.default_rng(105800000+item['id']);perm=rng.permutation(len(images));sh_coeff,_,_=s104.infer(models,images[perm].copy());sh_edge=models['b'].edge_history(images[perm].copy())
 return {'state':np.asarray(coeff,float),'temp':temp_pool(edge),'rev_state':np.asarray(rev_coeff,float),'rev_temp':temp_pool(rev_edge),'sh_state':np.asarray(sh_coeff,float),'sh_temp':temp_pool(sh_edge),'truth':truth,'truth_coeff':truth_coeff(models,truth),'action':np.array(ACTIONS.index(item['action']),dtype=np.int64)}
def atomic_npz(path,data):
 tmp=path.with_suffix('.tmp.npz');np.savez_compressed(tmp,**data);os.replace(tmp,path)
def load_cases(data_dir,items,role):
 out=[]
 for item in items:
  if item['role']!=role:continue
  p=data_dir/f"{item['id']}.npz"
  if not p.exists():continue
  with np.load(p,allow_pickle=False)as z:row={k:np.array(z[k],copy=True) for k in z.files}
  row.update({'id':item['id'],'action_name':item['action'],'replicate':item['replicate']});out.append(row)
 return out
def fit_linear(x,y,lam):
 x=np.asarray(x,float);y=np.asarray(y,float);xm=x.mean(0);xs=x.std(0);xs[xs<1e-9]=1.;ym=y.mean(0);ys=y.std(0);ys[ys<1e-9]=1.;zx=(x-xm)/xs;zy=(y-ym)/ys;w=np.linalg.solve(zx.T@zx+lam*np.eye(zx.shape[1]),zx.T@zy);return {'xm':xm,'xs':xs,'ym':ym,'ys':ys,'w':w}
def pred_linear(m,x):return ((np.asarray(x,float)-m['xm'])/m['xs']@m['w'])*m['ys']+m['ym']
def targets(rows):
 y=np.stack([r['truth_coeff'] for r in rows]);one=np.eye(3)[[int(r['action']) for r in rows]];return np.concatenate([y,one],axis=1)
def fit_models(train):
 y=targets(train);state=np.stack([r['state'] for r in train]);temp=np.stack([r['temp'] for r in train]);models={}
 models['state_multitask_ridge']={'kind':'linear','feature':'state','fit':fit_linear(state,y,10.)}
 xm=state.mean(0);xs=state.std(0);xs[xs<1e-9]=1.;rng=np.random.default_rng(105810);w=rng.normal(size=(state.shape[1],RFF_DIM))/np.sqrt(state.shape[1]);b=rng.uniform(0,2*np.pi,size=RFF_DIM);phi=np.sqrt(2/RFF_DIM)*np.cos((state-xm)/xs@w+b);models['state_random_fourier']={'kind':'rff','feature':'state','xm':xm,'xs':xs,'rw':w,'rb':b,'fit':fit_linear(phi,y,10.)}
 models['temporal_pool_ridge']={'kind':'linear','feature':'temp','fit':fit_linear(temp,y,100.)}
 classifier=fit_linear(temp,np.eye(3)[[int(r['action']) for r in train]],10.);experts=[]
 for ai in range(3):
  rr=[r for r in train if int(r['action'])==ai];experts.append(fit_linear(np.stack([r['temp'] for r in rr]),np.stack([r['truth_coeff'] for r in rr]),100.))
 models['temporal_action_experts']={'kind':'experts','feature':'temp','classifier':classifier,'experts':experts};return models
def predict(model,x):
 if model['kind']=='linear':z=pred_linear(model['fit'],x);return z[:72],z[72:]
 if model['kind']=='rff':phi=np.sqrt(2/RFF_DIM)*np.cos((np.asarray(x)-model['xm'])/model['xs']@model['rw']+model['rb']);z=pred_linear(model['fit'],phi);return z[:72],z[72:]
 logits=pred_linear(model['classifier'],x);ai=int(np.argmax(logits));return pred_linear(model['experts'][ai],x),logits
def feature(row,model,name,neutral):
 key=model['feature']
 if name=='candidate':return row[key]
 if name=='neutral_visual':return neutral[key]
 if name=='reversed_visual':return row['rev_'+key]
 if name=='shuffled_visual':return row['sh_'+key]
 return np.zeros_like(row[key])
def decode(models,coeff,n=49):return np.clip(models['b'].cosine_basis(n)@np.asarray(coeff).reshape(6,12).T,-np.pi*55/180,np.pi*55/180)
def evaluate(name,model,rows,neutral,base_models):
 out=[]
 for r in rows:
  controls={};candidate_logits=None
  for c in CONTROLS:
   coeff,logits=predict(model,feature(r,model,c,neutral));traj=decode(base_models,coeff,len(r['truth']));controls[c]={'truth_rmse_rad':float(np.sqrt(np.mean((traj-r['truth'])**2))),'target_sha256':sha_bytes(np.asarray(traj,dtype='<f8').tobytes())}
   if c=='candidate':candidate_logits=logits
  out.append({'id':r['id'],'action':r['action_name'],'predicted_action':ACTIONS[int(np.argmax(candidate_logits))],'controls':controls})
 return out
def metrics(rows,required):
 correct=sum(r['predicted_action']==r['action'] for r in rows);wins={c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad'] for r in rows) for c in CONTROLS if c!='candidate'};means={c:float(np.mean([r['controls'][c]['truth_rmse_rad'] for r in rows])) for c in CONTROLS};distinct=all(r['controls']['candidate']['target_sha256']!=r['controls'][c]['target_sha256'] for r in rows for c in CONTROLS if c!='candidate');passed=correct>=required and all(v>=required for v in wins.values())and distinct;return {'cases':len(rows),'required':required,'action_correct':correct,'truth_wins':wins,'mean_truth_rmse_rad':means,'targets_distinct':distinct,'passed':passed}
def choose(selection):
 eligible=[(name,x) for name,x in selection.items() if x['metrics']['passed']]
 if not eligible:return None
 return min(eligible,key=lambda z:(z[1]['metrics']['mean_truth_rmse_rad']['candidate'],z[0]))[0]
def pack_model(path,name,m):
 arrays={'model_name':np.array(name)}
 def lin(prefix,x):
  for k,v in x.items():arrays[prefix+k]=v
 if m['kind']=='linear':arrays['kind']=np.array('linear');arrays['feature']=np.array(m['feature']);lin('fit_',m['fit'])
 elif m['kind']=='rff':arrays.update({'kind':np.array('rff'),'feature':np.array('state'),'rff_mean':m['xm'],'rff_scale':m['xs'],'rff_weights':m['rw'],'rff_bias':m['rb']});lin('fit_',m['fit'])
 else:
  arrays.update({'kind':np.array('experts'),'feature':np.array('temp')});lin('classifier_',m['classifier'])
  for i,e in enumerate(m['experts']):lin(f'expert{i}_',e)
 np.savez_compressed(path,**arrays)
def protocol_for(desc):return {'schema':'action-aware-temporal-tournament-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner105c_sha256':RUNNER105C_SHA,'series105c_result_sha256':RESULT105C_SHA,'prior_outcomes':'Series104,105B,105C remain no-go','expected_wall_budget_hours':EXPECTED_HOURS,'checkpoint_each_capture':True,'resume_allowed':True,'training_uses_action_labels_and_actual_truth':True,'models':list(MODELS),'model_definitions':{'state_multitask_ridge':'official frozen state -> joint truth coefficients + action one-hot, ridge10','state_random_fourier':'384 deterministic cosine features -> multitask ridge10','temporal_pool_ridge':'384 hashed edge temporal-pool features -> multitask ridge100','temporal_action_experts':'temporal action ridge10 + three class-conditional trajectory ridges100'},'motions':desc,'selection_rule':'model must pass action/control >=12/18 on selection; among eligible minimum candidate RMSE then name; if none final remains untouched','final_rule':'selected model action correct and candidate wins vs neutral/reversed/zero/shuffled >=12/18; distinct targets','selection_and_final_not_used_for_fit':True,'post_result_tuning':False}
def fixture(temp,progress):
 names={n:{'metrics':{'passed':n=='temporal_action_experts','mean_truth_rmse_rad':{'candidate':.08 if n=='temporal_action_experts'else.2}}}for n in MODELS};selected=choose(names);rows=[]
 for i,a in enumerate(ACTIONS*6):
  controls={c:{'truth_rmse_rad':.08 if c=='candidate'else.2,'target_sha256':c+str(i)}for c in CONTROLS};rows.append({'id':1216+i,'action':a,'predicted_action':a,'controls':controls})
 primary={**metrics(rows,18),'development_candidate':True,'scientific_result':False};np.savez_compressed(temp/'selected_action_aware_model.npz',model_name=np.array(selected));progress('Fixture готова',.98,1,1);return names,selected,rows,primary,'fixture-model'
def run(source,d_folder,output_root=ROOT,resume=None,fixture_mode=False,progress=lambda *x:None):
 s105c,s105,s104,s102,s103,result105c,result105,result104=authorize();root=Path(output_root);root.mkdir(parents=True,exist_ok=True)
 if resume:
  folder=Path(resume);protocol=json.loads((folder/'protocol.json').read_text(encoding='utf8'));desc=protocol['motions'];items=[]
  # Recreate exact angle arrays only after sources are authorized below.
 else:folder=root/('action_aware_tournament_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();protocol=None
 temp=folder/'result_incomplete';temp.mkdir(exist_ok=True);data=folder/'checkpoint_data';data.mkdir(exist_ok=True);progress('Проверяются exact prerequisites',.01,0,1)
 if fixture_mode:desc=[];items=[]
 else:
  s101,base_models,items_new,desc_new,guards=prepare(s105c,s105,s104,s102,source,d_folder,result105c,result105)
  if protocol is None:items=items_new;desc=desc_new;protocol=protocol_for(desc);save(folder/'protocol.json',protocol)
  else:
   if protocol.get('script_sha256')!=file_sha(__file__):raise ValueError('Resume runner отличается от frozen protocol.')
   byid={x['id']:x for x in items_new};items=[byid[x['id']] for x in desc]
 if fixture_mode:
  protocol=protocol_for([]);protocol['mode']='fixture';save(folder/'protocol.json',protocol);selection,selected,final_rows,primary,model_sha=fixture(temp,progress)
 else:
  neutral_path=data/'neutral.npz';s101.worker_init(base_models['bundle'],base_models['s84v']);bridge=s103.Bridge();total=len(items)+1
  try:
   if not neutral_path.exists():
    n=len(np.asarray(items[0]['angles_deg']));images,_=s104.capture(s103,bridge,np.zeros((n,6)),progress,.015,.005,'Neutral official-eye control');coeff,_,_=s104.infer(base_models,images);atomic_npz(neutral_path,{'state':np.asarray(coeff,float),'temp':temp_pool(base_models['b'].edge_history(images))})
   for idx,item in enumerate([x for x in items if x['role']in('train','selection')]):
    p=data/f"{item['id']}.npz"
    if not p.exists():atomic_npz(p,case_features(s105,s104,s103,base_models,bridge,item,progress,.02+.70*(idx+1)/total))
    progress(f'Checkpoint {item["role"]} {item["id"]}',.02+.70*(idx+1)/total,idx+1,total)
   train=load_cases(data,items,'train');sel=load_cases(data,items,'selection')
   if len(train)!=90 or len(sel)!=18:raise ValueError('Checkpoint train/selection неполон.')
   with np.load(neutral_path,allow_pickle=False)as z:neutral={k:np.array(z[k],copy=True)for k in z.files}
   fitted=fit_models(train);selection={}
   for name in MODELS:
    rows=evaluate(name,fitted[name],sel,neutral,base_models);selection[name]={'metrics':metrics(rows,12),'rows':rows}
   selected=choose(selection)
   if selected is None:
    final_rows=[];primary={'final_cases':0,'passed':False,'development_candidate':False,'scientific_result':False,'reason':'no model passed frozen selection gate; final remained untouched'};model_sha=None
   else:
    final_items=[x for x in items if x['role']=='final']
    for j,item in enumerate(final_items):
     p=data/f"{item['id']}.npz"
     if not p.exists():atomic_npz(p,case_features(s105,s104,s103,base_models,bridge,item,progress,.73+.23*(j+1)/len(final_items)))
     progress(f'Checkpoint final {item["id"]}',.73+.23*(j+1)/len(final_items),j+1,len(final_items))
    final=load_cases(data,items,'final');final_rows=evaluate(selected,fitted[selected],final,neutral,base_models);fm=metrics(final_rows,12);primary={**fm,'development_candidate':fm['passed'],'scientific_result':False};model_path=temp/'selected_action_aware_model.npz';pack_model(model_path,selected,fitted[selected]);model_sha=file_sha(model_path)
   before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p) for p in before}or frozen_before!=s104.manifest(frozen_path):raise ValueError('Frozen sources изменились.')
  finally:bridge.close()
 report={'schema':'action-aware-temporal-tournament-result-v1','status':'fixture_completed'if fixture_mode else'completed','protocol':protocol,'series105c_primary':result105c['primary'],'selection':selection,'selected_model':selected,'selected_model_sha256':model_sha,'primary':primary,'final':final_rows,'limitations':['Supervised engineering development uses generated action labels and actual demonstrator truth.','Selection split chooses among four declared ideas; final is untouched unless a model passes selection.','Even a pass only authorizes separately preregistered physical Series106.','No biological vision, FlyVis/FlyWire, living animal or mirror-neuron claim.']};save(temp/'summary.json',report)
 if final_rows:
  with(temp/'final105d.csv').open('w',newline='',encoding='utf8')as f:
   flat=[{'id':r['id'],'action':r['action'],'predicted_action':r['predicted_action'],**{c+'_rmse':r['controls'][c]['truth_rmse_rad']for c in CONTROLS}}for r in final_rows];w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
 (temp/'ИТОГ.txt').write_text('SERIES105D: ACTION-AWARE TEMPORAL TOURNAMENT\n\nSelected: '+str(selected)+'\nDevelopment gate: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\nНе biological/physical confirmation result.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});result=folder/'result';temp.rename(result);progress('Готово',1.,1,1);return result
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series105D: 15-hour action-aware tournament');root.geometry('840x500+100+45');root.attributes('-topmost',True);status=tk.StringVar(value='Новый запуск или продолжение checkpoint');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series105D: action-aware temporal tournament',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='До15 часов:4 заранее заданные идеи,90 train +18 selection; final18 открывается только после selection pass.\nКаждый official-eye capture сохраняется отдельно; расчёт можно безопасно продолжить.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=650,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();buttons=tk.Frame(root);buttons.pack(pady=14);new=tk.Button(buttons,text='Начать новый запуск',padx=18,pady=9);cont=tk.Button(buttons,text='Продолжить checkpoint',padx=18,pady=9);new.pack(side='left',padx=8);cont.pack(side='left',padx=8)
 def update(text,fraction,done,total):
  def apply():
   p=round(fraction*100,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.02:elapsed=time.time()-start[0];eta.set(f'Прошло {elapsed/3600:.2f} ч · осталось примерно {elapsed*(1-fraction)/fraction/3600:.2f} ч')
  root.after(0,apply)
 def launch(resume=None):
  d=filedialog.askdirectory(title='Выберите завершённую result-папку Series89D',mustexist=True,initialdir=str(D_ROOT.resolve()if D_ROOT.exists()else Path.cwd()),parent=root)
  if not d:return
  source=filedialog.askdirectory(title='Выберите завершённую production Series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve()if SOURCE_ROOT.exists()else Path.cwd()),parent=root)
  if not source:return
  new.config(state='disabled');cont.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(source,d,resume=resume,progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series105D','Tournament завершён.',parent=root);new.config(state='normal');cont.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-105D.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series105D',f'{exc}\n\nCheckpoint сохранён. Отчёт открыт: {error.resolve()}',parent=root),new.config(state='normal'),cont.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 def resume_pick():
  p=filedialog.askdirectory(title='Выберите папку action_aware_tournament_... с protocol.json',mustexist=True,initialdir=str(ROOT.resolve()if ROOT.exists()else Path.cwd()),parent=root)
  if p:launch(p)
 new.config(command=lambda:launch(None));cont.config(command=resume_pick);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--resume');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.',a.output_root,fixture_mode=True))
 elif a.source84z and a.result89d:print(run(a.source84z,a.result89d,a.output_root,a.resume,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d.')
if __name__=='__main__':main()
