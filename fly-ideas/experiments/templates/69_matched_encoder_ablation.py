#!/usr/bin/env python3
"""Series 69: paired compact-vs-rich encoder ablation on the exact series-67 stream."""
from __future__ import annotations
import argparse,concurrent.futures,csv
from datetime import datetime,timezone
import hashlib,importlib.util,io,json,math,multiprocessing,os
from pathlib import Path
import shutil,sqlite3,sys,time,uuid,zipfile
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER67=HERE/'67_piecewise_rich_observer_replay.py';RUNNER67_SHA='9e2e362e16e9d01fef1e293a246e5c7da10922b05b7c6710c5f838c14ed37832'
ROOT=Path('workspace/runs/ideas/i-observational/matched-encoder-ablation');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/piecewise-rich-replay')
AXES=('left_x','left_y','left_z','right_x','right_y','right_z');COMPACT_UNITS=24;OBS_BASIS=10;CDIM=240;YDIM=72
LR=.002;WEIGHT_DECAY=1e-6;BATCH=32;MIN_RAM=4*1024**3;MIN_DISK=2*1024**3
OLD_AND_REPLICATED=frozenset({'577c5bd1a8df428718522ab24287b3aebd7db2a3228d33ffde59c7c373fe7e14','801605e32df2374217b6e2a58be8554db3d1cf02ba17a30e4c39e4aabf9761e9','e2088980df2382fde184d0b9a5d052fa57658ba22e2b064aac25ab4afaeccfc4','47545738bfe5cdb0444b41424617478845f4d52f62f43f86910c4ba87d849400','75c93df56bce3034de6166a3d6025448ed76cbc70e48e8c1dc0716f61879894e','ad613a5dbe3ee7467c4e9f8998f9e343da9e6eed08ec04e65a0515debf3c90d7','4c2c6c704cf6549804559cfaa039af8f6b549c2a5a58aeba8288baba4b51cb7e','90f4038e2203d32a47f16d7a69d3d2d9bf09d348ed03a1835e25aba10350665d','1dc2d66a91b08de96abf2ada3cea89ad64db9992adec0b0dc309786b0156fea1','c7ac4d7bc09a609b52df8acd8c6d4c92ba4d4e8855a529494b0df56d4d06ca88'})
_rng=np.random.default_rng(6601);COMPACT_PROJECTION=_rng.normal(0,1/math.sqrt(192),(192,COMPACT_UNITS))

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def load67():
 if file_sha(RUNNER67)!=RUNNER67_SHA:raise ValueError('Закреплённый runner серии 67 изменился.')
 spec=importlib.util.spec_from_file_location('ablation67',RUNNER67);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def source67(folder,allow_fixture=False):
 m=load67();folder,db,p,state=m.read_state(folder)
 if state['stage']!='completed':raise ValueError('Нужна завершённая серия 67.')
 out=m.verify_output(folder/'result');summary=json.loads((out/'summary.json').read_text(encoding='utf8'));expected='fixture_completed' if allow_fixture else 'completed'
 if summary.get('status')!=expected or (not allow_fixture and (summary.get('training_episodes')!=60000 or summary.get('aggregate',{}).get('primary_pass') is not True)):raise ValueError('Нужен полный успешный source серии 67.')
 model=out/'autonomous_model.npz'
 if file_sha(model)!=summary.get('model_sha256'):raise ValueError('SHA rich модели не совпадает.')
 with np.load(model,allow_pickle=False) as z:rich_w=np.array(z['weights'],dtype=float,copy=True);projection=np.array(z['projection'],dtype=float,copy=True)
 if rich_w.shape!=(m.XDIM+1,YDIM) or not np.array_equal(projection,m.PROJECTION):raise ValueError('Rich модель имеет неверные размеры.')
 with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as con:
  records=con.execute("SELECT candidate_id,motion_sha256,rgb_sha256 FROM episodes WHERE status='accepted' ORDER BY candidate_id").fetchall()
 if len(records)!=summary['training_episodes'] or len({r[0] for r in records})!=len(records):raise ValueError('Training stream серии 67 повреждён.')
 ids=[int(r[0]) for r in records];motions={r[1] for r in records};rgb={int(r[0]):r[2] for r in records};src=m.source_state(p['source_series59'])
 return m,folder,db,p,state,summary,rich_w,ids,motions,rgb,src

