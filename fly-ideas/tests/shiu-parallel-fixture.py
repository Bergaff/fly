"""Полный минимальный протокол 28: pilot, последовательное/параллельное resume и остановка.
Данные и отбор синтетические; Windows проверяется отдельно вручную.
"""
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys


def main():
    import numpy as np
    import pandas as pd
    root=Path(__file__).resolve().parents[1];tmp=Path(sys.argv[1]);templates=root/'experiments/templates'
    sys.path.insert(0,str(templates))
    parallel=importlib.import_module('29_shiu_lesions_parallel')
    assert hashlib.sha256((templates/'28_shiu_lesions_v630.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest()==parallel.LESION_SHA
    lesion=parallel.load_lesion();top=lesion.load_top();base=top.base_module()
    original_trial=lesion.trial
    ids=list(dict.fromkeys(base.LEFT+base.RIGHT+list(base.MN9.values())+['720575940000000001']))
    lookup={x:i for i,x in enumerate(ids)};candidate=ids[-1]
    conn=tmp/'conn.parquet';comp=tmp/'neurons.csv'
    pd.DataFrame({'Completed':[True]*len(ids)},index=[int(x) for x in ids]).to_csv(comp)
    edges=[(lookup[base.RIGHT[0]],lookup[base.MN9['left']],20),(lookup[base.RIGHT[0]],lookup[base.MN9['right']],15),
           (lookup[base.RIGHT[0]],lookup[candidate],15),(lookup[candidate],lookup[base.MN9['left']],12)]
    pd.DataFrame([{'Presynaptic_ID':int(ids[i]),'Postsynaptic_ID':int(ids[j]),'Presynaptic_Index':i,'Postsynaptic_Index':j,
                   'Connectivity':n,'Excitatory':1,'Excitatory x Connectivity':n} for i,j,n in edges]).to_parquet(conn,index=False)
    base.EXPECTED={'connections':base.fingerprint(conn)['git_blob_sha1'],'neurons':base.fingerprint(comp)['git_blob_sha1']}
    top.base_module=lambda:base;lesion.load_top=lambda:top
    lesion.validate_top=lambda *_:([candidate],len(ids))
    lesion.FREQS=[100];lesion.SEEDS=[0,1]
    folder=tmp/'top';folder.mkdir();(folder/'checkpoint.json').write_text('test');(folder/'top200.csv').write_text('test')
    os.environ.update(FLY_SHIU_CONNECTIONS=str(conn),FLY_SHIU_NEURONS=str(comp))
    def run(name,source=None,pilot=False,mode='serial',stop=False):
        out=tmp/name;out.mkdir();os.environ['FLY_RUN_DIR']=str(out)
        runner=parallel.ParallelTrials(out,folder)
        calls=[]
        def worker(b,d,f,s,t):
            calls.append((f,t,s))
            result=runner.trial(b,d,f,s,t)
            if stop: (out/'stop.request').write_text('stop')
            return result
        lesion.trial=worker if mode=='parallel' else original_trial
        sys.argv=['lesion','--top-run',str(folder),'--simulate']+(['--pilot'] if pilot else [])+(['--resume-from',str(source)] if source else [])
        interrupted=False
        try: code=lesion.main()
        except KeyboardInterrupt: interrupted=True;code=0
        finally: runner.close()
        return out,code,interrupted,calls
    def rows(out):
        with sqlite3.connect(out/'lesions.sqlite3') as db:
            return db.execute('SELECT frequency,target,seed,left_count,right_count FROM trials ORDER BY frequency,target,seed').fetchall()
    pilot,code,_,_=run('pilot',pilot=True);assert code==0 and len(rows(pilot))==2
    source_hash=hashlib.sha256((pilot/'lesions.sqlite3').read_bytes()).hexdigest()
    serial,code,_,_=run('serial',source=pilot);assert code==0 and len(rows(serial))==4
    fast,code,_,calls=run('parallel',source=pilot,mode='parallel')
    assert code==0 and rows(fast)==rows(serial), (rows(fast),rows(serial))
    assert calls==[(100,'',1),(100,candidate,1)],calls
    assert hashlib.sha256((pilot/'lesions.sqlite3').read_bytes()).hexdigest()==source_hash
    stopped,code,interrupted,calls=run('stopped',source=pilot,mode='parallel',stop=True)
    assert code==0 and interrupted and len(rows(stopped))==3 and len(calls)==2
    stopped_hash=hashlib.sha256((stopped/'lesions.sqlite3').read_bytes()).hexdigest()
    continued,code,_,_=run('continued',source=stopped)
    assert code==0 and rows(continued)==rows(serial)
    assert hashlib.sha256((stopped/'lesions.sqlite3').read_bytes()).hexdigest()==stopped_hash
    # Проверяем именно оболочку 29, её отчёт и совместимость с прежней базой.
    parallel.load_lesion=lambda:lesion
    wrapper=tmp/'wrapper';wrapper.mkdir();os.environ['FLY_RUN_DIR']=str(wrapper)
    sys.argv=['parallel','--simulate','--top-run',str(folder),'--resume-from',str(pilot)]
    assert parallel.main()==0 and rows(wrapper)==rows(serial)
    report=json.loads((wrapper/'summary.json').read_text(encoding='utf-8'))
    execution=json.loads((wrapper/'parallel_execution.json').read_text(encoding='utf-8'))
    assert report['status']=='ok' and execution['workers']==2 and report['execution']==execution
    assert all(x=='1' for x in execution['thread_limits'].values())
    # И остановку через точку входа: данные первого завершённого повтора остаются в копии.
    original_method=parallel.ParallelTrials.trial
    def stop_first(self,*args):
        result=original_method(self,*args);(self.out/'stop.request').write_text('stop');return result
    parallel.ParallelTrials.trial=stop_first
    wrapped_stop=tmp/'wrapped-stop';wrapped_stop.mkdir();os.environ['FLY_RUN_DIR']=str(wrapped_stop)
    sys.argv=['parallel','--simulate','--top-run',str(folder),'--resume-from',str(pilot)]
    assert parallel.main()==0 and len(rows(wrapped_stop))==3
    report=json.loads((wrapped_stop/'summary.json').read_text(encoding='utf-8'))
    assert report['status']=='stopped' and report['result']['completed']==3 and report['execution']['status']=='stopped'
    assert hashlib.sha256((pilot/'lesions.sqlite3').read_bytes()).hexdigest()==source_hash
    parallel.ParallelTrials.trial=original_method
    # Windows-порог RAM можно проверить без выделения большой сети.
    original_memory=parallel.free_memory_windows
    parallel.free_memory_windows=lambda:1024**3
    guarded=parallel.ParallelTrials(pilot,folder)
    try: guarded.prepare(None);raise AssertionError('порог памяти не сработал')
    except MemoryError: pass
    assert guarded.pool is None
    guarded.pool=object();assert guarded.check_stop() and 'RAM' in guarded.reason;guarded.pool=None
    low=tmp/'low-memory';low.mkdir();os.environ['FLY_RUN_DIR']=str(low)
    sys.argv=['parallel','--simulate','--top-run',str(folder),'--resume-from',str(pilot)]
    assert parallel.main()==1
    low_report=json.loads((low/'summary.json').read_text(encoding='utf-8'))
    assert low_report['status']=='error' and 'ГиБ' in low_report['error'] and low_report['execution']['status']=='error'
    assert rows(low)==rows(pilot) and hashlib.sha256((pilot/'lesions.sqlite3').read_bytes()).hexdigest()==source_hash
    parallel.free_memory_windows=original_memory
    # Исключение рабочего процесса не записывает ложный результат в базу.
    broken=tmp/'broken-worker';broken.mkdir()
    with sqlite3.connect(pilot/'lesions.sqlite3') as source,sqlite3.connect(broken/'lesions.sqlite3') as dest: source.backup(dest)
    with sqlite3.connect(broken/'lesions.sqlite3') as db:
        meta=json.loads(db.execute('SELECT value FROM metadata').fetchone()[0]);meta['candidates']=['missing']
        db.execute('UPDATE metadata SET value=?',(json.dumps(meta),));db.execute('DELETE FROM trials WHERE target<>? ',('',))
        db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(100,'',1,1,1,1.0,lesion.row_hash(100,'',1,1,1,1.0)))
    before=rows(broken);data=base.validate_inputs(conn,comp,True)
    failed=parallel.ParallelTrials(broken,folder)
    try: failed.trial(base,data,100,0,'missing');raise AssertionError('ошибка процесса не передана')
    except KeyError: pass
    finally: failed.close()
    assert rows(broken)==before
    # Запрос до начала работы не создаёт процессов и не изменяет базу.
    blocked=tmp/'blocked';blocked.mkdir();(blocked/'stop.request').write_text('stop')
    runner=parallel.ParallelTrials(blocked,folder)
    try: runner.trial(base,None,100,0,'');raise AssertionError('остановка проигнорирована')
    except KeyboardInterrupt: pass
    finally: runner.close()
    assert runner.pool is None
    print('parallel resume, exact spike counts, interruption and source preservation: ok')

if __name__=='__main__': main()
