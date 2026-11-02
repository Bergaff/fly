"""Experimental C++17 wrapper for the existing Colab GPU pilot, never CPU resume."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

REFERENCE_SHA256='e169c93c9b3162bd5303172038e5129956b0e9c4ef5320d1d03ef200aba399a9'


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def cpp17(flags):
    return [f for f in flags if not f.startswith(('-std=', '--std='))]+['-std=c++17']


def configure():
    import brian2cuda  # registers preferences
    import brian2 as b2
    import numpy as np
    if (b2.__version__,np.__version__)!=('2.10.1','2.2.6'):
        raise ValueError('Проба требует Brian2 2.10.1 и NumPy 2.2.6.')
    b2.prefs.codegen.cpp.extra_compile_args_gcc=cpp17(b2.prefs.codegen.cpp.extra_compile_args_gcc)
    backend=b2.prefs.devices.cuda_standalone.cuda_backend
    backend.extra_compile_args_nvcc=cpp17(backend.extra_compile_args_nvcc)
    return b2,np,list(b2.prefs.codegen.cpp.extra_compile_args_gcc),list(backend.extra_compile_args_nvcc)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--script',required=True);parser.add_argument('--root',required=True);args=parser.parse_args()
    script=Path(args.script).resolve();root=Path(args.root).resolve()
    if digest(script)!=REFERENCE_SHA256: raise ValueError('Код исходной серии не совпадает с проверенной версией; проба остановлена.')
    b2,np,host_flags,nvcc_flags=configure()
    print('Эксперимент CUDA 13: C++17 включён для nvcc и компилятора CPU.',flush=True)
    print('Флаги CPU:',host_flags,flush=True);print('Флаги nvcc:',nvcc_flags,flush=True)
    nvcc=subprocess.run(['nvcc','--version'],capture_output=True,text=True,check=True).stdout.strip()
    out=root/'04_Отдельные_GPU_пробы'
    before=set(out.glob('gpu_*.json')) if out.is_dir() else set()
    spec=importlib.util.spec_from_file_location('fly_colab_gpu_reference',script)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    saved=sys.argv
    try:
        sys.argv=[str(script),'--root',str(root),'--mode','gpu-pilot']
        module.main()
    finally: sys.argv=saved
    new=set(out.glob('gpu_*.json'))-before
    if len(new)!=1:
        raise ValueError('Не удалось однозначно найти результат GPU: файлы не изменены, проверьте папку вручную.')
    report=new.pop();record=report.with_name(report.stem+'_compiler.json')
    info={'kind':'fly-colab-experimental-gpu-compiler-1','gpu_pilot_file':report.name,'gpu_pilot_sha256':digest(report),
          'reference_script_sha256':REFERENCE_SHA256,'wrapper_sha256':digest(Path(__file__)),
          'brian2_version':b2.__version__,'numpy_version':np.__version__,'python_version':sys.version.split()[0],
          'host_compiler_flags':host_flags,'nvcc_compiler_flags':nvcc_flags,'nvcc_version_output':nvcc,
          'caveat':'Отдельный экспериментальный GPU-пилот; не смешивается с CPU-серией. Эквивалентность не установлена.'}
    with record.open('x',encoding='utf8') as f:json.dump(info,f,ensure_ascii=False,indent=2)
    print('Параметры компиляции сохранены отдельно:',record,flush=True)

if __name__=='__main__':main()
