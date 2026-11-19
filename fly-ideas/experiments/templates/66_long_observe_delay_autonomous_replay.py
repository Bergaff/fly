#!/usr/bin/env python3
"""Series 66: observation -> internal state -> delay -> autonomous replay."""
from __future__ import annotations
import argparse,concurrent.futures,csv
from datetime import datetime,timezone
import hashlib,importlib.util,io,json,math,multiprocessing,os
from pathlib import Path
import shutil,sqlite3,sys,time,uuid,zipfile
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER59=HERE/'59_long_user_wing_learning.py';RUNNER59_SHA='5c700f4c72f3614c245ab34f2b7bf7f8469e3114cb46568556157a2b99e5ddcf'
ROOT=Path('workspace/runs/ideas/i-observational/observe-delay-replay');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/wing-user-long')
AXES=('left_x','left_y','left_z','right_x','right_y','right_z');OBS_UNITS=24;OBS_BASIS=10;OUT_BASIS=12;XDIM=OBS_UNITS*OBS_BASIS;YDIM=len(AXES)*OUT_BASIS
RIDGE=1.0;DELAY_S=.5;MIN_RAM=4*1024**3;MIN_DISK=2*1024**3
# Series 60-62 reused series-59 tests; series 63-64 introduced these six holdouts; series 65 had none.
PRIOR_HOLDOUT_MOTIONS=frozenset({
 '59c3778e3055e6bb18d09736541dcb4fd0a9b27fef2f0c52c365886398fc779d',
 '90b29ef78833b0a84c9241b30a179af2e374c8e5b7a42abf13936c68a2b4a5b8',
 '7b38ade07720d23b99f73c3ace7c16feb0983b9ce8346eb058b2a19e57e0921a',
 '7b088a0712dbe5852ac27588d8a9fa0f3d29722ded5bbd6f5a0cd6a3ea272f8a',
 '06bcb616a991cf2f31e3e02f53cd74f828fc5b4e093dd496d6ec72f28d07a091',
 '3fbf12ef88f7b9458caa27727d1b20021f807df934059b31142716304137f987',
})
_rng=np.random.default_rng(6601);PROJECTION=_rng.normal(0,1/math.sqrt(192),(192,OBS_UNITS))

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def load_runner():
 if file_sha(RUNNER59)!=RUNNER59_SHA:raise ValueError('Закреплённый скрипт серии 59 изменился.')
 spec=importlib.util.spec_from_file_location('autonomous_runner59',RUNNER59);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def source_state(folder):
 runner=load_runner();proto,ev,pre,stim,ck,base,large=runner.dependencies();folder=Path(folder).resolve();db=folder/'study.sqlite3';saved,state,stage,seconds=runner.saved_state(db,proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая серия 59.')
 runner.verify_result(folder/'result',saved,state);train,tests=proto.split_from_sources(state['sources'],stim)
 return runner,proto,ev,stim,large,folder,db,saved,state,train,tests

def basis(n,k):
 if n<k:raise ValueError('Движение слишком короткое для закреплённого базиса.')
 phase=(np.arange(n)+.5)/n;return np.column_stack([np.ones(n)]+[np.cos(np.pi*j*phase) for j in range(1,k)])
def frame_activity(images):
 images=np.asarray(images)
 if images.dtype!=np.uint8 or images.ndim!=5 or images.shape[1:]!=(2,32,48,3):raise ValueError('Некорректные изображения наблюдения.')
 lum=images.astype(np.float64).mean(axis=-1)/255;v=lum.reshape(len(images),2,8,4,12,4).mean(axis=(3,5)).reshape(len(images),192)
 return np.tanh((v-.5)@PROJECTION)
def encode(images):
 a=frame_activity(images);b=basis(len(a),OBS_BASIS);return ((b[:,:,None]*a[:,None,:]).mean(axis=0)).reshape(-1),a
def target_coeff(angles):
 y=np.asarray(angles,dtype=float);b=basis(len(y),OUT_BASIS);return np.linalg.lstsq(b,y,rcond=None)[0].T.reshape(-1)
def decode(coeff,n):return basis(n,OUT_BASIS)@np.asarray(coeff).reshape(6,OUT_BASIS).T

def empty_stats():return {'n':0,'sx':np.zeros(XDIM),'sx2':np.zeros(XDIM),'sy':np.zeros(YDIM),'sxy':np.zeros((XDIM,YDIM)),'sxx':np.zeros((XDIM,XDIM))}
def update_stats(s,x,y):
 x=np.asarray(x);y=np.asarray(y)
 if x.shape!=(XDIM,) or y.shape!=(YDIM,) or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Некорректный эпизод обучения.')
 s['n']+=1;s['sx']+=x;s['sx2']+=x*x;s['sy']+=y;s['sxy']+=np.outer(x,y);s['sxx']+=np.outer(x,x)
def pack_stats(s):
 mem=io.BytesIO();np.savez_compressed(mem,**s);return mem.getvalue()
def unpack_stats(blob,digest):
 if sha(blob)!=digest or len(blob)>32*1024*1024:raise ValueError('SHA статистик не совпадает.')
 with zipfile.ZipFile(io.BytesIO(blob)) as z:
  if sum(x.file_size for x in z.infolist())>32*1024*1024:raise ValueError('Архив статистик слишком велик.')
 with np.load(io.BytesIO(blob),allow_pickle=False) as z:s={k:(int(z[k]) if k=='n' else np.array(z[k],dtype=float,copy=True)) for k in z.files}
 if set(s)!={'n','sx','sx2','sy','sxy','sxx'} or s['sx'].shape!=(XDIM,) or s['sy'].shape!=(YDIM,) or s['sxx'].shape!=(XDIM,XDIM) or s['sxy'].shape!=(XDIM,YDIM):raise ValueError('Некорректные статистики.')
 return s
def fit(s):
 n=s['n'];mean=s['sx']/n;scale=np.sqrt(np.maximum(s['sx2']/n-mean*mean,0));scale[scale<1e-6]=1;intercept=s['sy']/n
 cov=(s['sxx']/n-np.outer(mean,mean))/np.outer(scale,scale);rhs=(s['sxy']/n-np.outer(mean,intercept))/scale[:,None];weights=np.linalg.solve(cov+RIDGE*np.eye(XDIM),rhs)
 return {'mean':mean,'scale':scale,'intercept':intercept,'weights':weights}
def predict(model,x):return (np.asarray(x)-model['mean'])/model['scale']@model['weights']+model['intercept']

def freeze_holdouts(paths,stim,blocked):
 if len(paths)!=5:raise ValueError('Нужно ровно пять новых JSON.')
 out=[];seen=set(blocked)
 for i,p in enumerate(paths,1):
  p=Path(p)
  if not p.is_file() or p.stat().st_size>1024*1024:raise ValueError(f'Holdout {i} отсутствует или слишком велик.')
  raw=p.read_bytes();obj=json.loads(raw.decode('utf-8-sig'));t,y=stim.sample_trajectory(obj);motion=stim.motion_hash(y)
  if motion in seen:raise ValueError(f'Holdout {i} совпадает с прежним или другим движением.')
  seen.add(motion);out.append({'index':i,'raw':raw,'obj':obj,'times':t,'angles_deg':y,'source_sha256':sha(raw),'motion_sha256':motion,'basename':p.name})
 return out

def make_protocol(source,saved,state,items,limit):
 return {'schema':'observe-delay-autonomous-replay-v1','mode':'fixture' if limit else 'full','script_sha256':file_sha(__file__),'runner59_sha256':RUNNER59_SHA,'source_series59':str(source),'source_database_sha256':file_sha(Path(source)/'study.sqlite3'),'source_protocol_sha256':sha(canonical(saved).encode()),'source_candidates':state['next_id'],'fixture_limit':limit,'observer_units':OBS_UNITS,'observer_temporal_basis':OBS_BASIS,'internal_state_coefficients':YDIM,'output_temporal_basis':OUT_BASIS,'delay_s':DELAY_S,'ridge':RIDGE,'projection_seed':6601,'workers':2,'holdouts':[{'index':x['index'],'copy':f'input/holdout_{x["index"]:03d}.json','source_sha256':x['source_sha256'],'motion_sha256':x['motion_sha256'],'basename':x['basename']} for x in items],'primary_metric':'mean holdout autonomous normal-observation RMSE minus stationary-zero RMSE across all six axes','secondary_controls':['reversed observation','shuffled observation','static observation','closed observation'],'replay_access':'internal coefficient state and replay phase only; no images, teacher angles, or buffered predictions'}

def create(folder,protocol,items):
 folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir(exist_ok=False);(folder/'input').mkdir();db=folder/'study.sqlite3';blob=pack_stats(empty_stats());text=canonical(protocol)
 for x in items:(folder/'input'/f'holdout_{x["index"]:03d}.json').write_bytes(x['raw'])
 with sqlite3.connect(db) as c:
  c.execute('PRAGMA journal_mode=DELETE');c.execute('PRAGMA synchronous=FULL');c.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)');c.execute('CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),next_index INTEGER NOT NULL,elapsed REAL NOT NULL,stats BLOB NOT NULL,stats_sha256 TEXT NOT NULL,stage TEXT NOT NULL)');c.execute('CREATE TABLE episodes(position INTEGER PRIMARY KEY,candidate_id INTEGER UNIQUE NOT NULL,rgb_sha256 TEXT NOT NULL)');c.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','observe-delay-replay-checkpoint-v1'),('protocol',text),('protocol_sha256',sha(text.encode()))]);c.execute("INSERT INTO state VALUES(1,0,0,?,?, 'training')",(blob,sha(blob)))
 return db

