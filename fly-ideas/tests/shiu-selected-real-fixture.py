"""Проверяет ввод/отбор и реальные одиночные и двойные лезии на искусственной сети."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def main():
    root=Path(__file__).resolve().parents[1];templates=root/'experiments/templates'
    # Существующая фикстура создаёт синтетические входы, полный проверяемый топ-200,
    # а также сверяет два состояния исходного ядра с авторским model.py.
    fixture=root/'tests/shiu-lesions-fixture.py'
    prefix=fixture.read_text(encoding='utf8').split('# Маленький план для проверки транзакций')[0]
    scope={'__file__':str(fixture),'__name__':'fixture_prefix'}
    exec(compile(prefix,str(fixture),'exec'),scope)
    base=scope['base'];top=scope['top'];lesion=scope['lesion'];data=scope['data'];folder=scope['folder'];hashes=scope['hashes']
    import numpy as np
    import brian2 as b2
    meta={'schema':1,'connection_sha256':hashes['connections']['sha256'],'neuron_sha256':hashes['neurons']['sha256'],
          'top_script_sha256':lesion.TOP_SHA,'base_sha256':top.BASE_SHA256,'lesion_script_sha256':hashlib.sha256((templates/'28_shiu_lesions_v630.py').read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
          'top_checkpoint_sha256':top.hashfile(folder/'checkpoint.json'),'top_csv_sha256':top.hashfile(folder/'top200.csv'),
          'python':sys.version.split()[0],'brian2':b2.__version__,'numpy':np.__version__,'candidates':scope['selected'],
          'frequencies_hz':lesion.FREQS,'seeds':lesion.SEEDS,'side':'right','duration_ms':1000,'dt_ms':.1}
    view=load('view',templates/'30_shiu_lesion_overview.py');study=load('study',templates/'31_shiu_selected_lesions.py')
    view.reference=lambda:lesion;study.overview=lambda:view
    os.environ.update(FLY_SHIU_CONNECTIONS=str(scope['conn']),FLY_SHIU_NEURONS=str(scope['comp']))
    ref,b,checked=study.validate_simulation(meta,folder)
    selected,_=study.selection(meta,b);assert len(selected)==10
    # Одиночная лезия 31 должна использовать в точности функцию из 28.
    a=lesion.trial(base,checked,50,7,selected[0]);b=study.run_trial(lesion,base,checked,[selected[0]],7)
    assert a[:2]==b[:2],(a,b)
    # Двойная лезия должна совпадать с явным обнулением выходов обеих клеток.
    modified=checked['weights'].copy()
    for rid in selected[:2]: modified[checked['pre']==checked['lookup'][rid]]=0
    altered=dict(checked);altered['weights']=modified
    a=lesion.trial(base,altered,50,9,'');b=study.run_trial(lesion,base,checked,selected[:2],9)
    assert a[:2]==b[:2],(a,b)
    assert np.array_equal(checked['weights'],data['weights'])
    # Несовпадение версий отсекается до расчёта.
    wrong=dict(meta);wrong['numpy']='wrong'
    try: study.validate_simulation(wrong,folder);raise AssertionError('другая версия принята')
    except ValueError as e: assert 'не совпадают' in str(e)
    print('validated inputs and actual synthetic single/double lesions: ok')

if __name__=='__main__': main()
