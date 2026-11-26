#!/usr/bin/env python3
"""Series112: frozen physical validation of the Series111 operational router."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER111=HERE/'111_operational_nuisance_router.py';RUNNER111_SHA='f6f3e3efa6f11e7ada0a1fca66187ad3c971a39fa08c6d36b0daf474df858fef'
RESULT111=HERE.parent/'reports'/'operational-nuisance-router-111-user-result.json';RESULT111_SHA='9ecc0f2b4568ee2a0f5bcdeca552c28caa3e295b52c98993fdf8a04593146765'
BASE_SHA='1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1';ADAPTER_SHA='4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57';ROUTER='spatial_then_temporal_on_reject';ROUTER_ARTIFACT_SHA='2810ecddc8cbc24e7cbcf4ac2c614a3971327236c0ba9c6bc008bccbd5bc9282'
ROOT=Path('workspace/runs/ideas/i-observational/frozen-operational-router-physical');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact');MODEL_ROOT=Path('workspace/runs/ideas/i-observational/action-aware-temporal-tournament');ADAPTER_ROOT=Path('workspace/runs/ideas/i-observational/grooming-temporal-order-repair')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');DOMAINS=('dim','bright','low_contrast','sensor_noise','horizontal_shift','frame_dropout');CONDITIONS=('candidate','neutral_visual','reversed_visual','shuffled_visual','zero_input','base_shuffled_ablation','open_loop');COMPARATORS=('neutral_visual','reversed_visual','shuffled_visual','zero_input')
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
 if file_sha(RESULT111)!=RESULT111_SHA:raise ValueError('Exact genuine Series111 result изменён.')
 r=json.loads(RESULT111.read_text(encoding='utf8'));p=r.get('primary',{})
 if r.get('status')!='completed'or r.get('protocol',{}).get('script_sha256')!=RUNNER111_SHA or r.get('selected_router')!=ROUTER or r.get('selected_router_sha256')!=ROUTER_ARTIFACT_SHA or p.get('passed')is not True or p.get('development_candidate')is not True or p.get('scientific_result')is not False or len(r.get('final',[]))!=18:raise ValueError('Series112 требует exact successful Series111 result.')
 s111=load_module('series112_source111',RUNNER111,RUNNER111_SHA);deps=s111.authorize();return(s111,*deps,r)
def hashes_in(x):
 out=set()
 if isinstance(x,dict):
  for k,v in x.items():out.add(v)if k=='motion_sha256'and isinstance(v,str)else out.update(hashes_in(v))
 elif isinstance(x,list):
  for v in x:out.update(hashes_in(v))
 return out
def specs(m86):
 out=[]
 for di,d in enumerate(DOMAINS):
  for ai,a in enumerate(ACTIONS):
   ident=1450+di*3+ai;seed=112100+di*10+ai;amp=(.61,.70,.79,.89,.98,1.04)[di];speed=(.60,.78,.96,1.14,1.30,1.38)[(di+2*ai)%6];out.append({'role':'physical_final','id':ident,'domain':d,'action':a,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(a,seed,amp,speed)})
 return out
def prepare(s111,s110,s109,s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r111,r110,r109,r108,r107,r106,r105d,r105c,r105):
 s101,base,_,_,guards=s111.prepare(s110,s109,s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r110,r109,r108,r107,r106,r105d,r105c,r105);m86=base['m'].load88().load87().load86();seen=hashes_in(r111)|hashes_in(r110)|hashes_in(r109)|hashes_in(r108)|hashes_in(r107)|hashes_in(r106)|hashes_in(r105d)|hashes_in(r105c)|hashes_in(r105)
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)as db:seen|={z[0]for z in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items=[];desc=[]
 for x in specs(m86):
  h=s105.motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series112 motion пересекается с прежними outcomes.')
  q={**x,'motion_sha256':h};items.append(q);desc.append({k:v for k,v in q.items()if k!='angles_deg'});seen.add(h)
 return s101,base,items,desc,guards
def make_targets(s110,s107,s105d,base,model,det,pack,neutral,n):
 def one(name):
  p=pack[name];temp=p['temp'];_,logits=s105d.predict(model,temp);ai=int(np.argmax(logits));targets={};accepted={}
  for c,t,d in(('candidate',temp,p['diag']),('neutral_visual',neutral[name]['temp'],neutral[name]['diag']),('reversed_visual',p['rev_temp'],p['rev_diag']),('shuffled_visual',p['sh_temp'],p['sh_diag'])):targets[c],accepted[c]=s110.target(s107,s105d,base,model,det,t,d,ai,n)
  zero,_=s105d.predict(model,np.zeros_like(temp));targets['zero_input']=s105d.decode(base,zero,n);bcoeff,_=s105d.predict(model,p['sh_temp']);targets['base_shuffled_ablation']=s105d.decode(base,bcoeff,n);targets['open_loop']=targets['candidate'];return targets,accepted,logits
 spatial=one('percentile_spatial')
 if spatial[1]['candidate']:return(*spatial,'percentile_spatial')
 temporal=one('percentile_temporal');return(*temporal,'percentile_temporal')
def capture_case(s110,s109,s107,s105d,s104,s103,base,bridge,item,neutral,model,det,progress,fraction):
 cmd=np.asarray(item['angles_deg'],float)*np.pi/180;raw,actual=s104.capture(s103,bridge,cmd,progress,max(.02,fraction-.006),.006,f'Frozen router physical capture {item["id"]}');truth=np.asarray(actual[2:],float);nuis=s109.perturb(raw,item['domain'],112000000+item['id']);pack={}
 for name in('percentile_spatial','percentile_temporal'):pack[name]=s110.feature_pack(s109,s107,s105d,base,s110.normalize(nuis,name),item['id'])
 targets,accepted,logits,chosen=make_targets(s110,s107,s105d,base,model,det,pack,neutral,len(truth));return truth,targets,accepted,logits,chosen
def safe(x):return x['finite']and x['minimum_thorax_z_mm']>=.15 and x['maximum_thorax_z_mm']<=2.5 and x['contact_frame_fraction']>0
def decide(rows,fixture=False):
 n=len(rows);overall=n if fixture else 12;per_action=6 if fixture else 4;per_domain=3 if fixture else 2;accept=n if fixture else 15;open_req=n if fixture else 15;cand=[r['controls']['candidate']for r in rows];wins={c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows)for c in COMPARATORS};by_a={a:{c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['action']==a)for c in COMPARATORS}for a in ACTIONS};by_d={d:{c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['domain']==d)for c in COMPARATORS}for d in DOMAINS};kept=sum(r['validity_accepted']['candidate']for r in rows);rejected=sum(not r['validity_accepted']['shuffled_visual']for r in rows);correct=sum(r['predicted_action']==r['action']for r in rows);kept_a={a:sum(r['validity_accepted']['candidate']for r in rows if r['action']==a)for a in ACTIONS};reject_a={a:sum(not r['validity_accepted']['shuffled_visual']for r in rows if r['action']==a)for a in ACTIONS};correct_a={a:sum(r['predicted_action']==a for r in rows if r['action']==a)for a in ACTIONS};kept_d={d:sum(r['validity_accepted']['candidate']for r in rows if r['domain']==d)for d in DOMAINS};reject_d={d:sum(not r['validity_accepted']['shuffled_visual']for r in rows if r['domain']==d)for d in DOMAINS};open_wins=sum(r['controls']['candidate']['truth_rmse_rad']<r['controls']['open_loop']['truth_rmse_rad']for r in rows);gain=sum(r['controls']['shuffled_visual']['truth_rmse_rad']>r['controls']['base_shuffled_ablation']['truth_rmse_rad']for r in rows);tracking=float(np.mean([x['tracking_rmse_rad']for x in cand]));means={c:float(np.mean([r['controls'][c]['truth_rmse_rad']for r in rows]))for c in CONDITIONS};distinct=all(r['target_hashes']['candidate']!=r['target_hashes'][c]for r in rows for c in COMPARATORS);passed=sum(safe(x)for x in cand)==n and tracking<=.20 and kept>=accept and rejected>=accept and correct>=accept and all(kept_a[a]>=per_action and reject_a[a]>=per_action and correct_a[a]>=per_action for a in ACTIONS)and all(kept_d[d]>=per_domain and reject_d[d]>=per_domain for d in DOMAINS)and all(wins[c]>=overall for c in COMPARATORS)and all(by_a[a][c]>=per_action for a in ACTIONS for c in COMPARATORS)and all(by_d[d][c]>=per_domain for d in DOMAINS for c in COMPARATORS)and open_wins>=open_req and distinct;return{'cases':n,'required_overall':overall,'required_per_action':per_action,'required_per_domain':per_domain,'candidate_safe_cases':sum(safe(x)for x in cand),'candidate_mean_tracking_rmse_rad':tracking,'candidate_validity_kept':kept,'shuffled_validity_rejected':rejected,'action_correct':correct,'candidate_kept_by_action':kept_a,'shuffled_rejected_by_action':reject_a,'action_correct_by_class':correct_a,'candidate_kept_by_domain':kept_d,'shuffled_rejected_by_domain':reject_d,'candidate_truth_wins':wins,'candidate_truth_wins_by_action':by_a,'candidate_truth_wins_by_domain':by_d,'open_loop_wins':open_wins,'adapter_gain_diagnostic':gain,'mean_truth_rmse_rad':means,'targets_distinct':distinct,'passed':passed,'physical_development_candidate':passed,'scientific_result':False}
def fixture_rows():
 rows=[]
 for di,d in enumerate(DOMAINS):
  for ai,a in enumerate(ACTIONS):
   controls={c:{'finite':True,'tracking_rmse_rad':.05,'truth_rmse_rad':.06 if c=='candidate'else(.13 if c=='base_shuffled_ablation'else.21),'contact_frame_fraction':1.,'mean_contact_legs':4.,'max_actuator_force_norm':8.,'minimum_thorax_z_mm':.8,'maximum_thorax_z_mm':1.2,'energy_abs_work':1.,'torque_saturation_fraction':0.}for c in CONDITIONS};rows.append({'id':1450+di*3+ai,'domain':d,'action':a,'predicted_action':a,'chosen_frontend':'percentile_spatial','validity_accepted':{'candidate':True,'neutral_visual':True,'reversed_visual':True,'shuffled_visual':False},'target_hashes':{c:c+str(di)+str(ai)for c in CONDITIONS},'controls':controls})
 return rows
def run(source,d_folder,model_folder,adapter_folder,output_root=ROOT,fixture=False,progress=lambda*x:None):
 s111,s110,s109,s108,s107,s106,s105d,s105c,s105,s104,s102,s103,r105d,r105c,r105,r106,r107,r108,r109,r110,r111=authorize();model_path,model=s106.load_selected(model_folder)if not fixture else(Path(__file__),None);adapter_path,det=s108.load_adapter(adapter_folder)if not fixture else(Path(__file__),None);root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('frozen_operational_router_physical_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();progress('Проверяются exact artifacts',.01,0,1)
 if fixture:desc=[];rows=fixture_rows();trace=[];primary=decide(rows,True)
 else:
  s101,base,items,desc,guards=prepare(s111,s110,s109,s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r111,r110,r109,r108,r107,r106,r105d,r105c,r105);s101.worker_init(base['bundle'],base['s84v']);bridge=s103.Bridge();rows=[];trace=[]
  try:
   n=len(np.asarray(items[0]['angles_deg']));raw_neutral,_=s104.capture(s103,bridge,np.zeros((n,6)),progress,.01,.02,'Neutral frozen router source');neutral={}
   for name in('percentile_spatial','percentile_temporal'):
    f=s110.feature_pack(s109,s107,s105d,base,s110.normalize(raw_neutral,name),112999999);neutral[name]=f
   total=len(items)*len(CONDITIONS);done=0
   for i,item in enumerate(items):
    domain_neutral={}
    for name in('percentile_spatial','percentile_temporal'):domain_neutral[name]=s110.feature_pack(s109,s107,s105d,base,s110.normalize(s109.perturb(raw_neutral,item['domain'],112900000+item['id']),name),112900000+item['id'])
    truth,targets,accepted,logits,chosen=capture_case(s110,s109,s107,s105d,s104,s103,base,bridge,item,domain_neutral,model,det,progress,.03+.25*(i+1)/len(items));controls={}
    for c in CONDITIONS:
     metric=s104.rollout(s103,bridge,targets[c],truth,c=='open_loop');sample=metric.pop('sample');controls[c]=metric
     for fi,angles in enumerate(sample):trace.append({'id':item['id'],'domain':item['domain'],'action':item['action'],'chosen_frontend':chosen,'condition':c,'frame':fi,**{s103.MAPPED_DOF[j]:float(angles[j])for j in range(6)}})
     done+=1;progress('Frozen router physical controls',.28+.68*done/total,done,total)
    rows.append({'id':item['id'],'domain':item['domain'],'action':item['action'],'predicted_action':ACTIONS[int(np.argmax(logits))],'chosen_frontend':chosen,'validity_accepted':accepted,'target_hashes':{c:sha_bytes(np.asarray(v,dtype='<f8').tobytes())for c,v in targets.items()},'controls':controls})
   before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p)for p in before}or frozen_before!=s104.manifest(frozen_path)or file_sha(model_path)!=BASE_SHA or file_sha(adapter_path)!=ADAPTER_SHA:raise ValueError('Frozen sources/artifacts изменились.')
   primary=decide(rows,False)
  finally:bridge.close()
 protocol={'schema':'frozen-operational-router-physical-v1','mode':'fixture'if fixture else'full','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner111_sha256':RUNNER111_SHA,'series111_result_sha256':RESULT111_SHA,'selected_router':ROUTER,'selected_router_artifact_sha256':ROUTER_ARTIFACT_SHA,'base_model_sha256':BASE_SHA,'adapter_sha256':ADAPTER_SHA,'training_allowed':False,'selection_allowed':False,'post_result_tuning':False,'domains':list(DOMAINS),'motions':desc,'conditions':list(CONDITIONS),'primary_rule':'all safe/tracking<=.20; validity/action>=15,>=4/action,>=2/domain; wins>=12,>=4/action,>=2/domain; open-loop>=15; distinct; adapter gain diagnostic'};save(folder/'protocol.json',protocol);report={'schema':'frozen-operational-router-physical-result-v1','status':'fixture_completed'if fixture else'completed','protocol':protocol,'series111_primary':r111['primary'],'primary':primary,'tests':rows,'limitations':['Exact Series111 spatial-then-temporal-on-reject route; no Series112 training or selection.','Visual nuisances remain deterministic digital post-capture perturbations; physical body is simulated.','Supervised generated-action engineering validation, not biological learning, living-fly or hardware-camera transfer.']};save(temp/'summary.json',report)
 if trace:
  with(temp/'physical_trace.csv').open('w',newline='',encoding='utf8')as f:w=csv.DictWriter(f,fieldnames=list(trace[0]));w.writeheader();w.writerows(trace)
 (temp/'ИТОГ.txt').write_text('SERIES112: FROZEN OPERATIONAL ROUTER PHYSICAL VALIDATION\n\nPrimary: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\nEngineering physical validation, not biological result.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series112: frozen operational router physical validation');root.geometry('900x520+70+35');root.attributes('-topmost',True);status=tk.StringVar(value='Выберите exact artifacts и frozen sources');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series112: frozen physical test operational router',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='6 nuisance domains ×3 actions ×7 physical conditions =126 rollouts.\nExact Series111 route; no training, selection or threshold tuning.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=700,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать base105D, adapter107, result89D, source84Z и запустить',padx=18,pady=9);button.pack(pady=14)
 def update(text,fraction,done,total):
  def apply():
   p=round(100*fraction,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.02:e=time.time()-start[0];eta.set(f'Прошло {e/60:.1f} мин · осталось примерно {e*(1-fraction)/fraction/60:.1f} мин')
  root.after(0,apply)
 def begin():
  model=filedialog.askdirectory(title='Выберите Series105D или result',mustexist=True,initialdir=str(MODEL_ROOT.resolve()if MODEL_ROOT.exists()else Path.cwd()),parent=root)
  if not model:return
  adapter=filedialog.askdirectory(title='Выберите Series107 или result',mustexist=True,initialdir=str(ADAPTER_ROOT.resolve()if ADAPTER_ROOT.exists()else Path.cwd()),parent=root)
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
     messagebox.showinfo('Series112','Physical validation завершён.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-112.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series112',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--model105d');p.add_argument('--adapter107');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.','.','.',a.output_root,True))
 elif all((a.source84z,a.result89d,a.model105d,a.adapter107)):print(run(a.source84z,a.result89d,a.model105d,a.adapter107,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d+model105d+adapter107.')
if __name__=='__main__':main()
