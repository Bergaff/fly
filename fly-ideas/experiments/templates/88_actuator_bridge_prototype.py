#!/usr/bin/env python3
"""Series88: preregistered bounded closed-loop actuator bridge prototype."""
from __future__ import annotations
import argparse,concurrent.futures,hashlib,importlib.util,json,math,multiprocessing,os,sqlite3,sys,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;RUNNER87=HERE/'87_causal_shared_unit_lesions.py';RUNNER87_SHA='105f0c26e0b9fd5e0fa9a6060af48fe4fa900da09ff5e906116da1d12d7caa54';GO87=HERE.parent/'reports'/'causal-shared-unit-lesions-user-summary-extract.json';GO87_SHA='f30a118a72e450cbe76024c74ff32764b8f545f41b3ecc6b3957f9fd0a6faf6f'
ROOT=Path('workspace/runs/ideas/i-observational/actuator-bridge-prototype');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble');ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal');LIMIT=np.deg2rad(55.);DT=.004;FRAME_DT=.04;TORQUE_LIMIT=.35
WORK87=None

def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load87():
 if file_sha(RUNNER87)!=RUNNER87_SHA:raise ValueError('Закреплённый runner87 изменился.')
 s=importlib.util.spec_from_file_location('series88_source',RUNNER87);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def authorize87():
 if file_sha(GO87)!=GO87_SHA:raise ValueError('Published series87 extract изменён.')
 d=json.loads(GO87.read_text(encoding='utf8'))
 if not d.get('primary',{}).get('passed') or d.get('source_file_sha256')!='033a2fc502c99bfca0b17adee53386bfb9f7fdab989b14a04d6394f2e1c27fa6':raise ValueError('Series87 causal go не подтверждён.')
 motions=d.get('protocol',{}).get('motions',[])
 if [x.get('id') for x in motions]!=list(range(498,537)):raise ValueError('Series87 disclosed motions изменены.')
 return {x['motion_sha256'] for x in motions}
def specs(fixture=False):
 m87=load87();m86=m87.load86();out=[];ident=537
 for rep in range(10):
  for ai,action in enumerate(ACTIONS):
   amp=(.78,.9,1.)[(rep+2*ai)%3];speed=(.72,1.,1.28)[(rep+ai)%3];seed=880200+10*rep+ai;out.append({'role':'evaluation','id':ident,'replicate':rep+1,'action':action,'actuator_seed':seed,'amplitude':amp,'speed':speed,'angles_deg':m86.motif(action,seed,amp,speed)});ident+=1
 return [x for x in out if x['id'] in (537,538,539)] if fixture else out
def prepare(stim,labels,training_hashes,fixture=False):
 m87=load87();m86=m87.load86();seen={x['motion_sha256'] for x in labels}|set(training_hashes)|m86.disclosed_hashes()|m87.published86_hashes()|authorize87();out=[];desc=[]
 for x in specs(fixture):
  h=stim.motion_hash(np.asarray(x['angles_deg'],float))
  if h in seen:raise ValueError('Series88 motion совпал с training/disclosed motion.')
  seen.add(h);item={**x,'motion_sha256':h};out.append(item);desc.append({k:v for k,v in item.items() if k!='angles_deg'})
 return out,desc
def contact_sensor(q):
 q=np.asarray(q);return np.exp(-((q[[0,3]]-q[[1,4]])/.42)**2-((q[[2,5]]-.35)/.55)**2)
