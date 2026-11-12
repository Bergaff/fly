"""Checkpoint survives a simulated locked progress file and resumes unchanged."""
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import json
root=Path(__file__).resolve().parents[1];script=root/'experiments/templates/44_two_flies_large_study.py'
compat=root/'experiments/long-study-compat/sitecustomize.py'
expected='f90e6633c0115b9f3faf21aae3b1ecdfb6dbf29308ac4ad5e4dc588b1ec2e364'
assert hashlib.sha256(script.read_bytes()).hexdigest()==expected
base={**os.environ,'MUJOCO_GL':'disable','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
with tempfile.TemporaryDirectory() as temp:
    parent=Path(temp);study=parent/'large_two_flies_fixture';inject=parent/'inject';inject.mkdir()
    # Reproduce the original bug after the first group's transaction commits.
    (inject/'sitecustomize.py').write_text('''import os\n_original=os.replace\n_count=0\ndef blocked(a,b,*x,**y):\n global _count\n if str(b).endswith("progress.json"):\n  _count+=1\n  if _count>=2:raise PermissionError("simulated WinError 5")\n return _original(a,b,*x,**y)\nos.replace=blocked\n''')
    env={**base,'PYTHONPATH':str(inject)}
    first=subprocess.run([sys.executable,str(script),'--new',str(study),'--test-count','5'],cwd=root,env=env,text=True,capture_output=True,timeout=60)
    assert first.returncode!=0 and 'simulated WinError 5' in first.stderr,first.stdout+first.stderr
    with sqlite3.connect(study/'study.sqlite3') as db:
        groups=db.execute('select count(*) from groups').fetchone()[0]
        before=dict(db.execute('select group_id||condition,sha256 from trials'))
        assert 1<=groups<5 and len(before)==groups*6
    # Installed shim encounters two transient locks on EVERY update, then succeeds.
    (inject/'sitecustomize.py').write_text('''import importlib.util,os\ns=importlib.util.spec_from_file_location("compat_test",%r)\nm=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nm._DELAY_SECONDS=0\nreal=m._original_replace\ncount=0\ndef flaky(a,b,*x,**y):\n global count\n if m._is_progress(a,b):\n  count+=1\n  if count%%3:raise PermissionError("temporary WinError 5")\n return real(a,b,*x,**y)\nm._original_replace=flaky\nos.replace=m._replace_with_retry\n'''%str(compat))
    resumed=subprocess.run([sys.executable,str(script),'--resume',str(study)],cwd=root,env=env,text=True,capture_output=True,timeout=90)
    assert resumed.returncode==0,resumed.stdout+resumed.stderr
    assert json.loads((study/'progress.json').read_text())['state']=='completed'
    with sqlite3.connect(study/'study.sqlite3') as db:
        after=dict(db.execute('select group_id||condition,sha256 from trials'))
        assert db.execute('select count(*) from groups').fetchone()[0]==5
        assert all(after[k]==v for k,v in before.items())
assert hashlib.sha256(script.read_bytes()).hexdigest()==expected
print('Real checkpoint resumed with simulated locked progress file')
