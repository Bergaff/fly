"""Искусственная сеть только для проверки прямого вызова авторского ядра."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import pandas as pd

root = Path(__file__).resolve().parents[1]
tmp = Path(sys.argv[1])
def load(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

control = load('control', root/'experiments/templates/25_shiu_v630_control.py')
check = load('check', root/'experiments/templates/26_shiu_original_check.py')
assert check.LEFT == control.LEFT and check.MN9 == control.MN9
ids = sorted(set(control.LEFT + control.RIGHT + list(control.MN9.values())), key=int)
lookup = {v: i for i, v in enumerate(ids)}
comp = tmp/'cells.csv'; conn = tmp/'edges.parquet'
pd.DataFrame({'Completed': [True]*len(ids)}, index=[int(x) for x in ids]).to_csv(comp)
rows = [(lookup[x],lookup[control.MN9['left']],30,1) for x in control.LEFT]
rows += [(lookup[x],lookup[control.MN9['right']],25,1) for x in control.LEFT]
rows += [(0,len(ids)-1,2,-1)]
pd.DataFrame([{'Presynaptic_ID':int(ids[i]),'Postsynaptic_ID':int(ids[j]), 'Presynaptic_Index':i, 'Postsynaptic_Index':j,
               'Connectivity':n,'Excitatory':sign,'Excitatory x Connectivity':sign*n} for i,j,n,sign in rows]).to_parquet(conn,index=False)
check.EXPECTED = {'connections':check.fingerprint(conn)['git_blob_sha1'], 'neurons':check.fingerprint(comp)['git_blob_sha1']}
def run(*args):
    out=tmp/f'out-{len(list(tmp.glob("out-*")))}'; out.mkdir()
    os.environ.update(FLY_RUN_DIR=str(out),FLY_SHIU_CONNECTIONS=str(conn),FLY_SHIU_NEURONS=str(comp))
    sys.argv=['check',*args]
    code=check.main(); report=json.loads((out/'summary.json').read_text(encoding='utf8'))
    return code,report,out
code,r,_=run()
assert code==0 and r['status']=='preflight_complete' and r['author_model']['sha256']==check.AUTHOR_MODEL_SHA256
code,r,out=run('--simulate')
assert code==0 and r['status']=='ok' and (out/'report.txt').exists(), r
src=control.validate_inputs(conn,comp,True)
result=control.simulate_one(src, 'left',100.0,0)
for key in ['left_mn9_rate_hz','right_mn9_rate_hz','stimulus_rates_hz']:
    assert r['result'][key] == result[key], (key,r['result'][key],result[key])
check.AUTHOR_MODEL_SHA256 = 'bad'
code,r,out=run('--simulate')
assert code==1 and r['status']=='error' and 'model.py' in r['error']
check.AUTHOR_MODEL_SHA256 = check.fingerprint(root/'experiments/templates/26_shiu_author_model.py')['sha256']
check.EXPECTED['connections']='bad'
code,r,out=run('--simulate')
assert code==1 and r['status']=='error' and 'не совпадают' in r['error']
print('ok')
