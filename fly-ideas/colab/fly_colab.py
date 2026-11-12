"""Shiu v630 on Colab: independent CPU series, immutable Drive checkpoints, GPU pilot.

The three reference scripts are copied unmodified beside this file. No external
SQLite is imported. Drive checkpoint files are new immutable files, not a live DB.
"""
import argparse
import concurrent.futures
import csv
import datetime
import gzip
import hashlib
import importlib.util
import json
import math
import multiprocessing
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time
import uuid

for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_key]='1'
TOTAL=8*201*30
CONNECTION='2023_03_23_connectivity_630_final.parquet'
NEURONS='2023_03_23_completeness_630_final.csv'
SCRIPT_SHA={'25_shiu_v630_control.py':'b5f200a3e9472c9aa6318acab8b5fb928d23af3b458c2d43fc29909241e95711',
            '27_shiu_top200_v630.py':'e630558dbb35e34d5af45bde417e1b91d36e2c6a7c4417e87be27fa2565b2f08',
            '28_shiu_lesions_v630.py':'fdedb0ac3c7b81692b44c6b5f07f2e2142e3af1617db179426de3b250b57dd93',
            '30_shiu_lesion_overview.py':'881b0a654be06ec4b6fb295d5a0247591a4b54083f0cd7ffbe3a0358659c6638'}
_DATA=None
_BASE=None
_LESION=None


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def load_reference():
    folder=Path(__file__).resolve().parent
    for name,expected in SCRIPT_SHA.items():
        if sha(folder/name)!=expected: raise ValueError('Не совпадает контрольная сумма кода: '+name)
    spec=importlib.util.spec_from_file_location('fly_colab_lesion',folder/'28_shiu_lesions_v630.py')
    lesion=importlib.util.module_from_spec(spec);spec.loader.exec_module(lesion)
    top=lesion.load_top();return lesion,top,top.base_module()


def verify_top(lesion,top,base,data,hashes,folder):
    """Validate the original top under its recorded environment, without claiming it ran here."""
    import numpy as np
    report=json.loads((folder/'summary.json').read_text(encoding='utf8'))
    if report.get('status')!='ok' or report.get('mode')!='simulation' or report.get('result',{}).get('trials')!=30:
        raise ValueError('Нужна папка полного топ-200 на 30 повторов.')
    old=report.get('protocol',{})
    versions={k:old.get(k) for k in ('python','brian2','numpy')}
    if any(not isinstance(v,str) or not v for v in versions.values()): raise ValueError('Нет версий исходного топа.')
    expected={'schema':1,'connection_sha256':hashes['connections']['sha256'],'neuron_sha256':hashes['neurons']['sha256'],
              'script_sha256':lesion.TOP_SHA,'base_sha256':top.BASE_SHA256,**versions,'side':'right','frequency_hz':200,
              'duration_ms':1000,'dt_ms':0.1,'seeds':lesion.SEEDS}
    if old!=expected: raise ValueError('Протокол отбора не соответствует авторским данным или коду.')
    counts=top.read_checkpoint(folder,expected,len(data['ids']))
    if sorted(counts)!=lesion.SEEDS: raise ValueError('Нужны все 30 повторов топа.')
    total=np.zeros(len(data['ids']),dtype=np.int64)
    for c,_ in counts.values(): total+=c
    order=sorted(np.flatnonzero(total>0).tolist(),key=lambda i:(-int(total[i]),int(data['ids'][i])))
    if len(order)<200 or report['result'].get('active_neurons')!=len(order) or report['result'].get('cutoff_rate_hz')!=int(total[order[199]])/30:
        raise ValueError('Итог топ-200 не соответствует повторам.')
    with (folder/'top200.csv').open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=['rank','root_id','mean_rate_hz','total_spikes_30_trials']: raise ValueError('Неправильная таблица top200.csv.')
        rows=list(reader)
    if len(rows)!=200: raise ValueError('В топе должно быть ровно 200 строк.')
    for rank,(row,i) in enumerate(zip(rows,order[:200]),1):
        if row['rank']!=str(rank) or row['root_id']!=data['ids'][i] or row['total_spikes_30_trials']!=str(int(total[i])) or not math.isclose(float(row['mean_rate_hz']),int(total[i])/30,rel_tol=1e-12,abs_tol=1e-12):
            raise ValueError('Таблица топ-200 не соответствует повторам: строка '+str(rank))
    return [data['ids'][i] for i in order[:200]], old


