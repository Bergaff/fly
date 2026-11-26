#!/usr/bin/env python3
"""Series114: deterministic diagnosis of the unresolved Series113A bridge types."""
from __future__ import annotations
import argparse,csv,hashlib,json,os,threading,traceback,uuid
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
INPUT=HERE.parent/'reports'/'fly-mirror-foundation-113abc-user-result.json'
INPUT_SHA='482f6bfcf82c5b354e7b11ed5c6eb3fce1bd9ac4a67c0950d9590df4bdc42666'
ROOT=Path('workspace/runs/ideas/i-observational/bridge-gap-diagnostic-114')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def diagnose(record):
 t=record['flyvis_type'];status=record['status']
 if status=='reviewed_type_without_root_set':
  return 'reviewed_match_missing_roots','root_source_expansion','Find a pinned reviewed source that assigns FlyWire root IDs to this already cross-dataset-reviewed type.'
 if t.startswith('R') and t[1:].isdigit():
  return 'peripheral_photoreceptor_scope_gap','photoreceptor_coverage_audit','Audit whether the official visual-parts table intentionally excludes peripheral photoreceptors; add roots only from a reviewed pinned source.'
 if t.startswith('CT1('):
  return 'split_nomenclature_gap','nomenclature_resolution','Resolve the parenthetical CT1 compartment name against reviewed OL/FlyWire nomenclature before any root assignment.'
 return 'unreviewed_type_gap','reviewed_mapping_expansion','Locate reviewed cross-dataset nomenclature evidence and a pinned root-ID source; lexical similarity alone is forbidden.'
def run(output_root=ROOT):
 if sha(INPUT)!=INPUT_SHA:raise ValueError('Exact genuine Series113 result changed.')
 x=json.loads(INPUT.read_text(encoding='utf8'));a=x['calculation_a'];records=a['records']
 unresolved=[r for r in records if r['status']!='reviewed_type_to_root_set'];rows=[]
 for r in unresolved:
  cause,work,evidence=diagnose(r);rows.append({'flyvis_type':r['flyvis_type'],'series113_status':r['status'],'diagnostic_class':cause,'required_work':work,'required_evidence':evidence,'reviewed_relations':r.get('match_relations',[]),'automatic_completion_allowed':False})
 mapped=a['mapped_type_root_sets'];total=a['flyvis_types'];gate_parts={'minimum_mapped_types':mapped>=47,'minimum_reviewed_types':a['reviewed_type_root_sets']>=45,'disjoint_root_sets':a['root_sets_disjoint']}
 rubric=x['calculation_c']['gates'];true_gates=sum(bool(v) for v in rubric.values())
 report={'schema':'bridge-gap-diagnostic-114-v1','status':'completed','created_utc':datetime.now(timezone.utc).isoformat(),'input_sha256':INPUT_SHA,'answer':{'series113a_passed':bool(a['passed']),'acceptance_gate_completion_percent':100*sum(gate_parts.values())/len(gate_parts),'type_coverage_percent':100*mapped/total,'mapped_types':mapped,'total_types':total,'unresolved_types':len(unresolved),'method_foundation_gates_percent':100.0,'full_biological_rubric_descriptive_percent':100*true_gates/len(rubric),'percent_warning':'Type coverage and gate completion are different denominators. The biological rubric percentage is descriptive only, not probability of success.'},'gate_parts':gate_parts,'gap_class_counts':dict(Counter(r['diagnostic_class'] for r in rows)),'unresolved':rows,'completion_policy':{'can_complete_from_current_exact_sources':False,'reason':'Current exact sources contain no roots for 4 reviewed types and no reviewed match for 12 types. Guessing aliases would violate provenance.','next_executable_stage':'Acquire and preregister additional reviewed type/root sources, then rerun this audit before extending the bridge.'},'scientific_result':False}
 root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('bridge_gap_diagnostic_114_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir()
 save(folder/'summary.json',report)
 with(folder/'unresolved_types.csv').open('w',newline='',encoding='utf8')as f:
  w=csv.writer(f);w.writerow(['flyvis_type','series113_status','diagnostic_class','required_work','automatic_completion_allowed']);
  for r in rows:w.writerow([r['flyvis_type'],r['series113_status'],r['diagnostic_class'],r['required_work'],'false'])
 (folder/'ИТОГ.txt').write_text(f"SERIES114 — ДИАГНОСТИКА 113A\n\n113A gate: PASS (100% критериев gate)\nПокрытие типов: {mapped}/{total} = {100*mapped/total:.1f}%\nНе закрыто: {len(unresolved)} типов\n\nАвтоматическое дополнение запрещено: текущие источники не дают достаточного reviewed evidence.\nСмотрите unresolved_types.csv.\n",encoding='utf-8-sig')
 return folder
def gui():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Series114: диагностика покрытия 113A');root.geometry('760x360+80+50');root.attributes('-topmost',True)
 text=tk.StringVar(value='113A прошёл gate; диагностика разделит gate completion и фактическое покрытие типов.')
 tk.Label(root,text='Series114 — диагностика незакрытых типов',font=('Arial',14,'bold'),pady=18).pack();tk.Label(root,textvariable=text,wraplength=680,justify='center').pack(pady=12);button=tk.Button(root,text='Запустить диагностику',padx=24,pady=10);button.pack(pady=18)
 def begin():
  button.config(state='disabled');text.set('Проверяется exact genuine Series113 result…')
  def work():
   try:
    folder=run()
    def ok():
     text.set('Готово: gate 100%, покрытие49/65 =75,4%, незакрыто16 типов.');
     if os.name=='nt':os.startfile(str(folder.resolve()))
     messagebox.showinfo('Series114',f'Диагностика завершена.\n{folder.resolve()}',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as e:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-114.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(e).__name__+': '+str(e)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');root.after(0,lambda:(messagebox.showerror('Series114',str(e),parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args();print(run(a.output_root)) if not a.gui else gui()
if __name__=='__main__':main()
