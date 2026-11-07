"""Маленькие искусственные таблицы только для автоматической проверки сравнения."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import pandas as pd

root = Path(__file__).resolve().parents[1]
script = root / 'experiments/templates/24_compare_shiu_connectivity.py'
tmp = Path(sys.argv[1])
ids = [720575940000000001 + i for i in range(5)]
comp = tmp / 'author cells.csv'; edges = tmp / 'author edges.parquet'; p = tmp / 'princeton.csv'; nt = tmp / 'nt.csv'
pd.DataFrame({'Completed': [True]*len(ids)}, index=ids).to_csv(comp)
author_rows = [(0,1,3,1),(1,0,5,-1),(2,0,7,1),(3,2,1,-1)]
def write_author(rows):
    pd.DataFrame([{'Presynaptic_ID': ids[i], 'Postsynaptic_ID': ids[j], 'Presynaptic_Index': i, 'Postsynaptic_Index': j,
                   'Connectivity': n, 'Excitatory': sign, 'Excitatory x Connectivity': sign*n} for i,j,n,sign in rows]).to_parquet(edges, index=False)
write_author(author_rows)
pd.DataFrame([(ids[0],ids[1],1,'A'),(ids[0],ids[1],4,'B'),(ids[1],ids[0],5,'A'),
              (ids[2],ids[0],7,'A'), (ids[3],ids[4],2,'A'), (ids[4],ids[2],2,'A')], columns=['pre_root_id','post_root_id','syn_count','neuropil']).to_csv(p,index=False)
pd.DataFrame([(ids[0],'ach'), (ids[1],'ach'), (ids[2],'da'), (ids[3],'gaba'), (ids[4],'ach')], columns=['root_id','nt_type']).to_csv(nt,index=False)
before = {f: hashlib.sha256(f.read_bytes()).hexdigest() for f in [comp, edges, p, nt]}

def run(env_add=None):
    out = tmp / ('out-' + str(len(list(tmp.glob('out-*'))))); out.mkdir()
    env = dict(os.environ, FLY_RUN_DIR=str(out), FLY_CONNECTOME=str(p), FLY_SHIU_CONNECTIONS=str(edges), FLY_SHIU_NEURONS=str(comp), FLY_NEUROTRANSMITTERS=str(nt))
    env.update(env_add or {})
    r = subprocess.run([sys.executable, str(script)], env=env, capture_output=True, text=True, timeout=90)
    return r, json.loads((out/'summary.json').read_text(encoding='utf8')), out
r, report, out = run()
assert r.returncode == 0 and report['status'] == 'ok', (r.stdout,r.stderr,report)
m = report['metrics']
assert m['same_ids_in_both'] == 5 and m['author_pairs'] == 4 and m['princeton_pairs'] == 5, m
assert m['common_pairs'] == 3 and m['author_only_pairs'] == 1 and m['princeton_only_pairs'] == 2, m
assert abs(m['jaccard_pairs'] - 1/2) < 1e-9
assert m['author_synapses_on_common_pairs'] == 15 and m['princeton_synapses_on_common_pairs'] == 17
assert m['equal_weight_common_pairs'] == 2 and abs(m['mean_absolute_weight_difference'] - 2/3) < 1e-9
assert report['sign_comparison']['same_sign'] == 1 and report['sign_comparison']['different_sign'] == 1 and report['sign_comparison']['unavailable_or_excluded'] == 1
assert not any(report['author_git_blob_matches_reference'].values())
assert all((out / name).is_file() for name in ['report.txt','comparison.csv','pairs.png','weights.png'])
assert not list(out.glob('.compare_tmp-*'))
assert all(hashlib.sha256(f.read_bytes()).hexdigest() == digest for f,digest in before.items())
r, report, out = run({'FLY_NEUROTRANSMITTERS': ''})
assert r.returncode == 0 and report['sign_comparison']['status'] == 'not_selected'
# Индексы из связей обязаны соответствовать списку, а не только совпадающим ID.
df = pd.read_parquet(edges); df.loc[0, 'Presynaptic_Index'] = 2; df.to_parquet(edges,index=False)
r, report, out = run()
assert r.returncode == 1 and report['status'] == 'error' and 'не соответствует' in report['error']
assert not list(out.glob('.compare_tmp-*'))
write_author(author_rows)
# Отсутствующая таблица и неправильный CSV не заменяются искусственными данными.
r, report, _ = run({'FLY_SHIU_CONNECTIONS': ''})
assert r.returncode == 1 and report['status'] == 'error' and 'FLY_SHIU_CONNECTIONS' in report['error']
p.write_text('pre_root_id,post_root_id,syn_count\n1,2,0\n', encoding='utf8')
r, report, _ = run()
assert r.returncode == 1 and report['status'] == 'error'
print('ok')
