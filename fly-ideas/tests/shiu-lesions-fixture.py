"""Синтетическая сеть: авторская лезия, проверки исходного отбора, resume."""
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import numpy as np
import pandas as pd
import brian2 as b2

root=Path(__file__).resolve().parents[1]; tmp=Path(sys.argv[1]); templates=root/'experiments/templates'
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=load('base',templates/'25_shiu_v630_control.py'); top=load('top',templates/'27_shiu_top200_v630.py')
lesion=load('lesion',templates/'28_shiu_lesions_v630.py'); author=load('author',root/'tests/fixtures/shiu-reference/model.py')
ids=sorted(set(base.LEFT+base.RIGHT+list(base.MN9.values())+[str(720575940000000000+i) for i in range(210)]),key=int)
lookup={x:i for i,x in enumerate(ids)};comp=tmp/'comp.csv';conn=tmp/'conn.parquet'
pd.DataFrame({'Completed':[True]*len(ids)},index=[int(x) for x in ids]).to_csv(comp)
# Сеть с влиянием входа на MN9, включая несколько путей.
rows=[(lookup[r],lookup[x],12,1) for r in base.RIGHT for x in ids[:210]]
rows += [(lookup[base.RIGHT[0]],lookup[base.MN9['left']],20,1),(lookup[base.RIGHT[0]],lookup[base.MN9['right']],15,1)]
pd.DataFrame([{'Presynaptic_ID':int(ids[i]),'Postsynaptic_ID':int(ids[j]),'Presynaptic_Index':i,'Postsynaptic_Index':j,'Connectivity':n,'Excitatory':sign,'Excitatory x Connectivity':sign*n} for i,j,n,sign in rows]).to_parquet(conn,index=False)
base.EXPECTED={'connections':base.fingerprint(conn)['git_blob_sha1'],'neurons':base.fingerprint(comp)['git_blob_sha1']}
top.base_module=lambda:base;lesion.load_top=lambda:top
data=base.validate_inputs(conn,comp,True);target=base.RIGHT[0]
for silenced in ['',target]:
    result=lesion.trial(base,data,100,3,silenced)
    b2.start_scope();b2.defaultclock.dt=.1*b2.ms;b2.prefs.codegen.target='numpy'
    params=dict(author.default_params);params['r_poi']=100*b2.Hz
    neu,syn,mon=author.create_model(comp,conn,params)
    pois,neu=author.poi(neu,[lookup[x] for x in base.RIGHT],[],params)
    if silenced: syn=author.silence([lookup[silenced]],syn)
    net=b2.Network(neu,syn,mon,*pois);b2.seed(3);net.run(1000*b2.ms,namespace={})
    assert result[:2]==(int(mon.count[lookup[base.MN9['left']]]),int(mon.count[lookup[base.MN9['right']]]))
    del net,mon,pois,syn,neu

# Сохранённый отбор генерируется тестом без проведения 30 сетевых симуляций.
folder=tmp/'top-run';folder.mkdir(); hashes={'connections':base.fingerprint(conn),'neurons':base.fingerprint(comp)}
protocol={'schema':1,'connection_sha256':hashes['connections']['sha256'],'neuron_sha256':hashes['neurons']['sha256'],
          'script_sha256':lesion.TOP_SHA,'base_sha256':top.BASE_SHA256,'python':sys.version.split()[0],'brian2':b2.__version__,
          'numpy':np.__version__,'side':'right','frequency_hz':200,'duration_ms':1000,'dt_ms':0.1,'seeds':list(range(30))}
checkpoint={'protocol':protocol,'completed':{}};total=np.zeros(len(ids),dtype='int64')
for seed in range(30):
    c=np.arange(len(ids),dtype='int64')+seed+1;total+=c
    f=folder/f'counts_seed_{seed:02d}.npy';np.save(f,c,allow_pickle=False)
    checkpoint['completed'][str(seed)]={'sha256':top.hashfile(f),'wall_seconds':1.0}
