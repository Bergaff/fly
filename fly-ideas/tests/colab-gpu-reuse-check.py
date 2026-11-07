"""Real small C++ standalone test, not a CUDA test."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import json
import numpy as np
import brian2 as b2

path=Path(__file__).resolve().parents[1]/'colab'/'gpu_reuse_pilot.py'
spec=importlib.util.spec_from_file_location('reuse_pilot',path)
pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
assert pilot.with_cxx17(['-std=c++11','-use_fast_math'])==['-use_fast_math','-std=c++17']
base=SimpleNamespace(RIGHT=[0],MN9={'left':3,'right':4})
data={'ids':[0,1,2,3,4],'lookup':{n:n for n in range(5)},
      'pre':np.array([0,2,2,1],dtype=np.int32),
      'post':np.array([2,3,4,3],dtype=np.int32),
      'weights':np.array([500,500,500,5],dtype=np.int32)}
with TemporaryDirectory(prefix='reuse-test-') as temp:
    root=Path(temp);out=root/'results';out.mkdir()
    result=pilot.run_sequence(b2,base,data,root/'build',out,{'target':2},backend_name='cpp_standalone')
    assert result['repeated_control_equal']
    assert result['trials'][0]['left_count']>0 and result['trials'][0]['right_count']>0
    assert result['trials'][1]['left_count']==0 and result['trials'][1]['right_count']==0
    assert [x['condition'] for x in result['trials']]==['control','lesion','control_restored']
    assert all(x['outgoing_weight_check'] for x in result['trials'])
    assert json.loads((out/'01_compilation.json').read_text())['affected_outgoing_synapses']==2
print('Малая Brian2 C++ standalone сеть и три запуска проверены; CUDA не проверен.')
