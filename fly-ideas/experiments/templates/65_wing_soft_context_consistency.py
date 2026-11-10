#!/usr/bin/env python3
"""Series 65: train one frozen soft-consistency right_x model.

The original series-59 training set remains intact. A fixed penalty discourages
right_x prediction changes between original and counterfactual context images.
No new holdout is evaluated or used to choose the penalty in this series.
"""
from __future__ import annotations
import argparse,concurrent.futures
from datetime import datetime,timezone
import hashlib,importlib.util,io,json,math,multiprocessing,os
from pathlib import Path
import shutil,sqlite3,sys,time,uuid,zipfile
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
REP64=HERE/'64_wing_context_invariant_replication.py'
REP64_SHA='7e88c46704b889c2b0cd8903730f0f3a5fa0ef89835928bfa2c9094c0d8bb6bc'
ROOT=Path('workspace/runs/ideas/i-observational/wing-soft-consistency')
SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/wing-context-invariant')
DIM=576;TARGET=3;LAMBDA=0.1;MIN_RAM=4*1024**3;MIN_DISK=2*1024**3


def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def load64():
    if file_sha(REP64)!=REP64_SHA:raise ValueError('Закреплённый скрипт серии 64 изменился.')
    spec=importlib.util.spec_from_file_location('soft_consistency_rep64',REP64);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def output_manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}
def pack_delta(frames,dxx):
    dxx=np.asarray(dxx,dtype=np.float64)
    if type(frames)!=int or frames<0 or dxx.shape!=(DIM,DIM) or not np.isfinite(dxx).all():raise ValueError('Некорректные consistency-статистики.')
    mem=io.BytesIO();np.savez_compressed(mem,frames=np.array(frames,dtype=np.int64),dxx=dxx);return mem.getvalue()
def unpack_delta(blob,digest):
    if sha(blob)!=digest or len(blob)>32*1024*1024:raise ValueError('SHA consistency-статистик не совпадает.')
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if sum(x.file_size for x in z.infolist())>16*1024*1024:raise ValueError('Consistency-архив слишком велик.')
    with np.load(io.BytesIO(blob),allow_pickle=False) as z:
        if set(z.files)!={'frames','dxx'} or z['frames'].shape!=() or z['frames'].dtype.kind not in 'iu':raise ValueError('Некорректный consistency-архив.')
        frames=int(z['frames']);dxx=np.array(z['dxx'],dtype=np.float64,copy=True)
    if frames<0 or dxx.shape!=(DIM,DIM) or not np.isfinite(dxx).all():raise ValueError('Некорректные consistency-статистики.')
    return frames,dxx


def source_info(folder):
    rep=load64();ci,runner,proto,ev,stim,source_folder,result,protocol,summary,control,invariant,blocked=rep.verify_source(folder)
    if protocol['mode'] not in ('full','fixture'):raise ValueError('Некорректный режим серии 63.')
    source59=ci.source_state(protocol['source_series']);source_db=source59[8]
    ids=ci.selected_ids(source_db,protocol['train_count'],protocol['replacement_count'])
    if len(ids)!=protocol['replacement_count']:raise ValueError('Список пар серии 63 изменился.')
    blocked={x['motion_sha256'] for x in source59[13]}|{protocol['holdout_motion_sha256']}
    return rep,ci,runner,proto,ev,stim,source_folder,result,protocol,summary,control,source59,source_db,ids,blocked


