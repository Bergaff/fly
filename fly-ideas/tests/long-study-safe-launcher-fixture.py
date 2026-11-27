"""Test selective recovery and run the real worker/checkpoint with simulated locks."""
import builtins
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'experiments/templates'))
spec=importlib.util.spec_from_file_location('safe_launcher',root/'experiments/templates/44_two_flies_safe_launcher.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
script=root/'experiments/templates/44_two_flies_large_study.py'
sha='f90e6633c0115b9f3faf21aae3b1ecdfb6dbf29308ac4ad5e4dc588b1ec2e364'
assert hashlib.sha256(script.read_bytes()).hexdigest()==sha

# A lock on either temporary write or replace is contained around the display
# only, throttled, then retried on final status; other errors propagate.
calls=[]
def locked(*args): calls.append(args[1]);raise PermissionError('progress.json.tmp locked')
m._original_status=locked
m.status_with_lock_recovery(None,'running',1,3,0)
m.status_with_lock_recovery(None,'running',2,3,0)
assert calls==['running']
m.status_with_lock_recovery(None,'completed',3,3,0);assert calls==['running','completed']
def restored(*args): calls.append(args[1]);return 'ok'
m._original_status=restored
assert m.status_with_lock_recovery(None,'completed',3,3,0)=='ok' and not m._progress_blocked
def real_error(*args):raise OSError('disk failed')
m._original_status=real_error
try:m.status_with_lock_recovery(None,'completed',3,3,0)
except OSError as e:assert 'disk failed' in str(e)
else:raise AssertionError('unrelated progress error suppressed')

# CSV transient lock succeeds; persistent lock retries interactively without
# losing a partial export, or raises if noninteractive/cancelled.
m._CSV_RETRIES=2;m._CSV_DELAY=0
attempt=[]
def flaky(*args):
    attempt.append(1)
    if len(attempt)<3:raise PermissionError('csv busy')
    return 42
m._original_export=flaky
assert m.export_with_lock_recovery(None,None)==42 and len(attempt)==3
attempt=[]
def locked_csv(*args):attempt.append(1);raise PermissionError('csv busy')
m._original_export=locked_csv
old_stdin=sys.stdin;old_input=builtins.input
class TTY(io.StringIO):
    def isatty(self):return True
try:
    sys.stdin=io.StringIO()
    try:m.export_with_lock_recovery(None,None)
    except PermissionError as e:assert e.__cause__ and len(attempt)==3
    else:raise AssertionError('noninteractive persistent lock hidden')
    attempt.clear();sys.stdin=TTY();builtins.input=lambda prompt:'q'
    try:m.export_with_lock_recovery(None,None)
    except PermissionError as e:assert 'пользователем' in str(e) and len(attempt)==3
    else:raise AssertionError('cancel hidden')
    attempt.clear()
    def later_ok(*args):
        attempt.append(1)
        if len(attempt)<5:raise PermissionError('csv busy')
        return 'done'
    m._original_export=later_ok;builtins.input=lambda prompt:''
    assert m.export_with_lock_recovery(None,None)=='done' and len(attempt)==5
finally:sys.stdin=old_stdin;builtins.input=old_input
def broken_db(*args):raise sqlite3.OperationalError('sqlite failure')
m._original_export=broken_db
try:m.export_with_lock_recovery(None,None)
except sqlite3.OperationalError:pass
else:raise AssertionError('SQLite error suppressed')

with tempfile.TemporaryDirectory() as tmp:
    tmp=Path(tmp);folder=tmp/'large_two_flies_test';inject=tmp/'inject';inject.mkdir()
    # Simulate a permanently locked temporary progress write, not merely replace,
    # and two transient CSV replacement errors inside a real 5-group run.
    (inject/'sitecustomize.py').write_text('''import os\nfrom pathlib import Path\nreal_write=Path.write_text\nreal_replace=os.replace\ncount=0\ndef blocked_write(self,*a,**k):\n if self.name=="progress.json.tmp":raise PermissionError("simulated progress tmp lock")\n return real_write(self,*a,**k)\ndef blocked_replace(a,b,*x,**y):\n global count\n if str(b).endswith("conditions_summary.csv") and count<2:\n  count+=1\n  raise PermissionError("simulated csv lock")\n return real_replace(a,b,*x,**y)\nPath.write_text=blocked_write\nos.replace=blocked_replace\n''')
    env={**os.environ,'PYTHONPATH':str(inject),'FLY_LONG_STUDY_IO_RETRY':'0','MUJOCO_GL':'disable'}
    launcher=root/'experiments/templates/44_two_flies_safe_launcher.py'
    p=subprocess.run([sys.executable,str(launcher),'--new',str(folder),'--test-count','5'],cwd=root,env=env,text=True,capture_output=True,timeout=100)
    assert p.returncode==0,p.stdout+p.stderr
    assert 'simulated progress tmp lock' in p.stderr and 'simulated csv lock' in p.stderr and 'COMPLETED: 5/5' in p.stdout
    assert not (folder/'progress.json').exists() and (folder/'conditions_summary.csv').is_file()
    with sqlite3.connect(folder/'study.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM groups').fetchone()[0]==5
        before=dict(db.execute('SELECT group_id||condition,sha256 FROM trials'));assert len(before)==30
    # Permanent failure at progress replace also leaves the study running.
    (inject/'sitecustomize.py').write_text('''import os\nreal=os.replace\ndef blocked(a,b,*x,**y):\n if str(b).endswith("progress.json"):raise PermissionError("simulated progress replace lock")\n return real(a,b,*x,**y)\nos.replace=blocked\n''')
    second=tmp/'large_two_flies_replace_lock'
    p=subprocess.run([sys.executable,str(launcher),'--new',str(second),'--test-count','1'],cwd=root,env=env,text=True,capture_output=True,timeout=100)
    assert p.returncode==0 and 'COMPLETED: 1/1' in p.stdout and 'simulated progress replace lock' in p.stderr,p.stdout+p.stderr
    with sqlite3.connect(second/'study.sqlite3') as db:assert db.execute('SELECT COUNT(*) FROM groups').fetchone()[0]==1
    # Resume through the new launcher with the same scientific hash and verify
    # all committed payloads survive unchanged and final status is restored.
    env.pop('PYTHONPATH')
    p=subprocess.run([sys.executable,str(launcher),'--resume',str(folder)],cwd=root,env=env,text=True,capture_output=True,timeout=100)
    assert p.returncode==0,p.stdout+p.stderr
    assert json.loads((folder/'progress.json').read_text())['state']=='completed'
    with sqlite3.connect(folder/'study.sqlite3') as db:
        assert dict(db.execute('SELECT group_id||condition,sha256 FROM trials'))==before
assert hashlib.sha256(script.read_bytes()).hexdigest()==sha
print('Safe launcher lock tests passed')
