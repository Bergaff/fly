#!/usr/bin/env python3
"""Series129A-D: low-load historical FlyGym audit + small shared Ollama battery.

This is the finite final package. It does not reopen blocked Series127/128 and does not
claim a new physical controller run, biological validation, or general intelligence.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,re,threading,time,traceback,urllib.request,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;REPORTS=HERE.parent/'reports';ROOT=Path('workspace/runs/ideas/i-observational/hour-flygym-ai-final-129');OLLAMA='http://127.0.0.1:11434';MODEL='qwen2.5:7b'
GRAPH=REPORTS/'biological-digital-pipeline-116a-61x61.csv';PATHS=REPORTS/'biological-digital-pipeline-116b-61x8.csv'
PINS={'graph':'03157b503d0271cb0991db524d45220bb8f49ce62e3ba171dc997ed7f3816150','paths':'4186bb6fdbe0a0e81f8626469027976ade1d416ff0549af94b85fb1b07aa3ca1','106':'1eadcbcfea31c973f9993da16be7cd0b01998d2f4c6c7aa27c54b4c08da00be9','109':'e7cfc5068fb53ae69782d3d31ce03e16605c044699a3a41590193a5276c99f03','112':'da0b244c4d1dba53e81ebc95a6a1496b2517d2e3da5969be305a75af5a5c3b01','121':'0f16b0ac2775df05059b64e7c608784af486592ec78e1e00286d72e026d0a41f','125':'2101304b029fa4228ac53ab83cdf2781fc65efebbdd432b560f46f9aa8a5c94d','126':'c57c6f636b5987628ea1983246344ee8bd77bbd4f37231f5d60880c56432aaf5'}
FILES={'106':REPORTS/'frozen-action-aware-physical-validation-106-user-result.json','109':REPORTS/'frozen-nuisance-robustness-ablation-109-user-result.json','112':REPORTS/'frozen-operational-router-physical-112-user-result.json','121':REPORTS/'local-ollama-narrow-benchmark-121-qwen2.5-7b-user-result-60.json','125':REPORTS/'multihop-structural-specificity-125-user-result.json','126':REPORTS/'independent-physical-outcome-development-126-user-result.json'}
FAMILIES=('dn_routing','multihop_readout','lesion_counterfactual','physical_control_audit');VARIANTS=('json_direct','compact_table','verify_then_json')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def request(path,payload=None,timeout=600):
 data=None if payload is None else json.dumps(payload).encode();q=urllib.request.Request(OLLAMA+path,data=data,headers={'Content-Type':'application/json'});return json.loads(urllib.request.urlopen(q,timeout=timeout).read().decode())
def parse(text):
 try:
  x=json.loads(text);return str(x.get('answer','')).strip() if isinstance(x,dict) else ''
 except Exception:
  m=re.search(r'"answer"\s*:\s*"([^"]+)"',text);return m.group(1).strip() if m else ''
def load_inputs():
 for k,p in [('graph',GRAPH),('paths',PATHS),*FILES.items()]:
  if sha(p)!=PINS[k]:raise ValueError(f'Frozen input SHA mismatch: {k}')
 def matrix(p):
  rows=list(csv.reader(Path(p).open(encoding='utf8')));return [r[0] for r in rows[1:]],[*rows[0][1:]],np.asarray([[float(v) for v in r[1:]]for r in rows[1:]])
 types,_,g=matrix(GRAPH);ptypes,dns,p=matrix(PATHS);assert types==ptypes;g=np.log1p(g);g/=np.maximum(g.sum(1,keepdims=True),1e-15);p/=np.maximum(p.sum(1,keepdims=True),1e-15);return types,dns,g,p,{k:json.loads(v.read_text(encoding='utf8')) for k,v in FILES.items()}
def physical_audit(data):
 rows=[]
 for series in ('106','109','112'):
  key='repaired_candidate' if series=='109' else 'candidate'
  for x in data[series]['tests']:
   c=x['controls'][key];rows.append({'series':int(series),'action':x['action'],'domain':x.get('domain','standard'),'tracking_rmse_rad':c['tracking_rmse_rad'],'truth_rmse_rad':c['truth_rmse_rad'],'contact_frame_fraction':c['contact_frame_fraction'],'max_actuator_force_norm':c['max_actuator_force_norm'],'energy_abs_work':c['energy_abs_work']})
 arr=np.asarray([[r[k]for k in ('tracking_rmse_rad','truth_rmse_rad','contact_frame_fraction','max_actuator_force_norm','energy_abs_work')]for r in rows]);rng=np.random.default_rng(129000001);boots=np.asarray([arr[rng.integers(0,len(arr),len(arr))].mean(0)for _ in range(10000)]);names=('tracking_rmse_rad','truth_rmse_rad','contact_frame_fraction','max_actuator_force_norm','energy_abs_work')
 return {'mode':'immutable_historical_official_flygym_audit','new_physical_run':False,'cases':len(rows),'series':[106,109,112],'means':dict(zip(names,arr.mean(0).tolist())),'bootstrap_95':{k:[float(np.quantile(boots[:,i],.025)),float(np.quantile(boots[:,i],.975))]for i,k in enumerate(names)},'rows':rows}
def make_case(family,index,types,dns,g,p,data):
 rng=np.random.default_rng(129100000+FAMILIES.index(family)*100000+index);variant=VARIANTS[index%len(VARIANTS)]
 if family=='dn_routing':
  ids=rng.choice(61,4,replace=False);w=rng.uniform(.1,1,8);items={types[i]:np.round(p[i],5).tolist()for i in ids};answer=types[ids[int(np.argmax(p[ids]@w))]];payload={'weights':np.round(w,5).tolist(),'candidates':items};rule='Choose the candidate whose vector has the largest dot product with weights.'
 elif family=='multihop_readout':
  stim=np.zeros(61);ids=rng.choice(61,5,replace=False);stim[ids]=rng.uniform(.2,1,5);stim/=stim.sum();z=stim.copy();total=stim.copy()
  for h in range(1,5):z=z@g;total+=.65**h*z
  scores=total@p;pick=rng.choice(8,4,replace=False);payload={'channels':{dns[i]:round(float(scores[i]),7)for i in pick}};answer=dns[pick[int(np.argmax(scores[pick]))]];rule='Choose the channel with the largest score.'
 elif family=='lesion_counterfactual':
  base=rng.uniform(0,1,8);items={f'L{i+1}':np.round(base+rng.normal(0,.15,8),5).tolist()for i in range(4)};answer=max(items,key=lambda k:float(np.linalg.norm(np.asarray(items[k])-base)));payload={'baseline':np.round(base,5).tolist(),'lesions':items};rule='Choose the lesion with the largest Euclidean distance from baseline.'
 else:
  series=('106','109','112')[index%3];test=data[series]['tests'][index%len(data[series]['tests'])];keys=['candidate' if series!='109' else'repaired_candidate','neutral_visual','reversed_visual','zero_input'];items={k:{'truth_rmse':round(float(test['controls'][k]['truth_rmse_rad']),7),'contact':round(float(test['controls'][k]['contact_frame_fraction']),7)}for k in keys};valid=[k for k,v in items.items()if v['contact']>0];answer=min(valid,key=lambda k:items[k]['truth_rmse']);payload={'official_flygym_historical_controls':items};rule='Among controls with contact above zero, choose the smallest truth_rmse.'
 if variant=='compact_table':body='; '.join(f'{k}={v}'for k,v in payload.items())
 else:body=json.dumps(payload,separators=(',',':'))
 lead='Check the arithmetic before answering. ' if variant=='verify_then_json' else ''
 prompt=lead+rule+' Reply only JSON {"answer":"exact label"}. Data: '+body
 return {'family':family,'index':index,'variant':variant,'expected':answer,'prompt':prompt,'payload_sha256':hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()}
def summarize(rows,elapsed,max_cases,cooldown,model_meta,physical,fixture):
 families={}
 for f in FAMILIES:
  z=[r for r in rows if r['family']==f];families[f]={'cases':len(z),'correct':sum(r['correct']for r in z),'accuracy':sum(r['correct']for r in z)/len(z) if z else None,'mean_wall_seconds':float(np.mean([r['wall_seconds']for r in z]))if z else None,'by_prompt_variant':{v:{'cases':sum(r['variant']==v for r in z),'correct':sum(r['correct']and r['variant']==v for r in z)}for v in VARIANTS}}
 return {'schema':'light-flygym-ai-final-129-v2','status':'fixture_completed'if fixture else'completed','contract':{'maximum_ai_cases':max_cases,'cooldown_seconds':cooldown,'adaptive_case_count':False,'model_required':MODEL,'families':list(FAMILIES),'prompt_variants':list(VARIANTS),'temperature':0,'shared_exact_cases':True,'manual_confirmation_required':True,'automatic_ollama_server_start':False,'model_unload_requested_after_run':True,'historical_physical_audit_not_new_run':True,'series127_128_remain_unauthorized':True,'no_post_result_tuning':True},'series129a_physical_evidence_audit':physical,'series129b_shared_ai_benchmark':{'model':model_meta,'total_cases':len(rows),'total_correct':sum(r['correct']for r in rows),'families':families},'series129c_efficiency':{'elapsed_seconds':elapsed,'mean_ollama_wall_seconds':float(np.mean([r['wall_seconds']for r in rows]))if rows else None,'project_exact_accuracy':1.0,'ollama_accuracy':sum(r['correct']for r in rows)/len(rows)if rows else None},'series129d_final_decisions':{'fly_digital_engineering':'NO_GO_EXTERNAL_BEHAVIOR_ADVANTAGE','cross_animal_transfer':'ALGORITHM_EXISTS_VALIDATED_OTHER_SPECIES_0','ai_comparison':'NARROW_SHARED_TASKS_ONLY_NOT_GENERAL_INTELLIGENCE','biological_mirror_neurons':'NOT_ESTABLISHED','series130_same_synthetic_seed_authorized':False},'input_shas':PINS,'limitations':['AI tasks test exact narrow numeric decisions, not organism-level intelligence.','Physical section audits historical official FlyGym outcomes; no new Graph controller execution.','Series126 NO-GO is preserved; this package cannot reverse it.']}
def unload_model():
 try:request('/api/generate',{'model':MODEL,'keep_alive':0},timeout=30);return True
 except Exception:return False
def run(output_root,max_cases=12,cooldown=5,fixture=False,progress=lambda *_:None):
 max_cases=12 if fixture else max(4,min(int(max_cases),12));cooldown=0 if fixture else max(3,float(cooldown));types,dns,g,p,data=load_inputs();physical=physical_audit(data);folder=Path(output_root)/(('fixture_'if fixture else'light_')+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True);jsonl=folder/'case_rows.jsonl';rows=[];counts={f:0 for f in FAMILIES};start=time.monotonic();model_meta={'name':'fixture','fixture':True};unloaded=True
 if not fixture:
  tags=request('/api/tags',timeout=10).get('models',[]);names=[x.get('name')for x in tags]
  if MODEL not in names:raise RuntimeError(f'Требуется установленная Ollama model {MODEL}. Найдены: {names}')
  tag=next(x for x in tags if x.get('name')==MODEL);model_meta={'name':MODEL,'digest':tag.get('digest'),'size_bytes':tag.get('size')}
 try:
  with jsonl.open('a',encoding='utf8')as out:
   while len(rows)<max_cases:
    f=FAMILIES[len(rows)%len(FAMILIES)];case=make_case(f,counts[f],types,dns,g,p,data);counts[f]+=1;t0=time.monotonic()
    if fixture:raw=json.dumps({'answer':case['expected'] if len(rows)%5 else'fixture_wrong'});response={'response':raw}
    else:response=request('/api/generate',{'model':MODEL,'prompt':case['prompt'],'stream':False,'format':'json','keep_alive':'30s','options':{'temperature':0,'seed':129000001}},timeout=180);raw=response.get('response','')
    answer=parse(raw);row={k:v for k,v in case.items()if k!='prompt'}|{'answer':answer,'correct':answer==case['expected'],'wall_seconds':time.monotonic()-t0,'raw_response':raw};rows.append(row);out.write(json.dumps(row,ensure_ascii=False)+'\n');out.flush();(folder/'progress.json').write_text(json.dumps({'status':'running','cases':len(rows),'maximum_cases':max_cases,'counts':counts,'elapsed_seconds':time.monotonic()-start},indent=2)+'\n',encoding='utf8');progress(len(rows),max_cases,f)
    if not fixture and len(rows)<max_cases:time.sleep(cooldown)
 finally:
  if not fixture:unloaded=unload_model()
 elapsed=time.monotonic()-start;result=summarize(rows,elapsed,max_cases,cooldown,model_meta,physical,fixture);result['series129c_efficiency']['model_unload_request_succeeded']=unloaded;(folder/'progress.json').write_text(json.dumps({'status':'completed','cases':len(rows),'maximum_cases':max_cases,'counts':counts,'elapsed_seconds':elapsed,'model_unloaded':unloaded},indent=2)+'\n',encoding='utf8');(folder/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(folder/'ИТОГ.txt').write_text('\n'.join(['SERIES129A-D — LOW-LOAD FLYGYM + AI BATTERY','',f"Status: {result['status']}",f"Elapsed: {elapsed/60:.1f} min",f"AI cases: {len(rows)} / max {max_cases}",f"Ollama accuracy: {result['series129c_efficiency']['ollama_accuracy']:.4f}",f"Model unload requested: {unloaded}",'','Fly engineering: NO-GO external behavioral advantage','AI comparison: narrow shared tasks only','Biological mirror neurons: not established','Series127/128 remain unauthorized.'])+'\n',encoding='utf-8-sig');progress(len(rows),max_cases,'Готово');return folder
def gui():
 import tkinter as tk
 from tkinter import messagebox,ttk
 root=tk.Tk();root.title('Series129A-D: лёгкий FlyGym + AI финал');root.geometry('820x500+80+45');root.attributes('-topmost',True);status=tk.StringVar(value='Ollama должна быть уже запущена; runner не запускает сервер сам');pct=tk.DoubleVar(value=0);cases=tk.StringVar(value='Cases: 0 / 12');button=tk.Button(root,text='Запустить 12 запросов с паузами',padx=24,pady=12)
 tk.Label(root,text='Series129A-D · безопасный малый FlyGym + Qwen audit',font=('Arial',15,'bold'),pady=16).pack();tk.Label(root,text='A: offline audit48 historical official-FlyGym cases\nB: ровно12 AI cases: 4 families ×3 prompt variants\nC: пауза5 секунд между запросами\nD: финальные решения и stop rules',justify='center').pack();tk.Label(root,text='Важно: Qwen временно загрузится в память и может кратковременно включить вентиляторы.\nАвтозапуска Ollama нет; после12-го ответа runner немедленно запрашивает выгрузку модели.\nЕсли нагрузка нежелательна — нажмите «Нет» в подтверждении и ничего не запустится.',fg='#8b1a1a',justify='center').pack(pady=12);tk.Label(root,textvariable=status).pack();ttk.Progressbar(root,variable=pct,maximum=100,length=620).pack(pady=8);tk.Label(root,textvariable=cases).pack();button.pack(pady=14)
 def start():
  if not messagebox.askyesno('Подтверждение нагрузки','Запустить только12 запросов Qwen2.5:7b с паузами5 секунд?\n\nМодель временно займёт память. После теста будет отправлена команда выгрузки.',parent=root):return
  button.config(state='disabled')
  def upd(done,total,stage):root.after(0,lambda:(cases.set(f'Cases: {done} / {total}'),pct.set(done/total*100),status.set(stage)))
  def work():
   try:
    out=run(ROOT,12,5,False,upd)
    def ok():
     button.config(state='normal');pct.set(100);status.set('Готово; отправлена команда выгрузки модели')
     if os.name=='nt':os.startfile(str(out.resolve()))
     messagebox.showinfo('Series129',f'Лёгкий пакет завершён:\n{out.resolve()}',parent=root)
    root.after(0,ok)
   except Exception as e:
    unload_model();q=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-129.txt';q.parent.mkdir(parents=True,exist_ok=True);q.write_text(type(e).__name__+': '+str(e)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');root.after(0,lambda:(button.config(state='normal'),status.set('Ошибка; отправлена команда выгрузки'),messagebox.showerror('Series129',f'{e}\n\n{q.resolve()}',parent=root)))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=start);root.mainloop()
def main():
 a=argparse.ArgumentParser();a.add_argument('--gui',action='store_true');a.add_argument('--fixture',action='store_true');a.add_argument('--max-cases',type=int,default=12);a.add_argument('--cooldown',type=float,default=5);a.add_argument('--output-root',type=Path,default=ROOT);x=a.parse_args();print(run(x.output_root,x.max_cases,x.cooldown,x.fixture))if not x.gui else gui()
if __name__=='__main__':main()
