#!/usr/bin/env python3
"""Series113A-C: reviewed visual bridge, motor-readout readiness, fly-first mirror rubric."""
from __future__ import annotations
import argparse,csv,hashlib,json,os,subprocess,threading,time,traceback,uuid
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
RESULT112=HERE.parent/'reports'/'frozen-operational-router-physical-112-user-result.json';RESULT112_SHA='da0b244c4d1dba53e81ebc95a6a1496b2517d2e3da5969be305a75af5a5c3b01'
ROOT=Path('workspace/runs/ideas/i-observational/fly-mirror-foundation-113abc');CACHE=Path('workspace/sources/series113')
SOURCES={
 'flyvis':{'url':'https://github.com/TuragaLab/flyvis.git','commit':'92b3845cc426dd309a1a0e1b3890156c42e14021','file':'flyvis/connectome/fib25-fib19_v2.2.json','sha':'bfbb0766251ff09e22723d0ebbf7b14793e70b3ae8ad0eea64eac9d28223351a'},
 'ol_annotations':{'url':'https://github.com/flyconnectome/ol_annotations.git','commit':'11a4c97980a08e726733e115f553faf8c7023044','file':'data/olmatching.tsv','sha':'87d83b9a971c7ae7405f43a26b42002a96a84afa2e2bd94deb83e4588308e87b'},
 'visual_parts':{'url':'https://github.com/murthylab/visual-system-parts-list.git','commit':'0d8574d46627ce7fadd968a3c5d602e837325373','file':'data/neuron_table.csv','sha':'8d1de464db0ce17906d5c224d6c1c0db7d4d43259be58a82a8393842d10e4e28'},
 'flywire_annotations':{'url':'https://github.com/flyconnectome/flywire_annotations.git','commit':'8587524c1748ce5ef2080822a2fc890fc03bf597','file':'supplemental_files/Supplemental_file1_neuron_annotations.tsv','sha':'9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be'},
}
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw')
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def manifest(folder):return{str(p.relative_to(folder)).replace('\\','/'):file_sha(p)for p in sorted(Path(folder).rglob('*'))if p.is_file()and p.name!='complete.json'}
def git(args,cwd=None):
 q=subprocess.run(['git',*args],cwd=cwd,text=True,capture_output=True)
 if q.returncode:raise RuntimeError('git '+' '.join(args)+'\n'+q.stdout+'\n'+q.stderr)
 return q.stdout.strip()
def acquire(name,spec,cache,progress,fraction):
 d=cache/name;d.mkdir(parents=True,exist_ok=True)
 if not(d/'.git').exists():git(['init'],d);git(['remote','add','origin',spec['url']],d)
 elif git(['remote','get-url','origin'],d)!=spec['url']:raise ValueError(f'{name}: source URL изменён.')
 progress(f'Загружается exact source: {name}',fraction,0,1);git(['fetch','--depth','1','origin',spec['commit']],d);git(['checkout','--detach','--force','FETCH_HEAD'],d)
 if git(['rev-parse','HEAD'],d)!=spec['commit']:raise ValueError(f'{name}: commit mismatch')
 # Read the Git blob, not the checked-out file: Windows core.autocrlf may rewrite LF to CRLF.
 q=subprocess.run(['git','show',spec['commit']+':'+spec['file']],cwd=d,capture_output=True)
 if q.returncode:raise RuntimeError(f'{name}: git show failed: '+q.stderr.decode('utf8','replace'))
 exact=cache/'exact_blobs';exact.mkdir(parents=True,exist_ok=True);p=exact/(name+'_'+Path(spec['file']).name);p.write_bytes(q.stdout)
 if file_sha(p)!=spec['sha']:raise ValueError(f'{name}: Git blob SHA mismatch; expected {spec["sha"]}, got {file_sha(p)}')
 return p
