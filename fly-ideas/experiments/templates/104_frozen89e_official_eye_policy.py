#!/usr/bin/env python3
"""Series104: frozen89E policy driven by official FlyGym observer-eye frames."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,math,os,sqlite3,threading,time,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER102=HERE/'102_frozen89e_flygym_replication.py';RUNNER102_SHA='16309bb094236e861fff6eeb1b4d24ce072d6f7ab55c8f88cd6f12e6d94d7a19'
RUNNER103=HERE/'103_flygym_interbody_vision_preflight.py';RUNNER103_SHA='33bc95e41032d1f6bc823d626c6ea8c2f80a7135e5c3b8254c656b8400823d11'
RESULT103=HERE.parent/'reports'/'flygym-interbody-vision-preflight-user-result.json';RESULT103_SHA='1a13fe460bfb7bfc0af70203465ba42b74ba0809d53672bdad0afb209c6184bf'
ROOT=Path('workspace/runs/ideas/i-observational/frozen89e-official-eye-policy');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');D_ROOT=Path('workspace/runs/ideas/i-observational/routing-margin-contact')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');CONDITIONS=('candidate','neutral_visual','reversed_visual','zero_state','shuffled_state','shared_lesion','open_loop')
def sha_bytes(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha_bytes(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load_module(name,path,expected):
 if file_sha(path)!=expected:raise ValueError(f'Закреплённый {path.name} изменился.')
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize():
 if file_sha(RESULT103)!=RESULT103_SHA:raise ValueError('Series103 genuine result изменён.')
 x=json.loads(RESULT103.read_text(encoding='utf8'))
 if x.get('status')!='completed' or x.get('primary',{}).get('passed') is not True or x.get('primary',{}).get('scientific_result') is not False:raise ValueError('Нужен exact Series103 vision preflight pass.')
 if x.get('protocol',{}).get('script_sha256')!=RUNNER103_SHA:raise ValueError('Series103 result не соответствует runner.')
 s102=load_module('series104_source102',RUNNER102,RUNNER102_SHA);s103=load_module('series104_source103',RUNNER103,RUNNER103_SHA);s102.authorize();return s102,s103,x
def motion_specs(m86):
 out=[];ident=903
 for rep in range(2):
  for ai,action in enumerate(ACTIONS):
   seed=104010+rep*10+ai;amp=(.75,.88)[rep];speed=(.84,1.08)[(rep+ai)%2];out.append({'role':'official_eye_policy','id':ident,'replicate':rep+1,'action':action,'seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 return out
def prepare(s102,source_folder,d_folder):
 s101=load_module('series104_source101',s102.RUNNER101,s102.RUNNER101_SHA);s89=s101.load89e();s89.authorize_d();md=s89.load_d();mc=md.load_c();m6=mc.load_b6();m5=m6.load_b5();m4=m5.load_b4();m3=m4.load_b3();m2=m3.load_b2();m=m2.load_b();m88=m.load88();m87=m88.load87();m86=m87.load86();frozen_path,d_summary,angle,identity,common,experts,selections,standard,standard_selections,temp=s89.load_frozen(d_folder,False);frozen_before=manifest(frozen_path);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,False)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:seen={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 seen|={x['motion_sha256'] for x in saved['labels']}|m86.disclosed_hashes()|m87.published86_hashes()|m88.authorize87()|m.authorize89()|m2.authorize_b()|m3.authorize_b2()|s89.authorize_d()
 for old in s89.specs(False):seen.add(stim.motion_hash(np.asarray(old['angles_deg'],float)))
 for old in s102.load101().motion_specs(m86,False):seen.add(stim.motion_hash(np.asarray(old['angles_deg'],float)))
 for old in s102.motion_specs(m86,False):seen.add(stim.motion_hash(np.asarray(old['angles_deg'],float)))
 items=[];desc=[]
 for x in motion_specs(m86):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series104 motion совпал с training/disclosed/Series101/102 motion.')
  item={**x,'motion_sha256':h};items.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'});seen.add(h)
 models={'md':md,'m3':m3,'m2':m2,'m':m,'b':b,'a':a,'bundle':bundle,'d_summary':d_summary,'angle':angle,'identity':identity,'temp':temp,'common':common,'experts':experts,'selections':selections,'standard':standard,'standard_selections':standard_selections,'s84v':s84v}
 guards=(before,frozen_before,frozen_path);return s101,models,items,desc,guards
def infer(models,images):
 x=models['b'].edge_history(images);shared=models['a'].predict_selected(models['bundle'],x);coeff,target=models['b'].compress_replay(shared);targets,probs=models['md'].controls_for(models['m3'],models['m2'],models['m'],models['b'],coeff,target,models['angle'],models['identity'],models['temp'],models['common'],float(models['d_summary']['model']['common_selected']['lambda']),models['experts'],models['selections'],models['standard'],models['standard_selections']);return coeff,{k:np.asarray(v,float) for k,v in targets.items()},np.asarray(probs,float)
def capture(s103,bridge,commands,progress,base,span,label):
 sim=bridge.sim;sim.reset();sim.step();commands=np.asarray(commands,float);frames=len(commands);desired=[]
 for k in (0,1):
  x=np.tile(bridge.neutral[k],(frames,1))
  if k==0:x[:,bridge.map_idx[k]]+=np.clip(commands,-.35,.35)
  desired.append(x)
 images=[];samples=[];steps=(frames-1)*round(s103.FRAME_DT/s103.DT)+1
 for n in range(steps):
  phase=n*s103.DT/s103.FRAME_DT;i=min(int(phase),frames-2);alpha=min(phase-i,1.)
  for k,name in enumerate(bridge.names):
   target=(1-alpha)*desired[k][i]+alpha*desired[k][i+1];vel=(desired[k][i+1]-desired[k][i])/s103.FRAME_DT;q=sim.get_joint_angles(name)[bridge.q_idx[k]];dq=sim.get_joint_velocities(name)[bridge.q_idx[k]];u=np.clip(s103.KP*(target-q)+s103.KD*(vel-dq),-s103.TORQUE_LIMIT,s103.TORQUE_LIMIT);sim.set_actuator_inputs(name,bridge.ActuatorType.MOTOR,u);sim.set_leg_adhesion_states(name,np.ones(6,dtype=bool))
  sim.step()
  if n%round(s103.FRAME_DT/s103.DT)==0:
   images.append(s103.resize_eye_pair(sim.get_raw_vision('observer')));q=sim.get_joint_angles('demonstrator')[bridge.q_idx[0]];samples.append(q[bridge.map_idx[0]]-bridge.neutral[0][bridge.map_idx[0]]);progress(label,base+span*len(images)/frames,len(images),frames)
 return np.asarray(images),np.asarray(samples)
def rollout(s103,bridge,policy,truth,open_loop=False):
 sim=bridge.sim;sim.reset();sim.step();frames=len(policy);desired=[]
 for k,traj in enumerate((truth,policy)):
  x=np.tile(bridge.neutral[k],(frames,1));x[:,bridge.map_idx[k]]+=np.clip(np.asarray(traj),-.35,.35);desired.append(x)
 steps=(frames-1)*round(s103.FRAME_DT/s103.DT)+1;sample=[];contacts=[];forces=[];zs=[];finite=True;saturated=0;energy=0.
 for n in range(steps):
  phase=n*s103.DT/s103.FRAME_DT;i=min(int(phase),frames-2);alpha=min(phase-i,1.)
  for k,name in enumerate(bridge.names):
   target=(1-alpha)*desired[k][i]+alpha*desired[k][i+1];vel=(desired[k][i+1]-desired[k][i])/s103.FRAME_DT;q=sim.get_joint_angles(name)[bridge.q_idx[k]];dq=sim.get_joint_velocities(name)[bridge.q_idx[k]];raw=s103.KP*((target-bridge.neutral[k]) if(open_loop and k==1)else(target-q))+s103.KD*(vel if(open_loop and k==1)else(vel-dq));saturated+=int(np.any(np.abs(raw)>s103.TORQUE_LIMIT));u=np.clip(raw,-s103.TORQUE_LIMIT,s103.TORQUE_LIMIT);sim.set_actuator_inputs(name,bridge.ActuatorType.MOTOR,u);sim.set_leg_adhesion_states(name,np.ones(6,dtype=bool));energy+=float(np.sum(np.abs(u*dq))*s103.DT)
  sim.step();finite&=bool(np.isfinite(sim.mj_data.qpos).all()and np.isfinite(sim.mj_data.qvel).all())
  if n%round(s103.FRAME_DT/s103.DT)==0:
   q=sim.get_joint_angles('observer')[bridge.q_idx[1]];sample.append(q[bridge.map_idx[1]]-bridge.neutral[1][bridge.map_idx[1]]);found,*_=sim.get_ground_contact_info('observer');contacts.append(int(np.count_nonzero(found>.5)));forces.append(float(np.linalg.norm(sim.get_actuator_forces('observer',bridge.ActuatorType.MOTOR))));body_names=[x.name for x in bridge.flies[1].get_bodysegs_order()];zs.append(float(sim.get_body_positions('observer')[body_names.index('c_thorax'),2]))
 sample=np.asarray(sample);truth=np.clip(np.asarray(truth),-.35,.35);policy=np.clip(np.asarray(policy),-.35,.35);return {'finite':finite,'tracking_rmse_rad':float(np.sqrt(np.mean((sample-policy)**2))),'truth_rmse_rad':float(np.sqrt(np.mean((sample-truth)**2))),'contact_frame_fraction':float(np.mean(np.asarray(contacts)>0)),'mean_contact_legs':float(np.mean(contacts)),'max_actuator_force_norm':max(forces),'minimum_thorax_z_mm':min(zs),'maximum_thorax_z_mm':max(zs),'energy_abs_work':energy,'torque_saturation_fraction':saturated/(steps*2),'sample':sample}
def decide(rows,fixture=False):
 n=len(rows);state_req=n if fixture else math.ceil(2*n/3);open_req=n if fixture else math.ceil(5*n/6);candidate=[r['controls']['candidate'] for r in rows];safe=lambda x:x['finite']and x['minimum_thorax_z_mm']>=.15 and x['maximum_thorax_z_mm']<=2.5 and x['contact_frame_fraction']>0;wins={k:sum(r['controls']['candidate']['truth_rmse_rad']<r['controls'][k]['truth_rmse_rad'] for r in rows) for k in CONDITIONS if k!='candidate'};correct=sum(r['predicted_action']==r['action'] for r in rows);tracking=float(np.mean([x['tracking_rmse_rad'] for x in candidate]));distinct=all(r['target_hashes']['candidate']!=r['target_hashes'][k] for r in rows for k in ('neutral_visual','reversed_visual','zero_state','shuffled_state','shared_lesion'));passed=sum(safe(x) for x in candidate)==n and tracking<=.20 and correct>=state_req and all(wins[k]>=state_req for k in ('neutral_visual','reversed_visual','zero_state','shuffled_state')) and wins['open_loop']>=open_req and distinct;return {'cases':n,'required_control_wins':state_req,'required_open_loop_wins':open_req,'required_action_correct':state_req,'candidate_safe_cases':sum(safe(x) for x in candidate),'candidate_mean_tracking_rmse_rad':tracking,'action_correct':correct,'candidate_truth_wins':wins,'visual_and_state_controls_distinct':distinct,'passed':passed,'scientific_result':False}
def fixture_rows():
 rows=[]
 for i,a in enumerate(ACTIONS):
  controls={k:{'finite':True,'tracking_rmse_rad':.05,'truth_rmse_rad':.08 if k=='candidate' else .2,'contact_frame_fraction':1.,'mean_contact_legs':3.,'max_actuator_force_norm':8.,'minimum_thorax_z_mm':.8,'maximum_thorax_z_mm':1.2,'energy_abs_work':1.,'torque_saturation_fraction':0.} for k in CONDITIONS};rows.append({'id':903+i,'action':a,'predicted_action':a,'state_sha256':'c'+str(i),'target_hashes':{k:k+str(i) for k in CONDITIONS},'controls':controls});rows[-1]['target_hashes']['open_loop']=rows[-1]['target_hashes']['candidate']
 return rows
def run(source,d_folder,output_root=ROOT,fixture=False,progress=lambda *x:None):
 s102,s103,go103=authorize();root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('frozen89e_official_eye_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);temp=folder/'result_incomplete';temp.mkdir(parents=True);progress('Проверяются frozen/vision prerequisites',.01,0,1)
 if fixture:desc=[];rows=fixture_rows();trace=[];primary=decide(rows,True)
 else:
  s101,models,items,desc,guards=prepare(s102,source,d_folder);bridge=s103.Bridge();rows=[];trace=[]
  try:
   neutral_frames=len(np.asarray(items[0]['angles_deg']));neutral_images,_=capture(s103,bridge,np.zeros((neutral_frames,6)),progress,.03,.07,'Official neutral-visual control');neutral_coeff,neutral_targets,_=infer(models,neutral_images)
   cases=[]
   for ci,item in enumerate(items):
    commands=np.asarray(item['angles_deg'],float)*np.pi/180;images,actual=capture(s103,bridge,commands,progress,.10+.30*ci/len(items),.30/len(items),f'Official-eye capture {ci+1}/{len(items)}');coeff,targets,probs=infer(models,images);rev_coeff,rev_targets,_=infer(models,images[::-1].copy());cases.append({'item':item,'truth':actual[2:],'coeff':coeff,'targets':{'candidate':targets['candidate'],'neutral_visual':neutral_targets['candidate'],'reversed_visual':rev_targets['candidate'],'zero_state':targets['zero_state'],'shuffled_state':targets['shuffled_state'],'shared_lesion':targets['shared_lesion'],'open_loop':targets['candidate']},'probs':probs,'neutral_coeff':neutral_coeff,'reversed_coeff':rev_coeff})
   total=len(cases)*len(CONDITIONS);done=0
   for c in cases:
    controls={}
    for name in CONDITIONS:
     metric=rollout(s103,bridge,c['targets'][name],c['truth'],name=='open_loop');sample=metric.pop('sample');controls[name]=metric
     for fi,angles in enumerate(sample):trace.append({'id':c['item']['id'],'action':c['item']['action'],'condition':name,'frame':fi,**{s103.MAPPED_DOF[j]:float(angles[j]) for j in range(6)}})
     done+=1;progress('Official-eye policy physical controls',.40+.56*done/total,done,total)
    hashes={k:sha_bytes(np.asarray(v,dtype='<f8').tobytes()) for k,v in c['targets'].items()};rows.append({'id':c['item']['id'],'action':c['item']['action'],'predicted_action':ACTIONS[int(np.argmax(c['probs']))],'state_sha256':sha_bytes(np.asarray(c['coeff'],dtype='<f8').tobytes()),'neutral_visual_state_sha256':sha_bytes(np.asarray(c['neutral_coeff'],dtype='<f8').tobytes()),'reversed_visual_state_sha256':sha_bytes(np.asarray(c['reversed_coeff'],dtype='<f8').tobytes()),'target_hashes':hashes,'controls':controls})
   before,frozen_before,frozen_path=guards
   if before!={p:file_sha(p) for p in before}or frozen_before!=manifest(frozen_path):raise ValueError('Frozen sources изменились.')
   primary=decide(rows,False)
  finally:bridge.close()
 protocol={'schema':'frozen89e-official-eye-policy-v1','mode':'fixture'if fixture else'full','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'series103_result_sha256':RESULT103_SHA,'training_allowed':False,'selection_allowed':False,'post_result_tuning_allowed':False,'motions':desc,'official_visual_input':'observer add_vision/get_raw_vision; bilinear resize to 2x64x96; unchanged frozen edge_history','controls':list(CONDITIONS),'primary_rule':'all candidate safe/contact; mean tracking<=0.20rad; action correct and wins vs neutral/reversed/zero/shuffled>=4/6; wins vs open_loop>=5/6; visual/state targets distinct'};save(folder/'protocol.json',protocol);report={'schema':'frozen89e-official-eye-policy-result-v1','status':'fixture_completed'if fixture else'completed','protocol':protocol,'primary':primary,'tests':rows,'limitations':['First frozen policy test on official observer-eye images; still an engineering adapter result.','No training, model selection, FlyVis, connectome mapping, living animal, or biological claim.','Official fisheye RGB is resized to the frozen external-camera tensor shape; distribution equivalence is not assumed.']};save(temp/'summary.json',report)
 if trace:
  with(temp/'physical_trace.csv').open('w',newline='',encoding='utf8')as f:w=csv.DictWriter(f,fieldnames=list(trace[0]));w.writeheader();w.writerows(trace)
 (temp/'ИТОГ.txt').write_text('SERIES104: FROZEN89E ON OFFICIAL EYE IMAGES\n\nPrimary: '+('ВЫПОЛНЕН'if primary['passed']else'НЕ ВЫПОЛНЕН')+'.\nEngineering policy bridge, не биологический результат.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,1,1);return folder/'result'
def gui():
 import brian2
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Series104: frozen89E on official eyes');root.geometry('780x430+140+70');root.attributes('-topmost',True);status=tk.StringVar(value='Выберите frozen sources и запустите official-eye policy bridge');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series104: frozen89E получает official FlyGym eye images',font=('Arial',13,'bold'),pady=14).pack();tk.Label(root,text='6 новых motions. Official observer eyes → frozen policy → official MOTOR body.\nОбучения, выбора модели и настройки после результата нет.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=600,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Выбрать result89D и source84Z, затем запустить',padx=18,pady=8);button.pack(pady=12)
 def update(text,fraction,done,total):
  def apply():
   p=round(fraction*100,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.02:elapsed=time.time()-start[0];eta.set(f'Прошло {elapsed/60:.1f} мин · осталось примерно {elapsed*(1-fraction)/fraction/60:.1f} мин')
  root.after(0,apply)
 def begin():
  d=filedialog.askdirectory(title='Выберите завершённую result-папку series89D',mustexist=True,initialdir=str(D_ROOT.resolve()if D_ROOT.exists()else Path.cwd()),parent=root)
  if not d:return
  source=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve()if SOURCE_ROOT.exists()else Path.cwd()),parent=root)
  if not source:return
  button.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(source,d,progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series104','Official-eye policy test завершён.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-104.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series104',f'{exc}\n\nОтчёт открыт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--source84z');p.add_argument('--result89d');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args()
 if a.gui:gui()
 elif a.fixture:print(run('.','.',a.output_root,True))
 elif a.source84z and a.result89d:print(run(a.source84z,a.result89d,a.output_root,False))
 else:p.error('Нужен --gui, --fixture или source84z+result89d.')
if __name__=='__main__':main()
