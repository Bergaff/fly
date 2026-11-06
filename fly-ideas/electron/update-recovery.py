"""Диагностика и безопасная приостановка ожидающего обновления. Данные не переносит."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import uuid
from datetime import datetime, timezone


def inspect(app):
    app=Path(app).resolve()
    for name in ('START.bat','electron/app-update.py'):
        if not (app/name).is_file(): raise ValueError('Выберите папку Fly Ideas с START.bat и electron/app-update.py.')
    spec=importlib.util.spec_from_file_location('installed_fly_updater',app/'electron/app-update.py')
    u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
    base=app/'workspace'/'.app-updates';pending=base/'pending.json';journal=base/'journal.json'
    for path in (app,app/'workspace',base,pending):
        if u.is_link(path): raise ValueError(f'Ссылка или точка повторной обработки запрещена: {path}')
    if journal.exists() or u.is_link(journal): raise ValueError('Обнаружен journal.json: могло прерваться применение. Ничего не меняйте и сообщите об этом.')
    if not pending.is_file(): raise ValueError('pending.json не найден; приостанавливать нечего.')
    contents=pending.read_bytes();m=json.loads(contents.decode('utf-8-sig'))
    if m.get('version')!=1 or m.get('branch')!='arena/01a0b34a-fly' or Path(m.get('app','')).resolve()!=app:
        raise ValueError('План обновления не относится к выбранной папке или ветке.')
    commit=m.get('commit','');stage=m.get('stage','')
    if not re.fullmatch(r'[0-9a-f]{40}',commit) or not re.fullmatch('stage-'+commit+'-[0-9a-f]{32}',stage):
        raise ValueError('Некорректное имя сохранённого снимка; ничего не меняю.')
    files=m.get('files')
    if not isinstance(files,dict) or not files or len(files)>2000 or '.gitattributes' not in files or any(not isinstance(k,str) or not u.permitted(k) or not isinstance(v,str) or not re.fullmatch(r'[0-9a-f]{64}',v) for k,v in files.items()):
        raise ValueError('Повреждённый или неподходящий список файлов в плане; ничего не меняю.')
    staged=base/stage
    if u.is_link(staged) or not staged.is_dir(): raise ValueError('Сохранённая папка обновления отсутствует или является ссылкой.')
    pid=m.get('owner_pid')
    if u.is_running(pid): raise ValueError('Приложение, подготовившее обновление, ещё работает или состояние процесса неизвестно. Закройте все окна Fly Ideas.')
    config=Path(m.get('config',''))
    if not config.is_absolute() or not config.is_file(): raise ValueError('Файл настроек из плана не найден. Ничего не меняю.')
    cfgbytes=config.read_bytes();cfg=json.loads(cfgbytes.decode('utf-8-sig'))
    entries=[('workspace',app/'workspace')]
    for k,v in (cfg.get('dirs') or {}).items():
        if isinstance(v,str) and v: entries.append(('dirs.'+str(k),Path(v)))
    for project,item in (cfg.get('projectDirs') or {}).items():
        if isinstance(item,dict):
            for k,v in item.items():
                if isinstance(v,str) and v: entries.append(('projectDirs.'+str(project)+'.'+str(k),Path(v)))
    for k,v in (cfg.get('dataFiles') or {}).items():
        if isinstance(v,str) and v: entries.append(('dataFiles.'+str(k),Path(v)))
    if isinstance(cfg.get('syncFolder'),str) and cfg['syncFolder']: entries.append(('syncFolder',Path(cfg['syncFolder'])))
    target=(app/'.gitattributes').resolve();conflicts=[]
    for name,path in entries:
        p=path.resolve()
        if p==target or p in target.parents: conflicts.append((name,str(p)))
    lines=['Диагностика пересечения обновления',f'Время UTC: {datetime.now(timezone.utc).isoformat()}',f'Папка приложения: {app}',f'Проверяемый файл: {target}',f'Коммит снимка: {commit}', '', 'Защищённые пути, пересекающиеся с файлом:']
    if conflicts: lines += [f'{name}: {value}' for name,value in conflicts]
    else: lines.append('Совпадение не найдено. Возможно, изменились настройки или причина отличается; обратитесь за помощью.')
    lines += ['', 'Показаны только совпадающие пути, не весь конфиг и не ключи. Проверьте личные пути перед отправкой.', 'Настройки, пользовательские файлы, снимок и резервные копии не изменяются.']
    return u,app,base,pending,journal,staged,config,hashlib.sha256(contents).hexdigest(),hashlib.sha256(cfgbytes).hexdigest(),'\n'.join(lines)+'\n',bool(conflicts)


def pause_update(info, confirmed):
    u,app,base,pending,journal,staged,config,pending_hash,config_hash,_,conflicts=info
    if not confirmed:return None
    if not conflicts: raise ValueError('Пересечение .gitattributes не найдено; приостановка отменена.')
    if journal.exists() or u.is_link(journal) or not pending.is_file() or u.is_link(pending) or u.is_link(staged):
        raise ValueError('Состояние обновления изменилось; приостановка отменена.')
    data=pending.read_bytes()
    if hashlib.sha256(data).hexdigest()!=pending_hash or hashlib.sha256(config.read_bytes()).hexdigest()!=config_hash:
        raise ValueError('План или настройки изменились после проверки; приостановка отменена.')
    if u.is_running(json.loads(data.decode('utf-8-sig')).get('owner_pid')): raise ValueError('Приложение ещё работает; приостановка отменена.')
    paused=base/('pending-paused-'+datetime.now().strftime('%Y%m%d_%H%M%S')+'-'+uuid.uuid4().hex+'.json')
    if paused.exists(): raise ValueError('Имя архива уже существует; приостановка отменена.')
    os.rename(pending,paused)
    return paused


def main():
    if len(sys.argv)!=2: raise ValueError('Не выбрана папка приложения.')
    info=inspect(sys.argv[1]);report=info[2]/('update-diagnostic-'+uuid.uuid4().hex+'.txt')
    with report.open('x',encoding='utf-8-sig') as f:f.write(info[-2])
    print(info[-2]);print('Отчёт сохранён:',report)
    if os.name=='nt':
        try: os.startfile(str(report))
        except OSError: print('Не удалось открыть отчёт автоматически; путь указан выше.')
    print('\n1: временно приостановить ожидающее обновление и сохранить его снимок.')
    print('Enter: ничего не менять. Перед приостановкой закройте все окна Fly Ideas.')
    answer=input('Ваш выбор: ').strip()
    paused=pause_update(info,answer=='1')
    if paused:
        print('\nОбновление приостановлено. План сохранён:',paused)
        print('Настройки и пользовательские данные не изменены. Теперь откройте START.bat двойным щелчком.')
        print('Пришлите строки о пересечении из открытого отчёта; перед отправкой проверьте личные пути.')
    else: print('План и настройки не изменены. Пришлите строки о пересечении из открытого отчёта.')


if __name__=='__main__':
    try: main()
    except Exception as e:
        print('ОСТАНОВЛЕНО:',str(e),file=sys.stderr);sys.exit(1)
