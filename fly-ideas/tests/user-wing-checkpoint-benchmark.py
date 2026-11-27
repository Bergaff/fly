"""Manual synthetic SQLite benchmark; results do not model real training or Windows."""
import importlib.util
import sqlite3
import tempfile
import time
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('checkpoint',root/'experiments/templates/54_user_wing_checkpoint.py');cp=importlib.util.module_from_spec(spec);spec.loader.exec_module(cp)
with tempfile.TemporaryDirectory() as td:
    path=Path(td)/'benchmark.sqlite3';source={'example.json':b'example'}
    proto={'source_sha256':{k:cp.sha(v) for k,v in source.items()},'mode':'development benchmark, not scientific output'}
    cp.create(path,proto,source)
    def measure(label):
        times=[]
        for _ in range(3):
            start=time.perf_counter();state=cp.open_verified(path,proto);times.append(time.perf_counter()-start)
        stats=state['stats'];stats['n']+=48
        rec={'id':state['next_id'],'status':'accepted','frames':48,'spec':{'r':'example'},'motion_sha256':'1'*64,'rgb_sha256':'2'*64}
        start=time.perf_counter();cp.commit_batch(path,proto,state['next_id'],[rec],stats,state['elapsed']+1);elapsed=time.perf_counter()-start
        print(label,'database_MiB',round(path.stat().st_size/1024**2,2),'verify_s',[round(v,3) for v in times],'commit_s',round(elapsed,3),flush=True)
    measure('empty')
    with sqlite3.connect(path) as db:
        # Fabricated records and dense stats only test I/O overhead and do not represent any training run.
        row='{"source_train_id":1,"scale":['+','.join(['1.01234567']*6)+'],"offset_deg":['+','.join(['0.12345678']*6)+'],"time_factor":1.011,"distance":4.01,"side_offset":0.1,"meta":"'+'x'*150+'"}'
        db.executemany("INSERT INTO candidates VALUES (?,'accepted',48,?,?,?)",((i,row,'1'*64,'2'*64) for i in range(1,100001)))
        rng=np.random.default_rng(42);x=rng.random((96,576));y=rng.random((96,6));stats=cp.empty_stats()
        stats.update(sx=x.sum(0),sx2=(x*x).sum(0),sy=y.sum(0),sxy=x.T@y,sxx=x.T@x,n=100001*48)
        blob=cp.pack_stats(stats);print('dense_stats_MiB',round(len(blob)/1024**2,2));db.execute('UPDATE state SET next_id=?,elapsed=?,stats=?,stats_sha256=? WHERE id=1',(100001,1,blob,cp.sha(blob)))
    measure('100k')