def read_state(folder):
 folder=Path(folder).resolve();db=folder/'study.sqlite3'
 with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as c:meta=dict(c.execute('SELECT key,value FROM metadata'));row=c.execute('SELECT next_index,elapsed,stats,stats_sha256,stage FROM state WHERE id=1').fetchone();count=c.execute('SELECT COUNT(*) FROM episodes').fetchone()[0]
 if sha(meta['protocol'].encode())!=meta['protocol_sha256']:raise ValueError('Повреждён протокол.')
 p=json.loads(meta['protocol']);expected={**p,'script_sha256':file_sha(__file__),'runner59_sha256':RUNNER59_SHA}
 if canonical(expected)!=meta['protocol'] or not row or row[0]!=count or row[4] not in ('training','evaluation','completed'):raise ValueError('Состояние серии 66 повреждено.')
 return folder,db,p,{'next_index':row[0],'elapsed':row[1],'stats':unpack_stats(row[2],row[3]),'stage':row[4]}
def free_check(large,folder,fixture):
 if fixture:return
 ram=large.available_ram()
 if ram is None or ram<MIN_RAM:raise MemoryError('Нужно не менее 4 ГиБ свободной RAM.')
 if shutil.disk_usage(folder).free<MIN_DISK:raise OSError('Нужно не менее 2 ГиБ на диске.')

