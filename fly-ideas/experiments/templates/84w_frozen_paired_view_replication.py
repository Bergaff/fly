#!/usr/bin/env python3
"""Series84W: read-only frozen replication of model84V on motions381-390."""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,sys,uuid
from datetime import datetime
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
RUNNER84V=HERE/'84v_paired_view_distal_consistency.py';RUNNER84V_SHA='05a0cdd4696af5b8901a1d34a205db8a286264f518cb54e93d1e0b9f9e9e4a52'
MODEL84V_SHA='44b98c31526f5d43bb8eef26fd91ccec827988061df94e01c8aa0a6a19f3b7af';SEED=8428;IDS=tuple(range(381,391))
ROOT=Path('workspace/runs/ideas/i-observational/frozen-paired-view-replication');SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/paired-view-distal-consistency')
def sha(x):return hashlib.sha256(x).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def serial(x):
 if isinstance(x,np.ndarray):return x.tolist()
 if isinstance(x,np.generic):return x.item()
 raise TypeError(type(x).__name__)
def save(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False,default=serial)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load84v():
 if file_sha(RUNNER84V)!=RUNNER84V_SHA:raise ValueError('Закреплённый runner84V изменился.')
 s=importlib.util.spec_from_file_location('frozen84v_source',RUNNER84V);v=importlib.util.module_from_spec(s);s.loader.exec_module(v);return v

def holdouts():
 rng=np.random.default_rng(SEED);out=[]
 for i,ident in enumerate(IDS,1):
  n=5 if i<=5 else 9;z=rng.integers(-55,56,size=(n,6)).astype(int);z[:,3]=np.clip(-z[:,0]+np.rint(.25*z[:,3]).astype(int),-55,55);z[:,4]=np.clip(z[:,1]+np.rint(.25*z[:,4]).astype(int),-55,55);z[:,5]=np.clip(-z[:,2]+np.rint(.25*z[:,5]).astype(int),-55,55);obj={'schema':'fly-wings-trajectory-v1','semantic_schema':'fly-foreleg-grooming-six-joint-v1','channels':list(v.m.AXES),'fps':25,'duration_s':2,'keyframes':[{'t':2*j/(n-1),'angles_deg':z[j].tolist()} for j in range(n)]};raw=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode();out.append((ident,raw))
 return out