def make_protocol(info,fixture_limit=None):
    rep,ci,runner,proto,ev,stim,folder,result,source_protocol,summary,control,source59,source_db,ids,blocked=info
    if fixture_limit is not None:
        if type(fixture_limit)!=int or not 1<=fixture_limit<=min(8,len(ids)):raise ValueError('Fixture допускает 1–8 пар.')
        ids=ids[:fixture_limit]
    protocol={'schema':'wing-soft-context-consistency-v1','mode':'fixture' if fixture_limit is not None else 'full','script_sha256':file_sha(__file__),'replication64_script_sha256':REP64_SHA,
      'source_series63':str(folder),'source_series63_protocol_sha256':sha(canonical(source_protocol).encode()),'source_series59_database_sha256':file_sha(source_db),'source_control_model_sha256':summary['control_model_sha256'],
      'target_axis':'right_x','consistency_lambda':LAMBDA,'ridge_lambda':1.0,'pair_rule':source_protocol['replacement_rule'],'donor_offset':source_protocol['donor_offset'],'pair_count':len(ids),'fixture_limit':fixture_limit,
      'objective':'mean original supervised squared error + ridge + 0.1 * mean paired prediction-difference squared error','holdout_policy':'No new holdout is loaded or evaluated in series 65.','workers':2}
    return protocol,ids


def create(folder,protocol):
    folder=Path(folder);folder.parent.mkdir(parents=True,exist_ok=True);folder.mkdir(exist_ok=False);db=folder/'study.sqlite3';blob=pack_delta(0,np.zeros((DIM,DIM)))
    text=canonical(protocol)
    with sqlite3.connect(db) as conn:
        conn.execute('PRAGMA journal_mode=DELETE');conn.execute('PRAGMA synchronous=FULL')
        conn.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT NOT NULL)');conn.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1),next_index INTEGER NOT NULL,elapsed REAL NOT NULL,pair_frames INTEGER NOT NULL,delta BLOB NOT NULL,delta_sha256 TEXT NOT NULL,stage TEXT NOT NULL)')
        conn.execute('CREATE TABLE pairs (position INTEGER PRIMARY KEY,candidate_id INTEGER UNIQUE NOT NULL,donor_id INTEGER NOT NULL,original_rgb_sha256 TEXT NOT NULL,counterfactual_rgb_sha256 TEXT NOT NULL)')
        conn.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','wing-soft-context-consistency-checkpoint-v1'),('protocol',text),('protocol_sha256',sha(text.encode()))])
        conn.execute("INSERT INTO state VALUES (1,0,0,0,?,?, 'training')",(blob,sha(blob)))
    return db


def read_state(folder):
    folder=Path(folder).resolve();db=folder/'study.sqlite3'
    if not db.is_file():raise ValueError('Не найдена база серии 65.')
    with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as conn:
        if conn.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError('SQLite не прошла quick_check.')
        meta=dict(conn.execute('SELECT key,value FROM metadata').fetchall());row=conn.execute('SELECT next_index,elapsed,pair_frames,delta,delta_sha256,stage FROM state WHERE id=1').fetchone();count=conn.execute('SELECT COUNT(*) FROM pairs').fetchone()[0]
    if set(meta)!={'schema','protocol','protocol_sha256'} or meta['schema']!='wing-soft-context-consistency-checkpoint-v1' or sha(meta['protocol'].encode())!=meta['protocol_sha256']:raise ValueError('Повреждён протокол серии 65.')
    protocol=json.loads(meta['protocol']);expected={**protocol,'script_sha256':file_sha(__file__),'replication64_script_sha256':REP64_SHA}
    if canonical(expected)!=meta['protocol']:raise ValueError('Скрипт или протокол серии 65 изменился.')
    if not row or row[0]!=count or row[5] not in ('training','fitting','completed') or not 0<=row[0]<=protocol['pair_count'] or not math.isfinite(row[1]) or row[1]<0:raise ValueError('Повреждено состояние серии 65.')
    frames,dxx=unpack_delta(row[3],row[4])
    if frames!=row[2]:raise ValueError('Число парных кадров не согласуется.')
    return folder,db,protocol,{'next_index':row[0],'elapsed':row[1],'pair_frames':frames,'dxx':dxx,'stage':row[5]}


