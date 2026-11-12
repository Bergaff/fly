#!/usr/bin/env python3
"""File-selection wrapper for series 59; never changes saved study scripts.

It checks and displays the chosen baseline folder before asking for new tests.
All actual calculation, locking, checkpoints and pause remain in series 59.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import uuid

HERE=Path(__file__).resolve().parent
STUDY=HERE/'59_long_user_wing_learning.py'
ROOT=Path('workspace/runs/ideas/i-observational/wing-user-long')
BASELINE_ROOT=Path('workspace/runs/ideas/i-observational/wing-studio-user-learning')


def series_module():
    spec=importlib.util.spec_from_file_location('long_wing_selector_series',STUDY)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def check_previous(folder):
    """Read-only diagnosis of the exact chosen path; no files are created."""
    folder=Path(folder).resolve()
    if not folder.is_dir():raise ValueError(f'Выбранная папка не существует или недоступна:\n{folder}')
    problems=[]
    for name in ('metadata.json','model_six_axes.npz','input_manifest.json'):
        if not (folder/name).is_file():problems.append(f'Не найден файл {name}.')
    if not (folder/'input').is_dir():problems.append('Не найдена папка input.')
    if (folder/'INCOMPLETE.txt').exists():problems.append('Есть INCOMPLETE.txt: предыдущий расчёт отмечен незавершённым.')
    for name,limit in (('metadata.json',1024*1024),('model_six_axes.npz',32*1024*1024),('input_manifest.json',1024*1024)):
        p=folder/name
        if p.is_file() and p.stat().st_size>limit:problems.append(f'Файл {name} больше допустимого размера ({limit//1024//1024} МиБ).')
    if problems:
        hint=''
        if folder.name=='input' or folder.name.startswith('test_'):
            hint=f'\nВыбрана вложенная папка. Нужна родительская папка:\n{folder.parent}'
        raise ValueError('Проверенная папка:\n'+str(folder)+'\n\n'+'\n'.join(problems)+hint)
    series=series_module();proto,ev,pre,stim,ck,base,large=series.dependencies()
    try:
        _,model_sha=ev.load_series51_model(folder)
        metadata=json.loads(pre.read_limited(folder/'metadata.json',1024*1024).decode('utf-8-sig'))
        manifest_bytes=pre.read_limited(folder/'input_manifest.json',1024*1024)
        if metadata.get('manifest_sha256')!=pre.digest(manifest_bytes):
            raise ValueError('SHA файла input_manifest.json не совпадает с metadata.json.')
        manifest=json.loads(manifest_bytes.decode('utf-8-sig'))
        entries=manifest.get('inputs')
        if manifest.get('schema')!='wing-user-inputs-v1' or not isinstance(entries,list):raise ValueError('Манифест имеет неверный формат.')
        counts={'train':0,'test':0};seen=set()
        for entry in entries:
            if not isinstance(entry,dict) or entry.get('role') not in counts:raise ValueError('В манифесте указана неверная роль файла.')
            role=entry['role'];counts[role]+=1;number=counts[role];name=f'{role}_{number:03d}.json'
            if entry.get('id')!=number or entry.get('copy')!=f'input/{name}':raise ValueError(f'Неверное имя копии в манифесте: {name}.')
            raw=pre.read_limited(folder/'input'/name,1024*1024)
            _,degrees=stim.sample_trajectory(json.loads(raw.decode('utf-8-sig')))
            motion=stim.motion_hash(degrees)
            if pre.digest(raw)!=entry.get('source_sha256') or motion!=entry.get('sampled_motion_sha256'):
                raise ValueError(f'Копия input/{name} отличается от манифеста.')
            if motion in seen:raise ValueError('В предыдущем наборе повторяются полные движения.')
            seen.add(motion)
        if not 2<=counts['train']<=50 or not 1<=counts['test']<=20:
            raise ValueError('Нужно 2–50 старых обучающих и 1–20 старых проверочных движений.')
    except Exception as exc:
        raise ValueError(f'Проверенная папка:\n{folder}\n\nПроверка не пройдена: {type(exc).__name__}: {exc}') from exc
    return {'folder':str(folder),'train_count':counts['train'],'test_count':counts['test'],'model_sha256':model_sha}


def invoke(*args):
    # Same Python environment and untouched series 59; propagate its exit code.
    return subprocess.call([sys.executable,str(STUDY),*map(str,args)])


def choose():
    import tkinter as tk
    from tkinter import filedialog,messagebox,simpledialog
    root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
    def initial(path):return str(path.resolve()) if path.exists() else str(Path.cwd())
    try:
        action=simpledialog.askinteger('Длительное обучение','Введите номер:\n1: начать новую серию\n2: продолжить серию\n3: запросить паузу',minvalue=1,maxvalue=3,parent=root)
        if action is None:print('Выбор отменён.',flush=True);return 0
        if action in (2,3):
            folder=filedialog.askdirectory(title='Выберите папку серии wing_user_long_...',initialdir=initial(ROOT),parent=root)
            if not folder:print('Выбор отменён.',flush=True);return 0
            return invoke('--resume' if action==2 else '--pause',folder)
        messagebox.showinfo('Предыдущая короткая проба','Выберите целиком папку результата user_wing_learning_..., не папку input или test_001. В ней должны лежать metadata.json и model_six_axes.npz.',parent=root)
        while True:
            previous=filedialog.askdirectory(title='Папка результата user_wing_learning_... (не input и не test_001)',initialdir=initial(BASELINE_ROOT),parent=root)
            if not previous:print('Выбор отменён.',flush=True);return 0
            try: report=check_previous(previous)
            except Exception as exc:
                print('ПРОВЕРКА ПАПКИ:',exc,file=sys.stderr,flush=True)
                if not messagebox.askretrycancel('Папка не подошла',str(exc)+'\n\nВыбрать другую папку?',parent=root):return 1
                continue
            ok=messagebox.askyesno('Папка проверена',f"Выбрана и проверена папка:\n{report['folder']}\n\nОбучающих движений: {report['train_count']}; прежних проверок: {report['test_count']}.\nПродолжить?",parent=root)
            if ok:break
        messagebox.showinfo('Новое движение для проверки','Теперь выберите новый JSON движения для проверки. Несколько файлов можно выбрать с Ctrl. Старая проверка добавится отдельно.',parent=root)
        fresh=list(filedialog.askopenfilenames(title='Новые проверочные траектории JSON',filetypes=[('Траектория JSON','*.json')],parent=root))
        if not fresh:print('Выбор отменён.',flush=True);return 0
        answer=messagebox.askyesnocancel('Время обучения','Запустить на 8 часов?\nДа: 8 часов. Нет: 4 часа. Отмена: не запускать.\nПроверка после обучения займёт дополнительное время.',parent=root)
        if answer is None:print('Выбор отменён.',flush=True);return 0
        hours=8 if answer else 4
        messagebox.showinfo('Перед запуском','Два процесса. Word может замедлиться. При свободной RAM меньше 4 ГиБ или месте на диске меньше 2 ГиБ расчёт остановится с сохранённой партией. Для паузы откройте этот BAT ещё раз и выберите 3.',parent=root)
        folder=ROOT/('wing_user_long_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8])
        return invoke('--new',folder,'--previous',previous,'--fresh',*fresh,'--hours',hours)
    finally:root.destroy()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--choose',action='store_true');group.add_argument('--check-old')
    args=parser.parse_args()
    if args.choose:return choose()
    print(json.dumps(check_previous(args.check_old),ensure_ascii=False,indent=2));return 0


if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print(f'ОШИБКА ВЫБОРА: {type(exc).__name__}: {exc}',file=sys.stderr,flush=True)
        sys.exit(1)
