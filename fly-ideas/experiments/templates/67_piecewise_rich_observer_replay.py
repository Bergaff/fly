#!/usr/bin/env python3
"""Series 67: matched piecewise training and richer temporal observer state."""
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
ROOT=Path('workspace/runs/ideas/i-observational/piecewise-rich-replay');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/wing-user-long')
AXES=('left_x','left_y','left_z','right_x','right_y','right_z')
SPATIAL_UNITS=96;OBS_BASIS=10;OUT_BASIS=12;XDIM=SPATIAL_UNITS*OBS_BASIS*2;YDIM=72
DELAY_S=.5;DELTA_GAIN=4.0;TARGET_EPISODES=60000;BATCH=32;LR=0.002;WEIGHT_DECAY=1e-6
MIN_RAM=4*1024**3;MIN_DISK=2*1024**3;TRAIN_SEED=6702;FEATURE_SEED=6701
# Series 63-64 and the completed series-66 battery. Series 60-62 reused series-59 tests; series 65 had no holdout.
PRIOR_HOLDOUT_MOTIONS=frozenset({
 '59c3778e3055e6bb18d09736541dcb4fd0a9b27fef2f0c52c365886398fc779d',
 '90b29ef78833b0a84c9241b30a179af2e374c8e5b7a42abf13936c68a2b4a5b8','7b38ade07720d23b99f73c3ace7c16feb0983b9ce8346eb058b2a19e57e0921a',
 '7b088a0712dbe5852ac27588d8a9fa0f3d29722ded5bbd6f5a0cd6a3ea272f8a','06bcb616a991cf2f31e3e02f53cd74f828fc5b4e093dd496d6ec72f28d07a091',
 '3fbf12ef88f7b9458caa27727d1b20021f807df934059b31142716304137f987',
 '3628ada0eee2a0e82edc18c779a1a330a13f237388e07395861bc50af655230f','622d448a2b97846ad01f04f3d3a6f0966f3b30698d78c90e543e68c744431b1f',
 '32677a11dbe62d7f50af63847e7699d3b9022854f0b968689bbcded04dc687c8','58ae5c22fe76a2152813fdaf467555b9446e57fe6794abc78f75b9c31a59b948',
 '873a1946cab7f7f627a944a30dded8cd5f4566e31c21c6ec98a8b1ad948c53b6',
})
_rng=np.random.default_rng(FEATURE_SEED);PROJECTION=_rng.normal(0,1/math.sqrt(192),(192,SPATIAL_UNITS))

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def load_runner():
 if file_sha(RUNNER59)!=RUNNER59_SHA:raise ValueError('Закреплённый runner серии 59 изменился.')
 spec=importlib.util.spec_from_file_location('rich_runner59',RUNNER59);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def source_state(folder):
 runner=load_runner();proto,ev,pre,stim,ck,base,large=runner.dependencies();folder=Path(folder).resolve();db=folder/'study.sqlite3';saved,state,stage,seconds=runner.saved_state(db,proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая серия 59.')
 runner.verify_result(folder/'result',saved,state)
 return runner,proto,stim,large,folder,db,saved,state

def basis(n,k):
 if n<k:raise ValueError('Слишком мало кадров для temporal basis.')
 phase=(np.arange(n)+.5)/n;return np.column_stack([np.ones(n)]+[np.cos(np.pi*j*phase) for j in range(1,k)])
def frame_activity(images):
 images=np.asarray(images)
 if images.dtype!=np.uint8 or images.ndim!=5 or images.shape[1:]!=(2,32,48,3):raise ValueError('Некорректные изображения наблюдения.')
 lum=images.astype(np.float64).mean(axis=-1)/255
 blocks=lum.reshape(len(images),2,8,4,12,4).mean(axis=(3,5)).reshape(len(images),192)
 return np.tanh((blocks-.5)@PROJECTION)
def encode(images):
 activity=frame_activity(images);delta=np.empty_like(activity);delta[0]=0;delta[1:]=(activity[1:]-activity[:-1])*DELTA_GAIN;b=basis(len(activity),OBS_BASIS)
 level=(b[:,:,None]*activity[:,None,:]).mean(axis=0).reshape(-1);change=(b[:,:,None]*delta[:,None,:]).mean(axis=0).reshape(-1)
 return np.concatenate([level,change]),activity,delta
def target_coeff(angles_rad):
 y=np.asarray(angles_rad,dtype=float);return np.linalg.lstsq(basis(len(y),OUT_BASIS),y,rcond=None)[0].T.reshape(-1)
def replay_from_state(state,n):
 state=np.asarray(state,dtype=float)
 if state.shape!=(YDIM,):raise ValueError('Replay принимает только 72 коэффициента состояния.')
 return np.clip(basis(n,OUT_BASIS)@state.reshape(6,OUT_BASIS).T,-math.pi/3,math.pi/3)
def motion_hash(degrees):
 normalized=np.round((np.asarray(degrees)*np.pi/180)*180/np.pi,7);normalized[normalized==0]=0
 return sha(np.asarray(normalized,dtype='<f8').tobytes())
def piecewise_candidate(ident):
 if type(ident)!=int or not 0<=ident<2**32:raise ValueError('Некорректный candidate id.')
 rng=np.random.default_rng(np.random.SeedSequence([TRAIN_SEED,ident]));keys=rng.integers(-45,46,size=(5,6)).astype(float);t=np.arange(51)/25;kt=np.arange(5)*.5
 degrees=np.stack([np.interp(t,kt,keys[:,j]) for j in range(6)],axis=1)
 spec={'candidate_id':ident,'seed':[TRAIN_SEED,ident],'keyframes_deg':keys.astype(int).tolist(),'distance':float(rng.uniform(3.7,4.3)),'side_offset':float(rng.uniform(-.3,.3)),'motion_sha256':motion_hash(degrees)}
 return spec,degrees

def freeze_holdouts(paths,stim,blocked):
 if len(paths)!=5:raise ValueError('Нужно ровно пять новых JSON серии 67.')
 out=[];seen=set(blocked);expected=np.arange(5)*.5
 for i,path in enumerate(paths,1):
  path=Path(path)
  if not path.is_file() or path.stat().st_size>1024*1024:raise ValueError(f'Holdout {i} отсутствует или слишком велик.')
  raw=path.read_bytes();obj=json.loads(raw.decode('utf-8-sig'));times,degrees=stim.sample_trajectory(obj)
  key_times=np.asarray([x['t'] for x in obj.get('keyframes',[])],dtype=float) if isinstance(obj,dict) else np.array([])
  if obj.get('duration_s')!=2 or key_times.shape!=(5,) or not np.allclose(key_times,expected,rtol=0,atol=1e-9):raise ValueError('Holdout серии 67 должен быть создан кнопкой случайного движения: 2 с, точки 0/0,5/1/1,5/2 с.')
  motion=stim.motion_hash(degrees)
  if motion in seen:raise ValueError(f'Holdout {i} совпадает с прежним или другим движением.')
  seen.add(motion);out.append({'index':i,'raw':raw,'obj':obj,'times':times,'angles_deg':degrees,'source_sha256':sha(raw),'motion_sha256':motion,'basename':path.name})
 return out

def empty_adam():return {'step':0,'accepted':0,'w':np.zeros((XDIM+1,YDIM)),'m':np.zeros((XDIM+1,YDIM)),'v':np.zeros((XDIM+1,YDIM))}
def adam_update(state,x,y):
 x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float)
 if x.ndim!=2 or x.shape[1]!=XDIM or y.shape!=(len(x),YDIM) or not np.isfinite(x).all() or not np.isfinite(y).all():raise ValueError('Некорректная Adam batch.')
 xa=np.column_stack([x,np.ones(len(x))]);pred=xa@state['w'];grad=xa.T@(pred-y)/len(x);grad[:-1]+=WEIGHT_DECAY*state['w'][:-1]
 norm=float(np.linalg.norm(grad));grad*=min(1.0,5.0/max(norm,1e-12));state['step']+=1;state['accepted']+=len(x);b1=.9;b2=.999
 state['m']=b1*state['m']+(1-b1)*grad;state['v']=b2*state['v']+(1-b2)*grad*grad
 mh=state['m']/(1-b1**state['step']);vh=state['v']/(1-b2**state['step']);state['w']-=LR*mh/(np.sqrt(vh)+1e-8)
 return float(np.mean((pred-y)**2))