def prepare(root,local,store):
    import numpy as np
    import brian2 as b2
    lesion,top,base=load_reference()
    inputs=root/'01_Исходные_файлы';folder=inputs/'top200';local_input=local/'inputs';local_input.mkdir()
    copied={}
    for filename in (CONNECTION,NEURONS):
        source=inputs/filename
        if not source.is_file(): raise ValueError('Нет файла на Диске: '+str(source))
        destination=local_input/filename;print('Копируем',filename,'на временный диск Colab...',flush=True)
        shutil.copyfile(source,destination);copied[filename]=destination
    local_top=local_input/'top200';local_top.mkdir()
    for name in ['summary.json','checkpoint.json','top200.csv']+[f'counts_seed_{i:02d}.npy' for i in range(30)]:
        if not (folder/name).is_file(): raise ValueError('В папке top200 не найден файл: '+name)
        shutil.copyfile(folder/name,local_top/name)
    hashes={'connections':base.fingerprint(copied[CONNECTION]),'neurons':base.fingerprint(copied[NEURONS])}
    if any(hashes[k]['git_blob_sha1']!=v for k,v in base.EXPECTED.items()): raise ValueError('Авторские файлы v630 не совпадают с контрольными суммами.')
    print('Проверяем таблицы и все повторы топ-200...',flush=True)
    data=base.validate_inputs(copied[CONNECTION],copied[NEURONS],store)
    for kind,name in [('connections',CONNECTION),('neurons',NEURONS)]:
        stat=copied[name].stat()
        if (stat.st_size,stat.st_mtime_ns)!=(hashes[kind]['bytes'],hashes[kind]['mtime_ns']): raise ValueError('Исходный файл изменился во время проверки: '+name)
    candidates,original_top=verify_top(lesion,top,base,data,hashes,local_top)
    meta={'schema':1,'connection_sha256':hashes['connections']['sha256'],'neuron_sha256':hashes['neurons']['sha256'],
          'top_script_sha256':lesion.TOP_SHA,'base_sha256':top.BASE_SHA256,'lesion_script_sha256':SCRIPT_SHA['28_shiu_lesions_v630.py'],
          'top_checkpoint_sha256':sha(local_top/'checkpoint.json'),'top_csv_sha256':sha(local_top/'top200.csv'),
          'python':sys.version.split()[0],'brian2':b2.__version__,'numpy':np.__version__,'candidates':candidates,
          'frequencies_hz':lesion.FREQS,'seeds':lesion.SEEDS,'side':'right','duration_ms':1000,'dt_ms':0.1}
    return lesion,top,base,data,meta,original_top


def checkpoint_list(folder):
    """Unpublished .pending files are ignored; damaged markers or branches stop."""
    records={}
    for path in folder.glob('checkpoint_*.json'):
        try:
            info=json.loads(path.read_text(encoding='utf8'))
            if info.get('format')!='fly-colab-cpu-checkpoint-1' or info.get('id')!=path.stem: raise ValueError()
            if not isinstance(info.get('sha256'),str) or not isinstance(info.get('rows'),int): raise ValueError()
            records[info['id']]=info
        except (ValueError,OSError,TypeError) as exc:
            raise ValueError('Метка снимка повреждена: '+path.name+'. Автоматический откат запрещён.') from exc
    if not records: return records,None
    parents=[v.get('parent') for v in records.values()]
    if parents.count(None)!=1 or any(p is not None and p not in records for p in parents):
        raise ValueError('История снимков неполна или имеет несколько корней. Автоматическое продолжение остановлено.')
    children={k:[] for k in records}
    for ident,v in records.items():
        if v['parent'] is not None: children[v['parent']].append(ident)
    if any(len(v)>1 for v in children.values()): raise ValueError('Обнаружены две ветки снимков. Не запускайте две сессии и не объединяйте их автоматически.')
    leaves=[k for k,v in children.items() if not v]
    if len(leaves)!=1: raise ValueError('История снимков имеет несколько окончаний.')
    seen=set();cur=leaves[0]
    while cur is not None:
        if cur in seen: raise ValueError('Цикл в истории снимков.')
        seen.add(cur);cur=records[cur]['parent']
    if len(seen)!=len(records): raise ValueError('История снимков повреждена.')
    return records,leaves[0]


