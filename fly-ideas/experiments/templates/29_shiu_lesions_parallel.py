"""Возобновление лезий v630 с двумя параллельными процессами.

Запускает неизменённую реализацию 28 и использует её формат базы, поэтому
совместим с проверенными контрольными точками последовательного расчёта.
Каждый процесс хранит отдельную сеть; требуется дополнительная память.
"""
import argparse
import concurrent.futures
import ctypes
import hashlib
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import sqlite3
import sys
import threading
import time

# Ограничиваем фоновые численные пулы; не меняем seed или параметры модели.
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
LESION_SHA='fdedb0ac3c7b81692b44c6b5f07f2e2142e3af1617db179426de3b250b57dd93'
TOTAL=8*201*30
_WORKER_BASE=None
_WORKER_DATA=None
_WORKER_LESION=None
_JOB_HANDLE=None


def windows_worker_job():
    """При аварийном завершении Python Windows закроет связанные процессы."""
    global _JOB_HANDLE
    if sys.platform!='win32': return
    from ctypes import wintypes
    class BasicLimits(ctypes.Structure):
        _fields_=[('per_process_user_time',ctypes.c_longlong),('per_job_user_time',ctypes.c_longlong),('flags',wintypes.DWORD),
                  ('min_working_set',ctypes.c_size_t),('max_working_set',ctypes.c_size_t),('active_limit',wintypes.DWORD),
                  ('affinity',ctypes.c_size_t),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
    class IoCounters(ctypes.Structure):
        _fields_=[(x,ctypes.c_ulonglong) for x in ('read_ops','write_ops','other_ops','read_bytes','write_bytes','other_bytes')]
    class ExtendedLimits(ctypes.Structure):
        _fields_=[('basic',BasicLimits),('io',IoCounters),('process_memory',ctypes.c_size_t),('job_memory',ctypes.c_size_t),
                  ('peak_process_memory',ctypes.c_size_t),('peak_job_memory',ctypes.c_size_t)]
    kernel=ctypes.windll.kernel32
    kernel.CreateJobObjectW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p];kernel.CreateJobObjectW.restype=ctypes.c_void_p
    kernel.SetInformationJobObject.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    job=kernel.CreateJobObjectW(None,None)
    if not job: raise OSError('Не удалось создать защитную группу процессов Windows.')
    limits=ExtendedLimits();limits.basic.flags=0x00002000  # KILL_ON_JOB_CLOSE
    if not kernel.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(job,kernel.GetCurrentProcess()):
        kernel.CloseHandle(job)
        raise OSError('Windows не разрешила безопасно привязать рабочие процессы. Используйте последовательный режим.')
    _JOB_HANDLE=job


def watch_parent(stop_file):
    """После закрытия приложения просим Python закончить текущие повторы."""
    if sys.platform!='win32': return
    kernel=ctypes.windll.kernel32
    kernel.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    parent_pid=int(os.environ.get('FLY_PARENT_PID') or os.getppid())
    handle=kernel.OpenProcess(0x00100000,False,parent_pid)  # SYNCHRONIZE
    if not handle: raise OSError('Не удалось подключить защиту при закрытии приложения.')
    def watch():
        try:
            if kernel.WaitForSingleObject(handle,0xffffffff)!=0:
                os._exit(1)  # не оставляем рабочие процессы без наблюдения
            try: stop_file.write_text('parent exited',encoding='utf-8')
            except OSError: os._exit(1)  # job object завершит дочерние процессы
        finally: kernel.CloseHandle(handle)
    threading.Thread(target=watch,name='parent-watch',daemon=True).start()


