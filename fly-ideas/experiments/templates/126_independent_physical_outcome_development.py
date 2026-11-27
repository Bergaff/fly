#!/usr/bin/env python3
"""Series126: offline development against independent official-FlyGym physical outcomes.

Historical Series106/109/112 outcomes were produced before this Graph Core benchmark and
are not generated from the61x61 graph. Series112 is a historical audit, not a new untouched final.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,os,threading,time,traceback,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;REPORTS=HERE.parent/'reports';OUTPUT_ROOT=Path('workspace/runs/ideas/i-observational/independent-physical-outcome-126')
FILES={'train106':('frozen-action-aware-physical-validation-106-user-result.json','1eadcbcfea31c973f9993da16be7cd0b01998d2f4c6c7aa27c54b4c08da00be9'),'development109':('frozen-nuisance-robustness-ablation-109-user-result.json','e7cfc5068fb53ae69782d3d31ce03e16605c044699a3a41590193a5276c99f03'),'historical_audit112':('frozen-operational-router-physical-112-user-result.json','da0b244c4d1dba53e81ebc95a6a1496b2517d2e3da5969be305a75af5a5c3b01')}
MATRIX=REPORTS/'biological-digital-pipeline-116a-61x61.csv';PROTOS=REPORTS/'adaptive-three-direction-118-action-prototypes.json';MATRIX_SHA='03157b503d0271cb0991db524d45220bb8f49ce62e3ba171dc997ed7f3816150';PROTOS_SHA='28edd80b81111d47708f163aaf9b250f7ad330a87d6c9dc5ee70e7895843ca04';ACTIONS=['foreleg_rubbing','head_directed_grooming','reach_withdraw'];DOMAINS=['standard','dim','bright','low_contrast','sensor_noise','horizontal_shift','frame_dropout'];TARGETS=['tracking_rmse_rad','truth_rmse_rad','contact_frame_fraction','max_actuator_force_norm','energy_abs_work'];SCALE_FLOORS=np.asarray([.01,.02,.05,.5,2.0]);ALPHAS=[1e-4,1e-3,1e-2,.1,1,10]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load_core():
    if sha(MATRIX)!=MATRIX_SHA or sha(PROTOS)!=PROTOS_SHA:raise ValueError('Core SHA mismatch.')
    rows=list(csv.reader(MATRIX.open(encoding='utf8')));g=np.asarray([[float(x) for x in r[1:]] for r in rows[1:]]);g=np.log1p(g);g/=np.maximum(g.sum(1,keepdims=True),1e-15);p=np.asarray(json.loads(PROTOS.read_text(encoding='utf8'))['prototypes']);return g,p
G,P=load_core()
def graph_controls():
    rng=np.random.default_rng(126_000_001);rewired=np.zeros_like(G)
    for i in range(61):
        vals=G[i,G[i]>0];rewired[i,rng.choice(61,len(vals),replace=False)]=vals
    rewired/=np.maximum(rewired.sum(1,keepdims=True),1e-15);random=np.zeros_like(G);mask=G>0;random[mask]=rng.uniform(.01,1,np.count_nonzero(mask));random/=np.maximum(random.sum(1,keepdims=True),1e-15);return rewired,random
REWIRED,RANDOM=graph_controls()
def propagate(x,matrix):
    z=x.copy();total=x.copy()
    for h in range(1,5):z=z@matrix;total+=.65**h*z
    return total/np.maximum(total.sum(1,keepdims=True),1e-15)
def load_dataset(role):
    filename,expected=FILES[role];path=REPORTS/filename
    if sha(path)!=expected:raise ValueError(role+' result SHA mismatch.')
    d=json.loads(path.read_text(encoding='utf8'));motions={m['id']:m for m in d['protocol']['motions']};rows=[]
    key='candidate' if role!='development109' else 'repaired_candidate'
    for case in d['tests']:
        m=motions[case['id']];control=case['controls'][key];rows.append({'id':case['id'],'action':case['action'],'domain':case.get('domain','standard'),'amplitude':float(m['amplitude']),'speed':float(m['speed']),'target':[float(control[k]) for k in TARGETS]})
    return rows
def arrays(rows,kind):
    meta=[];stim=[];targets=[]
    for r in rows:
        meta.append([float(r['action']==a) for a in ACTIONS]+[r['amplitude'],r['speed']]+[float(r['domain']==d) for d in DOMAINS]);stim.append(P[ACTIONS.index(r['action'])]*r['amplitude']);targets.append(r['target'])
    meta=np.asarray(meta);stim=np.asarray(stim);stim/=np.maximum(stim.sum(1,keepdims=True),1e-15)
    if kind=='metadata':x=meta
    elif kind=='raw_types':x=np.c_[meta,stim]
    elif kind=='graph_multihop':x=np.c_[meta,propagate(stim,G)]
    elif kind=='rewired_graph':x=np.c_[meta,propagate(stim,REWIRED)]
    elif kind=='matched_random_graph':x=np.c_[meta,propagate(stim,RANDOM)]
    elif kind=='random_feature_mlp':x=np.c_[meta,stim]
    else:raise KeyError(kind)
    return x,np.asarray(targets)
def fit_scaler(x):return x.mean(0),np.maximum(x.std(0),1e-8)
def ridge_fit(x,y,alpha):
    z=np.column_stack([x,np.ones(len(x))]);return np.linalg.solve(z.T@z+alpha*np.eye(z.shape[1]),z.T@y)
def ridge_predict(x,w):return np.column_stack([x,np.ones(len(x))])@w
def fit_random_mlp(x,y,alpha,seed=126_000_002):
    rng=np.random.default_rng(seed);mean,std=fit_scaler(x);xn=(x-mean)/std;w=rng.normal(0,np.sqrt(2/x.shape[1]),(x.shape[1],32));b=rng.normal(0,.01,32);h=np.maximum(xn@w+b,0);out=ridge_fit(h,y,alpha);return mean,std,w,b,out
def predict_random_mlp(x,m):mean,std,w,b,out=m;return ridge_predict(np.maximum((x-mean)/std@w+b,0),out)
def normalized_rmse(pred,y,scale):return float(np.sqrt(np.mean(((pred-y)/scale)**2)))
def fit_model(kind,train_rows,alpha):
    x,y=arrays(train_rows,kind)
    if kind=='random_feature_mlp':return fit_random_mlp(x,y,alpha)
    mean,std=fit_scaler(x);return mean,std,ridge_fit((x-mean)/std,y,alpha)
def predict_model(kind,rows,model):
    x,y=arrays(rows,kind)
    if kind=='random_feature_mlp':return predict_random_mlp(x,model),y
    mean,std,w=model;return ridge_predict((x-mean)/std,w),y
def metrics(pred,y,scale):
    return {'normalized_rmse':normalized_rmse(pred,y,scale),'per_target_rmse':{k:float(np.sqrt(np.mean((pred[:,i]-y[:,i])**2))) for i,k in enumerate(TARGETS)},'per_target_mae':{k:float(np.mean(np.abs(pred[:,i]-y[:,i]))) for i,k in enumerate(TARGETS)}}
def run(output_root,progress=lambda *_:None):
    folder=output_root/('independent_physical_outcome_126_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True)
    series106=load_dataset('train106');series109=load_dataset('development109');audit=load_dataset('historical_audit112')
    # Series109 is partitioned before fitting: two actions/domain augment fit, the third is development-only.
    development_fit=[r for r in series109 if r['action']!='reach_withdraw'];development_select=[r for r in series109 if r['action']=='reach_withdraw'];train=series106+development_fit
    _,ytrain=arrays(train,'metadata');scale=np.maximum(ytrain.std(0),SCALE_FLOORS);kinds=['metadata','raw_types','graph_multihop','rewired_graph','matched_random_graph','random_feature_mlp'];development={};progress(1,4,'Development selection')
    for kind in kinds:
        candidates=[]
        for alpha in ALPHAS:
            model=fit_model(kind,train,alpha);pred,y=predict_model(kind,development_select,model);candidates.append({'alpha':alpha,**metrics(pred,y,scale)})
        best=min(candidates,key=lambda r:r['normalized_rmse']);development[kind]={'selected_alpha':best['alpha'],'candidates':candidates}
    progress(2,4,'Historical audit');combined=series106+series109;rows=[]
    constant=np.repeat(np.asarray([r['target'] for r in combined]).mean(0,keepdims=True),len(audit),axis=0);ya=np.asarray([r['target'] for r in audit]);rows.append({'name':'constant_mean','parameter_count':5,'development_selected':False,'historical_audit':metrics(constant,ya,scale)})
    for kind in kinds:
        alpha=development[kind]['selected_alpha'];model=fit_model(kind,combined,alpha);start=time.perf_counter();pred,y=predict_model(kind,audit,model);elapsed=time.perf_counter()-start;dim=arrays(combined,kind)[0].shape[1];count=(dim+1)*5 if kind!='random_feature_mlp' else (dim+1)*32+33*5
        rows.append({'name':kind,'parameter_count':count,'development_selected':True,'selected_alpha':alpha,'historical_audit':{**metrics(pred,y,scale),'mean_seconds_per_case':elapsed/len(audit)}})
    by={r['name']:r for r in rows};graph=by['graph_multihop']['historical_audit']['normalized_rmse'];control_names=['metadata','raw_types','rewired_graph','matched_random_graph','random_feature_mlp'];comparisons={n:{'control_normalized_rmse':by[n]['historical_audit']['normalized_rmse'],'relative_improvement':float((by[n]['historical_audit']['normalized_rmse']-graph)/by[n]['historical_audit']['normalized_rmse'])} for n in control_names};go=all(v['relative_improvement']>=.05 for v in comparisons.values())
    result={'schema':'independent-physical-outcome-development-126-v1','status':'completed','contract':{'target_source':'historical official FlyGym/NeuroMechFly physical outcomes','targets_not_generated_by_graph':True,'train_series':106,'development_series':109,'development_partition':{'fit_actions':['foreleg_rubbing','head_directed_grooming'],'selection_action':['reach_withdraw']},'historical_audit_series':112,'historical_audit_is_not_new_untouched_final':True,'target_metrics':TARGETS,'normalization_scale':scale.tolist(),'normalization_scale_floors':SCALE_FLOORS.tolist(),'source_shas':{k:v[1] for k,v in FILES.items()},'graph_input_shas':{'matrix':MATRIX_SHA,'prototypes':PROTOS_SHA},'post_audit_tuning':False,'not_biological_validation':True},'case_counts':{'series106_fit':len(series106),'series109_fit':len(development_fit),'series109_selection':len(development_select),'series112_historical_audit':len(audit)},'development':development,'historical_audit':rows,'comparisons_to_graph':comparisons,'gates':{'graph_margin_required':.05,'graph_advantage_go':go,'series127_authorized':go,'series128_authorized':False,'decision':'GO_TO_SERIES127_UNTOUCHED' if go else 'NO_GO_TEMPORARY_ENGINEERING_CLOSE'},'interpretation':{'outcome_prediction_not_controller_execution':True,'new_physical_run':False,'old_physical_evidence_not_relabelled':True,'series127_untouched_data_not_inspected':True}}
    (folder/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8');lines=['SERIES126 — INDEPENDENT PHYSICAL OUTCOME DEVELOPMENT','',f"Fit: 106={len(series106)} + 109={len(development_fit)} | Development selection109: {len(development_select)} | Historical audit112: {len(audit)}",'']+[f"{r['name']}: normalized RMSE={r['historical_audit']['normalized_rmse']:.6f}" for r in rows]+['',f"Graph advantage >=5% versus every control: {go}",f"Decision: {result['gates']['decision']}",'','Historical outcome prediction only; not a new controller execution or untouched final.'];(folder/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');progress(4,4,'Готово');return folder

def gui():
    import tkinter as tk
    from tkinter import messagebox,ttk
    root=tk.Tk();root.title('Series126: independent physical outcome');root.geometry('780x400+90+60');root.attributes('-topmost',True);status=tk.StringVar(value='Готово');bar=tk.DoubleVar(value=0)
    tk.Label(root,text='Independent FlyGym outcome development',font=('Arial',15,'bold'),pady=15).pack();tk.Label(root,text='Train: Series106 · Development: Series109 · Historical audit: Series112\nTargets were produced by official FlyGym before Graph Core.',justify='center').pack();tk.Label(root,textvariable=status).pack(pady=12);ttk.Progressbar(root,variable=bar,maximum=4,length=570).pack(pady=8);button=tk.Button(root,text='Запустить Series126',padx=20,pady=9);button.pack(pady=12)
    def start():
        button.config(state='disabled')
        def work():
            try:
                out=run(OUTPUT_ROOT,lambda d,t,s:root.after(0,lambda:(bar.set(d),status.set(s))))
                def done():
                    button.config(state='normal');status.set('Готово');
                    if os.name=='nt':os.startfile(str(out.resolve()))
                    messagebox.showinfo('Series126',f'Результат:\n{out.resolve()}',parent=root)
                root.after(0,done)
            except Exception as e:
                p=OUTPUT_ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-126.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(type(e).__name__+': '+str(e)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');root.after(0,lambda:(button.config(state='normal'),status.set('Ошибка'),messagebox.showerror('Series126',f'{e}\n\n{p.resolve()}',parent=root)))
        threading.Thread(target=work,daemon=True).start()
    button.config(command=start);root.mainloop()
def main():
    p=argparse.ArgumentParser();p.add_argument('--gui',action='store_true');p.add_argument('--output-root',type=Path,default=OUTPUT_ROOT);a=p.parse_args();print(run(a.output_root)) if not a.gui else gui()
if __name__=='__main__':main()
