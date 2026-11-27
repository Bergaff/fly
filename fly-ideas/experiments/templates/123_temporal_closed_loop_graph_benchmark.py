#!/usr/bin/env python3
"""Series123: synthetic temporal closed-loop benchmark for graph and non-graph controllers.

Engineering stress test only: no living-neuron, biological, whole-brain, or intelligence claim.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,threading,time,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent; REPORTS=HERE.parent/'reports'
MATRIX=REPORTS/'biological-digital-pipeline-116a-61x61.csv'; PATHS=REPORTS/'biological-digital-pipeline-116b-61x8.csv'; PROTOS=REPORTS/'adaptive-three-direction-118-action-prototypes.json'
MATRIX_SHA='03157b503d0271cb0991db524d45220bb8f49ce62e3ba171dc997ed7f3816150'; PATHS_SHA='4186bb6fdbe0a0e81f8626469027976ade1d416ff0549af94b85fb1b07aa3ca1'; PROTOS_SHA='28edd80b81111d47708f163aaf9b250f7ad330a87d6c9dc5ee70e7895843ca04'
OUTPUT_ROOT=Path('workspace/runs/ideas/i-observational/temporal-closed-loop-123'); TRAIN_SEED=123_000_001; TEST_SEED=123_000_002; STEPS=120; SENSOR_DELAY=2; MOTOR_DELAY=2

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load_core():
    if (sha(MATRIX),sha(PATHS),sha(PROTOS))!=(MATRIX_SHA,PATHS_SHA,PROTOS_SHA): raise ValueError('Frozen input SHA mismatch.')
    mr=list(csv.reader(MATRIX.open(encoding='utf8'))); pr=list(csv.reader(PATHS.open(encoding='utf8'))); proto=json.loads(PROTOS.read_text(encoding='utf8'))
    g=np.asarray([[float(x) for x in r[1:]] for r in mr[1:]]); paths=np.asarray([[float(x) for x in r[1:]] for r in pr[1:]]); p=np.asarray(proto['prototypes'])
    g=np.log1p(g); g=g/np.maximum(g.sum(1,keepdims=True),1e-12); paths=paths/np.maximum(paths.sum(1,keepdims=True),1e-12)
    motor=p@paths; motor=motor-motor.mean(0,keepdims=True); motor=.48*motor/max(np.max(np.abs(motor)),1e-12)
    rng=np.random.default_rng(123_000_000); context=rng.normal(0,1,(2,61)); context/=np.linalg.norm(context,axis=1,keepdims=True)
    phase=rng.normal(0,1,(2,61)); phase/=np.linalg.norm(phase,axis=1,keepdims=True)
    mask=g>0; random=rng.normal(0,1,g.shape)*mask; random=random/np.maximum(np.sum(np.abs(random),1,keepdims=True),1e-12)
    return g,paths,p,motor,context,phase,random
CORE=load_core(); NAMES=['memoryless_ridge','history4_ridge','random_reservoir61','graph_reservoir61']

def blueprint(seed,episodes,stress='clean'):
    g,paths,p,motor,context_vec,phase_vec,_=CORE; out=[]
    for e in range(episodes):
        rng=np.random.default_rng(seed+e); context=int(rng.integers(0,2)); modes=[]; phases=[]; switches=[]; last=-1
        while len(modes)<STEPS:
            mode=int(rng.integers(0,3));
            if mode==last: mode=(mode+1+int(rng.integers(0,2)))%3
            length=int(rng.integers(16,29)); switches.append(len(modes)); modes.extend([mode]*length); phases.extend(np.arange(length)/max(length-1,1)); last=mode
        modes=np.asarray(modes[:STEPS]); phases=np.asarray(phases[:STEPS]); switches=[x for x in switches if 0<x<STEPS]
        target=np.empty((STEPS,8)); obs=np.empty((STEPS,61)); cue=set(switches+[0]); observed_mask=(rng.random(61)>.35).astype(float)
        for t,(mode,ph) in enumerate(zip(modes,phases)):
            wave=np.sin(2*np.pi*ph); target[t]=np.clip(motor[mode]*(.72+.28*wave)+(.035 if context else -.035)*np.cos(np.arange(8)+2*np.pi*ph),-.62,.62)
            strong=1.0 if any(0<=t-s<3 for s in cue) else 0.0
            obs[t]=strong*p[mode]+.10*(phase_vec[0]*np.sin(2*np.pi*ph)+phase_vec[1]*np.cos(2*np.pi*ph))
            if t<3: obs[t]+=.22*context_vec[context]
        noise=.018 if stress!='noise' else .06; obs=np.clip((obs+rng.normal(0,noise,obs.shape))*observed_mask,0,None)
        if stress=='cue_loss': obs[:3]=0
        if stress=='partial': obs*=((rng.random(obs.shape)>.25).astype(float))
        delay=SENSOR_DELAY+(2 if stress=='extra_delay' else 0); delivered=np.zeros_like(obs); delivered[delay:]=obs[:-delay]
        disturbance=rng.normal(0,.006,(STEPS,8)); out.append({'context':context,'modes':modes,'switches':switches,'target':target,'obs':delivered,'disturbance':disturbance,'motor_delay':MOTOR_DELAY+(2 if stress=='extra_delay' else 0)})
    return out

def dynamics(body,command,context,disturbance):
    inertia=.86 if context else .76; gain=1-inertia; return inertia*body+gain*np.tanh(command)+disturbance

def teacher_rollout(ep):
    body=np.zeros(8); queue=[np.zeros(8) for _ in range(ep['motor_delay'])]; bodies=[]; commands=[]
    inertia=.86 if ep['context'] else .76; gain=1-inertia
    for t in range(STEPS):
        future=ep['target'][min(STEPS-1,t+ep['motor_delay'])]; command=np.arctanh(np.clip((future-inertia*body)/gain,-.95,.95)); command=np.clip(command,-2,2)
        queue.append(command); applied=queue.pop(0); body=dynamics(body,applied,ep['context'],ep['disturbance'][t]); bodies.append(body.copy()); commands.append(command)
    return np.asarray(bodies),np.asarray(commands)

def reservoir_step(h,obs,body,matrix,paths): return np.tanh(.78*h+.18*(matrix.T@h)+6.0*obs+.16*(paths@body))
def fit_ridge(x,y,alpha=1e-3):
    z=np.column_stack([x,np.ones(len(x))]); return np.linalg.solve(z.T@z+alpha*np.eye(z.shape[1]),z.T@y)
def predict_ridge(x,w): return np.append(x,1)@w

def features_for_episode(ep,bodies,name):
    _,paths,_,_,_,_,random=CORE; g=CORE[0]; h=np.zeros(61); history=[np.zeros(69) for _ in range(3)]; features=[]
    for t in range(STEPS):
        raw=np.r_[ep['obs'][t],bodies[t-1] if t else np.zeros(8)]
        if name=='memoryless_ridge': feature=raw
        elif name=='history4_ridge': feature=np.concatenate(history+[raw]); history=(history+[raw])[1:]
        else:
            h=reservoir_step(h,ep['obs'][t],bodies[t-1] if t else np.zeros(8),g if name=='graph_reservoir61' else random,paths); feature=np.r_[h,bodies[t-1] if t else np.zeros(8)]
        features.append(feature)
    return np.asarray(features)

def train_models(episodes):
    collected={n:[] for n in NAMES}; targets=[]
    for ep in episodes:
        bodies,commands=teacher_rollout(ep); targets.append(commands)
        for n in NAMES: collected[n].append(features_for_episode(ep,bodies,n))
    y=np.concatenate(targets); return {n:fit_ridge(np.concatenate(collected[n]),y) for n in NAMES}

def evaluate_one(ep,name,weights):
    _,paths,_,_,_,_,random=CORE; g=CORE[0]; body=np.zeros(8); queue=[np.zeros(8) for _ in range(ep['motor_delay'])]; h=np.zeros(61); history=[np.zeros(69) for _ in range(3)]; bodies=[]; start=time.perf_counter()
    for t in range(STEPS):
        raw=np.r_[ep['obs'][t],body]
        if name=='memoryless_ridge': feature=raw
        elif name=='history4_ridge': feature=np.concatenate(history+[raw]); history=(history+[raw])[1:]
        else: h=reservoir_step(h,ep['obs'][t],body,g if name=='graph_reservoir61' else random,paths); feature=np.r_[h,body]
        command=np.clip(predict_ridge(feature,weights),-2,2); queue.append(command); applied=queue.pop(0); body=dynamics(body,applied,ep['context'],ep['disturbance'][t]); bodies.append(body.copy())
    elapsed=time.perf_counter()-start; bodies=np.asarray(bodies); frame=np.sqrt(np.mean((bodies-ep['target'])**2,axis=1)); switch_windows=[frame[s:min(STEPS,s+8)].mean() for s in ep['switches']]
    return {'rmse':float(np.sqrt(np.mean((bodies-ep['target'])**2))),'success_rate':float(np.mean(frame<.20)),'switch_recovery_error':float(np.mean(switch_windows)) if switch_windows else None,'seconds_per_step':elapsed/STEPS}

def evaluate_oracle(ep):
    start=time.perf_counter(); bodies,_=teacher_rollout(ep); elapsed=time.perf_counter()-start; frame=np.sqrt(np.mean((bodies-ep['target'])**2,axis=1)); windows=[frame[s:min(STEPS,s+8)].mean() for s in ep['switches']]
    return {'rmse':float(np.sqrt(np.mean((bodies-ep['target'])**2))),'success_rate':float(np.mean(frame<.20)),'switch_recovery_error':float(np.mean(windows)) if windows else None,'seconds_per_step':elapsed/STEPS}
def aggregate(episodes,name,w=None):
    rows=[evaluate_oracle(ep) if name=='privileged_oracle' else evaluate_one(ep,name,w) for ep in episodes]; return {k:float(np.mean([r[k] for r in rows if r[k] is not None])) for k in rows[0]}
def parameter_count(name): return {'memoryless_ridge':70*8,'history4_ridge':277*8,'random_reservoir61':70*8+2489,'graph_reservoir61':70*8+2489}[name]

def run(train_episodes,test_episodes,output_root,progress=lambda *_:None):
    folder=output_root/('temporal_closed_loop_123_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]); folder.mkdir(parents=True)
    progress(1,4,'Генерирую train'); train=blueprint(TRAIN_SEED,train_episodes); models=train_models(train); progress(2,4,'Frozen test')
    conditions=['clean','noise','partial','cue_loss','extra_delay']; results=[]
    tests={c:blueprint(TEST_SEED,test_episodes,c) for c in conditions}
    for name,w in models.items():
        row={'name':name,'parameter_or_scalar_count':parameter_count(name),'readout_trainable_count':int(w.size),'conditions':{c:aggregate(tests[c],name,w) for c in conditions}}; results.append(row)
    results.append({'name':'privileged_oracle','parameter_or_scalar_count':0,'readout_trainable_count':0,'uses_hidden_future_target_and_context':True,'conditions':{c:aggregate(tests[c],'privileged_oracle') for c in conditions}})
    progress(3,4,'Сохраняю'); result={'schema':'temporal-closed-loop-graph-benchmark-123-v1','status':'completed','contract':{'synthetic_engineering_task':True,'train_episodes':train_episodes,'test_episodes_per_condition':test_episodes,'steps_per_episode':STEPS,'sensor_delay':SENSOR_DELAY,'motor_delay':MOTOR_DELAY,'contexts':2,'action_modes':3,'action_switching':True,'partial_observability':True,'body_feedback':True,'closed_loop_dynamics':True,'frozen_input_shas':{'matrix':MATRIX_SHA,'paths':PATHS_SHA,'prototypes':PROTOS_SHA},'train_seed':TRAIN_SEED,'test_seed':TEST_SEED,'not_biological_validation':True,'not_whole_brain_model':True,'not_general_intelligence_benchmark':True},'models':results,'interpretation':{'graph_advantage_claim_requires_graph_to_beat_history_and_random_reservoir':True,'controller_is_synthetic':True,'living_neuron_claim':False}}
    (folder/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['SERIES123 — SYNTHETIC TEMPORAL CLOSED LOOP','',f'Train episodes: {train_episodes} | Test/condition: {test_episodes} | Steps: {STEPS}','']
    for r in results:
        c=r['conditions']['clean']; lines.append(f"{r['name']}: RMSE={c['rmse']:.5f}, success={c['success_rate']*100:.2f}%, switch={c['switch_recovery_error']:.5f}, us/step={c['seconds_per_step']*1e6:.3f}")
    lines+=['','Synthetic engineering benchmark only; no biology, whole-brain, or general-intelligence claim.']; (folder/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig'); progress(4,4,'Готово'); return folder

def gui():
    import tkinter as tk
    from tkinter import messagebox,ttk
    root=tk.Tk(); root.title('Series123: temporal closed loop'); root.geometry('760x420+90+60'); root.attributes('-topmost',True); train=tk.IntVar(value=80); test=tk.IntVar(value=30); status=tk.StringVar(value='Готово'); bar=tk.DoubleVar(value=0)
    tk.Label(root,text='Временной closed-loop benchmark',font=('Arial',15,'bold'),pady=15).pack(); tk.Label(root,text='Состояние · последовательности · body feedback · задержки · контекст\nпереключение · partial observability · нелинейная динамика',justify='center').pack(); form=tk.Frame(root);form.pack(pady=15)
    tk.Label(form,text='Train episodes:').grid(row=0,column=0,padx=6,pady=5);tk.Spinbox(form,from_=20,to=500,increment=20,textvariable=train,width=8).grid(row=0,column=1);tk.Label(form,text='Test/condition:').grid(row=1,column=0,padx=6,pady=5);tk.Spinbox(form,from_=10,to=200,increment=10,textvariable=test,width=8).grid(row=1,column=1)
    tk.Label(root,textvariable=status).pack();ttk.Progressbar(root,variable=bar,maximum=4,length=570).pack(pady=8);button=tk.Button(root,text='Запустить Series123',padx=20,pady=9);button.pack(pady=10)
    def start():
        button.config(state='disabled');a,b=int(train.get()),int(test.get())
        def work():
            try:
                out=run(a,b,OUTPUT_ROOT,lambda d,t,s:root.after(0,lambda:(bar.set(d),status.set(s))))
                def done():
                    button.config(state='normal');status.set('Готово');
                    if os.name=='nt':os.startfile(str(out.resolve()))
                    messagebox.showinfo('Series123',f'Результат:\n{out.resolve()}',parent=root)
                root.after(0,done)
            except Exception as e:
                p=OUTPUT_ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-123.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(type(e).__name__+': '+str(e)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');root.after(0,lambda:(button.config(state='normal'),status.set('Ошибка'),messagebox.showerror('Series123',f'{e}\n\n{p.resolve()}',parent=root)))
        threading.Thread(target=work,daemon=True).start()
    button.config(command=start);root.mainloop()
def main():
    p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--train-episodes',type=int,default=80);p.add_argument('--test-episodes',type=int,default=30);p.add_argument('--output-root',type=Path,default=OUTPUT_ROOT);a=p.parse_args();print(run(a.train_episodes,a.test_episodes,a.output_root)) if not a.gui else gui()
if __name__=='__main__':main()
