#!/usr/bin/env python3
"""Pixel-permutation controls for the fixed two-flies visual toy network."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
BRIDGE_SHA = '2bbda0cb87d1be2ab3dbddb9a57505741369758791e768d639b35d19dc9dc27c'
SEED = 20261106


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bridge_module():
    path=HERE/'42_two_flies_motor_bridge.py'
    if sha(path)!=BRIDGE_SHA: raise ValueError('Скрипт 42 не соответствует закреплённой версии.')
    spec=importlib.util.spec_from_file_location('matched_bridge',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def scramble(frames, tilewise, seed=SEED):
    """One fixed pixel permutation per region, applied to every frame, eye and RGB channel."""
    n,eyes,h,w,channels=frames.shape
    if eyes!=2 or channels!=3 or h%4 or w%4: raise ValueError('Некорректная форма кадров.')
    out=np.empty_like(frames);rng=np.random.default_rng(seed)
    for row in range(4 if tilewise else 1):
        for col in range(4 if tilewise else 1):
            hh=h//4 if tilewise else h;ww=w//4 if tilewise else w
            y=row*hh;x=col*ww
            pixels=frames[:,:,y:y+hh,x:x+ww,:].reshape(n,eyes,hh*ww,3)
            out[:,:,y:y+hh,x:x+ww,:]=pixels[:,:,rng.permutation(hh*ww),:].reshape(n,eyes,hh,ww,3)
    return out


def rgb_hist_matches(a,b):
    # RGB triples are compared within each eye and each frame, exactly.
    def packed(x):
        x=x.astype(np.uint32)
        return (x[...,0]<<16)|(x[...,1]<<8)|x[...,2]
    a=packed(a).reshape(a.shape[0],2,-1);b=packed(b).reshape(b.shape[0],2,-1)
    return np.all(np.sort(a,axis=-1)==np.sort(b,axis=-1),axis=-1)


def motion_sums(frames):
    # Integer sum of per-pixel absolute RGB-mean differences, up to factor 1/3.
    lum=frames.astype(np.int16).sum(axis=-1)
    delta=np.abs(np.diff(lum,axis=0,prepend=lum[:1])).astype(np.int64)
    return delta.sum(axis=(2,3))


def preview(frames,path):
    images=[Image.fromarray(np.concatenate((f[0],f[1]),axis=1)) for f in frames]
    images[0].save(path,save_all=True,append_images=images[1:],duration=20,loop=0,optimize=False)


def run(source, make_gif=True):
    bridge=bridge_module()
    source,engine,mapping,originals,digests=bridge.load_source(source)
    wings=originals['wing_3hz_0deg']['frames']; stationary=originals['wing_stationary']['frames']; obj=originals['object_3hz_0deg']['frames'];n=len(wings)
    cases=[('wings',wings),('stationary',stationary),('reverse',wings[::-1].copy()),('tile_scramble',scramble(wings,True)),('global_scramble',scramble(wings,False)),('object_unmatched',obj)]
    # Validate directly on lossless RGB arrays, before producing output.
    for name,frames in cases:
        if name in ('wings','tile_scramble','global_scramble'):
            if not np.all(rgb_hist_matches(wings,frames)) or not np.array_equal(motion_sums(wings),motion_sums(frames)):
                raise ValueError(f'Контроль {name}: не сохранились глобальные характеристики изображений.')
        if name=='reverse':
            expected=np.concatenate([np.zeros((1,2),dtype=np.int64),motion_sums(wings)[1:][::-1]])
            if not np.all(rgb_hist_matches(wings[::-1],frames)) or not np.array_equal(motion_sums(frames),expected):
                raise ValueError('Обратный порядок кадров не прошёл проверку.')
    ref_features=engine.features(wings)
    tile_features=engine.features(dict(cases)['tile_scramble'])
    max_feature_error=float(np.max(np.abs(ref_features-tile_features)))
    if max_feature_error>1e-6: raise ValueError('Перемешивание внутри областей изменило вход нейронов более чем на 1e-6.')
    dest=source/('matched_controls_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:8]);dest.mkdir()
    meta=dict(status='running',created_utc=datetime.now(timezone.utc).isoformat(),input_directory=str(source),input_sha256=digests,
        engine_sha256=bridge.ENGINE_SHA,source_series_sha256=bridge.SOURCE_SHA,bridge_sha256=BRIDGE_SHA,script_sha256=sha(__file__),
        python=platform.python_version(),versions={p:importlib.metadata.version(p) for p in ('numpy','mujoco','brian2','pillow')},
        fps=50,duration_s=2,seed=SEED,initial_seed=0,integration_dt_ms=1,feature_max_abs_difference_tile_scramble=max_feature_error,
        conditions=[x[0] for x in cases],match_checks='Exact RGB histograms per eye/frame and exact absolute luminance difference sums per eye/frame for the two spatial permutations; reverse pairs transitions in opposite order. Tile neural input checked within 1e-6.',
        limitations='32 artificial LIF cells respond to absolute per-tile luminance changes; no direction selectivity, motor dynamics, learning, anatomical cells or biological replicates. Spatial permutations destroy natural spatial correlations and are not plausible flies; only stated statistics are matched.')
    (dest/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
    data={}
    for name,frames in cases:
        feat=engine.features(frames);times,ids,drive=engine.simulate(feat,1/50,0)
        counts=np.bincount(ids,minlength=32);sub=dest/name;sub.mkdir()
        np.savez_compressed(sub/'neural_input.npz',neural_input=frames,source_frame=np.arange(n-1,-1,-1) if name=='reverse' else np.arange(n))
        bridge.save_csv(sub/'spikes.csv',['time_s','neuron_id'],((float(t),int(i)) for t,i in zip(times,ids)))
        bridge.save_csv(sub/'visual_input.csv',['frame','time_s','neuron_id','motion_abs_diff','drive'],((k,k/50,i,float(feat[k,i]),float(drive[k,i])) for k in range(n) for i in range(32)))
        if make_gif:preview(frames,sub/'observer_input.gif')
        data[name]=dict(features=feat,counts=counts,spikes=len(ids),motion=motion_sums(frames))
        print(f'{name}: {len(ids)} спайков; средний вход {feat.mean():.8f}',flush=True)
    reference=data['wings'];summary=[];neurons=[];metrics=[]
    for name,frames in cases:
        result=data[name];hist=rgb_hist_matches(wings[::-1] if name=='reverse' else wings,frames)
        for k in range(n):
            comparison=n-k if name=='reverse' and k else k
            for eye in range(2):
                metrics.append((name,k,eye,int(hist[k,eye]),int(result['motion'][k,eye]),int(reference['motion'][comparison,eye]),comparison))
        summary.append((name,result['spikes'],float(result['features'].mean()),result['spikes']-reference['spikes'],float(np.max(np.abs(result['features']-reference['features']))),bool(np.all(hist))))
        for i in range(32):
            neurons.append((name,i,mapping[i]['eye'],mapping[i]['tile_row'],mapping[i]['tile_col'],int(result['counts'][i]),int(reference['counts'][i]),int(result['counts'][i]-reference['counts'][i]),float(result['features'][:,i].mean()),float(reference['features'][:,i].mean()),float(np.max(np.abs(result['features'][:,i]-reference['features'][:,i])))))
    bridge.save_csv(dest/'conditions_summary.csv',['condition','spikes','mean_motion_abs_diff','spike_difference_vs_wings','max_frame_neuron_feature_difference_vs_wings','same_rgb_histograms_as_paired_wings'],summary)
    bridge.save_csv(dest/'neuron_comparison.csv',['condition','neuron_id','eye','tile_row','tile_col','spikes','wings_spikes','spike_difference','mean_motion_abs_diff','wings_mean_motion_abs_diff','max_frame_feature_difference'],neurons)
    bridge.save_csv(dest/'image_matching.csv',['condition','frame','eye_index','same_rgb_histogram','abs_luminance_diff_sum_x3','wings_abs_luminance_diff_sum_x3','paired_wings_transition_frame'],metrics)
    (dest/'report.txt').write_text('''КОНТРОЛИ ЗРИТЕЛЬНОГО ВХОДА\n\nwings: исходные кадры, stationary: неподвижные крылья, reverse: кадры в обратном порядке; tile_scramble: перестановка пикселей отдельно внутри каждого из 4×4 участков, global_scramble: одна перестановка по всему изображению глаза. Одна фиксированная перестановка применяется ко всем кадрам, обоим глазам и всем каналам RGB. object_unmatched: прежний движущийся объект, он не уравнен с крыльями. Исходный файл не изменяется.\n\nДля пространственных перестановок проверены точное совпадение гистограммы RGB в каждом глазу и кадре и совпадение суммы абсолютных изменений яркости между соседними кадрами в каждом глазу. В tile_scramble также проверено совпадение входов всех 32 искусственных нейронов с точностью 1e-6; различия меньше порога могут возникать из-за порядка суммирования. Для reverse сохранены те же переходы, но в обратном порядке; сравнивайте с парным номером перехода. Нулевой первый кадр не имеет предшественника. У object и stationary совпадение не предполагается.\n\nimage_matching.csv содержит проверенные глобальные величины для каждого кадра и глаза. neuron_comparison.csv: каждый ID, спайки и разность с wings; visual_input.csv и spikes.csv содержат входы по кадрам и все события каждого ID, neural_input.npz содержит точные RGB, GIF только для просмотра. Порядок источника указан в NPZ.\n\nЭто не реалистичные контрольные изображения и не проверки биологических зеркальных нейронов: перестановка разрушает формы, соседство пикселей и локальную пространственную статистику. Совпадение глобальных показателей не означает одинаковый вход каждого нейрона. Модель непосредственно использует абсолютную разницу яркости по областям, без чувствительности к знаку или направлению движения; совпадение входов при tile_scramble ожидается по конструкции. Временной порядок и начальные условия могут менять результат reverse. Одно детерминированное моделирование, без биологических повторов и статистических тестов, без обучения и моторного поведения.\n''',encoding='utf-8-sig')
    if any(sha(source/f)!=value for f,value in digests.items()):raise ValueError('Исходные файлы изменились во время расчёта; результат неполон.')
    meta['status']='completed';meta['finished_utc']=datetime.now(timezone.utc).isoformat();(dest/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
    print('RESULT_DIR='+str(dest),flush=True)
    return dest


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run');parser.add_argument('--choose',action='store_true');args=parser.parse_args();source=args.run
    if args.choose:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw();root.attributes('-topmost',True)
        try:source=filedialog.askdirectory(title='Выберите завершённую папку visual_controls_...',initialdir=str(Path('workspace/runs/ideas/i-observational/visual-controls').resolve()))
        finally:root.destroy()
        if not source:print('Выбор отменён.');return
    if not source:parser.error('Нужно указать --run или --choose')
    dest=run(source)
    if args.choose and os.name=='nt':os.startfile(str(dest))


if __name__=='__main__':
    try:main()
    except Exception as e:print(f'ОШИБКА: {e}',file=sys.stderr,flush=True);sys.exit(1)
