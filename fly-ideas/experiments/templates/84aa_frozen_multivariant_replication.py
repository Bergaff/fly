#!/usr/bin/env python3
"""Series84AA: read-only frozen replication of selected model84Z on motions441-450."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,sys,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER84Z=HERE/'84z_multivariant_ridge_ensemble.py';RUNNER84Z_SHA='fa4040d7271f2c98021042054ebe60767ad092de81d610a60815738be9f57a6b'
MODEL84Z_SHA='cb7610514c423372362f6cd3512b19f39c156213728c5ecaafe17fe10734e4b0';SEED=8436;IDS=tuple(range(441,451))
ROOT=Path('workspace/runs/ideas/i-observational/frozen-multivariant-replication');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/multivariant-ridge-ensemble')
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load84z():
 if file_sha(RUNNER84Z)!=RUNNER84Z_SHA:raise ValueError('Закреплённый runner84Z изменился.')
 s=importlib.util.spec_from_file_location('frozen84z_source',RUNNER84Z);z=importlib.util.module_from_spec(s);s.loader.exec_module(z);return z

def holdouts():
 rng=np.random.default_rng(SEED);out=[]
 for i,ident in enumerate(IDS,1):
  n=5 if i<=5 else 9;z=rng.integers(-55,56,size=(n,6)).astype(int);z[:,3]=np.clip(-z[:,0]+np.rint(.25*z[:,3]).astype(int),-55,55);z[:,4]=np.clip(z[:,1]+np.rint(.25*z[:,4]).astype(int),-55,55);z[:,5]=np.clip(-z[:,2]+np.rint(.25*z[:,5]).astype(int),-55,55);obj={'schema':'fly-wings-trajectory-v1','semantic_schema':'fly-foreleg-grooming-six-joint-v1','channels':['left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal'],'fps':25,'duration_s':2,'keyframes':[{'t':2*j/(n-1),'angles_deg':z[j].tolist()} for j in range(n)]};raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode();out.append((ident,raw))
 return out

def plain_model(path,ev):
 with np.load(path,allow_pickle=False) as z:return ev.checked_model({k:z[k] for k in z.files})
def selected_bundle(path,ev):
 expected={'selected_variant','new_weight','right_distal_ridge','new_mean','new_scale','new_intercept','new_weights','source84v_mean','source84v_scale','source84v_intercept','source84v_weights'}
 with np.load(path,allow_pickle=False) as z:
  if set(z.files)!=expected:raise ValueError('Frozen selected model bundle имеет неверные поля.')
  name=str(z['selected_variant'].item());weight=float(z['new_weight']);ridge=float(z['right_distal_ridge']);new=ev.checked_model({k:np.array(z['new_'+k],copy=True) for k in ('mean','scale','intercept','weights')});old=ev.checked_model({k:np.array(z['source84v_'+k],copy=True) for k in ('mean','scale','intercept','weights')})
 if not np.isfinite(weight) or not np.isfinite(ridge) or not 0<=weight<=1:raise ValueError('Frozen selected model metadata повреждены.')
 return {'selected_variant':name,'new_weight':weight,'right_distal_ridge':ridge,'new':new,'source84v':old}
def predict_model(mod,x):return (x-mod['mean'])/mod['scale']@mod['weights']+mod['intercept']
def predict_selected(bundle,x):return np.clip(bundle['new_weight']*predict_model(bundle['new'],x)+(1-bundle['new_weight'])*predict_model(bundle['source84v'],x),-np.pi*55/180,np.pi*55/180)

def source(folder,fixture=False):
 z=load84z();b=z.m;proto,ev,pre,stim,ck,base,large=b.dependencies();folder=Path(folder).resolve();saved,state,stage,_=b.saved_state(folder/'study.sqlite3',proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая series84Z.')
 result=folder/'result';b.verify_result(result,saved,state);summary=json.loads((result/'summary.json').read_text(encoding='utf8'));expected='fixture_completed' if fixture else'completed'
 if summary.get('status')!=expected or not summary.get('primary',{}).get('passed'):raise ValueError('Нужен завершённый go84Z соответствующего режима.')
 paths=(folder/'study.sqlite3',result/'model_selected.npz',result/'source84v_model.npz',result/'source84s_model.npz',result/'source84r_model.npz',result/'summary.json',result/'complete.json');extra=folder/'evaluation-recovery.json';tracked=paths+((extra,) if extra.is_file() else());before={str(p):file_sha(p) for p in tracked};model_sha=file_sha(paths[1])
 if model_sha!=summary.get('selected_model_sha256') or (not fixture and model_sha!=MODEL84Z_SHA):raise ValueError('Нужна frozen production selected model84Z.')
 if any(file_sha(path)!=summary.get(key) for path,key in ((paths[2],'source84v_model_sha256'),(paths[3],'source84s_model_sha256'),(paths[4],'source84r_model_sha256'))):raise ValueError('Frozen comparator SHA не совпадает.')
 bundle=selected_bundle(paths[1],ev);source84v=plain_model(paths[2],ev)
 if not fixture and (bundle['selected_variant']!='ridge_0175' or bundle['right_distal_ridge']!=.175 or bundle['new_weight']!=1.):raise ValueError('Нужен frozen selected ridge_0175 model84Z.')
 if any(not np.array_equal(bundle['source84v'][k],source84v[k]) for k in source84v):raise ValueError('Embedded frozen84V отличается от comparator file.')
 return z,b,proto,ev,stim,saved,state,summary,paths,tracked,before,bundle,source84v

def tests(stim,labels):
 seen={x['motion_sha256'] for x in labels};items=[];desc=[]
 for ident,raw in holdouts():
  t,a=stim.sample_trajectory(json.loads(raw));h=stim.motion_hash(a)
  if h in seen:raise ValueError('Replication holdout совпал с раскрытым движением.')
  seen.add(h);items.append({'id':ident,'times':t,'angles_deg':a,'motion_sha256':h});desc.append({'id':ident,'source_sha256':sha(raw),'motion_sha256':h,'family':'piecewise5' if ident<=445 else'piecewise9'})
 return items,desc

def existing(root,protocol):
 root=Path(root)
 if not root.exists():return None
 for folder in sorted(root.glob('frozen_multivariant_replication_*'),reverse=True):
  result=folder/'result'
  try:
   p=json.loads((folder/'protocol.json').read_text(encoding='utf8'));c=json.loads((result/'complete.json').read_text(encoding='utf8'));s=json.loads((result/'summary.json').read_text(encoding='utf8'))
   if p==protocol and s.get('protocol')==p and len(s.get('tests',[]))==(8 if p['mode']=='fixture' else 160) and manifest(result)==c.get('files'):return result
  except (OSError,UnicodeError,ValueError,TypeError):pass
 return None

def run(source_folder,output_root=ROOT,fixture=False):
 print('1/5 Проверяются frozen source84Z, comparators, SQLite и manifest...',flush=True);z,b,proto,ev,stim,saved,state,source_summary,paths,tracked,before,bundle,s84v=source(source_folder,fixture);items,desc=tests(stim,saved['labels']);items=items[:2] if fixture else items;desc=desc[:len(items)];protocol={'schema':'frozen-multivariant-replication-v1','mode':'fixture' if fixture else'full','script_sha256':file_sha(__file__),'runner84z_sha256':RUNNER84Z_SHA,'selected_model_sha256':file_sha(paths[1]),'selected_variant':bundle['selected_variant'],'right_distal_ridge':bundle['right_distal_ridge'],'new_weight':bundle['new_weight'],'source84v_model_sha256':file_sha(paths[2]),'source84s_model_sha256':file_sha(paths[3]),'source84r_model_sha256':file_sha(paths[4]),'motion_seed':SEED,'holdouts':desc,'geometry_corners':4 if fixture else 16,'training_allowed':False,'development_selection_allowed':False,'primary_rule':'same strict frozen84V/84S/84R global/lower-X/X/Z/control/corner gates as84Z final'}
 old=existing(output_root,protocol)
 if old:print('Найден и проверен готовый результат:',old,flush=True);return old
 train,_=proto.split_from_sources(state['sources'],stim);accepted,sample=b.sampled_records(Path(source_folder)/'study.sqlite3',len(train));audit=b.overlap_sample_broad(items,sample,128);audit.update({'accepted_total':accepted,'is_exhaustive':audit['audited_count']==accepted});print(f'2/5 Source и audit готовы: {audit["audited_count"]}/{accepted}.',flush=True)
 s84,s84r=plain_model(paths[3],ev),plain_model(paths[4],ev);scene=b.VisibleForelegGroomingScene(proto.load('rep84aa_engine','38_two_flies_observation.py'));corners=[b.geometry_corners()[i] for i in(0,2,4,6)] if fixture else b.geometry_corners();root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('frozen_multivariant_replication_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);rows=[];print('3/5 Frozen models загружены; начинается read-only evaluation.',flush=True)
 for number,item in enumerate(items,1):
  full=item['angles_deg']*np.pi/180;truth=full[2:]
  for corner in corners:
   cid=corner['corner_id'];images=scene.render(full,view=corner['view']);x=b.edge_history(images);cp=predict_selected(bundle,x);vp=np.clip(predict_model(s84v,x),-np.pi*55/180,np.pi*55/180);sp=np.clip(predict_model(s84,x),-np.pi*55/180,np.pi*55/180);rp=np.clip(predict_model(s84r,x),-np.pi*55/180,np.pi*55/180);coeff,replay=b.compress_replay(cp);_,vr=b.compress_replay(vp);_,sr=b.compress_replay(sp);_,rr=b.compress_replay(rp);rng=np.random.default_rng(np.random.SeedSequence([843600,item['id'],cid]));controls={}
   for name,img in {'shuffled':images[rng.permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)}.items():q=b.edge_history(img);_,replay_control=b.compress_replay(predict_selected(bundle,q));controls[name]=b.replay_metrics(truth,replay_control)
   digest=sha(np.asarray(coeff,dtype='<f8').tobytes());r={'test_id':item['id'],'corner_id':cid,'frames':len(truth),'view':corner['view'],'candidate':b.replay_metrics(truth,replay),'source84v':b.replay_metrics(truth,vr),'source84s':b.replay_metrics(truth,sr),'source84r':b.replay_metrics(truth,rr),'zero':b.replay_metrics(truth,np.zeros_like(truth)),'controls':controls,'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':True,'state_sha256_before_delay':digest,'state_sha256_after_delay':digest,'diagnostics':{'rgb_sha256':sha(images.tobytes()),'unique_rgb_frames':len({q.tobytes() for q in images}),'changed_rgb_values':int(np.count_nonzero(images[1:]!=images[:-1])),'candidate_feature_max_std':float(np.max(np.std(x,0))),'candidate_clipped_fraction':float(np.mean(np.abs(cp)>=np.pi*55/180))}};rows.append(r);td=temp/f'test_{item["id"]:03d}'/f'corner_{cid:02d}';td.mkdir(parents=True);save(td/'metrics.json',r);save(td/'internal_state.json',{'coefficients':list(map(float,coeff)),'delay_s':.5,'updates_during_delay':0})
  print(f'  Проверено движение {item["id"]}: {number}/{len(items)}.',flush=True)
 print('4/5 Проверяются preregistered replication gates...',flush=True);primary=z.primary_decision(rows,fixture);report={'schema':'frozen-multivariant-replication-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':primary,'tests':rows,'source84z_primary':source_summary['primary'],'source84z_development':source_summary['development'],'audit':audit,'limitations':['Read-only evaluation; selected model84Z and frozen84V/84S/84R unchanged.','No training or variant selection in replication.','New motions use same synthetic family/grid.','No natural vision, actuators, closed loop, biological brain or mirror-neuron evidence.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 84AA: FROZEN REPLICATION MODEL84Z\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'protocol_sha256':sha(json.dumps(protocol,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84Z изменилась.')
 complete=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))
 if manifest(folder/'result')!=complete['files']:raise ValueError('Manifest повреждён.')
 print('5/5 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog
 root=tk.Tk();root.title('Серия84AA: frozen replication model84Z');root.geometry('620x160+180+140');root.attributes('-topmost',True);tk.Label(root,text='Read-only replication frozen selected model84Z.\nВыберите завершённую папку multivariant_ridge_ensemble_....\nОбучения и повторного выбора variants нет.',font=('Arial',11),padx=20,pady=20).pack();root.update();root.lift();root.focus_force()
 try:
  folder=filedialog.askdirectory(title='Выберите завершённую series84Z',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
  if not folder:print('Выбор отменён.');return
  root.withdraw();root.update();run(folder)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source84z');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--allow-fixture-source',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:choose()
 elif a.source84z:run(a.source84z,a.output_root,a.allow_fixture_source)
 else:p.error('Нужен --choose или --source84z.')
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА: {type(exc).__name__}: {exc}\nSource84Z не изменялась.',file=sys.stderr,flush=True);sys.exit(1)