def source(folder,fixture=False):
 global v;v=load84v();b=v.m;proto,ev,pre,stim,ck,base,large=b.dependencies();folder=Path(folder).resolve();saved,state,stage,_=b.saved_state(folder/'study.sqlite3',proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая series84V.')
 result=folder/'result';b.verify_result(result,saved,state);summary=json.loads((result/'summary.json').read_text(encoding='utf8'));expected='fixture_completed' if fixture else'completed'
 if summary.get('status')!=expected or not summary.get('primary',{}).get('passed'):raise ValueError('Нужен завершённый go84V соответствующего режима.')
 paths=(folder/'study.sqlite3',result/'model_paired_view.npz',result/'source84s_model.npz',result/'source84r_model.npz',result/'summary.json',result/'complete.json');before={str(p):file_sha(p) for p in paths};model_sha=file_sha(paths[1])
 if model_sha!=summary.get('candidate_model_sha256') or (not fixture and model_sha!=MODEL84V_SHA):raise ValueError('Нужна frozen production model84V.')
 if file_sha(paths[2])!=summary.get('source84s_model_sha256') or file_sha(paths[3])!=summary.get('source84r_model_sha256'):raise ValueError('Frozen comparator SHA не совпадает.')
 return b,proto,ev,stim,large,saved,state,summary,paths,before

def tests(stim,labels):
 seen={x['motion_sha256'] for x in labels};items=[];desc=[]
 for ident,raw in holdouts():
  t,a=stim.sample_trajectory(json.loads(raw));h=stim.motion_hash(a)
  if h in seen:raise ValueError('Replication holdout совпал с раскрытым движением.')
  seen.add(h);items.append({'id':ident,'times':t,'angles_deg':a,'motion_sha256':h});desc.append({'id':ident,'source_sha256':sha(raw),'motion_sha256':h,'family':'piecewise5' if ident<=385 else'piecewise9'})
 return items,desc

def existing(root,protocol):
 root=Path(root)
 if not root.exists():return None
 for folder in sorted(root.glob('frozen_paired_view_replication_*'),reverse=True):
  result=folder/'result'
  try:
   p=json.loads((folder/'protocol.json').read_text(encoding='utf8'));c=json.loads((result/'complete.json').read_text(encoding='utf8'));s=json.loads((result/'summary.json').read_text(encoding='utf8'))
   if p==protocol and s.get('protocol')==p and len(s.get('tests',[]))==(8 if p['mode']=='fixture' else 160) and manifest(result)==c.get('files'):return result
  except (OSError,UnicodeError,ValueError,TypeError):pass
 return None

def run(source_folder,output_root=ROOT,fixture=False):
 print('1/5 Проверяются frozen source84V, comparators, SQLite и manifest...',flush=True);b,proto,ev,stim,large,saved,state,source_summary,paths,before=source(source_folder,fixture);items,desc=tests(stim,saved['labels']);items=items[:2] if fixture else items;desc=desc[:len(items)];protocol={'schema':'frozen-paired-view-replication-v1','mode':'fixture' if fixture else 'full','script_sha256':file_sha(__file__),'runner84v_sha256':RUNNER84V_SHA,'source84v_model_sha256':file_sha(paths[1]),'source84s_model_sha256':file_sha(paths[2]),'source84r_model_sha256':file_sha(paths[3]),'motion_seed':SEED,'holdouts':desc,'geometry_corners':4 if fixture else 16,'training_allowed':False,'primary_rule':'same dual-comparator absolute/lower-X/X/Z/control/corner gates as84V'}
 old=existing(output_root,protocol)
 if old:print('Найден и проверен готовый результат:',old,flush=True);return old
 train,_=proto.split_from_sources(state['sources'],stim);accepted,sample=b.sampled_records(Path(source_folder)/'study.sqlite3',len(train));audit=b.overlap_sample_broad(items,sample,128);audit.update({'accepted_total':accepted,'is_exhaustive':audit['audited_count']==accepted});print(f'2/5 Source и audit готовы: {audit["audited_count"]}/{accepted}.',flush=True)
 def model(path):
  with np.load(path,allow_pickle=False) as z:return ev.checked_model({k:z[k] for k in z.files})
 candidate,s84,s84r=model(paths[1]),model(paths[2]),model(paths[3]);scene=b.VisibleForelegGroomingScene(proto.load('rep84w_engine','38_two_flies_observation.py'));corners=[b.geometry_corners()[i] for i in(0,2,4,6)] if fixture else b.geometry_corners();root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('frozen_paired_view_replication_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);rows=[];print('3/5 Models загружены; начинается evaluation.',flush=True)
 for number,item in enumerate(items,1):
  full=item['angles_deg']*np.pi/180;truth=full[2:]
  for corner in corners:
   cid=corner['corner_id'];images=scene.render(full,view=corner['view']);x=b.edge_history(images)
   def pred(mod):return np.clip((x-mod['mean'])/mod['scale']@mod['weights']+mod['intercept'],-np.pi*55/180,np.pi*55/180)
   cp,sp,rp=pred(candidate),pred(s84),pred(s84r);coeff,replay=b.compress_replay(cp);_,sr=b.compress_replay(sp);_,rr=b.compress_replay(rp);rng=np.random.default_rng(np.random.SeedSequence([842800,item['id'],cid]));controls={}
   for name,img in {'shuffled':images[rng.permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)}.items():q=b.edge_history(img);q=np.clip((q-candidate['mean'])/candidate['scale']@candidate['weights']+candidate['intercept'],-np.pi*55/180,np.pi*55/180);_,replay_control=b.compress_replay(q);controls[name]=b.replay_metrics(truth,replay_control)
   digest=sha(np.asarray(coeff,dtype='<f8').tobytes());r={'test_id':item['id'],'corner_id':cid,'frames':len(truth),'view':corner['view'],'candidate':b.replay_metrics(truth,replay),'source84s':b.replay_metrics(truth,sr),'source84r':b.replay_metrics(truth,rr),'zero':b.replay_metrics(truth,np.zeros_like(truth)),'controls':controls,'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':True,'state_sha256_before_delay':digest,'state_sha256_after_delay':digest,'diagnostics':{'rgb_sha256':sha(images.tobytes()),'unique_rgb_frames':len({q.tobytes() for q in images}),'changed_rgb_values':int(np.count_nonzero(images[1:]!=images[:-1])),'candidate_feature_max_std':float(np.max(np.std(x,0))),'candidate_clipped_fraction':float(np.mean(np.abs(cp)>=np.pi*55/180))}};rows.append(r);td=temp/f'test_{item["id"]:03d}'/f'corner_{cid:02d}';td.mkdir(parents=True);save(td/'metrics.json',r);save(td/'internal_state.json',{'coefficients':list(map(float,coeff)),'delay_s':.5,'updates_during_delay':0})
  print(f'  Проверено движение {item["id"]}: {number}/{len(items)}.',flush=True)
 print('4/5 Проверяются preregistered gates...',flush=True);primary=v.primary_decision(rows,fixture);report={'schema':'frozen-paired-view-replication-result-v1','status':'fixture_completed' if fixture else'completed','protocol':protocol,'primary':primary,'tests':rows,'source84v_primary':source_summary['primary'],'audit':audit,'limitations':['Read-only evaluation; model84V/84S/84R unchanged.','New motions use same synthetic family/grid.','No natural vision, actuators, closed loop, biological brain or mirror-neuron evidence.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 84W: FROZEN REPLICATION 84V\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else'НЕ ВЫПОЛНЕН')+'.\n',encoding='utf-8-sig');save(temp/'complete.json',{'protocol_sha256':sha(json.dumps(protocol,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),'files':manifest(temp)});temp.rename(folder/'result');after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84V изменилась.')
 complete=json.loads((folder/'result'/'complete.json').read_text(encoding='utf8'))
 if manifest(folder/'result')!=complete['files']:raise ValueError('Manifest повреждён.')
 print('5/5 Готово:',folder/'result',flush=True);return folder/'result'
def choose():
 import tkinter as tk
 from tkinter import filedialog
 root=tk.Tk();root.title('Серия84W: frozen replication');root.geometry('580x150+180+140');root.attributes('-topmost',True);tk.Label(root,text='Read-only replication frozen model84V.\nВыберите завершённую папку paired_view_distal_....\nОбучения и настройки модели нет.',font=('Arial',11),padx=20,pady=20).pack();root.update();root.lift();root.focus_force()
 try:
  folder=filedialog.askdirectory(title='Выберите завершённую series84V',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
  if not folder:print('Выбор отменён.');return
  root.withdraw();root.update();run(folder)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source84v');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--allow-fixture-source',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:choose()
 elif a.source84v:run(a.source84v,a.output_root,a.allow_fixture_source)
 else:p.error('Нужен --choose или --source84v.')
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА: {type(exc).__name__}: {exc}\nSource84V не изменялась.',file=sys.stderr,flush=True);sys.exit(1)
