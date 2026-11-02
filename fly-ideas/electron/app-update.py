"""Подготовка и применение снимка фиксированной ветки без Git и без изменения workspace."""
import argparse
import hashlib
import gzip
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
import uuid

BRANCH='arena/01a0b34a-fly'
API='https://api.github.com/repos/Bergaff/fly'
ARCHIVE='https://codeload.github.com/Bergaff/fly/tar.gz/'
MAX_DOWNLOAD=25*1024*1024
MAX_TOTAL=80*1024*1024
MAX_FILE=12*1024*1024
ALLOWED_DIRS={'src','electron','experiments','public','colab','mcp','tests'}
ALLOWED_ROOT={'README.md','package.json','package-lock.json','index.html','tsconfig.json','tsconfig.app.json','tsconfig.node.json','vite.config.ts','components.json','environment.yml','SETUP-PYTHON.bat','BUILD-EXE.bat','.gitattributes','.gitignore','.oxlintrc.json'}


def permitted(rel):
    if not isinstance(rel,str) or not rel or '\\' in rel or ':' in rel or '\x00' in rel: return False
    p=PurePosixPath(rel);parts=p.parts
    if p.is_absolute() or not parts or any(x in ('.','..') or not x or x.endswith(('.', ' ')) or re.search(r'[<>"|?*\x00-\x1f]',x) or re.match(r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)',x,re.I) for x in parts): return False
    return (len(parts)==1 and rel in ALLOWED_ROOT) or (len(parts)>1 and parts[0] in ALLOWED_DIRS and not any(x in {'node_modules','workspace','.git','__pycache__'} for x in parts))


def request(url,limit):
    req=urllib.request.Request(url,headers={'User-Agent':'fly-ideas-update','Accept':'application/vnd.github+json'})
    with urllib.request.urlopen(req,timeout=60) as response:
        if not response.geturl().startswith(('https://api.github.com/', 'https://codeload.github.com/')): raise ValueError('Недопустимый адрес загрузки.')
        data=response.read(limit+1)
    if len(data)>limit: raise ValueError('Слишком большой ответ GitHub; обновление остановлено.')
    return data


def blob_hash(data): return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def sha(data): return hashlib.sha256(data).hexdigest()


def is_link(path):
    path=Path(path)
    if path.is_symlink(): return True
    try: return bool(getattr(path.lstat(),'st_file_attributes',0) & 0x400)
    except FileNotFoundError: return False


def safe_dir(path,create=False):
    path=Path(path)
    if create: path.mkdir(parents=True,exist_ok=True)
    if is_link(path) or not path.is_dir(): raise ValueError(f'Нужна обычная папка: {path}')
    return path


def update_root(app):
    workspace=safe_dir(app/'workspace',True)
    return safe_dir(workspace/'.app-updates',True)


def atomic_json(path,value):
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w',encoding='utf8') as f:
        json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)