def make_snapshot(db,folder,parent):
    folder.mkdir(parents=True,exist_ok=True)
    _,latest=checkpoint_list(folder)
    if latest!=parent: raise ValueError('Снимки на Диске изменились в другой сессии. Расчёт остановлен, ветви не объединяются.')
    ident='checkpoint_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex
    target=folder/(ident+'.sqlite.gz');marker=folder/(ident+'.json');pending=folder/(ident+'.pending')
    with tempfile.TemporaryDirectory() as temp:
        snapshot=Path(temp)/'snapshot.sqlite3'
        with sqlite3.connect(snapshot) as destination: db.backup(destination)
        count=db.execute('SELECT COUNT(*) FROM trials').fetchone()[0]
        with snapshot.open('rb') as source, target.open('xb') as raw:
            with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as zipped: shutil.copyfileobj(source,zipped,1024*1024)
            raw.flush();os.fsync(raw.fileno())
    checksum=sha(target)
    info={'format':'fly-colab-cpu-checkpoint-1','id':ident,'parent':parent,'rows':count,'sha256':checksum,
          'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'coordinator_sha256':sha(Path(__file__))}
    with pending.open('x',encoding='utf8') as f: json.dump(info,f,ensure_ascii=False,sort_keys=True);f.flush();os.fsync(f.fileno())
    if json.loads(pending.read_text(encoding='utf8'))!=info or sha(target)!=checksum: raise OSError('Не удалось перечитать снимок на Диске.')
    os.rename(pending,marker)  # .json появляется только после полной записи метки
    if json.loads(marker.read_text(encoding='utf8'))!=info: raise OSError('Не удалось проверить опубликованную метку.')
    print(f'Снимок на Google Диске: {count}/{TOTAL} ({ident})',flush=True)
    return ident


def restore_snapshot(folder,ident,record,destination,lesion,meta):
    target=folder/(ident+'.sqlite.gz')
    if not target.is_file() or sha(target)!=record['sha256']: raise ValueError('Последний сохранённый снимок повреждён; автоматический откат не выполняется.')
    old=destination/'resume';old.mkdir()
    with gzip.open(target,'rb') as source,(old/'lesions.sqlite3').open('xb') as f: shutil.copyfileobj(source,f,1024*1024)
    current=destination/'database';current.mkdir()
    db=lesion.open_db(current,meta,old)
    if db.execute('SELECT COUNT(*) FROM trials').fetchone()[0]!=record['rows']:
        db.close();raise ValueError('Количество повторов в снимке не совпадает.')
    return db


def load_overview():
    script=Path(__file__).resolve().parent/'30_shiu_lesion_overview.py'
    spec=importlib.util.spec_from_file_location('fly_overview',script);view=importlib.util.module_from_spec(spec);spec.loader.exec_module(view)
    return view


def export_latest(root,local):
    load_reference()  # контроль кода
    folder=root/'02_CPU_полный_план'/'checkpoints'
    records,last=checkpoint_list(folder)
    if last is None: raise ValueError('Сохранённых снимков CPU пока нет.')
    record=records[last];archive=folder/(last+'.sqlite.gz')
    if sha(archive)!=record['sha256']: raise ValueError('Последний снимок повреждён.')
    tmp=local/'lesions.sqlite3'
    with gzip.open(archive,'rb') as a,tmp.open('xb') as b: shutil.copyfileobj(a,b,1024*1024)
    view=load_overview()
    meta,rows=view.read_checked(tmp)
    if len(rows)!=record['rows']: raise ValueError('Неверное число повторов в снимке.')
    view.read_top(root/'01_Исходные_файлы'/'top200',meta)
    dest=root/'05_Экспорт_для_приложения'/('export_'+uuid.uuid4().hex[:12]);dest.mkdir(parents=True)
    with tmp.open('rb') as a,(dest/'lesions.sqlite3').open('xb') as b: shutil.copyfileobj(a,b,1024*1024);b.flush();os.fsync(b.fileno())
    if sha(dest/'lesions.sqlite3')!=sha(tmp): raise OSError('Не удалось проверить экспорт на Диске.')
    print(f'Проверенная база ({len(rows)}/{TOTAL}): {dest}',flush=True)


def available_bytes():
    import psutil
    avail=psutil.virtual_memory().available
    for limit,used in [('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory.current'),('/sys/fs/cgroup/memory/memory.limit_in_bytes','/sys/fs/cgroup/memory/memory.usage_in_bytes')]:
        try:
            l=Path(limit).read_text().strip();u=int(Path(used).read_text().strip())
            if l!='max': avail=min(avail,max(0,int(l)-u))
        except (OSError,ValueError): pass
    return avail


def worker(key):
    frequency,target,seed=key
    return _LESION.trial(_BASE,_DATA,frequency,seed,target)


def save_final(db,root,base,meta):
    folder=root/'03_Готовые_таблицы';folder.mkdir(exist_ok=True)
    out=folder/('results_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8]);out.mkdir()
    result=_LESION.save_results(db,out,base,meta['candidates'])
    (out/'summary.json').write_text(json.dumps({'status':'complete','total':TOTAL,'result':result,'protocol':meta},ensure_ascii=False,indent=2),encoding='utf8')
    print('Готовые таблицы:',out,flush=True)


def cpu_series(root,local,max_workers,every,max_trials=0):
    global _BASE,_DATA,_LESION
    _LESION,top,_BASE,_DATA,meta,top_env=prepare(root,local,True)
    print('Версии топ-200:',top_env['python'],top_env['numpy'],top_env['brian2'],'; версии Colab:',meta['python'],meta['numpy'],meta['brian2'],flush=True)
    folder=root/'02_CPU_полный_план'/'checkpoints';folder.mkdir(parents=True,exist_ok=True)
    records,last=checkpoint_list(folder)
    if last:
        if records[last].get('coordinator_sha256')!=sha(Path(__file__)): raise ValueError('Версия управляющего кода отличается от сохранённой. Продолжение остановлено.')
        db=restore_snapshot(folder,last,records[last],local,_LESION,meta)
    else:
        out=local/'database';out.mkdir();db=_LESION.open_db(out,meta,None)
        last=make_snapshot(db,folder,None)
    done=set(db.execute('SELECT frequency,target,seed FROM trials'));print(f'Сохранено: {len(done)}/{TOTAL}',flush=True)
    if len(done)==TOTAL:
        save_final(db,root,_BASE,meta);db.close();return
    avail=available_bytes();workers=2 if max_workers==2 and (os.cpu_count() or 1)>=2 and avail>=10*1024**3 else 1
    print(f'CPU процессов: {workers}; свободная память примерно {avail/1024**3:.1f} ГиБ. GPU в основной серии не используется.',flush=True)
    plan=((f,t,s) for f in _LESION.FREQS for t in ['']+meta['candidates'] for s in _LESION.SEEDS if (f,t,s) not in done)
    if max_trials:
        import itertools
        plan=itertools.islice(plan,max_trials)
    pending={};new_since=0;pool=None
    try:
        # fork передаёт данные на Linux без повторного чтения; отдельные сети всё равно требуют RAM.
        pool=concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('fork'))
        exhausted=False;stopping=False
        while pending or not exhausted:
            if not stopping and available_bytes()<2*1024**3:
                print('Недостаточно свободной памяти: завершаем начатые повторы и сохраняем снимок.',flush=True);stopping=True;exhausted=True
            while not exhausted and not stopping and len(pending)<workers:
                try: key=next(plan)
                except StopIteration: exhausted=True;break
                pending[pool.submit(worker,key)]=key
            if not pending: break
            complete,_=concurrent.futures.wait(pending,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in complete:
                freq,target,seed=pending.pop(future);left,right,seconds=future.result()
                db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(freq,target,seed,left,right,seconds,_LESION.row_hash(freq,target,seed,left,right,seconds)));db.commit()
                done.add((freq,target,seed));new_since+=1
                print(f'{len(done)}/{TOTAL}: {freq} Гц, {target or "контроль"}, seed {seed}',flush=True)
                if new_since>=every: last=make_snapshot(db,folder,last);new_since=0
        if new_since: last=make_snapshot(db,folder,last);new_since=0
        if len(done)==TOTAL: save_final(db,root,_BASE,meta)
    except BaseException:
        if new_since:
            try: last=make_snapshot(db,folder,last)
            except Exception as exc: print('Не удалось сохранить последние повторы на Диск:',exc,flush=True)
        raise
    finally:
        if pool:
            for process in list((getattr(pool,'_processes',None) or {}).values()):
                if process.is_alive(): process.terminate()
            pool.shutdown(wait=True,cancel_futures=True)
        db.close()


def pilot(root,local,device):
    lesion,top,base,data,meta,top_env=prepare(root,local,True)
    target=next(x for x in meta['candidates'] if x not in base.RIGHT and x not in base.MN9.values())
    report={'backend':device,'status':'running','protocol':meta,'original_top_environment':top_env,'coordinator_sha256':sha(Path(__file__)),'trials':[],
            'warning':'Пилот не используется в полном CPU-плане; разные backend могут иметь разные случайные последовательности. GPU использует отдельную реализацию в координаторе, а не функцию trial из кода 28. CPU время не включает построение сети, GPU время включает компиляцию.'}
    for name,rid in [('control',''),('lesion',target)]:
        print('Пилот',device,name,flush=True)
        if device=='cpu': l,r,seconds=lesion.trial(base,data,100,0,rid)
        else: l,r,seconds=gpu_trial(base,data,100,0,rid,local/name)
        report['trials'].append({'condition':name,'target':rid,'frequency_hz':100,'seed':0,'left_count':l,'right_count':r,'wall_seconds':seconds})
    report['status']='complete'
    output=root/'04_Отдельные_GPU_пробы';output.mkdir(parents=True,exist_ok=True)
    path=output/(device+'_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')+'_'+uuid.uuid4().hex[:8]+'.json')
    with path.open('x',encoding='utf8') as f: json.dump(report,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    print('Пилот сохранён:',path,flush=True)


def gpu_trial(base,data,frequency,seed,target,build):
    import brian2 as b2
    import brian2cuda  # noqa: F401, registers cuda_standalone
    # Each call compiles separately; pilot only. No promise of matching CPU random streams.
    b2.device.reinit();b2.set_device('cuda_standalone',directory=str(build),build_on_run=True)
    b2.start_scope();b2.defaultclock.dt=0.1*b2.ms
    p={'v_0':-52*b2.mV,'v_rst':-52*b2.mV,'v_th':-45*b2.mV,'t_mbr':20*b2.ms,'tau':5*b2.ms,'t_rfc':2.2*b2.ms}
    eq='dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)\ndg/dt = -g / tau : volt (unless refractory)\nrfc : second'
    n=b2.NeuronGroup(len(data['ids']),eq,method='linear',threshold='v > v_th',reset='v = v_rst; g = 0*mV',refractory='rfc',namespace=p)
    n.v=p['v_0'];n.g=0;n.rfc=p['t_rfc']
    syn=b2.Synapses(n,n,'w : volt',on_pre='g += w',delay=1.8*b2.ms);syn.connect(i=data['pre'],j=data['post'])
    weights=data['weights'].copy()
    if target: weights[data['pre']==data['lookup'][target]]=0
    syn.w=weights*0.275*b2.mV
    pois=[]
    for rid in base.RIGHT:
        idx=data['lookup'][rid];n[idx].rfc=0*b2.ms
        pois.append(b2.PoissonInput(n[idx],'v',N=1,rate=frequency*b2.Hz,weight=0.275*250*b2.mV))
    mon=b2.SpikeMonitor(n,record=False);net=b2.Network(n,syn,mon,*pois);b2.seed(seed)
    start=time.time();net.run(1000*b2.ms,namespace={})
    return int(mon.count[data['lookup'][base.MN9['left']]]),int(mon.count[data['lookup'][base.MN9['right']]]),round(time.time()-start,3)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--mode',choices=['check','cpu','cpu-pilot','gpu-pilot','export'],required=True)
    parser.add_argument('--workers',type=int,choices=[1,2],default=2);parser.add_argument('--checkpoint-every',type=int,default=25);parser.add_argument('--max-trials',type=int,default=0)
    args=parser.parse_args()
    if not 1<=args.checkpoint_every<=100 or args.max_trials<0: raise ValueError('Неверный интервал снимков или предел повторов.')
    if args.mode in ('check','cpu','cpu-pilot','gpu-pilot'):
        import numpy as np
        import brian2 as b2
        expected=('2.10.1','2.2.6') if args.mode=='gpu-pilot' else ('2.9.0','1.26.4')
        if (b2.__version__,np.__version__)!=expected: raise ValueError(f'Неподходящие версии Brian2/NumPy: {b2.__version__}/{np.__version__}; требуются {expected}.')
    root=Path(args.root)
    if not root.is_dir(): raise ValueError('Нет корневой папки на Google Диске: '+str(root))
    with tempfile.TemporaryDirectory(prefix='fly-colab-',dir='/content' if Path('/content').is_dir() else None) as temp:
        local=Path(temp)
        if args.mode=='export': export_latest(root,local)
        elif args.mode=='check':
            lesion,top,base,data,meta,top_env=prepare(root,local,False)
            print(f'Проверка завершена. Топ-200 проверен. План: {TOTAL} повторов. Симуляции не запускались.',flush=True)
        elif args.mode=='cpu': cpu_series(root,local,args.workers,args.checkpoint_every,args.max_trials)
        elif args.mode=='cpu-pilot': pilot(root,local,'cpu')
        else: pilot(root,local,'gpu')

if __name__=='__main__': main()