def actuator_rollout(target,seed,closed_loop=True):
 """Track state-decoded targets with bounded torque; no truth/RGB/teacher argument exists."""
 target=np.asarray(target,float)
 if target.ndim!=2 or target.shape[1]!=6 or len(target)<2 or not np.isfinite(target).all():raise ValueError('Неверная target policy.')
 target=np.clip(target,-LIMIT,LIMIT);steps=(len(target)-1)*round(FRAME_DT/DT)+1;q=np.zeros(6);dq=np.zeros(6);tilt=np.zeros(2);dtilt=np.zeros(2);rng=np.random.default_rng(seed);q+=rng.normal(0,.004,6);qs=[];torques=[];contacts=[];tilts=[];zs=[];saturated=0
 for n in range(steps):
  phase=n*DT/FRAME_DT;i=min(int(phase),len(target)-2);a=min(phase-i,1.);des=(1-a)*target[i]+a*target[i+1];vel=(target[i+1]-target[i])/FRAME_DT;actual_contact=contact_sensor(q);desired_contact=contact_sensor(des)
  if closed_loop:u=1.65*(des-q)+.22*(vel-dq);u[[2,5]]+=.045*(desired_contact-actual_contact)
  else:u=.055*vel+.20*des
  saturated+=int(np.any(np.abs(u)>TORQUE_LIMIT));u=np.clip(u,-TORQUE_LIMIT,TORQUE_LIMIT);ddq=(u-.045*dq)/.018;dq+=DT*ddq;q+=DT*dq
  hit=np.abs(q)>LIMIT
  if np.any(hit):q=np.clip(q,-LIMIT,LIMIT);dq[hit]*=-.08
  reaction=np.array([u[0]+u[1]+u[2]-u[3]-u[4]-u[5],u[0]-u[1]-u[3]+u[4]])
  dtilt+=DT*(.025*reaction-2.8*tilt-.9*dtilt);tilt+=DT*dtilt;z=.40-.018*np.linalg.norm(tilt)-.002*np.sum(np.abs(q))
  qs.append(q.copy());torques.append(u.copy());contacts.append(actual_contact);tilts.append(tilt.copy());zs.append(z)
 idx=np.arange(len(target))*round(FRAME_DT/DT);sample=np.asarray(qs)[idx];tau=np.asarray(torques);energy=float(np.sum(np.abs(tau*np.asarray([np.zeros(6),*np.diff(qs,axis=0)/DT])))*DT);rmse=float(np.sqrt(np.mean((sample-target)**2)));limit_hits=int(np.sum(np.abs(sample)>=LIMIT-1e-9));nan_count=int(np.size(sample)-np.isfinite(sample).sum());return {'trace':sample,'tracking_rmse_rad':rmse,'completion_ratio':float(np.mean(np.linalg.norm(sample,axis=1)>.08)),'limit_violations':limit_hits,'nan_count':nan_count,'energy_abs_work':energy,'torque_saturation_fraction':saturated/steps,'max_abs_torque':float(np.max(np.abs(tau))),'max_tilt_rad':float(np.max(np.abs(tilts))),'minimum_body_z':float(np.min(zs)),'mean_contact':float(np.mean(contacts)),'proprioception_feedback':closed_loop,'contact_feedback':closed_loop}
def worker_init(bundle,s84v):
 global WORK87
 WORK87=load87();WORK87.worker_init(bundle,s84v)
def worker_task(arg):
 item,corner=arg;row=WORK87.worker_task((item,corner));b=WORK87.WORKER86.WORK['b'];shared=np.asarray(row.pop('_shared'));truth=np.asarray(row.pop('_execution'));row.pop('_private',None);coeff,target=b.compress_replay(shared);digest=sha(np.asarray(coeff,dtype='<f8').tobytes());closed=actuator_rollout(target,8800000+item['id']*100+corner['corner_id'],True);opened=actuator_rollout(target,8800000+item['id']*100+corner['corner_id'],False);closed_trace=closed.pop('trace');open_trace=opened.pop('trace');row['actuator']={'closed_loop':closed,'open_loop':opened,'truth_rmse_rad':float(np.sqrt(np.mean((closed_trace-truth)**2))),'target_policy_sha256':digest,'state_coefficients':72,'teacher_access_during_rollout':False,'rgb_access_during_rollout':False,'framewise_observer_buffer_access_during_rollout':False};return row
def decision(rows,fixture=False):
 c=[r['actuator']['closed_loop'] for r in rows];o=[r['actuator']['open_loop'] for r in rows];cases=len(rows);finite=all(x['nan_count']==0 for x in c);limits=all(x['limit_violations']==0 for x in c);stable=all(x['max_tilt_rad']<=.25 and x['minimum_body_z']>=.30 for x in c);bounded=all(x['max_abs_torque']<=TORQUE_LIMIT+1e-12 and x['energy_abs_work']<=4. for x in c);tracking=float(np.mean([x['tracking_rmse_rad'] for x in c]));open_tracking=float(np.mean([x['tracking_rmse_rad'] for x in o]));wins=sum(x['tracking_rmse_rad']<y['tracking_rmse_rad'] for x,y in zip(c,o));completion=sum(x['completion_ratio']>=.65 for x in c);required=cases if fixture else math.ceil(.90*cases);passed=finite and limits and stable and bounded and tracking<=.12 and tracking<.80*open_tracking and wins>=required and completion>=required;return {'cases':cases,'finite_passed':finite,'joint_limits_passed':limits,'support_stability_passed':stable,'bounded_torque_energy_passed':bounded,'closed_loop_tracking_rmse_rad':tracking,'open_loop_tracking_rmse_rad':open_tracking,'closed_loop_better_wins':wins,'completed_bouts':completion,'required_cases':required,'passed':passed}