WORK=None
def worker_init(train):
 global WORK
 r=load_runner();proto,ev,pre,stim,ck,base,large=r.dependencies();studio=proto.load('auto66_studio','50_two_flies_wing_studio_pilot.py');engine=proto.load('auto66_engine','38_two_flies_observation.py');pilot=proto.load('auto66_pilot','47_two_flies_imitation_learning.py');pilot.lower_priority();WORK=(stim,studio.Scene(engine),train)
def worker_episode(ident):
 stim,scene,train=WORK;spec,degrees=stim.candidate(train,ident);images=scene.render(degrees*np.pi/180,distance=spec['distance'],offset=spec['side_offset']);x,_=encode(images);y=target_coeff(degrees*np.pi/180);return {'candidate_id':ident,'rgb_sha256':sha(images.tobytes())},x,y

def commit(db,expected,records,stats,elapsed):
 blob=pack_stats(stats)
 with sqlite3.connect(db,timeout=30) as c:
  c.execute('PRAGMA synchronous=FULL');row=c.execute('SELECT next_index,elapsed,stage FROM state WHERE id=1').fetchone()
  if row[0]!=expected or row[2]!='training' or elapsed<row[1]:raise ValueError('Контрольная точка изменилась.')
  c.executemany('INSERT INTO episodes VALUES(?,?,?)',[(expected+i,r['candidate_id'],r['rgb_sha256']) for i,r in enumerate(records)]);c.execute('UPDATE state SET next_index=?,elapsed=?,stats=?,stats_sha256=? WHERE id=1',(expected+len(records),elapsed,blob,sha(blob)))