def free_check(large,folder,fixture):
    if fixture:return
    ram=large.available_ram()
    if ram is None:raise OSError('Не удалось измерить свободную RAM.')
    if ram<MIN_RAM:raise MemoryError(f'Свободно {ram/1024**3:.2f} ГиБ RAM, нужно не менее 4 ГиБ.')
    if shutil.disk_usage(folder).free<MIN_DISK:raise OSError('Свободно менее 2 ГиБ на диске.')


WORKER_CI=None
def worker_init(train,blocked):
    global WORKER_CI
    rep=load64();ci=rep.load63();ci.worker_init(train,blocked);WORKER_CI=ci
def worker_pair(ident):
    rec,x0,y0,x1,y1=WORKER_CI.worker_replace(ident)
    if x0.shape!=x1.shape or y0.shape!=y1.shape or not np.array_equal(y0[:,TARGET],y1[:,TARGET]):raise ValueError('Парная замена изменила target.')
    dx=x0-x1
    return rec,len(dx),dx.T@dx


def commit(db,expected,records,frames,dxx,elapsed):
    blob=pack_delta(frames,dxx)
    with sqlite3.connect(db,timeout=30) as conn:
        conn.execute('PRAGMA synchronous=FULL');row=conn.execute('SELECT next_index,elapsed,stage FROM state WHERE id=1').fetchone()
        if row[0]!=expected or row[2]!='training' or elapsed<row[1]:raise ValueError('Контрольная точка изменилась.')
        conn.executemany('INSERT INTO pairs VALUES (?,?,?,?,?)',[(expected+i,r['candidate_id'],r['donor_id'],r['original_rgb_sha256'],r['counterfactual_rgb_sha256']) for i,r in enumerate(records)])
        conn.execute('UPDATE state SET next_index=?,elapsed=?,pair_frames=?,delta=?,delta_sha256=? WHERE id=1',(expected+len(records),elapsed,frames,blob,sha(blob)))


def fit_model(info,state,base,ev):
    source_stats=info[11][10]['stats'];control=info[10]
    mean,scale,intercept,weights=base.fit(source_stats)
    for key,value in {'mean':mean,'scale':scale,'intercept':intercept,'weights':weights}.items():
        if not np.allclose(value,control[key],rtol=0,atol=1e-12):raise ValueError('Контрольная модель не воспроизведена.')
    n=source_stats['n'];cov=(source_stats['sxx']/n-np.outer(mean,mean))/np.outer(scale,scale);rhs=(source_stats['sxy']/n-np.outer(mean,intercept))/scale[:,None]
    delta_cov=(state['dxx']/state['pair_frames'])/np.outer(scale,scale)
    soft_weights=weights.copy();soft_weights[:,TARGET]=np.linalg.solve(cov+base.RIDGE*np.eye(DIM)+LAMBDA*delta_cov,rhs[:,TARGET])
    soft=ev.checked_model({'mean':mean,'scale':scale,'intercept':intercept,'weights':soft_weights})
    wc=weights[:,TARGET];ws=soft_weights[:,TARGET]
    diagnostics={'pair_frames':state['pair_frames'],'control_mean_squared_pair_difference':float(wc@delta_cov@wc),'soft_mean_squared_pair_difference':float(ws@delta_cov@ws),'relative_pair_difference_change_percent':float(100*(ws@delta_cov@ws/(wc@delta_cov@wc)-1))}
    return control,soft,diagnostics


