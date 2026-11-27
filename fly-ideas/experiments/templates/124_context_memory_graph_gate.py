#!/usr/bin/env python3
"""Series124: context-necessary memory gate before any new physical FlyGym port."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,threading,time,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; BASE=HERE/'123_temporal_closed_loop_graph_benchmark.py'; BASE_SHA='73fd16bf5b730083d3e04308a58be739d5cfa26515f8a0658a462c1612be77ce'; OUTPUT_ROOT=Path('workspace/runs/ideas/i-observational/context-memory-graph-gate-124')
TRAIN_SEED=124_000_001; DEV_SEED=124_000_002; FINAL_SEED=124_000_003; STEPS=120; LEAKS=[.90,.95,.98,.995]; SENSOR_DELAY=2; MOTOR_DELAY=2
if hashlib.sha256(BASE.read_bytes()).hexdigest()!=BASE_SHA: raise ValueError('Frozen Series123 runner changed.')
spec=importlib.util.spec_from_file_location('series123_frozen',BASE); base=importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
g,paths,prototypes,motor,context_vec,phase_vec,random_matrix=base.CORE
NAMES=['memoryless_ridge','history8_ridge','random_reservoir61','graph_reservoir61','privileged_context_ridge','privileged_context_bilinear']

def blueprint(seed,count,condition='clean'):
    episodes=[]; permutation=np.asarray([1,2,0])
    for e in range(count):
        rng=np.random.default_rng(seed+e); context=int(rng.integers(0,2)); modes=[]; phases=[]; switches=[]; last=-1
        while len(modes)<STEPS:
            mode=int(rng.integers(0,3));
            if mode==last: mode=(mode+1+int(rng.integers(0,2)))%3
            length=int(rng.integers(16,29)); switches.append(len(modes)); modes.extend([mode]*length); phases.extend(np.arange(length)/max(1,length-1)); last=mode
        modes=np.asarray(modes[:STEPS]); phases=np.asarray(phases[:STEPS]); switches=[x for x in switches if 0<x<STEPS]; target=np.empty((STEPS,8)); obs=np.empty((STEPS,61)); observed=(rng.random(61)>.35).astype(float)
        for t,(mode,ph) in enumerate(zip(modes,phases)):
            mapped=mode if context==0 else int(permutation[mode]); wave=np.sin(2*np.pi*ph); target[t]=np.clip(motor[mapped]*(.72+.28*wave)+(.03 if context else -.03)*np.cos(np.arange(8)+2*np.pi*ph),-.62,.62)
            mode_cue=1.0 if any(0<=t-s<3 for s in switches+[0]) else .04; obs[t]=mode_cue*prototypes[mode]+.10*(phase_vec[0]*np.sin(2*np.pi*ph)+phase_vec[1]*np.cos(2*np.pi*ph))
            if t<3 and condition!='cue_loss': obs[t]+=.55*context_vec[context]
        noise=.018 if condition!='noise' else .06; obs=(obs+rng.normal(0,noise,obs.shape))*observed
        if condition=='partial': obs*=rng.random(obs.shape)>.25
        delay=SENSOR_DELAY+(2 if condition=='extra_delay' else 0); delivered=np.zeros_like(obs); delivered[delay:]=obs[:-delay]
        episodes.append({'context':context,'modes':modes,'switches':switches,'target':target,'obs':delivered,'disturbance':rng.normal(0,.006,(STEPS,8)),'motor_delay':MOTOR_DELAY+(2 if condition=='extra_delay' else 0)})
    return episodes

def step_reservoir(h,obs,body,matrix,leak):
    candidate=np.tanh(.18*(matrix.T@h)+6*obs+.16*(paths@body)); return leak*h+(1-leak)*candidate

def feature_episode(ep,bodies,name,leak=.98):
    h=np.zeros(61); history=[np.zeros(69) for _ in range(7)]; out=[]
    for t in range(STEPS):
        body=bodies[t-1] if t else np.zeros(8); raw=np.r_[ep['obs'][t],body]
        if name=='memoryless_ridge': feature=raw
        elif name=='history8_ridge': feature=np.concatenate(history+[raw]); history=(history+[raw])[1:]
        elif name=='privileged_context_ridge': feature=np.r_[raw,np.eye(2)[ep['context']]]
        elif name=='privileged_context_bilinear':
            ctx=np.eye(2)[ep['context']]; feature=np.r_[raw,ctx,ep['obs'][t]*ctx[0],ep['obs'][t]*ctx[1]]
        else: h=step_reservoir(h,ep['obs'][t],body,g if name=='graph_reservoir61' else random_matrix,leak); feature=np.r_[h,body]
        out.append(feature)
    return np.asarray(out)

def fit_ridge(x,y,alpha=1e-3):
    z=np.column_stack([x,np.ones(len(x))]); return np.linalg.solve(z.T@z+alpha*np.eye(z.shape[1]),z.T@y)
def predict(x,w): return np.append(x,1)@w

def train(name,episodes,leak=.98):
    features=[]; commands=[]; contexts=[]
    for ep in episodes:
        bodies,cmd=base.teacher_rollout(ep); f=feature_episode(ep,bodies,name,leak); features.append(f); commands.append(cmd); contexts.append(np.repeat(np.eye(2)[ep['context']][None,:],STEPS,axis=0))
    x=np.concatenate(features); return {'motor':fit_ridge(x,np.concatenate(commands)),'context':fit_ridge(x,np.concatenate(contexts)),'leak':leak}

def evaluate_episode(ep,name,model):
    body=np.zeros(8); queue=[np.zeros(8) for _ in range(ep['motor_delay'])]; h=np.zeros(61); history=[np.zeros(69) for _ in range(7)]; bodies=[]; context_hits=[]; start=time.perf_counter()
    for t in range(STEPS):
        raw=np.r_[ep['obs'][t],body]
        if name=='memoryless_ridge': feature=raw
        elif name=='history8_ridge': feature=np.concatenate(history+[raw]); history=(history+[raw])[1:]
        elif name=='privileged_context_ridge': feature=np.r_[raw,np.eye(2)[ep['context']]]
        elif name=='privileged_context_bilinear':
            ctx=np.eye(2)[ep['context']]; feature=np.r_[raw,ctx,ep['obs'][t]*ctx[0],ep['obs'][t]*ctx[1]]
        else: h=step_reservoir(h,ep['obs'][t],body,g if name=='graph_reservoir61' else random_matrix,model['leak']); feature=np.r_[h,body]
        command=np.clip(predict(feature,model['motor']),-2,2); context_hits.append(int(np.argmax(predict(feature,model['context']))==ep['context'])); queue.append(command); applied=queue.pop(0); body=base.dynamics(body,applied,ep['context'],ep['disturbance'][t]); bodies.append(body.copy())
    elapsed=time.perf_counter()-start; bodies=np.asarray(bodies); frame=np.sqrt(np.mean((bodies-ep['target'])**2,axis=1)); windows=[frame[s:min(STEPS,s+8)].mean() for s in ep['switches']]
    return {'rmse':float(np.sqrt(np.mean((bodies-ep['target'])**2))),'success_rate':float(np.mean(frame<.20)),'late_context_accuracy':float(np.mean(context_hits[12:])),'switch_error':float(np.mean(windows)),'seconds_per_step':elapsed/STEPS}
def aggregate(episodes,name,model):
    rows=[evaluate_episode(e,name,model) for e in episodes]; return {k:float(np.mean([r[k] for r in rows])) for k in rows[0]}
def count(name): return {'memoryless_ridge':560,'history8_ridge':4424,'random_reservoir61':3049,'graph_reservoir61':3049,'privileged_context_ridge':576,'privileged_context_bilinear':1552}[name]

def run(train_count,dev_count,final_count,output_root,progress=lambda *_:None):
    folder=output_root/('context_memory_gate_124_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]); folder.mkdir(parents=True); train_eps=blueprint(TRAIN_SEED,train_count); dev_eps=blueprint(DEV_SEED,dev_count); progress(1,5,'Development selection')
    selected={}; dev_table={}
    for name in NAMES:
        candidates=LEAKS if 'reservoir' in name else [.98]; rows=[]
        for leak in candidates:
            model=train(name,train_eps,leak); metric=aggregate(dev_eps,name,model); score=metric['rmse']+.08*(1-metric['late_context_accuracy']); rows.append({'leak':leak,'score':score,**metric})
        best=min(rows,key=lambda r:r['score']); selected[name]=train(name,train_eps,best['leak']); dev_table[name]={'selected_leak':best['leak'],'candidates':rows}
    progress(2,5,'Untouched final'); conditions=['clean','cue_loss','noise','partial','extra_delay']; tests={c:blueprint(FINAL_SEED,final_count,c) for c in conditions}; rows=[]
    for name in NAMES: rows.append({'name':name,'parameter_or_scalar_count':count(name),'selected_leak':selected[name]['leak'] if 'reservoir' in name else None,'conditions':{c:aggregate(tests[c],name,selected[name]) for c in conditions}})
    by={r['name']:r for r in rows}; clean=lambda n:by[n]['conditions']['clean']; context_necessary=clean('privileged_context_ridge')['late_context_accuracy']>.95 and clean('memoryless_ridge')['late_context_accuracy']<=.65
    graph_go=context_necessary and clean('graph_reservoir61')['late_context_accuracy']>=.80 and clean('graph_reservoir61')['rmse']+.005<min(clean('random_reservoir61')['rmse'],clean('memoryless_ridge')['rmse']) and by['graph_reservoir61']['conditions']['cue_loss']['late_context_accuracy']<=.65
    result={'schema':'context-memory-graph-gate-124-v1','status':'completed','contract':{'context_changes_action_mapping':True,'same_observation_requires_different_action_by_context':True,'context_cue_only_initial':True,'development_selection_only':True,'untouched_final_seed':FINAL_SEED,'train_episodes':train_count,'development_episodes':dev_count,'final_episodes_per_condition':final_count,'steps':STEPS,'leak_candidates':LEAKS,'frozen_series123_runner_sha256':BASE_SHA,'not_biological_validation':True,'physical_flygym_port_authorized_only_if_graph_go':True},'development':dev_table,'models':rows,'gates':{'context_necessity_pass':context_necessary,'graph_advantage_go':graph_go,'decision':'GO_TO_NEW_FLYGYM_PORT' if graph_go else 'NO_GO_KEEP_PHYSICAL_PORT_BLOCKED'},'interpretation':{'new_physical_result':False,'living_neuron_claim':False,'whole_brain_claim':False}}
    (folder/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8'); lines=['SERIES124 — CONTEXT MEMORY GRAPH GATE','',f"Context necessity: {context_necessary}",f"Graph advantage: {graph_go}",f"Decision: {result['gates']['decision']}",'']
    for r in rows:
        m=r['conditions']['clean']; lines.append(f"{r['name']}: RMSE={m['rmse']:.5f}, success={m['success_rate']*100:.2f}%, context={m['late_context_accuracy']*100:.2f}%")
    lines+=['','Series124 is synthetic; earlier official FlyGym evidence is separate.'];(folder/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');progress(5,5,'Готово');return folder

def gui():
    import tkinter as tk
    from tkinter import messagebox,ttk
    root=tk.Tk();root.title('Series124: context memory graph gate');root.geometry('780x440+90+60');root.attributes('-topmost',True);tr=tk.IntVar(value=80);dv=tk.IntVar(value=20);fn=tk.IntVar(value=30);status=tk.StringVar(value='Готово');bar=tk.DoubleVar(value=0)
    tk.Label(root,text='Context-necessary memory gate',font=('Arial',15,'bold'),pady=15).pack();tk.Label(root,text='Одинаковое наблюдение требует разных действий в двух контекстах.\nDevelopment выбирает leak; final seed остаётся untouched.',justify='center').pack();form=tk.Frame(root);form.pack(pady=12)
    for i,(label,var) in enumerate([('Train episodes:',tr),('Development episodes:',dv),('Final/condition:',fn)]):tk.Label(form,text=label).grid(row=i,column=0,padx=6,pady=4);tk.Spinbox(form,from_=10,to=300,increment=10,textvariable=var,width=8).grid(row=i,column=1)
    tk.Label(root,textvariable=status).pack();ttk.Progressbar(root,variable=bar,maximum=5,length=570).pack(pady=8);button=tk.Button(root,text='Запустить Series124',padx=20,pady=9);button.pack(pady=10)
    def start():
        button.config(state='disabled');a,b,c=int(tr.get()),int(dv.get()),int(fn.get())
        def work():
            try:
                out=run(a,b,c,OUTPUT_ROOT,lambda d,t,s:root.after(0,lambda:(bar.set(d),status.set(s))))
                def done():
                    button.config(state='normal');status.set('Готово');
                    if os.name=='nt':os.startfile(str(out.resolve()))
                    messagebox.showinfo('Series124',f'Результат:\n{out.resolve()}',parent=root)
                root.after(0,done)
            except Exception as e:
                p=OUTPUT_ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-124.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(type(e).__name__+': '+str(e)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');root.after(0,lambda:(button.config(state='normal'),status.set('Ошибка'),messagebox.showerror('Series124',f'{e}\n\n{p.resolve()}',parent=root)))
        threading.Thread(target=work,daemon=True).start()
    button.config(command=start);root.mainloop()
def main():
    p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--train-episodes',type=int,default=80);p.add_argument('--dev-episodes',type=int,default=20);p.add_argument('--final-episodes',type=int,default=30);p.add_argument('--output-root',type=Path,default=OUTPUT_ROOT);a=p.parse_args();print(run(a.train_episodes,a.dev_episodes,a.final_episodes,a.output_root)) if not a.gui else gui()
if __name__=='__main__':main()
