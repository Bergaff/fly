#!/usr/bin/env python3
"""Series 84T: fixed-count console-stall and worker-CPU accounting diagnostic."""
from __future__ import annotations
import argparse,concurrent.futures,csv,ctypes,hashlib,importlib.util,json,multiprocessing,os,platform,sys,time,uuid
from datetime import datetime,timezone
from pathlib import Path
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER=HERE/'84r_eight_hour_distal_robust_grooming.py'
RUNNER_SHA='d60f23d33185fde7c18e56ccf26a510166955ded4c5384ec0578ec67185cfd6d'
ROOT=Path('workspace/runs/ideas/i-observational/console-compute-accounting')
COUNT=128
BASE=None

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def save_json(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='complete.json'}
def load84r(name='console84t_base'):
 if file_sha(RUNNER)!=RUNNER_SHA:raise ValueError('Закреплённый runner84R изменился.')
 s=importlib.util.spec_from_file_location(name,RUNNER);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def disable_quick_edit():
 """Disable Windows QuickEdit for this shared console so a mouse click cannot suspend Python."""
 if os.name!='nt':return {'platform':os.name,'supported':False,'disabled':False,'reason':'not_windows'}
 kernel=ctypes.WinDLL('kernel32',use_last_error=True);kernel.GetStdHandle.argtypes=[ctypes.c_int];kernel.GetStdHandle.restype=ctypes.c_void_p;kernel.GetConsoleMode.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint)];kernel.SetConsoleMode.argtypes=[ctypes.c_void_p,ctypes.c_uint];handle=kernel.GetStdHandle(-10);mode=ctypes.c_uint()
 if not handle or not kernel.GetConsoleMode(handle,ctypes.byref(mode)):
  return {'platform':'nt','supported':False,'disabled':False,'winerror':ctypes.get_last_error()}
 before=int(mode.value);after=(before|0x0080)&~0x0040
 if not kernel.SetConsoleMode(handle,after):return {'platform':'nt','supported':True,'disabled':False,'mode_before':before,'requested_mode':after,'winerror':ctypes.get_last_error()}
 verify=ctypes.c_uint();ok=bool(kernel.GetConsoleMode(handle,ctypes.byref(verify)));actual=int(verify.value) if ok else None
 return {'platform':'nt','supported':True,'disabled':bool(ok and not(actual&0x0040)),'mode_before':before,'mode_after':actual,'quick_edit_before':bool(before&0x0040),'quick_edit_after':bool(actual&0x0040) if actual is not None else None}

def worker_init():
 global BASE
 BASE=load84r('console84t_worker');BASE.worker_init([],{})
def worker(ident):
 cpu0=time.process_time();wall0=time.perf_counter();rec,x,y=BASE.worker_generate(900000+ident);cpu=time.process_time()-cpu0;wall=time.perf_counter()-wall0
 if rec['status']!='accepted' or x.shape!=(49,576) or y.shape!=(49,6):raise ValueError('Неверный diagnostic candidate.')
 return {'index':ident,'sequence_id':rec['id'],'cpu_seconds':cpu,'worker_wall_seconds':wall,'frames':rec['frames'],'motion_sha256':rec['motion_sha256'],'rgb_sha256':rec['rgb_sha256'],'feature_sha256':sha(np.asarray(x,dtype='<f8').tobytes()),'target_sha256':sha(np.asarray(y,dtype='<f8').tobytes()),'feature_max_std':float(np.max(np.std(x,0))),'finite':bool(np.isfinite(x).all() and np.isfinite(y).all())}

