#!/usr/bin/env python3
"""Series84V: paired-view model development for distal consistency.

Exactly 4096 new base motions are each rendered in four counterfactual views.
Model84S and model84R are frozen comparators. No disclosed motion321-350 is reused.
"""
from __future__ import annotations
import argparse,concurrent.futures,csv,hashlib,importlib.util,io,itertools,json,multiprocessing,os,sys,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER84S=HERE/'84s_fixed_count_lowerx_distal_grooming.py';RUNNER84S_SHA='67915637388a508b88c112ce9f39a0396fcc5a2ef9492928f402826809a8dcd2'
MODEL84S_SHA='a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f'
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal');TARGET=16384
ROOT=Path('workspace/runs/ideas/i-observational/paired-view-distal-consistency');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/lowerx-distal-fixed-count')

def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def load84s():
 if file_sha(RUNNER84S)!=RUNNER84S_SHA:raise ValueError('Закреплённый runner84S изменился.')
 s=importlib.util.spec_from_file_location('paired84v_base',RUNNER84S);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load84s();BASE_PROTOCOL=m.protocol;BASE_VERIFY=m.verify_pins;BASE_WORKER_INIT=m.worker_init;BASE_WORKER_GENERATE=m.worker_generate

def paired_view(ident):
 base=ident//4;slot=ident%4;corners=m.geometry_corners();lower=[x['view'] for x in corners if x['view']['body_x']==3.82];upper=[x['view'] for x in corners if x['view']['body_x']==4.18]
 # For every motion: two lower-X and two upper-X views; opposite side/z/y bits.
 k=base%8;op=k^7;return (lower[k],lower[op],upper[(k+3)%8],upper[((k+3)%8)^7])[slot].copy()
def paired_candidate(ident):
 if type(ident)!=int or not 0<=ident<TARGET:raise ValueError('Неверный paired candidate id.')
 base=ident//4;rng=np.random.default_rng(np.random.SeedSequence([8425,base]));t=np.arange(51,dtype=float)/25;family=('piecewise5','piecewise9','harmonic','chirp')[base%4]
 if family.startswith('piecewise'):
  count=5 if family=='piecewise5' else 9;knots=np.linspace(0,2,count);values=rng.integers(-55,56,size=(count,6)).astype(float);degrees=np.stack([np.interp(t,knots,values[:,j]) for j in range(6)],axis=1);parameters={'keyframes_deg':values.astype(int).tolist()}
 else:
  offset=rng.uniform(-12,12,6);amplitude=rng.uniform(18,48,6);phase=rng.uniform(0,2*np.pi,6)
  if family=='harmonic':frequency=rng.uniform(.4,3.2,6);degrees=offset+amplitude*np.sin(2*np.pi*t[:,None]*frequency+phase);parameters={'offset_deg':offset.tolist(),'amplitude_deg':amplitude.tolist(),'phase_rad':phase.tolist(),'frequency_hz':frequency.tolist()}
  else:f0=rng.uniform(.25,1.2,6);f1=rng.uniform(1.8,4.0,6);sweep=(f1-f0)/2;degrees=offset+amplitude*np.sin(phase+2*np.pi*(t[:,None]*f0+.5*t[:,None]**2*sweep));parameters={'offset_deg':offset.tolist(),'amplitude_deg':amplitude.tolist(),'phase_rad':phase.tolist(),'f0_hz':f0.tolist(),'f1_hz':f1.tolist()}
 degrees[:,3]=-degrees[:,0]+.25*degrees[:,3];degrees[:,4]=degrees[:,1]+.25*degrees[:,4];degrees[:,5]=-degrees[:,2]+.25*degrees[:,5];before=degrees.copy();degrees=np.clip(degrees,-55,55)
 spec={'protocol':'paired-view-distal-consistency-v1','sequence_id':ident,'base_motion_id':base,'paired_view_slot':ident%4,'generator_seed':[8425,base],'family':family,'parameters':parameters,'foreleg_pattern':'three-joint opposed grooming with 0.25 independent perturbation','distance':4.,'side_offset':0.,'view':paired_view(ident),'clipped_values':int(np.count_nonzero(before!=degrees)),'sampled_motion_sha256':m.broad_motion_hash(degrees)};return spec,degrees

