#!/usr/bin/env python3
"""Series87: preregistered causal shared/observation/execution/random lesions."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;RUNNER86=HERE/'86_multiaction_compositional_population.py';RUNNER86_SHA='7dc5686028a2fe82d683f091a1f0a08deab25bcc2be41320b5d52e91de6d9714';REPORT86=HERE.parent/'reports'/'multiaction-compositional-population-user-summary-extract.json';REPORT86_SOURCE_SHA='e66a6b52890bbf33b5071f7a2acb15d29a2e8051448a8dfae500df482b46da00'
ROOT=Path('workspace/runs/ideas/i-observational/causal-shared-unit-lesions');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load86():
 if file_sha(RUNNER86)!=RUNNER86_SHA:raise ValueError('Закреплённый runner86 изменился.')
 s=importlib.util.spec_from_file_location('series87_source',RUNNER86);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def published86_hashes():
 d=json.loads(REPORT86.read_text(encoding='utf8'))
 if d.get('source_file_sha256')!=REPORT86_SOURCE_SHA or [x['id'] for x in d['protocol']['motions']]!=list(range(471,498)):raise ValueError('Published series86 identity изменён.')
 return {x['motion_sha256'] for x in d['protocol']['motions']}
def specs(fixture=False):
 m86=load86();out=[];ident=498
 for action in ACTIONS:
  for rep,speed in enumerate((.85,1.1,1.35)):out.append({'role':'calibration','id':ident,'action':action,'lesion_seed':8701+ident,'amplitude':.75,'speed':speed,'angles_deg':m86.motif(action,8701+ident,.75,speed)});ident+=1
 ident=507
 for replicate in range(10):
  for ai,action in enumerate(ACTIONS):
   amp=(.8,.9,1.)[(replicate+ai)%3];speed=(.7,1.,1.3)[(2*replicate+ai)%3];seed=870200+10*replicate+ai;out.append({'role':'evaluation','id':ident,'replicate':replicate+1,'action':action,'lesion_seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 if fixture:
  wanted={498,501,504,507,508,509};return [x for x in out if x['id'] in wanted]
 return out
def prepare(stim,labels,training_hashes,fixture=False):
 m86=load86();seen={x['motion_sha256'] for x in labels}|set(training_hashes)|m86.disclosed_hashes()|published86_hashes();out=[];desc=[]
 for x in specs(fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series87 motion совпал с training/disclosed motion.')
  seen.add(h);item={**x,'motion_sha256':h};out.append(item);desc.append({k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in item.items() if k!='angles_deg'})
 return out,desc
def source(folder,fixture=False):
 m86=load86();s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m86.source(folder,fixture)
 if (not fixture and file_sha(paths[1])!=s85.load84aa().MODEL84Z_SHA) or not summary['primary']['passed']:raise ValueError('Нужен successful frozen model84Z.')
 return m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v
def distance(x,y):return float(np.linalg.norm(np.asarray(x)-np.asarray(y)))
def class_margin(v,label,prototypes,scale):
 ds={a:distance(np.asarray(v)/scale,np.asarray(prototypes[a])/scale) for a in ACTIONS};return min(v for a,v in ds.items() if a!=label)-ds[label]
def classify(v,prototypes,scale):return min(ACTIONS,key=lambda a:distance(np.asarray(v)/scale,np.asarray(prototypes[a])/scale))
def mask_features(v,axes,center):
 q=np.array(v,copy=True)
 for axis in axes:
  j=AXES.index(axis)
  for k in (j,6+j,12+j):q[k]=center[k]
 return q
def lesion_trace(trace,axes):
 q=np.array(trace,copy=True)
 for axis in axes:q[:,AXES.index(axis)]=0.
 return q
def trace_rmse(truth,pred):return float(np.sqrt(np.mean((np.asarray(truth)-np.asarray(pred))**2)))
def replay_rmse(b,truth,pred):
 _,r=b.compress_replay(pred);return b.replay_metrics(truth,r)['rmse_rad']
def rank_groups(m86,b,calibration,rows,traces):
 cal_vectors=[];private_vectors=[];prototypes={};private_prototypes={}
 for action in ACTIONS:
  vv=[];pv=[]
  for item in calibration:
   if item['action']==action:
    obs=m86.features(np.mean(traces[(item['id'],'shared')],0));private=m86.features(np.mean(traces[(item['id'],'private')],0));exe=m86.features(traces[(item['id'],'execution')][0]);vv.extend((obs,exe));pv.extend((private,exe))
  prototypes[action]=np.mean(vv,0);private_prototypes[action]=np.mean(pv,0);cal_vectors.extend(vv);private_vectors.extend(pv)
 scale=np.std(cal_vectors,0);scale[scale<.02]=.02;private_scale=np.std(private_vectors,0);private_scale[private_scale<.02]=.02;center=np.mean(cal_vectors,0);cal_rows=[r for r in rows if r['role']=='calibration'];shared_corr={axis:m86.correlation(cal_rows,'shared_observation',axis) for axis in AXES};shared_impact={};exec_impact={};obs_impact={}
 for axis in AXES:
  sd=[];ed=[];md=[]
  for item in calibration:
   ident=item['id'];truth=traces[(ident,'execution')][0];obs=np.mean(traces[(ident,'shared')],0);sd.append(trace_rmse(truth,lesion_trace(obs,[axis]))-trace_rmse(truth,obs));ed.append(replay_rmse(b,truth,lesion_trace(truth,[axis]))-replay_rmse(b,truth,truth));v=m86.features(obs);md.append(class_margin(v,item['action'],prototypes,scale)-class_margin(mask_features(v,[axis],center),item['action'],prototypes,scale))
  shared_impact[axis]=float(np.mean(sd)+np.mean(ed));exec_impact[axis]=float(np.mean(ed));obs_impact[axis]=float(np.mean(md))
 eligible=[a for a in AXES if shared_corr[a]>=.15]
 if len(eligible)<2:raise ValueError('Calibration не нашла2 shared-selective units.')
 shared=sorted(eligible,key=lambda a:(shared_impact[a],a),reverse=True)[:2];observation=sorted(AXES,key=lambda a:(obs_impact[a],a),reverse=True)[:2];execution=sorted(AXES,key=lambda a:(exec_impact[a],a),reverse=True)[:2];remaining=[a for a in AXES if a not in shared];rng=np.random.default_rng(8704);random_group=sorted(rng.choice(remaining,2,replace=False).tolist())
 ranking={'shared_correlation':shared_corr,'shared_impact':shared_impact,'observation_margin_impact':obs_impact,'execution_replay_impact':exec_impact,'groups':{'shared_selective':shared,'observation_only':observation,'execution_only':execution,'random_matched':random_group},'lesion_budget_semantic_units':2,'ranking_data':'calibration498-506 only'}
 return prototypes,private_prototypes,scale,private_scale,center,ranking
def evaluate(m86,b,items,rows,traces):
 calibration=[x for x in items if x['role']=='calibration'];evaluation=[x for x in items if x['role']=='evaluation'];prototypes,private_prototypes,scale,private_scale,center,ranking=rank_groups(m86,b,calibration,rows,traces);g=ranking['groups'];motion=[]
 for item in evaluation:
  ident=item['id'];truth=traces[(ident,'execution')][0];obs_views=traces[(ident,'shared')];obs=np.mean(obs_views,0);feat=m86.features(obs);base_margin=class_margin(feat,item['action'],prototypes,scale);obs_feat=mask_features(feat,g['observation_only'],center);obs_margin=class_margin(obs_feat,item['action'],prototypes,scale);base_pred=classify(feat,prototypes,scale);obs_pred=classify(obs_feat,prototypes,scale);private_feat=m86.features(np.mean(traces[(ident,'private')],0));private_pred=classify(private_feat,private_prototypes,private_scale);base_r=[];shared_r=[];random_r=[]
  for view in obs_views:base_r.append(replay_rmse(b,truth,view));shared_r.append(replay_rmse(b,truth,lesion_trace(view,g['shared_selective'])));random_r.append(replay_rmse(b,truth,lesion_trace(view,g['random_matched'])))
  prod_base=replay_rmse(b,truth,truth);prod_exec=replay_rmse(b,truth,lesion_trace(truth,g['execution_only']));prod_shared=replay_rmse(b,truth,lesion_trace(truth,g['shared_selective']));prod_random=replay_rmse(b,truth,lesion_trace(truth,g['random_matched']));motion.append({'id':ident,'replicate':item['replicate'],'action':item['action'],'baseline_prediction':base_pred,'observation_lesion_prediction':obs_pred,'private_prediction':private_pred,'baseline_margin':base_margin,'observation_lesion_margin':obs_margin,'recognition_margin_loss':base_margin-obs_margin,'observation_replay_rmse':{'baseline':float(np.mean(base_r)),'shared_lesion':float(np.mean(shared_r)),'random_lesion':float(np.mean(random_r))},'production_replay_rmse':{'baseline':prod_base,'execution_lesion':prod_exec,'shared_lesion':prod_shared,'random_lesion':prod_random}})
 baseline_correct=sum(x['baseline_prediction']==x['action'] for x in motion);private_correct=sum(x['private_prediction']==x['action'] for x in motion);obs_correct=sum(x['observation_lesion_prediction']==x['action'] for x in motion);margin_losses=[x['recognition_margin_loss'] for x in motion];recognition={'baseline_correct':baseline_correct,'private_correct':private_correct,'observation_lesion_correct':obs_correct,'cases':30,'margin_loss_mean':float(np.mean(margin_losses)),'margin_loss_wins':sum(x>0 for x in margin_losses)};recognition['passed']=baseline_correct>=20 and baseline_correct>=private_correct-2 and recognition['margin_loss_mean']>0 and recognition['margin_loss_wins']>=18
 base=np.array([x['observation_replay_rmse']['baseline'] for x in motion]);shared=np.array([x['observation_replay_rmse']['shared_lesion'] for x in motion]);random=np.array([x['observation_replay_rmse']['random_lesion'] for x in motion]);shared_effect={'baseline_mean':float(np.mean(base)),'shared_lesion_mean':float(np.mean(shared)),'random_lesion_mean':float(np.mean(random)),'shared_degradation':float(np.mean(shared-base)),'random_degradation':float(np.mean(random-base)),'shared_vs_random_wins':int(np.sum((shared-base)>(random-base)))};shared_effect['passed']=shared_effect['shared_degradation']>1.05*shared_effect['random_degradation'] and shared_effect['shared_vs_random_wins']>=18
 pb=np.array([x['production_replay_rmse']['baseline'] for x in motion]);pe=np.array([x['production_replay_rmse']['execution_lesion'] for x in motion]);production={'baseline_mean':float(np.mean(pb)),'execution_lesion_mean':float(np.mean(pe)),'degradation':float(np.mean(pe-pb)),'degradation_wins':int(np.sum(pe>pb))};production['passed']=production['execution_lesion_mean']>1.20*production['baseline_mean'] and production['degradation_wins']>=27
 no_collapse=shared_effect['shared_lesion_mean']<float(np.mean([trace_rmse(traces[(x['id'],'execution')][0],np.zeros_like(traces[(x['id'],'execution')][0])) for x in evaluation]));double={'observation_specific':recognition['margin_loss_mean']>0,'execution_specific':production['degradation']>0,'unaffected_cross_routes_exact_by_design':True,'no_total_observation_collapse':no_collapse};double['passed']=all(double.values());passed=recognition['passed'] and shared_effect['passed'] and production['passed'] and double['passed'];return {'ranking':ranking,'motion_results':motion,'recognition':recognition,'shared_causal_effect':shared_effect,'execution_causal_effect':production,'double_dissociation':double,'passed':passed}
def run(source_folder,workers,output_root=ROOT,fixture=False):
 m86=load86();s85=m86.load85();workers,count=s85.worker_choice(workers);print('1/5 Проверяются frozen86/85/84Z identities...',flush=True);m86,s85,a,z,b,proto,stim,saved,state,source_summary,paths,tracked,before,bundle,s84v=source(source_folder,fixture)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items,desc=prepare(stim,saved['labels'],training_hashes,fixture);train,_=proto.split_from_sources(state['sources'],stim);accepted,sample=b.sampled_records(Path(source_folder)/'study.sqlite3',len(train));audit=b.overlap_sample_broad(items,sample,128);audit.update({'accepted_total':accepted,'is_exhaustive':audit['audited_count']==accepted});all_corners=b.geometry_corners();blocking=[all_corners[i] for i in (0,4,8,12)] if fixture else all_corners;cal=[all_corners[i] for i in (0,4,8,12)];tasks=[(x,c) for x in items for c in (cal if x['role']=='calibration' else blocking)];protocol={'schema':'causal-shared-unit-lesions-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner86_sha256':RUNNER86_SHA,'selected_model_sha256':file_sha(paths[1]),'training_allowed':False,'actions':list(ACTIONS),'calibration_seed':8701,'evaluation_seed_base':870200,'evaluation_replicates':10,'motions':desc,'calibration_corners':[x['corner_id'] for x in cal],'blocking_corners':len(blocking),'lesion_budget_semantic_units':2,'ranking_uses_blocking':False,'workers':count,'worker_choice':str(workers),'primary_rule':'baseline identity>=20/30 and >=private-2; obs-lesion margin loss>0 in>=18/30; shared obs degradation>1.05 random and wins>=18/30; execution lesion RMSE>1.20 baseline and wins>=27/30; double dissociation and no total collapse'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('causal_shared_unit_lesions_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/5 Запускается {len(tasks)} cases, workers={count}.',flush=True);rows=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=m86.init_worker,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(m86.task,tasks),1):rows.append(row);print(f'  Cases {n}/{len(tasks)}',flush=True) if n%16==0 else None
 traces={}
 for row in rows:
  ident=row['id'];traces.setdefault((ident,'shared'),[]).append(row.pop('_shared'));traces.setdefault((ident,'private'),[]).append(row.pop('_private'));traces.setdefault((ident,'execution'),[]).append(row.pop('_execution'));td=temp/row['role']/f'test_{ident:03d}'/f'corner_{row["corner_id"]:02d}';td.mkdir(parents=True);save(td/'metrics.json',row)
 print('3/5 Ranking calibration-only и causal lesion gates...',flush=True);decision=evaluate(m86,b,items,rows,traces);report={'schema':'causal-shared-unit-lesions-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':decision,'tests':rows,'source84z_primary':source_summary['primary'],'audit':audit,'limitations':['Interventions target engineered semantic/pathway units, not biological neurons.','Observation-only lesion masks classifier feature blocks; execution-only lesion zeros proprioceptive channels.','Synthetic motifs and frozen supervised visual decoder; no natural vision.','Kinematic replay only; no actuators, forces or closed-loop correction.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 87: CAUSAL LESIONS\n\nPrimary: '+('ВЫПОЛНЕН' if decision['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 complete=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))
 if manifest(folder/'result')!=complete['files']:raise ValueError('Manifest series87 повреждён.')
 print('4/5 Source84Z неизменна.',flush=True);print('5/5 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия87: causal shared-unit lesions');root.geometry('710x350+180+100');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия87: calibration-only ranking и causal lesions\n10 новых replicates ×3 actions; frozen model84Z.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать завершённую папку84Z и запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 folder=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not folder:root.destroy();return
 root.withdraw();root.update();result=run(folder,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия87 завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-87.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 87: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
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
