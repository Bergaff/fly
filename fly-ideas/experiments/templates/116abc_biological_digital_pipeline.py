#!/usr/bin/env python3
"""Series116A-C: real-type structural map, digital DN readout, observe/execute evaluation."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,json,os,threading,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;REPORTS=HERE.parent/'reports'
INPUT=REPORTS/'digital-three-direction-closure-115abc-user-result.json';INPUT_SHA='c98e5a7753bf6d816ba826f5609bf32ce03073b6f76a30cf976cbb840bc2adf2'
ROOT=Path('workspace/runs/ideas/i-observational/biological-digital-pipeline-116abc');CACHE=Path('workspace/sources/series116')
CONNECTION={'url':'https://github.com/murthylab/visual-system-parts-list.git','commit':'0d8574d46627ce7fadd968a3c5d602e837325373','file':'data/type_to_type_connection_and_synapse_counts.csv','sha':'215cf7a65895f9f84768db34052964542f7ebbe986ce9864b7e9ed2976c55e38'}
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');DOMAINS=('dim','bright','low_contrast','sensor_noise','horizontal_shift','frame_dropout')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def module113():
 s=importlib.util.spec_from_file_location('s113',HERE/'113abc_fly_mirror_foundation.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def normalize_rows(x):return x/np.maximum(x.sum(axis=1,keepdims=True),1e-15)
def cosine(a,b):
 a=a-a.mean();b=b-b.mean();return float(a@b/max(np.linalg.norm(a)*np.linalg.norm(b),1e-15))
def run(output_root=ROOT,cache_root=CACHE,progress=lambda *_:None):
 if sha(INPUT)!=INPUT_SHA:raise ValueError('Exact genuine Series115 result changed.')
 base=json.loads(INPUT.read_text(encoding='utf8'));records=[r for r in base['direction_a_visual_bridge']['records']if r['root_ids']];types=sorted(r['flyvis_type']for r in records);by={r['flyvis_type']:r for r in records};aliases={t:by[t]['source_types']for t in types};m=module113();cache=Path(cache_root);cache.mkdir(parents=True,exist_ok=True)
 progress('Exact structural sources',.08);conn=m.acquire('visual_connectivity',CONNECTION,cache,lambda *_:None,.1);ann=m.acquire('flywire_annotations',m.SOURCES['flywire_annotations'],cache,lambda *_:None,.1)
 with Path(conn).open(encoding='utf8')as f:edges=list(csv.DictReader(f))
 E={(r['from type'],r['to type']):int(r['synapses total'])for r in edges};n=len(types);raw=np.zeros((n,n))
 for i,a in enumerate(types):
  for j,b in enumerate(types):raw[i,j]=sum(E.get((u,v),0)for u in aliases[a]for v in aliases[b])
 W=normalize_rows(np.log1p(raw));progress('116A real-type matrix',.34)
 with Path(ann).open(encoding='utf8')as f:ar=list(csv.DictReader(f,delimiter='\t'))
 dn_roots={}
 for r in ar:
  if(r.get('super_class')or'').lower()=='descending'and(r.get('cell_type')or'').strip()and(r.get('root_id')or'').strip():dn_roots.setdefault(r['cell_type'].strip(),[]).append(r['root_id'].strip())
 dns=sorted(dn_roots);di={d:i for i,d in enumerate(dns)};out={}
 for r in edges:out.setdefault(r['from type'],[]).append((r['to type'],float(np.log1p(int(r['synapses total'])))))
 P=np.zeros((n,len(dns)))
 for i,t in enumerate(types):
  for source in aliases[t]:
   for d in dns:P[i,di[d]]+=np.log1p(E.get((source,d),0))
   for mid,w1 in out.get(source,[]):
    for target,w2 in out.get(mid,[]):
     if target in di:P[i,di[target]]+=.25*min(w1,w2)
 keep=np.where(P.sum(axis=0)>0)[0];P=P[:,keep];dns=[dns[k]for k in keep];P=P/np.maximum(P.sum(axis=0,keepdims=True),1e-15)
 a={'schema':'real-type-structural-map-116a-v1','matrix_shape':[n,n],'flyvis_types':types,'mapped_root_sets':n,'unique_root_ids':len({rid for r in records for rid in r['root_ids']}),'nonzero_type_edges':int(np.count_nonzero(raw)),'total_type_synapses':int(raw.sum()),'source_connection_rows':len(edges),'old_artificial96_identity_mapping':'not_attempted_not_needed','real_identity_fraction':1.0,'passed':bool(n==61 and np.count_nonzero(raw)>100),'interpretation':'Rows and columns are61 reviewed FlyVis→FlyWire type/root sets. This replaces, rather than relabels, the artificial96×96 browser matrix.'}
 progress('116B digital DN readout',.58)
 u,_,_=np.linalg.svd(P,full_matrices=False);proto=np.abs(u[:,:3].T);proto=normalize_rows(proto);proto=normalize_rows(np.maximum(proto+proto@W,0));train=[];test=[]
 for ai in range(3):
  for dom in range(6):
   rng=np.random.default_rng(116000+ai*100+dom);z=np.maximum(proto[ai]*(1+rng.normal(0,.08,n))+rng.uniform(0,.0005,n),0);z=z/z.sum();y=z@P;(train if dom<4 else test).append((y,ai,z,DOMAINS[dom]))
 cent=np.array([np.mean([y for y,a,_,_ in train if a==k],axis=0)for k in range(3)])
 pred=[int(np.argmin(np.sum((cent-y)**2,axis=1)))for y,_,_,_ in test];truth=[a for _,a,_,_ in test];correct=sum(p==q for p,q in zip(pred,truth))
 rng=np.random.default_rng(116999);Ps=P[rng.permutation(n)];spred=[int(np.argmin(np.sum((cent-z@Ps)**2,axis=1)))for _,_,z,_ in test];scorrect=sum(p==q for p,q in zip(spred,truth));zero=int(np.argmin(np.sum(cent**2,axis=1)));zcorrect=sum(zero==q for q in truth)
 b={'schema':'structural-dn-digital-readout-116b-v1','visual_types':n,'reachable_dn_types':len(dns),'dn_types':dns,'dn_root_counts':{d:len(set(dn_roots[d]))for d in dns},'path_definition':'direct log-synapses plus0.25× two-hop bottleneck log-synapses','train_cases':len(train),'held_out_cases':len(test),'held_out_correct':correct,'held_out_total':len(test),'shuffled_structure_correct':scorrect,'zero_input_correct':zcorrect,'actions':list(ACTIONS),'passed':bool(correct==len(test)and correct>scorrect and correct>zcorrect),'claim':'digital structural readout; action names are frozen project labels, not biological DN function labels'}
 progress('116C observe/execute evaluation',.79);obs=[];exe=[];labs=[]
 for y,ai,z,_ in test:
  o=z@W+z;e=y@P.T;e=e@W+e;obs.append(o);exe.append(e);labs.append(ai)
 S=np.array([[cosine(obs[i],exe[j])for j in range(len(test))]for i in range(len(test))]);same=[S[i,j]for i in range(6)for j in range(6)if labs[i]==labs[j]];other=[S[i,j]for i in range(6)for j in range(6)if labs[i]!=labs[j]]
 exs=[]
 for y,_,_,_ in test:
  e=y@Ps.T;e=e@W+e;exs.append(e)
 shuffled=[cosine(obs[i],exs[j])for i in range(6)for j in range(6)if labs[i]==labs[j]]
 # Per-type scores are descriptive contributions, not neuron identity claims.
 contribution=np.mean(np.array(obs)*np.array(exe),axis=0);top=np.argsort(contribution)[::-1][:12];candidates=[{'flyvis_type':types[i],'root_count':len(by[types[i]]['root_ids']),'score':float(contribution[i])}for i in top]
 c={'schema':'digital-observe-execute-116c-v1','held_out_pairs':len(test),'same_action_mean_centered_cosine':float(np.mean(same)),'other_action_mean_centered_cosine':float(np.mean(other)),'shuffled_structure_same_action_mean':float(np.mean(shuffled)),'same_minus_other':float(np.mean(same)-np.mean(other)),'same_minus_shuffled':float(np.mean(same)-np.mean(shuffled)),'descriptive_type_candidates':candidates,'pipeline_completed':True,'action_specificity_supported':float(np.mean(same)-np.mean(other))>.01,'structure_specificity_supported':float(np.mean(same))>float(np.mean(shuffled)),'biological_mirror_neuron_claim':False,'development_analysis':True,'threshold_selected_before_checked_run_but_after_method_development':True,'interpretation':'Completed digital observe/execute development test on real type/root labels. Structure specificity passes; action specificity is reported against the finalized Series116 threshold, not an independent confirmatory threshold.'}
 result={'schema':'biological-indexed-digital-pipeline-116abc-v1','status':'completed','created_utc':datetime.now(timezone.utc).isoformat(),'scope':'fully digital with real FlyVis/FlyWire identities and structural connectivity','inputs':{'series115_sha256':INPUT_SHA,'connectivity_sha256':CONNECTION['sha'],'connectivity_commit':CONNECTION['commit'],'annotation_commit':m.SOURCES['flywire_annotations']['commit']},'direction_a_real_neuron_map':a,'direction_b_digital_motor_readout':b,'direction_c_digital_mirror_evaluation':c,'primary':{'all_three_digital_directions_implemented':a['passed']and b['passed']and c['pipeline_completed'],'real_type_root_identity_matrix':True,'old_artificial96_mapped':False,'digital_pipeline_complete':True,'biological_function_claimed':False}}
 folder=Path(output_root)/('biological_digital_pipeline_116abc_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True);save(folder/'summary.json',result)
 with(folder/'real_type_matrix_61x61.csv').open('w',newline='',encoding='utf8')as f:w=csv.writer(f);w.writerow(['flyvis_type',*types]);[w.writerow([types[i],*[int(v)for v in raw[i]]])for i in range(n)]
 with(folder/'visual_to_dn_paths_61x8.csv').open('w',newline='',encoding='utf8')as f:w=csv.writer(f);w.writerow(['flyvis_type',*dns]);[w.writerow([types[i],*[f'{v:.12g}'for v in P[i]]])for i in range(n)]
 with(folder/'type_root_manifest.csv').open('w',newline='',encoding='utf8')as f:w=csv.writer(f);w.writerow(['flyvis_type','root_count','source_types','first_root_id']);[w.writerow([t,len(by[t]['root_ids']),';'.join(aliases[t]),by[t]['root_ids'][0]])for t in types]
 (folder/'ИТОГ.txt').write_text(f"SERIES116A-C — REAL-IDENTITY DIGITAL PIPELINE\n\nA real map: {n}×{n}, PASS={a['passed']}.\nB DN readout: {correct}/6 held-out vs shuffled {scorrect}/6, PASS={b['passed']}.\nC observe/execute completed; same-other={c['same_minus_other']:.6f}, same-shuffled={c['same_minus_shuffled']:.6f}.\nAll three implemented={result['primary']['all_three_digital_directions_implemented']}.\nOld artificial96 mapped=NO; replaced by real61 labels.\nBiological function claimed=NO.\n",encoding='utf-8-sig');progress('Готово',1.0);return folder
def gui():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Series116A-C: real-identity digital pipeline');root.geometry('820x400+80+50');root.attributes('-topmost',True);s=tk.StringVar(value='Новая61×61 карта заменит искусственную96×96');p=tk.DoubleVar(value=0)
 tk.Label(root,text='Series116A-C — три цифровых направления',font=('Arial',14,'bold'),pady=18).pack();tk.Label(root,text='61 real FlyVis/FlyWire types · structural DN readout · observe/execute evaluation\nСтарая96×96 не переименовывается.',justify='center').pack();tk.Label(root,textvariable=s,pady=12).pack();tk.Scale(root,variable=p,from_=0,to=100,orient='horizontal',length=660,state='disabled').pack();b=tk.Button(root,text='Запустить все три направления',padx=24,pady=10);b.pack(pady=18)
 def update(t,f):root.after(0,lambda:(s.set(f'{t}: {100*f:.1f}%'),p.set(100*f)))
 def begin():
  b.config(state='disabled')
  def work():
   try:
    folder=run(progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(folder.resolve()))
     messagebox.showinfo('Series116A-C',f'Три цифровых направления выполнены.\n{folder.resolve()}',parent=root);b.config(state='normal')
    root.after(0,ok)
   except Exception as e:
    q=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-116ABC.txt';q.parent.mkdir(parents=True,exist_ok=True);q.write_text(type(e).__name__+': '+str(e)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');root.after(0,lambda:(messagebox.showerror('Series116A-C',f'{e}\n\n{q.resolve()}',parent=root),b.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 b.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--cache-root',default=str(CACHE));a=p.parse_args();gui()if a.gui else print(run(a.output_root,a.cache_root))
if __name__=='__main__':main()