def prepare(app,config,owner_pid):
    app=Path(app).resolve();base=update_root(app)
    if (base/'pending.json').exists() or (base/'journal.json').exists(): raise ValueError('Уже есть ожидающее или незавершённое обновление. Закройте приложение и запустите START.bat.')
    commit=json.loads(request(API+'/commits/arena%2F01a0b34a-fly',4*1024*1024))['sha']
    if not re.fullmatch('[0-9a-f]{40}',commit): raise ValueError('Некорректный идентификатор коммита.')
    tree=json.loads(request(API+'/git/trees/'+commit+'?recursive=1',10*1024*1024))
    if tree.get('truncated'): raise ValueError('GitHub вернул неполный список файлов.')
    expected={}
    for x in tree['tree']:
        name=x['path']
        if not name.startswith('fly-ideas/'): continue
        rel=name[len('fly-ideas/'):]
        if not permitted(rel): continue
        if x['type']=='tree': continue
        if x['type']!='blob' or x['mode'] not in ('100644','100755') or not re.fullmatch('[0-9a-f]{40}',x['sha']):
            raise ValueError(f'Недопустимый объект в обновлении: {rel}')
        expected[rel]=x['sha']
    if not {'package.json','package-lock.json','electron/main.cjs','src/App.tsx'}<=expected.keys(): raise ValueError('Неполный список файлов приложения.')
    archive=request(ARCHIVE+commit,MAX_DOWNLOAD)
    with gzip.GzipFile(fileobj=io.BytesIO(archive)) as zipped:
        unpacked=zipped.read(MAX_TOTAL+8*1024*1024+1)
    if len(unpacked)>MAX_TOTAL+8*1024*1024: raise ValueError('Распакованный архив слишком велик.')
    staged=Path(tempfile.mkdtemp(prefix='download-',dir=base));total=0;files={}
    try:
        with tarfile.open(fileobj=io.BytesIO(unpacked),mode='r:') as tar:
            for member in tar:
                parts=PurePosixPath(member.name).parts
                if len(parts)<3 or parts[1]!='fly-ideas': continue
                rel='/'.join(parts[2:])
                if not permitted(rel): continue
                if member.isdir(): continue
                if rel not in expected or not member.isfile() or member.size>MAX_FILE or rel in files:
                    raise ValueError(f'Недопустимый файл в архиве: {rel}')
                total+=member.size
                if total>MAX_TOTAL: raise ValueError('Размер файлов обновления слишком велик.')
                f=tar.extractfile(member)
                if f is None: raise ValueError(f'Не удалось прочитать {rel}')
                data=f.read(MAX_FILE+1)
                if len(data)!=member.size: raise ValueError(f'Неполный файл в архиве: {rel}')
                # GitHub archive honours *.bat eol=crlf; Git blob stores LF.
                if rel.lower().endswith('.bat'): data=data.replace(b'\r\n',b'\n')
                if blob_hash(data)!=expected[rel]: raise ValueError(f'Контрольная сумма Git не совпадает: {rel}')
                target=staged.joinpath(*PurePosixPath(rel).parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
                files[rel]=sha(data)
        if set(files)!=set(expected): raise ValueError('Архив не содержит все файлы из дерева коммита.')
        final=base/('stage-'+commit+'-'+uuid.uuid4().hex)
        os.replace(staged,final)
        manifest={'version':1,'branch':BRANCH,'commit':commit,'app':str(app),'config':str(Path(config).resolve()),
                  'stage':final.name,'files':files,'python':sys.executable,'owner_pid':owner_pid}
        atomic_json(base/'pending.json',manifest)
        return {'commit':commit,'files':len(files),'stage':str(final),'skipped_launcher':'START.bat'}
    except Exception:
        shutil.rmtree(staged,ignore_errors=True)
        raise


def is_running(pid):
    if not isinstance(pid,int) or pid<=0: return True
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:
            return ctypes.get_last_error()!=87
        try:
            code=ctypes.c_ulong()
            return not kernel.GetExitCodeProcess(handle,ctypes.byref(code)) or code.value==259
        finally: kernel.CloseHandle(handle)
    try: os.kill(pid,0);return True
    except ProcessLookupError: return False
    except PermissionError: return True


def protected_paths(app,config):
    paths=[app/'workspace']
    if config.exists():
        cfg=json.loads(config.read_text(encoding='utf8'))
        paths += [Path(v) for v in (cfg.get('dirs') or {}).values() if isinstance(v,str) and v]
        for item in (cfg.get('projectDirs') or {}).values():
            if isinstance(item,dict): paths += [Path(v) for v in item.values() if isinstance(v,str) and v]
        for v in (cfg.get('dataFiles') or {}).values():
            if isinstance(v,str) and v: paths.append(Path(v))
        if isinstance(cfg.get('syncFolder'),str) and cfg['syncFolder']: paths.append(Path(cfg['syncFolder']))
    return [x.resolve() for x in paths]


def check_target(app,rel,protected):
    if not permitted(rel): raise ValueError(f'Недопустимый путь: {rel}')
    target=app.joinpath(*PurePosixPath(rel).parts)
    current=app
    for part in PurePosixPath(rel).parts:
        current=current/part
        if is_link(current): raise ValueError(f'Ссылка в пути обновления: {current}')
    full=target.resolve()
    if any(full==p or p in full.parents for p in protected): raise ValueError(f'Путь обновления пересекается с пользовательскими данными: {target}')
    if target.exists() and not target.is_file(): raise ValueError(f'Ожидался файл: {target}')
    return target


def atomic_write(target,data):
    # Never reuse a user-created temporary filename; keep replacements on the same filesystem.
    target.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+target.name+'.fly-update-',dir=target.parent)
    try:
        if target.exists(): os.chmod(name,stat.S_IMODE(target.stat().st_mode))
        else: os.chmod(name,0o644)
        with os.fdopen(fd,'wb') as stream:
            fd=-1;stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(name,target)
    finally:
        if fd!=-1: os.close(fd)
        try: os.unlink(name)
        except FileNotFoundError: pass


def restore(app,base,journal):
    if not re.fullmatch(r'backup-[A-Za-z0-9_-]+',journal.get('backup','')): raise ValueError('Некорректный путь резервной копии.')
    backup=safe_dir(base/journal['backup'])
    for item in journal['files']:
        target=check_target(app,item['rel'],protected_paths(app,Path(journal['config'])))
        if item['existed']:
            data=backup.joinpath(*PurePosixPath(item['rel']).parts).read_bytes()
            if sha(data)!=item['sha256']: raise ValueError('Повреждена резервная копия; автоматическое восстановление остановлено.')
            atomic_write(target,data)
        elif target.exists(): target.unlink()
    (base/'journal.json').unlink()