def compact_encode(images,m):
 images=np.asarray(images)
 if images.dtype!=np.uint8 or images.ndim!=5 or images.shape[1:]!=(2,32,48,3):raise ValueError('Некорректные изображения.')
 lum=images.astype(np.float64).mean(axis=-1)/255;blocks=lum.reshape(len(images),2,8,4,12,4).mean(axis=(3,5)).reshape(len(images),192);activity=np.tanh((blocks-.5)@COMPACT_PROJECTION);b=m.basis(len(activity),OBS_BASIS)
 return (b[:,:,None]*activity[:,None,:]).mean(axis=0).reshape(-1),activity

def freeze(paths,stim,blocked):
 if len(paths)!=5:raise ValueError('Нужно ровно пять новых JSON для ablation.')
 out=[];seen=set(blocked);expected=np.arange(5)*.5
 for i,path in enumerate(paths,1):
  path=Path(path)
  if not path.is_file() or path.stat().st_size>1024*1024:raise ValueError(f'Holdout {i} отсутствует или слишком велик.')
  raw=path.read_bytes();obj=json.loads(raw.decode('utf-8-sig'));times,degrees=stim.sample_trajectory(obj);key=np.asarray([x['t'] for x in obj.get('keyframes',[])],dtype=float)
  if obj.get('duration_s')!=2 or key.shape!=(5,) or not np.allclose(key,expected,rtol=0,atol=1e-9):raise ValueError('Нужны random движения: 2 с и шаг 0,5 с.')
  motion=stim.motion_hash(degrees)
  if motion in seen:raise ValueError(f'Holdout {i} совпадает с training или прежней батареей.')
  seen.add(motion);out.append({'index':i,'raw':raw,'obj':obj,'times':times,'angles_deg':degrees,'source_sha256':sha(raw),'motion_sha256':motion,'basename':path.name})
 return out

def empty_adam():return {'step':0,'seen':0,'w':np.zeros((CDIM+1,YDIM)),'m':np.zeros((CDIM+1,YDIM)),'v':np.zeros((CDIM+1,YDIM))}
def update(state,x,y):
 xa=np.column_stack([x,np.ones(len(x))]);pred=xa@state['w'];grad=xa.T@(pred-y)/len(x);grad[:-1]+=WEIGHT_DECAY*state['w'][:-1];norm=float(np.linalg.norm(grad));grad*=min(1,5/max(norm,1e-12));state['step']+=1;state['seen']+=len(x);b1=.9;b2=.999;state['m']=b1*state['m']+(1-b1)*grad;state['v']=b2*state['v']+(1-b2)*grad*grad;state['w']-=LR*(state['m']/(1-b1**state['step']))/(np.sqrt(state['v']/(1-b2**state['step']))+1e-8);return float(np.mean((pred-y)**2))
def predict(w,x):return np.append(np.asarray(x),1.)@w
def pack(s):
 mem=io.BytesIO();np.savez_compressed(mem,step=np.int64(s['step']),seen=np.int64(s['seen']),w=s['w'],m=s['m'],v=s['v']);return mem.getvalue()
def unpack(blob,digest):
 if sha(blob)!=digest or len(blob)>16*1024*1024:raise ValueError('Compact checkpoint SHA/size неверен.')
 with zipfile.ZipFile(io.BytesIO(blob)) as z:
  if sum(x.file_size for x in z.infolist())>16*1024*1024:raise ValueError('Compact checkpoint слишком велик.')
 with np.load(io.BytesIO(blob),allow_pickle=False) as z:s={'step':int(z['step']),'seen':int(z['seen']),'w':np.array(z['w'],copy=True),'m':np.array(z['m'],copy=True),'v':np.array(z['v'],copy=True)}
 if any(s[k].shape!=(CDIM+1,YDIM) for k in ('w','m','v')):raise ValueError('Compact checkpoint shape неверен.')
 return s

def create(folder,p,items):
 folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir(exist_ok=False);(folder/'input').mkdir();blob=pack(empty_adam());text=canonical(p)
 for x in items:(folder/'input'/f'holdout_{x["index"]:03d}.json').write_bytes(x['raw'])
 with sqlite3.connect(folder/'study.sqlite3') as db:db.execute('PRAGMA synchronous=FULL');db.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)');db.execute('CREATE TABLE state(id INTEGER PRIMARY KEY CHECK(id=1),position INTEGER NOT NULL,elapsed REAL NOT NULL,checkpoint BLOB NOT NULL,checkpoint_sha256 TEXT NOT NULL,stage TEXT NOT NULL,last_loss REAL)');db.execute('CREATE TABLE episodes(position INTEGER PRIMARY KEY,candidate_id INTEGER UNIQUE NOT NULL,rgb_sha256 TEXT NOT NULL)');db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','matched-encoder-ablation-checkpoint-v1'),('protocol',text),('protocol_sha256',sha(text.encode()))]);db.execute("INSERT INTO state VALUES(1,0,0,?,?, 'training',NULL)",(blob,sha(blob)))