def norm(x):return(x or'').strip()
def calculation_a(flyvis_path,match_path,neurons_path):
 fly=sorted({norm(x.get('name'))for x in json.loads(Path(flyvis_path).read_text(encoding='utf8'))['nodes']})
 with Path(match_path).open(encoding='utf8')as f:matches=list(csv.DictReader(f,delimiter='\t'))
 with Path(neurons_path).open(encoding='utf8')as f:neurons=list(csv.DictReader(f))
 roots=defaultdict(list)
 for r in neurons:
  t=norm(r.get('resolved type'));rid=norm(r.get('cell ID'))
  if t and rid:roots[t].append(rid)
 index=defaultdict(list)
 for r in matches:
  for c in('OL_type','Matsliah_type','Schlegel_type'):
   v=norm(r.get(c))
   if v and v!='NA':index[v].append(r)
 records=[];all_roots=[]
 for t in fly:
  rs=sorted(set(roots.get(t,[])));mr=index.get(t,[]);reviewed=any(norm(x.get('matched as'))not in('','NA','unmatched')for x in mr)
  if rs and reviewed:status='reviewed_type_to_root_set'
  elif rs:status='direct_name_root_set_without_cross_dataset_match'
  elif mr:status='reviewed_type_without_root_set'
  else:status='unmatched'
  records.append({'flyvis_type':t,'status':status,'root_count':len(rs),'root_ids':rs,'match_relations':sorted(set(norm(x.get('matched as'))for x in mr if norm(x.get('matched as'))not in('','NA'))),'match_urls':sorted(set(norm(x.get('URL'))for x in mr if norm(x.get('URL'))not in('','NA')))})
  all_roots.extend(rs)
 counts=Counter(x['status']for x in records);mapped=sum(x['root_count']>0 for x in records);reviewed=sum(x['status']=='reviewed_type_to_root_set'for x in records);passed=mapped>=47 and reviewed>=45 and len(all_roots)==len(set(all_roots))
 return{'schema':'flyvis-flywire-type-bridge-v1','flyvis_types':len(fly),'mapped_type_root_sets':mapped,'reviewed_type_root_sets':reviewed,'status_counts':dict(counts),'total_assigned_roots':len(all_roots),'root_sets_disjoint':len(all_roots)==len(set(all_roots)),'coverage_gate':'>=47/65 types with root sets and >=45 reviewed type matches; root sets disjoint','passed':passed,'interpretation':'Type-to-root-set bridge only; not a one-to-one functional neuron identity or retinotopic column registration.','records':records}
def calculation_b(annotations_path):
 with Path(annotations_path).open(encoding='utf8')as f:r=csv.DictReader(f,delimiter='\t');fields=r.fieldnames or[];rows=[x for x in r if norm(x.get('super_class')).lower()=='descending']
 roots=[norm(x.get('root_id'))for x in rows if norm(x.get('root_id'))];types=[norm(x.get('cell_type'))for x in rows if norm(x.get('cell_type'))];typed=sum(bool(norm(x.get('cell_type')))for x in rows);male_link=sum(bool(norm(x.get('supertype')))for x in rows);hemi_link=sum(bool(norm(x.get('hemibrain_type')))for x in rows)
 # Official annotation table has anatomy/type fields, but no machine-readable action-validation field.
 action_fields=[x for x in fields if any(k in x.lower()for k in('behavior','action','groom','reach','rub','function','stimulat','silenc'))]
 action={a:{'functionally_validated_root_ids':[],'connectome_candidates':[],'ready':False,'reason':'no preregistered machine-readable functional action label in pinned official annotation source'}for a in ACTIONS}
 inventory_ok=len(rows)>=1000 and len(roots)==len(set(roots)) and typed>=1000;readout_ready=all(x['ready']for x in action.values())
 return{'schema':'motor-readout-readiness-v1','descending_rows':len(rows),'unique_root_ids':len(set(roots)),'typed_rows':typed,'unique_types':len(set(types)),'male_cns_supertype_links':male_link,'hemibrain_type_links':hemi_link,'machine_readable_action_fields':action_fields,'anatomical_inventory_passed':inventory_ok,'actions':action,'validated_three_action_readout':readout_ready,'passed':readout_ready,'interpretation':'The official source supports a descending-neuron inventory, not a functionally validated three-action joint-command readout. Anatomy-only candidates must not be relabeled as validated.'}