def run(source_folder,workers,output_root=ROOT,fixture=False):
 authorize87();m87=load87();m86=m87.load86();s85=m86.load85();workers,count=s85.worker_choice(workers);print('1/5 Проверяются causal go87 и frozen84Z...',flush=True);m86,s85,a,z,b,proto,stim,saved,state,summary,paths,tracked,before,bundle,s84v=m87.source(source_folder,fixture)
 with sqlite3.connect(Path(source_folder,'study.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:training_hashes={x[0] for x in db.execute("SELECT motion_sha256 FROM candidates WHERE status='accepted'")}
 items,desc=prepare(stim,saved['labels'],training_hashes,fixture);corners=[b.geometry_corners()[i] for i in (0,4,8,12)] if fixture else b.geometry_corners();tasks=[(x,c) for x in items for c in corners];protocol={'schema':'actuator-bridge-prototype-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner87_sha256':RUNNER87_SHA,'series87_extract_sha256':GO87_SHA,'selected_model_sha256':file_sha(paths[1]),'training_allowed':False,'motions':desc,'geometry_corners':len(corners),'workers':count,'worker_choice':str(workers),'actuator':{'dt_s':DT,'frame_dt_s':FRAME_DT,'joint_limit_rad':LIMIT,'torque_limit':TORQUE_LIMIT,'proprioception_feedback':True,'contact_feedback':True,'surrogate_support_dynamics':True},'forbidden_rollout_access':['teacher trajectory','observation RGB','framewise observer prediction buffer'],'primary_rule':'all finite/limits/support/torque-energy; mean closed tracking<=0.12rad and <0.80 open; >=90% cases closed wins and completion>=0.65'};root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('actuator_bridge_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);print(f'2/5 Запускается {len(tasks)} visual+actuator cases, workers={count}.',flush=True);rows=[]
 with concurrent.futures.ProcessPoolExecutor(max_workers=count,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(bundle,s84v)) as pool:
  for n,row in enumerate(pool.map(worker_task,tasks),1):rows.append(row);print(f'  Cases {n}/{len(tasks)}',flush=True) if n%len(corners)==0 else None
 for row in rows:
  td=temp/f'test_{row["id"]:03d}'/f'corner_{row["corner_id"]:02d}';td.mkdir(parents=True);save(td/'metrics.json',row)
 print('3/5 Проверяются stability, limits, NaN, energy и closed-loop gate...',flush=True);primary=decision(rows,fixture);report={'schema':'actuator-bridge-prototype-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':primary,'tests':rows,'source84z_primary':summary['primary'],'limitations':['Reduced six-joint actuator/support surrogate, not FlyGym, muscles or a complete free-standing fly body.','Target policy reconstructs the observed synthetic action; no novel action invention.','Contact is an engineered two-channel geometric proxy, not MuJoCo collision force.','Frozen supervised synthetic visual decoder; no natural vision or biological neurons.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 88: ACTUATOR BRIDGE PROTOTYPE\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 if manifest(folder/'result')!=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))['files']:raise ValueError('Manifest series88 повреждён.')
 print('4/5 Source84Z неизменна.',flush=True);print('5/5 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия88: actuator bridge');root.geometry('720x360+180+100');root.attributes('-topmost',True);choice=tk.StringVar(value='6');tk.Label(root,text='Серия88: bounded actuators и closed-loop feedback\n30 новых motions ×16 views; frozen model84Z.',font=('Arial',11),padx=20,pady=18).pack();tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
 for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
 selected={'go':False};tk.Button(root,text='Выбрать завершённую папку84Z и запустить',command=lambda:(selected.update(go=True),root.quit()),padx=18,pady=8).pack(pady=18);root.mainloop()
 if not selected['go']:root.destroy();return
 folder=filedialog.askdirectory(title='Выберите завершённую production series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
 if not folder:root.destroy();return
 root.withdraw();root.update();result=run(folder,choice.get());
 if os.name=='nt':os.startfile(str(result))
 messagebox.showinfo('Серия88 завершена','Папка результата открыта. Передайте summary.json.',parent=root);root.destroy()
def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-88.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('СЕРИЯ 88: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
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