def read_state(folder):
 folder=Path(folder).resolve();dbp=folder/'study.sqlite3'
 with sqlite3.connect(dbp.resolve().as_uri()+'?mode=ro',uri=True) as db:meta=dict(db.execute('SELECT key,value FROM metadata'));row=db.execute('SELECT position,elapsed,checkpoint,checkpoint_sha256,stage,last_loss FROM state WHERE id=1').fetchone();count=db.execute('SELECT COUNT(*) FROM episodes').fetchone()[0]
 if meta.get('schema')!='matched-encoder-ablation-checkpoint-v1' or sha(meta['protocol'].encode())!=meta.get('protocol_sha256') or not row:raise ValueError('База ablation повреждена.')
 p=json.loads(meta['protocol'])
 if file_sha(__file__)!=p['script_sha256']:raise ValueError('Скрипт ablation изменился.')
 state=unpack(row[2],row[3])
 if row[0]!=count or row[0]!=state['seen'] or row[4] not in ('training','evaluation','completed'):raise ValueError('Checkpoint ablation несогласован.')
 return folder,dbp,p,{'position':row[0],'elapsed':float(row[1]),'adam':state,'stage':row[4],'last_loss':row[5]}

def free_check(large,folder,fixture):
 if fixture:return
 ram=large.available_ram()
 if ram is None or ram<MIN_RAM:raise MemoryError('Нужно не менее 4 ГиБ свободной RAM.')
 if shutil.disk_usage(folder).free<MIN_DISK:raise OSError('Нужно не менее 2 ГиБ диска.')

WORKER67=None
def worker_init(source59):
 global WORKER67
 m=load67();runner,proto,stim,large,source,db,saved,state=m.source_state(source59);proto.worker_init([],set());WORKER67=(m,proto)
def worker_episode(ident):
 m,proto=WORKER67;spec,degrees=m.piecewise_candidate(ident);images=proto.SCENE.render(degrees*np.pi/180,distance=spec['distance'],offset=spec['side_offset']);x,activity=compact_encode(images,m);y=m.target_coeff(degrees*np.pi/180);return ident,sha(images.tobytes()),x,y

def commit(dbp,start,records,state,elapsed,loss):
 blob=pack(state)
 with sqlite3.connect(dbp,timeout=30) as db:db.execute('PRAGMA synchronous=FULL');db.execute('BEGIN IMMEDIATE');db.executemany('INSERT INTO episodes VALUES (?,?,?)',records);db.execute('UPDATE state SET position=?,elapsed=?,checkpoint=?,checkpoint_sha256=?,last_loss=? WHERE id=1',(start+len(records),elapsed,blob,sha(blob),loss))
def metrics(truth,pred):
 e=np.asarray(pred)-np.asarray(truth);return {'frames':len(e),'rmse_rad':float(np.sqrt(np.mean(e*e))),'mae_rad':float(np.mean(np.abs(e))),'axis_rmse_rad':{a:float(np.sqrt(np.mean(e[:,i]**2))) for i,a in enumerate(AXES)}}
def verify_result(out):
 out=Path(out);manifest=json.loads((out/'complete.json').read_text(encoding='utf8'))
 for name,digest in manifest['files'].items():
  if file_sha(out/name)!=digest:raise ValueError('SHA результата ablation не совпадает.')
 return out