def calculation_c(a,b,r112):
 gates={
  'frozen_functional_observation_to_action_surrogate':bool(r112.get('primary',{}).get('passed')),
  'reviewed_visual_type_to_root_set_bridge':bool(a['passed']),
  'descending_neuron_anatomical_inventory':bool(b['anatomical_inventory_passed']),
  'functionally_validated_three_action_motor_readout':bool(b['validated_three_action_readout']),
  'biological_observation_recordings_same_identified_neurons':False,
  'biological_execution_recordings_same_identified_neurons':False,
  'matched_visual_motion_and_action_identity_controls_in_biology':False,
  'causal_biological_intervention':False,
  'independent_animals_and_replication':False,
 }
 method_gates=('frozen_functional_observation_to_action_surrogate','reviewed_visual_type_to_root_set_bridge','descending_neuron_anatomical_inventory');method_ready=all(gates[k]for k in method_gates);biological_candidate=all(gates.values())
 return{'schema':'fly-first-mirror-evaluation-v1','scope':'Drosophila-first; species-neutral field names are frozen for later external validation','gates':gates,'method_foundation_ready':method_ready,'biological_mirror_neuron_candidate':biological_candidate,'scientific_result':False,'decision':'foundation_ready_biological_gate_open'if biological_candidate else('foundation_ready_biological_evidence_pending'if method_ready else'foundation_not_ready'),'next_required':['preregister and source literature-backed action labels for all three actions','obtain observation and execution recordings from the same identified neurons','run matched motion/action controls and causal intervention across independent flies']}
def fixture_sources(folder):
 folder.mkdir(parents=True,exist_ok=True);paths={}
 fly={'nodes':[{'name':'T4a'},{'name':'T5a'}]};(folder/'fly.json').write_text(json.dumps(fly));paths['flyvis']=folder/'fly.json'
 (folder/'match.tsv').write_text('OL_type\tMatsliah_type\tSchlegel_type\tmatched as\tURL\nT4a\tT4a\tT4a\t1-to-1\thttps://example/T4a\nT5a\tT5a\tT5a\t1-to-1\thttps://example/T5a\n');paths['ol_annotations']=folder/'match.tsv'
 (folder/'neurons.csv').write_text('cell ID,resolved type\n1,T4a\n2,T5a\n');paths['visual_parts']=folder/'neurons.csv'
 (folder/'ann.tsv').write_text('root_id\tsuper_class\tcell_type\tsupertype\themibrain_type\n10\tdescending\tDNx\t1\tDNx\n');paths['flywire_annotations']=folder/'ann.tsv';return paths
