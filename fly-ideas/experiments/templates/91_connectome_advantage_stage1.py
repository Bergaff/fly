#!/usr/bin/env python3
"""Stage91: bounded 96-unit topology benchmark before any biological mapping."""
from __future__ import annotations
import argparse,csv,hashlib,json,multiprocessing,os,sys,traceback,uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from pathlib import Path
import numpy as np

ROOT=Path('workspace/runs/ideas/i-connectome-advantage/stage-1-96-unit-benchmark')
ACTIONS=('foreleg_rubbing','head_directed_grooming','reach_withdraw')

def serial(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf-8')
def file_sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def make_data(seed,count,ood):
    rng=np.random.default_rng(seed);steps=8;channels=6
    basis=np.array([
        [[np.sin(2*np.pi*t),-np.sin(2*np.pi*t),.15,0,0,0] for t in np.linspace(0,1,steps,endpoint=False)],
        [[.55+.25*np.sin(2*np.pi*t),.55-.25*np.sin(2*np.pi*t),.35+.12*np.cos(2*np.pi*t),.08*np.sin(2*np.pi*t),0,0] for t in np.linspace(0,1,steps,endpoint=False)],
        [[.35*np.sin(np.pi*t),.35*np.sin(np.pi*t),0,0,np.sin(np.pi*t),.12*np.sin(np.pi*t)] for t in np.linspace(0,1,steps,endpoint=False)],
    ],dtype=np.float64)
    xs=[];ys=[];labels=[]
    for _ in range(count):
        action=int(rng.integers(0,3));amplitude=float(rng.uniform(.55,1.2));shift=int(rng.integers(-1,2) if ood else 0)
        trajectory=np.roll(basis[action],shift,axis=0)*amplitude
        view_scale=.34 if ood else .10;mix=np.eye(channels)+rng.normal(0,view_scale,(channels,channels))/np.sqrt(channels)
        observed=trajectory@mix+rng.normal(0,.035 if ood else .02,trajectory.shape)
        if ood and rng.random()<.45:
            observed[int(rng.integers(0,steps)),int(rng.integers(0,channels))]=0
        target=np.concatenate((np.eye(3)[action],trajectory.mean(0)))
        xs.append(observed.reshape(-1));ys.append(target);labels.append(action)
    return np.asarray(xs),np.asarray(ys),np.asarray(labels)

def masks(seed,input_dim,hidden):
    structured=np.zeros((input_dim,hidden),dtype=np.float64);steps=input_dim//6
    for unit in range(hidden):
        channel=unit%6
        for time in range(steps):
            structured[time*6+channel,unit]=1
            structured[time*6+(channel+1)%6,unit]=1
    rng=np.random.default_rng(seed);shuffled=structured.reshape(-1)[rng.permutation(structured.size)].reshape(structured.shape)
    return {'structured96':structured,'shuffled96':shuffled,'dense96':np.ones_like(structured)}

def train_model(x,y,mask,seed,epochs):
    rng=np.random.default_rng(seed);n,d=x.shape;h=mask.shape[1];o=y.shape[1];fan=np.maximum(1,mask.sum(0))
    w=rng.normal(0,1,(d,h))/np.sqrt(fan)[None,:]*mask;b=np.zeros(h);v=rng.normal(0,.08,(h,o));c=np.zeros(o)
    params=[w,b,v,c];mom=[np.zeros_like(q) for q in params];vel=[np.zeros_like(q) for q in params];step=0
    for epoch in range(epochs):
        for start in rng.permutation(np.arange(0,n,64)):
            ids=np.arange(start,min(start+64,n));xb=x[ids];yb=y[ids];hidden=np.tanh(xb@w+b);pred=hidden@v+c;delta=2*(pred-yb)/(len(ids)*o)
            grads=[xb.T@((delta@v.T)*(1-hidden**2))*mask,((delta@v.T)*(1-hidden**2)).sum(0),hidden.T@delta,delta.sum(0)]
            step+=1
            for i,(parameter,grad) in enumerate(zip(params,grads)):
                mom[i]=.9*mom[i]+.1*grad;vel[i]=.999*vel[i]+.001*grad*grad
                parameter-=.006*(mom[i]/(1-.9**step))/(np.sqrt(vel[i]/(1-.999**step))+1e-8)
        w*=mask
    return w,b,v,c

def metrics(model,x,y,labels,lesion):
    w,b,v,c=model;hidden=np.tanh(x@w+b);pred=hidden@v+c
    if lesion is not None: hidden[:,lesion]=0;pred=hidden@v+c
    return {'accuracy':float(np.mean(np.argmax(pred[:,:3],1)==labels)),'trajectory_rmse':float(np.sqrt(np.mean((pred[:,3:]-y[:,3:])**2)))}

def one_seed(args):
    seed,fixture=args;train_n,test_n,epochs=(96,60,12) if fixture else(720,360,180)
    x_train,y_train,l_train=make_data(91000+seed,train_n,False);x_test,y_test,l_test=make_data(92000+seed,test_n,True)
    mean=x_train.mean(0);std=np.maximum(x_train.std(0),1e-6);x_train=(x_train-mean)/std;x_test=(x_test-mean)/std
    topology=masks(93000+seed,x_train.shape[1],96);lesion=np.random.default_rng(94000+seed).choice(96,10,replace=False);rows=[]
    for index,(name,mask) in enumerate(topology.items()):
        model=train_model(x_train,y_train,mask,95000+seed*10+index,epochs);normal=metrics(model,x_test,y_test,l_test,None);damaged=metrics(model,x_test,y_test,l_test,lesion)
        rows.append({'seed':seed,'model':name,'units':96,'active_input_weights':int(mask.sum()),'trainable_parameters':int(mask.sum()+96*9+96+9),'test_examples':test_n,**normal,'lesion_fraction':10/96,'lesion_accuracy':damaged['accuracy'],'lesion_trajectory_rmse':damaged['trajectory_rmse']})
    return rows

def summarize(rows,seeds):
    by={name:[row for row in rows if row['model']==name] for name in ('structured96','shuffled96','dense96')}
    aggregate={name:{key:float(np.mean([row[key] for row in group])) for key in ('accuracy','trajectory_rmse','lesion_accuracy','lesion_trajectory_rmse')}|{'trainable_parameters':group[0]['trainable_parameters']} for name,group in by.items()}
    paired=[next(row for row in by['structured96'] if row['seed']==seed)['accuracy']>next(row for row in by['shuffled96'] if row['seed']==seed)['accuracy'] for seed in seeds]
    primary={'accuracy_margin_required':.02,'rmse_ratio_required':.98,'paired_seed_wins_required':int(np.ceil(len(seeds)*2/3)),'paired_seed_wins':sum(paired)}
    primary['passed']=aggregate['structured96']['accuracy']>=aggregate['shuffled96']['accuracy']+.02 and aggregate['structured96']['trajectory_rmse']<=aggregate['shuffled96']['trajectory_rmse']*.98 and sum(paired)>=primary['paired_seed_wins_required']
    return aggregate,primary

def worker_choice(value):
    raw=str(value).strip().lower()
    if raw=='max':return 'max',max(1,os.cpu_count() or 1)
    number=int(raw)
    if number not in (2,4,6):raise ValueError('Workers должны быть 2, 4, 6 или max.')
    return str(number),number

def run(workers='6',output_root=ROOT,fixture=False):
    label,count=worker_choice(workers);seeds=list(range(2 if fixture else 12));root=Path(output_root);root.mkdir(parents=True,exist_ok=True)
    folder=root/('fixture' if fixture else 'connectome_advantage_stage1_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(exist_ok=fixture)
    incomplete=folder/'result_incomplete';incomplete.mkdir(exist_ok=True)
    protocol={'schema':'connectome-advantage-stage1-v1','scientific_result':False if fixture else None,'stage':'96 engineered units; no biological IDs','actions':list(ACTIONS),'models':['structured96','shuffled96','dense96'],'seeds':seeds,'workers':count,'worker_choice':label,'same_examples':True,'same_units':96,'structured_vs_shuffled_same_parameter_count':True,'dense96_is_unit_matched_not_parameter_matched':True,'test_shift':'unseen view mixing, time shift, noise and partial occlusion','delay_s':.5,'latent_state_held_without_input_during_delay':True,'lesion_units':10,'primary':'structured96 accuracy >= shuffled96 +0.02, RMSE <=0.98*shuffled96, paired accuracy wins >=2/3 seeds','script_sha256':file_sha(__file__)};save(incomplete/'protocol.json',protocol)
    print(f'Этап1: {len(seeds)} seeds, workers={count}. Это artificial96 benchmark, не реальные нейроны.',flush=True);rows=[]
    with ProcessPoolExecutor(max_workers=min(count,len(seeds)),mp_context=multiprocessing.get_context('spawn')) as pool:
        for done,batch in enumerate(pool.map(one_seed,[(seed,fixture) for seed in seeds]),1):rows.extend(batch);print(f'  seeds {done}/{len(seeds)}',flush=True)
    aggregate,primary=summarize(rows,seeds);summary={'schema':'connectome-advantage-stage1-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'aggregate':aggregate,'primary':primary,'limitations':['The 96 units are engineered software units, not fly neurons.','Structured mask is a preregistered computational prior, not a connectome.','Dense96 has the same unit count but more parameters; shuffled96 is the parameter-matched primary control.','Synthetic actions and view shifts do not establish an advantage in animals.','A pass only authorizes frozen replication; it does not authorize FlyWire mapping.']};save(incomplete/'summary.json',summary)
    with (incomplete/'seed_metrics.csv').open('w',newline='',encoding='utf-8-sig') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    text='ЭТАП 1: 96-UNIT CONNECTOME ADVANTAGE BENCHMARK\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'\n\nЭто сравнение искусственных96-unit архитектур. Реальные нейроны мухи не использованы.\nСледующий допустимый шаг: независимая frozen replication; biological mapping пока запрещён.\n'
    (incomplete/'ИТОГ.txt').write_text(text,encoding='utf-8-sig');save(incomplete/'complete.json',{'files':{p.name:file_sha(p) for p in incomplete.iterdir() if p.is_file() and p.name!='complete.json'}});incomplete.rename(folder/'result')
    print('Готово:',folder/'result',flush=True);return folder/'result'

def choose():
    import tkinter as tk
    from tkinter import messagebox
    root=tk.Tk();root.title('Этап1: преимущество 96-unit архитектуры');root.geometry('700x360+180+120');root.attributes('-topmost',True);choice=tk.StringVar(value='6');started={'value':False}
    tk.Label(root,text='Этап1: честное сравнение artificial96-unit архитектур\nstructured96 против parameter-matched shuffled96 и unit-matched dense96.\nЭто короткий synthetic benchmark, не FlyWire и не биологический результат.',font=('Arial',11),padx=20,pady=20).pack()
    tk.Label(root,text='Workers:',font=('Arial',10,'bold')).pack()
    for text,value in [('2','2'),('4','4'),('6','6'),('Максимум','max')]:tk.Radiobutton(root,text=text,variable=choice,value=value).pack(anchor='center')
    tk.Button(root,text='Запустить этап1',command=lambda:(started.update(value=True),root.quit()),padx=22,pady=9).pack(pady=18);root.mainloop()
    if not started['value']:root.destroy();return
    root.withdraw();result=run(choice.get());
    if os.name=='nt':os.startfile(str(result));os.startfile(str(result/'ИТОГ.txt'))
    messagebox.showinfo('Этап1 завершён','Результат и копируемый ИТОГ.txt открыты.\n\n'+str(result.resolve()),parent=root);root.destroy()

def failure_report(exc):
    path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-ЭТАП1.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('ЭТАП1: ОТЧЁТ ОБ ОШИБКЕ\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig')
    if os.name=='nt':
        try:os.startfile(str(path))
        except OSError:pass
    try:
        import tkinter as tk
        from tkinter import messagebox
        root=tk.Tk();root.withdraw();root.attributes('-topmost',True);messagebox.showerror('Этап1 остановлен','Ошибка записана в копируемый файл:\n\n'+str(path.resolve()),parent=root);root.destroy()
    except Exception:pass
    return path

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--choose',action='store_true');parser.add_argument('--workers',default='6');parser.add_argument('--output-root',default=str(ROOT));parser.add_argument('--fixture',action='store_true');args=parser.parse_args()
    if args.choose:choose()
    else:run(args.workers,args.output_root,args.fixture)
if __name__=='__main__':
    try:main()
    except Exception as exc:
        report=failure_report(exc);print(f'ОШИБКА: {exc}\nОтчёт: {report.resolve()}',file=sys.stderr);sys.exit(1)