def load_lesion():
    path=Path(__file__).parent/'28_shiu_lesions_v630.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=LESION_SHA:
        raise ValueError('Исходный скрипт лезий изменён: совместимость контрольной точки не подтверждена.')
    spec=importlib.util.spec_from_file_location('lesion_reference',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def free_memory_windows():
    if sys.platform!='win32': return None
    from ctypes import wintypes
    class MemoryStatus(ctypes.Structure):
        _fields_=[('dwLength',wintypes.DWORD),('dwMemoryLoad',wintypes.DWORD),('ullTotalPhys',ctypes.c_ulonglong),
                  ('ullAvailPhys',ctypes.c_ulonglong),('ullTotalPageFile',ctypes.c_ulonglong),('ullAvailPageFile',ctypes.c_ulonglong),
                  ('ullTotalVirtual',ctypes.c_ulonglong),('ullAvailVirtual',ctypes.c_ulonglong),('ullAvailExtendedVirtual',ctypes.c_ulonglong)]
    status=MemoryStatus();status.dwLength=ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError('Не удалось проверить свободную оперативную память Windows.')
    return int(status.ullAvailPhys)


def worker_setup(data):
    global _WORKER_BASE,_WORKER_DATA,_WORKER_LESION
    if sys.platform=='win32':
        kernel=ctypes.windll.kernel32
        kernel.GetCurrentProcess.restype=ctypes.c_void_p
        kernel.SetPriorityClass.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
        if not kernel.SetPriorityClass(kernel.GetCurrentProcess(),0x00004000):
            raise OSError('Не удалось установить пониженный приоритет рабочего процесса.')
    elif hasattr(os,'nice'):
        os.nice(10)
    _WORKER_LESION=load_lesion();_WORKER_BASE=_WORKER_LESION.load_top().base_module();_WORKER_DATA=data
    print(f'Рабочий процесс {os.getpid()}: низкий приоритет, готов.',flush=True)


def worker_trial(key):
    freq,target,seed=key
    return _WORKER_LESION.trial(_WORKER_BASE,_WORKER_DATA,freq,seed,target)


class ParallelTrials:
    def __init__(self,out,top_run,workers=2):
        self.out=Path(out);self.top_run=Path(top_run);self.workers=workers
        self.stop_file=self.out/'stop.request';self.pool=None;self.pending=[];self.remaining=iter(())
        self.stopping=False;self.reason='Остановка по запросу пользователя.'

    def check_stop(self):
        if self.stop_file.exists():
            self.stopping=True
        elif self.pool is not None:
            available=free_memory_windows()
            if available is not None and available < 2*1024**3:
                self.reason=f'Свободной RAM осталось {available/1024**3:.1f} ГиБ. Новые повторы остановлены.'
                if not self.stopping: print(self.reason,flush=True)
                self.stopping=True
        return self.stopping

    def prepare(self,data):
        # 28 уже проверил источники и записал подтверждённый протокол в базу.
        with sqlite3.connect(self.out/'lesions.sqlite3') as db:
            meta=json.loads(db.execute('SELECT value FROM metadata WHERE key=?',('protocol',)).fetchone()[0])
            existing=set(db.execute('SELECT frequency,target,seed FROM trials'))
        plan=((f,t,s) for f in meta['frequencies_hz'] for t in ['']+meta['candidates'] for s in meta['seeds'])
        self.remaining=(key for key in plan if key not in existing)
        available=free_memory_windows()
        if available is not None and available < 8*1024**3:
            raise MemoryError(f'Для двух процессов нужно не менее 8 ГиБ свободной RAM перед стартом; сейчас {available/1024**3:.1f} ГиБ. Закройте приложения или продолжите в одном процессе.')
        if available is not None: print(f'Свободная RAM перед стартом: {available/1024**3:.1f} ГиБ. Это не гарантия, что памяти хватит.',flush=True)
        context=multiprocessing.get_context('spawn')
        self.pool=concurrent.futures.ProcessPoolExecutor(max_workers=self.workers,mp_context=context,initializer=worker_setup,initargs=(data,))
        self.fill()

    def fill(self):
        while len(self.pending)<self.workers and not self.stopping:
            try: key=next(self.remaining)
            except StopIteration: break
            self.pending.append((key,self.pool.submit(worker_trial,key)))

    def trial(self,base,data,freq,seed,target):
        if self.check_stop():
            raise KeyboardInterrupt(self.reason)
        if self.pool is None: self.prepare(data)
        if not self.pending or self.pending[0][0]!=(freq,target,seed):
            raise ValueError('Порядок параллельных заданий не совпадает с проверенным планом; расчёт остановлен.')
        key,future=self.pending.pop(0)
        while True:
            try:
                result=future.result(timeout=0.5)
                break
            except concurrent.futures.TimeoutError:
                self.check_stop()
        if not self.check_stop(): self.fill()
        return result

    def close(self):
        if self.pool is not None: self.pool.shutdown(wait=True,cancel_futures=True)


def stopped_summary(out,reason):
    db_path=out/'lesions.sqlite3'; completed=0
    if db_path.is_file():
        with sqlite3.connect(db_path) as db:
            completed=db.execute('SELECT COUNT(*) FROM trials').fetchone()[0]
    files=[x for x in ('lesions.sqlite3','progress.json') if (out/x).is_file()]
    report={'status':'stopped','mode':'simulation','scope':'Лезии v630, параллельное продолжение; не биологическая валидация.',
            'result':{'completed':completed,'total':TOTAL},'reason':reason,'files':files,
            'caveats':['Остановка завершена. Продолжайте из папки этого прогона; исходная папка не изменена.',
                       'Проверка модели на искусственной сети не доказывает полной эквивалентности на v630.']}
    tmp=out/'summary.json.tmp'
    with tmp.open('w',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(tmp,out/'summary.json')


def main():
    p=argparse.ArgumentParser(description=__doc__,add_help=False)
    p.add_argument('--workers',type=int,default=2)
    options,remaining=p.parse_known_args()
    if options.workers!=2: raise ValueError('Этот режим рассчитан только на два процесса.')
    if '--simulate' not in remaining or '--resume-from' not in remaining or '--pilot' in remaining or '--top-run' not in remaining:
        raise ValueError('Параллельный режим предназначен для продолжения сохранённого расчёта.')
    top_run=remaining[remaining.index('--top-run')+1]
    out=Path(os.environ['FLY_RUN_DIR'])
    windows_worker_job()
    watch_parent(out/'stop.request')
    lesion=load_lesion();runner=ParallelTrials(out,top_run,options.workers)
    lesion.trial=runner.trial;sys.argv=['28_shiu_lesions_v630.py',*remaining]
    execution={'mode':'parallel','workers':options.workers,'script_sha256':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
               'worker_priority':'below_normal','thread_limits':{k:os.environ[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')},
               'top_run':top_run,'resume_from':remaining[remaining.index('--resume-from')+1],
               'start_unix':time.time(),'status':'running'}
    def save_execution():
        tmp=out/'parallel_execution.json.tmp'
        with tmp.open('w',encoding='utf-8') as f: json.dump(execution,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(tmp,out/'parallel_execution.json')
    save_execution()
    print('Параллельный режим: два процесса, пониженный приоритет. При остановке дождитесь завершения текущего повтора.',flush=True)
    stopped=False
    try:
        code=lesion.main()
    except KeyboardInterrupt:
        stopped=True;code=0
        print('Остановка. Сохраняем уже завершённые повторы и закрываем процессы...',flush=True)
    finally:
        runner.close()
    if stopped:
        stopped_summary(out,runner.reason)
        print('Расчёт остановлен; базу можно использовать для продолжения.',flush=True)
    execution.update(status='stopped' if stopped else 'ok' if code==0 else 'error',end_unix=time.time())
    save_execution()
    summary=out/'summary.json'
    if summary.is_file():
        report=json.loads(summary.read_text(encoding='utf-8'));report['execution']=execution
        report.setdefault('files',[]).append('parallel_execution.json')
        tmp=out/'summary.json.tmp'
        with tmp.open('w',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(tmp,summary)
    return code


if __name__=='__main__':
    multiprocessing.freeze_support()
    try: sys.exit(main())
    except Exception as exc:
        print(f'Ошибка параллельного запуска: {type(exc).__name__}: {exc}',file=sys.stderr,flush=True)
        sys.exit(1)