def run(output_root=ROOT,cache_root=CACHE,fixture=False,progress=lambda*x:None):
 if file_sha(RESULT112)!=RESULT112_SHA:raise ValueError('Exact genuine Series112 result изменён.')
 r112=json.loads(RESULT112.read_text(encoding='utf8'))
 if r112.get('status')!='completed'or r112.get('primary',{}).get('physical_development_candidate')is not True or r112.get('primary',{}).get('scientific_result')is not False:raise ValueError('Series113 требует exact successful Series112 result.')
 root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('fly_mirror_foundation_113abc_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();progress('Проверяется Series112',.02,0,1)
 if fixture:paths=fixture_sources(folder/'fixture_sources')
 else:
  cache=Path(cache_root);cache.mkdir(parents=True,exist_ok=True);paths={}
  for i,(n,s)in enumerate(SOURCES.items()):paths[n]=acquire(n,s,cache,progress,.05+.45*(i+1)/len(SOURCES))
 progress('113A: FlyVis→FlyWire bridge',.58,0,3);a=calculation_a(paths['flyvis'],paths['ol_annotations'],paths['visual_parts'])
 if fixture:a['coverage_gate']='fixture';a['passed']=True
 progress('113B: motor-readout readiness',.72,1,3);b=calculation_b(paths['flywire_annotations'])
 if fixture:b['anatomical_inventory_passed']=True
 progress('113C: fly-first mirror rubric',.86,2,3);c=calculation_c(a,b,r112)
 protocol={'schema':'fly-mirror-foundation-113abc-v1','mode':'fixture'if fixture else'full','created_utc':datetime.now(timezone.utc).isoformat(),'script_sha256':file_sha(__file__),'series112_result_sha256':RESULT112_SHA,'source_cutoff':'2026-09-18','sources':SOURCES,'post_result_tuning':False,'three_calculations':['A reviewed type-to-root-set bridge','B motor-readout readiness audit','C Drosophila-first mirror-evaluation rubric']};save(folder/'protocol.json',protocol)
 report={'schema':'fly-mirror-foundation-113abc-result-v1','status':'fixture_completed'if fixture else'completed','protocol':protocol,'calculation_a':a,'calculation_b':b,'calculation_c':c,'primary':{'source_bridge_passed':a['passed'],'motor_readout_validated':b['passed'],'method_foundation_ready':c['method_foundation_ready'],'biological_mirror_neuron_candidate':c['biological_mirror_neuron_candidate'],'scientific_result':False},'limitations':['Type mapping expands FlyVis types to sets of FlyWire neurons; no one-to-one identity is inferred.','Descending-neuron anatomy is not a validated action readout.','Series112 is supervised simulated engineering evidence, not biological recording.']};save(temp/'summary.json',report)
 with(temp/'flyvis_flywire_bridge.csv').open('w',newline='',encoding='utf8')as f:
  w=csv.writer(f);w.writerow(['flyvis_type','status','root_count','root_ids'])
  for x in a['records']:w.writerow([x['flyvis_type'],x['status'],x['root_count'],';'.join(x['root_ids'])])
 (temp/'ИТОГ.txt').write_text('SERIES113A-C: FLY MIRROR FOUNDATION\n\nA bridge: '+('PASS'if a['passed']else'NO-GO')+'\nB validated motor readout: '+('PASS'if b['passed']else'NOT YET')+'\nC foundation: '+c['decision']+'\nBiological mirror-neuron claim: NO.\n',encoding='utf-8-sig');save(temp/'complete.json',{'files':manifest(temp)});temp.rename(folder/'result');progress('Готово',1.,3,3);return folder/'result'
def gui():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Series113A-C: fly mirror foundation');root.geometry('900x500+70+40');root.attributes('-topmost',True);status=tk.StringVar(value='Exact official sources будут загружены с GitHub');pct=tk.DoubleVar(value=0);overall=tk.StringVar(value='Общий прогресс: 0,0%');eta=tk.StringVar(value='Оставшееся время появится после начала');start=[None]
 tk.Label(root,text='Series113A-C: три расчёта одним запуском',font=('Arial',14,'bold'),pady=14).pack();tk.Label(root,text='A FlyVis→FlyWire bridge · B motor-readout readiness · C fly-first mirror rubric\nИсточники pinned до cutoff; anatomy не подменяет functional validation.',justify='center').pack();tk.Label(root,textvariable=status,pady=10).pack();tk.Scale(root,variable=pct,from_=0,to=100,orient='horizontal',length=700,state='disabled').pack();tk.Label(root,textvariable=overall,font=('Arial',10,'bold')).pack();tk.Label(root,textvariable=eta).pack();button=tk.Button(root,text='Запустить три расчёта',padx=22,pady=10);button.pack(pady=16)
 def update(text,fraction,done,total):
  def apply():
   p=round(100*fraction,1);status.set(text);pct.set(p);overall.set(f'Общий прогресс: {p:.1f}%'.replace('.',','))
   if start[0]and fraction>.03:e=time.time()-start[0];eta.set(f'Прошло {e/60:.1f} мин · осталось примерно {e*(1-fraction)/fraction/60:.1f} мин')
  root.after(0,apply)
 def begin():
  button.config(state='disabled');start[0]=time.time()
  def work():
   try:
    result=run(progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(result))
     messagebox.showinfo('Series113A-C','Три расчёта завершены.',parent=root);button.config(state='normal')
    root.after(0,ok)
   except Exception as exc:
    error=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-113ABC.txt';error.parent.mkdir(parents=True,exist_ok=True);error.write_text(type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
     try:os.startfile(str(error.resolve()))
     except OSError:pass
    root.after(0,lambda:(messagebox.showerror('Series113A-C',f'{exc}\n\nОтчёт: {error.resolve()}',parent=root),button.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 button.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--fixture',action='store_true');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--cache-root',default=str(CACHE));a=p.parse_args()
 if a.gui:gui()
 else:print(run(a.output_root,a.cache_root,a.fixture))
if __name__=='__main__':main()