def evaluate(folder,p,state,source):
 out=folder/'result'
 if out.exists():return verify_result(out)
 m,source_folder,source_db,p67,state67,summary67,rich_w,ids,motions,rgb,src=source;runner,proto,stim,large,source59,db59,saved59,state59=src;proto.worker_init([],set());scene=proto.SCENE;temp=folder/'result.tmp'
 if temp.exists():shutil.rmtree(temp)
 temp.mkdir();np.savez_compressed(temp/'compact_model.npz',weights=state['adam']['w'],projection=COMPACT_PROJECTION);rows=[]
 for h in p['holdouts']:
  obj=json.loads((folder/h['copy']).read_text(encoding='utf-8-sig'));t,deg=stim.sample_trajectory(obj);truth=deg*np.pi/180;normal=scene.render(truth);rng=np.random.default_rng(690000+h['index']);order=rng.permutation(len(normal));variants={'normal':normal,'reversed':normal[::-1].copy(),'shuffled':normal[order].copy(),'static':np.repeat(normal[:1],len(normal),axis=0),'closed':np.zeros_like(normal)};scores={};states={};ca=None;ra=None;rd=None
  for condition,images in variants.items():
   cx,cact=compact_encode(images,m);rx,ract,rdelta=m.encode(images);cs=predict(state['adam']['w'],cx);rs=m.predict(rich_w,rx);states[(condition,'compact')]=cs;states[(condition,'rich')]=rs;scores[condition]={'compact':metrics(truth,m.replay_from_state(cs,len(truth))),'rich':metrics(truth,m.replay_from_state(rs,len(truth)))}
   if condition=='normal':ca=cact;ra=ract;rd=rdelta
  zero=metrics(truth,np.zeros_like(truth));row={'holdout_index':h['index'],'frames':len(truth),'zero':zero,'conditions':scores,'compact_state_sha256':sha(np.asarray(states[('normal','compact')],dtype='<f8').tobytes()),'rich_state_sha256':sha(np.asarray(states[('normal','rich')],dtype='<f8').tobytes()),'delay_s':m.DELAY_S,'state_unchanged_during_delay':True};rows.append(row);td=temp/f'holdout_{h["index"]:03d}';td.mkdir()
  save_json(td/'metrics.json',row);save_json(td/'internal_states.json',{'compact':list(map(float,states[('normal','compact')])),'rich':list(map(float,states[('normal','rich')])),'updates_during_delay':0,'forbidden_replay_inputs':['observation images','teacher angles','buffered predictions']})
  with (td/'observer_activity.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['time_s',*[f'compact_{i:02d}' for i in range(COMPACT_UNITS)],*[f'rich_level_{i:03d}' for i in range(m.SPATIAL_UNITS)],*[f'rich_delta_{i:03d}' for i in range(m.SPATIAL_UNITS)]]);w.writerows([[float(tv),*map(float,c),*map(float,r),*map(float,d)] for tv,c,r,d in zip(t,ca,ra,rd)])
  compact_pred=m.replay_from_state(states[('normal','compact')],len(truth));rich_pred=m.replay_from_state(states[('normal','rich')],len(truth))
  with (td/'autonomous_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.writer(f);w.writerow(['replay_time_s',*[f'teacher_{a}_rad' for a in AXES],*[f'compact_{a}_rad' for a in AXES],*[f'rich_{a}_rad' for a in AXES]]);w.writerows([[float(tv),*map(float,y),*map(float,c),*map(float,r)] for tv,y,c,r in zip(t,truth,compact_pred,rich_pred)])
  for model,pred in (('compact',compact_pred),('rich',rich_pred)):
   save_json(td/f'playback_{model}.json',{'schema':'fly-wings-result-v1','fps':25,'duration_s':2,'trajectory':obj,'samples':[{'t':float(tv),'teacher_deg':list(map(float,y)),'prediction_deg':list(map(float,q*180/np.pi))} for tv,y,q in zip(t,deg,pred)],'method':f'matched encoder ablation: {model} state -> delay -> replay'})
  print(f'Ablation holdout {h["index"]}/5.',flush=True)
 models={}
 for model in ('compact','rich'):
  means={condition:float(np.mean([r['conditions'][condition][model]['rmse_rad'] for r in rows])) for condition in ('normal','static','shuffled','reversed','closed')};means['zero']=float(np.mean([r['zero']['rmse_rad'] for r in rows]));diffs={name:means['normal']-means[name] for name in ('zero','static','shuffled','reversed','closed')};models[model]={'mean_rmse_rad':means,'normal_minus_control_rmse_rad':diffs,'temporal_primary_pass':all(diffs[n]<0 for n in ('zero','static','shuffled','reversed'))}
 rich_minus_compact=models['rich']['mean_rmse_rad']['normal']-models['compact']['mean_rmse_rad']['normal'];wins=sum(r['conditions']['normal']['rich']['rmse_rad']<r['conditions']['normal']['compact']['rmse_rad'] for r in rows);primary=rich_minus_compact<0 and wins>=4 and models['rich']['temporal_primary_pass'];aggregate={'models':models,'rich_minus_compact_normal_rmse_rad':rich_minus_compact,'rich_better_than_compact':wins,'primary_pass':primary};report={'schema':'matched-encoder-ablation-result-v1','created_utc':datetime.now(timezone.utc).isoformat(),'status':'fixture_completed' if p['mode']=='fixture' else 'completed','protocol':p,'compact_training_episodes':state['adam']['seen'],'compact_optimizer_steps':state['adam']['step'],'source_rich_model_sha256':summary67['model_sha256'],'compact_model_sha256':file_sha(temp/'compact_model.npz'),'aggregate':aggregate,'holdouts':rows,'limitations':['Rich модель ранее показала положительный результат; новая батарея закреплена до compact training.','Сравнение разделяет encoder при одном training stream, но остаётся synthetic matched опытом.','Обе модели используют artificial state и cosine replay, не мозг или мышцы.']};save_json(temp/'summary.json',report);lines=['СЕРИЯ 69: MATCHED ENCODER ABLATION','',f'Compact/rich normal RMSE: {models["compact"]["mean_rmse_rad"]["normal"]:.6f} / {models["rich"]["mean_rmse_rad"]["normal"]:.6f}.',f'Rich minus compact: {rich_minus_compact:+.6f} рад.',f'Rich лучше compact: {wins}/5.',f'Rich temporal primary: {models["rich"]["temporal_primary_pass"]}.',f'Составной ablation primary: {"ДА" if primary else "НЕТ"}.','','Обе модели получили один и тот же training stream и одинаковые target/optimizer settings.',*report['limitations']];(temp/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');files={str(q.relative_to(temp)).replace('\\','/'):file_sha(q) for q in temp.rglob('*') if q.is_file()};save_json(temp/'complete.json',{'files':files});temp.rename(out);return out

def process(folder,max_batches=None):
 folder,dbp,p,state=read_state(folder);source=source67(p['source_series67'],p['mode']=='fixture');m,source_folder,source_db,p67,state67,summary67,rich_w,ids,motions,rgb,src=source;large=src[3]
 if sha(canonical(p67).encode())!=p['source_series67_protocol_sha256'] or summary67['model_sha256']!=p['source_rich_model_sha256']:raise ValueError('Source серии 67 изменился.')
 large.job_guard()
 with large.RunLock(folder):
  if state['stage']=='completed':verify_result(folder/'result');print('Ablation уже завершён.');return
  if state['stage']=='evaluation':
   out=evaluate(folder,p,state,source)
   with sqlite3.connect(dbp) as db:db.execute("UPDATE state SET stage='completed' WHERE id=1")
   print('Готово:',out);return
  free_check(large,folder,p['mode']=='fixture');target=len(ids);position=state['position'];adam=state['adam'];prior=state['elapsed'];started=time.monotonic();batches=0;batch_size=2 if p['mode']=='fixture' else BATCH
  with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(p67['source_series59'],)) as pool:
   while position<target:
    pause=folder/'pause.request'
    if pause.exists():pause.unlink();print('Пауза: checkpoint сохранён.');return
    if max_batches is not None and batches>=max_batches:print('Fixture остановлена после партии.');return
    batch_ids=ids[position:min(position+batch_size,target)];generated=list(pool.map(worker_episode,batch_ids));records=[];xs=[];ys=[]
    for expected,(ident,digest,x,y) in zip(batch_ids,generated):
     if ident!=expected or digest!=rgb[ident]:raise ValueError('RGB training stream не совпадает с серией 67.')
     records.append((position+len(records),ident,digest));xs.append(x);ys.append(y)
    loss=update(adam,np.stack(xs),np.stack(ys));elapsed=prior+time.monotonic()-started;commit(dbp,position,records,adam,elapsed,loss);position+=len(records);batches+=1;rate=position/max(elapsed,1e-9);print(f'Compact encoder {position}/{target}; loss {loss:.6g}; остаток {(target-position)/max(rate,1e-9)/3600:.2f} ч.',flush=True)
  with sqlite3.connect(dbp) as db:db.execute("UPDATE state SET stage='evaluation' WHERE id=1")
  folder,dbp,p,state=read_state(folder);out=evaluate(folder,p,state,source)
  with sqlite3.connect(dbp) as db:db.execute("UPDATE state SET stage='completed' WHERE id=1")
  print('Готово:',out)
  if os.name=='nt':
   try:os.startfile(str(out))
   except OSError:pass

def start(folder,source,holdouts,fixture=False,max_batches=None):
 data=source67(source,fixture);m,source_folder,source_db,p67,state67,summary67,rich_w,ids,motions,rgb,src=data;stim=src[2];large=src[3];blocked=set(m.PRIOR_HOLDOUT_MOTIONS)|set(OLD_AND_REPLICATED)|motions;items=freeze(holdouts,stim,blocked)
 if fixture and len(ids)>16:ids=ids[:4]
 protocol={'schema':'matched-encoder-ablation-v1','mode':'fixture' if fixture else 'full','script_sha256':file_sha(__file__),'runner67_sha256':RUNNER67_SHA,'source_series67':str(source_folder),'source_series67_protocol_sha256':sha(canonical(p67).encode()),'source_rich_model_sha256':summary67['model_sha256'],'training_stream_episodes':len(ids),'compact_encoder':{'units':COMPACT_UNITS,'projection_seed':6601,'level_features':CDIM},'rich_encoder':p67['observer'],'optimizer':{'name':'Adam','learning_rate':LR,'weight_decay':WEIGHT_DECAY},'holdouts':[{'index':x['index'],'copy':f'input/holdout_{x["index"]:03d}.json','basename':x['basename'],'source_sha256':x['source_sha256'],'motion_sha256':x['motion_sha256']} for x in items],'primary_rule':'rich mean normal RMSE below compact, rich wins at least 4/5, and rich temporal primary passes','replay_access':'both models create 72 coefficient state; replay receives state and phase only'}
 folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True);free_check(large,folder.parent,fixture);create(folder,protocol,items)
 if fixture:
  # Restrict the copied source stream through a private protocol field used only by bounded tests.
  with sqlite3.connect(folder/'study.sqlite3') as db:
   protocol['fixture_ids']=ids;txt=canonical(protocol);db.execute("UPDATE metadata SET value=? WHERE key='protocol'",(txt,));db.execute("UPDATE metadata SET value=? WHERE key='protocol_sha256'",(sha(txt.encode()),))
 print('Новая батарея закреплена; compact и rich сравниваются на одном stream.',flush=True);process(folder,max_batches)
def request_pause(folder):
 folder,dbp,p,state=read_state(folder);large=source67(p['source_series67'],p['mode']=='fixture')[-1][3]
 if state['stage']!='training':raise ValueError('Обучение compact уже закончено.')
 try:
  with large.RunLock(folder):pass
 except ValueError:pass
 else:raise ValueError('Ablation сейчас не работает.')
 (folder/'pause.request').write_text('pause\n',encoding='utf8');print('Запрос паузы записан.')
def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox,simpledialog
 root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
 try:
  action=simpledialog.askinteger('Серия 69','Введите номер:\n1: начать\n2: продолжить\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
  if action is None:return
  if action in (2,3):
   folder=filedialog.askdirectory(title='Папка matched_encoder_ablation_...',initialdir=str(ROOT.resolve()) if ROOT.exists() else str(Path.cwd()),parent=root)
   if not folder:return
   return process(folder) if action==2 else request_pause(folder)
  source=filedialog.askdirectory(title='Успешная серия 67 piecewise_rich_replay_...',initialdir=str(SOURCE_ROOT.resolve()) if SOURCE_ROOT.exists() else str(Path.cwd()),parent=root)
  if not source:return
  messagebox.showinfo('Новая батарея','Выберите пять новых random JSON. Движения 31–35 и 41–45 запрещены.',parent=root);hold=list(filedialog.askopenfilenames(title='Пять новых JSON ablation',filetypes=[('Траектория JSON','*.json')],parent=root))
  if len(hold)!=5:raise ValueError(f'Выбрано {len(hold)}, нужно 5.')
  folder=ROOT/('matched_encoder_ablation_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);start(folder,source,hold)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--choose',action='store_true');g.add_argument('--new');g.add_argument('--resume');g.add_argument('--pause');p.add_argument('--source');p.add_argument('--holdouts',nargs='*');p.add_argument('--fixture',action='store_true',help=argparse.SUPPRESS);p.add_argument('--batches',type=int,help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:return choose()
 if a.new:
  if not a.source or len(a.holdouts or [])!=5:p.error('Нужны source и пять holdout.')
  return start(a.new,a.source,a.holdouts,a.fixture,a.batches)
 if a.resume:return process(a.resume,a.batches)
 return request_pause(a.pause)
if __name__=='__main__':
 multiprocessing.freeze_support()
 try:sys.exit(main() or 0)
 except Exception as exc:print(f'ОШИБКА СЕРИИ 69: {type(exc).__name__}: {exc}\nSource и holdout не изменялись.',file=sys.stderr,flush=True);sys.exit(1)