def metrics(truth,pred):
 e=np.asarray(pred)-np.asarray(truth);return {'frames':len(truth),'rmse_rad':float(np.sqrt(np.mean(e*e))),'mae_rad':float(np.mean(np.abs(e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)},'opposite_sign_values':int(np.sum((pred*truth<0)&(truth!=0)))}
def evaluate(folder,p,state,src,proto,ev,stim,train,tests):
 out=folder/'result'
 if out.exists():return out
 model=fit(state['stats']);temp=folder/('result_incomplete_'+uuid.uuid4().hex);temp.mkdir();np.savez_compressed(temp/'autonomous_model.npz',**model);studio=proto.load('auto66_eval_studio','50_two_flies_wing_studio_pilot.py');engine=proto.load('auto66_eval_engine','38_two_flies_observation.py');scene=studio.Scene(engine);rows=[]
 labels=[]
 for h in p['holdouts']:
  raw=(folder/h['copy']).read_bytes();obj=json.loads(raw.decode('utf-8-sig'));t,deg=stim.sample_trajectory(obj);labels.append((h,obj,t,deg))
 for h,obj,t,deg in labels:
  truth=deg*np.pi/180;images=scene.render(truth);conditions={'normal':images,'reversed':images[::-1].copy(),'shuffled':images[np.random.default_rng(660000+h['index']).permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)};preds={};states={};activities=None
  for name,im in conditions.items():
   x,a=encode(im);coeff=predict(model,x);replay=np.clip(decode(coeff,len(truth)),-math.pi/3,math.pi/3);preds[name]=replay;states[name]=coeff
   if name=='normal':activities=a
  zero=np.zeros_like(truth);result={'holdout_index':h['index'],'frames':len(truth),'normal':metrics(truth,preds['normal']),'zero':metrics(truth,zero),'controls':{k:metrics(truth,v) for k,v in preds.items() if k!='normal'},'internal_state_sha256':sha(np.asarray(states['normal'],dtype='<f8').tobytes()),'delay_s':DELAY_S,'state_unchanged_during_delay':True};result['normal_minus_zero_rmse_rad']=result['normal']['rmse_rad']-result['zero']['rmse_rad'];rows.append(result);td=temp/f'holdout_{h["index"]:03d}';td.mkdir()
  with (td/'observer_activity.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['time_s',*[f'unit_{i:02d}' for i in range(OBS_UNITS)]]);w.writerows([[float(tv),*map(float,a)] for tv,a in zip(t,activities)])
  with (td/'autonomous_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['replay_time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'autonomous_{a}_rad' for a in AXES]]);w.writerows([[float(tv),*map(float,y),*map(float,q)] for tv,y,q in zip(t,truth,preds['normal'])])
  save_json(td/'internal_state.json',{'schema':'observer-internal-state-v1','holdout_index':h['index'],'coefficients':list(map(float,states['normal'])),'delay_s':DELAY_S,'updates_during_delay':0,'replay_inputs':['internal coefficient state','replay phase'],'forbidden_replay_inputs':['observation images','teacher angles','buffered predictions']});save_json(td/'metrics.json',result)
  playback={'schema':'fly-wings-result-v1','fps':25,'duration_s':obj['duration_s'],'trajectory':obj,'samples':[{'t':float(tv),'teacher_deg':list(map(float,y)),'prediction_deg':list(map(float,q*180/np.pi))} for tv,y,q in zip(t,deg,preds['normal'])],'method':'observe full episode -> coefficient state -> 0.5 s delay -> autonomous phase decoder','limitations':['Предсказание создаётся из внутреннего состояния и фазы, не из кадров во время replay.','Латентные units не являются идентифицированными биологическими нейронами.']};save_json(td/'playback.json',playback);print(f'Автономный replay {h["index"]}/5.',flush=True)
 primary=float(np.mean([x['normal_minus_zero_rmse_rad'] for x in rows]));agg={'holdouts':5,'primary_mean_normal_minus_zero_rmse_rad':primary,'normal_better_than_zero':sum(x['normal_minus_zero_rmse_rad']<0 for x in rows),'mean_normal_rmse_rad':float(np.mean([x['normal']['rmse_rad'] for x in rows])),'mean_zero_rmse_rad':float(np.mean([x['zero']['rmse_rad'] for x in rows])),'mean_control_rmse_rad':{name:float(np.mean([x['controls'][name]['rmse_rad'] for x in rows])) for name in ('reversed','shuffled','static','closed')}};report={'schema':'observe-delay-autonomous-replay-result-v1','created_utc':datetime.now(timezone.utc).isoformat(),'status':'fixture_completed' if p['mode']=='fixture' else 'completed','protocol':p,'model_sha256':file_sha(temp/'autonomous_model.npz'),'training_episodes':state['stats']['n'],'aggregate':agg,'holdouts':rows,'limitations':['Внутреннее состояние обучено supervised по углам целой наблюдаемой последовательности.','Replay не читает изображения или teacher после наблюдения, но остаётся линейным декодером, не моторной биомеханикой.','Observer units искусственные и не являются доказательством зеркальных нейронов.','Пять пользовательских holdout не являются биологическими повторами.']};save_json(temp/'summary.json',report);lines=['СЕРИЯ 66: НАБЛЮДЕНИЕ → СОСТОЯНИЕ → ЗАДЕРЖКА → АВТОНОМНЫЙ REPLAY','',f'Обучающих эпизодов: {state["stats"]["n"]}. Задержка: {DELAY_S:.2f} с.',f'Основная средняя разность RMSE normal replay − stationary zero: {primary:+.6f} рад (отрицательное лучше).',f'Normal лучше zero на {agg["normal_better_than_zero"]}/5 движений.',f'Средняя RMSE normal / zero: {agg["mean_normal_rmse_rad"]:.6f} / {agg["mean_zero_rmse_rad"]:.6f} рад.','',f'Контроли, средняя RMSE: {agg["mean_control_rmse_rad"]}.','','Во время replay используются только внутреннее состояние и фаза; кадры, teacher и буфер прогнозов недоступны.',*report['limitations']];(temp/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(canonical(p).encode()),'files':{str(q.relative_to(temp)).replace('\\','/'):file_sha(q) for q in temp.rglob('*') if q.is_file()}});temp.rename(out);return out

