#!/usr/bin/env python3
"""Series90: bounded reviewed biological-mapping gate.

This is an evidence audit, not a simulation. It must close rather than invent a
FlyVis-to-FlyWire mapping or a descending/motor readout after seeing outcomes.
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, sys, traceback
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent.parent
REPORTS=PROJECT/'experiments'/'reports'
AUDIT=REPORTS/'series90-reviewed-mapping-source-audit.json'
EXTRACT=REPORTS/'frozen-routing-margin-replication-89e-user-summary-extract.json'
AUDIT_SHA='ceb7ab4af9ae9fc62e70cd735a99add2b6de998b14601926852883c87da84382'
EXTRACT_SHA='fc4d84ff7f7f97bbbe4570a0b5ac727c2a1700a37e773aaae3ca9b8fb9859686'
SOURCE89E_SHA='c2608558f4fcddd570367010b8293ecd04204099fae6b26cf2935b44618869a3'
ROOT=PROJECT/'workspace'/'runs'/'ideas'/'i-observational'/'series90-reviewed-mapping-gate'


def digest(path:Path)->str:
 h=hashlib.sha256()
 with path.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 return h.hexdigest()


def atomic_json(path:Path,value):
 tmp=path.with_suffix(path.suffix+'.tmp')
 with tmp.open('w',encoding='utf8') as f:
  json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(tmp,path)


def authenticate89e():
 if digest(EXTRACT)!=EXTRACT_SHA:raise ValueError('SHA frozen89E extract не совпал.')
 data=json.loads(EXTRACT.read_text(encoding='utf8'))
 if data.get('schema')!='frozen-routing-margin-replication-89e-user-summary-extract-v1':raise ValueError('Неверная schema frozen89E extract.')
 if data.get('source_file_sha256')!=SOURCE89E_SHA:raise ValueError('Source SHA frozen89E не совпал.')
 p=data.get('reported_primary',{})
 checks={
  'reported_passed':p.get('passed') is True,
  'identity_gate':p.get('identity_gate_passed') is True,
  'angle_gate':p.get('angle_gate_passed') is True,
  'contact_gate':p.get('contact_gate_passed') is True,
  'cases':len(data.get('tests',[]))==216,
  'trials':sum(len(x.get('trials',[])) for x in data.get('tests',[]))==648,
 }
 if not all(checks.values()):raise ValueError('Frozen89E prerequisite не воспроизведён.')
 return checks


def evaluate():
 if digest(AUDIT)!=AUDIT_SHA:raise ValueError('SHA source audit не совпал.')
 audit=json.loads(AUDIT.read_text(encoding='utf8'))
 if audit.get('schema')!='series90-reviewed-mapping-source-audit-v1' or audit.get('audit_conclusion')!='mapping_gate_closed':raise ValueError('Source audit schema/decision invalid.')
 repos={x['repository']:x['commit'] for x in audit['sources']}
 expected={'TuragaLab/flyvis':'92b3845cc426dd309a1a0e1b3890156c42e14021','philshiu/Drosophila_brain_model':'91bdd1e7dcf193f3e7ca5a8933497fcef63b7960','NeLy-EPFL/flygym':'3c8ce5e6cc90dd1ef0b63db53c5e8724c6bedb09'}
 if repos!=expected:raise ValueError('Source commit pins changed.')
 local={x['path']:x['sha256'] for x in audit['existing_local_protocols']}
 for rel,want in local.items():
  if digest(PROJECT/rel)!=want:raise ValueError(f'Local protocol pin changed: {rel}')
 prerequisite=authenticate89e()
 gates={
  'functional89e_frozen_go':True,
  'official_flyvis_activity':True,
  'reviewed_flyvis_to_flywire_mapping':False,
  'fixed_activity_to_rate_rule':False,
  'shiu_flywire_simulation_and_lesions':True,
  'preregistered_descending_motor_readout':False,
  'mapping_permutation_and_lesion_controls':True,
  'official_flygym_body_api':True,
  'validated_end_to_end_action_chain':False,
 }
 if list(gates)!=audit['required_gates']:raise ValueError('Required-gate order/content changed.')
 passed=all(gates.values())
 if passed:raise AssertionError('Current frozen audit must not silently open the mapping gate.')
 return {'schema':'series90-reviewed-biological-mapping-gate-result-v1','status':'completed','decision':'mapping_gate_closed','scientific_result':True,'calculation_kind':'bounded evidence audit; no neural/body simulation','workers':'not applicable','audit_snapshot_utc':audit['audited_utc'],'platform':platform.platform(),'pins':{'source_audit_sha256':AUDIT_SHA,'frozen89e_extract_sha256':EXTRACT_SHA,'frozen89e_source_sha256':SOURCE89E_SHA,'repositories':repos,'local_protocols':local},'functional_prerequisite89e':prerequisite,'gates':gates,'required_passed':sum(gates.values()),'required_total':len(gates),'full_chain_run_authorized':False,'closed_reasons':['No externally reviewed FlyVis-type to FlyWire-root-ID mapping for the frozen89E action chain.','No preregistered and independently validated descending/motor readout for foreleg rubbing, head grooming and reach-withdraw.','The pinned official repositories provide the components separately but no reviewed end-to-end mapping/readout for the three frozen89E actions.','Name matching, selected gains or a post-hoc adapter would manufacture rather than test the proposed mechanism.'],'allowed_conclusions':['Series82-89E support a functional synthetic mirror-like surrogate: observation-derived internal state, delayed autonomous action reconstruction, causal digital lesions, actuator control and frozen replication under registered controls.','Series90 does not establish a reviewed biological chain, so no identified neuron in the model may be called a biological mirror neuron.','The current roadmap ends with mapping gate closed. Future biological work requires independent mapping/readout evidence and a new preregistration, not retrospective completion of series90.'],'forbidden_conclusions':['Biological mirror neurons were discovered or proven.','FlyVis, Shiu/FlyWire and FlyGym currently form a validated natural observation-to-action mechanism for these three actions.','Synthetic lesion necessity proves necessity in a living fly.'],'source_audit_conclusion':audit['audit_conclusion'],'source_audit_reason':audit['reason']}


def report_text(r):
 yes=lambda v:'ПРОЙДЕН' if v else 'ЗАКРЫТ'
 lines=['СЕРИЯ 90: REVIEWED BIOLOGICAL MAPPING GATE','',f"РЕШЕНИЕ: {r['decision']}",f"Пройдено обязательных gates: {r['required_passed']}/{r['required_total']}",'','GATES']
 lines += [f"- {k}: {yes(v)}" for k,v in r['gates'].items()]
 lines += ['','ПОЧЕМУ GATE ЗАКРЫТ']+[f'- {x}' for x in r['closed_reasons']]
 lines += ['','РАЗРЕШЁННЫЕ ВЫВОДЫ']+[f'- {x}' for x in r['allowed_conclusions']]
 lines += ['','ЗАПРЕЩЁННЫЕ ВЫВОДЫ']+[f'- {x}' for x in r['forbidden_conclusions']]
 lines += ['','Это заключительная серия текущего roadmap82–90. Закрытый mapping gate является корректным научным итогом, а не технической ошибкой.']
 return '\n'.join(lines)+'\n'


def choose_output():
 ROOT.mkdir(parents=True,exist_ok=True)
 return ROOT/('mapping_gate_'+datetime.now().strftime('%Y%m%d_%H%M%S'))


def open_report(path):
 try:
  if os.name=='nt':os.startfile(path)  # type: ignore[attr-defined]
 except Exception:pass


def gui_confirm():
 try:
  import tkinter as tk
  from tkinter import messagebox
  root=tk.Tk();root.withdraw()
  ok=messagebox.askokcancel('Серия 90','Запустить заключительный bounded-аудит biological mapping gate?\n\nЭто не долгий расчёт, workers не применяются. Никакие mapping или motor gains не будут подбираться.')
  root.destroy();return ok
 except Exception:return True


def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path);ap.add_argument('--choose',action='store_true');a=ap.parse_args()
 if a.choose and not gui_confirm():return 0
 out=a.output or choose_output();out.mkdir(parents=True,exist_ok=True)
 try:
  result=evaluate();code=0
 except Exception as exc:
  result={'schema':'series90-reviewed-biological-mapping-gate-result-v1','status':'error','decision':'not_evaluated','created_utc':datetime.now(timezone.utc).isoformat(),'error':f'{type(exc).__name__}: {exc}','traceback':traceback.format_exc()};code=1
 atomic_json(out/'summary.json',result)
 text=report_text(result) if code==0 else 'СЕРИЯ 90: ОШИБКА АУДИТА\n\n'+result['error']+'\n\n'+result['traceback']
 report=out/'ОТЧЕТ-СЕРИЯ-90.txt';report.write_text(text,encoding='utf-8-sig');open_report(report)
 if a.choose:
  try:
   import tkinter as tk
   from tkinter import messagebox
   root=tk.Tk();root.withdraw();messagebox.showinfo('Серия 90',('Аудит завершён. Mapping gate закрыт корректно.' if code==0 else 'Аудит остановлен ошибкой.')+'\nОткрыт копируемый отчёт.');root.destroy()
  except Exception:pass
 print(json.dumps(result,ensure_ascii=False,indent=2));print('Отчёт:',report.resolve());return code

if __name__=='__main__':raise SystemExit(main())
