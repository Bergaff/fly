#!/usr/bin/env python3
"""Series84Z: preregistered multi-variant ridge/ensemble model development.

Exactly 4096 new base motions use the four balanced84V views. Six fixed variants are selected on development motions before one untouched blocking evaluation.
Model84V, model84S and model84R are frozen comparators. No disclosed motion321-420 is reused.
"""
from __future__ import annotations
import argparse,concurrent.futures,csv,hashlib,importlib.util,io,itertools,json,multiprocessing,os,sqlite3,sys,time,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER84V=HERE/'84v_paired_view_distal_consistency.py';RUNNER84V_SHA='05a0cdd4696af5b8901a1d34a205db8a286264f518cb54e93d1e0b9f9e9e4a52'
MODEL84V_SHA='44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af'
RECOVERABLE_SCRIPT_SHAS=('7c1383acdcfcc3257cb2133398d97c891e2be701f5a7fbdfe1df604fa96138ed','82bee325e64b7d74f749e3a71fb1b6c21eb309076369368d83bc616816fa8ad4')
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal');TARGET=16384
ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/paired-view-distal-consistency')
SELECTED_WORKERS=6;SELECTED_RESOURCE_MODE='6'

def set_resources(choice):
 global SELECTED_WORKERS,SELECTED_RESOURCE_MODE
 if str(choice).lower()=='max':SELECTED_WORKERS=max(1,os.cpu_count() or 1);SELECTED_RESOURCE_MODE='max'
 else:
  workers=int(choice)
  if workers not in (2,4,6):raise ValueError('Workers должны быть2,4,6 или max.')
  SELECTED_WORKERS=workers;SELECTED_RESOURCE_MODE=str(workers)
 return SELECTED_WORKERS

def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def load84v():
 if file_sha(RUNNER84V)!=RUNNER84V_SHA:raise ValueError('Закреплённый runner84V изменился.')
 s=importlib.util.spec_from_file_location('multivariant84z_source',RUNNER84V);v=importlib.util.module_from_spec(s);s.loader.exec_module(v);return v
v=load84v();m=v.m;BASE_PROTOCOL=v.protocol;BASE_WORKER_INIT=m.worker_init;BASE_WORKER_GENERATE=m.worker_generate

def paired_view(ident):
 base=ident//4;slot=ident%4;corners=m.geometry_corners();lower=[x['view'] for x in corners if x['view']['body_x']==3.82];upper=[x['view'] for x in corners if x['view']['body_x']==4.18]
 # Exact balanced84V allocation: two lower-X and two upper-X views.
 k=base%8;op=k^7;return (lower[k],lower[op],upper[(k+3)%8],upper[((k+3)%8)^7])[slot].copy()
def paired_candidate(ident):
 if type(ident)!=int or not 0<=ident<TARGET:raise ValueError('Неверный paired candidate id.')
 base=ident//4;rng=np.random.default_rng(np.random.SeedSequence([8433,base]));t=np.arange(51,dtype=float)/25;family=('piecewise5','piecewise9','harmonic','chirp')[base%4]
 if family.startswith('piecewise'):
  count=5 if family=='piecewise5' else 9;knots=np.linspace(0,2,count);values=rng.integers(-55,56,size=(count,6)).astype(float);degrees=np.stack([np.interp(t,knots,values[:,j]) for j in range(6)],axis=1);parameters={'keyframes_deg':values.astype(int).tolist()}
 else:
  offset=rng.uniform(-12,12,6);amplitude=rng.uniform(18,48,6);phase=rng.uniform(0,2*np.pi,6)
  if family=='harmonic':frequency=rng.uniform(.4,3.2,6);degrees=offset+amplitude*np.sin(2*np.pi*t[:,None]*frequency+phase);parameters={'offset_deg':offset.tolist(),'amplitude_deg':amplitude.tolist(),'phase_rad':phase.tolist(),'frequency_hz':frequency.tolist()}
  else:f0=rng.uniform(.25,1.2,6);f1=rng.uniform(1.8,4.0,6);sweep=(f1-f0)/2;degrees=offset+amplitude*np.sin(phase+2*np.pi*(t[:,None]*f0+.5*t[:,None]**2*sweep));parameters={'offset_deg':offset.tolist(),'amplitude_deg':amplitude.tolist(),'phase_rad':phase.tolist(),'f0_hz':f0.tolist(),'f1_hz':f1.tolist()}
 degrees[:,3]=-degrees[:,0]+.25*degrees[:,3];degrees[:,4]=degrees[:,1]+.25*degrees[:,4];degrees[:,5]=-degrees[:,2]+.25*degrees[:,5];before=degrees.copy();degrees=np.clip(degrees,-55,55)
 spec={'protocol':'multivariant-ridge-ensemble-v1','sequence_id':ident,'base_motion_id':base,'paired_view_slot':ident%4,'generator_seed':[8433,base],'family':family,'parameters':parameters,'foreleg_pattern':'three-joint opposed grooming with 0.25 independent perturbation','distance':4.,'side_offset':0.,'view':paired_view(ident),'clipped_values':int(np.count_nonzero(before!=degrees)),'sampled_motion_sha256':m.broad_motion_hash(degrees)};return spec,degrees

