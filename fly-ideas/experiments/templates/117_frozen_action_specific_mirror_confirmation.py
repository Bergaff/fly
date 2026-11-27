#!/usr/bin/env python3
"""Series117: frozen digital action-specific observe/execute confirmation."""
from __future__ import annotations
import argparse,csv,hashlib,json,os,threading,traceback,uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;REPORTS=HERE.parent/'reports';ROOT=Path('workspace/runs/ideas/i-observational/frozen-action-specific-mirror-117')
R116=REPORTS/'biological-digital-pipeline-116abc-user-result.json';R116_SHA='3bf8603cccc0b2770775bb4cbc5f846221303e0d5c1860b0f5c4fc547a1e6bf1'
MATRIX=REPORTS/'biological-digital-pipeline-116a-61x61.csv';MATRIX_SHA='03157b503d0271cb0991db524d45220bb8f49ce62e3ba171dc997ed7f3816150'
PATHS=REPORTS/'biological-digital-pipeline-116b-61x8.csv';PATHS_SHA='4186bb6fdbe0a0e81f8626469027976ade1d416ff0549af94b85fb1b07aa3ca1'
MANIFEST=REPORTS/'biological-digital-pipeline-116a-root-manifest.csv';MANIFEST_SHA='37c92d1d7b4bf75824ff1a214f8d3ece8de773990e90039bff9a9e88a2711288'
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw');RIDGE=.01;MARGIN=.1;CONTROL_ADVANTAGE=.2
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def normrows(x):return x/np.maximum(x.sum(1,keepdims=True),1e-15)
def cosine(a,b):
 a=a-a.mean();b=b-b.mean();return float(a@b/max(np.linalg.norm(a)*np.linalg.norm(b),1e-15))
def read_matrix(path):
 with Path(path).open(encoding='utf8')as f:r=list(csv.reader(f));return r[0][1:],[z[0]for z in r[1:]],np.array([[float(v)for v in z[1:]]for z in r[1:]],float)
def fit(pairs):
 O=np.array([q['observation']for q in pairs]);X=np.array([q['execution']for q in pairs]);mo=O.mean(0);mx=X.mean(0);A=O-mo;B=X-mx;M=np.linalg.solve(B.T@B+RIDGE*np.eye(B.shape[1]),B.T@A);return mo,mx,M
def evaluate(final,mo,mx,M,execution_override=None):
 O=[q['observation']-mo for q in final];E=[((q['execution']if execution_override is None else execution_override[i])-mx)@M for i,q in enumerate(final)];labels=[q['action_index']for q in final];n=len(final);S=np.array([[cosine(O[i],E[j])for j in range(n)]for i in range(n)]);pred=[]
 for i in range(n):pred.append(max(range(3),key=lambda a:float(np.mean([S[i,j]for j in range(n)if labels[j]==a]))))
 same=float(np.mean([S[i,j]for i in range(n)for j in range(n)if labels[i]==labels[j]]));other=float(np.mean([S[i,j]for i in range(n)for j in range(n)if labels[i]!=labels[j]]));return{'same_action_mean':same,'other_action_mean':other,'margin':same-other,'correct':sum(a==b for a,b in zip(pred,labels)),'total':n,'predicted':pred,'similarity':S}