def process(folder,max_batches=None):
 folder,db,p,state=read_state(folder);src=source_state(p['source_series59']);runner,proto,ev,stim,large,source,source_db,saved,source_st,train,tests=src
 if file_sha(source_db)!=p['source_database_sha256'] or sha(canonical(saved).encode())!=p['source_protocol_sha256']:raise ValueError('Исходная серия изменилась.')
 with sqlite3.connect(source_db.resolve().as_uri()+'?mode=ro',uri=True) as c:ids=[r[0] for r in c.execute("SELECT id FROM candidates WHERE status='accepted' ORDER BY id")];expected_rgb=dict(c.execute("SELECT id,rgb_sha256 FROM candidates WHERE status='accepted'"))
 if p['fixture_limit']:ids=ids[:p['fixture_limit']]
 large.job_guard()
 with large.RunLock(folder):
  if state['stage']=='completed':print('Серия уже завершена:',folder/'result');return
  free_check(large,folder,p['mode']=='fixture');done=state['next_index'];stats=state['stats'];prior=state['elapsed'];started=time.monotonic();batches=0
  if state['stage']=='training':
   with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(train,)) as pool:
    while done<len(ids):
     pause=folder/'pause.request'
     if pause.exists():pause.unlink();print('Пауза: последняя партия сохранена.');return
     if max_batches is not None and batches>=max_batches:print('Fixture остановлена после партии.');return
     batch=ids[done:done+2];generated=list(pool.map(worker_episode,batch));records=[]
     for ident,(rec,x,y) in zip(batch,generated):
      if rec['candidate_id']!=ident or rec['rgb_sha256']!=expected_rgb[ident]:raise ValueError('RGB эпизода не воспроизведён.')
      update_stats(stats,x,y);records.append(rec)
     elapsed=prior+time.monotonic()-started;commit(db,done,records,stats,elapsed);done+=len(records);batches+=1;print(f'Сохранено эпизодов {done}/{len(ids)}.',flush=True)
   with sqlite3.connect(db) as c:c.execute("UPDATE state SET stage='evaluation' WHERE id=1 AND stage='training'")
   folder,db,p,state=read_state(folder)
  if state['stage']=='evaluation':
   out=evaluate(folder,p,state,src,proto,ev,stim,train,tests)
   with sqlite3.connect(db) as c:c.execute("UPDATE state SET stage='completed' WHERE id=1 AND stage='evaluation'")
   print('Готово:',out)
   if os.name=='nt':
    try:os.startfile(str(out))
    except OSError:pass

