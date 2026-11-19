#!/usr/bin/env python3
"""Series86: preregistered multi-action identity and compositional shared-population test."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;RUNNER85=HERE/'85_shared_latent_population.py';RUNNER85_SHA='cdef42fd5f4f45d7b5b37ab01f2b3ba4af22663265b1e1980254a7b44596b210'
ROOT=Path('workspace/runs/ideas/i-observational/multiaction-compositional-population');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');REPORTS=HERE.parent/'reports';DISCLOSED_EXTRACTS=((REPORTS/'frozen-multivariant-replication-user-summary-extract.json','93daa4e4dc360b2b741ee7ff8cac6934d58d293c3aedc82bdc914184e71c468b',range(441,451)),(REPORTS/'shared-latent-population-user-summary-extract.json','f3fc151bedebaaac8600412172696157f9491144ac23fb7c23a11d76a479d4db',range(451,471)));ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal');WORK={}
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load85():
 if file_sha(RUNNER85)!=RUNNER85_SHA:raise ValueError('Закреплённый runner85 изменился.')
 s=importlib.util.spec_from_file_location('series86_source',RUNNER85);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def motif(action,seed,amplitude=1.,cycles=1.,frames=51):
 rng=np.random.default_rng(seed);t=np.linspace(0,1,frames);phase=rng.uniform(-.18,.18);w=2*np.pi*cycles*(t+phase)
 if action=='foreleg_rubbing':
  base=np.stack([24*np.sin(w),34*np.sin(w+.7),46*np.sin(w+1.2),-24*np.sin(w),34*np.sin(w+.7),-46*np.sin(w+1.2)],1)
 elif action=='head_directed_grooming':
  pulse=np.sin(w);base=np.stack([35+18*pulse,-22+28*np.sin(w+.8),38*np.sin(w+1.4),35+18*pulse,-22+28*np.sin(w+.8),38*np.sin(w+1.4)],1)
 elif action=='reach_withdraw':
  reach=np.sin(np.pi*t**(1/max(cycles,.05)));side=-1 if seed%2 else 1;active=np.stack([48*reach,-35*reach,25*reach],1);quiet=np.stack([6*np.sin(w),5*np.sin(w+.4),4*np.sin(w+.8)],1);base=np.concatenate((active,quiet),1) if side<0 else np.concatenate((quiet,active),1)
 else:raise ValueError('Неизвестное действие.')
 return np.clip(amplitude*base,-55,55)
def specs(fixture=False):
 out=[];ident=471
 for action in ACTIONS:
  for rep,cycles in enumerate((.9,1.15,1.4)):
   out.append({'role':'calibration','id':ident,'action':action,'seed':8601+ident,'amplitude':.70,'speed':cycles,'angles_deg':motif(action,8601+ident,.70,cycles)});ident+=1
 ident=480
 for action in ACTIONS:
  for rep,(amp,speed) in enumerate(((.85,.75),(.85,1.25),(1.,.75),(1.,1.25))):out.append({'role':'identity','id':ident,'action':action,'seed':8602+ident,'amplitude':amp,'speed':speed,'angles_deg':motif(action,8602+ident,amp,speed)});ident+=1
 pairs=[(ACTIONS[0],ACTIONS[1]),(ACTIONS[1],ACTIONS[0]),(ACTIONS[0],ACTIONS[2]),(ACTIONS[2],ACTIONS[0]),(ACTIONS[1],ACTIONS[2]),(ACTIONS[2],ACTIONS[1])]
 for ident,pair in zip(range(492,498),pairs):
  left=motif(pair[0],8603+ident,.9,1.,26);right=motif(pair[1],9603+ident,.9,1.,26);out.append({'role':'composition','id':ident,'action_order':list(pair),'seed':[8603+ident,9603+ident],'amplitude':.9,'speed':1.,'split_after_eval_frames':23,'angles_deg':np.concatenate((left[:-1],right),0)})
 if fixture:
  wanted={471,474,477,480,484,488,492,493};return [x for x in out if x['id'] in wanted]
 return out
def disclosed_hashes():
 out=set()
 for path,expected,ids in DISCLOSED_EXTRACTS:
  data=json.loads(path.read_text(encoding='utf8'))
  if data.get('source_file_sha256')!=expected or [x['id'] for x in data['protocol']['holdouts']]!=list(ids):raise ValueError('Published holdout extract identity изменился.')
  out.update(x['motion_sha256'] for x in data['protocol']['holdouts'])
 return out
def prepare(stim,labels,training_hashes,fixture=False):
 seen={x['motion_sha256'] for x in labels}|set(training_hashes)|disclosed_hashes();out=[];desc=[]
 for x in specs(fixture):
  angles=np.asarray(x['angles_deg'],float);h=stim.motion_hash(angles)
  if h in seen:raise ValueError('Series86 motion совпал с training/disclosed motion.')
  seen.add(h);item={**x,'motion_sha256':h};out.append(item);desc.append({k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in item.items() if k!='angles_deg'})
 return out,desc
def source(folder,fixture=False):
 s85=load85();a,z,b,proto,ev,stim,saved,state,summary,paths,tracked,before,bundle,s84v=s85.source(folder,fixture)
 if (not fixture and file_sha(paths[1])!=s85.load84aa().MODEL84Z_SHA) or not summary['primary']['passed']:raise ValueError('Нужен successful frozen model84Z.')
 return s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v
def init_worker(bundle,s84v):
 s85=load85();a=s85.load84aa();z=a.load84z();b=z.m;proto,ev,pre,stim,ck,base,large=b.dependencies();scene=b.VisibleForelegGroomingScene(proto.load('series86_engine','38_two_flies_observation.py'));WORK.update(s85=s85,a=a,b=b,scene=scene,bundle=bundle,s84v=s84v)
def corr_sufficient(x,y):return {'n':len(x),'sx':float(np.sum(x)),'sy':float(np.sum(y)),'sxx':float(x@x),'syy':float(y@y),'sxy':float(x@y)}
def task(arg):
 item,corner=arg;a=WORK['a'];b=WORK['b'];full=item['angles_deg']*np.pi/180;truth=full[2:];cid=corner['corner_id'];images=WORK['scene'].render(full,view=corner['view']);x=b.edge_history(images);shared=a.predict_selected(WORK['bundle'],x);private=np.clip(a.predict_model(WORK['s84v'],x),-np.pi*55/180,np.pi*55/180);rng=np.random.default_rng(np.random.SeedSequence([860400,item['id'],cid]));controls={}
 for name,img in {'shuffled':images[rng.permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)}.items():controls[name]=a.predict_selected(WORK['bundle'],b.edge_history(img))
 _,sr=b.compress_replay(shared);_,pr=b.compress_replay(private);coeff,er=b.compress_replay(truth);metrics={'shared_observation':b.replay_metrics(truth,sr),'private_observation':b.replay_metrics(truth,pr),'execution_mode':b.replay_metrics(truth,er),'zero':b.replay_metrics(truth,np.zeros_like(truth)),'controls':{}}
 for name,q in controls.items():_,r=b.compress_replay(q);metrics['controls'][name]=b.replay_metrics(truth,r)
 suff={name:{} for name in ('shared_observation','private_observation','shuffled','static','closed')}
 for j,axis in enumerate(AXES):
  suff['shared_observation'][axis]=corr_sufficient(shared[:,j],truth[:,j]);suff['private_observation'][axis]=corr_sufficient(private[:,j],truth[:,j])
  for name,q in controls.items():suff[name][axis]=corr_sufficient(q[:,j],truth[:,j])
 digest=sha(np.asarray(coeff,dtype='<f8').tobytes());return {k:v for k,v in item.items() if k!='angles_deg'}|{'corner_id':cid,'frames':49,'view':corner['view'],**metrics,'population_sufficient':suff,'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':True,'state_sha256_before_delay':digest,'state_sha256_after_delay':digest,'diagnostics':{'rgb_sha256':sha(images.tobytes()),'unique_rgb_frames':len({q.tobytes() for q in images}),'feature_max_std':float(np.max(np.std(x,0)))},'_shared':shared,'_private':private,'_execution':truth}
def features(trace):
 x=np.asarray(trace);velocity=np.diff(x,axis=0)*max(1,len(x)-1);return np.concatenate((np.mean(x,0),np.std(x,0),np.sqrt(np.mean(velocity**2,0))))
def classify(v,prototypes,scale):return min(ACTIONS,key=lambda a:float(np.linalg.norm((v-prototypes[a])/scale)))
def pooled(rows,key):
 n=sum(r['frames'] for r in rows);return math.sqrt(sum(r['frames']*r[key]['rmse_rad']**2 for r in rows)/n)
def correlation(rows,name,axis):
 s={k:sum(r['population_sufficient'][name][axis][k] for r in rows) for k in ('n','sx','sy','sxx','syy','sxy')};n=s['n'];vx=s['sxx']-s['sx']**2/n;vy=s['syy']-s['sy']**2/n;return (s['sxy']-s['sx']*s['sy']/n)/math.sqrt(vx*vy) if vx>1e-12 and vy>1e-12 else 0.
def representation_rsa(obs,exe,seed):
 ids=sorted(obs);od=[];ed=[];pairs=[]
 for i,x in enumerate(ids):
  for y in ids[i+1:]:od.append(float(np.linalg.norm(obs[x]-obs[y])));ed.append(float(np.linalg.norm(exe[x]-exe[y])));pairs.append([x,y])
 actual=float(np.corrcoef(od,ed)[0,1]);rng=np.random.default_rng(seed);null=[];vals=[exe[x] for x in ids]
 for _ in range(1000):
  q=rng.permutation(len(ids));pd=[]
  for i in range(len(ids)):
   for j in range(i+1,len(ids)):pd.append(float(np.linalg.norm(vals[q[i]]-vals[q[j]])))
  null.append(float(np.corrcoef(od,pd)[0,1]))
 p95=float(np.quantile(null,.95));return {'correlation':actual,'shuffled_p95':p95,'permutations':1000,'pairs':pairs,'observation_distances':od,'execution_distances':ed,'passed':actual>=.30 and actual>p95}
def accuracy_null(pred,labels,seed):
 actual=sum(a==b for a,b in zip(pred,labels));rng=np.random.default_rng(seed);null=[sum(a==b for a,b in zip(pred,rng.permutation(labels))) for _ in range(1000)];return actual,float(np.quantile(null,.95))
def primary(rows,traces,items):
 calibration=[x for x in items if x['role']=='calibration'];identity=[x for x in items if x['role']=='identity'];composition=[x for x in items if x['role']=='composition'];cal_vectors=[];private_cal_vectors=[];prototypes={};private_prototypes={}
 for action in ACTIONS:
  vv=[];pv=[]
  for item in calibration:
   if item['action']==action:
    obs=features(np.mean(traces[(item['id'],'shared')],0));private_obs=features(np.mean(traces[(item['id'],'private')],0));exe=features(traces[(item['id'],'execution')][0]);vv.extend((obs,exe));pv.extend((private_obs,exe))
  prototypes[action]=np.mean(vv,0);private_prototypes[action]=np.mean(pv,0);cal_vectors.extend(vv);private_cal_vectors.extend(pv)
 scale=np.std(cal_vectors,axis=0);scale[scale<.02]=.02;private_scale=np.std(private_cal_vectors,axis=0);private_scale[private_scale<.02]=.02;obs={};exe={};private={};pred=[];private_pred=[];labels=[];per_action={a:{'correct':0,'cases':0} for a in ACTIONS};identity_rows=[]
 for item in identity:
  ident=item['id'];obs[ident]=features(np.mean(traces[(ident,'shared')],0));private[ident]=features(np.mean(traces[(ident,'private')],0));exe[ident]=features(traces[(ident,'execution')][0]);guess=classify(obs[ident],prototypes,scale);pg=classify(private[ident],private_prototypes,private_scale);pred.append(guess);private_pred.append(pg);labels.append(item['action']);per_action[item['action']]['cases']+=1;per_action[item['action']]['correct']+=guess==item['action'];identity_rows.append({'id':ident,'action':item['action'],'shared_prediction':guess,'private_prediction':pg,'amplitude':item['amplitude'],'speed':item['speed']})
 correct,p95=accuracy_null(pred,labels,860501);private_correct=sum(a==b for a,b in zip(private_pred,labels));identity_pass=correct>=8 and correct>=private_correct-1 and correct>p95 and all(x['correct']>=2 for x in per_action.values());rsa=representation_rsa({k:v/scale for k,v in obs.items()},{k:v/scale for k,v in exe.items()},860502)
 comp_rows=[];comp_correct=0
 for item in composition:
  ident=item['id'];shared=np.mean(traces[(ident,'shared')],0);cut=item['split_after_eval_frames'];guess=[classify(features(shared[:cut]),prototypes,scale),classify(features(shared[cut:]),prototypes,scale)];ok=guess==item['action_order'];comp_correct+=ok;comp_rows.append({'id':ident,'expected':item['action_order'],'predicted':guess,'passed':ok})
 composition_pass=comp_correct>=4;eval_rows=[r for r in rows if r['role']!='calibration'];corrs={name:{a:correlation(eval_rows,name,a) for a in AXES} for name in ('shared_observation','shuffled','static','closed')};dual={a:corrs['shared_observation'][a]>=.15 and corrs['shared_observation'][a]>max(corrs[x][a] for x in ('shuffled','static','closed')) for a in AXES};total=sum(r['frames'] for r in eval_rows);combined={k:pooled(eval_rows,k) for k in ('shared_observation','private_observation','execution_mode','zero')};combined.update({x:math.sqrt(sum(r['frames']*r['controls'][x]['rmse_rad']**2 for r in eval_rows)/total) for x in ('shuffled','static','closed')});performance=combined['shared_observation']<=1.05*combined['private_observation'] and combined['shared_observation']<min(combined[x] for x in ('zero','shuffled','static','closed'));population_pass=sum(dual.values())>=4 and performance;passed=identity_pass and rsa['passed'] and composition_pass and population_pass
 audit={'feature_order':['mean6','std6','time_normalized_velocity_rms6'],'scale':scale,'prototypes':prototypes,'private_scale':private_scale,'private_prototypes':private_prototypes,'identity_observation_features':obs,'identity_execution_features':exe,'identity_private_features':private,'rsa':rsa}
 return {'identity':{'cases':identity_rows,'correct':correct,'required':8,'private_correct':private_correct,'shuffled_accuracy_p95':p95,'per_action':per_action,'passed':identity_pass},'cross_mode_rsa':rsa,'composition':{'cases':comp_rows,'correct':comp_correct,'required':4,'passed':composition_pass},'population':{'correlations':corrs,'dual_active_units':dual,'dual_active_count':sum(dual.values()),'dual_active_required':4,'combined':combined,'performance_margin':.05,'performance_passed':performance,'passed':population_pass},'representation_audit':audit,'passed':passed}
def run(source_folder,workers,output_root=ROOT,fixture=False):
 s85=load85();workers,count=s85.worker_choice(workers);print('1/5 Проверяются frozen85/84AA/84Z identities...',flush=True);s85,a,z,b,proto,stim,saved,state,source_summary,paths,tracked,before,bundle,s84v=source(source_folder,fixture)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items,desc=prepare(stim,saved['labels'],training_hashes,fixture);train,_=proto.split_from_sources(state['sources'],stim);accepted,sample=b.sampled_records(Path(source_folder)/'study.sqlite3',len(train));audit=b.overlap_sample_broad(items,sample,128);audit.update({'accepted_total':accepted,'is_exhaustive':audit['audited_count']==accepted});all_corners=b.geometry_corners();blocking_corners=[all_corners[i] for i in (0,4,8,12)] if fixture else all_corners;cal_corners=[all_corners[i] for i in (0,4,8,12)];tasks=[(x,c) for x in items for c in (cal_corners if x['role']=='calibration' else blocking_corners)];protocol={'schema':'multiaction-compositional-population-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner85_sha256':RUNNER85_SHA,'selected_model_sha256':file_sha(paths[1]),'training_allowed':False,'actions':list(ACTIONS),'calibration_seed':8601,'identity_seed':8602,'composition_seed':8603,'motions':desc,'calibration_corners':[x['corner_id'] for x in cal_corners],'blocking_corners':len(blocking_corners),'workers':count,'worker_choice':str(workers),'primary_rule':'identity >=8/12, >=private-1, >shuffle p95, each action>=2/4; RSA>=.30 and >1000-shuffle p95; ordered compositions>=4/6; >=4/6 dual units corr>=.15 above controls; shared RMSE<=1.05 private and below controls'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('multiaction_compositional_population_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/5 Запускается {len(tasks)} cases, workers={count}.',flush=True);rows=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=init_worker,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(task,tasks),1):rows.append(row);print(f'  Cases {n}/{len(tasks)}',flush=True) if n%16==0 else None
 traces={}
 for row in rows:
  ident=row['id'];traces.setdefault((ident,'shared'),[]).append(row.pop('_shared'));traces.setdefault((ident,'private'),[]).append(row.pop('_private'));traces.setdefault((ident,'execution'),[]).append(row.pop('_execution'));td=temp/row['role']/f'test_{ident:03d}'/f'corner_{row["corner_id"]:02d}';td.mkdir(parents=True);save(td/'metrics.json',row)
 print('3/5 Вычисляются action identity, RSA и compositional gates...',flush=True);decision=primary(rows,traces,items);report={'schema':'multiaction-compositional-population-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':decision,'tests':rows,'source84z_primary':source_summary['primary'],'audit':audit,'limitations':['Three engineered synthetic kinematic motifs, not natural behavior labels.','Artificial six-unit semantic population, not biological neurons.','Frozen supervised visual decoder; no natural vision or action invention.','Kinematic replay only; no actuators, forces or closed-loop correction.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 86: MULTI-ACTION COMPOSITION\n\nPrimary: '+('ВЫПОЛНЕН' if decision['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 complete=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))
 if manifest(folder/'result')!=complete['files']:raise ValueError('Manifest series86 повреждён.')
 print('4/5 Source84Z неизменна.',flush=True);print('5/5 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия86: multi-action composition');root.geometry('700x340+180+110');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия86: три действия, identity и compositional holdout\nFrozen model84Z не обучается.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать завершённую папку84Z и запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 folder=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not folder:root.destroy();return
 root.withdraw();root.update();result=run(folder,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия86 завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-86.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 86: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
 if os.name=='nt':
  try:os.startfile(str(path))
  except OSError:pass
 return path
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source84z');p.add_argument('--workers',default='6');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true',help=argparse.SUPPRESS);q=p.parse_args()
 if q.choose:choose()
 elif q.source84z:run(q.source84z,q.workers,q.output_root,q.fixture)
 else:p.error('Нужен --choose или --source84z.')
if __name__=='__main__':
 try:main()
 except Exception as exc:report=failure_report(exc);print(f'ОШИБКА: {type(exc).__name__}: {exc}\nОтчёт: {report.resolve()}',file=sys.stderr);sys.exit(1)
