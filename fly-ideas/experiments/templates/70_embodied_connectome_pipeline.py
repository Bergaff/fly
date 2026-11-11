#!/usr/bin/env python3
"""Series 70: audited preflight and data contracts for FlyVis -> Shiu -> FlyGym.

This runner does not call an unavailable biological mapping a result.  It checks the
three isolated runtimes, freezes source files, and builds a bounded contract fixture.
The full scientific run remains blocked until a reviewed FlyVis-cell-type to FlyWire-ID
mapping and an a-priori motor readout are supplied.
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path('workspace/runs/ideas/i-observational/embodied-connectome')
AUTHOR_MODEL=Path(__file__).with_name('26_shiu_author_model.py')
AUTHOR_SHA='fc45837d7122c6ce2a7f3f2f23c515992e4b232aadb919efabb72337fac88e4e'
STAGES=[
 {'id':1,'name':'visible-series69','status':'implemented','input':'series 69 result/holdout_001','output':'Fly Ideas synchronized replay'},
 {'id':2,'name':'flyvis-eye-encoder','status':'environment-gated','input':'two-eye frames','output':'typed FlyVis activity'},
 {'id':3,'name':'shiu-visual-bridge','status':'mapping-gated','input':'reviewed type-to-FlyWire mapping','output':'spikes plus digital lesions'},
 {'id':4,'name':'flygym-body','status':'readout-gated','input':'a-priori motor readout','output':'MuJoCo body trajectory'},
]
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def run_python(exe,code):
 try:
  p=subprocess.run([str(exe),'-c',code],capture_output=True,text=True,timeout=45)
  return {'ok':p.returncode==0,'command':str(exe),'stdout':p.stdout.strip()[-2000:],'stderr':p.stderr.strip()[-2000:]}
 except Exception as e:return {'ok':False,'command':str(exe),'error':f'{type(e).__name__}: {e}'}
def candidate(env,default):return os.environ.get(env,'').strip() or str(default)
def preflight():
 base=Path('workspace')
 flyvis=candidate('FLY_FLYVIS_PYTHON',base/'.venv-flyvis/Scripts/python.exe')
 flygym=candidate('FLY_FLYGYM_PYTHON',base/'.venv-flygym/Scripts/python.exe')
 brain=candidate('FLY_BRAIN_PYTHON',base/'.venv-two-flies/Scripts/python.exe')
 checks={
  'flyvis':run_python(flyvis,"import json,flyvis,torch;print(json.dumps({'flyvis':getattr(flyvis,'__version__','unknown'),'torch':torch.__version__}))"),
  'flygym':run_python(flygym,"import json,flygym,mujoco,numpy;print(json.dumps({'flygym':getattr(flygym,'__version__','unknown'),'mujoco':mujoco.__version__,'numpy':numpy.__version__}))"),
  'brain':run_python(brain,"import json,brian2,numpy,pandas,pyarrow;print(json.dumps({'brian2':brian2.__version__,'numpy':numpy.__version__,'pandas':pandas.__version__}))"),
 }
 files={}
 for key,env in [('connections','FLY_SHIU_CONNECTIONS'),('neurons','FLY_SHIU_NEURONS')]:
  p=Path(os.environ.get(env,'').strip()) if os.environ.get(env,'').strip() else None
  files[key]={'available':bool(p and p.is_file()),'path':str(p) if p else None,'sha256':sha(p) if p and p.is_file() else None}
 files['author_model']={'available':AUTHOR_MODEL.is_file(),'path':str(AUTHOR_MODEL),'sha256':sha(AUTHOR_MODEL) if AUTHOR_MODEL.is_file() else None,'matches_pinned':AUTHOR_MODEL.is_file() and sha(AUTHOR_MODEL)==AUTHOR_SHA}
 gates={
  'stage2_runtime':checks['flyvis']['ok'],
  'stage3_runtime_and_data':checks['brain']['ok'] and files['connections']['available'] and files['neurons']['available'] and files['author_model']['matches_pinned'],
  'stage4_runtime':checks['flygym']['ok'],
  'reviewed_visual_mapping':False,
  'preregistered_motor_readout':False,
 }
 return {'schema':'embodied-connectome-preflight-v1','created_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'stages':STAGES,'checks':checks,'files':files,'gates':gates,'ready_for_full_scientific_run':all(gates.values()),'limitations':['Runtime availability is not biological validation.','No FlyVis type-to-FlyWire ID mapping is guessed.','No descending-neuron-to-wing/body mapping is guessed.','Fixture mode tests contracts only and is not a scientific result.']}
def fixture(out):
 import math
 out.mkdir(parents=True,exist_ok=True)
 frames=51;units=8
 visual=[[math.sin(i/7+j*.3) for j in range(units)] for i in range(frames)]
 mapping={'schema':'flyvis-flywire-mapping-v1','reviewed':False,'entries':[{'flyvis_column':j,'flywire_ids':[10_000+j],'gain_hz':20.0} for j in range(units)]}
 spikes=[[max(0,v)*20 for v in row] for row in visual]
 lesion=[row[:] for row in spikes]
 for row in lesion:row[0]=0
 state=[sum(row[j] for row in spikes)/frames for j in range(units)]
 lesion_state=[sum(row[j] for row in lesion)/frames for j in range(units)]
 body=[max(-45,min(45,(state[i%units]-state[(i+1)%units])*2)) for i in range(6)]
 lesion_body=[max(-45,min(45,(lesion_state[i%units]-lesion_state[(i+1)%units])*2)) for i in range(6)]
 if body==lesion_body:raise AssertionError('Contract lesion had no downstream effect.')
 artifact={'schema':'embodied-connectome-contract-fixture-v1','status':'fixture_completed','scientific_result':False,'frames':frames,'mapping':mapping,'normal_body_command_deg':body,'lesion_body_command_deg':lesion_body,'lesion_changes_output':True,'stages':STAGES}
 (out/'fixture.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 return artifact
def choose_out():
 ROOT.mkdir(parents=True,exist_ok=True);stamp=datetime.now().strftime('%Y%m%d_%H%M%S');p=ROOT/f'embodied_{stamp}';p.mkdir();return p
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');ap.add_argument('--fixture',action='store_true');ap.add_argument('--output',type=Path);a=ap.parse_args()
 if not a.preflight and not a.fixture:a.preflight=True
 out=a.output or choose_out();out.mkdir(parents=True,exist_ok=True)
 report=preflight();
 if a.fixture:report['fixture']=fixture(out)
 (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 lines=['СЕРИЯ 70: FLYVIS → SHIU → FLYGYM, PREFLIGHT','',f"FlyVis runtime: {report['checks']['flyvis']['ok']}",f"Shiu runtime/data: {report['gates']['stage3_runtime_and_data']}",f"FlyGym runtime: {report['checks']['flygym']['ok']}",'','Полный научный запуск намеренно заблокирован без reviewed visual mapping и preregistered motor readout.','Fixture, если запрошена, проверяет только форматы и эффект цифровой лезии.']
 (out/'ОТЧЕТ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
 print('Отчёт:',out.resolve());return 0
if __name__=='__main__':raise SystemExit(main())