def predict(w,x):return np.append(np.asarray(x,dtype=float),1.0)@w

def pack_state(s):
 mem=io.BytesIO();np.savez_compressed(mem,step=np.int64(s['step']),accepted=np.int64(s['accepted']),w=s['w'],m=s['m'],v=s['v']);return mem.getvalue()
def unpack_state(blob,digest):
 if sha(blob)!=digest or len(blob)>64*1024*1024:raise ValueError('SHA или размер checkpoint неверен.')
 with zipfile.ZipFile(io.BytesIO(blob)) as z:
  if sum(x.file_size for x in z.infolist())>64*1024*1024:raise ValueError('Распакованный checkpoint слишком велик.')
 with np.load(io.BytesIO(blob),allow_pickle=False) as z:s={'step':int(z['step']),'accepted':int(z['accepted']),'w':np.array(z['w'],copy=True),'m':np.array(z['m'],copy=True),'v':np.array(z['v'],copy=True)}
 if any(s[k].shape!=(XDIM+1,YDIM) for k in ('w','m','v')) or s['step']<0 or s['accepted']<0:raise ValueError('Некорректный Adam checkpoint.')
 return s

def make_protocol(source,saved,items,limit):
 target=limit or TARGET_EPISODES
 return {'schema':'piecewise-rich-observer-replay-v1','mode':'fixture' if limit else 'full','script_sha256':file_sha(__file__),'runner59_sha256':RUNNER59_SHA,'source_series59':str(source),'source_database_sha256':file_sha(Path(source)/'study.sqlite3'),'source_protocol_sha256':sha(canonical(saved).encode()),'target_training_episodes':target,'workers':2,'batch':2 if limit else BATCH,'training_generator':{'seed':TRAIN_SEED,'duration_s':2,'keyframe_step_s':.5,'keyframe_integer_range_deg':[-45,45],'distance_range':[3.7,4.3],'side_offset_range':[-.3,.3]},'observer':{'spatial_units':SPATIAL_UNITS,'feature_seed':FEATURE_SEED,'temporal_basis':OBS_BASIS,'delta_gain':DELTA_GAIN,'feature_dimensions':XDIM},'internal_state_coefficients':YDIM,'output_temporal_basis':OUT_BASIS,'delay_s':DELAY_S,'optimizer':{'name':'Adam','learning_rate':LR,'weight_decay':WEIGHT_DECAY},'holdouts':[{'index':x['index'],'copy':f'input/holdout_{x["index"]:03d}.json','source_sha256':x['source_sha256'],'motion_sha256':x['motion_sha256'],'basename':x['basename']} for x in items],'primary_rule':'mean normal RMSE must be lower than stationary zero, static, shuffled, and reversed','replay_access':'internal coefficient state and replay phase only; no images, teacher angles, or buffered predictions'}