top.atomic_json(folder/'checkpoint.json',checkpoint)
order=sorted(range(len(ids)),key=lambda i:(-int(total[i]),int(ids[i])))
with (folder/'top200.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['rank','root_id','mean_rate_hz','total_spikes_30_trials'])
    for rank,i in enumerate(order[:200],1): w.writerow([rank,ids[i],int(total[i])/30,int(total[i])])
top.atomic_json(folder/'summary.json',{'status':'ok','mode':'simulation','protocol':protocol,'result':{'trials':30,'active_neurons':len(ids),'cutoff_rate_hz':int(total[order[199]])/30}})
selected,active=lesion.validate_top(top,base,data,hashes,folder)
assert len(selected)==200 and active==len(ids) and selected[0]==ids[order[0]]
original=(folder/'top200.csv').read_bytes();(folder/'top200.csv').write_bytes(original.replace(ids[order[0]].encode(),b'123456789012345678'))
try: lesion.validate_top(top,base,data,hashes,folder);raise AssertionError('подмена списка принята')
except ValueError as e: assert 'не соответствует' in str(e)
(folder/'top200.csv').write_bytes(original)
original_counts=(folder/'counts_seed_00.npy').read_bytes();(folder/'counts_seed_00.npy').write_bytes(original_counts+b'bad')
try: lesion.validate_top(top,base,data,hashes,folder);raise AssertionError('подмена повтора принята')
except ValueError as e: assert 'сумма' in str(e)
(folder/'counts_seed_00.npy').write_bytes(original_counts)

# Маленький план для проверки транзакций и продолжения, не научный результат.
lesion.FREQS=[50,100];lesion.SEEDS=[0,1]
candidates=[x for x in selected if x not in base.RIGHT and x not in base.MN9.values()][:2]
lesion.validate_top=lambda top,base,data,hashes,folder:(candidates,len(ids))
calls=[]
def fake(base,data,freq,seed,target):
    calls.append((freq,target,seed))
    if freq==50:return (0,5,1.0)
    return (0 if target==candidates[0] else 10,5,1.0)
lesion.trial=fake
def run(*argv):
    out=tmp/f'lesion-{len(list(tmp.glob("lesion-*")))}';out.mkdir()
    os.environ.update(FLY_RUN_DIR=str(out),FLY_SHIU_CONNECTIONS=str(conn),FLY_SHIU_NEURONS=str(comp))
    sys.argv=['lesions','--top-run',str(folder),*argv]
    code=lesion.main();return code,json.loads((out/'summary.json').read_text(encoding='utf8')),out
code,report,pilot=run('--simulate','--pilot')
assert code==0 and report['status']=='pilot_complete' and calls==[(100,'',0),(100,candidates[0],0)]
source_hash=hashlib.sha256((pilot/'lesions.sqlite3').read_bytes()).hexdigest();calls.clear()
code,report,full=run('--simulate','--resume-from',str(pilot))
assert code==0 and report['status']=='ok' and len(calls)==10 and report['result']['completed']==12
assert hashlib.sha256((pilot/'lesions.sqlite3').read_bytes()).hexdigest()==source_hash
assert (100,'',0) not in calls and (100,candidates[0],0) not in calls
with (full/'lesion_classification.csv').open(encoding='utf-8-sig',newline='') as f: result=list(csv.DictReader(f))
assert result[0]['left_mn9_le_80_percent_any_frequency']=='yes'
assert result[1]['left_mn9_le_80_percent_any_frequency']=='undefined'
with (full/'lesion_rates.csv').open(encoding='utf-8-sig',newline='') as f: rates=list(csv.DictReader(f))
assert rates[0]['ratio_left']=='' and rates[1]['ratio_left']=='0.0'
# База другого протокола не может быть незаметно продолжена.
mismatch=tmp/'mismatched';mismatch.mkdir()
with sqlite3.connect(full/'lesions.sqlite3') as src, sqlite3.connect(mismatch/'lesions.sqlite3') as dest: src.backup(dest)
with sqlite3.connect(mismatch/'lesions.sqlite3') as db:
    meta=json.loads(db.execute('SELECT value FROM metadata WHERE key="protocol"').fetchone()[0]);meta['side']='left'
    db.execute('UPDATE metadata SET value=? WHERE key="protocol"',(json.dumps(meta),))
calls.clear();code,report,_=run('--simulate','--resume-from',str(mismatch))
assert code==1 and 'другими данными' in report['error'] and calls==[]
# Правдоподобная подмена значения не проходит проверку суммы строки.
with sqlite3.connect(pilot/'lesions.sqlite3') as db: db.execute('UPDATE trials SET left_count=9 WHERE target=?',(candidates[0],))
calls.clear();code,report,_=run('--simulate','--resume-from',str(pilot))
assert code==1 and 'Контрольная сумма' in report['error'] and calls==[]
with sqlite3.connect(pilot/'lesions.sqlite3') as db: db.execute('UPDATE trials SET left_count=10001 WHERE target=?',(candidates[0],))
calls.clear();code,report,_=run('--simulate','--resume-from',str(pilot))
assert code==1 and 'некорректные повторы' in report['error'] and calls==[]
print('ok')
