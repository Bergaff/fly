"""Описательный обзор всех 20 seed индивидуальности; новых симуляций нет."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import statistics
import sys
import traceback

HOLDOUT_SHA='8263bdae9cf934ad4aacacfb83fc5899e55f7150a096392aa328f83eef1ee950'
MODE='shiu-individuality-20seed-descriptive-v1'


def load_holdout():
    path=Path(__file__).parent/'35_shiu_individuality_holdout.py'
    if hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()!=HOLDOUT_SHA:
        raise ValueError('Код проверки на новых seed изменён. Анализ остановлен.')
    spec=importlib.util.spec_from_file_location('holdout_original',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def checked_data(pilot,extension,holdout,shared,view,study,manifest,out):
    _,meta,controls=pilot.source_snapshot(shared,view,study,manifest,out)
    old_protocol=pilot.protocol(meta,controls,study.name)
    base=pilot.pilot_dir(Path(os.environ['FLY_SHIU_SHARED_ROOT']),study.name)
    previous=holdout.load_previous(pilot,extension,shared,view,base,old_protocol,out)
    protocol=holdout.make_protocol(pilot,old_protocol,previous)
    folder=base/'holdout_10seeds_v1';source=folder/'holdout.sqlite3'
    if folder.is_symlink() or not folder.is_dir() or source.is_symlink() or not source.is_file():
        raise ValueError('База проверки на новых seed отсутствует или является ссылкой.')
    with shared.lock(folder): view.snapshot(source,out/'holdout.sqlite3')
    db=holdout.open_db(pilot,out,protocol,previous,False)
    try: rows=db.execute('SELECT variant,seed,left_count,right_count,sim_seconds,total_seconds,weight_sha256,digest FROM trials ORDER BY variant,seed').fetchall()
    finally: db.close()
    if len(rows)!=100 or {(r[0],r[1]) for r in rows}!={(v,s) for v in pilot.VARIANTS for s in holdout.NEW_SEEDS}:
        raise ValueError('Нужны все 100 проверенных новых повторов seed 10–19.')
    return controls,sorted(previous+rows),protocol


def analyze(pilot,holdout,view,out,controls,rows,protocol):
    values={(r[0],r[1]):r for r in rows};ctrl={r[2]:r for r in controls}
    variants=[];seed_rows=[];trial_rows=[]
    for v in pilot.VARIANTS:
        all_rows=[values[(v,s)] for s in range(20)]
        left=[r[2] for r in all_rows];right=[r[3] for r in all_rows]
        variants.append({'variant':v+1,'weight_seed':1000+v,'trials':20,'left_mean_hz':statistics.mean(left),
            'left_sd_hz':statistics.stdev(left),'right_mean_hz':statistics.mean(right),'right_sd_hz':statistics.stdev(right),
            'left_mean_0_9':statistics.mean(left[:10]),'left_mean_10_19':statistics.mean(left[10:]),
            'right_mean_0_9':statistics.mean(right[:10]),'right_mean_10_19':statistics.mean(right[10:]),
            'left_mean_minus_control':statistics.mean(left[s]-ctrl[s][3] for s in range(20)),
            'right_mean_minus_control':statistics.mean(right[s]-ctrl[s][4] for s in range(20)),
            'weight_sha256':all_rows[0][6]})
        for r in all_rows:
            _,s,l,rr,sim,total,w,_=r
            trial_rows.append({'variant':v+1,'weight_seed':1000+v,'input_seed':s,'left_count':l,'right_count':rr,
                'control_left_count':ctrl[s][3],'control_right_count':ctrl[s][4],
                'left_difference':l-ctrl[s][3],'right_difference':rr-ctrl[s][4],
                'origin':'pilot' if s<3 else 'extension' if s<10 else 'holdout','weight_sha256':w})
    for s in range(20):
        left=[values[(v,s)][2] for v in pilot.VARIANTS];right=[values[(v,s)][3] for v in pilot.VARIANTS]
        seed_rows.append({'input_seed':s,'control_left_count':ctrl[s][3],'control_right_count':ctrl[s][4],
            'variants_left_mean':statistics.mean(left),'variants_right_mean':statistics.mean(right),
            'variants_left_min':min(left),'variants_left_max':max(left),
            'left_variant_9':left[8],'left_variant_10':left[9],'left_difference_10_minus_9':left[9]-left[8]})
    pilot.write_csv(out/'variants_20seed.csv',list(variants[0]),variants)
    pilot.write_csv(out/'seeds_20seed.csv',list(seed_rows[0]),seed_rows)
    pilot.write_csv(out/'trials_20seed.csv',list(trial_rows[0]),trial_rows)
    left_a=[x['left_mean_0_9'] for x in variants];left_b=[x['left_mean_10_19'] for x in variants]
    right_a=[x['right_mean_0_9'] for x in variants];right_b=[x['right_mean_10_19'] for x in variants]
    rankcorr=lambda a,b:holdout.correlation(holdout.average_ranks(a),holdout.average_ranks(b))
    diffs=[values[(9,s)][2]-values[(8,s)][2] for s in range(20)]
    # Balanced two-way descriptive decomposition, not a variance-components model.
    def decomposition(index):
        matrix=[[values[(v,s)][index] for s in range(20)] for v in pilot.VARIANTS]
        grand=statistics.mean(x for row in matrix for x in row)
        vm=[statistics.mean(row) for row in matrix]
        sm=[statistics.mean(row[s] for row in matrix) for s in range(20)]
        ss_v=20*sum((x-grand)**2 for x in vm)
        ss_s=10*sum((x-grand)**2 for x in sm)
        ss_res=sum((matrix[v][s]-vm[v]-sm[s]+grand)**2 for v in range(10) for s in range(20))
        return {'total_ss':sum((x-grand)**2 for row in matrix for x in row),
                'variant_mean_ss':ss_v,'seed_mean_ss':ss_s,'residual_ss':ss_res}
    sums={'left':decomposition(2),'right':decomposition(3)}
    metrics={'left_spearman_0_9_vs_10_19':rankcorr(left_a,left_b),
             'left_pearson_0_9_vs_10_19':holdout.correlation(left_a,left_b),
             'right_spearman_0_9_vs_10_19':rankcorr(right_a,right_b),
             'control_left_mean_hz':statistics.mean(ctrl[s][3] for s in range(20)),
             'control_right_mean_hz':statistics.mean(ctrl[s][4] for s in range(20)),
             'all_variants_left_mean_hz':statistics.mean(x['left_mean_hz'] for x in variants),
             'all_variants_right_mean_hz':statistics.mean(x['right_mean_hz'] for x in variants),
             'variant_10_minus_9_left_mean_hz':statistics.mean(diffs),
             'variant_10_above_9_seed_count':sum(x>0 for x in diffs),
             'variant_10_equal_9_seed_count':sum(x==0 for x in diffs),
             'variant_10_below_9_seed_count':sum(x<0 for x in diffs),
             'sums_of_squares':sums}
    fmt=lambda x:'не определена' if x is None else f'{x:.3f}'
    text=['ОБЗОР МОДЕЛЬНЫХ ВАРИАНТОВ НА 20 SEED','Проверены исходные 100 и новые 100 повторов, а также контрольные данные; симуляции не запускались.',
          '10 искусственных фиксированных вариантов, 50 Гц, 1 с; все 20 seed на вариант.',
          f"Контроль seed 0–19: левый {metrics['control_left_mean_hz']:.2f} Гц, правый {metrics['control_right_mean_hz']:.2f} Гц.",
          f"Среднее вариантов: левый {metrics['all_variants_left_mean_hz']:.2f} Гц, правый {metrics['all_variants_right_mean_hz']:.2f} Гц.",
          f"Спирмен для средних по вариантам, 0–9 против 10–19: левый {fmt(metrics['left_spearman_0_9_vs_10_19'])}, правый {fmt(metrics['right_spearman_0_9_vs_10_19'])}.",
          f"Левый MN9: вариант 10 минус 9 на всех 20 seed {metrics['variant_10_minus_9_left_mean_hz']:.2f} Гц; выше/равно/ниже: {metrics['variant_10_above_9_seed_count']}/{metrics['variant_10_equal_9_seed_count']}/{metrics['variant_10_below_9_seed_count']}. Пара выбрана после просмотра первой серии.",
          '', 'Вариант | левый среднее ± SD | правый среднее ± SD | разница слева с контролем']
    for x in variants:
        text.append(f"{x['variant']:>7} | {x['left_mean_hz']:.2f} ± {x['left_sd_hz']:.2f} | {x['right_mean_hz']:.2f} ± {x['right_sd_hz']:.2f} | {x['left_mean_minus_control']:+.2f}")
    text.extend(['','Описательное разложение суммы квадратов для полной таблицы 10 × 20 (не модель доли индивидуальности):'])
    for side,ss in sums.items():
        text.append(f"{side}: всего {ss['total_ss']:.2f}; различия средних вариантов {ss['variant_mean_ss']:.2f}; различия средних seed {ss['seed_mean_ss']:.2f}; остаток {ss['residual_ss']:.2f}.")
    text.extend(['Остаток включает взаимодействие и шум; на каждую комбинацию только один повтор, разделить их нельзя.',
                 'Seed фиксированы, одинаковый номер не гарантирует одинаковых входных спайков. Это не причинное разложение и не оценка доли индивидуальности.',
                 '10 искусственных вариантов одной модели и одна частота не являются животными или поведением. Значимость и устойчивый биологический фенотип не установлены.',
                 'Разница вариантов 9 и 10 и дальнейшие сравнения имеют исследовательский характер; никакой тест значимости не выполнялся.'])
    (out/'report.txt').write_text('\n'.join(text)+'\n',encoding='utf8')
    view.atomic_json(out/'summary.json',{'status':'complete','mode':MODE,'study_id':protocol['study_id'],'trials':len(rows),'seeds':20,
        'metrics':metrics,'previous_rows_sha256':protocol['previous_rows_sha256'],
        'files':['report.txt','variants_20seed.csv','seeds_20seed.csv','trials_20seed.csv','source_snapshot.sqlite3','pilot.sqlite3','extension.sqlite3','holdout.sqlite3']})
    print('\n'.join(text),flush=True)


def execute(pilot,extension,holdout,shared,view,study,manifest,out):
    controls,rows,protocol=checked_data(pilot,extension,holdout,shared,view,study,manifest,out)
    analyze(pilot,holdout,view,out,controls,rows,protocol)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['analyze-20'],required=True);parser.add_argument('--study',required=True);args=parser.parse_args()
    out=Path(os.environ['FLY_RUN_DIR']);out.mkdir(parents=True,exist_ok=True)
    try:
        holdout=load_holdout();extension=holdout.load_extension();pilot=extension.load_pilot();shared=pilot.load_shared();module,view=shared.modules()
        study=shared.study_path(os.environ['FLY_SHIU_SHARED_ROOT'],args.study);manifest=shared.read_manifest(study)
        execute(pilot,extension,holdout,shared,view,study,manifest,out);return 0
    except Exception as exc:
        out.joinpath('summary.json').write_text(json.dumps({'status':'error','mode':MODE,'error':f'{type(exc).__name__}: {exc}','files':[]},ensure_ascii=False,indent=2),encoding='utf8')
        print(traceback.format_exc(),file=sys.stderr,flush=True);return 1

if __name__=='__main__':sys.exit(main())
