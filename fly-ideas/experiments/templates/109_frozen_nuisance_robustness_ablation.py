#!/usr/bin/env python3
"""Series109: frozen visual-nuisance transfer with explicit adapter ablation."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER108=HERE/'108_frozen_grooming_repair_physical_validation.py';RUNNER108_SHA='7fd7efb4c6219834bafc2ca7b3098e5c1208dd036f5b46f4c2ac34fc911960d4'
RESULT108=HERE.parent/'reports'/'frozen-grooming-repair-physical-108-user-result.json';RESULT108_SHA='9253e4bcb60ee9ea3d5fa990561e4807ee31eaf51b457fd198735b4d90ec0e64'
BASE_SHA='1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1';ADAPTER_SHA='4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57'
ROOT=Path('workspace/runs/ideas/i-observational/frozen-nuisance-robustness');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact');MODEL_ROOT=Path('workspace/runs/ideas/i-observational/action-aware-temporal-tournament');ADAPTER_ROOT=Path('workspace/runs/ideas/i-observational/grooming-temporal-order-repair')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');DOMAINS=('dim','bright','low_contrast','sensor_noise','horizontal_shift','frame_dropout');CONDITIONS=('repaired_candidate','base_candidate_ablation','neutral_visual','reversed_visual','repaired_shuffled','base_shuffled_ablation','zero_input','open_loop')
def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha_bytes(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return{str(p.relative_to(folder)).replace('\\','/'):file_sha(p)for p in sorted(Path(folder).rglob('*'))if p.is_file()and p.name!='complete.json'}
def load_module(name,path,sha):
 if file_sha(path)!=sha:raise ValueError(f'Закреплённый {path.name} изменился.')
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize():
 if file_sha(RESULT108)!=RESULT108_SHA:raise ValueError('Exact genuine Series108 result изменён.')
 r=json.loads(RESULT108.read_text(encoding='utf8'));p=r.get('primary',{})
 if r.get('status')!='completed'or r.get('protocol',{}).get('script_sha256')!=RUNNER108_SHA or r.get('protocol',{}).get('base_model_sha256')!=BASE_SHA or r.get('protocol',{}).get('adapter_sha256')!=ADAPTER_SHA or p.get('physical_development_candidate')is not True or p.get('scientific_result')is not False:raise ValueError('Series109 требует exact successful Series108 engineering result.')
 s108=load_module('series109_source108',RUNNER108,RUNNER108_SHA);deps=s108.authorize();return(s108,*deps,r)
def hashes_in(x):
 out=set()
 if isinstance(x,dict):
  for k,v in x.items():out.add(v)if k=='motion_sha256'and isinstance(v,str)else out.update(hashes_in(v))
 elif isinstance(x,list):
  for v in x:out.update(hashes_in(v))
 return out
def specs(m86):
 out=[]
 for di,domain in enumerate(DOMAINS):
  for ai,a in enumerate(ACTIONS):
   ident=1360+di*3+ai;seed=109100+di*10+ai;amp=(.58,.66,.75,.86,.95,1.02)[di];speed=(.56,.74,.92,1.10,1.26,1.34)[(di+ai)%6];out.append({'role':'cross_domain_final','id':ident,'domain':domain,'action':a,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(a,seed,amp,speed)})
 return out
def prepare(s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r109base,r107,r106,r105d,r105c,r105):
 s101,models,_,_,guards=s108.prepare(s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r107,r106,r105d,r105c,r105);m86=models['m'].load88().load87().load86();seen=hashes_in(r109base)|hashes_in(r107)|hashes_in(r106)|hashes_in(r105d)|hashes_in(r105c)|hashes_in(r105)
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)as db:seen|={z[0]for z in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items=[];desc=[]
 for x in specs(m86):
  h=s105.motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series109 motion пересекается с прежними outcomes.')
  q={**x,'motion_sha256':h};items.append(q);desc.append({k:v for k,v in q.items()if k!='angles_deg'});seen.add(h)
 return s101,models,items,desc,guards
def perturb(images,domain,seed):
 x=np.asarray(images);dtype=x.dtype;y=x.astype(float);scale=255. if np.issubdtype(dtype,np.integer)else max(1.,float(np.max(y)))
 if domain=='dim':y*=.55
 elif domain=='bright':y=np.clip(y*1.28+.05*scale,0,scale)
 elif domain=='low_contrast':
  mean=np.mean(y,axis=tuple(range(1,y.ndim)),keepdims=True);y=mean+.52*(y-mean)
 elif domain=='sensor_noise':y+=np.random.default_rng(seed).normal(0,.035*scale,size=y.shape)
 elif domain=='horizontal_shift':y=np.roll(y,3,axis=-2 if y.ndim>=4 and y.shape[-1]in(1,3,4)else-1)
 elif domain=='frame_dropout':
  for i in range(4,len(y),5):y[i]=y[i-1]
 y=np.clip(y,0,scale);return np.rint(y).astype(dtype)if np.issubdtype(dtype,np.integer)else y.astype(dtype)
def base_target(s105d,base,model,temp,n):
 coeff,logits=s105d.predict(model,temp);return s105d.decode(base,coeff,n),logits
def repaired_target(s107,s105d,base,model,det,temp,d,ai,n):
 coeff,_=s105d.predict(model,temp);zero,_=s105d.predict(model,np.zeros_like(temp));ok=s107.valid(det,d,ai);return s105d.decode(base,coeff if ok else zero,n),ok
def capture_case(s108,s107,s105d,s104,s103,base,bridge,item,neutral_images,model,det,progress,fraction):
 cmd=np.asarray(item['angles_deg'],float)*np.pi/180;raw,actual=s104.capture(s103,bridge,cmd,progress,max(.02,fraction-.006),.006,f'Nuisance transfer capture {item["id"]}');truth=np.asarray(actual[2:],float);images=perturb(raw,item['domain'],109000000+item['id']);neutral=perturb(neutral_images,item['domain'],109900000+item['id']);edge=base['b'].edge_history(images);nt_edge=base['b'].edge_history(neutral);rng=np.random.default_rng(109000000+item['id']);perm=rng.permutation(len(images));rev=base['b'].edge_history(images[::-1].copy());sh=base['b'].edge_history(images[perm].copy());temp=s105d.temp_pool(edge);base_candidate,logits=base_target(s105d,base,model,temp,len(truth));ai=int(np.argmax(logits));targets={'base_candidate_ablation':base_candidate};accepted={};targets['repaired_candidate'],accepted['candidate']=repaired_target(s107,s105d,base,model,det,temp,s107.diag(edge),ai,len(truth));targets['neutral_visual'],accepted['neutral']=repaired_target(s107,s105d,base,model,det,s105d.temp_pool(nt_edge),s107.diag(nt_edge),ai,len(truth));targets['reversed_visual'],accepted['reversed']=repaired_target(s107,s105d,base,model,det,s105d.temp_pool(rev),s107.diag(rev),ai,len(truth));sh_temp=s105d.temp_pool(sh);targets['repaired_shuffled'],accepted['shuffled']=repaired_target(s107,s105d,base,model,det,sh_temp,s107.diag(sh),ai,len(truth));targets['base_shuffled_ablation'],_=base_target(s105d,base,model,sh_temp,len(truth));zero,_=s105d.predict(model,np.zeros_like(temp));targets['zero_input']=s105d.decode(base,zero,len(truth));targets['open_loop']=targets['repaired_candidate'];return truth,targets,accepted,logits
def safe(x):return x['finite']and x['minimum_thorax_z_mm']>=.15 and x['maximum_thorax_z_mm']<=2.5 and x['contact_frame_fraction']>0
def decide(rows,fixture=False):
 n=len(rows);overall=n if fixture else 12;open_req=n if fixture else 15;per_action=6 if fixture else 3;per_domain=3 if fixture else 2;accept_req=n if fixture else 15;accept_action=6 if fixture else 4;cand=[r['controls']['repaired_candidate']for r in rows];comparators=('neutral_visual','reversed_visual','repaired_shuffled','zero_input');wins={c:sum(r['controls']['repaired_candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows)for c in comparators};by_action={a:{c:sum(r['controls']['repaired_candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['action']==a)for c in comparators}for a in ACTIONS};by_domain={d:{c:sum(r['controls']['repaired_candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['domain']==d)for c in comparators}for d in DOMAINS};open_wins=sum(r['controls']['repaired_candidate']['truth_rmse_rad']<r['controls']['open_loop']['truth_rmse_rad']for r in rows);adapter_gain=sum(r['controls']['repaired_shuffled']['truth_rmse_rad']>r['controls']['base_shuffled_ablation']['truth_rmse_rad']for r in rows);gain_action={a:sum(r['controls']['repaired_shuffled']['truth_rmse_rad']>r['controls']['base_shuffled_ablation']['truth_rmse_rad']for r in rows if r['action']==a)for a in ACTIONS};gain_domain={d:sum(r['controls']['repaired_shuffled']['truth_rmse_rad']>r['controls']['base_shuffled_ablation']['truth_rmse_rad']for r in rows if r['domain']==d)for d in DOMAINS};kept=sum(r['validity_accepted']['candidate']for r in rows);rejected=sum(not(r['validity_accepted']['shuffled'])for r in rows);kept_action={a:sum(r['validity_accepted']['candidate']for r in rows if r['action']==a)for a in ACTIONS};rejected_action={a:sum(not(r['validity_accepted']['shuffled'])for r in rows if r['action']==a)for a in ACTIONS};kept_domain={d:sum(r['validity_accepted']['candidate']for r in rows if r['domain']==d)for d in DOMAINS};rejected_domain={d:sum(not(r['validity_accepted']['shuffled'])for r in rows if r['domain']==d)for d in DOMAINS};correct=sum(r['predicted_action']==r['action']for r in rows);correct_action={a:sum(r['predicted_action']==a for r in rows if r['action']==a)for a in ACTIONS};tracking=float(np.mean([x['tracking_rmse_rad']for x in cand]));distinct=all(r['target_hashes']['repaired_candidate']!=r['target_hashes'][c]for r in rows for c in comparators);passed=sum(safe(x)for x in cand)==n and tracking<=.20 and kept>=accept_req and rejected>=accept_req and correct>=accept_req and all(kept_action[a]>=accept_action and rejected_action[a]>=accept_action and correct_action[a]>=accept_action for a in ACTIONS)and all(kept_domain[d]>=per_domain and rejected_domain[d]>=per_domain for d in DOMAINS)and all(wins[c]>=overall for c in comparators)and all(by_action[a][c]>=per_action for a in ACTIONS for c in comparators)and all(by_domain[d][c]>=per_domain for d in DOMAINS for c in comparators)and open_wins>=open_req and adapter_gain>=overall and all(gain_action[a]>=per_action for a in ACTIONS)and all(gain_domain[d]>=per_domain for d in DOMAINS)and distinct;return{'cases':n,'required_overall':overall,'required_per_action':per_action,'required_per_domain':per_domain,'candidate_safe_cases':sum(safe(x)for x in cand),'candidate_mean_tracking_rmse_rad':tracking,'candidate_validity_kept':kept,'shuffled_validity_rejected':rejected,'candidate_kept_by_action':kept_action,'shuffled_rejected_by_action':rejected_action,'candidate_kept_by_domain':kept_domain,'shuffled_rejected_by_domain':rejected_domain,'action_correct':correct,'action_correct_by_class':correct_action,'candidate_truth_wins':wins,'candidate_truth_wins_by_action':by_action,'candidate_truth_wins_by_domain':by_domain,'open_loop_wins':open_wins,'adapter_gain_cases':adapter_gain,'adapter_gain_by_action':gain_action,'adapter_gain_by_domain':gain_domain,'targets_distinct':distinct,'passed':passed,'robustness_candidate':passed,'scientific_result':False}
def fixture_rows():
 rows=[]
 for di,d in enumerate(DOMAINS):
  for ai,a in enumerate(ACTIONS):
   controls={c:{'finite':True,'tracking_rmse_rad':.05,'truth_rmse_rad':(.06 if c in('repaired_candidate','base_candidate_ablation')else(.13 if c=='base_shuffled_ablation'else.21)),'contact_frame_fraction':1.,'mean_contact_legs':4.,'max_actuator_force_norm':8.,'minimum_thorax_z_mm':.8,'maximum_thorax_z_mm':1.2,'energy_abs_work':1.,'torque_saturation_fraction':0.}for c in CONDITIONS};rows.append({'id':1360+di*3+ai,'domain':d,'action':a,'predicted_action':a,'validity_accepted':{'candidate':True,'neutral':True,'reversed':True,'shuffled':False},'target_hashes':{c:c+str(di)+str(ai)for c in CONDITIONS},'controls':controls})
 return rows
def run(source,d_folder,model_folder,adapter_folder,output_root=ROOT,fixture=False,progress=lambda*x:None):
 s108,s107,s106,s105d,s105c,s105,s104,s102,s103,r105d,r105c,r105,r106,r107,r108=authorize();model_path,model=s106.load_selected(model_folder)if not fixture else(Path(__file__),None);adapter_path,det=s108.load_adapter(adapter_folder)if not fixture else(Path(__file__),None);root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('nuisance_robustness_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();progress('Проверяются exact artifacts',.01,0,1)
 if fixture:desc=[];rows=fixture_rows();trace=[];primary=decide(rows,True)
 else:
  s101,base,items,desc,guards=prepare(s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r108,r107,r106,r105d,r105c,r105);s101.worker_init(base['bundle'],base['s84v']);bridge=s103.Bridge();rows=[];trace=[]
  try:
   n=len(np.asarray(items[0]['angles_deg']));neutral_images,_=s104.capture(s103,bridge,np.zeros((n,6)),progress,.01,.02,'Neutral nuisance source');total=len(items)*len(CONDITIONS);done=0
   for i,item in enumerate(items):
    truth,targets,accepted,logits=capture_case(s108,s107,s105d,s104,s103,base,bridge,item,neutral_images,model,det,progress,.03+.25*(i+1)/len(items));controls={}
    for c in CONDITIONS:
     metric=s104.rollout(s103,bridge,targets[c],truth,c=='open_loop');sample=metric.pop('sample');controls[c]=metric
     for fi,angles in enumerate(sample):trace.append({'id':item['id'],'domain':item['domain'],'action':item['action'],'condition':c,'frame':fi,**{s103.MAPPED_DOF[j]:float(angles[j])for j in range(6)}})
     done+=1;progress('Cross-domain physical controls',.28+.68*done/total,done,total)
    hashes={c:sha_bytes(np.asarray(v,dtype='<f8').tobytes())for c,v in targets.items()};rows.append({'id':item['id'],'domain':item['domain'],'action':item['action'],'predicted_action':ACTIONS[int(np.argmax(logits))],'validity_accepted':accepted,'target_hashes':hashes,'controls':controls})
   before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p)for p in before}or frozen_before!=s104.manifest(frozen_path)or file_sha(model_path)!=BASE_SHA or file_sha(adapter_path)!=ADAPTER_SHA:raise ValueError('Frozen sources/artifacts изменились.')
   primary=decide(rows,False)
  finally:bridge.close()
 protocol={'schema':'frozen-nuisance-robustness-ablation-v1','mode':'fixture'if fixture else'full','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner108_sha256':RUNNER108_SHA,'series108_result_sha256':RESULT108_SHA,'base_model_sha256':BASE_SHA,'adapter_sha256':ADAPTER_SHA,'training_allowed':False,'selection_allowed':False,'post_result_tuning':False,'domains':list(DOMAINS),'motions':desc,'conditions':list(CONDITIONS),'nuisance_definition':'deterministic post-capture pixel/frame perturbations; physical demonstrator/body and official-eye capture unchanged','primary_rule':'all safety/tracking; validity/action>=15 and >=4/action, >=2/domain; wins repaired controls>=12, >=3/action, >=2/domain; open>=15; adapter improves shuffled RMSE>=12, >=3/action, >=2/domain; distinct'};save(folder/'protocol.json',protocol);report={'schema':'frozen-nuisance-robustness-ablation-result-v1','status':'fixture_completed'if fixture else'completed','protocol':protocol,'series108_primary':r108['primary'],'primary':primary,'tests':rows,'limitations':['Visual nuisances are deterministic digital post-capture perturbations, not physical camera hardware changes.','Exact supervised generated-action policy; no Series109 training or selection.','No biological vision, living fly, real muscles, FlyVis/FlyWire/connectome or mirror-neuron claim.']};save(temp/'summary.json',report)
 if trace:
  with(temp/'physical_trace.csv').open('w',newline='',encoding='utf8')as f:w=csv.DictWriter(f,fieldnames=list(trace[0]));w.writeheader();w.writerows(trace)
 (temp/'ИТОГ.txt').write_text('SERIES109: FROZEN NUISANCE ROBUSTNESS + ADAPTER ABLATION\n\nPrimary: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\nCross-domain engineering robustness, not biological result.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series109: nuisance robustness + adapter ablation');root.geometry('880x520+80+35');root.attributes('-topmost',True);status=tk.StringVar(value='Выберите exact artifacts и frozen sources');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series109: новый домен, не ещё одни похожие seeds',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='6 visual nuisance domains ×3 actions ×8 physical conditions =144 rollouts.\nExact frozen policy; explicit base-only adapter ablation; no fit/selection/tuning.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=690,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать base105D, adapter107, result89D, source84Z и запустить',padx=18,pady=9);button.pack(pady=14)
 def update(text,fraction,done,total):
  def apply():
   p=round(100*fraction,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.02:e=time.time()-start[0];eta.set(f'Прошло {e/60:.1f} мин · осталось примерно {e*(1-fraction)/fraction/60:.1f} мин')
  root.after(0,apply)
 def begin():
  model=filedialog.askdirectory(title='Выберите папку запуска Series105D или её result',mustexist=True,initialdir=str(MODEL_ROOT.resolve()if MODEL_ROOT.exists()else Path.cwd()),parent=root)
  if not model:return
  adapter=filedialog.askdirectory(title='Выберите папку запуска Series107 или её result',mustexist=True,initialdir=str(ADAPTER_ROOT.resolve()if ADAPTER_ROOT.exists()else Path.cwd()),parent=root)
  if not adapter:return
  d=filedialog.askdirectory(title='Выберите завершённую result89D',mustexist=True,initialdir=str(D_ROOT.resolve()if D_ROOT.exists()else Path.cwd()),parent=root)
  if not d:return
  source=filedialog.askdirectory(title='Выберите production source84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve()if SOURCE_ROOT.exists()else Path.cwd()),parent=root)
  if not source:return
  button.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(source,d,model,adapter,progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series109','Robustness validation завершён.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-109.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series109',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--model105d');p.add_argument('--adapter107');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.','.','.',a.output_root,True))
 elif all((a.source84z,a.result89d,a.model105d,a.adapter107)):print(run(a.source84z,a.result89d,a.model105d,a.adapter107,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d+model105d+adapter107.')
if __name__=='__main__':main()
