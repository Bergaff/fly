"""Контроль топ-200 и возобновления только на искусственных данных."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import pandas as pd
import numpy as np
import brian2 as b2

root=Path(__file__).resolve().parents[1]; tmp=Path(sys.argv[1])
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
base=load('base',root/'experiments/templates/25_shiu_v630_control.py')
top=load('top',root/'experiments/templates/27_shiu_top200_v630.py')
author=load('author',root/'tests/fixtures/shiu-reference/model.py')
ids=sorted(set(base.LEFT+base.RIGHT+list(base.MN9.values())+[str(720575940000000000+i) for i in range(210)]),key=int)
index={v:i for i,v in enumerate(ids)}
comp=tmp/'neurons.csv'; conn=tmp/'edges.parquet'
pd.DataFrame({'Completed':[True]*len(ids)},index=[int(x) for x in ids]).to_csv(comp)
rows=[(index[r],index[x],12,1) for r in base.RIGHT for x in ids[:210]]
rows += [(0,len(ids)-1,2,-1)]
pd.DataFrame([{'Presynaptic_ID':int(ids[i]),'Postsynaptic_ID':int(ids[j]),'Presynaptic_Index':i,'Postsynaptic_Index':j,
               'Connectivity':n,'Excitatory':s,'Excitatory x Connectivity':s*n} for i,j,n,s in rows]).to_parquet(conn,index=False)
base.EXPECTED={'connections':base.fingerprint(conn)['git_blob_sha1'],'neurons':base.fingerprint(comp)['git_blob_sha1']}
top.base_module=lambda:base
# Сравниваем число спайков ВСЕХ нейронов с исходными функциями авторского model.py.
data=base.validate_inputs(conn,comp,True)
counts,_=top.trial_counts(base,data,3)
b2.start_scope(); b2.defaultclock.dt=0.1*b2.ms; b2.prefs.codegen.target='numpy'
params=dict(author.default_params); params['r_poi']=200*b2.Hz
neu,syn,mon=author.create_model(comp,conn,params)
pois,neu=author.poi(neu,[index[r] for r in base.RIGHT],[],params)
net=b2.Network(neu,syn,mon,*pois); b2.seed(3); net.run(1000*b2.ms,namespace={})
assert np.array_equal(counts,np.asarray(mon.count[:],dtype='int64'))
del net,neu,syn,mon,pois

def run(*args):
    out=tmp/f'out-{len(list(tmp.glob("out-*")))}';out.mkdir()
    os.environ.update(FLY_RUN_DIR=str(out),FLY_SHIU_CONNECTIONS=str(conn),FLY_SHIU_NEURONS=str(comp))
    sys.argv=['top',*args]
    status=top.main(); return status,json.loads((out/'summary.json').read_text(encoding='utf8')),out
code,report,out=run()
assert code==0 and report['status']=='preflight_complete' and not (out/'checkpoint.json').exists()
# Пилот даёт ровно один сохраняемый повтор и не выдаёт готовый топ-200.
pilot_calls=[]
def pilot(base,data,seed):
    pilot_calls.append(seed)
    return np.arange(len(ids),dtype=np.int64)+seed+1, 1.0
top.trial_counts=pilot
code,report,pilot_run=run('--simulate','--pilot')
assert code==0 and report['status']=='pilot_complete' and pilot_calls==[0]
assert not (pilot_run/'top200.csv').exists()
assert len(json.loads((pilot_run/'checkpoint.json').read_text(encoding='utf8'))['completed'])==1

# Контролируемые частоты в тесте, чтобы быстро проверить все 30 сохранений.
calls=[]
def fake(base,data,seed):
    calls.append(seed)
    if seed==5: raise RuntimeError('test interruption')
    return np.arange(len(ids),dtype=np.int64)+seed+1, 1.0
top.trial_counts=fake
code,report,partial=run('--simulate')
assert code==1 and report['status']=='error' and calls==list(range(6))
state=json.loads((partial/'checkpoint.json').read_text(encoding='utf8'))
assert len(state['completed'])==5
calls=[]
def resume(base,data,seed):
    calls.append(seed); return np.arange(len(ids),dtype=np.int64)+seed+1,1.0
top.trial_counts=resume
code,report,out=run('--simulate','--resume-from',str(partial))
assert code==0 and report['status']=='ok' and calls==list(range(5,30)), report
assert len(json.loads((out/'checkpoint.json').read_text(encoding='utf8'))['completed'])==30
frame=pd.read_csv(out/'top200.csv',dtype={'root_id':'string'})
assert len(frame)==200 and int(frame.iloc[0].root_id)==int(ids[-1])
assert abs(frame.iloc[0].mean_rate_hz-(len(ids)+14.5)) < 1e-9
calls=[]; code,report,from_pilot=run('--simulate','--resume-from',str(pilot_run))
assert code==0 and calls==list(range(1,30)) and report['status']=='ok'
assert (from_pilot/'top200.csv').read_bytes()==(out/'top200.csv').read_bytes()
# Не продолжать с повреждёнными данными и не менять предыдущий прогон.
file=partial/'counts_seed_00.npy'; original=file.read_bytes(); file.write_bytes(original+b'bad')
calls=[]; code,report,_=run('--simulate','--resume-from',str(partial))
assert code==1 and report['status']=='error' and 'контрольная сумма' in report['error'].lower() and calls==[]
assert file.read_bytes()==original+b'bad'
print('ok')