def run(output_root=ROOT,progress=lambda *_:None):
 for p,h in((R116,R116_SHA),(MATRIX,MATRIX_SHA),(PATHS,PATHS_SHA),(MANIFEST,MANIFEST_SHA)):
  if sha(p)!=h:raise ValueError(f'Exact frozen input changed: {p.name}')
 r116=json.loads(R116.read_text(encoding='utf8'));types,mrows,raw=read_matrix(MATRIX);dns,ptypes,P=read_matrix(PATHS)
 if types!=mrows or types!=ptypes or len(types)!=61 or len(dns)!=8 or P.shape!=(61,8):raise ValueError('Series116 matrix/path dimensions changed.')
 W=normrows(np.log1p(raw));candidates=[x['flyvis_type']for x in r116['direction_c_digital_mirror_evaluation']['descriptive_type_candidates']];ci=np.array([types.index(t)for t in candidates]);progress('Frozen inputs and candidates',.12)
 u,_,_=np.linalg.svd(P,full_matrices=False);proto=normrows(np.abs(u[:,:3].T));proto=normrows(np.maximum(proto+proto@W,0));train=[];final=[]
 for ai in range(3):
  for k in range(10):
   rng=np.random.default_rng(117000+ai*100+k);z=np.maximum(proto[ai]*(1+rng.normal(0,.14,len(types)))+rng.uniform(0,.001,len(types)),0);z/=z.sum();dn=z@P;o=z@W+z;e=dn@P.T;e=e@W+e;q={'action':ACTIONS[ai],'action_index':ai,'case_id':f'117-{ai}-{k}','observation':o[ci],'execution':e[ci],'visual':z}
   (train if k<6 else final).append(q)
 progress('Fit development alignment',.42);mo,mx,M=fit(train);real=evaluate(final,mo,mx,M)
 # Pairing control: rotate training observations by one complete six-case action block.
 paired=[]
 for i,q in enumerate(train):paired.append({**q,'observation':train[(i+6)%len(train)]['observation']})
 pmo,pmx,PM=fit(paired);label_control=evaluate(final,pmo,pmx,PM)
 # Strong structural control: retrain and test after fixed visual-type row shuffle.
 rng=np.random.default_rng(117999);Ps=P[rng.permutation(len(types))];strain=[];sfinal=[]
 for source,target in((train,strain),(final,sfinal)):
  for q in source:
   dn=q['visual']@Ps;e=dn@Ps.T;e=e@W+e;target.append({**q,'execution':e[ci]})
 smo,smx,SM=fit(strain);structure_control=evaluate(sfinal,smo,smx,SM)
 identity_control=evaluate(final,mo,mx,M,[q['execution'][::-1]for q in final]);zero_control=evaluate(final,mo,mx,M,[np.zeros(len(ci))for _ in final]);progress('Frozen final and controls',.78)
 gate=real['margin']>=MARGIN and real['correct']>=10 and all(real['margin']>=z['margin']+CONTROL_ADVANTAGE for z in(label_control,structure_control,identity_control)) and real['correct']>max(label_control['correct'],structure_control['correct'],identity_control['correct'],zero_control['correct'])
 def compact(z):return{k:v for k,v in z.items()if k!='similarity'}
 result={'schema':'frozen-action-specific-mirror-confirmation-117-v1','status':'completed','created_utc':datetime.now(timezone.utc).isoformat(),'protocol':{'series116_user_sha256':R116_SHA,'matrix_sha256':MATRIX_SHA,'paths_sha256':PATHS_SHA,'manifest_sha256':MANIFEST_SHA,'frozen_candidate_types':candidates,'development_cases':len(train),'untouched_final_cases':len(final),'ridge':RIDGE,'primary_margin_threshold':MARGIN,'minimum_margin_advantage_over_controls':CONTROL_ADVANTAGE,'post_final_tuning':False,'development_disclosure':'method and thresholds developed after Series116; Series117 final seeds first evaluated by this frozen runner'},'real':compact(real),'controls':{'rotated_action_pairing':compact(label_control),'retrained_shuffled_structure':compact(structure_control),'reversed_candidate_identity':compact(identity_control),'zero_execution':compact(zero_control)},'candidate_root_counts':{x['flyvis_type']:x['root_count']for x in r116['direction_c_digital_mirror_evaluation']['descriptive_type_candidates']},'primary':{'action_specific_digital_confirmation_passed':bool(gate),'same_action_margin':real['margin'],'all_controls_beaten':bool(real['correct']>max(label_control['correct'],structure_control['correct'],identity_control['correct'],zero_control['correct'])),'computational_mirror_candidates':candidates if gate else[],'biological_mirror_neuron_claim':False,'scientific_biological_result':False}}
 folder=Path(output_root)/('frozen_action_specific_mirror_117_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True);save(folder/'summary.json',result)
 with(folder/'final_similarity_12x12.csv').open('w',newline='',encoding='utf8')as f:w=csv.writer(f);w.writerow(['observation_case',*[q['case_id']for q in final]]);[w.writerow([final[i]['case_id'],*[f'{v:.12g}'for v in real['similarity'][i]]])for i in range(len(final))]
 with(folder/'frozen_candidates.csv').open('w',newline='',encoding='utf8')as f:w=csv.writer(f);w.writerow(['rank','flyvis_type','root_count']);[w.writerow([i+1,t,result['candidate_root_counts'][t]])for i,t in enumerate(candidates)]
 (folder/'ИТОГ.txt').write_text(f"SERIES117 — FROZEN ACTION-SPECIFIC DIGITAL CONFIRMATION\n\nFinal: {real['correct']}/{real['total']}; margin={real['margin']:.6f}.\nControls correct: pairing={label_control['correct']}, structure={structure_control['correct']}, identity={identity_control['correct']}, zero={zero_control['correct']}.\nPrimary pass={gate}.\nComputational candidates={len(candidates)if gate else 0}.\nBiological mirror-neuron claim=NO.\n",encoding='utf-8-sig');progress('Готово',1.0);return folder
def gui():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.title('Series117: frozen action-specific confirmation');root.geometry('820x400+80+50');root.attributes('-topmost',True);s=tk.StringVar(value='12 кандидатов и final seeds заморожены');p=tk.DoubleVar(value=0)
 tk.Label(root,text='Series117 — action-specific digital confirmation',font=('Arial',14,'bold'),pady=18).pack();tk.Label(root,text='18 development cases ·12 untouched final cases ·4 controls\nNo post-final tuning; no biological claim.',justify='center').pack();tk.Label(root,textvariable=s,pady=12).pack();tk.Scale(root,variable=p,from_=0,to=100,orient='horizontal',length=660,state='disabled').pack();b=tk.Button(root,text='Запустить frozen confirmation',padx=24,pady=10);b.pack(pady=18)
 def update(t,f):root.after(0,lambda:(s.set(f'{t}: {100*f:.1f}%'),p.set(100*f)))
 def begin():
  b.config(state='disabled')
  def work():
   try:
    folder=run(progress=update)
    def ok():
     if os.name=='nt':os.startfile(str(folder.resolve()))
     messagebox.showinfo('Series117',f'Frozen confirmation завершён.\n{folder.resolve()}',parent=root);b.config(state='normal')
    root.after(0,ok)
   except Exception as e:
    q=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-117.txt';q.parent.mkdir(parents=True,exist_ok=True);q.write_text(type(e).__name__+': '+str(e)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');root.after(0,lambda:(messagebox.showerror('Series117',f'{e}\n\n{q.resolve()}',parent=root),b.config(state='normal')))
  threading.Thread(target=work,daemon=True).start()
 b.config(command=begin);root.mainloop()
def main():
 p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--output-root',default=str(ROOT));a=p.parse_args();gui()if a.gui else print(run(a.output_root))
if __name__=='__main__':main()