def create(folder,p,items):
 folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir(exist_ok=False);(folder/'input').mkdir();blob=pack_state(empty_adam());text=canonical(p)
 for x in items:(folder/'input'/f'holdout_{x["index"]:03d}.json').write_bytes(x['raw'])
 with sqlite3.connect(folder/'study.sqlite3') as db:
  db.execute('PRAGMA journal_mode=DELETE');db.execute('PRAGMA synchronous=FULL');db.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)');db.execute('CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),next_candidate INTEGER NOT NULL,elapsed REAL NOT NULL,checkpoint BLOB NOT NULL,checkpoint_sha256 TEXT NOT NULL,stage TEXT NOT NULL,last_loss REAL)');db.execute('CREATE TABLE episodes(candidate_id INTEGER PRIMARY KEY,status TEXT NOT NULL,motion_sha256 TEXT NOT NULL,rgb_sha256 TEXT)');db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','piecewise-rich-checkpoint-v1'),('protocol',text),('protocol_sha256',sha(text.encode()))]);db.execute("INSERT INTO state VALUES(1,0,0,?,?, 'training',NULL)",(blob,sha(blob)))

def read_state(folder):
 folder=Path(folder).resolve();dbp=folder/'study.sqlite3'
 with sqlite3.connect(dbp.resolve().as_uri()+'?mode=ro',uri=True) as db:meta=dict(db.execute('SELECT key,value FROM metadata'));row=db.execute('SELECT next_candidate,elapsed,checkpoint,checkpoint_sha256,stage,last_loss FROM state WHERE id=1').fetchone();count=db.execute('SELECT COUNT(*) FROM episodes').fetchone()[0]
 if meta.get('schema')!='piecewise-rich-checkpoint-v1' or sha(meta['protocol'].encode())!=meta.get('protocol_sha256') or not row:raise ValueError('Повреждена база серии 67.')
 p=json.loads(meta['protocol'])
 if file_sha(__file__)!=p['script_sha256']:raise ValueError('Скрипт серии 67 изменился; продолжение остановлено.')
 state=unpack_state(row[2],row[3])
 if row[0]!=count or row[4] not in ('training','evaluation','completed') or state['accepted']>p['target_training_episodes']:raise ValueError('Несогласованный checkpoint серии 67.')
 return folder,dbp,p,{'next_candidate':row[0],'elapsed':float(row[1]),'adam':state,'stage':row[4],'last_loss':row[5]}