def prepared_holdouts():
 folder=ROOT/'prepared_holdouts_seeds_8434_8435';folder.mkdir(parents=True,exist_ok=True);paths=[]
 for seed,start in ((8434,421),(8435,431)):
  rng=np.random.default_rng(seed)
  for i,ident in enumerate(range(start,start+10),1):
   path=folder/f'holdout_{ident:03d}.json';count=5 if i<=5 else 9;v=rng.integers(-55,56,size=(count,6)).astype(int);v[:,3]=np.clip(-v[:,0]+np.rint(.25*v[:,3]).astype(int),-55,55);v[:,4]=np.clip(v[:,1]+np.rint(.25*v[:,4]).astype(int),-55,55);v[:,5]=np.clip(-v[:,2]+np.rint(.25*v[:,5]).astype(int),-55,55);obj={'schema':'fly-wings-trajectory-v1','semantic_schema':'fly-foreleg-grooming-six-joint-v1','channels':list(AXES),'fps':25,'duration_s':2,'keyframes':[{'t':2*j/(count-1),'angles_deg':v[j].tolist()} for j in range(count)]};raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
   if path.exists() and path.read_bytes()!=raw:raise ValueError('Закреплённый holdout изменён.')
   if not path.exists():path.write_bytes(raw)
   paths.append(path)
 return paths

