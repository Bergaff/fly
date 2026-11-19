import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types

root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('gpu_cuda13',root/'colab/gpu_cuda13_pilot.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
assert module.cpp17(['-O3','-std=c++11','-std=c++14','--std=c++11'])==['-O3','-std=c++17']
cpp=types.SimpleNamespace(extra_compile_args_gcc=['-O3','-std=c++11'])
backend=types.SimpleNamespace(extra_compile_args_nvcc=['-w','-use_fast_math'])
prefs=types.SimpleNamespace(codegen=types.SimpleNamespace(cpp=cpp),devices=types.SimpleNamespace(cuda_standalone=types.SimpleNamespace(cuda_backend=backend)))
brian=types.SimpleNamespace(__version__='2.10.1',prefs=prefs)
numpy=types.SimpleNamespace(__version__='2.2.6')
old={k:sys.modules.get(k) for k in ('brian2','brian2cuda','numpy')}
sys.modules.update({'brian2':brian,'brian2cuda':types.ModuleType('brian2cuda'),'numpy':numpy})
old_argv=sys.argv;old_run=module.subprocess.run
try:
    with tempfile.TemporaryDirectory() as d:
        tmp=Path(d);script=tmp/'fly_colab.py'
        script.write_text("""import json,sys
from pathlib import Path
def main():
    assert sys.argv[1:]==['--root',str(ROOT),'--mode','gpu-pilot']
    p=ROOT/'04_Отдельные_GPU_пробы';p.mkdir();(p/'gpu_test.json').write_text(json.dumps({'status':'complete'}))
ROOT=Path(%r)
""" % str(tmp),encoding='utf8')
        module.REFERENCE_SHA256=module.digest(script)
        module.subprocess.run=lambda *args,**kwargs:types.SimpleNamespace(stdout='Cuda compilation tools, release 13.0')
        sys.argv=['gpu_cuda13_pilot.py','--script',str(script),'--root',str(tmp)]
        before=script.read_bytes();module.main();assert script.read_bytes()==before
        out=tmp/'04_Отдельные_GPU_пробы';data=json.loads((out/'gpu_test_compiler.json').read_text(encoding='utf8'))
        assert data['gpu_pilot_sha256']==module.digest(out/'gpu_test.json')
        assert data['host_compiler_flags']==['-O3','-std=c++17']
        assert data['nvcc_compiler_flags']==['-w','-use_fast_math','-std=c++17']
        assert sys.argv[0]=='gpu_cuda13_pilot.py'
finally:
    sys.argv=old_argv;module.subprocess.run=old_run
    for k,v in old.items():
        if v is None:sys.modules.pop(k,None)
        else:sys.modules[k]=v
print('CUDA 13 C++17: флаги, неизменный CPU-код, отдельная запись параметров: ok')