def free_check(large,folder,fixture):
 if fixture:return
 ram=large.available_ram()
 if ram is None or ram<MIN_RAM:raise MemoryError('Нужно не менее 4 ГиБ свободной RAM.')
 if shutil.disk_usage(folder).free<MIN_DISK:raise OSError('Нужно не менее 2 ГиБ свободного места.')

WORKER=None;WORKER_BLOCKED=None
def worker_init(blocked):
 global WORKER,WORKER_BLOCKED
 runner=load_runner();proto,*_=runner.dependencies();proto.worker_init([],set());WORKER=proto;WORKER_BLOCKED=set(blocked)
def worker_episode(ident):
 spec,degrees=piecewise_candidate(ident)
 if spec['motion_sha256'] in WORKER_BLOCKED:return {'candidate_id':ident,'status':'rejected','motion_sha256':spec['motion_sha256'],'rgb_sha256':None},None,None
 images=WORKER.SCENE.render(degrees*np.pi/180,distance=spec['distance'],offset=spec['side_offset']);x,_,_=encode(images);y=target_coeff(degrees*np.pi/180)
 return {'candidate_id':ident,'status':'accepted','motion_sha256':spec['motion_sha256'],'rgb_sha256':sha(images.tobytes())},x,y

def commit(dbp,start,records,adam,elapsed,loss):
 blob=pack_state(adam)
 with sqlite3.connect(dbp,timeout=30) as db:
  db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE');db.executemany('INSERT INTO episodes VALUES (:candidate_id,:status,:motion_sha256,:rgb_sha256)',records);db.execute('UPDATE state SET next_candidate=?,elapsed=?,checkpoint=?,checkpoint_sha256=?,last_loss=? WHERE id=1',(start+len(records),elapsed,blob,sha(blob),loss))

