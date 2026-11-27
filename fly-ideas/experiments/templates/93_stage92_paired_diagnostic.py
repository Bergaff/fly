#!/usr/bin/env python3
"""Read-only paired diagnosis of the completed Stage92 development benchmark."""
from __future__ import annotations
import argparse,json,math,os,sqlite3,statistics,traceback
from datetime import datetime
from pathlib import Path

ROOT=Path('workspace/runs/ideas/i-connectome-advantage/stage-2-complex-development')
SCENARIOS=('clean','view_high','occlusion','lesion10','lesion25','state_noise','combined_harsh')
BUDGETS=(5,30)

def serial_json(path,value):
 Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')

def latest_completed():
 if not ROOT.exists():return None
 folders=[]
 for p in ROOT.glob('complex_*'):
  if (p/'summary.json').exists() and (p/'study.sqlite3').exists() and (p/'complete.json').exists():folders.append(p)
 return max(folders,key=lambda p:p.stat().st_mtime) if folders else None

def quantile(values,p):
 if not values:return None
 ordered=sorted(values);position=(len(ordered)-1)*p;low=math.floor(position);high=math.ceil(position)
 return ordered[low] if low==high else ordered[low]*(high-position)+ordered[high]*(position-low)

def correlation(xs,ys):
 if len(xs)<2:return 0.0
 mx=statistics.fmean(xs);my=statistics.fmean(ys);sx=sum((x-mx)**2 for x in xs);sy=sum((y-my)**2 for y in ys)
 return sum((x-mx)*(y-my) for x,y in zip(xs,ys))/math.sqrt(sx*sy) if sx>0 and sy>0 else 0.0

def wilson(success,total,z=1.959963984540054):
 if not total:return [0.0,0.0]
 p=success/total;den=1+z*z/total;centre=(p+z*z/(2*total))/den;half=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/den
 return [centre-half,centre+half]

def group_stats(rows):
 da=[r[0] for r in rows];dr=[r[1] for r in rows];n=len(rows)
 aw=sum(x>0 for x in da);at=sum(x==0 for x in da);rw=sum(x>0 for x in dr);rt=sum(x==0 for x in dr)
 dual=sum(a>0 and r>0 for a,r in zip(da,dr));acc_only=sum(a>0 and r<=0 for a,r in zip(da,dr));rmse_only=sum(a<=0 and r>0 for a,r in zip(da,dr));neither=n-dual-acc_only-rmse_only
 def distribution(values):return {'mean':statistics.fmean(values),'median':statistics.median(values),'q05':quantile(values,.05),'q25':quantile(values,.25),'q75':quantile(values,.75),'q95':quantile(values,.95)}
 return {'n':n,'accuracy_delta_structured_minus_shuffled':distribution(da),'rmse_improvement_shuffled_minus_structured':distribution(dr),'accuracy':{'wins':aw,'ties':at,'losses':n-aw-at,'win_rate':aw/n},'rmse':{'wins':rw,'ties':rt,'losses':n-rw-rt,'win_rate':rw/n},'joint':{'dual_wins':dual,'accuracy_only':acc_only,'rmse_only':rmse_only,'neither':neither,'dual_win_rate':dual/n,'dual_win_wilson95':wilson(dual,n)},'delta_correlation':correlation(da,dr)}

def load_rows(db,budget,scenario):
 sql="""SELECT s.accuracy-q.accuracy,q.rmse-s.rmse
 FROM metrics s JOIN metrics q ON s.replicate=q.replicate AND s.budget=q.budget AND s.scenario=q.scenario
 WHERE s.model='structured96' AND q.model='shuffled96' AND s.budget=? AND s.scenario=? ORDER BY s.replicate"""
 return [(float(a),float(r)) for a,r in db.execute(sql,(budget,scenario))]