def apply(app):
    app=Path(app).resolve();base=update_root(app);journal_path=base/'journal.json'
    pending=base/'pending.json'
    if pending.exists() and is_running(json.loads(pending.read_text(encoding='utf8')).get('owner_pid')):
        raise ValueError('Приложение, подготовившее обновление, ещё работает. Закройте все окна Fly Ideas и повторите запуск.')
    if journal_path.exists():
        journal=json.loads(journal_path.read_text(encoding='utf8'))
        if journal.get('app')!=str(app): raise ValueError('Журнал обновления относится к другой папке.')
        restore(app,base,journal)
        print('Прерванное обновление отменено из резервной копии. Повторите запуск START.bat.');return 1
    if not pending.exists(): return 0
    m=json.loads(pending.read_text(encoding='utf8'))
    if m.get('version')!=1 or m.get('app')!=str(app) or m.get('branch')!=BRANCH or not re.fullmatch(r'[0-9a-f]{40}',m.get('commit','')) or not re.fullmatch('stage-'+m['commit']+'-[0-9a-f]{32}',m.get('stage','')):
        raise ValueError('Некорректный план обновления.')
    if is_running(m.get('owner_pid')): raise ValueError('Приложение, подготовившее обновление, ещё работает. Закройте все окна Fly Ideas и повторите запуск.')
    stage=safe_dir(base/m['stage']);protected=protected_paths(app,Path(m['config']))
    files=m.get('files');
    if not isinstance(files,dict) or len(files)>2000 or not files: raise ValueError('Некорректный список файлов.')
    changed=[]
    for rel,expected in sorted(files.items()):
        target=check_target(app,rel,protected)
        source=check_target(stage,rel,[])
        if not source.is_file() or not re.fullmatch(r'[0-9a-f]{64}',expected): raise ValueError('Повреждён план обновления.')
        data=source.read_bytes()
        if len(data)>MAX_FILE or sha(data)!=expected: raise ValueError(f'Повреждён файл обновления: {rel}')
        if rel.lower().endswith('.bat'): data=data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        if target.is_file() and target.stat().st_size>MAX_FILE: raise ValueError(f'Существующий файл слишком велик для обновления: {rel}')
        old=target.read_bytes() if target.is_file() else None
        if old!=data: changed.append((rel,target,data,old))
    if any(rel in ('package.json','package-lock.json') for rel,_,_,_ in changed):
        if is_link(app/'node_modules'): raise ValueError('node_modules является ссылкой; автоматическая установка запрещена.')
        modules=(app/'node_modules').resolve()
        if any(p==modules or modules in p.parents for p in protected):
            raise ValueError('Папка данных или проекта находится в node_modules; автоматическая установка зависимостей запрещена.')
    backup=Path(tempfile.mkdtemp(prefix='backup-'+m['commit'][:12]+'-',dir=base));backup_name=backup.name;entries=[]
    for rel,target,data,old in changed:
        if old is not None:
            dest=backup.joinpath(*PurePosixPath(rel).parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(old)
        entries.append({'rel':rel,'existed':old is not None,'sha256':sha(old) if old is not None else None})
    journal={'app':str(app),'config':m['config'],'backup':backup_name,'files':entries}
    atomic_json(journal_path,journal)
    try:
        for rel,target,data,old in changed:
            target=check_target(app,rel,protected_paths(app,Path(m['config'])))
            atomic_write(target,data)
        if any(rel in ('package.json','package-lock.json') for rel,_,_,_ in changed): (base/'npm-pending').write_text('install',encoding='utf8')
        # If interrupted before this point, the next start restores the backup.
        journal_path.unlink()
    except Exception:
        restore(app,base,journal)
        raise
    # After the journal is removed, repeated application is safe if cleanup is interrupted.
    pending.unlink()
    shutil.rmtree(stage,ignore_errors=True)
    print(f"Обновление {m['commit'][:12]} применено. Изменено файлов: {len(changed)}. Резервные копии: {backup}")
    return 0


def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--apply',action='store_true');p.add_argument('--app',required=True);p.add_argument('--config');p.add_argument('--owner-pid',type=int);args=p.parse_args()
    try:
        if args.prepare:
            if not args.config or not args.owner_pid: raise ValueError('Не указан конфиг или процесс приложения.')
            print(json.dumps(prepare(args.app,args.config,args.owner_pid),ensure_ascii=False));return 0
        if args.apply: return apply(args.app)
        raise ValueError('Не указан режим обновления.')
    except Exception as e:
        print(f'Обновление остановлено: {type(e).__name__}: {e}',file=sys.stderr);return 1

if __name__=='__main__':sys.exit(main())
