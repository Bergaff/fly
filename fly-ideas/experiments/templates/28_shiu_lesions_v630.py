"""Исходящие лезии v630: проба и возобновляемый расчёт.

Требует папку полного прогона 27 с summary.json, top200.csv и всеми 30
контрольными файлами. По умолчанию проверяет входы; --simulate --pilot
выполняет только контроль и одну лезию, --simulate запускает полный план.
"""
# Portions adapted from Drosophila_brain_model/model.py (MIT License).
# Copyright (c) 2023 Philip Shiu and Nico Spiller
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import math
import os
import sqlite3
import sys
import time
import traceback
from pathlib import Path

TOP_SHA = 'e630558dbb35e34d5af45bde417e1b91d36e2c6a7c4417e87be27fa2565b2f08'
FREQS = [50,60,70,80,90,100,110,120]
SEEDS = list(range(30))


def load_top():
    path=Path(__file__).parent/'27_shiu_top200_v630.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=TOP_SHA:
        raise ValueError('Версия скрипта отбора топ-200 не совпадает с проверенной.')
    spec=importlib.util.spec_from_file_location('top_reference',path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def validate_top(top, base, data, hashes, folder):
    import numpy as np
    report=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    if report.get('status')!='ok' or report.get('mode')!='simulation' or report.get('result',{}).get('trials')!=30:
        raise ValueError('Нужна папка завершённого полного отбора топ-200 на 30 повторов, не пилота.')
    import brian2 as b2
    expected={'schema':1,'connection_sha256':hashes['connections']['sha256'],'neuron_sha256':hashes['neurons']['sha256'],
              'script_sha256':TOP_SHA,'base_sha256':top.BASE_SHA256,'python':sys.version.split()[0],
              'brian2':b2.__version__,'numpy':np.__version__,'side':'right','frequency_hz':200,
              'duration_ms':1000,'dt_ms':0.1,'seeds':SEEDS}
    if report.get('protocol') != expected:
        raise ValueError('Протокол, версия кода, Python, пакеты или исходные данные отбора не совпадают с текущими.')
    counts=top.read_checkpoint(folder,expected,len(data['ids']))
    if sorted(counts)!=SEEDS:
        raise ValueError('В отборе топ-200 должны быть все 30 проверенных повторов.')
    total=np.zeros(len(data['ids']),dtype=np.int64)
    for c,_ in counts.values(): total+=c
    order=sorted(np.flatnonzero(total>0).tolist(),key=lambda i:(-int(total[i]),int(data['ids'][i])))
    if len(order)<200: raise ValueError('В отборе менее 200 активных нейронов.')
    if report['result'].get('active_neurons') != len(order) or report['result'].get('cutoff_rate_hz') != int(total[order[199]])/30:
        raise ValueError('Итоговый отчёт отбора не соответствует сохранённым повторам.')
    with (folder/'top200.csv').open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=['rank','root_id','mean_rate_hz','total_spikes_30_trials']:
            raise ValueError('Неожиданные столбцы top200.csv.')
        rows=list(reader)
    if len(rows)!=200: raise ValueError('В top200.csv должно быть ровно 200 строк.')
    for rank,(row,i) in enumerate(zip(rows,order[:200]),1):
        if (row['rank']!=str(rank) or row['root_id']!=data['ids'][i]
            or row['total_spikes_30_trials']!=str(int(total[i]))
            or not math.isclose(float(row['mean_rate_hz']),int(total[i])/30,rel_tol=1e-12,abs_tol=1e-12)):
            raise ValueError(f'top200.csv не соответствует сохранённым повторам, строка {rank}.')
    return [data['ids'][i] for i in order[:200]],len(order)


def trial(base,data,frequency,seed,target):
    import numpy as np
    import brian2 as b2
    b2.start_scope(); b2.prefs.codegen.target='numpy'; b2.defaultclock.dt=0.1*b2.ms
    params={'v_0':-52*b2.mV,'v_rst':-52*b2.mV,'v_th':-45*b2.mV,'t_mbr':20*b2.ms,'tau':5*b2.ms,'t_rfc':2.2*b2.ms}
    eqs='dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)\ndg/dt = -g / tau : volt (unless refractory)\nrfc : second'
    neurons=b2.NeuronGroup(len(data['ids']),eqs,method='linear',threshold='v > v_th',reset='v = v_rst; g = 0*mV',refractory='rfc',namespace=params)
    neurons.v=params['v_0']; neurons.g=0; neurons.rfc=params['t_rfc']
    syn=b2.Synapses(neurons,neurons,'w : volt',on_pre='g += w',delay=1.8*b2.ms)
    syn.connect(i=data['pre'],j=data['post'])
    if target:
        weights=data['weights'].copy(); weights[data['pre']==data['lookup'][target]]=0
        syn.w=weights*0.275*b2.mV
        del weights
    else:
        syn.w=data['weights']*0.275*b2.mV
    pois=[]
    for rid in base.RIGHT:
        idx=data['lookup'][rid]; neurons[idx].rfc=0*b2.ms
        pois.append(b2.PoissonInput(neurons[idx],'v',N=1,rate=frequency*b2.Hz,weight=0.275*250*b2.mV))
    monitor=b2.SpikeMonitor(neurons,record=False); net=b2.Network(neurons,syn,monitor,*pois)
    b2.seed(seed); start=time.time(); net.run(1000*b2.ms,namespace={})
    result=(int(monitor.count[data['lookup'][base.MN9['left']]]),int(monitor.count[data['lookup'][base.MN9['right']]]),round(time.time()-start,3))
    del net,monitor,pois,syn,neurons
    gc.collect()
    return result


def row_hash(freq,target,seed,left,right,seconds):
    payload=json.dumps([freq,target,seed,left,right,float(seconds).hex()],separators=(',',':'),ensure_ascii=True)
    return hashlib.sha256(payload.encode('ascii')).hexdigest()


def open_db(out,meta,source):
    db_path=out/'lesions.sqlite3'
    if source:
        src=Path(source).resolve()
        if src==out.resolve(): raise ValueError('Папка продолжения должна отличаться от новой папки прогона.')
        source_db=src/'lesions.sqlite3'
        if not source_db.is_file(): raise ValueError('В выбранной папке нет lesions.sqlite3.')
        with sqlite3.connect(source_db.as_uri()+'?mode=ro',uri=True) as old, sqlite3.connect(db_path) as copy:
            old.backup(copy)
    db=sqlite3.connect(db_path)
    try:
        db.execute('PRAGMA synchronous=FULL')
        if source:
            if db.execute('PRAGMA quick_check').fetchone()[0]!='ok': raise ValueError('Контрольная база повреждена.')
            items=db.execute('SELECT value FROM metadata WHERE key=?',('protocol',)).fetchall()
            if len(items)!=1 or json.loads(items[0][0])!=meta: raise ValueError('Контрольная база создана с другими данными, версиями, списком или протоколом.')
            rows=db.execute('SELECT frequency,target,seed,left_count,right_count,wall_seconds,digest FROM trials').fetchall()
            allowed=set(meta['candidates'])|{''}; seen=set()
            for freq,target,seed,left,right,seconds,digest in rows:
                key=(freq,target,seed)
                if key in seen or freq not in FREQS or target not in allowed or seed not in SEEDS or not isinstance(left,int) or not isinstance(right,int) or not 0<=left<=10000 or not 0<=right<=10000 or not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<0:
                    raise ValueError('Контрольная база содержит некорректные повторы.')
                if digest!=row_hash(freq,target,seed,left,right,seconds): raise ValueError('Контрольная сумма повтора в базе не совпала.')
                seen.add(key)
        else:
            db.executescript('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL); CREATE TABLE trials(frequency INTEGER NOT NULL,target TEXT NOT NULL,seed INTEGER NOT NULL,left_count INTEGER NOT NULL,right_count INTEGER NOT NULL,wall_seconds REAL NOT NULL,digest TEXT NOT NULL,PRIMARY KEY(frequency,target,seed));')
            db.execute('INSERT INTO metadata VALUES(?,?)',('protocol',json.dumps(meta,ensure_ascii=False,sort_keys=True)))
            db.commit()
        return db
    except Exception:
        db.close(); raise


def save_results(db,out,base,candidates):
    import statistics
    existing={(f,t,s):(l,r) for f,t,s,l,r in db.execute('SELECT frequency,target,seed,left_count,right_count FROM trials')}
    with (out/'lesion_rates.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f); w.writerow(['rank','root_id','role','frequency_hz','control_left_hz','lesion_left_hz','ratio_left','control_right_hz','lesion_right_hz','ratio_right'])
        classified=[]
        for rank,target in enumerate(candidates,1):
            role='stimulated_grn' if target in base.RIGHT else 'mn9' if target in base.MN9.values() else 'other'
            hits=[]; undefined=False
            for freq in FREQS:
                control=[existing[(freq,'',seed)] for seed in SEEDS]
                lesion=[existing[(freq,target,seed)] for seed in SEEDS]
                cl=statistics.mean(x[0] for x in control); cr=statistics.mean(x[1] for x in control)
                ll=statistics.mean(x[0] for x in lesion); lr=statistics.mean(x[1] for x in lesion)
                ratio=ll/cl if cl else None; rr=lr/cr if cr else None
                if ratio is None: undefined=True
                elif ratio<=0.8: hits.append(freq)
                w.writerow([rank,target,role,freq,cl,ll,'' if ratio is None else ratio,cr,lr,'' if rr is None else rr])
            classified.append((rank,target,role,'yes' if hits else 'undefined' if undefined else 'no',';'.join(map(str,hits))))
    with (out/'lesion_classification.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.writer(f);w.writerow(['rank','root_id','role','left_mn9_le_80_percent_any_frequency','frequencies_hz']);w.writerows(classified)
    return {'classified_yes':sum(x[3]=='yes' for x in classified),'undefined':sum(x[3]=='undefined' for x in classified)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--top-run',required=True);p.add_argument('--simulate',action='store_true');p.add_argument('--pilot',action='store_true');p.add_argument('--resume-from',default='')
    args=p.parse_args();run=os.environ.get('FLY_RUN_DIR','').strip()
    if not run: print('FLY_RUN_DIR не задан. Запустите из приложения.',file=sys.stderr);return 2
    out=Path(run);out.mkdir(parents=True,exist_ok=True)
    report={'status':'pending','mode':'pilot' if args.pilot else 'simulation' if args.simulate else 'preflight','args':vars(args),
      'scope':'Исходящие лезии v630, правая стимуляция по авторскому ноутбуку; не биологическая валидация.',
      'caveats':['Сторона протокола в авторском ноутбуке и подписи статьи различается.',
       'Лезия обнуляет исходящие веса, не отключая собственные спайки выбранного нейрона. В списке есть стимулированные GRN и MN9.',
       'Критерий 80% рассчитывается по средним частотам левого MN9 при каждом уровне стимуляции. При нулевом контроле отношение не определено.',
       'Seed одинаков для контроля и лезии, но полное совпадение входных спайковых времён не проверяется. Псевдослучайные повторы не являются животными.',
       'Это отдельная реализация уравнений; совпадение на искусственной сети не доказывает полную эквивалентность авторскому коду или статье.'], 'files':[]}
    db=None
    try:
        if args.pilot and not args.simulate: raise ValueError('Для пилота требуется --simulate.')
        import numpy as np
        import brian2 as b2
        top=load_top();base=top.base_module()
        conn=base.input_file('FLY_SHIU_CONNECTIONS','.parquet');neurons=base.input_file('FLY_SHIU_NEURONS','.csv')
        print('Проверяем исходные данные v630...',flush=True)
        hashes={'connections':base.fingerprint(conn),'neurons':base.fingerprint(neurons)}
        if any(hashes[k]['git_blob_sha1']!=v for k,v in base.EXPECTED.items()): raise ValueError('Файлы не совпадают с авторской v630.')
        data=base.validate_inputs(conn,neurons,args.simulate)
        for key,path in [('connections',conn),('neurons',neurons)]:
            stat=path.stat()
            if (stat.st_size,stat.st_mtime_ns)!=(hashes[key]['bytes'],hashes[key]['mtime_ns']): raise ValueError(f'Файл изменился: {path}')
        print('Проверяем все повторы отбора и список топ-200...',flush=True)
        folder=Path(args.top_run);candidates,active=validate_top(top,base,data,hashes,folder)
        eligible=[x for x in candidates if x not in base.RIGHT and x not in base.MN9.values()]
        if not eligible: raise ValueError('Нет кандидата для пробной лезии вне стимулов и MN9.')
        pilot_target=eligible[0]
        meta={'schema':1,'connection_sha256':hashes['connections']['sha256'],'neuron_sha256':hashes['neurons']['sha256'],
              'top_script_sha256':TOP_SHA,'base_sha256':top.BASE_SHA256,'lesion_script_sha256':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
              'top_checkpoint_sha256':top.hashfile(folder/'checkpoint.json'),'top_csv_sha256':top.hashfile(folder/'top200.csv'),
              'python':sys.version.split()[0],'brian2':b2.__version__,'numpy':np.__version__,'candidates':candidates,
              'frequencies_hz':FREQS,'seeds':SEEDS,'side':'right','duration_ms':1000,'dt_ms':0.1}
        report.update(inputs=hashes,protocol=meta,top200={'path':str(folder),'active_neurons':active,'count':len(candidates),'pilot_target':pilot_target})
        if not args.simulate:
            report['status']='preflight_complete';code=0
        else:
            db=open_db(out,meta,args.resume_from)
            existing={(f,t,s) for f,t,s in db.execute('SELECT frequency,target,seed FROM trials')}
            plan=[(100,'',0),(100,pilot_target,0)] if args.pilot else [(f,t,s) for f in FREQS for t in ['']+candidates for s in SEEDS]
            done=sum(item in existing for item in plan)
            print(f'План: {len(plan)} повторов; уже сохранено: {done}.',flush=True)
            for freq,target,seed in plan:
                if (freq,target,seed) in existing: continue
                print(f'{done+1}/{len(plan)}: {freq} Гц, {target or "контроль"}, seed {seed}',flush=True)
                left,right,seconds=trial(base,data,freq,seed,target)
                db.execute('INSERT INTO trials VALUES(?,?,?,?,?,?,?)',(freq,target,seed,left,right,seconds,row_hash(freq,target,seed,left,right,seconds)));db.commit()
                existing.add((freq,target,seed));done+=1
                top.atomic_json(out/'progress.json',{'completed':done,'total':len(plan),'last':{'frequency_hz':freq,'target':target or None,'seed':seed}})
            report['files']=['lesions.sqlite3','progress.json']
            if args.pilot:
                a=db.execute('SELECT left_count,right_count FROM trials WHERE frequency=100 AND target=? AND seed=0',('',)).fetchone()
                b=db.execute('SELECT left_count,right_count FROM trials WHERE frequency=100 AND target=? AND seed=0',(pilot_target,)).fetchone()
                report['status']='pilot_complete';report['result']={'target':pilot_target,'frequency_hz':100,'seed':0,'control_left_hz':a[0],'lesion_left_hz':b[0],'control_right_hz':a[1],'lesion_right_hz':b[1]}
            else:
                report['status']='ok';report['result']={'completed':done,'total':len(plan),**save_results(db,out,base,candidates)}
                report['files']+=['lesion_rates.csv','lesion_classification.csv']
            code=0
    except Exception as exc:
        report['status']='error';report['error']=f'{type(exc).__name__}: {exc}';code=1
        print(traceback.format_exc(),file=sys.stderr,flush=True)
    finally:
        if db is not None: db.close()
    # Не зависим от import экспериментальных модулей для записи сообщения об ошибке.
    tmp=out/'summary.json.tmp'
    with tmp.open('w',encoding='utf-8') as f: json.dump(report,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
    os.replace(tmp,out/'summary.json')
    print(f'Лезии: {report["status"]}. Отчёт: {out / "summary.json"}',flush=True)
    return code

if __name__=='__main__': sys.exit(main())
