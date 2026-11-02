import ast
import base64
import gzip
import hashlib
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
notebook=json.loads((root/'colab/Shiu_v630_Colab.ipynb').read_text(encoding='utf8'))
assert notebook['nbformat']==4 and notebook['nbformat_minor']==5
cells=notebook['cells'];ids=[c['id'] for c in cells];assert len(ids)==len(set(ids))
programs=[''.join(c['source']) for c in cells if c['cell_type']=='code']
for source in programs: compile(source,'notebook-cell','exec')
source=next(s for s in programs if s.startswith('#@title 3б.'))
tree=ast.parse(source);entry=next(x for x in tree.body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id=='BUNDLE')
bundle=ast.literal_eval(entry.value)
for name,item in bundle.items():
    raw=gzip.decompress(base64.b64decode(item['gzip_base64']))
    assert hashlib.sha256(raw).hexdigest()==item['sha256']
    ref=(root/'colab/fly_colab.py') if name=='fly_colab.py' else (root/'experiments/templates'/name)
    assert raw==ref.read_bytes(),name
for var in ('START_CPU','RUN_GPU_PILOT','EXPORT_CPU'):
    source=next(s for s in programs if var+' = False' in s)
    assert var+' = False' in source
assert len(bundle)==5
print('Notebook JSON, cells, safe defaults and bundled code: ok')