def protocol(source_sha,labels,fixture_limit,proto,source84r_sha,console):
 p=BASE_PROTOCOL(source_sha,labels,fixture_limit,proto,source84r_sha,console);p.update({'schema':'multivariant-ridge-ensemble-v1','script_sha256':file_sha(__file__),'runner84v_sha256':RUNNER84V_SHA,'source84v_model_sha256':source_sha['source84v_model.npz'],'target_candidates':fixture_limit if fixture_limit is not None else TARGET,'workers':SELECTED_WORKERS,'batch':SELECTED_WORKERS,'worker_choice':SELECTED_RESOURCE_MODE})
 p['training_generator'].update({'seed':8433,'view_seed':None,'view_sampling':'4096 base motions x4 exact balanced84V paired corners:2 lower-X+2 upper-X','base_motions':(fixture_limit+3)//4 if fixture_limit is not None else 4096,'paired_views_per_motion':4,'lower_views_per_motion':2,'upper_views_per_motion':2,'exact_84v_view_allocation':True})
 p['variants']=[{'name':'ridge_0175','right_distal_ridge':.175,'new_weight':1.0},{'name':'ridge_0350','right_distal_ridge':.35,'new_weight':1.0},{'name':'ridge_0700','right_distal_ridge':.7,'new_weight':1.0},{'name':'ridge_1400','right_distal_ridge':1.4,'new_weight':1.0},{'name':'ensemble_v75_new25','right_distal_ridge':.35,'new_weight':.25},{'name':'ensemble_v50_new50','right_distal_ridge':.35,'new_weight':.5}]
 p['development']={'motion_seed':8434,'holdouts':list(range(421,431)),'geometry_corners':16,'selection':'eligible strict84X gates first; then maximize passed core gates, normalized RD wins, minimize normalized pooled error, fixed variant order'}
 p['evaluation']={'motion_seed':8435,'holdouts':list(range(431,441)),'geometry_corners':16,'comparators':['source84v','source84s','source84r'],'body_x_safeguards':[3.82,4.18],'camera_z_safeguards':[.36,.56],'lower_x_right_distal_wins_required':60,'state_coefficients':72,'delay_s':.5}
 p['primary_rule']='selected only on motions421-430; untouched motions431-440 x16 use strict gates: right distal below and >=60% wins vs frozen84V,84S,84R globally/lower-X; other axes <=5% worse all; combined below all/zero/controls; both X/Z; >=12/16 corners'
 return p
def verify_pins(proto,saved):
 if file_sha(__file__)!=saved['script_sha256'] or file_sha(RUNNER84V)!=RUNNER84V_SHA:raise ValueError('Runner84Z/84V изменился.')
 for name,expected in {**proto.PIN,**m.PIN}.items():
  if file_sha(HERE/name)!=expected:raise ValueError(f'Закреплённый файл {name} изменился.')

def source_snapshot(folder,fixture,proto,stim,ck):
 source_v=load84v();base=source_v.m;folder=Path(folder).resolve();saved,state,stage,_=base.saved_state(folder/'study.sqlite3',proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая series84V.')
 result=folder/'result';base.verify_result(result,saved,state);summary=json.loads((result/'summary.json').read_text(encoding='utf8'));expected='fixture_completed' if fixture else 'completed'
 if summary.get('status')!=expected or not summary.get('primary',{}).get('passed'):raise ValueError('Нужен завершённый go84V.')
 model=(result/'model_paired_view.npz').read_bytes();model_sha=sha(model)
 if model_sha!=summary.get('candidate_model_sha256') or (not fixture and model_sha!=MODEL84V_SHA):raise ValueError('Нужна frozen production model84V.')
 sources=dict(state['sources']);labels=[dict(x) for x in saved['labels']];fresh=prepared_holdouts();new=[x for x in labels if x['role']=='new_test']
 if len(new)!=10 or len(fresh)!=20:raise ValueError('Нужны10 source labels и20 новых development/blocking holdouts.')
 seen={x['motion_sha256'] for x in labels if x['role']!='new_test'}
 for index,path in enumerate(fresh,1):
  raw=path.read_bytes();_,angles=stim.sample_trajectory(json.loads(raw));motion=stim.motion_hash(angles)
  if motion in seen:raise ValueError('Новый holdout совпал с раскрытым движением.')
  seen.add(motion)
  if index<=10:label=new[index-1]
  else:label={**new[-1],'copy':f'test_{index:03d}.json'};labels.append(label)
  sources[label['copy']]=raw;label.update({'id':index,'source_sha256':sha(raw),'motion_sha256':motion,'original_basename':path.name,'role':'new_test'})
 sources['source84v_model.npz']=model;sources['source84v_summary.json']=(result/'summary.json').read_bytes()
 return {'sources':sources,'labels':labels,'source_sha256':{k:sha(v) for k,v in sorted(sources.items())},'source84r_model_sha256':summary['source84r_model_sha256']}

def pooled(rows,key,axis=None):
 n=sum(r['frames'] for r in rows);return float(np.sqrt(sum(r['frames']*(r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad'])**2 for r in rows)/n))
def primary_decision(rows,fixture):
 sources=('source84v','source84s','source84r');axes={};n=len(rows)
 for axis in AXES:
  c=pooled(rows,'candidate',axis);z=pooled(rows,'zero',axis);values={k:pooled(rows,k,axis) for k in sources};wz=sum(x['candidate']['axis_rmse_rad'][axis]<x['zero']['axis_rmse_rad'][axis] for x in rows);wins={k:sum(x['candidate']['axis_rmse_rad'][axis]<x[k]['axis_rmse_rad'][axis] for x in rows) for k in sources};ok=c<z and wz>=.70*n and (all(c<values[k] and wins[k]>=.60*n for k in sources) if axis=='right_distal' else all(c<=1.05*values[k] for k in sources));axes[axis]={'candidate':c,**values,'zero':z,'wins_vs_zero':wz,**{'wins_vs_'+k:wins[k] for k in sources},'cases':n,'passed':ok}
 combined={k:pooled(rows,k) for k in ('candidate',*sources,'zero')};total=sum(x['frames'] for x in rows)
 for name in ('shuffled','static','closed'):combined[name]=float(np.sqrt(sum(x['frames']*x['controls'][name]['rmse_rad']**2 for x in rows)/total))
 def safeguard(field,vals):
  out=[]
  for val in vals:
   rr=[x for x in rows if x['view'][field]==val];aa={}
   for axis in AXES:c=pooled(rr,'candidate',axis);z=pooled(rr,'zero',axis);w=sum(x['candidate']['axis_rmse_rad'][axis]<x['zero']['axis_rmse_rad'][axis] for x in rr);aa[axis]={'candidate':c,'zero':z,'wins':w,'cases':len(rr),'passed':c<z and w>=.70*len(rr)}
   out.append({'value':val,'axes':aa,'passed':all(x['passed'] for x in aa.values())})
  return out
 body=safeguard('body_x',(3.82,4.18));camera=safeguard('camera_z',(.36,.56));low=[x for x in rows if x['view']['body_x']==3.82];lr={'candidate':pooled(low,'candidate','right_distal'),**{k:pooled(low,k,'right_distal') for k in sources},'zero':pooled(low,'zero','right_distal'),'wins_vs_zero':sum(x['candidate']['axis_rmse_rad']['right_distal']<x['zero']['axis_rmse_rad']['right_distal'] for x in low),**{'wins_vs_'+k:sum(x['candidate']['axis_rmse_rad']['right_distal']<x[k]['axis_rmse_rad']['right_distal'] for x in low) for k in sources},'cases':len(low),'required_vs_zero':int(np.ceil(.75*len(low))),'required_vs_each_source':int(np.ceil(.60*len(low)))};lr['passed']=lr['candidate']<min(lr[k] for k in (*sources,'zero')) and lr['wins_vs_zero']>=lr['required_vs_zero'] and all(lr['wins_vs_'+k]>=lr['required_vs_each_source'] for k in sources);body[0]['axes']['right_distal']['passed']&=lr['passed'];body[0]['passed']=all(x['passed'] for x in body[0]['axes'].values())
 corners=[];need=2 if fixture else 7
 for corner in ([m.geometry_corners()[i] for i in(0,2,4,6)] if fixture else m.geometry_corners()):
  rr=[x for x in rows if x['corner_id']==corner['corner_id']];aa={}
  for axis in AXES:c=pooled(rr,'candidate',axis);z=pooled(rr,'zero',axis);w=sum(x['candidate']['axis_rmse_rad'][axis]<x['zero']['axis_rmse_rad'][axis] for x in rr);aa[axis]={'candidate':c,'zero':z,'wins':w,'cases':len(rr),'passed':c<z and w>=need}
  corners.append({'corner_id':corner['corner_id'],'view':corner['view'],'axes':aa,'passed':all(x['passed'] for x in aa.values())})
 required=4 if fixture else 12;p={'axes':axes,'combined':combined,'body_x_safeguards':body,'camera_z_safeguards':camera,'corner_results':corners,'corners_passed':sum(x['passed'] for x in corners),'corners_required':required,'lower_x_right_distal_comparator':lr};p['passed']=all(x['passed'] for x in axes.values()) and combined['candidate']<min(combined[k] for k in (*sources,'zero','shuffled','static','closed')) and all(x['passed'] for x in body+camera) and p['corners_passed']>=required;return p

def fit_variant(stats,right_distal_ridge):
 n=stats['n']
 if n<2:raise ValueError('Недостаточно данных для обучения.')
 mean=stats['sx']/n;scale=np.sqrt(np.maximum(stats['sx2']/n-mean*mean,0));scale[scale<1e-6]=1.;intercept=stats['sy']/n
 cov=(stats['sxx']/n-np.outer(mean,mean))/np.outer(scale,scale);rhs=(stats['sxy']/n-np.outer(mean,intercept))/scale[:,None];weights=np.empty((576,6));ridge=dict(m.RIDGE);ridge['right_distal']=float(right_distal_ridge)
 for j,axis in enumerate(AXES):weights[:,j]=np.linalg.solve(cov+ridge[axis]*np.eye(576),rhs[:,j])
 model={'mean':mean,'scale':scale,'intercept':intercept,'weights':weights}
 if any(not np.isfinite(x).all() for x in model.values()):raise ValueError('Variant содержит неконечные значения.')
 return model

def development_key(decision,index):
 rd=decision['axes']['right_distal'];lr=decision['lower_x_right_distal_comparator'];c=decision['combined']
 core=(rd['candidate']<rd['source84v'],rd['wins_vs_source84v']>=int(np.ceil(.60*rd['cases'])),lr['candidate']<lr['source84v'],lr['wins_vs_source84v']>=lr['required_vs_each_source'],c['candidate']<c['source84v'])
 normalized_wins=rd['wins_vs_source84v']/rd['cases']+lr['wins_vs_source84v']/lr['cases'];normalized_error=rd['candidate']/rd['source84v']+lr['candidate']/lr['source84v']+c['candidate']/c['source84v']
 return (int(decision['passed']),sum(core),normalized_wins,-normalized_error,-index)

def evaluate(folder,state,saved,elapsed,proto,ev,stim,base,large):
 folder=Path(folder);out=folder/'result'
 if out.exists():m.verify_result(out,saved,state);return out
 train,tests=proto.split_from_sources(state['sources'],stim)
 if len(tests)!=20 or [x['id'] for x in tests]!=list(range(1,21)):raise ValueError('Нужны ровно20 последовательных development/final holdouts.')
 def frozen(name):
  with np.load(io.BytesIO(state['sources'][name]),allow_pickle=False) as z:return ev.checked_model({k:z[k] for k in z.files})
 s84v=frozen('source84v_model.npz');s84=frozen('source84s_model.npz');s84r=frozen('source84r_model.npz')
 ridge_models={value:ev.checked_model(fit_variant(state['stats'],value)) for value in (.175,.35,.7,1.4)};specs={x['name']:dict(x) for x in saved['variants']}
 def predict_model(mod,x):return (x-mod['mean'])/mod['scale']@mod['weights']+mod['intercept']
 def predict_variant(name,x):
  spec=specs[name];new=predict_model(ridge_models[spec['right_distal_ridge']],x);old=predict_model(s84v,x);return np.clip(spec['new_weight']*new+(1-spec['new_weight'])*old,-np.pi*55/180,np.pi*55/180)
 scene=m.VisibleForelegGroomingScene(proto.load('multivariant84z_engine','38_two_flies_observation.py'));accepted,recs=m.sampled_records(folder/'study.sqlite3',len(train));audit=m.overlap_sample_broad(tests,recs,128);test_by_ident={}
 for item,overlap in zip(tests,audit['tests']):
  ident=420+item['id'];test_by_ident[ident]=(item,overlap)
 corners=[m.geometry_corners()[i] for i in(0,2,4,6)] if saved['mode']=='fixture' else m.geometry_corners()
 def render_group(ids,names,seed):
  grouped={name:[] for name in names}
  for ident in ids:
   item,overlap=test_by_ident[ident];full=item['angles_deg']*np.pi/180;truth=full[2:]
   for corner in corners:
    cid=corner['corner_id'];images=scene.render(full,view=corner['view']);x=m.edge_history(images);vp=np.clip(predict_model(s84v,x),-np.pi*55/180,np.pi*55/180);sp=np.clip(predict_model(s84,x),-np.pi*55/180,np.pi*55/180);rp=np.clip(predict_model(s84r,x),-np.pi*55/180,np.pi*55/180);_,vr=m.compress_replay(vp);_,sr=m.compress_replay(sp);_,rr=m.compress_replay(rp);rng=np.random.default_rng(np.random.SeedSequence([seed,ident,cid]));control_x={name:m.edge_history(img) for name,img in {'shuffled':images[rng.permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)}.items()}
    for name in names:
     cp=predict_variant(name,x);coeff,replay=m.compress_replay(cp);controls={}
     for control,q in control_x.items():_,moved=m.compress_replay(predict_variant(name,q));controls[control]=m.replay_metrics(truth,moved)
     digest=sha(np.asarray(coeff,dtype='<f8').tobytes());row={'test_id':ident,'corner_id':cid,'frames':len(truth),'view':corner['view'],'candidate':m.replay_metrics(truth,replay),'source84v':m.replay_metrics(truth,vr),'source84s':m.replay_metrics(truth,sr),'source84r':m.replay_metrics(truth,rr),'zero':m.replay_metrics(truth,np.zeros_like(truth)),'controls':controls,'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':True,'state_sha256_before_delay':digest,'state_sha256_after_delay':digest,'diagnostics':{'rgb_sha256':sha(images.tobytes()),'unique_rgb_frames':len({z.tobytes() for z in images}),'changed_rgb_values':int(np.count_nonzero(images[1:]!=images[:-1])),'candidate_feature_max_std':float(np.max(np.std(x,0))),'candidate_clipped_fraction':float(np.mean(np.abs(cp)>=np.pi*55/180))},'overlap_under_0_001_deg':overlap['under_0_001_deg'],'overlap_under_1_deg':overlap['under_1_deg'],'overlap_under_5_deg':overlap['under_5_deg']};grouped[name].append(row)
   print(f'Проверено движение {ident} на {len(corners)} corners для {len(names)} variant(s).',flush=True)
  return grouped
 dev_ids=list(range(421,431));final_ids=list(range(431,441));variant_order=[x['name'] for x in saved['variants']];development_rows=render_group(dev_ids,variant_order,843600);development={name:primary_decision(rows,saved['mode']=='fixture') for name,rows in development_rows.items()};keys={name:development_key(development[name],i) for i,name in enumerate(variant_order)};selected=max(variant_order,key=lambda name:keys[name]);final_rows=render_group(final_ids,[selected],843700)[selected];primary=primary_decision(final_rows,saved['mode']=='fixture')
 temp=folder/('evaluation_incomplete_'+uuid.uuid4().hex);temp.mkdir();variants_dir=temp/'variants';variants_dir.mkdir()
 for value,mod in ridge_models.items():np.savez_compressed(variants_dir/f'ridge_{int(round(value*10000)):04d}.npz',**mod)
 spec=specs[selected];new_model=ridge_models[spec['right_distal_ridge']];np.savez_compressed(temp/'model_selected.npz',selected_variant=np.array(selected),new_weight=np.array(spec['new_weight']),right_distal_ridge=np.array(spec['right_distal_ridge']),**{'new_'+k:v for k,v in new_model.items()},**{'source84v_'+k:v for k,v in s84v.items()});(temp/'source84v_model.npz').write_bytes(state['sources']['source84v_model.npz']);(temp/'source84s_model.npz').write_bytes(state['sources']['source84s_model.npz']);(temp/'source84r_model.npz').write_bytes(state['sources']['source84r_model.npz'])
 for name,rows in development_rows.items():
  for row in rows:
   td=temp/'development'/name/f'test_{row["test_id"]:03d}'/f'corner_{row["corner_id"]:02d}';td.mkdir(parents=True);save(td/'metrics.json',row)
 for row in final_rows:
  td=temp/f'test_{row["test_id"]:03d}'/f'corner_{row["corner_id"]:02d}';td.mkdir(parents=True);save(td/'metrics.json',row);save(td/'internal_state.json',{'coefficients_sha256':row['state_sha256_before_delay'],'delay_s':.5,'updates_during_delay':0})
 report={'schema':'multivariant-ridge-ensemble-result-v1','status':'fixture_completed' if saved['mode']=='fixture' else 'completed','protocol_mode':saved['mode'],'completion_basis':'committed_candidate_count','wall_diagnostic_seconds':elapsed,'candidates':state['next_id'],'accepted_candidates':accepted,'training_frames':state['stats']['n'],'source84v_model_sha256':saved['source84v_model_sha256'],'source84s_model_sha256':saved['source84s_model_sha256'],'source84r_model_sha256':saved['source84r_model_sha256'],'selected_model_sha256':file_sha(temp/'model_selected.npz'),'selected_variant':selected,'development':{'motions':dev_ids,'selection_keys':{name:list(keys[name]) for name in variant_order},'decisions':development},'primary':primary,'audit':{'accepted_total':accepted,'audited_count':audit['audited_count'],'is_exhaustive':audit['audited_count']==accepted,'sample_ids':audit['sample_ids']},'tests':final_rows,'development_tests':development_rows,'limitations':['Six variants are selected only on development motions421-430; primary uses untouched motions431-440.','Frozen84V,84S,84R comparators; motions321-420 are disclosed and excluded.','Synthetic supervised reconstruction; no actuators, closed loop, biological brain or mirror-neuron evidence.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 84Z: MULTIVARIANT RIDGE ENSEMBLE\n\nВыбран: '+selected+'\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');verify_pins(proto,saved);psha=sha(json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode());save(temp/'complete.json',{'protocol_sha256':psha,'candidates':state['next_id'],'files':m.output_manifest(temp)});temp.rename(out);m.verify_result(out,saved,state);return out
def migrate_evaluation_recovery(dbpath,proto):
 """One-time recovery of the completed-training DB made by the original84Z evaluator.

 Only script_sha256 changes after every other protocol field and the evaluation-stage
 checkpoint are verified. Training data, variants, selection and holdouts stay frozen.
 """
 uri=Path(dbpath).resolve().as_uri()+'?mode=rw'
 with sqlite3.connect(uri,uri=True,timeout=30) as db:
  meta=dict(db.execute('SELECT key,value FROM metadata'));saved=json.loads(meta.get('protocol','{}'))
  old_script_sha=saved.get('script_sha256')
  if old_script_sha not in RECOVERABLE_SCRIPT_SHAS:return False
  text=json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
  if meta.get('protocol')!=text or meta.get('protocol_sha256')!=sha(text.encode('utf8')):raise ValueError('Старый protocol повреждён; recovery запрещён.')
  phase=db.execute('SELECT stage,training_seconds FROM run_phase WHERE id=1').fetchone();state=db.execute('SELECT next_id FROM state WHERE id=1').fetchone();count=db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]
  if phase is None or phase[0]!='evaluation' or state is None or state[0]!=saved.get('target_candidates') or count!=state[0]:raise ValueError('Recovery разрешён только после полного training перед evaluation.')
  expected=protocol(saved['source_sha256'],saved['labels'],saved.get('fixture_limit'),proto,saved['source84r_model_sha256'],saved['quick_edit_action']);expected['visual_preflight']=m.visual_preflight(proto)
  left=dict(saved);right=dict(expected);left.pop('script_sha256',None);right.pop('script_sha256',None)
  if left!=right:raise ValueError('Научный protocol отличается; автоматический recovery запрещён.')
  new_text=json.dumps(expected,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False);db.execute('BEGIN IMMEDIATE');row=db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()
  if row is None or row[0]!=text:raise ValueError('Protocol изменился во время recovery.')
  db.execute("UPDATE metadata SET value=? WHERE key='protocol'",(new_text,));db.execute("UPDATE metadata SET value=? WHERE key='protocol_sha256'",(sha(new_text.encode('utf8')),));db.commit()
 log=Path(dbpath).parent/'evaluation-recovery.json';save(log,{'schema':'84z-evaluation-recovery-v1','old_script_sha256':old_script_sha,'recoverable_script_sha256':list(RECOVERABLE_SCRIPT_SHAS),'new_script_sha256':file_sha(__file__),'training_candidates':saved['target_candidates'],'scientific_protocol_changed':False,'reason':'use frozen sequential test index mapping without optional label fields'})
 print('Применён безопасный recovery evaluator84Z; training не повторяется.',flush=True);return True

def restore_resources(dbpath):
 global SELECTED_WORKERS,SELECTED_RESOURCE_MODE
 with sqlite3.connect(Path(dbpath).resolve().as_uri()+'?mode=ro',uri=True) as db:row=db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()
 if not row:raise ValueError('Не найден протокол ресурсов series84Z.')
 saved=json.loads(row[0]);workers=saved.get('workers');choice=saved.get('worker_choice')
 if type(workers)!=int or workers<1 or workers>64 or saved.get('batch')!=workers or choice not in ('2','4','6','max'):raise ValueError('Неверный закреплённый режим workers.')
 SELECTED_WORKERS=workers;SELECTED_RESOURCE_MODE=choice

def process_resources(folder,max_batches=None):
 proto,ev,pre,stim,ck,base,large=m.dependencies();folder=Path(folder).resolve();dbpath=folder/'study.sqlite3'
 if not dbpath.is_file():raise ValueError('В папке нет study.sqlite3 серии84Z.')
 restore_resources(dbpath);migrate_evaluation_recovery(dbpath,proto)
 console=m.disable_quick_edit()
 if os.name=='nt' and not console.get('disabled'):raise OSError('QuickEdit не отключён; продолжение запрещено.')
 large.job_guard()
 with large.RunLock(folder):
  saved,state,stage,seconds=m.saved_state(dbpath,proto,ck);target=saved['target_candidates'];fixture=saved['mode']=='fixture';workers=saved['workers'];batch=saved['batch']
  if type(workers)!=int or workers<1 or workers>max(64,os.cpu_count() or 1) or batch!=workers:raise ValueError('Неверная закреплённая конфигурация workers.')
  if max_batches is not None and (not fixture or type(max_batches)!=int or not 1<=max_batches<=4):raise ValueError('Предел партий только для fixture.')
  if stage=='completed':m.verify_result(folder/'result',saved,state);print('Серия уже завершена:',folder/'result');return
  m.free_check(large,folder,fixture);train,tests=proto.split_from_sources(state['sources'],stim);hold={x['motion_sha256'] for x in tests};done=state['next_id'];stats=state['stats'];prior=state['elapsed'];started=time.monotonic();batches=0
  print(f'Папка: {folder}\nСохранено {done}/{target}; workers{workers}, batch{batch}. Wall не завершает training.',flush=True)
  if stage=='training':
   with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(train,hold)) as pool:
    while True:
     pause=folder/'pause.request'
     if pause.exists():
      try:pause.unlink()
      except OSError:pass
      print('Пауза после сохранённой партии. Продолжите тем же BAT.',flush=True);return
     current=prior+time.monotonic()-started
     if done>=target:
      if done!=target or stats['n']<2:raise ValueError('Fixed target нарушен.')
      verify_pins(proto,saved);m.set_phase(dbpath,'training','evaluation',current);seconds=current;stage='evaluation';break
     if max_batches is not None and batches>=max_batches:print('Fixture остановлен после партии.',flush=True);return
     m.free_check(large,folder,fixture);end=min(done+batch,target);ids=list(range(done,end));t0=time.perf_counter();generated=list(pool.map(worker_generate,ids));records=[]
     for ident,(rec,x,y) in zip(ids,generated):
      expected,_=paired_candidate(ident)
      if rec['id']!=ident or rec['spec']!=expected or rec['motion_sha256']!=expected['sampled_motion_sha256']:raise ValueError('Candidate нарушил protocol.')
      rejected=rec['motion_sha256'] in hold
      if rejected!=(rec['status']=='rejected'):raise ValueError('Ошибка holdout block.')
      if not rejected:
       if x is None or y is None or x.shape!=(rec['frames'],576) or y.shape!=(rec['frames'],6):raise ValueError('Неверная worker партия.')
       base.update_stats(stats,x,y)
      elif x is not None or y is not None:raise ValueError('Rejected candidate передал frames.')
      if not np.isfinite(rec['worker_cpu_seconds']) or not np.isfinite(rec['worker_wall_seconds']):raise ValueError('Неверный worker timing.')
      records.append(rec)
     verify_pins(proto,saved);ck.commit_batch(dbpath,saved,done,records,stats,prior+time.monotonic()-started);batch_wall=time.perf_counter()-t0
     with sqlite3.connect(dbpath,timeout=30) as db:db.execute('PRAGMA synchronous=FULL');db.execute('INSERT INTO batch_timing VALUES (?,?,?,?,?,?)',(done,len(ids),batch_wall,sum(r['worker_cpu_seconds'] for r in records),max(r['worker_wall_seconds'] for r in records),datetime.utcnow().isoformat()+'Z'))
     done=end;batches+=1;print(f'Сохранено {done}/{target}; batch{len(ids)} wall {batch_wall:.2f}с; worker CPU {sum(r["worker_cpu_seconds"] for r in records):.2f}с.',flush=True)
  if stage=='evaluation':
   m.free_check(large,folder,fixture);state=ck.open_verified(dbpath,saved);print('Fixed count завершён. Evaluation.',flush=True);out=evaluate(folder,state,saved,seconds,proto,ev,stim,base,large);m.set_phase(dbpath,'evaluation','completed',seconds);print('Готово:',out,flush=True)
   if os.name=='nt':
    try:os.startfile(str(out))
    except OSError:pass

def worker_init(train,hold):BASE_WORKER_INIT(train,hold)
def worker_generate(ident):return BASE_WORKER_GENERATE(ident)
def candidate_probe(ident):
 spec,degrees=paired_candidate(ident);return spec['base_motion_id'],spec['paired_view_slot'],spec['view']['body_x'],spec['sampled_motion_sha256'],sha(np.asarray(degrees,dtype='<f8').tobytes())
def candidate_check():
 with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:rows=list(pool.map(candidate_probe,range(8)))
 for base in (0,1):
  group=rows[base*4:(base+1)*4];assert [x[1] for x in group]==[0,1,2,3] and [x[2] for x in group]==[3.82,3.82,4.18,4.18] and len({x[3] for x in group})==1 and len({x[4] for x in group})==1
 print('84Z spawn candidate check passed: two base motions with exact balanced84V four-view allocation.')

# Reuse the tested fixed-count lifecycle after replacing only preregistered hooks.
# Worker entry points stay in this executable module so Windows spawn can import them.
m.ROOT=ROOT;m.SOURCE84R_ROOT=SOURCE_ROOT;m.TARGET_CANDIDATES=TARGET;m.protocol=protocol;m.verify_pins=verify_pins;m.source_snapshot=source_snapshot;m.prepared_holdouts=prepared_holdouts;m.training_view=paired_view;m.broad_candidate=paired_candidate;m.evaluate=evaluate;m.worker_init=worker_init;m.worker_generate=worker_generate;m.process=process_resources

def choose():
 import tkinter as tk
 from tkinter import filedialog,simpledialog
 root=tk.Tk();root.title('Серия 84Z: multivariant ridge ensemble');root.geometry('670x190+180+140');root.resizable(False,False);root.attributes('-topmost',True);tk.Label(root,text='Model-development серия84Z.\n4096 новых движений ×4 balanced84V ракурса =16384 candidates.\nШесть вариантов выбираются на development; final blocking остаётся изолированным.',font=('Arial',11),justify='left',padx=20,pady=20).pack();root.update_idletasks();root.lift();root.focus_force();root.update()
 try:
  action=simpledialog.askinteger('Серия84Z','Введите номер:\n1: начать новую серию\n2: продолжить сохранённую серию\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
  if action is None:print('Выбор отменён.');return
  if action in (2,3):
   folder=filedialog.askdirectory(title='Выберите папку multivariant_ridge_ensemble_...',mustexist=True,initialdir=str(ROOT.resolve() if ROOT.exists() else Path.cwd()),parent=root)
   if not folder:print('Выбор отменён.');return
   root.withdraw();root.update();m.process(folder) if action==2 else m.request_pause(folder);return
  print('Открывается окно выбора завершённой папки series84V...',flush=True);source=filedialog.askdirectory(title='Серия84V: выберите завершённую series84V',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
  if not source:print('Выбор отменён.');return
  resource=simpledialog.askinteger('Ресурсы series84Z',f'Выберите workers:\n1: 2 workers\n2: 4 workers\n3: 6 workers\n4: МАКСИМУМ ({max(1,os.cpu_count() or 1)} workers; ресурсы для других программ не резервируются)',minvalue=1,maxvalue=4,parent=root)
  if resource is None:print('Выбор отменён.');return
  workers=set_resources('max' if resource==4 else {1:2,2:4,3:6}[resource])
  print('Выбрана source84V:',source,flush=True);print(f'Пререгистрация84Z: seed8433,4096 motions × exact84V 2 lower+2 upper; six variants; development421–430; untouched blocking431–440; workers{workers}.',flush=True);root.withdraw();root.update();folder=ROOT/('multivariant_ridge_ensemble_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);m.start(folder,source)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--choose',action='store_true');g.add_argument('--new');g.add_argument('--resume');g.add_argument('--pause');g.add_argument('--candidate-check',action='store_true',help=argparse.SUPPRESS);p.add_argument('--source84v');p.add_argument('--workers',choices=('2','4','6','max'),default='6');p.add_argument('--fixture-limit',type=int,help=argparse.SUPPRESS);p.add_argument('--batches',type=int,help=argparse.SUPPRESS);a=p.parse_args()
 if a.candidate_check:candidate_check()
 elif a.choose:choose()
 elif a.new:
  if not a.source84v:p.error('Нужна --source84v.')
  set_resources(a.workers);m.start(a.new,a.source84v,a.fixture_limit,a.batches)
 elif a.resume:m.process(a.resume,a.batches)
 else:m.request_pause(a.pause)
if __name__=='__main__':
 multiprocessing.freeze_support()
 try:main()
 except Exception as exc:print(f'ОШИБКА: {type(exc).__name__}: {exc}\nSource84V не изменялась; последняя committed партия сохранена.',file=sys.stderr,flush=True);sys.exit(1)
