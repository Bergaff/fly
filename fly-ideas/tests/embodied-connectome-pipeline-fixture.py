#!/usr/bin/env python3
import json, subprocess, sys, tempfile
from pathlib import Path
root=Path(__file__).parents[1]
script=root/'experiments/templates/70_embodied_connectome_pipeline.py'
with tempfile.TemporaryDirectory() as td:
 out=Path(td)/'result'
 p=subprocess.run([sys.executable,str(script),'--preflight','--fixture','--output',str(out)],cwd=root,text=True,capture_output=True,timeout=60)
 assert p.returncode==0,(p.stdout,p.stderr)
 d=json.loads((out/'summary.json').read_text(encoding='utf8'))
 assert d['schema']=='embodied-connectome-preflight-v1'
 assert d['ready_for_full_scientific_run'] is False
 assert d['gates']['reviewed_visual_mapping'] is False
 assert d['gates']['preregistered_motor_readout'] is False
 f=d['fixture'];assert f['scientific_result'] is False and f['lesion_changes_output'] is True
 assert f['normal_body_command_deg']!=f['lesion_body_command_deg']
 assert (out/'ОТЧЕТ.txt').is_file() and (out/'fixture.json').is_file()
print('embodied connectome pipeline fixture: OK')
