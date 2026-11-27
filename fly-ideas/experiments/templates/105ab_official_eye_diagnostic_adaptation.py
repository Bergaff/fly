#!/usr/bin/env python3
"""Series105A+B: diagnose official-eye domain shift, then fit one frozen paired adapter."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER104=HERE/'104_frozen89e_official_eye_policy.py';RUNNER104_SHA='ace8d99fa0ad71454fa7b4122868547c880817f9b45b9e654fb02245aad298a1'
RESULT104=HERE.parent/'reports'/'frozen89e-official-eye-policy-user-result.json';RESULT104_SHA='91109c557111c4278567d383a5f99ed281f05ea5bcbd5fa5e326752afdf6ba04'
ROOT=Path('workspace/runs/ideas/i-observational/official-eye-diagnostic-adaptation');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');TRAIN_N=12;VALID_N=6;VIEWS=(801,802,803,804);CONTROLS=('adapted','raw_frozen','neutral_visual','reversed_visual','zero_state','shuffled_state')
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
def motion_hash(degrees):
 x=np.asarray(degrees,float)
 if x.ndim!=2 or x.shape[1]!=6 or not np.isfinite(x).all():raise ValueError('Некорректное движение.')
 x=np.round((x*np.pi/180)*180/np.pi,7);x[x==0]=0;return sha_bytes(np.asarray(x,dtype='<f8').tobytes())
def authorize():
 if file_sha(RESULT104)!=RESULT104_SHA:raise ValueError('Exact Series104 result изменён.')
 result=json.loads(RESULT104.read_text(encoding='utf8'))
 if result.get('status')!='completed' or result.get('primary',{}).get('passed') is not False or result.get('primary',{}).get('scientific_result') is not False:raise ValueError('Series105 требует exact completed Series104 no-go.')
 if result.get('protocol',{}).get('script_sha256')!=RUNNER104_SHA:raise ValueError('Series104 result не соответствует corrected runner.')
 s104=load_module('series105_source104',RUNNER104,RUNNER104_SHA);s102,s103,_=s104.authorize();return s104,s102,s103,result
def adaptation_specs(m86):
 out=[]
 for rep in range(4):
  for ai,action in enumerate(ACTIONS):
   ident=1051+rep*3+ai;out.append({'role':'adapter_train','id':ident,'replicate':rep+1,'action':action,'seed':105100+rep*10+ai,'amplitude':(.68,.78,.88,.96)[rep],'speed':(.76,.92,1.08,1.16)[(rep+ai)%4],'angles_deg':m86.motif(action,105100+rep*10+ai,(.68,.78,.88,.96)[rep],(.76,.92,1.08,1.16)[(rep+ai)%4])})
 for rep in range(2):
  for ai,action in enumerate(ACTIONS):
   ident=1063+rep*3+ai;out.append({'role':'adapter_validation','id':ident,'replicate':rep+1,'action':action,'seed':105200+rep*10+ai,'amplitude':(.73,.93)[rep],'speed':(.84,1.12)[(rep+ai)%2],'angles_deg':m86.motif(action,105200+rep*10+ai,(.73,.93)[rep],(.84,1.12)[(rep+ai)%2])})
 return out
def prepare(s104,s102,source,d_folder):
 s101,models,diagnostic,diagnostic_desc,guards=s104.prepare(s102,source,d_folder);m=models['m'];m88=m.load88();m87=m88.load87();m86=m87.load86();s89=s101.load89e();seen=set()
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:seen|={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 seen|=m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|models['m2'].authorize_b()|models['m3'].authorize_b2()|s89.authorize_d()
 for old in s89.specs(False):seen.add(motion_hash(old['angles_deg']))
 for old in s102.load101().motion_specs(m86,False):seen.add(motion_hash(old['angles_deg']))
 for old in s102.motion_specs(m86,False):seen.add(motion_hash(old['angles_deg']))
 for old in s104.motion_specs(m86):seen.add(motion_hash(old['angles_deg']))
 items=[];desc=[]
 for x in adaptation_specs(m86):
  h=motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series105 training/validation motion пересекается с прежними или между splits.')
  item={**x,'motion_sha256':h};items.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'});seen.add(h)
 return s101,models,diagnostic,diagnostic_desc,items,desc,guards
def synthetic_reference(s101,models,item,views):
 rows=[s101.worker_visual((item,v)) for v in views];coeff=np.mean([np.asarray(r['_coeff'],float) for r in rows],axis=0);target=np.mean([np.asarray(r['_target'],float) for r in rows],axis=0)
 return coeff,target,[{'corner_id':int(r['corner_id']),'coeff_sha256':sha_bytes(np.asarray(r['_coeff'],dtype='<f8').tobytes())} for r in rows]
def capture_official(s104,s103,models,bridge,item,progress,base,span,label):
 commands=np.asarray(item['angles_deg'],float)*np.pi/180;images,actual=s104.capture(s103,bridge,commands,progress,base,span,label);coeff,targets,probs=s104.infer(models,images)
 return {'images':images,'truth':actual[2:],'coeff':np.asarray(coeff,float),'target':np.asarray(targets['candidate'],float),'probs':np.asarray(probs,float)}
def cosine(a,b):
 a=np.asarray(a,float).ravel();b=np.asarray(b,float).ravel();d=np.linalg.norm(a)*np.linalg.norm(b);return float(a@b/d) if d>0 else 0.
def rmse(a,b):return float(np.sqrt(np.mean((np.asarray(a,float)-np.asarray(b,float))**2)))
def diagnostic_row(s104,s101,s103,models,bridge,item,views,progress,base,span):
 off=capture_official(s104,s103,models,bridge,item,progress,base,span*.65,f'105A official {item["id"]}');syn_coeff,syn_target,view_hashes=synthetic_reference(s101,models,item,views)
 # Synthetic action probabilities must use the same unchanged frozen89E controls/readout.
 controls,probs=models['md'].controls_for(models['m3'],models['m2'],models['m'],models['b'],syn_coeff,syn_target,models['angle'],models['identity'],models['temp'],models['common'],float(models['d_summary']['model']['common_selected']['lambda']),models['experts'],models['selections'],models['standard'],models['standard_selections'])
 progress(f'105A synthetic reference {item["id"]}',base+span,1,1);edge=models['b'].edge_history(off['images'])
 return {'id':item['id'],'action':item['action'],'official_predicted_action':ACTIONS[int(np.argmax(off['probs']))],'synthetic_predicted_action':ACTIONS[int(np.argmax(probs))],'official_probabilities':{a:float(off['probs'][i]) for i,a in enumerate(ACTIONS)},'synthetic_probabilities':{a:float(probs[i]) for i,a in enumerate(ACTIONS)},'official_rgb_mean':float(np.mean(off['images'])),'official_rgb_std':float(np.std(off['images'])),'official_temporal_abs_delta':float(np.mean(np.abs(np.diff(off['images'].astype(float),axis=0)))),'official_edge_mean':float(np.mean(edge)),'official_edge_std':float(np.std(edge)),'state_cosine_official_to_synthetic':cosine(off['coeff'],syn_coeff),'state_nrmse_official_to_synthetic':rmse(off['coeff'],syn_coeff)/(float(np.std(syn_coeff))+1e-12),'official_target_truth_rmse_rad':rmse(off['target'],off['truth']),'synthetic_target_truth_rmse_rad':rmse(controls['candidate'],off['truth']),'official_state_sha256':sha_bytes(np.asarray(off['coeff'],dtype='<f8').tobytes()),'synthetic_mean_state_sha256':sha_bytes(np.asarray(syn_coeff,dtype='<f8').tobytes()),'synthetic_views':view_hashes}
def fit_adapter(x,y):
 x=np.asarray(x,float);y=np.asarray(y,float);mx=x.mean(0);my=y.mean(0);xc=x-mx;yc=y-my;sx=np.sqrt(np.mean(xc*xc,axis=0));sy=np.sqrt(np.mean(yc*yc,axis=0));cov=np.mean(xc*yc,axis=0);corr=np.divide(cov,sx*sy,out=np.zeros_like(cov),where=(sx*sy)>1e-12);corr=np.clip(corr,-1.,1.);scale=np.divide(corr*sy,sx,out=np.zeros_like(corr),where=sx>1e-12);scale=np.clip(scale,-3.,3.);return {'official_mean':mx,'synthetic_mean':my,'scale':scale,'correlation':corr}
def apply_adapter(model,coeff):return model['synthetic_mean']+(np.asarray(coeff,float)-model['official_mean'])*model['scale']
def policy_from_coeff(models,coeff):
 coeff=np.asarray(coeff,float);target=models['b'].cosine_basis(49)@coeff.reshape(6,12).T;controls,probs=models['md'].controls_for(models['m3'],models['m2'],models['m'],models['b'],coeff,target,models['angle'],models['identity'],models['temp'],models['common'],float(models['d_summary']['model']['common_selected']['lambda']),models['experts'],models['selections'],models['standard'],models['standard_selections']);return {k:np.asarray(v,float) for k,v in controls.items()},np.asarray(probs,float)
def validation_row(s104,s103,models,bridge,item,adapter,neutral_coeff,progress,base,span):
 off=capture_official(s104,s103,models,bridge,item,progress,base,span,f'105B validation {item["id"]}');adapted=apply_adapter(adapter,off['coeff']);controls,probs=policy_from_coeff(models,adapted);neutral_controls,_=policy_from_coeff(models,apply_adapter(adapter,neutral_coeff));rev_coeff,_,_=s104.infer(models,off['images'][::-1].copy());rev_controls,_=policy_from_coeff(models,apply_adapter(adapter,rev_coeff));targets={'adapted':controls['candidate'],'raw_frozen':off['target'],'neutral_visual':neutral_controls['candidate'],'reversed_visual':rev_controls['candidate'],'zero_state':controls['zero_state'],'shuffled_state':controls['shuffled_state']};metrics={k:{'truth_rmse_rad':rmse(v,off['truth']),'target_sha256':sha_bytes(np.asarray(v,dtype='<f8').tobytes())} for k,v in targets.items()}
 return {'id':item['id'],'action':item['action'],'predicted_action':ACTIONS[int(np.argmax(probs))],'probabilities':{a:float(probs[i]) for i,a in enumerate(ACTIONS)},'official_state_sha256':sha_bytes(np.asarray(off['coeff'],dtype='<f8').tobytes()),'adapted_state_sha256':sha_bytes(np.asarray(adapted,dtype='<f8').tobytes()),'controls':metrics}
def decide(rows,fixture=False):
 n=len(rows);required=n if fixture else 4;correct=sum(r['predicted_action']==r['action'] for r in rows);wins={k:sum(r['controls']['adapted']['truth_rmse_rad']<r['controls'][k]['truth_rmse_rad'] for r in rows) for k in CONTROLS if k!='adapted'};distinct=all(r['controls']['adapted']['target_sha256']!=r['controls'][k]['target_sha256'] for r in rows for k in ('neutral_visual','reversed_visual','zero_state','shuffled_state'));means={k:float(np.mean([r['controls'][k]['truth_rmse_rad'] for r in rows])) for k in CONTROLS};passed=correct>=required and all(wins[k]>=required for k in ('raw_frozen','neutral_visual','reversed_visual','zero_state','shuffled_state')) and distinct and means['adapted']<means['raw_frozen'];return {'validation_cases':n,'required_action_correct':required,'required_control_wins':required,'action_correct':correct,'adapted_truth_wins':wins,'mean_truth_rmse_rad':means,'targets_distinct':distinct,'passed':passed,'development_candidate':passed,'scientific_result':False}
def fixture_run(folder,temp,protocol,progress):
 rng=np.random.default_rng(105);x=rng.normal(size=(TRAIN_N,72));y=.4+1.7*x;adapter=fit_adapter(x,y);rows=[]
 for i,a in enumerate(ACTIONS*2):
  base=.20+i*.01;controls={k:{'truth_rmse_rad':base if k=='adapted' else base+.12,'target_sha256':k+str(i)} for k in CONTROLS};rows.append({'id':1063+i,'action':a,'predicted_action':a,'controls':controls})
 primary=decide(rows,True);diagnostic=[{'id':903+i,'action':a,'state_cosine_official_to_synthetic':.2,'official_target_truth_rmse_rad':.25,'synthetic_target_truth_rmse_rad':.10} for i,a in enumerate(ACTIONS*2)];np.savez_compressed(temp/'paired_diagonal_adapter.npz',**adapter);progress('Fixture готова',.98,1,1);return diagnostic,rows,primary,adapter,[]
def run(source,d_folder,output_root=ROOT,fixture=False,progress=lambda *x:None):
 s104,s102,s103,result104=authorize();root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('official_eye_adaptation_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();progress('Проверяются exact prerequisites',.01,0,1)
 if fixture:desc=[];diagnostic_desc=[]
 else:s101,models,diagnostic_items,diagnostic_desc,items,desc,guards=prepare(s104,s102,source,d_folder);views=[v for v in s101.views(False) if v['corner_id'] in VIEWS]
 protocol={'schema':'official-eye-diagnostic-adaptation-v1','mode':'fixture'if fixture else'full','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner104_sha256':RUNNER104_SHA,'series104_result_sha256':RESULT104_SHA,'series104_outcome':'completed preregistered no-go; never overwritten or reinterpreted','phase105a':{'role':'post-result diagnostic on disclosed Series104 motions903-908','fit_allowed':False,'primary_gate':None,'motions':diagnostic_desc},'phase105b':{'training_allowed':True,'adapter':'paired diagonal affine official frozen state to mean of four synthetic-view frozen states','fit_uses_action_labels_or_truth':False,'fixed_scale_clip':[-3,3],'train_cases':TRAIN_N,'validation_cases':VALID_N,'motions':desc,'validation_used_for_fit_or_selection':False,'hyperparameter_selection':False,'post_result_tuning':False},'synthetic_reference_views':list(VIEWS),'validation_controls':list(CONTROLS),'development_gate':'validation action correct>=4/6; adapted truth RMSE wins>=4/6 vs raw/neutral/reversed/zero/shuffled; all control targets distinct; mean adapted<mean raw. Success only authorizes separate untouched physical Series106.'};save(folder/'protocol.json',protocol)
 if fixture:diagnostic,rows,primary,adapter,desc=fixture_run(folder,temp,protocol,progress)
 else:
  s101.worker_init(models['bundle'],models['s84v']);bridge=s103.Bridge();diagnostic=[];pairs=[];rows=[]
  try:
   for i,item in enumerate(diagnostic_items):diagnostic.append(diagnostic_row(s104,s101,s103,models,bridge,item,views,progress,.03+.25*i/len(diagnostic_items),.25/len(diagnostic_items)))
   train=[x for x in items if x['role']=='adapter_train'];valid=[x for x in items if x['role']=='adapter_validation']
   for i,item in enumerate(train):
    off=capture_official(s104,s103,models,bridge,item,progress,.28+.35*i/len(train),.20/len(train),f'105B training official {item["id"]}');syn_coeff,_,view_hashes=synthetic_reference(s101,models,item,views);pairs.append({'id':item['id'],'action':item['action'],'official_coeff':off['coeff'],'synthetic_coeff':syn_coeff,'official_state_sha256':sha_bytes(np.asarray(off['coeff'],dtype='<f8').tobytes()),'synthetic_state_sha256':sha_bytes(np.asarray(syn_coeff,dtype='<f8').tobytes()),'synthetic_views':view_hashes});progress(f'105B training pair {item["id"]}',.28+.35*(i+1)/len(train),i+1,len(train))
   adapter=fit_adapter([p['official_coeff'] for p in pairs],[p['synthetic_coeff'] for p in pairs]);np.savez_compressed(temp/'paired_diagonal_adapter.npz',**adapter);neutral_n=len(np.asarray(valid[0]['angles_deg']));neutral_images,_=s104.capture(s103,bridge,np.zeros((neutral_n,6)),progress,.64,.04,'105B neutral visual');neutral_coeff,_,_=s104.infer(models,neutral_images)
   for i,item in enumerate(valid):rows.append(validation_row(s104,s103,models,bridge,item,adapter,neutral_coeff,progress,.68+.28*i/len(valid),.28/len(valid)))
   primary=decide(rows,False);before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p) for p in before}or frozen_before!=s104.manifest(frozen_path):raise ValueError('Frozen sources изменились.')
  finally:bridge.close()
  pair_clean=[{k:v for k,v in p.items() if k not in ('official_coeff','synthetic_coeff')} for p in pairs]
 report={'schema':'official-eye-diagnostic-adaptation-result-v1','status':'fixture_completed'if fixture else'completed','protocol':protocol,'series104_primary':result104['primary'],'diagnostic105a':{'cases':diagnostic,'interpretation_only':True,'can_change_series104':False},'adapter105b':{'model_sha256':file_sha(temp/'paired_diagonal_adapter.npz'),'training_pairs':[] if fixture else pair_clean,'mean_abs_feature_correlation':float(np.mean(np.abs(adapter['correlation']))),'nonzero_scales':int(np.count_nonzero(adapter['scale']))},'primary':primary,'validation':rows,'limitations':['Series105A is post-result diagnosis and cannot rescue or alter Series104.','Series105B is a newly trained engineering domain adapter, not unchanged frozen89E replication.','Validation is non-physical development evidence; any success requires new untouched Series106 physical outcomes.','No FlyVis/FlyWire/connectome mapping, living animal, biological vision, or mirror-neuron claim.']};save(temp/'summary.json',report)
 with(temp/'diagnostic105a.csv').open('w',newline='',encoding='utf8')as f:
  flat=[{k:v for k,v in r.items() if not isinstance(v,(dict,list))} for r in diagnostic];w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
 (temp/'ИТОГ.txt').write_text('SERIES105A+B: OFFICIAL-EYE DIAGNOSTIC + TRAINED ADAPTER\n\nSeries104 остаётся no-go.\n105B development gate: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\nНе биологический и не physical confirmation result.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series105A+B: official-eye diagnosis and adaptation');root.geometry('800x455+130+65');root.attributes('-topmost',True);status=tk.StringVar(value='Один запуск: диагностика105A, затем обучение и validation105B');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series105A + 105B',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='105A диагностирует раскрытые motions903–908. Затем105B обучает paired adapter\nтолько на train split и проверяет на отдельных validation motions. Series104 остаётся no-go.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=620,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать result89D и source84Z, затем запустить 105A+B',padx=18,pady=9);button.pack(pady=14)
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
     messagebox.showinfo('Series105A+B','Диагностика, adapter training и validation завершены.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-105AB.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series105A+B',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.',a.output_root,True))
 elif a.source84z and a.result89d:print(run(a.source84z,a.result89d,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d.')
if __name__=='__main__':main()
