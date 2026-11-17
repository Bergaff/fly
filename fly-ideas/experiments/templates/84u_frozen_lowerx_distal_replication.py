#!/usr/bin/env python3
"""Series 84U: read-only frozen replication of model84S on new motions341-350."""
from __future__ import annotations
import argparse,csv,hashlib,importlib.util,io,itertools,json,os,sys,uuid
from datetime import datetime
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
RUNNER84S=HERE/'84s_fixed_count_lowerx_distal_grooming.py'
RUNNER84S_SHA='67915637388a508b88c112ce9f39a0396fcc5a2ef9492928f402826809a8dcd2'
MODEL84S_SHA='a53e7016642db2ebd774e13a589aff841103a15fffd00430d77bf7fdbe93311f'
AXES=('left_proximal','left_middle','left_distal','right_proximal','right_middle','right_distal')
ROOT=Path('workspace/runs/ideas/i-observational/frozen-lowerx-distal-replication')
SOURCE_ROOT=Path('workspace/runs/ideas/i-observational/lowerx-distal-fixed-count')
SEED=8424
IDS=tuple(range(341,351))

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):return sha(Path(path).read_bytes())
def save(path,obj):Path(path).write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf8')
def manifest(folder):return {str(p.relative_to(folder)).replace('\\','/'):file_sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file() and p.name!='complete.json'}
def load84s():
 if file_sha(RUNNER84S)!=RUNNER84S_SHA:raise ValueError('Закреплённый runner84S изменился.')
 spec=importlib.util.spec_from_file_location('frozen84s',RUNNER84S);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def holdout_bytes():
 rng=np.random.default_rng(SEED);out=[]
 for i,ident in enumerate(IDS,1):
  count=5 if i<=5 else 9;v=rng.integers(-55,56,size=(count,6)).astype(int)
  v[:,3]=np.clip(-v[:,0]+np.rint(.25*v[:,3]).astype(int),-55,55);v[:,4]=np.clip(v[:,1]+np.rint(.25*v[:,4]).astype(int),-55,55);v[:,5]=np.clip(-v[:,2]+np.rint(.25*v[:,5]).astype(int),-55,55)
  obj={'schema':'fly-wings-trajectory-v1','semantic_schema':'fly-foreleg-grooming-six-joint-v1','channels':list(AXES),'fps':25,'duration_s':2,'keyframes':[{'t':2*j/(count-1),'angles_deg':v[j].tolist()} for j in range(count)]}
  out.append((ident,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()))
 return out

def source_snapshot(folder,allow_fixture=False):
 m=load84s();proto,ev,pre,stim,ck,base,large=m.dependencies();folder=Path(folder).resolve();saved,state,stage,_=m.saved_state(folder/'study.sqlite3',proto,ck)
 if stage!='completed':raise ValueError('Нужна завершённая серия84S.')
 result=folder/'result';m.verify_result(result,saved,state);summary=json.loads((result/'summary.json').read_text(encoding='utf8'))
 expected='fixture_completed' if allow_fixture else 'completed'
 if summary.get('status')!=expected or bool(saved.get('fixture_limit') is not None)!=allow_fixture:raise ValueError('Неверный режим source84S.')
 model=result/'model_lowerx_distal.npz';model_sha=file_sha(model)
 if model_sha!=summary.get('candidate_model_sha256'):raise ValueError('SHA model84S не совпадает с summary.')
 if not allow_fixture and model_sha!=MODEL84S_SHA:raise ValueError('Выбрана не preregistered model84S.')
 source_model=result/'source84r_model.npz'
 if file_sha(source_model)!=summary.get('source84r_model_sha256'):raise ValueError('SHA frozen source84R не совпадает.')
 before={str(p):file_sha(p) for p in (folder/'study.sqlite3',model,source_model,result/'summary.json',result/'complete.json')}
 return m,proto,ev,stim,large,saved,state,summary,model,source_model,before

