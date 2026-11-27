#!/usr/bin/env python3
"""Series122: frozen same-task baselines for the narrow61-to-8 routing operation.

This is not a brain, controller, biological, or general-intelligence benchmark.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, threading, time, traceback, uuid
from datetime import datetime
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
REPORTS=HERE.parent/'reports'
PATHS=REPORTS/'biological-digital-pipeline-116b-61x8.csv'
PATHS_SHA='4186bb6fdbe0a0e81f8626469027976ade1d416ff0549af94b85fb1b07aa3ca1'
QWEN60=REPORTS/'local-ollama-narrow-benchmark-121-qwen2.5-7b-user-result-60.json'
OUTPUT_ROOT=Path('workspace/runs/ideas/i-observational/graph-core-baselines-122')
TRAIN_SEED=122_000_001; TEST_SEED=121_000_001; GENERALIZATION_SEED=122_000_003


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def read_paths():
    if sha(PATHS)!=PATHS_SHA: raise ValueError('Exact61x8 paths artifact changed.')
    rows=list(csv.reader(PATHS.open(encoding='utf8')))
    values=np.asarray([[float(x) for x in row[1:]] for row in rows[1:]],float)
    return rows[0][1:],[row[0] for row in rows[1:]],values/np.maximum(values.sum(1,keepdims=True),1e-15)

def make_arrays(count,seed):
    _,_,values=read_paths(); rng=np.random.default_rng(seed); xs=[]; ys=[]; signatures=set(); attempts=0
    while len(xs)<count and attempts<count*100:
        attempts+=1; selected=rng.choice(len(values),4,replace=False); weights=rng.uniform(.15,1,8); scores=values[selected]@weights; order=np.argsort(scores)[::-1]
        if scores[order[0]]-scores[order[1]]<.015: continue
        rounded_v=np.round(values[selected],6); rounded_w=np.round(weights,6)
        xs.append(np.concatenate([rounded_v,np.broadcast_to(rounded_w,(4,8))],axis=1)); ys.append(int(order[0])); signatures.add(hashlib.sha256(selected.tobytes()+rounded_w.tobytes()).hexdigest())
    if len(xs)!=count: raise RuntimeError('Could not construct separated cases.')
    return np.asarray(xs),np.asarray(ys),signatures

def fit_ridge(x,y,ridge=1e-6):
    z=np.column_stack([x,np.ones(len(x))]); return np.linalg.solve(z.T@z+ridge*np.eye(z.shape[1]),z.T@y)
def ridge_predict(x,w): return np.column_stack([x,np.ones(len(x))])@w

def fit_mlp(x,y,seed=122_000_002,steps=600):
    rng=np.random.default_rng(seed); mean=x.mean(0); std=np.maximum(x.std(0),1e-6); xn=(x-mean)/std; ym=float(y.mean()); ys=max(float(y.std()),1e-6); yn=(y-ym)/ys
    width=234; w1=rng.normal(0,np.sqrt(2/16),(16,width)); b1=np.zeros(width); w2=rng.normal(0,np.sqrt(2/width),width); b2=0.; params=[w1,b1,w2,np.asarray(b2)]; m=[np.zeros_like(p) for p in params]; v=[np.zeros_like(p) for p in params]
    for step in range(1,steps+1):
        idx=rng.integers(0,len(xn),min(256,len(xn))); xb=xn[idx]; target=yn[idx]; pre=xb@w1+b1; hidden=np.maximum(pre,0); pred=hidden@w2+b2; dp=2*(pred-target)/len(idx)
        grads=[xb.T@(dp[:,None]*w2[None,:]*(pre>0)),(dp[:,None]*w2[None,:]*(pre>0)).sum(0),hidden.T@dp,np.asarray(dp.sum())]
        for i,(p,g) in enumerate(zip(params,grads)):
            m[i]=.9*m[i]+.1*g; v[i]=.999*v[i]+.001*g*g; p-=.003*(m[i]/(1-.9**step))/(np.sqrt(v[i]/(1-.999**step))+1e-8)
        b2=float(params[3]); params[3]=np.asarray(b2)
    return {'mean':mean,'std':std,'y_mean':ym,'y_std':ys,'w1':w1,'b1':b1,'w2':w2,'b2':b2,'steps':steps}
def mlp_predict(x,m): return (np.maximum((x-m['mean'])/m['std']@m['w1']+m['b1'],0)@m['w2']+m['b2'])*m['y_std']+m['y_mean']

def scores_for(name,x,model=None):
    flat=x.reshape(-1,16)
    if name=='exact_dot': return (x[:,:,:8]*x[:,:,8:]).sum(2)
    if name=='max_weight_channel_rule':
        channel=np.argmax(x[:,0,8:],axis=1); indices=np.broadcast_to(channel[:,None,None],(len(x),4,1)); return np.take_along_axis(x[:,:,:8],indices,axis=2).squeeze(2)
    if name=='additive_linear_ridge': return ridge_predict(flat,model).reshape(len(x),4)
    if name=='diagonal_bilinear_ridge': return ridge_predict(flat[:,:8]*flat[:,8:],model).reshape(len(x),4)
    if name=='parameter_matched_mlp': return mlp_predict(flat,model).reshape(len(x),4)
    raise KeyError(name)
def accuracy(name,x,y,model=None): return float(np.mean(np.argmax(scores_for(name,x,model),axis=1)==y))
def timed(name,x,model=None,repeats=200):
    samples=[]
    for _ in range(repeats):
        start=time.perf_counter(); scores_for(name,x,model); samples.append((time.perf_counter()-start)/len(x))
    return {'mean_seconds_per_case':float(np.mean(samples)),'p50_seconds_per_case':float(np.quantile(samples,.5)),'p95_seconds_per_case':float(np.quantile(samples,.95)),'max_seconds_per_case':float(max(samples)),'repeats':repeats}

def run(test_cases,train_cases,output_root,progress=lambda *_:None):
    folder=output_root/('graph_core_baselines_122_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]); folder.mkdir(parents=True)
    train_x,train_y,train_sig=make_arrays(train_cases,TRAIN_SEED); test_x,test_y,test_sig=make_arrays(test_cases,TEST_SEED); gen_x,gen_y,gen_sig=make_arrays(max(600,test_cases),GENERALIZATION_SEED)
    if train_sig&(test_sig|gen_sig) or test_sig&gen_sig: raise RuntimeError('Split overlap detected.')
    flat=train_x.reshape(-1,16); targets=(train_x[:,:,:8]*train_x[:,:,8:]).sum(2).reshape(-1)
    models={
      'additive_linear_ridge':fit_ridge(flat,targets),
      'diagonal_bilinear_ridge':fit_ridge(flat[:,:8]*flat[:,8:],targets),
    }
    progress(1,3,'Обучаю MLP'); models['parameter_matched_mlp']=fit_mlp(flat,targets); progress(2,3,'Проверяю baselines')
    specs={
      'exact_dot':(4214,'frozen graph-core scalar capacity; operation itself uses supplied vectors'),
      'max_weight_channel_rule':(0,'hand rule; no fitted coefficients'),
      'additive_linear_ridge':(17,'16 coefficients plus intercept'),
      'diagonal_bilinear_ridge':(9,'8 interaction coefficients plus intercept'),
      'parameter_matched_mlp':(4213,'16x234 +234 biases +234 output weights +1 bias'),
    }
    rng=np.random.default_rng(122_000_004); random_pred=rng.integers(0,4,len(test_y))
    noisy=test_x.copy(); noisy[:,:,:8]=np.clip(noisy[:,:,:8]+rng.normal(0,.02,noisy[:,:,:8].shape),0,None)
    dropout=test_x.copy(); dropout[:,:,:8]*=(rng.random(dropout[:,:,:8].shape)>=.1)
    rows=[]
    for name in specs:
        model=models.get(name); pred=np.argmax(scores_for(name,test_x,model),axis=1); gen=accuracy(name,gen_x,gen_y,model)
        ablations=[]
        for channel in range(8):
            ab=test_x.copy(); ab[:,:,channel]=0; ablations.append(accuracy(name,ab,test_y,model))
        count,description=specs[name]
        rows.append({'name':name,'parameter_or_scalar_count':count,'approximate_fp32_parameter_bytes':count*4,'count_interpretation':description,'correct':int(np.sum(pred==test_y)),'accuracy':float(np.mean(pred==test_y)),'new_seed_accuracy':gen,'noise_std_0_02_accuracy_against_clean_labels':accuracy(name,noisy,test_y,model),'input_dropout_0_10_accuracy_against_clean_labels':accuracy(name,dropout,test_y,model),'single_channel_ablation_mean_accuracy':float(np.mean(ablations)),'timing':timed(name,test_x,model)})
    qwen=None
    if QWEN60.exists():
        q=json.loads(QWEN60.read_text(encoding='utf8')); qwen={'source_sha256':sha(QWEN60),'model':q['ollama']['model'],'case_count':q['benchmark_contract']['case_count'],'correct':q['ollama']['correct'],'accuracy':q['ollama']['accuracy'],'mean_wall_seconds_per_case':q['ollama']['mean_wall_seconds_per_case'],'external_prompted_reference_only':True}
    result={'schema':'graph-core-baseline-benchmark-122-v1','status':'completed','contract':{'task':'rank four candidates by the weighted8-channel dot product','train_cases':train_cases,'test_cases':test_cases,'new_seed_cases':len(gen_y),'train_seed':TRAIN_SEED,'test_seed':TEST_SEED,'new_seed':GENERALIZATION_SEED,'paths_sha256':PATHS_SHA,'splits_disjoint':True,'test_cases_match_series121_prefix':True,'not_controller_benchmark':True,'not_general_intelligence_benchmark':True,'not_biological_validation':True},'random_choice_reference':{'correct':int(np.sum(random_pred==test_y)),'accuracy':float(np.mean(random_pred==test_y)),'expected_accuracy':.25},'models':rows,'qwen_series121_reference':qwen,'interpretation':{'exact_solver_is_oracle_by_task_definition':True,'small_bilinear_model_may_be_sufficient':True,'graph_core_superiority_claim':False,'controller_claim':False,'general_ai_claim':False}}
    (folder/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['SERIES122 — SAME-TASK BASELINES','',f'Train: {train_cases} | Test: {test_cases} | New seed: {len(gen_y)}','']+[f"{r['name']}: {r['correct']}/{test_cases} ({r['accuracy']*100:.2f}%), params/scalars={r['parameter_or_scalar_count']}, mean={r['timing']['mean_seconds_per_case']*1e6:.3f} us/case" for r in rows]+['',f"Random seeded reference: {result['random_choice_reference']['correct']}/{test_cases}",'','This is a narrow arithmetic ranking benchmark, not a controller, brain, biology, or general-intelligence test.']
    (folder/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig'); progress(3,3,'Готово'); return folder

def gui():
    import tkinter as tk
    from tkinter import messagebox
    root=tk.Tk(); root.title('Series122: Graph Core и baselines'); root.geometry('720x390+100+70'); root.attributes('-topmost',True)
    tests=tk.IntVar(value=600); trains=tk.IntVar(value=2000); status=tk.StringVar(value='Готово к локальному запуску'); progress=tk.DoubleVar(value=0)
    tk.Label(root,text='Graph Core против простых baseline-моделей',font=('Arial',15,'bold'),pady=15).pack(); tk.Label(root,text='Одинаковая узкая числовая задача. Без Ollama.\nЭто не проверка контроллера, мозга или общего интеллекта.',justify='center').pack()
    form=tk.Frame(root); form.pack(pady=14); tk.Label(form,text='Train cases:').grid(row=0,column=0,padx=6,pady=5); tk.Spinbox(form,from_=500,to=10000,increment=500,textvariable=trains,width=9).grid(row=0,column=1); tk.Label(form,text='Test cases:').grid(row=1,column=0,padx=6,pady=5); tk.Spinbox(form,from_=60,to=3000,increment=60,textvariable=tests,width=9).grid(row=1,column=1)
    tk.Label(root,textvariable=status).pack(); from tkinter import ttk; ttk.Progressbar(root,variable=progress,maximum=3,length=540).pack(pady=8)
    button=tk.Button(root,text='Запустить Series122',padx=20,pady=9); button.pack(pady=10)
    def start():
        button.config(state='disabled'); tc,rc=int(tests.get()),int(trains.get())
        def work():
            try:
                out=run(tc,rc,OUTPUT_ROOT,lambda done,total,text:root.after(0,lambda:(progress.set(done),status.set(text))))
                def done():
                    button.config(state='normal'); status.set('Готово');
                    if os.name=='nt': os.startfile(str(out.resolve()))
                    messagebox.showinfo('Series122',f'Результат сохранён:\n{out.resolve()}',parent=root)
                root.after(0,done)
            except Exception as error:
                path=OUTPUT_ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-122.txt'; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(type(error).__name__+': '+str(error)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig'); root.after(0,lambda:(button.config(state='normal'),status.set('Ошибка'),messagebox.showerror('Series122',f'{error}\n\n{path.resolve()}',parent=root)))
        threading.Thread(target=work,daemon=True).start()
    button.config(command=start); root.mainloop()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--gui',action='store_true'); p.add_argument('--test-cases',type=int,default=600); p.add_argument('--train-cases',type=int,default=2000); p.add_argument('--output-root',type=Path,default=OUTPUT_ROOT); a=p.parse_args()
    if a.gui: gui()
    else: print(run(a.test_cases,a.train_cases,a.output_root))
if __name__=='__main__': main()