def publish(folder,protocol,state,info,base,ev):
    out=folder/'result'
    if out.exists():
        complete=json.loads((out/'complete.json').read_text(encoding='utf8'));files=output_manifest(out)
        if complete.get('protocol_sha256')!=sha(canonical(protocol).encode()) or complete.get('files')!=files:raise ValueError('Контрольные суммы результата не совпадают.')
        return out
    control,soft,diag=fit_model(info,state,base,ev);temp=folder/('result_incomplete_'+uuid.uuid4().hex);temp.mkdir();np.savez_compressed(temp/'model_control.npz',**control);np.savez_compressed(temp/'model_soft_consistency.npz',**soft)
    report={'schema':'wing-soft-context-consistency-result-v1','created_utc':datetime.now(timezone.utc).isoformat(),'status':'fixture_completed' if protocol['mode']=='fixture' else 'completed','protocol':protocol,'pairs_completed':state['next_index'],'active_pair_seconds':state['elapsed'],'control_model_sha256':file_sha(temp/'model_control.npz'),'soft_model_sha256':file_sha(temp/'model_soft_consistency.npz'),'diagnostics':diag,'primary_holdout_result':None,'limitations':['Серия 65 только обучает заранее заданную модель и не проверяет её на новом holdout.','Consistency-пары синтетические и могут быть вне распределения.','Диагностика пар измерена на обучающих контрфактах и не является оценкой обобщения.','Supervised ridge и условные камеры не доказывают зеркальные нейроны или автономное воспроизведение.']}
    save_json(temp/'summary.json',report)
    lines=['СЕРИЯ 65: МЯГКАЯ CONTEXT-CONSISTENCY МОДЕЛЬ RIGHT_X','',f'Пары завершены: {state["next_index"]}; парных кадров: {state["pair_frames"]}.',f'Заранее закреплённый lambda consistency: {LAMBDA}.',f'Средний квадрат изменения прогноза на обучающих парах, контроль / soft: {diag["control_mean_squared_pair_difference"]:.8f} / {diag["soft_mean_squared_pair_difference"]:.8f}.',f'Изменение парной чувствительности: {diag["relative_pair_difference_change_percent"]:+.2f}%.','', 'Новый holdout не загружался и не оценивался. Теперь нужна следующая новая батарея движений.','Модели: model_control.npz и model_soft_consistency.npz.','',*report['limitations']]
    (temp/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(canonical(protocol).encode()),'files':output_manifest(temp)});temp.rename(out);return out


def process(folder,max_batches=None):
    folder,db,protocol,state=read_state(folder);info=source_info(protocol['source_series63']);rep,ci,runner,proto,ev,stim,source_folder,result,source_protocol,summary,control,source59,source_db,all_ids,blocked=info
    if sha(canonical(source_protocol).encode())!=protocol['source_series63_protocol_sha256'] or file_sha(source_db)!=protocol['source_series59_database_sha256']:raise ValueError('Исходная серия изменилась.')
    ids=all_ids[:protocol['pair_count']];base=source59[5];large=source59[6];fixture=protocol['mode']=='fixture';large.job_guard()
    with large.RunLock(folder):
        if state['stage']=='completed':publish(folder,protocol,state,info,base,ev);print('Серия уже завершена:',folder/'result',flush=True);return
        free_check(large,folder,fixture);done=state['next_index'];frames=state['pair_frames'];dxx=state['dxx'];prior=state['elapsed'];started=time.monotonic();batches=0
        if state['stage']=='training':
            with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init,initargs=(source59[12],blocked)) as pool:
                while done<len(ids):
                    pause=folder/'pause.request'
                    if pause.exists():pause.unlink();print('Пауза: последняя пара сохранена.',flush=True);return
                    if max_batches is not None and batches>=max_batches:print('Fixture остановлена после партии.',flush=True);return
                    free_check(large,folder,fixture);batch_ids=ids[done:done+2];generated=list(pool.map(worker_pair,batch_ids));records=[]
                    with sqlite3.connect(source_db.resolve().as_uri()+'?mode=ro',uri=True) as conn:expected=dict(conn.execute(f"SELECT id,rgb_sha256 FROM candidates WHERE id IN ({','.join('?' for _ in batch_ids)})",batch_ids))
                    for ident,(rec,n,part) in zip(batch_ids,generated):
                        if rec['candidate_id']!=ident or rec['original_rgb_sha256']!=expected.get(ident):raise ValueError('Исходный RGB кандидата не воспроизведён.')
                        frames+=n;dxx+=part;records.append(rec)
                    elapsed=prior+time.monotonic()-started;commit(db,done,records,frames,dxx,elapsed);done+=len(records);batches+=1;print(f'Сохранено consistency-пар {done}/{len(ids)}.',flush=True)
            with sqlite3.connect(db) as conn:conn.execute("UPDATE state SET stage='fitting' WHERE id=1 AND stage='training'")
            folder,db,protocol,state=read_state(folder)
        if state['stage']=='fitting':
            out=publish(folder,protocol,state,info,base,ev)
            with sqlite3.connect(db) as conn:conn.execute("UPDATE state SET stage='completed' WHERE id=1 AND stage='fitting'")
            print('Готово:',out,flush=True)
            if os.name=='nt':
                try:os.startfile(str(out))
                except OSError:pass


