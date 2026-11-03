import csv
import importlib.util
import os
import tempfile
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('paths', root / 'experiments/templates/39_shiu_rank62_mn9_paths.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    ids = np.array([m.SOURCE, m.TARGETS['left'], m.TARGETS['right'], 11, 12, 13], dtype=np.int64)
    rows = [(0,1,20,1), (0,1,4,1), (0,2,1,1), (0,3,5,1), (3,1,7,-1),
            (3,2,8,-1), (0,4,3,1), (4,1,2,1), (1,1,22,1), (0,0,10,1), (5,1,1,-1)]
    def create(path, rs):
        values = [[int(ids[i]),int(ids[j]),i,j,n,sgn,n*sgn] for i,j,n,sgn in rs]
        table = pa.table({name: pa.array([row[col] for row in values], type=pa.int64()) for col,name in enumerate(m.COLUMNS)})
        pq.write_table(table, path)
    parquet = td / 'a.parquet'; create(parquet, rows)
    source, incoming, count = m.collect(parquet, ids)
    direct, paths = m.path_rows(source, incoming)
    assert count == len(rows)
    assert direct == [['left',str(m.SOURCE),str(m.TARGETS['left']),24,1,2],['right',str(m.SOURCE),str(m.TARGETS['right']),1,1,1]]
    assert [(r[0],r[2],r[4],r[7]) for r in paths] == [('left','11',5,7),('left','12',3,2),('right','11',5,8)]
    assert paths[0][5] == 1 and paths[0][8] == -1
    d = {};m.add_edge(d, 1, 2, 3, 1)
    try: m.add_edge(d, 1, 2, 2, -1)
    except ValueError: pass
    else: raise AssertionError('conflicting signs accepted')
    # Entire-table ID/index check, even on unrelated rows.
    table = pq.read_table(parquet).to_pydict(); table['Presynaptic_ID'][-1] = 999
    pq.write_table(pa.table(table), td / 'bad.parquet')
    try: m.collect(td / 'bad.parquet', ids)
    except ValueError: pass
    else: raise AssertionError('invalid mapping accepted')
    neuronfile = td / 'ids.csv'
    with neuronfile.open('w', encoding='utf8', newline='') as f:
        w = csv.writer(f);w.writerow(['root_id']);w.writerows([[x] for x in ids])
    assert np.array_equal(m.ids_from_csv(neuronfile), ids)
    # Real entry point refuses unverified source, produces no result tables.
    out = td / 'out';os.environ.update(FLY_RUN_DIR=str(out), FLY_SHIU_CONNECTIONS=str(parquet), FLY_SHIU_NEURONS=str(neuronfile))
    try: m.main()
    except ValueError as e: assert 'не совпадают' in str(e)
    else: raise AssertionError('unverified input accepted')
    assert not (out / 'two_step_paths.csv').exists()
print('Rank-62 path fixture passed')
