#!/usr/bin/env python3
"""Read-only paired analysis of a completed or partial series 44 database."""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid
from datetime import datetime

for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[key] = '1'
import numpy as np

HERE = Path(__file__).resolve().parent
CONDITIONS = ('wings', 'stationary', 'occluded', 'reverse', 'tile_scramble', 'object_unmatched')
CONTROLS = ('reverse', 'tile_scramble')


def load_lock():
    # Reuse the exact OS-level lock of the study, without running or modifying it.
    spec = importlib.util.spec_from_file_location('two_flies_large', HERE / '44_two_flies_large_study.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.RunLock


def decode(blob, digest, group, condition, dt, duration):
    if hashlib.sha256(blob).hexdigest() != digest:
        raise ValueError(f'Неверная контрольная сумма: группа {group}, {condition}.')
    with np.load(io.BytesIO(blob), allow_pickle=False) as a:
        times = np.asarray(a['times_s']); ids = np.asarray(a['neuron_id']); features = np.asarray(a['features'])
    if times.ndim != 1 or ids.ndim != 1 or len(times) != len(ids) or not np.issubdtype(ids.dtype, np.integer):
        raise ValueError(f'Некорректные события: группа {group}, {condition}.')
    if not np.isfinite(times).all() or np.any(times < 0) or np.any(times >= duration) or np.any(ids < 0) or np.any(ids >= 32):
        raise ValueError(f'Событие вне диапазона: группа {group}, {condition}.')
    ticks = np.rint(times / dt).astype(np.int64)
    if not np.allclose(times, ticks * dt, rtol=0, atol=1e-8):
        raise ValueError(f'События не соответствуют шагу сети: группа {group}, {condition}.')
    if features.shape != (100, 32) or not np.isfinite(features).all():
        raise ValueError(f'Некорректный зрительный вход: группа {group}, {condition}.')
    events = [np.sort(ticks[ids == n]) for n in range(32)]
    if any(np.any(np.diff(x) == 0) for x in events):
        raise ValueError(f'Повтор события на одном шаге: группа {group}, {condition}.')
    return events, features


def write_csv(path, header, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


def analyze(folder, output_parent=None):
    folder = Path(folder).resolve(); dbpath = folder / 'study.sqlite3'
    if not dbpath.is_file(): raise ValueError('В выбранной папке нет study.sqlite3.')
    out_parent = Path(output_parent).resolve() if output_parent else folder
    out_parent.mkdir(parents=True, exist_ok=True)
    RunLock = load_lock()
    with RunLock(folder):
        db = sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True, timeout=30)
        pairs_file = None
        try:
            db.execute('PRAGMA query_only=ON'); db.execute('BEGIN')
            print('Проверка структуры базы. Для большой базы это может занять время.', flush=True)
            check = db.execute('PRAGMA quick_check').fetchall()
            if check != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchone():
                raise ValueError(f'База не прошла проверку SQLite: {check[:3]}')
            entry = db.execute("SELECT value FROM metadata WHERE key='protocol'").fetchone()
            if not entry: raise ValueError('В базе нет протокола.')
            protocol = json.loads(entry[0])
            if protocol.get('schema') != 1 or protocol.get('conditions') != list(CONDITIONS) or protocol.get('frames') != 100 or protocol.get('neural_dt_ms') != 1:
                raise ValueError('Неизвестный протокол серии 44; анализ остановлен.')
            dt = protocol['neural_dt_ms'] / 1000; duration = protocol['frames'] / protocol['fps']
            groups = db.execute('SELECT COUNT(*) FROM groups').fetchone()[0]
            if not groups: raise ValueError('В базе нет групп.')
            counts = dict(db.execute('SELECT condition,COUNT(*) FROM trials GROUP BY condition'))
            if counts != {c: groups for c in CONDITIONS}: raise ValueError('Некорректный набор условий в базе.')
            if db.execute('SELECT g.id FROM groups g LEFT JOIN trials t ON t.group_id=g.id GROUP BY g.id HAVING COUNT(t.condition)!=6 LIMIT 1').fetchone():
                raise ValueError('Обнаружена неполная группа условий.')
            if db.execute('SELECT t.group_id,t.condition FROM trials t LEFT JOIN neurons n ON n.group_id=t.group_id AND n.condition=t.condition GROUP BY t.group_id,t.condition HAVING COUNT(n.neuron_id)!=32 OR MIN(n.neuron_id)!=0 OR MAX(n.neuron_id)!=31 OR SUM(n.spikes)!=t.spikes LIMIT 1').fetchone():
                raise ValueError('Неполные или несогласованные данные нейронов.')
            out = out_parent / ('paired_analysis_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8])
            out.mkdir(); (out / 'INCOMPLETE.txt').write_text('Анализ выполняется или прерван. Не используйте файлы как готовые результаты.\n', encoding='utf-8')
            pairs_file = (out/'neuron_pairs.csv').open('w', newline='', encoding='utf-8-sig')
            pairs_writer = csv.writer(pairs_file)
            pairs_writer.writerow(['group_id','frequency_hz','control','neuron_id','wings_spikes','control_spikes','count_diff_control_minus_wings','matched_spikes_same_tick','unmatched_spike_events'])
            summary = {c: {'groups': 0, 'groups_identical_counts': 0, 'groups_identical_times': 0, 'different_neuron_pairs': 0, 'count_difference_sum': 0, 'absolute_count_difference_sum': 0, 'matched_spikes': 0, 'wings_spikes': 0, 'control_spikes': 0, 'max_feature_error': 0.0} for c in CONTROLS}
            accum = {}
            group_rows = []
            sql = '''SELECT g.id,g.frequency,g.phase,g.distance,g.offset,
                w.payload,w.sha256,w.spikes,r.payload,r.sha256,r.spikes,t.payload,t.sha256,t.spikes
                FROM groups g JOIN trials w ON w.group_id=g.id AND w.condition='wings'
                JOIN trials r ON r.group_id=g.id AND r.condition='reverse'
                JOIN trials t ON t.group_id=g.id AND t.condition='tile_scramble' ORDER BY g.id'''
            for index, row in enumerate(db.execute(sql), 1):
                ident, freq, phase, distance, offset = row[:5]
                data = {}
                for i, name in enumerate(('wings', *CONTROLS)):
                    blob, digest, total = row[5+i*3:8+i*3]
                    events, features = decode(blob, digest, ident, name, dt, duration)
                    if sum(map(len, events)) != total: raise ValueError(f'Число спайков в базе и данных отличается: {ident}, {name}.')
                    stored = list(db.execute('SELECT neuron_id,spikes FROM neurons WHERE group_id=? AND condition=? ORDER BY neuron_id', (ident,name)))
                    if stored != [(n,len(events[n])) for n in range(32)]: raise ValueError(f'Счёты нейронов отличаются от событий: {ident}, {name}.')
                    data[name] = (events, features)
                wing, wf = data['wings']
                for control in CONTROLS:
                    other, cf = data[control]; counts_diff = []; times_diff = []; matched = []
                    for neuron in range(32):
                        a, b = wing[neuron], other[neuron]; m = len(np.intersect1d(a, b, assume_unique=True))
                        diff = len(b)-len(a); sym = len(a)+len(b)-2*m
                        counts_diff.append(diff); times_diff.append(sym); matched.append(m)
                        pairs_writer.writerow((ident,freq,control,neuron,len(a),len(b),diff,m,sym))
                        key = (freq,control,neuron)
                        x = accum.setdefault(key, {'groups':0,'wings_spikes':0,'control_spikes':0,'count_diff':0,'abs_count_diff':0,'same_counts':0,'same_times':0,'matched':0,'event_difference':0})
                        x['groups'] += 1; x['wings_spikes'] += len(a); x['control_spikes'] += len(b); x['count_diff'] += diff; x['abs_count_diff'] += abs(diff); x['same_counts'] += diff == 0; x['same_times'] += sym == 0; x['matched'] += m; x['event_difference'] += sym
                    err = float(np.max(np.abs(wf-cf)))
                    sm = summary[control]; sm['groups'] += 1; sm['groups_identical_counts'] += all(x == 0 for x in counts_diff); sm['groups_identical_times'] += all(x == 0 for x in times_diff); sm['different_neuron_pairs'] += sum(x != 0 for x in times_diff); sm['count_difference_sum'] += sum(counts_diff); sm['absolute_count_difference_sum'] += sum(map(abs,counts_diff)); sm['matched_spikes'] += sum(matched); sm['wings_spikes'] += sum(map(len,wing)); sm['control_spikes'] += sum(map(len,other)); sm['max_feature_error'] = max(sm['max_feature_error'],err)
                    group_rows.append((ident,freq,phase,distance,offset,control,sum(map(len,wing)),sum(map(len,other)),sum(counts_diff),sum(map(abs,counts_diff)),sum(x != 0 for x in counts_diff),sum(x != 0 for x in times_diff),sum(matched),sum(times_diff),err))
                if index % 100 == 0 or index == groups: print(f'Проверено и сравнено групп: {index}/{groups}',flush=True)
            if index != groups: raise ValueError('Не все группы прочитаны.')
            pairs_file.close(); pairs_file = None
            write_csv(out/'groups.csv',['group_id','frequency_hz','phase_deg','distance','offset','control','wings_spikes','control_spikes','count_diff_control_minus_wings','sum_abs_neuron_count_diff','neurons_different_counts','neurons_different_times','matched_spikes_same_neuron_tick','unmatched_spike_events','max_abs_feature_diff'],group_rows)
            neuron_rows=[]
            for (freq,c,n),x in sorted(accum.items()):
                k=x['groups']; neuron_rows.append((freq,c,n,k,x['wings_spikes']/k,x['control_spikes']/k,x['count_diff']/k,x['abs_count_diff']/k,x['same_counts'],x['same_times'],x['matched'],x['event_difference']))
            write_csv(out/'neurons_by_frequency.csv',['frequency_hz','control','neuron_id','groups','mean_wings_spikes','mean_control_spikes','mean_count_diff','mean_abs_count_diff','groups_same_count','groups_same_times','matched_spikes_same_neuron_tick','unmatched_spike_events'],neuron_rows)
            result = {'source_database':str(dbpath),'expected_groups':protocol.get('total_groups'),'groups_analyzed':groups,'full_grid_groups':protocol.get('full_grid_groups'),'test_subset':protocol.get('test_subset'),'expected_group_count_reached':groups == protocol.get('total_groups'),'conditions_present':counts,'sqlite_quick_check':'ok','sha256_verified_conditions':['wings',*CONTROLS],'comparison':'same neuron ID and same 1 ms tick; unmatched is the sum of events present in only one condition','controls':summary,'limitations':['Descriptive model comparisons, not biological replicates or proof of mirror neurons.','Only wings, reverse and tile_scramble payload hashes and events were verified.','Equal totals do not imply equal per-neuron events.','Comparisons are paired within group; no multiple-testing significance claimed.']}
            (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            lines = ['ПАРНЫЙ АНАЛИЗ БОЛЬШОЙ СЕРИИ',f'Групп: {groups} из {protocol.get("total_groups")}; тестовый набор: {protocol.get("test_subset")}.','База открыта только для чтения. Проверены SQLite quick_check, структура и SHA трёх сравниваемых условий.','События совпадают, если совпали ID нейрона и шаг времени 1 мс.','Разности считают как контроль минус wings.']
            for c,x in summary.items():
                lines.extend(['',c, f'Групп с одинаковыми счётами всех 32 нейронов: {x["groups_identical_counts"]}/{groups}', f'Групп с одинаковыми временами всех 32 нейронов: {x["groups_identical_times"]}/{groups}',f'Пар нейронов с различающимися временами: {x["different_neuron_pairs"]}/{groups*32}',f'Средняя знаковая разность суммарных счётов: {x["count_difference_sum"]/groups:.6f}',f'Средняя сумма абсолютных разностей счётов нейронов: {x["absolute_count_difference_sum"]/groups:.6f}',f'Совпавших событий: {x["matched_spikes"]}; wings: {x["wings_spikes"]}; контроль: {x["control_spikes"]}', f'Максимальная абсолютная разность входа по кадрам и нейронам: {x["max_feature_error"]:.12g}'])
            lines.extend(['','Файлы: groups.csv по каждой группе и условию; neuron_pairs.csv по каждому нейрону и группе; neurons_by_frequency.csv по нейронам и частотам; summary.json подробная сводка.','Не биологические повторы и не доказательство зеркальных нейронов.'])
            (out/'ИТОГ.txt').write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
            (out/'INCOMPLETE.txt').unlink()
            print('\n'.join(lines),flush=True); print('\nРезультаты:',out,flush=True)
            return out
        finally:
            if pairs_file is not None: pairs_file.close()
            db.close()


def lower_priority():
    try:
        if os.name == 'nt':
            import ctypes
            kernel = ctypes.windll.kernel32
            kernel.GetCurrentProcess.restype = ctypes.c_void_p
            kernel.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            if not kernel.SetPriorityClass(kernel.GetCurrentProcess(), 0x00004000):
                print('Предупреждение: не удалось снизить приоритет процесса.', flush=True)
        elif hasattr(os, 'nice'):
            os.nice(10)
    except OSError:
        print('Предупреждение: не удалось снизить приоритет процесса.', flush=True)


def main():
    lower_priority()
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--folder');p.add_argument('--output-parent');a=p.parse_args()
    if not a.folder:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
        try: a.folder=filedialog.askdirectory(title='Выберите папку большого исследования с study.sqlite3')
        finally: root.destroy()
        if not a.folder: print('Выбор отменён.');return
    out=analyze(a.folder,a.output_parent)
    if os.name=='nt': os.startfile(str(out))

if __name__=='__main__':
    try: main()
    except Exception as e:
        print(f'ОШИБКА: {type(e).__name__}: {e}\nБаза не изменена. Если создана папка с INCOMPLETE.txt, анализ в ней не завершён.',file=sys.stderr,flush=True)
        sys.exit(1)