def diagnose(folder):
 folder=Path(folder);summary=json.loads((folder/'summary.json').read_text(encoding='utf-8-sig'))
 status=summary.get('status');mode=summary.get('protocol',{}).get('mode')
 if status!='completed' and not (status=='fixture_completed' and mode=='fixture'):raise ValueError('Stage92 не имеет completed status.')
 expected=int(summary['completed_replicates']);db=sqlite3.connect(folder/'study.sqlite3');db.execute('PRAGMA query_only=ON')
 replicate_count=db.execute('SELECT COUNT(*) FROM replicates').fetchone()[0];metric_count=db.execute('SELECT COUNT(*) FROM metrics').fetchone()[0]
 if replicate_count!=expected or metric_count!=expected*len(BUDGETS)*len(SCENARIOS)*3:raise ValueError(f'Неполная SQLite: replicates={replicate_count}, metrics={metric_count}.')
 groups={};all_rows=[];harsh_rows=[]
 for budget in BUDGETS:
  groups[str(budget)]={}
  for scenario in SCENARIOS:
   rows=load_rows(db,budget,scenario)
   if len(rows)!=expected:raise ValueError(f'Неполная группа budget={budget}, scenario={scenario}: {len(rows)}.')
   groups[str(budget)][scenario]=group_stats(rows);all_rows.extend(rows)
   if scenario=='combined_harsh':harsh_rows.extend(rows)
 db.close();overall=group_stats(all_rows);harsh=group_stats(harsh_rows)
 failing=[]
 for budget in BUDGETS:
  for scenario in SCENARIOS:
   item=groups[str(budget)][scenario]
   failing.append({'budget':budget,'scenario':scenario,'dual_win_rate':item['joint']['dual_win_rate'],'accuracy_win_rate':item['accuracy']['win_rate'],'rmse_win_rate':item['rmse']['win_rate'],'delta_correlation':item['delta_correlation']})
 failing.sort(key=lambda x:x['dual_win_rate'])
 result={'schema':'stage92-paired-diagnostic-v1','source_folder':str(folder.resolve()),'source_summary_schema':summary.get('schema'),'read_only':True,'replicates':replicate_count,'metrics':metric_count,'groups':groups,'harsh_all_budgets':harsh,'overall':overall,'lowest_dual_win_groups':failing[:7],'gate_reproduction':{'harsh_dual_win_rate':harsh['joint']['dual_win_rate'],'harsh_required':.60,'overall_dual_win_rate':overall['joint']['dual_win_rate'],'overall_required':.55,'candidate':False},'interpretation_boundary':'diagnosis of disclosed development data only; no threshold or architecture is changed and no frozen evidence is created'}
 out=folder/('paired-diagnostic_'+datetime.now().strftime('%Y%m%d_%H%M%S'));out.mkdir()
 serial_json(out/'diagnostic.json',result)
 lines=['ДИАГНОСТИКА STAGE92: PAIRED STABILITY','',f'Replicates: {replicate_count}; metric rows: {metric_count}.','Чтение SQLite: только read-only анализ, модели не переобучались.','',f'Harsh dual wins: {harsh["joint"]["dual_wins"]}/{harsh["n"]} = {100*harsh["joint"]["dual_win_rate"]:.4f}% при пороге60%.',f'Overall dual wins: {overall["joint"]["dual_wins"]}/{overall["n"]} = {100*overall["joint"]["dual_win_rate"]:.4f}% при пороге55%.','', 'РАЗЛОЖЕНИЕ ПО BUDGET И УСЛОВИЮ']
 for budget in BUDGETS:
  for scenario in SCENARIOS:
   x=groups[str(budget)][scenario];j=x['joint'];lines.append(f'budget{budget} {scenario}: dual {100*j["dual_win_rate"]:.4f}%; accuracy wins {100*x["accuracy"]["win_rate"]:.4f}%; RMSE wins {100*x["rmse"]["win_rate"]:.4f}%; acc-only {j["accuracy_only"]}; RMSE-only {j["rmse_only"]}; neither {j["neither"]}; corr {x["delta_correlation"]:.4f}.')
 lines.extend(['','САМЫЕ СЛАБЫЕ ГРУППЫ'])
 for x in failing[:7]:lines.append(f'budget{x["budget"]} {x["scenario"]}: dual {100*x["dual_win_rate"]:.4f}%, accuracy {100*x["accuracy_win_rate"]:.4f}%, RMSE {100*x["rmse_win_rate"]:.4f}%, corr {x["delta_correlation"]:.4f}.')
 lines.extend(['','ГРАНИЦА ВЫВОДА','Это диагностика уже раскрытого development результата. Она не меняет старый gate, не выбирает новый порог и не является frozen evidence. Следующий benchmark проектируется только после разбора этого отчёта.'])
 (out/'ДИАГНОСТИКА.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig');return out

def failure_report(exc):
 path=ROOT/'ПОСЛЕДНЯЯ-ОШИБКА-ДИАГНОСТИКИ-STAGE92.txt';path.parent.mkdir(parents=True,exist_ok=True);path.write_text('ДИАГНОСТИКА STAGE92: ОШИБКА\n'+datetime.now().isoformat()+'\n\n'+type(exc).__name__+': '+str(exc)+'\n\n'+traceback.format_exc(),encoding='utf-8-sig');return path

def gui():
 import tkinter as tk
 from tkinter import messagebox
 root=tk.Tk();root.withdraw();root.attributes('-topmost',True);folder=latest_completed()
 if not folder:messagebox.showerror('Диагностика Stage92','Не найдена завершённая папка Stage92 с summary.json, study.sqlite3 и complete.json.',parent=root);root.destroy();return
 if not messagebox.askokcancel('Диагностика Stage92','Найден завершённый расчёт:\n'+str(folder.resolve())+'\n\nПрочитать SQLite без изменения данных и создать paired-диагностику?',parent=root):root.destroy();return
 try:out=diagnose(folder)
 except Exception as exc:
  report=failure_report(exc);messagebox.showerror('Диагностика остановлена','Ошибка сохранена:\n'+str(report.resolve()),parent=root);os.startfile(str(report));root.destroy();return
 os.startfile(str(out));os.startfile(str(out/'ДИАГНОСТИКА.txt'));messagebox.showinfo('Диагностика готова','Открыты папка и ДИАГНОСТИКА.txt.\n\n'+str(out.resolve()),parent=root);root.destroy()

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--folder');parser.add_argument('--gui',action='store_true');args=parser.parse_args()
 if args.gui:gui()
 elif args.folder:print(diagnose(Path(args.folder)))
 else:raise ValueError('Укажите --gui или --folder.')
if __name__=='__main__':
 try:main()
 except Exception as exc:
  report=failure_report(exc);print(f'ОШИБКА: {exc}\nОтчёт: {report.resolve()}',file=os.sys.stderr);raise SystemExit(1)