def prepared_tests(stim,old_labels):
 seen={x['motion_sha256'] for x in old_labels};tests=[];descriptors=[]
 for ident,raw in holdout_bytes():
  obj=json.loads(raw);times,angles=stim.sample_trajectory(obj);motion=stim.motion_hash(angles)
  if motion in seen:raise ValueError('Replication holdout совпал с раскрытым движением.')
  seen.add(motion);tests.append({'id':ident,'times':times,'angles_deg':angles,'motion_sha256':motion});descriptors.append({'id':ident,'source_sha256':sha(raw),'motion_sha256':motion,'family':'piecewise5' if ident<=345 else 'piecewise9'})
 return tests,descriptors

def pooled(items,key,axis=None):
 n=sum(r['frames'] for r in items);return float(np.sqrt(sum(r['frames']*(r[key]['axis_rmse_rad'][axis] if axis else r[key]['rmse_rad'])**2 for r in items)/n))
def decisions(m,items,fixture):
 cases=len(items);axes={}
 for axis in AXES:
  c=pooled(items,'candidate',axis);s=pooled(items,'source84r',axis);z=pooled(items,'zero',axis);wz=sum(r['candidate']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in items);ws=sum(r['candidate']['axis_rmse_rad'][axis]<r['source84r']['axis_rmse_rad'][axis] for r in items)
  axes[axis]={'candidate':c,'source84r':s,'zero':z,'wins_vs_zero':wz,'wins_vs_source84r':ws,'cases':cases,'passed':c<z and wz>=.70*cases and ((c<s and ws>=.60*cases) if axis=='right_distal' else c<=1.05*s)}
 combined={k:pooled(items,k) for k in ('candidate','source84r','zero')};total=sum(r['frames'] for r in items)
 for name in ('shuffled','static','closed'):combined[name]=float(np.sqrt(sum(r['frames']*r['controls'][name]['rmse_rad']**2 for r in items)/total))
 def safeguard(field,values):
  groups=[]
  for value in values:
   rows=[r for r in items if r['view'][field]==value];aa={}
   for axis in AXES:
    c=pooled(rows,'candidate',axis);z=pooled(rows,'zero',axis);wins=sum(r['candidate']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in rows);aa[axis]={'candidate':c,'zero':z,'wins':wins,'cases':len(rows),'passed':c<z and wins>=.70*len(rows)}
   groups.append({'value':value,'axes':aa,'passed':all(x['passed'] for x in aa.values())})
  return groups
 body=safeguard('body_x',(3.82,4.18));camera=safeguard('camera_z',(.36,.56));lower=[r for r in items if r['view']['body_x']==3.82];lc=pooled(lower,'candidate','right_distal');ls=pooled(lower,'source84r','right_distal');lz=pooled(lower,'zero','right_distal');wz=sum(r['candidate']['axis_rmse_rad']['right_distal']<r['zero']['axis_rmse_rad']['right_distal'] for r in lower);ws=sum(r['candidate']['axis_rmse_rad']['right_distal']<r['source84r']['axis_rmse_rad']['right_distal'] for r in lower);lr={'candidate':lc,'source84r':ls,'zero':lz,'wins_vs_zero':wz,'wins_vs_source84r':ws,'cases':len(lower),'required_vs_zero':int(np.ceil(.75*len(lower))),'required_vs_source84r':int(np.ceil(.60*len(lower)))};lr['passed']=lc<lz and lc<ls and wz>=lr['required_vs_zero'] and ws>=lr['required_vs_source84r'];body[0]['axes']['right_distal']['passed']&=lr['passed'];body[0]['passed']=all(x['passed'] for x in body[0]['axes'].values())
 need=2 if fixture else 7;corners=[]
 for corner in m.geometry_corners() if not fixture else [m.geometry_corners()[i] for i in (0,2,4,6)]:
  rows=[r for r in items if r['corner_id']==corner['corner_id']];aa={}
  for axis in AXES:
   c=pooled(rows,'candidate',axis);z=pooled(rows,'zero',axis);wins=sum(r['candidate']['axis_rmse_rad'][axis]<r['zero']['axis_rmse_rad'][axis] for r in rows);aa[axis]={'candidate':c,'zero':z,'wins':wins,'cases':len(rows),'passed':c<z and wins>=need}
  corners.append({'corner_id':corner['corner_id'],'view':corner['view'],'axes':aa,'passed':all(x['passed'] for x in aa.values())})
 required=4 if fixture else 12;primary={'axes':axes,'combined':combined,'body_x_safeguards':body,'camera_z_safeguards':camera,'corner_results':corners,'corners_passed':sum(x['passed'] for x in corners),'corners_required':required,'lower_x_right_distal_comparator':lr}
 primary['passed']=all(x['passed'] for x in axes.values()) and combined['candidate']<combined['source84r'] and combined['candidate']<combined['zero'] and all(combined['candidate']<combined[k] for k in ('shuffled','static','closed')) and all(x['passed'] for x in body+camera) and primary['corners_passed']>=required
 return primary

