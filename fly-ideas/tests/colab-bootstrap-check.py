import importlib.util
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bootstrap',root/'colab/bootstrap.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)


def archive_at(path,bad_name=None,bad_link=None):
    with tarfile.open(path,'w:gz') as tar:
        def entry(name,data,mode=0o644):
            item=tarfile.TarInfo(name);item.size=len(data);item.mode=mode;tar.addfile(item,io.BytesIO(data))
        entry('python/bin/python3.12',b'#!/bin/sh\necho 3.12.16\n',0o755)
        if bad_name: entry(bad_name,b'escape')
        if bad_link:
            link=tarfile.TarInfo('python/bin/evil');link.type=tarfile.SYMTYPE;link.linkname=bad_link;tar.addfile(link)


with tempfile.TemporaryDirectory() as d:
    root_tmp=Path(d);source=root_tmp/'source.tgz';archive_at(source)
    sha=b.hash_file(source);base=root_tmp/'colab';python=b.ensure_python_312(base,source.as_uri(),sha)
    assert python.is_file() and b.executable_version(python,b.clean_python_env())=='3.12.16'
    assert b.ensure_python_312(base,source.as_uri(),sha)==python
    # Эмулируем venv/pip и убеждаемся, что используется новый Python, не ядро.
    import types
    real_run=b.subprocess.run;commands=[]
    def run_mock(cmd,**kwargs):
        commands.append((cmd,kwargs))
        if cmd[1:3]==['-m','venv']:
            venv=Path(cmd[3]);(venv/'bin').mkdir(parents=True);(venv/'bin/python').symlink_to(python)
            return types.SimpleNamespace(returncode=0)
        if cmd[1:4]==['-m','pip','install']:return types.SimpleNamespace(returncode=0)
        return real_run(cmd,**kwargs)
    b.subprocess.run=run_mock
    try:
        venv=base/'isolated';env=b.clean_python_env();out=b.ensure_venv(python,venv,['numpy==1.26.4'],env)
        assert out==venv/'bin/python' and commands[0][0][:3]==[str(python),'-m','venv']
        assert any(cmd[1:4]==['-m','pip','install'] and kwargs['env']==env for cmd,kwargs in commands)
    finally:b.subprocess.run=real_run
    # Не затирать уже изменённое окружение.
    python.write_bytes(b'other user content')
    try:b.ensure_python_312(base,source.as_uri(),sha);raise AssertionError('изменённый исполняемый файл принят')
    except RuntimeError as e:assert 'изменён' in str(e)
    assert python.read_bytes()==b'other user content'
    other=root_tmp/'bad-checksum'
    try:b.ensure_python_312(other,source.as_uri(),'0'*64);raise AssertionError('повреждённая загрузка принята')
    except ValueError as e:assert 'Контрольная сумма' in str(e)
    assert not (other/('fly-shiu-python-'+b.PYTHON_VERSION)).exists()
    for idx,kwargs in enumerate(({'bad_name':'python/../../escape'},{'bad_link':'../../../escape'})):
        bad=root_tmp/f'bad{idx}.tgz';archive_at(bad,**kwargs);dest=root_tmp/f'extract{idx}';dest.mkdir()
        try:b.safe_extract(bad,dest);raise AssertionError('архив вышел за пределы папки')
        except ValueError:pass
        assert not (root_tmp/'escape').exists()
    env_name='PYTHONPATH';old=os.environ.get(env_name);os.environ[env_name]='/colab/python313'
    try:assert env_name not in b.clean_python_env() and b.clean_python_env()['PYTHONNOUSERSITE']=='1'
    finally:
        if old is None:os.environ.pop(env_name,None)
        else:os.environ[env_name]=old
    # Путь к окружению с другой версией не перезаписывается.
    venv=root_tmp/'bad-venv';(venv/'bin').mkdir(parents=True);exe=venv/'bin/python';exe.write_text('#!/bin/sh\necho 3.13.0\n');exe.chmod(0o755)
    try:b.ensure_venv(python,venv,[],b.clean_python_env());raise AssertionError('другая версия среды принята')
    except RuntimeError as e:assert 'Версия' in str(e)
    assert exe.exists()
# Вывод и heartbeat должны попадать в поток самого блокнота, включая stderr.
import contextlib, subprocess, sys
captured=io.StringIO()
with contextlib.redirect_stdout(captured):
    b.run_with_output([sys.executable,'-c',"import time,sys;print('первая строка',flush=True);time.sleep(.25);print('сообщение ошибки',file=sys.stderr,flush=True)"], b.clean_python_env(), heartbeat=0.05)
text=captured.getvalue()
assert 'первая строка' in text and 'сообщение ошибки' in text and 'процесс ещё работает' in text
captured=io.StringIO()
with contextlib.redirect_stdout(captured):
    try: b.run_with_output([sys.executable,'-c','raise SystemExit(7)'],b.clean_python_env(),heartbeat=.1);raise AssertionError('ошибка скрыта')
    except subprocess.CalledProcessError as e:assert e.returncode==7
print('Bootstrap и потоковый журнал: проверено')
