#!/usr/bin/env python3
"""Series111: operational nuisance router on fresh selection and final cases."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER110=HERE/'110_nuisance_frontend_repair_tournament.py';RUNNER110_SHA='1d15c85d5969d20f82798249f302cd5f0728a3ad74d7d233c2a26c90588316c1'
RESULT110=HERE.parent/'reports'/'nuisance-frontend-repair-110-user-result.json';RESULT110_SHA='e93208643c0c1229fe27d8ffabacd4680bb42153a05bcec89900e1deb97e1fd3'
BASE_SHA='1bbb15cd398f2cba944cabf38cb49abf83b878bf28127674ff94caced5fa69e1';ADAPTER_SHA='4a8f141a4697fc7d3c3c1ad9e9a60eb27a6d93cb5e7403ad4a4b99e413009b57'
ROOT=Path('workspace/runs/ideas/i-observational/operational-nuisance-router');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact');MODEL_ROOT=Path('workspace/runs/ideas/i-observational/action-aware-temporal-tournament');ADAPTER_ROOT=Path('workspace/runs/ideas/i-observational/grooming-temporal-order-repair')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');DOMAINS=('dim','bright','low_contrast','sensor_noise','horizontal_shift','frame_dropout');ROUTES=('temporal_all','spatial_all','frame_all','predicted_reach_spatial','temporal_then_spatial_on_reject','spatial_then_temporal_on_reject');COMPARATORS=('neutral_visual','reversed_visual','zero_input','shuffled_visual')
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
 if file_sha(RESULT110)!=RESULT110_SHA:raise ValueError('Exact genuine Series110 result изменён.')
 r=json.loads(RESULT110.read_text(encoding='utf8'))
 if r.get('status')!='completed'or r.get('protocol',{}).get('script_sha256')!=RUNNER110_SHA or r.get('selected_frontend')is not None or r.get('primary',{}).get('reason')!='no frontend passed selection; final remained untouched':raise ValueError('Series111 требует exact Series110 selection no-go.')
 s110=load_module('series111_source110',RUNNER110,RUNNER110_SHA);deps=s110.authorize();return(s110,*deps,r)
def hashes_in(x):
 out=set()
 if isinstance(x,dict):
  for k,v in x.items():out.add(v)if k=='motion_sha256'and isinstance(v,str)else out.update(hashes_in(v))
 elif isinstance(x,list):
  for v in x:out.update(hashes_in(v))
 return out
def specs(m86):
 out=[]
 for role,start,seed0 in(('selection',1414,111100),('final',1432,111400)):
  for di,d in enumerate(DOMAINS):
   for ai,a in enumerate(ACTIONS):
    ident=start+di*3+ai;seed=seed0+di*10+ai;amp=(.59,.67,.76,.88,.97,1.03)[di];speed=(.57,.75,.93,1.11,1.29,1.37)[(di+ai)%6];out.append({'role':role,'id':ident,'domain':d,'action':a,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(a,seed,amp,speed)})
 return out
def prepare(s110,s109,s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r110,r109,r108,r107,r106,r105d,r105c,r105):
 s101,models,_,_,guards=s110.prepare(s109,s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r109,r108,r107,r106,r105d,r105c,r105);m86=models['m'].load88().load87().load86();seen=hashes_in(r110)|hashes_in(r109)|hashes_in(r108)|hashes_in(r107)|hashes_in(r106)|hashes_in(r105d)|hashes_in(r105c)|hashes_in(r105)
 with sqlite3.connect(Path(source,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)as db:seen|={z[0]for z in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items=[];desc=[]
 for x in specs(m86):
  h=s105.motion_hash(x['angles_deg'])
  if h in seen:raise ValueError('Series111 motion пересекается с прежними outcomes.')
  q={**x,'motion_sha256':h};items.append(q);desc.append({k:v for k,v in q.items()if k!='angles_deg'});seen.add(h)
 return s101,models,items,desc,guards
def route_rows(route,evaluated):
 out=[]
 for i,t in enumerate(evaluated['percentile_temporal']):
  s=evaluated['percentile_spatial'][i];f=evaluated['frame_percentile'][i]
  if route=='temporal_all':r=t
  elif route=='spatial_all':r=s
  elif route=='frame_all':r=f
  elif route=='predicted_reach_spatial':r=s if t['predicted_action']=='reach_withdraw'else t
  elif route=='temporal_then_spatial_on_reject':r=s if not t['validity_accepted']['candidate']else t
  else:r=t if not s['validity_accepted']['candidate']else s
  out.append(r)
 return out
def metrics(rows,fixture=False):
 n=len(rows);required=n if fixture else 12;per_action=6 if fixture else 4;per_domain=3 if fixture else 2;accept=n if fixture else 15;wins={c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows)for c in COMPARATORS};by_a={a:{c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['action']==a)for c in COMPARATORS}for a in ACTIONS};by_d={d:{c:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][c]['truth_rmse_rad']for r in rows if r['domain']==d)for c in COMPARATORS}for d in DOMAINS};kept=sum(r['validity_accepted']['candidate']for r in rows);rejected=sum(not(r['validity_accepted']['shuffled_visual'])for r in rows);correct=sum(r['predicted_action']==r['action']for r in rows);kept_a={a:sum(r['validity_accepted']['candidate']for r in rows if r['action']==a)for a in ACTIONS};reject_a={a:sum(not(r['validity_accepted']['shuffled_visual'])for r in rows if r['action']==a)for a in ACTIONS};correct_a={a:sum(r['predicted_action']==a for r in rows if r['action']==a)for a in ACTIONS};kept_d={d:sum(r['validity_accepted']['candidate']for r in rows if r['domain']==d)for d in DOMAINS};reject_d={d:sum(not(r['validity_accepted']['shuffled_visual'])for r in rows if r['domain']==d)for d in DOMAINS};gain=sum(r['controls']['shuffled_visual']['truth_rmse_rad']>r['controls']['base_shuffled_ablation']['truth_rmse_rad']for r in rows);means={c:float(np.mean([r['controls'][c]['truth_rmse_rad']for r in rows]))for c in ('candidate',*COMPARATORS,'base_shuffled_ablation')};distinct=all(r['controls']['candidate']['target_sha256']!=r['controls'][c]['target_sha256']for r in rows for c in COMPARATORS);passed=kept>=accept and rejected>=accept and correct>=accept and all(kept_a[a]>=per_action and reject_a[a]>=per_action and correct_a[a]>=per_action for a in ACTIONS)and all(kept_d[d]>=per_domain and reject_d[d]>=per_domain for d in DOMAINS)and all(wins[c]>=required for c in COMPARATORS)and all(by_a[a][c]>=per_action for a in ACTIONS for c in COMPARATORS)and all(by_d[d][c]>=per_domain for d in DOMAINS for c in COMPARATORS)and distinct;return{'cases':n,'required_overall':required,'required_per_action':per_action,'required_per_domain':per_domain,'candidate_kept':kept,'shuffled_rejected':rejected,'action_correct':correct,'candidate_kept_by_action':kept_a,'shuffled_rejected_by_action':reject_a,'action_correct_by_class':correct_a,'candidate_kept_by_domain':kept_d,'shuffled_rejected_by_domain':reject_d,'truth_wins':wins,'truth_wins_by_action':by_a,'truth_wins_by_domain':by_d,'adapter_gain_diagnostic':gain,'mean_truth_rmse_rad':means,'targets_distinct':distinct,'passed':passed}
def choose(selection):
 ok=[(n,v)for n,v in selection.items()if v['metrics']['passed']];return None if not ok else min(ok,key=lambda z:(z[1]['metrics']['mean_truth_rmse_rad']['candidate'],z[0]))[0]
def fixture(temp,progress):
 selection={n:{'metrics':{'passed':n=='predicted_reach_spatial','mean_truth_rmse_rad':{'candidate':.06}}}for n in ROUTES};selected=choose(selection);rows=[]
 for di,d in enumerate(DOMAINS):
  for ai,a in enumerate(ACTIONS):
   controls={c:{'truth_rmse_rad':.06 if c=='candidate'else(.13 if c=='base_shuffled_ablation'else.2),'target_sha256':c+str(di)+str(ai)}for c in('candidate',*COMPARATORS,'base_shuffled_ablation')};rows.append({'id':1432+di*3+ai,'domain':d,'action':a,'predicted_action':a,'validity_accepted':{'candidate':True,'shuffled_visual':False},'controls':controls})
 primary={**metrics(rows,True),'development_candidate':True,'scientific_result':False};np.savez_compressed(temp/'selected_operational_router.npz',route=np.array(selected));progress('Fixture готова',.98,1,1);return selection,selected,rows,primary,'fixture-router'
def run(source,d_folder,model_folder,adapter_folder,output_root=ROOT,fixture_mode=False,progress=lambda*x:None):
 s110,s109,s108,s107,s106,s105d,s105c,s105,s104,s102,s103,r105d,r105c,r105,r106,r107,r108,r109,r110=authorize();model_path,model=s106.load_selected(model_folder)if not fixture_mode else(Path(__file__),None);adapter_path,det=s108.load_adapter(adapter_folder)if not fixture_mode else(Path(__file__),None);root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('operational_nuisance_router_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();data=folder/'checkpoint_data';data.mkdir();progress('Проверяются exact artifacts',.01,0,1)
 if fixture_mode:protocol={'mode':'fixture'};save(folder/'protocol.json',protocol);selection,selected,final_rows,primary,router_sha=fixture(temp,progress)
 else:
  s101,base,items,desc,guards=prepare(s110,s109,s108,s107,s106,s105d,s105c,s105,s104,s102,source,d_folder,r110,r109,r108,r107,r106,r105d,r105c,r105);protocol={'schema':'operational-nuisance-router-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner110_sha256':RUNNER110_SHA,'series110_result_sha256':RESULT110_SHA,'base_model_sha256':BASE_SHA,'adapter_sha256':ADAPTER_SHA,'routes':list(ROUTES),'motions':desc,'primary_rule':'validity/action>=15, >=4/action, >=2/domain; wins>=12, >=4/action, >=2/domain; distinct; adapter gain reported not gated','reason_gain_not_gate':'safe abstention is judged by validity rejection and specificity; it need not intentionally maximize error relative to an already-poor base shuffled target','post_result_tuning':False};save(folder/'protocol.json',protocol);s101.worker_init(base['bundle'],base['s84v']);bridge=s103.Bridge()
  try:
   n=len(np.asarray(items[0]['angles_deg']));raw,_=s104.capture(s103,bridge,np.zeros((n,6)),progress,.01,.02,'Neutral operational router source');neutral={}
   for name in s110.NORMALIZERS:
    f=s110.feature_pack(s109,s107,s105d,base,s110.normalize(raw,name),111999999);neutral.update({name+'_'+k:v for k,v in f.items()})
   sels=[x for x in items if x['role']=='selection']
   for i,item in enumerate(sels):s110.atomic_npz(data/f"{item['id']}.npz",s110.capture_data(s109,s107,s105d,s104,s103,base,bridge,item,progress,.03+.65*(i+1)/len(sels)))
   sel=s110.load_cases(data,items,'selection');ev={n:s110.evaluate(s107,s105d,base,model,det,sel,neutral,n)for n in('percentile_temporal','percentile_spatial','frame_percentile')};selection={}
   for route in ROUTES:
    rows=route_rows(route,ev);selection[route]={'metrics':metrics(rows),'rows':rows}
   selected=choose(selection)
   if selected is None:final_rows=[];primary={'final_cases':0,'passed':False,'development_candidate':False,'scientific_result':False,'reason':'no operational router passed selection; final remained untouched'};router_sha=None
   else:
    finals=[x for x in items if x['role']=='final']
    for i,item in enumerate(finals):s110.atomic_npz(data/f"{item['id']}.npz",s110.capture_data(s109,s107,s105d,s104,s103,base,bridge,item,progress,.70+.27*(i+1)/len(finals)))
    final=s110.load_cases(data,items,'final');ev={n:s110.evaluate(s107,s105d,base,model,det,final,neutral,n)for n in('percentile_temporal','percentile_spatial','frame_percentile')};final_rows=route_rows(selected,ev);fm=metrics(final_rows);primary={**fm,'development_candidate':fm['passed'],'scientific_result':False};artifact=temp/'selected_operational_router.npz';np.savez_compressed(artifact,route=np.array(selected),runner_sha256=np.array(file_sha(__file__)));router_sha=file_sha(artifact)
   before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p)for p in before}or frozen_before!=s104.manifest(frozen_path)or file_sha(model_path)!=BASE_SHA or file_sha(adapter_path)!=ADAPTER_SHA:raise ValueError('Frozen sources/artifacts изменились.')
  finally:bridge.close()
 report={'schema':'operational-nuisance-router-result-v1','status':'fixture_completed'if fixture_mode else'completed','protocol':protocol,'series110_primary':r110['primary'],'selection':selection,'selected_router':selected,'selected_router_sha256':router_sha,'primary':primary,'final':final_rows,'limitations':['Operational gate differs prospectively from Series110: adapter RMSE gain is diagnostic, not a requirement to make invalid targets harmful.','Supervised route selection on generated nuisance cases; Series109/110 remain no-go.','Digital nuisance development, not hardware or biological transfer.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('SERIES111: OPERATIONAL NUISANCE ROUTER\n\nSelected: '+str(selected)+'\nGate: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series111: operational nuisance router');root.geometry('880x510+80+40');root.attributes('-topmost',True);status=tk.StringVar(value='Выберите exact artifacts и sources');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series111: operational nuisance router',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='Temporal/spatial/frame frontends и deterministic routes;18 selection + conditional final18.\nSafe rejection оценивается validity+specificity, а не намеренным ухудшением trajectory.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=690,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать base105D, adapter107, result89D, source84Z и запустить',padx=18,pady=9);button.pack(pady=14)
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
     messagebox.showinfo('Series111','Router tournament завершён.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-111.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series111',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--model105d');p.add_argument('--adapter107');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.','.','.',a.output_root,True))
 elif all((a.source84z,a.result89d,a.model105d,a.adapter107)):print(run(a.source84z,a.result89d,a.model105d,a.adapter107,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d+model105d+adapter107.')
if __name__=='__main__':main()