def run(source,output_root=ROOT,allow_fixture=False):
 m,proto,ev,stim,large,saved,state,source_summary,model_path,source_model_path,before=source_snapshot(source,allow_fixture);tests,descriptors=prepared_tests(stim,saved['labels']);tests=tests[:2] if allow_fixture else tests
 train,_=proto.split_from_sources(state['sources'],stim);accepted,sample=m.sampled_records(Path(source)/'study.sqlite3',len(train));audit=m.overlap_sample_broad(tests,sample,cap=128);audit.update({'accepted_total':accepted,'is_exhaustive':audit['audited_count']==accepted})
 with np.load(model_path,allow_pickle=False) as z:candidate=ev.checked_model({k:z[k] for k in z.files})
 with np.load(source_model_path,allow_pickle=False) as z:source_model=ev.checked_model({k:z[k] for k in z.files})
 protocol={'schema':'frozen-lowerx-distal-replication-v1','mode':'fixture' if allow_fixture else 'full','script_sha256':file_sha(__file__),'runner84s_sha256':RUNNER84S_SHA,'source84s_model_sha256':file_sha(model_path),'source84r_model_sha256':file_sha(source_model_path),'motion_seed':SEED,'holdouts':descriptors[:len(tests)],'geometry_corners':4 if allow_fixture else 16,'training_allowed':False,'primary_rule':'same absolute, frozen comparator, lower-X, body-X, camera-Z, controls and corner gates as84S'}
 root=Path(output_root);root.mkdir(parents=True,exist_ok=True);folder=root/('frozen_lowerx_distal_replication_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);folder.mkdir();temp=folder/'result_incomplete';temp.mkdir();save(folder/'protocol.json',protocol);scene=m.VisibleForelegGroomingScene(proto.load('rep84u_engine','38_two_flies_observation.py'));corners=[m.geometry_corners()[i] for i in (0,2,4,6)] if allow_fixture else m.geometry_corners();records=[]
 for item in tests:
  truth_full=item['angles_deg']*np.pi/180;truth=truth_full[2:]
  for corner in corners:
   cid=corner['corner_id'];images=scene.render(truth_full,view=corner['view']);x=m.edge_history(images);cp=np.clip((x-candidate['mean'])/candidate['scale']@candidate['weights']+candidate['intercept'],-np.pi*55/180,np.pi*55/180);sp=np.clip((x-source_model['mean'])/source_model['scale']@source_model['weights']+source_model['intercept'],-np.pi*55/180,np.pi*55/180);coeff,replay=m.compress_replay(cp);_,source_replay=m.compress_replay(sp);rng=np.random.default_rng(np.random.SeedSequence([842400,item['id'],cid]));controls={}
   for name,img in {'shuffled':images[rng.permutation(len(images))].copy(),'static':np.repeat(images[:1],len(images),axis=0),'closed':np.zeros_like(images)}.items():
    q=m.edge_history(img);q=np.clip((q-candidate['mean'])/candidate['scale']@candidate['weights']+candidate['intercept'],-np.pi*55/180,np.pi*55/180);_,rp=m.compress_replay(q);controls[name]=m.replay_metrics(truth,rp)
   digest=sha(np.asarray(coeff,dtype='<f8').tobytes());r={'test_id':item['id'],'corner_id':cid,'frames':len(truth),'view':corner['view'],'candidate':m.replay_metrics(truth,replay),'source84r':m.replay_metrics(truth,source_replay),'zero':m.replay_metrics(truth,np.zeros_like(truth)),'controls':controls,'state_coefficients':72,'delay_s':.5,'state_unchanged_during_delay':True,'state_sha256_before_delay':digest,'state_sha256_after_delay':digest,'diagnostics':{'rgb_sha256':sha(images.tobytes()),'unique_rgb_frames':len({a.tobytes() for a in images}),'changed_rgb_values':int(np.count_nonzero(images[1:]!=images[:-1])),'candidate_feature_max_std':float(np.max(np.std(x,0))),'candidate_clipped_fraction':float(np.mean(np.abs(cp)>=np.pi*55/180))}};records.append(r);td=temp/f'test_{item["id"]:03d}'/f'corner_{cid:02d}';td.mkdir(parents=True);save(td/'metrics.json',r);save(td/'internal_state.json',{'coefficients':list(map(float,coeff)),'delay_s':.5,'updates_during_delay':0})
 primary=decisions(m,records,allow_fixture);report={'schema':'frozen-lowerx-distal-replication-result-v1','status':'fixture_completed' if allow_fixture else 'completed','protocol':protocol,'primary':primary,'tests':records,'source84s_primary':source_summary['primary'],'audit':audit,'limitations':['Read-only evaluation; model84S and model84R are unchanged.','New motions use the same synthetic generator family and geometry grid.','No natural vision, actuators, closed loop, biological brain or mirror-neuron evidence.']};save(temp/'summary.json',report);(temp/'ИТОГ.txt').write_text('СЕРИЯ 84U: FROZEN REPLICATION 84S\n\nPrimary: '+('ВЫПОЛНЕН' if primary['passed'] else 'НЕ ВЫПОЛНЕН')+'.\nModel84S не переобучалась и не изменялась.\n',encoding='utf-8-sig');save(temp/'complete.json',{'protocol_sha256':sha(json.dumps(protocol,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()),'files':manifest(temp)});temp.rename(folder/'result')
 after={p:file_sha(p) for p in before}
 if before!=after:raise ValueError('Source84S изменился во время read-only replication.')
 if manifest(folder/'result')!=json.loads((folder/'result'/'complete.json').read_text())['files']:raise ValueError('Manifest replication повреждён.')
 print('Готово:',folder/'result');return folder/'result'

def choose():
 import tkinter as tk
 from tkinter import filedialog,messagebox
 root=tk.Tk();root.title('Серия 84U: frozen replication');root.geometry('560x150+180+140');root.resizable(False,False);root.attributes('-topmost',True)
 tk.Label(root,text='Серия 84U готова к read-only проверке model84S.\nСейчас откроется окно выбора завершённой папки lowerx_distal_fixed_count_....\nОбучения и настройки модели нет.',font=('Arial',11),justify='left',padx=20,pady=20).pack()
 root.update_idletasks();root.deiconify();root.lift();root.focus_force();root.update()
 try:
  print('Открывается окно выбора завершённой папки series84S...',flush=True)
  source=filedialog.askdirectory(title='Серия 84U: выберите завершённую папку series84S',mustexist=True,initialdir=str(SOURCE_ROOT.resolve() if SOURCE_ROOT.exists() else Path.cwd()),parent=root)
  if not source:print('Выбор папки отменён.',flush=True);return
  print('Выбрана source84S:',source,flush=True)
  messagebox.showinfo('Пререгистрация84U','Новые motions341–350, seed8424, все16 corners. Повторяются absolute, lower-X, X/Z, controls и corner gates без изменения модели. После закрытия этого окна начнётся проверка.',parent=root)
  root.withdraw();run(source)
 finally:root.destroy()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choose',action='store_true');p.add_argument('--source84s');p.add_argument('--output-root',default=str(ROOT));p.add_argument('--allow-fixture-source',action='store_true',help=argparse.SUPPRESS);a=p.parse_args()
 if a.choose:
  if a.source84s or a.allow_fixture_source:p.error('--choose используется отдельно.')
  choose()
 elif a.source84s:run(a.source84s,a.output_root,a.allow_fixture_source)
 else:p.error('Нужен --choose или --source84s.')
if __name__=='__main__':
 try:main()
 except Exception as exc:print(f'ОШИБКА: {type(exc).__name__}: {exc}\nSource84S не изменялась.',file=sys.stderr);sys.exit(1)