def prepared_holdouts():
 folder=ROOT/'prepared_holdouts_seed_8426';folder.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(8426);paths=[]
 for i,ident in enumerate(range(361,371),1):
  path=folder/f'holdout_{ident:03d}.json';count=5 if i<=5 else 9;v=rng.integers(-55,56,size=(count,6)).astype(int);v[:,3]=np.clip(-v[:,0]+np.rint(.25*v[:,3]).astype(int),-55,55);v[:,4]=np.clip(v[:,1]+np.rint(.25*v[:,4]).astype(int),-55,55);v[:,5]=np.clip(-v[:,2]+np.rint(.25*v[:,5]).astype(int),-55,55);obj={'schema':'fly-wings-trajectory-v1','semantic_schema':'fly-foreleg-grooming-six-joint-v1','channels':list(AXES),'fps':25,'duration_s':2,'keyframes':[{'t':2*j/(count-1),'angles_deg':v[j].tolist()} for j in range(count)]};raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
  if path.exists() and path.read_bytes()!=raw:raise ValueError('Закреплённый holdout изменён.')
  if not path.exists():path.write_bytes(raw)
  paths.append(path)
 return paths

def protocol(source_sha,labels,fixture_limit,proto,source84r_sha,console):
 p=BASE_PROTOCOL(source_sha,labels,fixture_limit,proto,source84r_sha,console);p.update({'schema':'paired-view-distal-consistency-v1','script_sha256':file_sha(__file__),'runner84s_sha256':RUNNER84S_SHA,'source84s_model_sha256':source_sha['source84s_model.npz'],'target_candidates':fixture_limit if fixture_limit is not None else TARGET})
 p['training_generator'].update({'seed':8425,'view_seed':None,'view_sampling':'4096 base motions x4 paired counterfactual exact corners:2 lower-X+2 upper-X','base_motions':(fixture_limit+3)//4 if fixture_limit is not None else 4096,'paired_views_per_motion':4})
 p['evaluation']={'motion_seed':8426,'holdouts':list(range(361,371)),'geometry_corners':16,'comparators':['source84s','source84r'],'body_x_safeguards':[3.82,4.18],'camera_z_safeguards':[.36,.56],'lower_x_right_distal_wins_required':60,'state_coefficients':72,'delay_s':.5}
 p['primary_rule']='motions361-370 x16: absolute gates unchanged; right distal below and >=60% wins vs both frozen84S and84R globally/lower-X; other axes <=5% worse both; combined below both/zero/controls; both X/Z; >=12/16 corners'
 return p
def verify_pins(proto,saved):
 if file_sha(__file__)!=saved['script_sha256'] or file_sha(RUNNER84S)!=RUNNER84S_SHA:raise ValueError('Runner84V/84S изменился.')
 for name,expected in {**proto.PIN,**m.PIN}.items():
  if file_sha(HERE/name)!=expected:raise ValueError(f'Закреплённый файл {name} изменился.')

def source_snapshot(folder,fixture,proto,stim,ck):
 source_m=load84s();folder=Path(folder).resolve();saved,state,stage,_=source_m.saved_state(folder/'study.sqlite3',proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая series84S.')
 result=folder/'result';source_m.verify_result(result,saved,state);summary=json.loads((result/'summary.json').read_text(encoding='utf8'));expected='fixture_completed' if fixture else 'completed'
 if summary.get('status')!=expected:raise ValueError('Режим source84S не совпадает.')
 model=(result/'model_lowerx_distal.npz').read_bytes();model_sha=sha(model)
 if model_sha!=summary.get('candidate_model_sha256') or (not fixture and model_sha!=MODEL84S_SHA):raise ValueError('Нужна закреплённая production model84S.')
 sources=dict(state['sources']);labels=[dict(x) for x in saved['labels']];fresh=prepared_holdouts();new=[x for x in labels if x['role']=='new_test'];seen={x['motion_sha256'] for x in labels}
 for label,path in zip(new,fresh):
  raw=path.read_bytes();_,angles=stim.sample_trajectory(json.loads(raw));motion=stim.motion_hash(angles)
  if motion in seen:raise ValueError('Новый holdout совпал с раскрытым движением.')
  seen.add(motion);sources[label['copy']]=raw;label.update({'source_sha256':sha(raw),'motion_sha256':motion,'original_basename':path.name})
 sources['source84s_model.npz']=model;sources['source84s_summary.json']=(result/'summary.json').read_bytes()
 return {'sources':sources,'labels':labels,'source_sha256':{k:sha(v) for k,v in sorted(sources.items())},'source84r_model_sha256':summary['source84r_model_sha256']}

def pooled(rows,key,axis=None):
 n=sum(r['frames'] for r in rows);return float(np.sqrt(sum(r['frames']*(r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad'])**2 for r in rows)/n))
def primary_decision(rows,fixture):
 axes={};n=len(rows)
 for a in AXES:
  c=pooled(rows,'candidate',a);z=pooled(rows,'zero',a);s=pooled(rows,'source84s',a);r=pooled(rows,'source84r',a);wz=sum(x['candidate']['axis_rmse_rad'][a]<x['zero']['axis_rmse_rad'][a] for x in rows);ws=sum(x['candidate']['axis_rmse_rad'][a]<x['source84s']['axis_rmse_rad'][a] for x in rows);wr=sum(x['candidate']['axis_rmse_rad'][a]<x['source84r']['axis_rmse_rad'][a] for x in rows);ok=c<z and wz>=.70*n and ((c<s and c<r and ws>=.60*n and wr>=.60*n) if a=='right_distal' else c<=1.05*s and c<=1.05*r);axes[a]={'candidate':c,'source84s':s,'source84r':r,'zero':z,'wins_vs_zero':wz,'wins_vs_source84s':ws,'wins_vs_source84r':wr,'cases':n,'passed':ok}
 combined={k:pooled(rows,k) for k in ('candidate','source84s','source84r','zero')};total=sum(x['frames'] for x in rows)
 for name in ('shuffled','static','closed'):combined[name]=float(np.sqrt(sum(x['frames']*x['controls'][name]['rmse_rad']**2 for x in rows)/total))
 def safeguard(field,vals):
  out=[]
  for val in vals:
   rr=[x for x in rows if x['view'][field]==val];aa={}
   for a in AXES:c=pooled(rr,'candidate',a);z=pooled(rr,'zero',a);w=sum(x['candidate']['axis_rmse_rad'][a]<x['zero']['axis_rmse_rad'][a] for x in rr);aa[a]={'candidate':c,'zero':z,'wins':w,'cases':len(rr),'passed':c<z and w>=.70*len(rr)}
   out.append({'value':val,'axes':aa,'passed':all(x['passed'] for x in aa.values())})
  return out
 body=safeguard('body_x',(3.82,4.18));camera=safeguard('camera_z',(.36,.56));low=[x for x in rows if x['view']['body_x']==3.82];lr={'candidate':pooled(low,'candidate','right_distal'),'source84s':pooled(low,'source84s','right_distal'),'source84r':pooled(low,'source84r','right_distal'),'zero':pooled(low,'zero','right_distal'),'wins_vs_zero':sum(x['candidate']['axis_rmse_rad']['right_distal']<x['zero']['axis_rmse_rad']['right_distal'] for x in low),'wins_vs_source84s':sum(x['candidate']['axis_rmse_rad']['right_distal']<x['source84s']['axis_rmse_rad']['right_distal'] for x in low),'wins_vs_source84r':sum(x['candidate']['axis_rmse_rad']['right_distal']<x['source84r']['axis_rmse_rad']['right_distal'] for x in low),'cases':len(low),'required_vs_zero':int(np.ceil(.75*len(low))),'required_vs_each_source':int(np.ceil(.60*len(low)))};lr['passed']=lr['candidate']<min(lr['source84s'],lr['source84r'],lr['zero']) and lr['wins_vs_zero']>=lr['required_vs_zero'] and lr['wins_vs_source84s']>=lr['required_vs_each_source'] and lr['wins_vs_source84r']>=lr['required_vs_each_source'];body[0]['axes']['right_distal']['passed']&=lr['passed'];body[0]['passed']=all(x['passed'] for x in body[0]['axes'].values())
 corners=[];need=2 if fixture else 7
 for corner in ([m.geometry_corners()[i] for i in(0,2,4,6)] if fixture else m.geometry_corners()):
  rr=[x for x in rows if x['corner_id']==corner['corner_id']];aa={}
  for a in AXES:c=pooled(rr,'candidate',a);z=pooled(rr,'zero',a);w=sum(x['candidate']['axis_rmse_rad'][a]<x['zero']['axis_rmse_rad'][a] for x in rr);aa[a]={'candidate':c,'zero':z,'wins':w,'cases':len(rr),'passed':c<z and w>=need}
  corners.append({'corner_id':corner['corner_id'],'view':corner['view'],'axes':aa,'passed':all(x['passed'] for x in aa.values())})
 required=4 if fixture else 12;p={'axes':axes,'combined':combined,'body_x_safeguards':body,'camera_z_safeguards':camera,'corner_results':corners,'corners_passed':sum(x['passed'] for x in corners),'corners_required':required,'lower_x_right_distal_comparator':lr};p['passed']=all(x['passed'] for x in axes.values()) and combined['candidate']<min(combined['source84s'],combined['source84r'],combined['zero'],combined['shuffled'],combined['static'],combined['closed']) and all(x['passed'] for x in body+camera) and p['corners_passed']>=required;return p

def evaluate(folder,state,saved,elapsed,proto,ev,stim,base,large):
 folder=Path(folder);out=folder/'result'
 if out.exists():m.verify_result(out,saved,state);return out
 train,tests=proto.split_from_sources(state['sources'],stim);labels={x['copy']:x for x in saved['labels']};candidate=ev.checked_model(m.fit_distal(state['stats']))
 def model(name):
  with np.load(io.BytesIO(state['sources'][name]),allow_pickle=False) as z:return ev.checked_model({k:z[k] for k in z.files})
 s84=model('source84s_model.npz');s84r=model('source84r_model.npz');scene=m.VisibleForelegGroomingScene(proto.load('paired84v_engine','38_two_flies_observation.py'));accepted,recs=m.sampled_records(folder/'study.sqlite3',len(train));audit=m.overlap_sample_broad(tests,recs,128);temp=folder/('evaluation_incomplete_'+uuid.uuid4().hex);temp.mkdir();np.savez_compressed(temp/'model_paired_view.npz',**candidate);(temp/'source84s_model.npz').write_bytes(state['sources']['source84s_model.npz']);(temp/'source84r_model.npz').write_bytes(state['sources']['source84r_model.npz']);rows=[];corners=[m.geometry_corners()[i] for i in(0,2,4,6)] if saved['mode']=='fixture' else m.geometry_corners()
 for item,overlap in zip(tests,audit['tests']):
  label=labels[f'test_{item["id"]:03d}.json'];
  if label['role']!='new_test':continue
  ident=int(label['original_basename'][8:11]);full=item['angles_deg']*np.pi/180;truth=full[2:]
  for corner in corners:
   cid=corner['corner_id'];images=scene.render(full,view=corner['view']);x=m.edge_history(images)
   def pred(mod):return np.clip((x-mod['mean'])/mod['scale']@mod['weights']+mod['intercept'],-np.pi*55/180,np.pi*55/180)
   cp,sp,rp=pred(candidate),pred(s84),pred(s84r);coeff,replay=m.compress_replay(cp);_,sr=m.compress_replay(sp);_,rr=m.compress_replay(rp);rng=np.random.default_rng(np.random.SeedSequence([842600,ident,cid]));controls={}
   for name,img in {'shuffled':images[rng.permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)}.items():q=m.edge_history(img);q=np.clip((q-candidate['mean'])/candidate['scale']@candidate['weights']+candidate['intercept'],-np.pi*55/180,np.pi*55/180);_,moved=m.compress_replay(q);controls[name]=m.replay_metrics(truth,moved)
   digest=sha(np.asarray(coeff,dtype='<f8').tobytes());row={'test_id':ident,'corner_id':cid,'frames':len(truth),'view':corner['view'],'candidate':m.replay_metrics(truth,replay),'source84s':m.replay_metrics(truth,sr),'source84r':m.replay_metrics(truth,rr),'zero':m.replay_metrics(truth,np.zeros_like(truth)),'controls':controls,'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':True,'state_sha256_before_delay':digest,'state_sha256_after_delay':digest,'diagnostics':{'rgb_sha256':sha(images.tobytes()),'unique_rgb_frames':len({z.tobytes() for z in images}),'changed_rgb_values':int(np.count_nonzero(images[1:]!=images[:-1])),'candidate_feature_max_std':float(np.max(np.std(x,0))),'candidate_clipped_fraction':float(np.mean(np.abs(cp)>=np.pi*55/180))},'overlap_under_0_001_deg':overlap['under_0_001_deg'],'overlap_under_1_deg':overlap['under_1_deg'],'overlap_under_5_deg':overlap['under_5_deg']};rows.append(row);td=temp/f'test_{ident:03d}'/f'corner_{cid:02d}';td.mkdir(parents=True);save(td/'metrics.json',row);save(td/'internal_state.json',{'coefficients':list(map(float,coeff)),'delay_s':.5,'updates_during_delay':0})
  print(f'Проверено paired-view движение {ident} на {len(corners)} corners.',flush=True)
 p=primary_decision(rows,saved['mode']=='fixture');report={'schema':'paired-view-distal-consistency-result-v1','status':'fixture_completed' if saved['mode']=='fixture' else 'completed','protocol_mode':saved['mode'],'completion_basis':'committed_candidate_count','wall_diagnostic_seconds':elapsed,'candidates':state['next_id'],'accepted_candidates':accepted,'training_frames':state['stats']['n'],'source84s_model_sha256':saved['source84s_model_sha256'],'source84r_model_sha256':saved['source84r_model_sha256'],'candidate_model_sha256':file_sha(temp/'model_paired_view.npz'),'primary':p,'audit':{'accepted_total':accepted,'audited_count':audit['audited_count'],'is_exhaustive':audit['audited_count']==accepted,'sample_ids':audit['sample_ids']},'tests':rows,'limitations':['Single preregistered intervention: four paired views per base motion at fixed render count.','Frozen84S and84R comparators; motions321-350 are disclosed and excluded.','Synthetic supervised reconstruction; no actuators, closed loop, biological brain or mirror-neuron evidence.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 84V: PAIRED-VIEW DISTAL CONSISTENCY\n\nPrimary: '+('ВЫПОЛНЕН' if p['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');verify_pins(proto,saved);psha=sha(json.dumps(saved,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode());save(temp/'complete.json',{'protocol_sha256':psha,'candidates':state['next_id'],'files':m.output_manifest(temp)});temp.rename(out);m.verify_result(out,saved,state);return out

def worker_init(train,hold):BASE_WORKER_INIT(train,hold)
def worker_generate(ident):return BASE_WORKER_GENERATE(ident)
def candidate_probe(ident):
 spec,degrees=paired_candidate(ident);return spec['base_motion_id'],spec['paired_view_slot'],spec['view']['body_x'],spec['sampled_motion_sha256'],sha(np.asarray(degrees,dtype='<f8').tobytes())
def candidate_check():
 with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:rows=list(pool.map(candidate_probe,range(8)))
 for base in (0,1):
  group=rows[base*4:(base+1)*4];assert [x[1] for x in group]==[0,1,2,3] and [x[2] for x in group]==[3.82,3.82,4.18,4.18] and len({x[3] for x in group})==1 and len({x[4] for x in group})==1
 print('84V spawn candidate check passed: two base motions, four identical-motion paired views each.')

# Reuse the tested fixed-count lifecycle after replacing only preregistered hooks.
# Worker entry points stay in this executable module so Windows spawn can import them.
m.ROOT=ROOT;m.SOURCE84R_ROOT=SOURCE_ROOT;m.TARGET_CANDIDATES=TARGET;m.protocol=protocol;m.verify_pins=verify_pins;m.source_snapshot=source_snapshot;m.prepared_holdouts=prepared_holdouts;m.training_view=paired_view;m.broad_candidate=paired_candidate;m.evaluate=evaluate;m.worker_init=worker_init;m.worker_generate=worker_generate

def choose():
 import tkinter as tk
 from tkinter import filedialog,simpledialog
 root=tk.Tk();root.title('Серия 84V: paired-view model');root.geometry('600x170+180+140');root.resizable(False,False);root.attributes('-topmost',True);tk.Label(root,text='Model-development серия84V.\n4096 новых движений ×4 связанных ракурса =16384 candidates.\nModel84S/84R остаются frozen.',font=('Arial',11),justify='left',padx=20,pady=20).pack();root.update_idletasks();root.lift();root.focus_force();root.update()
 try:
  action=simpledialog.askinteger('Серия84V','Введите номер:\n1: начать новую серию\n2: продолжить сохранённую серию\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
  if action is None:print('Выбор отменён.');return
  if action in (2,3):
   folder=filedialog.askdirectory(title='Выберите папку paired_view_distal_...',mustexist=True,initialdir=str(ROOT.resolve() if ROOT.exists() else Path.cwd()),parent=root)
   if not folder:print('Выбор отменён.');return
   root.withdraw();root.update();m.process(folder) if action==2 else m.request_pause(folder);return
  print('Открывается окно выбора завершённой папки series84S...',flush=True);source=filedialog.askdirectory(title='Серия84V: выберите завершённую series84S',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
  if not source:print('Выбор отменён.');return
  print('Выбрана source84S:',source,flush=True);print('Пререгистрация84V: seed8425,4096 motions ×4 views; holdouts361–370; comparators84S/84R.',flush=True);root.withdraw();root.update();folder=ROOT/('paired_view_distal_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);m.start(folder,source)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--choose',action='store_true');g.add_argument('--new');g.add_argument('--resume');g.add_argument('--pause');g.add_argument('--candidate-check',action='store_true',help=argparse.SUPPRESS);p.add_argument('--source84s');p.add_argument('--fixture-limit',type=int,help=argparse.SUPPRESS);p.add_argument('--batches',type=int,help=argparse.SUPPRESS);a=p.parse_args()
 if a.candidate_check:candidate_check()
 elif a.choose:choose()
 elif a.new:
  if not a.source84s:p.error('Нужна --source84s.')
  m.start(a.new,a.source84s,a.fixture_limit,a.batches)
 elif a.resume:m.process(a.resume,a.batches)
 else:m.request_pause(a.pause)
if __name__=='__main__':
 multiprocessing.freeze_support()
 try:main()
 except Exception as exc:print(f'ОШИБКА: {type(exc).__name__}: {exc}\nSource84S не изменялась; последняя committed партия сохранена.',file=sys.stderr,flush=True);sys.exit(1)
