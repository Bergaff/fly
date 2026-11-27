"""One-build GPU experiment: control, lesion and control again, all seed 0.

This is not the full lesion plan. It neither reads nor writes any CPU database.
"""
import argparse
import hashlib
import importlib.util
import importlib.metadata
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import time
import traceback
import uuid

REFERENCE_SHA='e169c93c9b3162bd5303172038e5129956b0e9c4ef5320d1d03ef200aba399a9'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def load_reference(path):
    if digest(path)!=REFERENCE_SHA: raise ValueError('Код базовой серии изменён; эксперимент остановлен.')
    spec=importlib.util.spec_from_file_location('fly_reference_reuse',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def with_cxx17(flags): return [x for x in flags if not x.startswith(('-std=','--std='))]+['-std=c++17']


def write_json(path,value):
    with path.open('x',encoding='utf8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())


def create_network(b2,base,data):
    """Same equations and stimulation as GPU pilot; no random seed fixed here."""
    b2.start_scope();b2.defaultclock.dt=0.1*b2.ms
    p={'v_0':-52*b2.mV,'v_rst':-52*b2.mV,'v_th':-45*b2.mV,'t_mbr':20*b2.ms,'tau':5*b2.ms,'t_rfc':2.2*b2.ms}
    eq='dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)\ndg/dt = -g / tau : volt (unless refractory)\nrfc : second'
    neurons=b2.NeuronGroup(len(data['ids']),eq,method='linear',threshold='v > v_th',reset='v = v_rst; g = 0*mV',refractory='rfc',namespace=p)
    neurons.v=p['v_0'];neurons.g=0;neurons.rfc=p['t_rfc']
    syn=b2.Synapses(neurons,neurons,'w : volt',on_pre='g += w',delay=1.8*b2.ms)
    syn.connect(i=data['pre'],j=data['post']);syn.w=data['weights']*0.275*b2.mV
    inputs=[];subgroups=[]
    for rid in base.RIGHT:
        idx=data['lookup'][rid];group=neurons[idx];subgroups.append(group);group.rfc=0*b2.ms
        inputs.append(b2.PoissonInput(group,'v',N=1,rate=100*b2.Hz,weight=0.275*250*b2.mV))
    monitor=b2.SpikeMonitor(neurons,record=False)
    return b2.Network(neurons,syn,monitor,*inputs),syn,monitor,subgroups


def run_sequence(b2,base,data,build,output,expected=None,backend_name='cuda_standalone'):
    import numpy as np
    target=expected['target'] if expected else next(x for x in data['ids'] if x not in base.RIGHT and x not in base.MN9.values())
    mask=data['pre']==data['lookup'][target];affected=int(np.count_nonzero(mask))
    if affected==0: raise ValueError('Выбранная клетка не имеет исходящих связей в модели; для этой проверки нужна другая.')
    b2.set_device(backend_name,directory=str(build),build_on_run=False)
    # Keep subgroup references alive across device.run calls (Brian keeps weak owners).
    network,syn,monitor,subgroups=create_network(b2,base,data)
    b2.seed(0);network.run(1000*b2.ms,namespace={})
    start=time.perf_counter();print('Компилируем модель один раз. Это может занять несколько минут.',flush=True)
    b2.device.build(directory=str(build),compile=True,run=False,with_output=True)
    compile_seconds=time.perf_counter()-start
    write_json(output/'01_compilation.json',{'compilation_seconds':round(compile_seconds,3),'target':target,'seed':0,'affected_outgoing_synapses':affected})
    print('Компиляция завершена за',round(compile_seconds,1),'с.',flush=True)
    base_weights=data['weights']*0.275*b2.mV
    lesion_weights=data['weights'].copy();lesion_weights[mask]=0;lesion_weights=lesion_weights*0.275*b2.mV
    trials=[];baseline=None
    for i,(name,run_args) in enumerate([('control',None),('lesion',{syn.w:lesion_weights}),('control_restored',{syn.w:base_weights})],1):
        print(f'{i}/3: {name}, seed 0; сеть создаётся заново без компиляции.',flush=True)
        started=time.perf_counter()
        b2.device.run(directory=str(build),run_args=run_args,with_output=True)
        elapsed=time.perf_counter()-started
        counts=(int(monitor.count[data['lookup'][base.MN9['left']]]),int(monitor.count[data['lookup'][base.MN9['right']]]))
        observed=np.asarray(syn.w[:]/b2.mV)
        if len(observed)!=len(data['weights']): raise ValueError('Не удалось проверить веса после запуска.')
        if name=='control': baseline=observed.copy();weight_check=bool(np.all(observed[mask]!=0))
        elif name=='lesion': weight_check=bool(np.all(observed[mask]==0) and np.count_nonzero(observed!=baseline)==affected)
        else: weight_check=bool(np.array_equal(observed,baseline))
        item={'condition':name,'seed':0,'target':target if name=='lesion' else '',
              'left_count':counts[0],'right_count':counts[1],'run_seconds_including_network_creation':round(elapsed,3),
              'outgoing_weight_check':weight_check}
        trials.append(item);write_json(output/f'{i+1:02d}_{name}.json',item)
        print(f'{name}: левый/правый MN9 {counts[0]}/{counts[1]}; {elapsed:.1f} с; проверка весов: {weight_check}',flush=True)
        if not weight_check: raise ValueError('Весовой контроль не пройден. Продолжение остановлено; эксперимент не годится для полной серии.')
    return {'compile_seconds':round(compile_seconds,3),'target':target,'frequency_hz':100,'trials':trials,
            'repeated_control_equal':(trials[0]['left_count'],trials[0]['right_count'])==(trials[2]['left_count'],trials[2]['right_count'])}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--script',required=True);parser.add_argument('--root',required=True);args=parser.parse_args()
    import numpy as np
    import brian2 as b2
    import brian2cuda  # register cuda standalone
    if (b2.__version__,np.__version__)!=('2.10.1','2.2.6'): raise ValueError('Нужны Brian2 2.10.1 и NumPy 2.2.6.')
    b2.prefs.codegen.cpp.extra_compile_args_gcc=with_cxx17(b2.prefs.codegen.cpp.extra_compile_args_gcc)
    backend=b2.prefs.devices.cuda_standalone.cuda_backend
    backend.extra_compile_args_nvcc=with_cxx17(backend.extra_compile_args_nvcc)
    ref=load_reference(Path(args.script));root=Path(args.root)
    if not root.is_dir(): raise ValueError('Нет папки исходных файлов на Google Диске.')
    # Директория новая, записи и промежуточные результаты не перезаписываются.
    output=root/'04_Отдельные_GPU_пробы'/('reuse_'+time.strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);output.mkdir(parents=True)
    print('Отдельная папка эксперимента:',output,flush=True)
    start={'mode':'experimental_gpu_compile_once','status':'started','script_sha256':digest(Path(__file__)),
           'reference_script_sha256':REFERENCE_SHA,'brian2':b2.__version__,'numpy':np.__version__,
           'brian2cuda':importlib.metadata.version('brian2cuda'),
           'nvcc_version':subprocess.run(['nvcc','--version'],capture_output=True,text=True,check=True).stdout.strip(),
           'gpu':subprocess.run(['nvidia-smi','--query-gpu=name,driver_version','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout.strip(),
           'python':sys.version.split()[0],'host_flags':list(b2.prefs.codegen.cpp.extra_compile_args_gcc),
           'nvcc_flags':list(backend.extra_compile_args_nvcc),'seed':0,'frequency_hz':100,
           'scope':'Одна компиляция и три запуска, только тест; результат не входит в полную CPU-серию.'}
    write_json(output/'00_start.json',start)
    try:
        with tempfile.TemporaryDirectory(prefix='fly-gpu-reuse-',dir='/content' if Path('/content').is_dir() else None) as temp:
            local=Path(temp);_,_,base,data,meta,top_env=ref.prepare(root,local,True)
            if ref.available_bytes()<4*1024**3: raise MemoryError('Менее 4 ГиБ свободной RAM перед запуском. Эксперимент остановлен.')
            target=next(x for x in meta['candidates'] if x not in base.RIGHT and x not in base.MN9.values())
            print('Выбрана клетка:',target,flush=True)
            result=run_sequence(b2,base,data,local/'compiled',output,{'target':target})
            result.update(status='complete',mode=start['mode'],protocol=meta,original_top_environment=top_env,
                          start=start,caveats=['Только seed 0 и одна клетка: биологическая и статистическая эквивалентность CPU/GPU не установлена.',
                          'Времена GPU включают создание сети и запуск, но время компиляции указано отдельно.',
                          'Повторное управление seed и смена частоты ещё не проверены; использовать для 48 240 повторов нельзя.'])
            write_json(output/'summary.json',result)
            print('Эксперимент завершён, сводка:',output/'summary.json',flush=True)
    except Exception as exc:
        write_json(output/'error.json',{'status':'error','error':f'{type(exc).__name__}: {exc}',
                                       'message':'Данные основной CPU-серии не изменялись.'})
        print(traceback.format_exc(),file=sys.stderr,flush=True);raise

if __name__=='__main__':main()
