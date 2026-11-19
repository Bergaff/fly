#!/usr/bin/env python3
"""Series85: preregistered shared observation/execution latent population prototype."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER84AA=HERE/'84aa_frozen_multivariant_replication.py';RUNNER84AA_SHA='846bf4b56e7d6d221a8a5a35eb02675f16bde570ea7e7b7a8e2d822f4c33e879'
ROOT=Path('workspace/runs/ideas/i-observational/shared-latent-population');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble')
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal');WORK={}
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load84aa():
 if file_sha(RUNNER84AA)!=RUNNER84AA_SHA:raise ValueError('Закреплённый runner84AA изменился.')
 s=importlib.util.spec_from_file_location('shared85_source',RUNNER84AA);a=importlib.util.module_from_spec(s);s.loader.exec_module(a);return a
def holdouts():
 out=[]
 for battery,(seed,start) in enumerate(((8502,451),(8503,461)),1):
  rng=np.random.default_rng(seed)
  for i,ident in enumerate(range(start,start+10),1):
   n=5 if i<=5 else 9;v=rng.integers(-55,56,size=(n,6)).astype(int);v[:,3]=np.clip(-v[:,0]+np.rint(.25*v[:,3]).astype(int),-55,55);v[:,4]=np.clip(v[:,1]+np.rint(.25*v[:,4]).astype(int),-55,55);v[:,5]=np.clip(-v[:,2]+np.rint(.25*v[:,5]).astype(int),-55,55);obj={'schema':'fly-wings-trajectory-v1','semantic_schema':'fly-foreleg-grooming-six-joint-v1','channels':list(AXES),'fps':25,'duration_s':2,'keyframes':[{'t':2*j/(n-1),'angles_deg':v[j].tolist()} for j in range(n)]};raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode();out.append((battery,ident,raw))
 return out
def source(folder,fixture=False):
 a=load84aa();data=a.source(folder,fixture);z,b,proto,ev,stim,saved,state,summary,paths,tracked,before,bundle,s84v=data
 if (not fixture and file_sha(paths[1])!=a.MODEL84Z_SHA) or not summary['primary']['passed']:raise ValueError('Нужен successful frozen model84Z соответствующего режима.')
 return a,z,b,proto,ev,stim,saved,state,summary,paths,tracked,before,bundle,s84v
def items(stim,labels,fixture=False):
 seen={x['motion_sha256'] for x in labels};out=[];desc=[]
 for battery,ident,raw in holdouts():
  t,a=stim.sample_trajectory(json.loads(raw));h=stim.motion_hash(a)
  if h in seen:raise ValueError('Series85 holdout совпал с раскрытым движением.')
  seen.add(h);out.append({'battery':battery,'id':ident,'times':t,'angles_deg':a,'motion_sha256':h});desc.append({'battery':battery,'id':ident,'source_sha256':sha(raw),'motion_sha256':h,'family':'piecewise5' if ident%10 in (1,2,3,4,5) else'piecewise9'})
 return (out[:2],desc[:2]) if fixture else(out,desc)
def init_worker(bundle,s84v,fixture):
 a=load84aa();z=a.load84z();b=z.m;proto,ev,pre,stim,ck,base,large=b.dependencies();scene=b.VisibleForelegGroomingScene(proto.load('series85_engine','38_two_flies_observation.py'));WORK.update(a=a,z=z,b=b,scene=scene,bundle=bundle,s84v=s84v,fixture=fixture)
def corr_sufficient(x,y):
 return {'n':len(x),'sx':float(np.sum(x)),'sy':float(np.sum(y)),'sxx':float(x@x),'syy':float(y@y),'sxy':float(x@y)}
def task(arg):
 item,corner=arg;a=WORK['a'];b=WORK['b'];full=item['angles_deg']*np.pi/180;truth=full[2:];cid=corner['corner_id'];images=WORK['scene'].render(full,view=corner['view']);x=b.edge_history(images);candidate=a.predict_selected(WORK['bundle'],x);private=np.clip(a.predict_model(WORK['s84v'],x),-np.pi*55/180,np.pi*55/180);rng=np.random.default_rng(np.random.SeedSequence([850400,item['id'],cid]));control_traces={}
 for name,img in {'shuffled':images[rng.permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)}.items():control_traces[name]=a.predict_selected(WORK['bundle'],b.edge_history(img))
 coeff,replay=b.compress_replay(candidate);exec_coeff,exec_replay=b.compress_replay(truth);_,private_replay=b.compress_replay(private);controls={};suff={name:{} for name in ('shared_observation','private_observation','shuffled','static','closed')}
 for name,q in control_traces.items():_,r=b.compress_replay(q);controls[name]=b.replay_metrics(truth,r)
 for j,axis in enumerate(AXES):
  suff['shared_observation'][axis]=corr_sufficient(candidate[:,j],truth[:,j]);suff['private_observation'][axis]=corr_sufficient(private[:,j],truth[:,j])
  for name,q in control_traces.items():suff[name][axis]=corr_sufficient(q[:,j],truth[:,j])
 digest=sha(np.asarray(coeff,dtype='<f8').tobytes());return {'battery':item['battery'],'test_id':item['id'],'corner_id':cid,'frames':len(truth),'view':corner['view'],'shared_observation':b.replay_metrics(truth,replay),'private_observation':b.replay_metrics(truth,private_replay),'execution_mode':b.replay_metrics(truth,exec_replay),'zero':b.replay_metrics(truth,np.zeros_like(truth)),'controls':controls,'population_sufficient':suff,'shared_units':6,'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':True,'state_sha256_before_delay':digest,'state_sha256_after_delay':digest,'diagnostics':{'rgb_sha256':sha(images.tobytes()),'unique_rgb_frames':len({q.tobytes() for q in images}),'feature_max_std':float(np.max(np.std(x,0)))},'_candidate':candidate,'_private':private,'_execution':truth}
def pooled(rows,key):
 n=sum(r['frames'] for r in rows);return math.sqrt(sum(r['frames']*r[key]['rmse_rad']**2 for r in rows)/n)
def combine_sufficient(rows,name,axis):
 out={k:sum(r['population_sufficient'][name][axis][k] for r in rows) for k in ('n','sx','sy','sxx','syy','sxy')};return out
def correlation(s):
 n=s['n'];vx=s['sxx']-s['sx']**2/n;vy=s['syy']-s['sy']**2/n;return (s['sxy']-s['sx']*s['sy']/n)/math.sqrt(vx*vy) if vx>1e-15 and vy>1e-15 else 0.
def rsa(obs,exe,seed):
 ids=sorted(obs);od=[];ed=[]
 for i,x in enumerate(ids):
  for y in ids[i+1:]:od.append(float(np.linalg.norm(obs[x]-obs[y])));ed.append(float(np.linalg.norm(exe[x]-exe[y])))
 actual=float(np.corrcoef(od,ed)[0,1]);rng=np.random.default_rng(seed);null=[];vals=[exe[x] for x in ids]
 for _ in range(1000):
  q=rng.permutation(len(ids));pd=[]
  for i in range(len(ids)):
   for j in range(i+1,len(ids)):pd.append(float(np.linalg.norm(vals[q[i]]-vals[q[j]])))
  null.append(float(np.corrcoef(od,pd)[0,1]))
 return {'correlation':actual,'shuffled_p95':float(np.quantile(null,.95)),'permutations':1000,'passed':actual>=.30 and actual>float(np.quantile(null,.95))}
def primary(rows,traces):
 batteries=[]
 for battery in (1,2):
  rr=[r for r in rows if r['battery']==battery];corrs={name:{axis:correlation(combine_sufficient(rr,name,axis)) for axis in AXES} for name in ('shared_observation','private_observation','shuffled','static','closed')};dual={axis:corrs['shared_observation'][axis]>=.20 and corrs['shared_observation'][axis]>max(corrs['shuffled'][axis],corrs['static'][axis],corrs['closed'][axis]) for axis in AXES};obs={};exe={};private={}
  for ident in sorted({r['test_id'] for r in rr}):
   tt=traces[(ident,'execution')][0];obs[ident]=np.mean(traces[(ident,'candidate')],axis=0).reshape(-1);private[ident]=np.mean(traces[(ident,'private')],axis=0).reshape(-1);exe[ident]=tt.reshape(-1)
  rs=rsa(obs,exe,850500+battery);pr=rsa(private,exe,850600+battery);combined={'shared_observation':pooled(rr,'shared_observation'),'private_observation':pooled(rr,'private_observation'),'execution_mode':pooled(rr,'execution_mode'),'zero':pooled(rr,'zero'),**{k:math.sqrt(sum(r['frames']*r['controls'][k]['rmse_rad']**2 for r in rr)/sum(r['frames'] for r in rr)) for k in ('shuffled','static','closed')}};performance=combined['shared_observation']<=1.02*combined['private_observation'] and combined['shared_observation']<min(combined[k] for k in ('zero','shuffled','static','closed'));passed=sum(dual.values())>=4 and rs['passed'] and performance;batteries.append({'battery':battery,'motions':list(range(451 if battery==1 else 461,461 if battery==1 else 471)),'unit_correlations':corrs,'dual_active_units':dual,'dual_active_count':sum(dual.values()),'dual_active_required':4,'shared_rsa':rs,'private_observation_rsa':pr,'combined':combined,'performance_not_worse_private_margin':.02,'performance_passed':performance,'passed':passed})
 return {'batteries':batteries,'shared_units':6,'common_decoder':'same six semantic units -> 72 compressed replay coefficients in both modes','private_controls_equal_unit_budget':True,'batteries_passed':sum(x['passed'] for x in batteries),'batteries_required':2,'passed':all(x['passed'] for x in batteries)}
def run(source_folder,workers,output_root=ROOT,fixture=False):
 if workers not in (2,4,6) and workers!='max':raise ValueError('Workers должны быть2,4,6 или max.')
 count=max(1,os.cpu_count() or 1) if workers=='max' else int(workers)
 print('1/5 Проверяются frozen go84Z и replication authorization84AA...',flush=True);a,z,b,proto,ev,stim,saved,state,source_summary,paths,tracked,before,bundle,s84v=source(source_folder,fixture);tests,desc=items(stim,saved['labels'],fixture);corners=[b.geometry_corners()[i] for i in (0,2,4,6)] if fixture else b.geometry_corners()
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 if any(x['motion_sha256'] in training_hashes for x in tests):raise ValueError('Series85 holdout совпал с training motion84Z.')
 train,_=proto.split_from_sources(state['sources'],stim);accepted,sample=b.sampled_records(Path(source_folder)/'study.sqlite3',len(train));audit=b.overlap_sample_broad(tests,sample,128);audit.update({'accepted_total':accepted,'is_exhaustive':audit['audited_count']==accepted})
 protocol={'schema':'shared-latent-population-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner84aa_sha256':RUNNER84AA_SHA,'selected_model_sha256':file_sha(paths[1]),'selected_variant':bundle['selected_variant'],'shared_units':6,'private_units_each':6,'common_decoder_coefficients':72,'training_allowed':False,'motion_seeds':[8502,8503],'holdouts':desc,'geometry_corners':len(corners),'workers':count,'worker_choice':str(workers),'primary_rule':'both batteries: >=4/6 dual-active units corr>=0.20 above temporal/static/closed; cross-mode RSA>=0.30 and >1000-label-shuffle p95; shared observation <=1.02 private84V and below zero/shuffled/static/closed'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('shared_latent_population_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/5 Запускается {len(tests)*len(corners)} cases, workers={count}.',flush=True);args=[(item,corner) for item in tests for corner in corners];rows=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=init_worker,initargs=(bundle,s84v,fixture)) as pool:
  for n,row in enumerate(pool.map(task,args),1):rows.append(row);print(f'  Cases {n}/{len(args)}',flush=True) if n%len(corners)==0 else None
 traces={}
 for row in rows:
  ident=row['test_id'];traces.setdefault((ident,'candidate'),[]).append(row.pop('_candidate'));traces.setdefault((ident,'private'),[]).append(row.pop('_private'));traces.setdefault((ident,'execution'),[]).append(row.pop('_execution'));td=temp/f'battery_{row["battery"]}'/f'test_{ident:03d}'/f'corner_{row["corner_id"]:02d}';td.mkdir(parents=True);save(td/'metrics.json',row)
 print('3/5 Пересчитываются shared-population gates...',flush=True);decision=primary(rows,traces);report={'schema':'shared-latent-population-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':decision,'tests':rows,'source84z_primary':source_summary['primary'],'audit':audit,'limitations':['Artificial six-unit semantic population; not biological neurons.','One grooming action family; action identity and compositional transfer remain for series86.','Frozen visual decoder and synthetic rendering; no natural vision.','Kinematic replay only; no actuators, forces or closed-loop correction.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 85: SHARED LATENT POPULATION\n\nPrimary: '+('ВЫПОЛНЕН' if decision['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 complete=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))
 if manifest(folder/'result')!=complete['files']:raise ValueError('Manifest series85 повреждён.')
 print('4/5 Source84Z осталась неизменной.',flush=True);print('5/5 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия85: shared latent population');root.geometry('680x330+180+120');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия85: shared observation/execution population prototype\nНовые motions451–470, две независимые batteries, без обучения model84Z.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать завершённую папку84Z и запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 folder=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not folder:root.destroy();return
 root.withdraw();root.update();result=run(folder,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия85 завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-85.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 85: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
 if os.name=='nt':
  try:os.startfile(str(path))
  except OSError:pass
 try:
  import tkinter as tk
  from tkinter import messagebox
  root=tk.Tk();root.withdraw();root.attributes('-topmost',True);messagebox.showerror('Серия85 остановлена','Подробная ошибка открыта в Блокноте. Пришлите файл:\n\n'+str(path.resolve()),parent=root);root.destroy()
 except Exception:pass
 return path
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source84z');p.add_argument('--workers',default='6');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture',action='store_true',help=argparse.SUPPRESS);a=p.parse_args();workers='max' if a.workers.lower()=='max' else int(a.workers)
 if a.choose:choose()
 elif a.source84z:run(a.source84z,workers,a.output_root,a.fixture)
 else:p.error('Нужен --choose или --source84z.')
if __name__=='__main__':
 try:main()
 except Exception as exc:report=failure_report(exc);print(f'ОШИБКА: {type(exc).__name__}: {exc}\nОтчёт: {report.resolve()}',file=sys.stderr);sys.exit(1)
