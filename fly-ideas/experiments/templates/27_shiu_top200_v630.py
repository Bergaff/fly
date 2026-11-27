"""Пробный этап топ-200 на авторской v630 при 200 Гц, без лезий.

По умолчанию только проверка. --simulate выполняет до 30 повторов; каждый
сохранён отдельно. --resume-from позволяет продолжить незавершённый прогон.
Это не вся Figure 1D и не проверенный биологический результат.
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
import gc
import hashlib
import importlib.util
import json
import os
import sys
import time
import traceback
from pathlib import Path

BASE_SHA256 = 'b5f200a3e9472c9aa6318acab8b5fb928d23af3b458c2d43fc29909241e95711'


def hashfile(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(2*1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, value):
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def base_module():
    path = Path(__file__).parent / '25_shiu_v630_control.py'
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(raw).hexdigest() != BASE_SHA256:
        raise ValueError('25_shiu_v630_control.py изменён или имеет другую версию; автоматический расчёт остановлен.')
    spec = importlib.util.spec_from_file_location('v630_base', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def trial_counts(base, data, seed):
    import numpy as np
    import brian2 as b2
    b2.start_scope(); b2.prefs.codegen.target = 'numpy'; b2.defaultclock.dt = 0.1*b2.ms
    params = {'v_0':-52*b2.mV, 'v_rst':-52*b2.mV, 'v_th':-45*b2.mV, 't_mbr':20*b2.ms, 'tau':5*b2.ms, 't_rfc':2.2*b2.ms}
    eqs = 'dv/dt = (v_0 - v + g) / t_mbr : volt (unless refractory)\ndg/dt = -g / tau : volt (unless refractory)\nrfc : second'
    neurons = b2.NeuronGroup(len(data['ids']), eqs, method='linear', threshold='v > v_th', reset='v = v_rst; g = 0*mV', refractory='rfc', namespace=params)
    neurons.v = params['v_0']; neurons.g = 0; neurons.rfc = params['t_rfc']
    syn = b2.Synapses(neurons, neurons, 'w : volt', on_pre='g += w', delay=1.8*b2.ms)
    syn.connect(i=data['pre'], j=data['post']); syn.w = data['weights']*0.275*b2.mV
    pois = []
    for rid in base.RIGHT:
        i = data['lookup'][rid]; neurons[i].rfc = 0*b2.ms
        pois.append(b2.PoissonInput(neurons[i], 'v', N=1, rate=200*b2.Hz, weight=0.275*250*b2.mV))
    monitor = b2.SpikeMonitor(neurons, record=False)
    net = b2.Network(neurons, syn, monitor, *pois)
    b2.seed(seed); start = time.time(); net.run(1000*b2.ms, namespace={})
    counts = np.asarray(monitor.count[:], dtype=np.int64).copy()
    elapsed = round(time.time()-start, 3)
    del net, monitor, pois, syn, neurons
    gc.collect()
    return counts, elapsed


def read_checkpoint(path, expected, neurons):
    import numpy as np
    state = json.loads((path/'checkpoint.json').read_text(encoding='utf-8'))
    if state.get('protocol') != expected or not isinstance(state.get('completed'), dict):
        raise ValueError('Контрольная точка имеет другие файлы, версии или параметры; продолжение запрещено.')
    counts = {}
    for seed_text, info in state['completed'].items():
        if not seed_text.isdigit() or int(seed_text) not in range(30) or not isinstance(info, dict):
            raise ValueError('Некорректный seed в контрольной точке.')
        seed = int(seed_text); f = path / f'counts_seed_{seed:02d}.npy'
        if hashfile(f) != info.get('sha256'):
            raise ValueError(f'Контрольная сумма повтора {seed} не совпала.')
        c = np.load(f, allow_pickle=False)
        if c.dtype != np.dtype('int64') or c.shape != (neurons,) or np.any(c < 0) or np.any(c > 10000):
            raise ValueError(f'Некорректные числа спайков в повторе {seed}.')
        counts[seed] = (c, float(info['wall_seconds']))
    return counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--simulate', action='store_true')
    p.add_argument('--pilot', action='store_true', help='Только один тестовый повтор; не создаёт топ-200')
    p.add_argument('--resume-from', default='', help='Папка прежнего прогона с checkpoint.json')
    args = p.parse_args()
    run = os.environ.get('FLY_RUN_DIR', '').strip()
    if not run:
        print('FLY_RUN_DIR не задан. Запустите из приложения.', file=sys.stderr); return 2
    out = Path(run); out.mkdir(parents=True, exist_ok=True)
    summary = {'status':'pending', 'mode':'simulation' if args.simulate else 'preflight',
               'scope':'Отбор топ-200 на авторской v630 при 200 Гц, 21 правый sugar GRN; без лезий и не вся Figure 1D.',
               'args':vars(args), 'files':[], 'caveats':[
                   'Группа из 21 правого сахарного нейрона взята из авторского figures.ipynb Figure 1D. В публикации и ноутбуке есть различие по стороне.',
                   'Сохраняется число спайков всех нейронов за 1 секунду, а не полные времена. При одинаковых средних частотах используется сортировка по числовому ID.',
                   'Уравнения переписаны по авторской модели; локальное присваивание w=0 в сбросе не используется. На искусственном графе числа спайков всех нейронов совпали с неизменённым авторским ядром для одного seed; полная эквивалентность не доказана.',
                   '30 псевдослучайных повторов не являются разными животными. Одного отбора топ-200 недостаточно для воспроизведения Figure 1D или лезий.']}
    try:
        if args.pilot and (not args.simulate or args.resume_from):
            raise ValueError('Режим пилота требует --simulate и не принимает --resume-from.')
        import numpy as np
        import brian2 as b2
        base = base_module()
        summary['author_source'] = base.SOURCE
        conn = base.input_file('FLY_SHIU_CONNECTIONS', '.parquet'); neurons = base.input_file('FLY_SHIU_NEURONS', '.csv')
        print('Проверяем исходные авторские файлы...', flush=True)
        hashes = {'connections':base.fingerprint(conn), 'neurons':base.fingerprint(neurons)}
        summary['inputs'] = hashes
        if any(hashes[k]['git_blob_sha1'] != v for k,v in base.EXPECTED.items()):
            raise ValueError('Файлы не совпадают с авторской v630.')
        print('Проверяем все индексы и веса...', flush=True)
        data = base.validate_inputs(conn, neurons, args.simulate)
        for key, file in [('connections',conn), ('neurons',neurons)]:
            st=file.stat(); before=hashes[key]
            if (st.st_size,st.st_mtime_ns)!=(before['bytes'],before['mtime_ns']):
                raise ValueError(f'Файл изменился: {file}')
        summary['data_check']={'neurons':len(data['ids']), 'connections':data['rows'], 'stimulation_ids':base.RIGHT}
        protocol={'schema':1,'connection_sha256':hashes['connections']['sha256'], 'neuron_sha256':hashes['neurons']['sha256'],
                  'script_sha256':hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
                  'base_sha256':BASE_SHA256, 'python':sys.version.split()[0], 'brian2':b2.__version__, 'numpy':np.__version__,
                  'side':'right','frequency_hz':200,'duration_ms':1000,'dt_ms':0.1,'seeds':list(range(30))}
        summary['protocol']=protocol
        if not args.simulate:
            summary['status']='preflight_complete'; code=0
        else:
            counts = {}
            if args.resume_from:
                source=Path(args.resume_from)
                if source.resolve() == out.resolve():
                    raise ValueError('Папка продолжения должна отличаться от новой папки прогона.')
                counts=read_checkpoint(source, protocol, len(data['ids']))
                print(f'Проверено и восстановлено повторов: {len(counts)} из 30.', flush=True)
            checkpoint={'protocol':protocol, 'completed':{}}
            atomic_json(out/'checkpoint.json',checkpoint)
            total=np.zeros(len(data['ids']),dtype=np.int64)
            for seed in range(1 if args.pilot else 30):
                if seed in counts:
                    c, elapsed = counts[seed]
                else:
                    print(f'Топ-200: повтор {seed+1}/30, seed {seed}.', flush=True)
                    c,elapsed = trial_counts(base, data, seed)
                target=out/f'counts_seed_{seed:02d}.npy'; temp=out/f'.counts_seed_{seed:02d}.tmp'
                with temp.open('wb') as f:
                    np.save(f,c,allow_pickle=False); f.flush(); os.fsync(f.fileno())
                os.replace(temp,target)
                checkpoint['completed'][str(seed)]={'sha256':hashfile(target),'wall_seconds':elapsed}
                atomic_json(out/'checkpoint.json',checkpoint)
                total += c
                print(f'Сохранено повторов: {seed+1}/30.', flush=True)
            if args.pilot:
                summary['status']='pilot_complete'
                summary['result']={'completed_seeds':[0], 'trials':1, 'active_neurons':int(np.count_nonzero(total)),
                                   'left_mn9_rate_hz':int(total[data['lookup'][base.MN9['left']]]),
                                   'right_mn9_rate_hz':int(total[data['lookup'][base.MN9['right']]])}
                summary['files']=['checkpoint.json']
                code=0
            else:
                # Только нейроны с ненулевой активностью. В случае равных частот применяется числовой ID.
                active=np.flatnonzero(total>0)
                order=sorted(active.tolist(), key=lambda i:(-int(total[i]),int(data['ids'][i])))
                if len(order)<200:
                    raise ValueError(f'Активных нейронов только {len(order)}; нельзя создать топ-200.')
                import csv
                with (out/'top200.csv').open('w',encoding='utf-8-sig',newline='') as f:
                    w=csv.writer(f); w.writerow(['rank','root_id','mean_rate_hz','total_spikes_30_trials'])
                    for rank,i in enumerate(order[:200],1): w.writerow([rank,data['ids'][i],int(total[i])/30,int(total[i])])
                summary['status']='ok'; summary['result']={'active_neurons':len(order),'trials':30,'top200_file':'top200.csv',
                    'cutoff_rate_hz':int(total[order[199]])/30,'completed_seeds':list(range(30))}
                summary['files']=['top200.csv','checkpoint.json']; code=0
    except Exception as exc:
        summary['status']='error'; summary['error']=f'{type(exc).__name__}: {exc}'; code=1
        print(traceback.format_exc(), file=sys.stderr,flush=True)
    atomic_json(out/'summary.json',summary)
    print(f'Топ-200: {summary["status"]}. Отчёт: {out / "summary.json"}',flush=True)
    return code


if __name__ == '__main__':
    sys.exit(main())
