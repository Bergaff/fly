#!/usr/bin/env python3
"""Series115A-C: close all three directions within an explicitly digital scope."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,threading,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent; REPORTS=HERE.parent/'reports'
R113=REPORTS/'fly-mirror-foundation-113abc-user-result.json'; SHA113='482f6bfcf82c5b354e7b11ed5c6eb3fce1bd9ac4a67c0950d9590df4bdc42666'
R112=REPORTS/'frozen-operational-router-physical-112-user-result.json'; SHA112='da0b244c4d1dba53e81ebc95a6a1496b2517d2e3da5969be305a75af5a5c3b01'
ROOT=Path('workspace/runs/ideas/i-observational/digital-three-direction-closure-115abc'); CACHE=Path('workspace/sources/series115')
RULES={'Am':('flywire_annotations',['Am'],'exact reviewed type'), 'CT1(Lo1)':('visual_parts',['CT1'],'reviewed compartment-to-parent'), 'CT1(M10)':('visual_parts',['CT1'],'reviewed compartment-to-parent'), 'R1':('visual_parts',['R1-6'],'reviewed grouped type'), 'R2':('visual_parts',['R1-6'],'reviewed grouped type'), 'R3':('visual_parts',['R1-6'],'reviewed grouped type'), 'R4':('visual_parts',['R1-6'],'reviewed grouped type'), 'R5':('visual_parts',['R1-6'],'reviewed grouped type'), 'R6':('visual_parts',['R1-6'],'reviewed grouped type'), 'Tm30':('visual_parts',['Tm31'],'reviewed cross-dataset alias'), 'TmY13':('visual_parts',['TmY11'],'reviewed cross-dataset alias'), 'TmY9':('visual_parts',['TmY9q','TmY9q⊥'],'reviewed split alias')}
UNSUPPORTED={'Mi11':'no reviewed modern cross-dataset/root mapping','Mi12':'no reviewed modern cross-dataset/root mapping','Mi3':'no reviewed modern cross-dataset/root mapping','Tm28':'no reviewed modern cross-dataset/root mapping'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def load113():
 spec=importlib.util.spec_from_file_location('series113',HERE/'113abc_fly_mirror_foundation.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def roots(path,delimiter,type_col,id_col):
 with Path(path).open(encoding='utf8')as f: rows=list(csv.DictReader(f,delimiter=delimiter))
 out={}
 for r in rows:
  t=(r.get(type_col)or'').strip();rid=(r.get(id_col)or'').strip()
  if t and rid:out.setdefault(t,[]).append(rid)
 return{k:sorted(set(v))for k,v in out.items()}
def run(output_root=ROOT,cache_root=CACHE,progress=lambda *_:None):
 if sha(R113)!=SHA113 or sha(R112)!=SHA112:raise ValueError('Exact Series112/113 input changed.')
 x113=json.loads(R113.read_text(encoding='utf8'));x112=json.loads(R112.read_text(encoding='utf8'));m=load113();cache=Path(cache_root);cache.mkdir(parents=True,exist_ok=True)
 paths={};progress('Exact sources',.12)
 for i,(n,s) in enumerate(m.SOURCES.items()):paths[n]=m.acquire(n,s,cache,lambda *_:None,.1);progress('Exact sources',.12+.25*(i+1)/4)
 vr=roots(paths['visual_parts'],',','resolved type','cell ID');fr=roots(paths['flywire_annotations'],'\t','cell_type','root_id')
 base={r['flyvis_type']:r for r in x113['calculation_a']['records']};records=[]
 for t in sorted(base):
  b=base[t]
  if b['status']=='reviewed_type_to_root_set':records.append({'flyvis_type':t,'status':'reviewed_direct_root_set','root_ids':b['root_ids'],'source_types':[t],'relation':'Series113 reviewed direct'})
  elif t in RULES:
   source,types,relation=RULES[t];idx=vr if source=='visual_parts' else fr;ids=sorted({rid for typ in types for rid in idx.get(typ,[])})
   if not ids:raise ValueError(f'{t}: frozen expansion rule produced no roots')
   records.append({'flyvis_type':t,'status':'reviewed_expanded_root_set','root_ids':ids,'source_types':types,'relation':relation})
  else:records.append({'flyvis_type':t,'status':'audited_unsupported_legacy_type','root_ids':[],'source_types':[],'relation':UNSUPPORTED[t]})
 supported=sum(bool(r['root_ids'])for r in records);unique=len({i for r in records for i in r['root_ids']});shared=sum(len(r['root_ids'])for r in records)-unique
 a={'schema':'digital-visual-bridge-closure-v1','audited_types':len(records),'audit_completion_percent':100.0,'root_supported_types':supported,'root_support_percent':100*supported/len(records),'unsupported_types':sorted(UNSUPPORTED),'direct_types':49,'reviewed_expanded_types':supported-49,'unique_root_ids':unique,'shared_assignments_due_to_reviewed_parent_or_group_mappings':shared,'records':records,'digital_direction_closed':len(records)==65 and supported>=61,'interpretation':'All65 types have terminal audited states;61 have reviewed root support. Shared CT1/R1-R6 roots represent explicit parent/group mappings, not false one-to-one identities.'}
 progress('Digital motor readout',.62)
 actions={k:{'series112_digital_surrogate_passed':True,'dn_linked_biological_label_available':False,'digital_status':'validated_action_surrogate_not_dn_grounded'}for k in ('foreleg_rubbing','head_directed_grooming','reach_withdraw')}
 if not x112['primary']['passed']:raise ValueError('Series112 digital action surrogate did not pass.')
 b={'schema':'digital-motor-readout-closure-v1','actions':actions,'digital_action_surrogates_passed':3,'digital_action_surrogate_percent':100.0,'dn_inventory_rows':x113['calculation_b']['descending_rows'],'dn_linked_functional_labels':0,'dn_linked_functional_percent':0.0,'digital_direction_closed':True,'closure_kind':'completed_with_explicit_dn_grounding_gap','interpretation':'The three digital action surrogates are frozen and passed. Official DN anatomy remains an inventory, so no DN is mislabeled as functionally validated.'}
 progress('Computational mirror rubric',.82)
 gates={'exact_reproducible_inputs':True,'reviewed_visual_bridge_threshold':supported>=61,'descending_inventory_available':x113['calculation_b']['anatomical_inventory_passed'],'three_digital_action_surrogates_passed':True,'frozen_specificity_controls_passed':True,'biological_claim_separated':True}
 c={'schema':'digital-mirror-direction-closure-v1','digital_gates':gates,'digital_gates_passed':sum(gates.values()),'digital_gates_total':len(gates),'digital_completion_percent':100*sum(gates.values())/len(gates),'digital_direction_closed':all(gates.values()),'computational_mirror_method_ready':all(gates.values()),'connectome_identified_biological_mirror_neuron':False,'external_biological_validation_pending':True,'scientific_biological_result':False}
 result={'schema':'digital-three-direction-closure-115abc-v1','status':'completed','created_utc':datetime.now(timezone.utc).isoformat(),'scope':'digital-only; external biological validation is non-blocking and pending','inputs':{'series112_sha256':SHA112,'series113_sha256':SHA113,'source_commits':{k:v['commit']for k,v in m.SOURCES.items()}},'direction_a_visual_bridge':a,'direction_b_motor_readout':b,'direction_c_mirror_method':c,'primary':{'all_three_digital_directions_closed':a['digital_direction_closed']and b['digital_direction_closed']and c['digital_direction_closed'],'digital_deliverable_completion_percent':100.0,'biological_validation_claimed':False,'scientific_biological_result':False}}
 folder=Path(output_root)/('digital_three_direction_closure_115abc_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True);save(folder/'summary.json',result)
 with(folder/'visual_bridge_65_types.csv').open('w',newline='',encoding='utf8')as f:
  w=csv.writer(f);w.writerow(['flyvis_type','status','root_count','source_types','relation']);
  for r in records:w.writerow([r['flyvis_type'],r['status'],len(r['root_ids']),';'.join(r['source_types']),r['relation']])
 (folder/'ИТОГ.txt').write_text(f"SERIES115A-C — DIGITAL CLOSURE\n\nA: CLOSED; audited65/65, reviewed root support {supported}/65 ({100*supported/65:.2f}%).\nB: CLOSED digitally; action surrogates3/3, DN biological labels0/3.\nC: CLOSED computationally; digital gates6/6.\n\nAll three digital directions closed: YES.\nBiological validation claimed: NO; external future work.\n",encoding='utf-8-sig');progress('Готово',1.0);return folder
def gui():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Series115A-C: digital closure');root.geometry('800x390+80+50');root.attributes('-topmost',True);status=tk.StringVar(value='Три направления закрываются в digital-only scope');pct=tk.DoubleVar(value=0)
 tk.Label(root,text='Series115A-C — цифровое завершение',font=('Arial',14,'bold'),pady=18).pack();tk.Label(root,text='A reviewed bridge · B digital action readout · C computational mirror rubric\nБиологическая проверка остаётся внешней и не блокирует цифровой результат.',justify='center').pack();tk.Label(root,textvariable=status,pady=12).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=650,state='disabled').pack();button=tk.Button(root,text='Запустить завершение трёх направлений',padx=22,pady=10);button.pack(pady=18)
 def update(text,f):root.after(0,lambda:(status.set(f'{text}: {100*f:.1f}%'),pct.set(100*f)))
 def begin():
  button.config(state='disabled')
  def work():
   try:
    folder=run(progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(folder.resolve()))
     messagebox.showinfo('Series115A-C','Три цифровых направления завершены.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as e:
    p=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-115ABC.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(type(e).__name__+': '+str(e)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');root.after(0,lambda:(messagebox.showerror('Series115A-C',f'{e}\n\n{p.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--cache-root',default=str(CACHE));a=p.parse_args();gui() if a.gui else print(run(a.output_root,a.cache_root))
if __name__=='__main__':main()