def run(output_root=ROOT,count=COUNT):
 if type(count)!=int or not 2<=count<=COUNT or count%2:raise ValueError('Diagnostic count должен быть чётным от2 до128.')
 console=disable_quick_edit();base=load84r();base.dependencies() # verify pinned scientific dependencies before timing
 root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('console_compute_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result.tmp';temp.mkdir()
 protocol={'schema':'console-compute-accounting-v1','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'runner84r_sha256':RUNNER_SHA,'python':platform.python_version(),'candidate_ids':[900000,900000+count-1],'candidate_count':count,'workers':2,'fixed_count_not_time_budget':True,'quick_edit_action':console,'scientific_model_training':False};save_json(folder/'protocol.json',protocol)
 rows=[];batch=[];started=time.perf_counter()
 with concurrent.futures.ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn'),initializer=worker_init) as pool:
  for start in range(0,count,2):
   t=time.perf_counter();pair=list(pool.map(worker,(start,start+1)));batch_wall=time.perf_counter()-t
   for row in pair:row['batch_index']=start//2;row['coordinator_batch_wall_seconds']=batch_wall;rows.append(row)
   batch.append({'batch_index':start//2,'candidate_indices':[start,start+1],'wall_seconds':batch_wall,'worker_cpu_seconds':sum(x['cpu_seconds'] for x in pair),'worker_reported_wall_max':max(x['worker_wall_seconds'] for x in pair)})
   print(f'Серия84T: готово {start+2}/{count}; batch wall {batch_wall:.2f} с.',flush=True)
 total_wall=time.perf_counter()-started;cpu=sum(x['cpu_seconds'] for x in rows);worker_wall=sum(x['worker_wall_seconds'] for x in rows);largest=max(batch,key=lambda x:x['wall_seconds']);ratios=[x['wall_seconds']/max(x['worker_reported_wall_max'],1e-9) for x in batch]
 summary={'schema':'console-compute-accounting-result-v1','status':'fixture_completed' if count<COUNT else 'completed','protocol':protocol,'candidate_count':count,'frames':sum(x['frames'] for x in rows),'coordinator_wall_seconds':total_wall,'worker_cpu_seconds_sum':cpu,'worker_cpu_parallel_equivalent_seconds':cpu/2,'worker_reported_wall_seconds_sum':worker_wall,'throughput_candidates_per_wall_hour':count/total_wall*3600,'largest_batch':largest,'max_coordinator_to_worker_wall_ratio':max(ratios),'suspected_blocked_batches':sum(r>2.0 and batch[i]['wall_seconds']>30 for i,r in enumerate(ratios)),'all_finite':all(x['finite'] for x in rows),'unique_motion_hashes':len({x['motion_sha256'] for x in rows}),'unique_rgb_hashes':len({x['rgb_sha256'] for x in rows}),'interpretation':['Fixed candidate count prevents a console stall from satisfying a time budget.','Worker CPU excludes time while a process is suspended or waiting; coordinator wall includes it.','QuickEdit is disabled for the current Windows console before workers start.','This is infrastructure diagnostics, not model training or scientific evidence.'],'records':rows,'batches':batch};save_json(temp/'summary.json',summary)
 with (temp/'candidate_timing.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 lines=['СЕРИЯ 84T: CONSOLE И COMPUTE ACCOUNTING',f'Кандидаты: {count}/{count}; frames: {summary["frames"]}.',f'Coordinator wall: {total_wall:.3f} с.',f'Worker CPU sum / parallel equivalent: {cpu:.3f}/{cpu/2:.3f} с.',f'Throughput: {summary["throughput_candidates_per_wall_hour"]:.2f} candidates/hour.',f'QuickEdit disabled: {console.get("disabled")}.',f'Suspected blocked batches: {summary["suspected_blocked_batches"]}.',*summary['interpretation']];(temp/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');save_json(temp/'complete.json',{'protocol_sha256':sha(json.dumps(protocol,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),'files':manifest(temp)});temp.rename(folder/'result')
 if os.name=='nt':
  try:os.startfile(str(folder/'result'))
  except OSError:pass
 print('Готово:',folder/'result');return folder

def choose():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
 try:
  if messagebox.askokcancel('Серия 84T','Технический fixed-count расчёт128 candidates. QuickEdit будет отключён, будут отдельно записаны worker CPU и wall time. Научная модель не обучается. Запустить?',parent=root):return run()
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--fixture-count',type=int,help=argparse.SUPPRESS);a=p.parse_args();return choose() if a.choose else run(a.output_root,a.fixture_count or COUNT)
if __name__=='__main__':
 multiprocessing.freeze_support()
 try:main()
 except Exception as exc:print(f'ОШИБКА СЕРИИ84T: {type(exc).__name__}: {exc}',file=sys.stderr,flush=True);sys.exit(1)
