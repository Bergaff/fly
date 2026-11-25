#!/usr/bin/env python3
"""Series107: supervised temporal-order repair tournament after the Series106 grooming no-go."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER106=HERE/'106_frozen_action_aware_physical_validation.py';RUNNER106_SHA='282a7a87ae43b3c6a5b2432c01495c564ee3dc3e1247c0230015917ada5ea5fa'
RESULT106=HERE.parent/'reports'/'frozen-action-aware-physical-validation-106-user-result.json';RESULT106_SHA='1eadcbcfea31c973f9993da16be7cd0b01998d2f4c6c7aa27c54b4c08da00be9'
MODEL105D_SHA='1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1'
ROOT=Path('workspace/runs/ideas/i-observational/grooming-temporal-order-repair');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact');MODEL_ROOT=Path('workspace/runs/ideas/i-observational/action-aware-temporal-tournament')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');CONTROLS=('candidate','neutral_visual','reversed_visual','zero_input','shuffled_visual');MODELS=tuple(f'{scope}_{shape}_{q}'for scope in('global','action')for shape in('linear','quadratic')for q in('q00','q05'));SPLITS=(('train',20,1246,107100),('selection',6,1306,107400),('final',6,1324,107600));EXPECTED_HOURS=12.
def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha_bytes(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p)for p in sorted(Path(folder).rglob('*'))if p.is_file()and p.name!='complete.json'}
def load_module(name,path,sha):
 if file_sha(path)!=sha:raise ValueError(f'Закреплённый {path.name} изменился.')
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize():
 if file_sha(RESULT106)!=RESULT106_SHA:raise ValueError('Exact genuine Series106 result изменён.')
 r=json.loads(RESULT106.read_text(encoding='utf8'));p=r.get('primary',{})
 if r.get('status')!='completed'or r.get('protocol',{}).get('script_sha256')!=RUNNER106_SHA or p.get('passed')is not False or p.get('physical_development_candidate')is not False or p.get('candidate_truth_wins_by_class',{}).get('head_directed_grooming',{}).get('shuffled_visual')!=1 or p.get('required_control_wins_per_class')!=2:raise ValueError('Series107 требует exact completed Series106 grooming-specific no-go.')
 s106=load_module('series107_source106',RUNNER106,RUNNER106_SHA);deps=s106.authorize();return(s106,*deps,r)
def hashes_in(x):
 out=set()
 if isinstance(x,dict):
  for k,v in x.items():out.add(v)if k=='motion_sha256'and isinstance(v,str)else out.update(hashes_in(v))
 elif isinstance(x,list):
  for v in x:out.update(hashes_in(v))
 return out
def specs(m86):
 out=[]
 for role,reps,start,seed0 in SPLITS:
  for rep in range(reps):
   for ai,a in enumerate(ACTIONS):
    ident=start+rep*3+ai;seed=seed0+rep*10+ai;amp=.61+.37*((rep*11+ai*5)%19)/18;speed=.70+.52*((rep*7+ai*3)%17)/16;out.append({'role':role,'id':ident,'replicate':rep+1,'action':a,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(a,seed,amp,speed)})
 return out
def prepare(s106,s105d,s105c,s105,s104,s102,source,d_folder,r106,r105d,r105c,r105):
 s101,models,_,_,guards=s106.prepare(s105d,s105c,s105,s104,s102,source,d_folder,r105d,r105c,r105);m=models['m'];m88=m.load88();m87=m88.load87();m86=m87.load86();seen=hashes_in(r106)|hashes_in(r105d)|hashes_in(r105c)|hashes_in(r105)
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)as db:seen|={z[0]for z in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items=[];desc=[]
 for x in specs(m86):
  h=s105.motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series107 motion пересекается с прежними outcomes или между splits.')
  q={**x,'motion_sha256':h};items.append(q);desc.append({k:v for k,v in q.items()if k!='angles_deg'});seen.add(h)
 return s101,models,items,desc,guards
def diag(edge,quadratic=False):
 x=np.asarray(edge,float);eps=1e-12;f=[]
 for lag in (1,2,4,8):
  a=x[:-lag];b=x[lag:];d=np.mean(np.abs(b-a),axis=1);f.extend((float(d.mean()),float(d.std()),float(np.quantile(d,.5)),float(np.quantile(d,.9))));num=np.sum(a*b,axis=1);den=np.sqrt(np.sum(a*a,axis=1)*np.sum(b*b,axis=1))+eps;f.append(float(np.mean(num/den)))
 d1=np.diff(x,axis=0);d2=np.diff(x,n=2,axis=0);energy=np.mean(x*x,axis=1);f.extend((float(np.mean(np.abs(d2))),float(np.std(np.abs(d2))),float(energy.mean()),float(energy.std()),float(np.quantile(energy,.9)),float(np.mean(np.abs(np.diff(energy))))));z=np.asarray(f,float);return np.concatenate((z,z*z))if quadratic else z
def truth_coeff(models,truth):
 b=models['b'].cosine_basis(len(truth));return np.linalg.lstsq(b,np.asarray(truth,float),rcond=None)[0].T.reshape(-1)
def case_data(s105d,s104,s103,base,bridge,item,progress,fraction):
 cmd=np.asarray(item['angles_deg'],float)*np.pi/180;images,actual=s104.capture(s103,bridge,cmd,progress,max(.02,fraction-.003),.003,f'Grooming repair dataset {item["id"]}');truth=np.asarray(actual[2:],float);edge=base['b'].edge_history(images);rng=np.random.default_rng(107000000+item['id']);perm=rng.permutation(len(images));rev=base['b'].edge_history(images[::-1].copy());sh=base['b'].edge_history(images[perm].copy());return {'temp':s105d.temp_pool(edge),'rev_temp':s105d.temp_pool(rev),'sh_temp':s105d.temp_pool(sh),'diag':diag(edge),'rev_diag':diag(rev),'sh_diag':diag(sh),'diag_q':diag(edge,True),'rev_diag_q':diag(rev,True),'sh_diag_q':diag(sh,True),'truth':truth,'truth_coeff':truth_coeff(base,truth),'action':np.array(ACTIONS.index(item['action']),dtype=np.int64)}
def atomic_npz(path,data):
 tmp=path.with_suffix('.tmp.npz');np.savez_compressed(tmp,**data);os.replace(tmp,path)
def load_cases(folder,items,role):
 out=[]
 for item in items:
  if item['role']!=role:continue
  p=folder/f"{item['id']}.npz"
  if not p.exists():continue
  with np.load(p,allow_pickle=False)as z:r={k:np.array(z[k],copy=True)for k in z.files}
  r.update({'id':item['id'],'action_name':item['action']});out.append(r)
 return out
def fit_linear(x,y,lam=3.):
 x=np.asarray(x,float);y=np.asarray(y,float);xm=x.mean(0);xs=x.std(0);xs[xs<1e-9]=1.;z=(x-xm)/xs;w=np.linalg.solve(z.T@z+lam*np.eye(z.shape[1]),z.T@y);return{'xm':xm,'xs':xs,'w':w}
def score(m,x):return float((np.asarray(x)-m['xm'])/m['xs']@m['w'])
def detector_rows(rows,key,action=None):
 rr=rows if action is None else[r for r in rows if int(r['action'])==action];x=[];y=[]
 for r in rr:x.extend((r[key],r['sh_'+key]));y.extend((1.,0.))
 return np.stack(x),np.asarray(y)
def fit_detector(rows,name):
 key='diag_q'if'quadratic'in name else'diag';per='action_'in name
 if per:
  fits=[];thresholds=[]
  for ai in range(3):
   x,y=detector_rows(rows,key,ai);m=fit_linear(x,y);scores=[score(m,r[key])for r in rows if int(r['action'])==ai];threshold=float(min(scores)-1e-12)if'q00'in name else float(np.quantile(scores,.05));fits.append(m);thresholds.append(threshold)
  return{'name':name,'key':key,'per_action':True,'fits':fits,'thresholds':np.asarray(thresholds)}
 x,y=detector_rows(rows,key);m=fit_linear(x,y);scores=[score(m,r[key])for r in rows];threshold=float(min(scores)-1e-12)if'q00'in name else float(np.quantile(scores,.05));return{'name':name,'key':key,'per_action':False,'fits':[m],'thresholds':np.array([threshold])}
def valid(det,x,action):
 i=action if det['per_action']else 0;return score(det['fits'][i],x)>=det['thresholds'][i]
def decode(s105d,base,coeff,n):return s105d.decode(base,coeff,n)
def evaluate(s105d,base,base_model,det,rows,neutral):
 out=[]
 for r in rows:
  base_coeff,logits=s105d.predict(base_model,r['temp']);ai=int(np.argmax(logits));zero_coeff,_=s105d.predict(base_model,np.zeros_like(r['temp']));controls={};accepted={}
  for c in CONTROLS:
   if c=='candidate':t,d=r['temp'],r[det['key']]
   elif c=='neutral_visual':t,d=neutral['temp'],neutral[det['key']]
   elif c=='reversed_visual':t,d=r['rev_temp'],r['rev_'+det['key']]
   elif c=='shuffled_visual':t,d=r['sh_temp'],r['sh_'+det['key']]
   else:t,d=np.zeros_like(r['temp']),None
   coeff,_=s105d.predict(base_model,t);ok=False if c=='zero_input'else valid(det,d,ai);coeff=coeff if ok else zero_coeff;traj=decode(s105d,base,coeff,len(r['truth']));controls[c]={'truth_rmse_rad':float(np.sqrt(np.mean((traj-r['truth'])**2))),'target_sha256':sha_bytes(np.asarray(traj,dtype='<f8').tobytes())};accepted[c]=ok
  out.append({'id':r['id'],'action':r['action_name'],'predicted_action':ACTIONS[ai],'validity_accepted':accepted,'controls':controls})
 return out
def metrics(rows,required=12,per_action=4):
 correct=sum(r['predicted_action']==r['action']for r in rows);wins={c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows)for c in CONTROLS if c!='candidate'};by={a:{c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['action']==a)for c in CONTROLS if c!='candidate'}for a in ACTIONS};means={c:float(np.mean([r['controls'][c]['truth_rmse_rad']for r in rows]))for c in CONTROLS};candidate_kept=sum(r['validity_accepted']['candidate']for r in rows);distinct=all(r['controls']['candidate']['target_sha256']!=r['controls'][c]['target_sha256']for r in rows for c in CONTROLS if c!='candidate');passed=correct>=required and candidate_kept==len(rows)and all(wins[c]>=required for c in wins)and all(by[a][c]>=per_action for a in ACTIONS for c in by[a])and distinct;return{'cases':len(rows),'required_overall':required,'required_per_action':per_action,'action_correct':correct,'candidate_kept':candidate_kept,'truth_wins':wins,'truth_wins_by_action':by,'mean_truth_rmse_rad':means,'targets_distinct':distinct,'passed':passed}
def choose(selection):
 ok=[(n,v)for n,v in selection.items()if v['metrics']['passed']];return None if not ok else min(ok,key=lambda z:(z[1]['metrics']['mean_truth_rmse_rad']['candidate'],z[0]))[0]
def pack(path,det):
 arrays={'adapter_name':np.array(det['name']),'base_model_sha256':np.array(MODEL105D_SHA),'key':np.array(det['key']),'per_action':np.array(det['per_action']),'thresholds':det['thresholds']}
 for i,m in enumerate(det['fits']):
  for k,v in m.items():arrays[f'fit{i}_{k}']=v
 np.savez_compressed(path,**arrays)
def protocol_for(desc):return{'schema':'grooming-temporal-order-repair-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner106_sha256':RUNNER106_SHA,'series106_result_sha256':RESULT106_SHA,'base_model_sha256':MODEL105D_SHA,'expected_wall_budget_hours':EXPECTED_HOURS,'checkpoint_each_capture':True,'resume_allowed':True,'training_uses_sequence_validity_labels_action_labels_and_actual_truth':True,'models':list(MODELS),'model_definitions':'global/action-specific linear or fixed quadratic temporal-order detector, each with train-min q00 or 5th-percentile q05 valid threshold; rejected sequence uses exact base zero-input target; base temporal classifier/experts unchanged','motions':desc,'selection_rule':'all candidate valid; action>=12/18; overall wins>=12/18 and per-action wins>=4/6 against every control; then minimum candidate RMSE','final_rule':'same frozen gate on untouched18 final; final unopened if no selection pass','post_result_tuning':False,'series106_final_reuse_forbidden':True}
def fixture(temp,progress):
 selection={n:{'metrics':{'passed':n=='action_quadratic_q05','mean_truth_rmse_rad':{'candidate':.06}}}for n in MODELS};selected=choose(selection);rows=[]
 for i,a in enumerate(ACTIONS*6):
  controls={c:{'truth_rmse_rad':.06 if c=='candidate'else.2,'target_sha256':c+str(i)}for c in CONTROLS};rows.append({'id':1324+i,'action':a,'predicted_action':a,'validity_accepted':{c:c=='candidate'or c=='reversed_visual'for c in CONTROLS},'controls':controls})
 primary={**metrics(rows,18,6),'development_candidate':True,'scientific_result':False};np.savez_compressed(temp/'selected_grooming_repair_adapter.npz',adapter_name=np.array(selected));progress('Fixture готова',.98,1,1);return selection,selected,rows,primary,'fixture-adapter'
def run(source,d_folder,model_folder,output_root=ROOT,resume=None,fixture_mode=False,progress=lambda*x:None):
 s106,s105d,s105c,s105,s104,s102,s103,r105d,r105c,r105,r106=authorize();root=Path(output_root);root.mkdir(parents=True,exist_ok=True)
 if resume:folder=Path(resume);protocol=json.loads((folder/'protocol.json').read_text(encoding='utf8'))
 else:folder=root/('grooming_order_repair_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();protocol=None
 temp=folder/'result_incomplete';temp.mkdir(exist_ok=True);data=folder/'checkpoint_data';data.mkdir(exist_ok=True);progress('Проверяются exact prerequisites',.01,0,1)
 if fixture_mode:desc=[];items=[];base_model=None;model_path=Path(__file__)
 else:
  model_path,base_model=s106.load_selected(model_folder);s101,base,items_new,desc_new,guards=prepare(s106,s105d,s105c,s105,s104,s102,source,d_folder,r106,r105d,r105c,r105)
  if protocol is None:items,desc=items_new,desc_new;protocol=protocol_for(desc);save(folder/'protocol.json',protocol)
  else:
   if protocol.get('script_sha256')!=file_sha(__file__):raise ValueError('Resume runner отличается от frozen protocol.')
   byid={x['id']:x for x in items_new};desc=protocol['motions'];items=[byid[x['id']]for x in desc]
 if fixture_mode:protocol=protocol_for([]);protocol['mode']='fixture';save(folder/'protocol.json',protocol);selection,selected,final_rows,primary,adapter_sha=fixture(temp,progress)
 else:
  neutral_path=data/'neutral.npz';s101.worker_init(base['bundle'],base['s84v']);bridge=s103.Bridge();total=len(items)+1
  try:
   if not neutral_path.exists():
    n=len(np.asarray(items[0]['angles_deg']));images,_=s104.capture(s103,bridge,np.zeros((n,6)),progress,.015,.005,'Neutral temporal-order control');edge=base['b'].edge_history(images);atomic_npz(neutral_path,{'temp':s105d.temp_pool(edge),'diag':diag(edge),'diag_q':diag(edge,True)})
   for idx,item in enumerate([x for x in items if x['role']in('train','selection')]):
    p=data/f"{item['id']}.npz"
    if not p.exists():atomic_npz(p,case_data(s105d,s104,s103,base,bridge,item,progress,.02+.70*(idx+1)/total))
    progress(f'Checkpoint {item["role"]} {item["id"]}',.02+.70*(idx+1)/total,idx+1,total)
   train=load_cases(data,items,'train');sel=load_cases(data,items,'selection')
   if len(train)!=60 or len(sel)!=18:raise ValueError('Checkpoint train/selection неполон.')
   with np.load(neutral_path,allow_pickle=False)as z:neutral={k:np.array(z[k],copy=True)for k in z.files}
   fitted={n:fit_detector(train,n)for n in MODELS};selection={}
   for n in MODELS:
    rows=evaluate(s105d,base,base_model,fitted[n],sel,neutral);selection[n]={'metrics':metrics(rows,12,4),'rows':rows,'thresholds':fitted[n]['thresholds']}
   selected=choose(selection)
   if selected is None:final_rows=[];primary={'final_cases':0,'passed':False,'development_candidate':False,'scientific_result':False,'reason':'no temporal-order repair passed frozen selection; final remained untouched'};adapter_sha=None
   else:
    final_items=[x for x in items if x['role']=='final']
    for j,item in enumerate(final_items):
     p=data/f"{item['id']}.npz"
     if not p.exists():atomic_npz(p,case_data(s105d,s104,s103,base,bridge,item,progress,.73+.23*(j+1)/len(final_items)))
     progress(f'Checkpoint final {item["id"]}',.73+.23*(j+1)/len(final_items),j+1,len(final_items))
    final=load_cases(data,items,'final');final_rows=evaluate(s105d,base,base_model,fitted[selected],final,neutral);fm=metrics(final_rows,12,4);primary={**fm,'development_candidate':fm['passed'],'scientific_result':False};adapter=temp/'selected_grooming_repair_adapter.npz';pack(adapter,fitted[selected]);adapter_sha=file_sha(adapter)
   before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p)for p in before}or frozen_before!=s104.manifest(frozen_path)or file_sha(model_path)!=MODEL105D_SHA:raise ValueError('Frozen sources/base model изменились.')
  finally:bridge.close()
 report={'schema':'grooming-temporal-order-repair-result-v1','status':'fixture_completed'if fixture_mode else'completed','protocol':protocol,'series106_primary':r106['primary'],'selection':selection,'selected_adapter':selected,'selected_adapter_sha256':adapter_sha,'primary':primary,'final':final_rows,'limitations':['Supervised engineering repair uses generated sequence-validity/action labels and actual demonstrator truth.','Series106 remains a no-go and its final is not reused.','A pass authorizes only a separately frozen new physical Series108.','No biological vision, FlyVis/FlyWire, living animal or mirror-neuron claim.']};save(temp/'summary.json',report)
 if final_rows:
  with(temp/'final107.csv').open('w',newline='',encoding='utf8')as f:flat=[{'id':r['id'],'action':r['action'],'predicted_action':r['predicted_action'],**{c+'_rmse':r['controls'][c]['truth_rmse_rad']for c in CONTROLS}}for r in final_rows];w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
 (temp/'ИТОГ.txt').write_text('SERIES107: GROOMING TEMPORAL-ORDER REPAIR\n\nSelected: '+str(selected)+'\nDevelopment gate: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\nSeries106 remains no-go; not biological/physical confirmation.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});result=folder/'result';temp.rename(result);progress('Готово',1.,1,1);return result
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series107: grooming temporal-order repair');root.geometry('850x510+95+40');root.attributes('-topmost',True);status=tk.StringVar(value='Новый запуск или продолжение checkpoint');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series107: чиним shuffled specificity груминга',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='60 train +18 selection + conditional untouched18 final. Восемь temporal-order detector идей.\nSeries106 не переигрывается: это новая supervised development серия с checkpoint каждого capture.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=660,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();box=tk.Frame(root);box.pack(pady=14);new=tk.Button(box,text='Начать новый запуск',padx=18,pady=9);cont=tk.Button(box,text='Продолжить checkpoint',padx=18,pady=9);new.pack(side='left',padx=8);cont.pack(side='left',padx=8)
 def update(text,fraction,done,total):
  def apply():
   p=round(100*fraction,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.02:e=time.time()-start[0];eta.set(f'Прошло {e/3600:.2f} ч · осталось примерно {e*(1-fraction)/fraction/3600:.2f} ч')
  root.after(0,apply)
 def launch(resume=None):
  model=filedialog.askdirectory(title='Выберите папку запуска Series105D или её result',mustexist=True,initialdir=str(MODEL_ROOT.resolve()if MODEL_ROOT.exists()else Path.cwd()),parent=root)
  if not model:return
  d=filedialog.askdirectory(title='Выберите завершённую result-папку Series89D',mustexist=True,initialdir=str(D_ROOT.resolve()if D_ROOT.exists()else Path.cwd()),parent=root)
  if not d:return
  source=filedialog.askdirectory(title='Выберите production Series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve()if SOURCE_ROOT.exists()else Path.cwd()),parent=root)
  if not source:return
  new.config(state='disabled');cont.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(source,d,model,resume=resume,progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series107','Repair tournament завершён.',parent=root);new.config(state='normal');cont.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-107.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series107',f'{exc}\n\nCheckpoint сохранён. Отчёт открыт: {error.resolve()}',parent=root),new.config(state='normal'),cont.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 def resume_pick():
  p=filedialog.askdirectory(title='Выберите grooming_order_repair_... с protocol.json',mustexist=True,initialdir=str(ROOT.resolve()if ROOT.exists()else Path.cwd()),parent=root)
  if p:launch(p)
 new.config(command=lambda:launch(None));cont.config(command=resume_pick);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--model105d');p.add_argument('--resume');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.','.',a.output_root,fixture_mode=True))
 elif a.source84z and a.result89d and a.model105d:print(run(a.source84z,a.result89d,a.model105d,a.output_root,a.resume,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d+model105d.')
if __name__=='__main__':main()