def start(folder,source,fixture_limit=None,max_batches=None):
    info=source_info(source);protocol,ids=make_protocol(info,fixture_limit);parent=Path(folder).parent;parent.mkdir(parents=True,exist_ok=True);free_check(info[11][6],parent,fixture_limit is not None);create(folder,protocol);print('Протокол закреплён. Новый holdout в серии 65 не используется.',flush=True);process(folder,max_batches)
def request_pause(folder):
    folder=Path(folder).resolve();_,_,protocol,state=read_state(folder);info=source_info(protocol['source_series63']);large=info[11][6]
    if state['stage']!='training':raise ValueError('Обучение пар уже закончено.')
    try:
        with large.RunLock(folder):pass
    except ValueError:pass
    else:raise ValueError('Серия сейчас не работает.')
    (folder/'pause.request').write_text('pause\n',encoding='utf8');print('Запрос паузы записан.',flush=True)


def choose():
    import tkinter as tk
    from tkinter import filedialog,messagebox,simpledialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    try:
        action=simpledialog.askinteger('Серия 65','Введите номер:\n1: начать\n2: продолжить\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
        if action is None:return
        if action in (2,3):
            folder=filedialog.askdirectory(title='Папка wing_soft_consistency_...',initialdir=str(ROOT.resolve()) if ROOT.exists() else str(Path.cwd()),parent=root)
            if not folder:return
            return process(folder) if action==2 else request_pause(folder)
        messagebox.showinfo('Исходная серия','Выберите завершённую папку wing_context_invariant_... серии 63. Новые holdout сейчас не выбираются.',parent=root)
        source=filedialog.askdirectory(title='Завершённая серия 63',initialdir=str(SOURCE_ROOT.resolve()) if SOURCE_ROOT.exists() else str(Path.cwd()),parent=root)
        if not source:return
        messagebox.showinfo('Перед запуском','Будут заново обработаны 30046 закреплённых пар. Два процесса, пауза через тот же BAT. Серия обучит модель, но не оценит новый holdout.',parent=root)
        folder=ROOT/('wing_soft_consistency_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);start(folder,source)
    finally:root.destroy()


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--choose',action='store_true');g.add_argument('--new');g.add_argument('--resume');g.add_argument('--pause')
    p.add_argument('--source');p.add_argument('--fixture-limit',type=int,help=argparse.SUPPRESS);p.add_argument('--batches',type=int,help=argparse.SUPPRESS);a=p.parse_args()
    if a.choose:return choose()
    if a.new:
        if not a.source:p.error('Нужен --source.')
        return start(a.new,a.source,a.fixture_limit,a.batches)
    if a.resume:return process(a.resume,a.batches)
    return request_pause(a.pause)

if __name__=='__main__':
    multiprocessing.freeze_support()
    try:sys.exit(main() or 0)
    except Exception as exc:print(f'ОШИБКА СЕРИИ 65: {type(exc).__name__}: {exc}\nИсходные серии не изменялись. Если папка серии 65 создана, последняя партия сохранена.',file=sys.stderr,flush=True);sys.exit(1)