def metrics(truth,pred):
 e=np.asarray(pred)-np.asarray(truth);return {'frames':len(e),'rmse_rad':float(np.sqrt(np.mean(e*e))),'mae_rad':float(np.mean(np.abs(e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)}}
def verify_output(out):
 out=Path(out);manifest=json.loads((out/'complete.json').read_text(encoding='utf8'))
 for name,digest in manifest['files'].items():
  if file_sha(out/name)!=digest:raise ValueError('Контрольные суммы результата серии 67 не совпали.')
 return out

def evaluate(folder,p,state,src):
 out=folder/'result'
 if out.exists():return verify_output(out)
 runner,proto,stim,large,source,source_db,saved,source_state_=src;proto.worker_init([],set());scene=proto.SCENE;temp=folder/'result.tmp'
 if temp.exists():shutil.rmtree(temp)
 temp.mkdir();np.savez_compressed(temp/'autonomous_model.npz',weights=state['adam']['w'],projection=PROJECTION)
 rows=[]
 for h in p['holdouts']:
  raw=(folder/h['copy']).read_bytes();obj=json.loads(raw.decode('utf-8-sig'));t,deg=stim.sample_trajectory(obj);truth=deg*np.pi/180;normal=scene.render(truth);rng=np.random.default_rng(670000+h['index']);order=rng.permutation(len(normal));variants={'normal':normal,'reversed':normal[::-1].copy(),'shuffled':normal[order].copy(),'static':np.repeat(normal[:1],len(normal),axis=0),'closed':np.zeros_like(normal)};preds={};states={};normal_activity=None;normal_delta=None
  for name,images in variants.items():
   x,activity,delta=encode(images);coeff=predict(state['adam']['w'],x);states[name]=coeff;preds[name]=replay_from_state(coeff,len(truth))
   if name=='normal':normal_activity=activity;normal_delta=delta
  zero=np.zeros_like(truth);result={'holdout_index':h['index'],'frames':len(truth),'normal':metrics(truth,preds['normal']),'zero':metrics(truth,zero),'controls':{k:metrics(truth,v) for k,v in preds.items() if k!='normal'},'internal_state_sha256':sha(np.asarray(states['normal'],dtype='<f8').tobytes()),'delay_s':DELAY_S,'state_unchanged_during_delay':True};rows.append(result);td=temp/f'holdout_{h["index"]:03d}';td.mkdir()
  with (td/'observer_activity.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['time_s',*[f'level_{i:03d}' for i in range(SPATIAL_UNITS)],*[f'delta_{i:03d}' for i in range(SPATIAL_UNITS)]]);w.writerows([[float(tv),*map(float,a),*map(float,d)] for tv,a,d in zip(t,normal_activity,normal_delta)])
  with (td/'autonomous_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['replay_time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'autonomous_{a}_rad' for a in AXES]]);w.writerows([[float(tv),*map(float,y),*map(float,q)] for tv,y,q in zip(t,truth,preds['normal'])])
  save_json(td/'internal_state.json',{'schema':'rich-observer-internal-state-v1','coefficients':list(map(float,states['normal'])),'updates_during_delay':0,'delay_s':DELAY_S,'replay_inputs':['72 coefficient state','replay phase'],'forbidden_replay_inputs':['observation images','teacher angles','buffered predictions']});save_json(td/'metrics.json',result)
  save_json(td/'playback.json',{'schema':'fly-wings-result-v1','fps':25,'duration_s':obj['duration_s'],'trajectory':obj,'samples':[{'t':float(tv),'teacher_deg':list(map(float,y)),'prediction_deg':list(map(float,q*180/np.pi))} for tv,y,q in zip(t,deg,preds['normal'])],'method':'rich level+delta observation -> 72 coefficient state -> 0.5 s delay -> autonomous phase decoder'})
  print(f'Проверено новое движение {h["index"]}/5.',flush=True)
 means={name:float(np.mean([r['normal']['rmse_rad'] if name=='normal' else r['zero']['rmse_rad'] if name=='zero' else r['controls'][name]['rmse_rad'] for r in rows])) for name in ('normal','zero','static','shuffled','reversed','closed')};diffs={name:means['normal']-means[name] for name in ('zero','static','shuffled','reversed','closed')};passed=all(diffs[name]<0 for name in ('zero','static','shuffled','reversed'))
 aggregate={'holdouts':5,'mean_rmse_rad':means,'normal_minus_control_rmse_rad':diffs,'normal_better_than_zero':sum(r['normal']['rmse_rad']<r['zero']['rmse_rad'] for r in rows),'primary_pass':passed};report={'schema':'piecewise-rich-observer-replay-result-v1','created_utc':datetime.now(timezone.utc).isoformat(),'status':'fixture_completed' if p['mode']=='fixture' else 'completed','protocol':p,'training_episodes':state['adam']['accepted'],'optimizer_steps':state['adam']['step'],'model_sha256':file_sha(temp/'autonomous_model.npz'),'aggregate':aggregate,'holdouts':rows,'limitations':['Обучающие движения синтетические и matched по общему генератору, но не копируют holdout.','Observer features и 72-коэффициентное состояние искусственные.','Replay остаётся cosine decoder, не мышечной биомеханикой.','Пять пользовательских файлов не являются независимыми животными или доказательством зеркальных нейронов.']};save_json(temp/'summary.json',report)
 lines=['СЕРИЯ 67: MATCHED PIECEWISE + RICH TEMPORAL OBSERVER','',f'Обучающих эпизодов: {state["adam"]["accepted"]}. Задержка: {DELAY_S:.2f} с.',f'Средняя RMSE: {means}.',f'Normal минус контроли: {diffs}.',f'Normal лучше zero на {aggregate["normal_better_than_zero"]}/5.',f'Заранее заданный составной критерий пройден: {"ДА" if passed else "НЕТ"}.','','Критерий требует normal ниже zero, static, shuffled и reversed.','Во время replay доступны только 72 коэффициента состояния и фаза.',*report['limitations']];(temp/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');files={str(q.relative_to(temp)).replace('\\','/'):file_sha(q) for q in temp.rglob('*') if q.is_file()};save_json(temp/'complete.json',{'files':files});temp.rename(out);return out

def process(folder,max_batches=None):
 folder,dbp,p,state=read_state(folder);src=source_state(p['source_series59']);runner,proto,stim,large,source,source_db,saved,source_st=src
 if file_sha(source_db)!=p['source_database_sha256'] or sha(canonical(saved).encode())!=p['source_protocol_sha256']:raise ValueError('Исходная серия 59 изменилась.')
 large.job_guard()
 with large.RunLock(folder):
  if state['stage']=='completed':verify_output(folder/'result');print('Серия уже завершена:',folder/'result');return
  if state['stage']=='evaluation':
   out=evaluate(folder,p,state,src)
   with sqlite3.connect(dbp) as db:db.execute("UPDATE state SET stage='completed' WHERE id=1")
   print('Готово:',out);return
  train59,test59=proto.split_from_sources(source_st['sources'],stim);blocked={x['motion_sha256'] for x in train59+test59}|{x['motion_sha256'] for x in p['holdouts']}|set(PRIOR_HOLDOUT_MOTIONS)
  free_check(large,folder,p['mode']=='fixture');target=p['target_training_episodes'];started=time.monotonic();prior=state['elapsed'];candidate=state['next_candidate'];adam=state['adam'];batches=0;batch_size=p['batch']
  with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(blocked,)) as pool:
   while adam['accepted']<target:
    pause=folder/'pause.request'
    if pause.exists():pause.unlink();print('Пауза: последний checkpoint сохранён.');return
    if max_batches is not None and batches>=max_batches:print('Fixture остановлена после партии.');return
    count=min(batch_size,target-adam['accepted']);ids=list(range(candidate,candidate+count));generated=list(pool.map(worker_episode,ids));records=[r for r,_,_ in generated];accepted=[(x,y) for r,x,y in generated if r['status']=='accepted'];loss=state['last_loss']
    if accepted:loss=adam_update(adam,np.stack([x for x,_ in accepted]),np.stack([y for _,y in accepted]))
    elapsed=prior+time.monotonic()-started;commit(dbp,candidate,records,adam,elapsed,loss);candidate+=len(records);batches+=1
    rate=adam['accepted']/max(elapsed,1e-9);eta=(target-adam['accepted'])/max(rate,1e-9);print(f'Сохранено {adam["accepted"]}/{target}; loss {loss:.6g}; ориентир остатка {eta/3600:.2f} ч.',flush=True)
  with sqlite3.connect(dbp) as db:db.execute("UPDATE state SET stage='evaluation' WHERE id=1 AND stage='training'")
  folder,dbp,p,state=read_state(folder);out=evaluate(folder,p,state,src)
  with sqlite3.connect(dbp) as db:db.execute("UPDATE state SET stage='completed' WHERE id=1 AND stage='evaluation'")
  print('Готово:',out)
  if os.name=='nt':
   try:os.startfile(str(out))
   except OSError:pass