def start(folder,source,holdouts,fixture_limit=None,max_batches=None):
 src=source_state(source);runner,proto,ev,stim,large,source,db,saved,state,train,tests=src;blocked={x['motion_sha256'] for x in train+tests}|set(PRIOR_HOLDOUT_MOTIONS);items=freeze_holdouts(holdouts,stim,blocked)
 if fixture_limit is not None and (type(fixture_limit)!=int or not 2<=fixture_limit<=8):raise ValueError('Fixture допускает 2–8 эпизодов.')
 p=make_protocol(source,saved,state,items,fixture_limit);parent=Path(folder).parent;parent.mkdir(parents=True,exist_ok=True);free_check(large,parent,fixture_limit is not None);create(folder,p,items);print('Пять holdout закреплены до обучения и прогнозов.',flush=True);process(folder,max_batches)
def request_pause(folder):
 folder=Path(folder).resolve();_,_,p,state=read_state(folder);large=source_state(p['source_series59'])[4]
 if state['stage']!='training':raise ValueError('Обучение уже закончено.')
 try:
  with large.RunLock(folder):pass
 except ValueError:pass
 else:raise ValueError('Серия сейчас не работает.')
 (folder/'pause.request').write_text('pause\n',encoding='utf8');print('Запрос паузы записан.')
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox,simpledialog
 root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
 try:
  action=simpledialog.askinteger('Серия 66','Введите номер:\n1: начать\n2: продолжить\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
  if action is None:return
  if action in (2,3):
   folder=filedialog.askdirectory(title='Папка observe_delay_replay_...',initialdir=str(ROOT.resolve()) if ROOT.exists() else str(Path.cwd()),parent=root)
   if not folder:return
   return process(folder) if action==2 else request_pause(folder)
  source=filedialog.askdirectory(title='Завершённая серия 59 wing_user_long_...',initialdir=str(SOURCE_ROOT.resolve()) if SOURCE_ROOT.exists() else str(Path.cwd()),parent=root)
  if not source:return
  messagebox.showinfo('Пять новых движений','Выберите ровно пять новых JSON одновременно. Они будут закреплены до обучения.',parent=root);hold=list(filedialog.askopenfilenames(title='Ровно пять новых holdout JSON',filetypes=[('Траектория JSON','*.json')],parent=root))
  if len(hold)!=5:raise ValueError(f'Выбрано {len(hold)}, нужно 5.')
  folder=ROOT/('observe_delay_replay_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);start(folder,source,hold)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--choose',action='store_true');g.add_argument('--new');g.add_argument('--resume');g.add_argument('--pause');p.add_argument('--source');p.add_argument('--holdouts',nargs='*');p.add_argument('--fixture-limit',type=int,help=argparse.SUPPRESS);p.add_argument('--batches',type=int,help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:return choose()
 if a.new:
  if not a.source or len(a.holdouts or [])!=5:p.error('Нужны --source и ровно пять --holdouts.')
  return start(a.new,a.source,a.holdouts,a.fixture_limit,a.batches)
 if a.resume:return process(a.resume,a.batches)
 return request_pause(a.pause)
if __name__=='__main__':
 multiprocessing.freeze_support()
 try:sys.exit(main() or 0)
 except Exception as exc:print(f'ОШИБКА СЕРИИ 66: {type(exc).__name__}: {exc}\nИсходные серии и holdout не изменялись.',file=sys.stderr,flush=True);sys.exit(1)
