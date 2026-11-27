"""Exercise transient and persistent Windows-style progress file locks."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('compat',root/'experiments/long-study-compat/sitecustomize.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m._RETRIES=2;m._DELAY_SECONDS=0
with tempfile.TemporaryDirectory() as tmp:
    directory=Path(tmp)/'large_two_flies_demo';directory.mkdir()
    source=directory/'progress.json.tmp';target=directory/'progress.json'
    source.write_text('new');target.write_text('old');calls=[]
    def transient(a,b,*args,**kwargs):
        calls.append(1)
        if len(calls)<3:raise PermissionError('locked')
        return os.replace(a,b,*args,**kwargs)
    m._original_replace=transient;m._replace_with_retry(source,target)
    assert len(calls)==3 and target.read_text()=='new' and not source.exists()
    source.write_text('newer');calls.clear()
    def always_locked(a,b,*args,**kwargs):calls.append((a,b));raise PermissionError('locked')
    m._original_replace=always_locked;warnings=io.StringIO()
    with contextlib.redirect_stderr(warnings):m._replace_with_retry(source,target)
    assert len(calls)==3 and 'отставать' in warnings.getvalue()
    assert target.read_text()=='new' and source.read_text()=='newer'
    # Other files are not retried or hidden, including CSV and database files.
    for a,b in [('trial.csv.tmp','trial.csv'),('study.sqlite3.tmp','study.sqlite3')]:
        calls.clear()
        try:m._replace_with_retry(directory/a,directory/b)
        except PermissionError:pass
        else:raise AssertionError('Unrelated error was hidden')
        assert len(calls)==1
    # No interception outside an actual study directory.
    calls.clear()
    try:m._replace_with_retry(Path(tmp)/'progress.json.tmp',Path(tmp)/'progress.json')
    except PermissionError:pass
    else:raise AssertionError('Unexpected directory intercepted')
    assert len(calls)==1
# The real Python startup hook is scoped to this launcher environment.
import subprocess,sys
env={**os.environ,'PYTHONPATH':str(root/'experiments/long-study-compat'),'FLY_LONG_STUDY_IO_RETRY':'1'}
startup=subprocess.run([sys.executable,'-c',"import os; assert getattr(os.replace, '_fly_progress_retry', False)"],env=env,capture_output=True,text=True)
assert startup.returncode==0,startup.stderr
print('Progress lock compatibility fixture passed')