def start(folder,source,holdouts,fixture_limit=None,max_batches=None):
 src=source_state(source);runner,proto,stim,large,source,db,saved,state=src
 if fixture_limit is not None and (type(fixture_limit)!=int or not 4<=fixture_limit<=16):raise ValueError('Fixture допускает 4–16 принятых эпизодов.')
 train59,test59=proto.split_from_sources(state['sources'],stim);blocked=set(PRIOR_HOLDOUT_MOTIONS)|{x['motion_sha256'] for x in train59+test59}
 items=freeze_holdouts(holdouts,stim,blocked);p=make_protocol(source,saved,items,fixture_limit);folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True);free_check(large,folder.parent,fixture_limit is not None);create(folder,p,items);print('Новая батарея закреплена до matched training.',flush=True);process(folder,max_batches)
def request_pause(folder):
 folder,dbp,p,state=read_state(folder);large=source_state(p['source_series59'])[3]
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
  action=simpledialog.askinteger('Серия 67','Введите номер:\n1: начать\n2: продолжить\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
  if action is None:return
  if action in (2,3):
   folder=filedialog.askdirectory(title='Папка piecewise_rich_replay_...',initialdir=str(ROOT.resolve()) if ROOT.exists() else str(Path.cwd()),parent=root)
   if not folder:return
   return process(folder) if action==2 else request_pause(folder)
  source=filedialog.askdirectory(title='Завершённая серия 59 wing_user_long_...',initialdir=str(SOURCE_ROOT.resolve()) if SOURCE_ROOT.exists() else str(Path.cwd()),parent=root)
  if not source:return
  messagebox.showinfo('Новая батарея','Создайте и выберите ровно пять НОВЫХ случайных JSON длительностью 2 с. Движения 21–25 выбирать нельзя.',parent=root);hold=list(filedialog.askopenfilenames(title='Пять новых JSON серии 67',filetypes=[('Траектория JSON','*.json')],parent=root))
  if len(hold)!=5:raise ValueError(f'Выбрано {len(hold)}, нужно 5.')
  folder=ROOT/('piecewise_rich_replay_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);start(folder,source,hold)
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
 except Exception as exc:print(f'ОШИБКА СЕРИИ 67: {type(exc).__name__}: {exc}\nСерия 59 и holdout не изменялись.',file=sys.stderr,flush=True);sys.exit(1)
