#!/usr/bin/env python3
"""Series110: deterministic nuisance-normalization front-end tournament."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER109=HERE/'109_frozen_nuisance_robustness_ablation.py';RUNNER109_SHA='691dbd14b76c1be975890236d1be81a9f8868b8825bb83846081730eaaf1f42b'
RESULT109=HERE.parent/'reports'/'frozen-nuisance-robustness-ablation-109-user-result.json';RESULT109_SHA='e7cfc5068fb53ae69782d3d31ce03e16605c044699a3a41590193a5276c99f03'
BASE_SHA='1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1';ADAPTER_SHA='4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57'
ROOT=Path('workspace/runs/ideas/i-observational/nuisance-frontend-repair');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact');MODEL_ROOT=Path('workspace/runs/ideas/i-observational/action-aware-temporal-tournament');ADAPTER_ROOT=Path('workspace/runs/ideas/i-observational/grooming-temporal-order-repair')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');DOMAINS=('dim','bright','low_contrast','sensor_noise','horizontal_shift','frame_dropout');NORMALIZERS=('raw','sequence_percentile','frame_percentile','sequence_zscore','percentile_temporal','percentile_spatial');CONTROLS=('candidate','neutral_visual','reversed_visual','zero_input','shuffled_visual','base_shuffled_ablation')
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
 if file_sha(RESULT109)!=RESULT109_SHA:raise ValueError('Exact genuine Series109 result изменён.')
 r=json.loads(RESULT109.read_text(encoding='utf8'));p=r.get('primary',{})
 if r.get('status')!='completed'or r.get('protocol',{}).get('script_sha256')!=RUNNER109_SHA or p.get('passed')is not False or p.get('robustness_candidate')is not False or p.get('candidate_kept_by_domain',{}).get('dim')!=0 or p.get('candidate_kept_by_domain',{}).get('low_contrast')!=0:raise ValueError('Series110 требует exact Series109 dim/contrast no-go.')
 s109=load_module('series110_source109',RUNNER109,RUNNER109_SHA);deps=s109.authorize();return(s109,*deps,r)
def hashes_in(x):
 out=set()
 if isinstance(x,dict):
  for k,v in x.items():out.add(v)if k=='motion_sha256'and isinstance(v,str)else out.update(hashes_in(v))
 elif isinstance(x,list):
  for v in x:out.update(hashes_in(v))
 return out
def specs(m86):
 out=[]
 for role,start,seed0 in(('selection',1378,110100),('final',1396,110400)):
  for di,d in enumerate(DOMAINS):
   for ai,a in enumerate(ACTIONS):
    ident=start+di*3+ai;seed=seed0+di*10+ai;amp=(.60,.68,.77,.87,.96,1.01)[di];speed=(.58,.76,.94,1.12,1.28,1.36)[(di+ai)%6];out.append({'role':role,'id':ident,'domain':d,'action':a,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(a,seed,amp,speed)})
 return out
def prepare(s109,s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r109,r108,r107,r106,r105d,r105c,r105):
 s101,models,_,_,guards=s109.prepare(s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r108,r107,r106,r105d,r105c,r105);m86=models['m'].load88().load87().load86();seen=hashes_in(r109)|hashes_in(r108)|hashes_in(r107)|hashes_in(r106)|hashes_in(r105d)|hashes_in(r105c)|hashes_in(r105)
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)as db:seen|={z[0]for z in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items=[];desc=[]
 for x in specs(m86):
  h=s105.motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series110 motion пересекается с прежними outcomes.')
  q={**x,'motion_sha256':h};items.append(q);desc.append({k:v for k,v in q.items()if k!='angles_deg'});seen.add(h)
 return s101,models,items,desc,guards
def normalize(images,name):
 x=np.asarray(images);dtype=x.dtype;y=x.astype(float);hi=255. if np.issubdtype(dtype,np.integer)else max(1.,float(np.max(y)))
 if name=='raw':return x.copy()
 axes=tuple(range(1,y.ndim))
 if name in('sequence_percentile','percentile_temporal','percentile_spatial'):
  lo,up=np.quantile(y,(.02,.98));y=(y-lo)*hi/max(up-lo,1e-9)
 elif name=='frame_percentile':
  lo=np.quantile(y,.02,axis=axes,keepdims=True);up=np.quantile(y,.98,axis=axes,keepdims=True);y=(y-lo)*hi/np.maximum(up-lo,1e-9)
 elif name=='sequence_zscore':y=(y-y.mean())*min(70.,.22*hi)/max(y.std(),1e-9)+.5*hi
 if name=='percentile_temporal':
  z=y.copy();z[1:-1]=(y[:-2]+2*y[1:-1]+y[2:])/4;y=z
 if name=='percentile_spatial':
  ax=-2 if y.ndim>=4 and y.shape[-1]in(1,3,4)else-1;other=ax-1;y=(4*y+np.roll(y,1,ax)+np.roll(y,-1,ax)+np.roll(y,1,other)+np.roll(y,-1,other))/8
 y=np.clip(y,0,hi);return np.rint(y).astype(dtype)if np.issubdtype(dtype,np.integer)else y.astype(dtype)
def feature_pack(s109,s107,s105d,base,images,item_id):
 edge=base['b'].edge_history(images);rng=np.random.default_rng(110000000+item_id);perm=rng.permutation(len(images));rev=base['b'].edge_history(images[::-1].copy());sh=base['b'].edge_history(images[perm].copy());return{'temp':s105d.temp_pool(edge),'diag':s107.diag(edge),'rev_temp':s105d.temp_pool(rev),'rev_diag':s107.diag(rev),'sh_temp':s105d.temp_pool(sh),'sh_diag':s107.diag(sh)}
def atomic_npz(path,data):
 tmp=path.with_suffix('.tmp.npz');np.savez_compressed(tmp,**data);os.replace(tmp,path)
def capture_data(s109,s107,s105d,s104,s103,base,bridge,item,progress,fraction):
 cmd=np.asarray(item['angles_deg'],float)*np.pi/180;raw,actual=s104.capture(s103,bridge,cmd,progress,max(.02,fraction-.006),.006,f'Nuisance repair capture {item["id"]}');truth=np.asarray(actual[2:],float);nuis=s109.perturb(raw,item['domain'],110900000+item['id']);out={'truth':truth,'action':np.array(ACTIONS.index(item['action']),dtype=np.int64)}
 for name in NORMALIZERS:
  f=feature_pack(s109,s107,s105d,base,normalize(nuis,name),item['id']);out.update({name+'_'+k:v for k,v in f.items()})
 return out
def load_cases(folder,items,role):
 out=[]
 for item in items:
  if item['role']!=role:continue
  with np.load(folder/f"{item['id']}.npz",allow_pickle=False)as z:r={k:np.array(z[k],copy=True)for k in z.files}
  r.update({'id':item['id'],'domain':item['domain'],'action_name':item['action']});out.append(r)
 return out
def target(s107,s105d,base,model,det,temp,d,ai,n):
 coeff,_=s105d.predict(model,temp);zero,_=s105d.predict(model,np.zeros_like(temp));ok=s107.valid(det,d,ai);return s105d.decode(base,coeff if ok else zero,n),ok
def evaluate(s107,s105d,base,model,det,rows,neutral,name):
 out=[]
 for r in rows:
  p=name+'_';temp=r[p+'temp'];_,logits=s105d.predict(model,temp);ai=int(np.argmax(logits));zero,_=s105d.predict(model,np.zeros_like(temp));controls={};accepted={}
  for c,t,d in(('candidate',temp,r[p+'diag']),('neutral_visual',neutral[name+'_temp'],neutral[name+'_diag']),('reversed_visual',r[p+'rev_temp'],r[p+'rev_diag']),('shuffled_visual',r[p+'sh_temp'],r[p+'sh_diag'])):
   traj,ok=target(s107,s105d,base,model,det,t,d,ai,len(r['truth']));controls[c]={'truth_rmse_rad':float(np.sqrt(np.mean((traj-r['truth'])**2))),'target_sha256':sha_bytes(np.asarray(traj,dtype='<f8').tobytes())};accepted[c]=ok
  ztraj=s105d.decode(base,zero,len(r['truth']));controls['zero_input']={'truth_rmse_rad':float(np.sqrt(np.mean((ztraj-r['truth'])**2))),'target_sha256':sha_bytes(np.asarray(ztraj,dtype='<f8').tobytes())};bcoeff,_=s105d.predict(model,r[p+'sh_temp']);btraj=s105d.decode(base,bcoeff,len(r['truth']));controls['base_shuffled_ablation']={'truth_rmse_rad':float(np.sqrt(np.mean((btraj-r['truth'])**2))),'target_sha256':sha_bytes(np.asarray(btraj,dtype='<f8').tobytes())};out.append({'id':r['id'],'domain':r['domain'],'action':r['action_name'],'predicted_action':ACTIONS[ai],'validity_accepted':accepted,'controls':controls})
 return out
def metrics(rows,fixture=False):
 n=len(rows);required=n if fixture else 12;per_action=6 if fixture else 4;per_domain=3 if fixture else 2;accept=n if fixture else 15;comparators=('neutral_visual','reversed_visual','zero_input','shuffled_visual');wins={c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows)for c in comparators};by_a={a:{c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['action']==a)for c in comparators}for a in ACTIONS};by_d={d:{c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['domain']==d)for c in comparators}for d in DOMAINS};kept=sum(r['validity_accepted']['candidate']for r in rows);rejected=sum(not(r['validity_accepted']['shuffled_visual'])for r in rows);correct=sum(r['predicted_action']==r['action']for r in rows);kept_d={d:sum(r['validity_accepted']['candidate']for r in rows if r['domain']==d)for d in DOMAINS};rejected_d={d:sum(not(r['validity_accepted']['shuffled_visual'])for r in rows if r['domain']==d)for d in DOMAINS};gain=sum(r['controls']['shuffled_visual']['truth_rmse_rad']>r['controls']['base_shuffled_ablation']['truth_rmse_rad']for r in rows);gain_d={d:sum(r['controls']['shuffled_visual']['truth_rmse_rad']>r['controls']['base_shuffled_ablation']['truth_rmse_rad']for r in rows if r['domain']==d)for d in DOMAINS};means={c:float(np.mean([r['controls'][c]['truth_rmse_rad']for r in rows]))for c in CONTROLS};distinct=all(r['controls']['candidate']['target_sha256']!=r['controls'][c]['target_sha256']for r in rows for c in comparators);passed=kept>=accept and rejected>=accept and correct>=accept and all(kept_d[d]>=per_domain and rejected_d[d]>=per_domain and gain_d[d]>=per_domain for d in DOMAINS)and gain>=required and all(wins[c]>=required for c in comparators)and all(by_a[a][c]>=per_action for a in ACTIONS for c in comparators)and all(by_d[d][c]>=per_domain for d in DOMAINS for c in comparators)and distinct;return{'cases':n,'required_overall':required,'required_per_action':per_action,'required_per_domain':per_domain,'candidate_kept':kept,'shuffled_rejected':rejected,'action_correct':correct,'candidate_kept_by_domain':kept_d,'shuffled_rejected_by_domain':rejected_d,'truth_wins':wins,'truth_wins_by_action':by_a,'truth_wins_by_domain':by_d,'adapter_gain_cases':gain,'adapter_gain_by_domain':gain_d,'mean_truth_rmse_rad':means,'targets_distinct':distinct,'passed':passed}
def choose(selection):
 ok=[(n,v)for n,v in selection.items()if v['metrics']['passed']];return None if not ok else min(ok,key=lambda z:(z[1]['metrics']['mean_truth_rmse_rad']['candidate'],z[0]))[0]
def fixture(temp,progress):
 selection={n:{'metrics':{'passed':n=='percentile_temporal','mean_truth_rmse_rad':{'candidate':.07}}}for n in NORMALIZERS};selected=choose(selection);rows=[]
 for di,d in enumerate(DOMAINS):
  for ai,a in enumerate(ACTIONS):
   controls={c:{'truth_rmse_rad':.07 if c=='candidate'else(.13 if c=='base_shuffled_ablation'else.2),'target_sha256':c+str(di)+str(ai)}for c in CONTROLS};rows.append({'id':1396+di*3+ai,'domain':d,'action':a,'predicted_action':a,'validity_accepted':{'candidate':True,'neutral_visual':True,'reversed_visual':True,'shuffled_visual':False},'controls':controls})
 primary={**metrics(rows,True),'development_candidate':True,'scientific_result':False};np.savez_compressed(temp/'selected_nuisance_frontend.npz',normalizer=np.array(selected));progress('Fixture готова',.98,1,1);return selection,selected,rows,primary,'fixture-frontend'
def run(source,d_folder,model_folder,adapter_folder,output_root=ROOT,fixture_mode=False,progress=lambda*x:None):
 s109,s108,s107,s106,s105d,s105c,s105,s104,s102,s103,r105d,r105c,r105,r106,r107,r108,r109=authorize();model_path,model=s106.load_selected(model_folder)if not fixture_mode else(Path(__file__),None);adapter_path,det=s108.load_adapter(adapter_folder)if not fixture_mode else(Path(__file__),None);root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('nuisance_frontend_repair_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();data=folder/'checkpoint_data';data.mkdir();progress('Проверяются exact artifacts',.01,0,1)
 if fixture_mode:desc=[];items=[];protocol={'mode':'fixture'};save(folder/'protocol.json',protocol);selection,selected,final_rows,primary,frontend_sha=fixture(temp,progress)
 else:
  s101,base,items,desc,guards=prepare(s109,s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r109,r108,r107,r106,r105d,r105c,r105);protocol={'schema':'nuisance-frontend-repair-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner109_sha256':RUNNER109_SHA,'series109_result_sha256':RESULT109_SHA,'base_model_sha256':BASE_SHA,'adapter_sha256':ADAPTER_SHA,'normalizers':list(NORMALIZERS),'motions':desc,'selection_rule':'pass validity/action/wins/adapter-gain overall+action+domain, then minimum candidate RMSE/name; final untouched if none','post_result_tuning':False};save(folder/'protocol.json',protocol);s101.worker_init(base['bundle'],base['s84v']);bridge=s103.Bridge()
  try:
   n=len(np.asarray(items[0]['angles_deg']));raw,_=s104.capture(s103,bridge,np.zeros((n,6)),progress,.01,.02,'Neutral nuisance frontend source');neutral={}
   for name in NORMALIZERS:
    f=feature_pack(s109,s107,s105d,base,normalize(raw,name),110999999);neutral.update({name+'_'+k:v for k,v in f.items()})
   selection_items=[x for x in items if x['role']=='selection']
   for i,item in enumerate(selection_items):atomic_npz(data/f"{item['id']}.npz",capture_data(s109,s107,s105d,s104,s103,base,bridge,item,progress,.03+.65*(i+1)/len(selection_items)))
   sel=load_cases(data,items,'selection');selection={}
   for name in NORMALIZERS:
    rows=evaluate(s107,s105d,base,model,det,sel,neutral,name);selection[name]={'metrics':metrics(rows),'rows':rows}
   selected=choose(selection)
   if selected is None:final_rows=[];primary={'final_cases':0,'passed':False,'development_candidate':False,'scientific_result':False,'reason':'no frontend passed selection; final remained untouched'};frontend_sha=None
   else:
    finals=[x for x in items if x['role']=='final']
    for i,item in enumerate(finals):atomic_npz(data/f"{item['id']}.npz",capture_data(s109,s107,s105d,s104,s103,base,bridge,item,progress,.70+.27*(i+1)/len(finals)))
    final=load_cases(data,items,'final');final_rows=evaluate(s107,s105d,base,model,det,final,neutral,selected);fm=metrics(final_rows);primary={**fm,'development_candidate':fm['passed'],'scientific_result':False};front=temp/'selected_nuisance_frontend.npz';np.savez_compressed(front,normalizer=np.array(selected),runner_sha256=np.array(file_sha(__file__)));frontend_sha=file_sha(front)
   before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p)for p in before}or frozen_before!=s104.manifest(frozen_path)or file_sha(model_path)!=BASE_SHA or file_sha(adapter_path)!=ADAPTER_SHA:raise ValueError('Frozen sources/artifacts изменились.')
  finally:bridge.close()
 report={'schema':'nuisance-frontend-repair-result-v1','status':'fixture_completed'if fixture_mode else'completed','protocol':protocol,'series109_primary':r109['primary'],'selection':selection,'selected_frontend':selected,'selected_frontend_sha256':frontend_sha,'primary':primary,'final':final_rows,'limitations':['Supervised selection among deterministic front ends on generated nuisance cases.','Series109 remains a no-go; pass only authorizes separate frozen physical validation.','Digital nuisances are not hardware camera or biological transfer.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('SERIES110: NUISANCE FRONTEND REPAIR\n\nSelected: '+str(selected)+'\nDevelopment gate: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series110: nuisance frontend repair');root.geometry('870x510+85+40');root.attributes('-topmost',True);status=tk.StringVar(value='Выберите exact artifacts и sources');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series110: чиним dim/low-contrast и noise/dropout',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='6 deterministic normalization ideas,18 selection и conditional untouched18 final.\nSeries109 final не переиспользуется; base+adapter остаются exact frozen.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=680,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать base105D, adapter107, result89D, source84Z и запустить',padx=18,pady=9);button.pack(pady=14)
 def update(text,fraction,done,total):
  def apply():
   p=round(100*fraction,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.02:e=time.time()-start[0];eta.set(f'Прошло {e/60:.1f} мин · осталось примерно {e*(1-fraction)/fraction/60:.1f} мин')
  root.after(0,apply)
 def begin():
  model=filedialog.askdirectory(title='Выберите папку Series105D или её result',mustexist=True,initialdir=str(MODEL_ROOT.resolve()if MODEL_ROOT.exists()else Path.cwd()),parent=root)
  if not model:return
  adapter=filedialog.askdirectory(title='Выберите папку Series107 или её result',mustexist=True,initialdir=str(ADAPTER_ROOT.resolve()if ADAPTER_ROOT.exists()else Path.cwd()),parent=root)
  if not adapter:return
  d=filedialog.askdirectory(title='Выберите result89D',mustexist=True,initialdir=str(D_ROOT.resolve()if D_ROOT.exists()else Path.cwd()),parent=root)
  if not d:return
  source=filedialog.askdirectory(title='Выберите source84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve()if SOURCE_ROOT.exists()else Path.cwd()),parent=root)
  if not source:return
  button.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(source,d,model,adapter,progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series110','Frontend tournament завершён.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-110.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series110',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--model105d');p.add_argument('--adapter107');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.','.','.',a.output_root,True))
 elif all((a.source84z,a.result89d,a.model105d,a.adapter107)):print(run(a.source84z,a.result89d,a.model105d,a.adapter107,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d+model105d+adapter107.')
if __name__=='__main__':main()
