"""Read-only folder selection diagnostics against a generated local 51 result."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

root=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
base=load('selector_baseline',root/'experiments/templates/51_two_flies_user_trajectory_learning.py')
selector=load('selector60',root/'experiments/templates/60_long_wing_folder_selector.py')
examples=root/'experiments/examples/wing-user-training'

def failed(fn,*fragments):
    try:fn()
    except ValueError as exc:
        for fragment in fragments:assert fragment in str(exc),str(exc)
    else:raise AssertionError('invalid folder accepted')

with tempfile.TemporaryDirectory() as d:
    tmp=Path(d);folder=base.run([examples/'train-a.json',examples/'train-b.json'],[examples/'test-a.json'],tmp/'runs')
    before={p.relative_to(folder):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
    report=selector.check_previous(folder)
    assert report['folder']==str(folder.resolve()) and report['train_count']==2 and report['test_count']==1
    result=subprocess.run([sys.executable,str(root/'experiments/templates/60_long_wing_folder_selector.py'),'--check-old',str(folder)],cwd=root,capture_output=True,text=True,timeout=30)
    assert result.returncode==0, result.stderr
    assert json.loads(result.stdout)['model_sha256']==report['model_sha256']
    failed(lambda:selector.check_previous(folder/'input'),'Не найден файл metadata.json',str((folder/'input').resolve()),str(folder.resolve()),'родительская')
    failed(lambda:selector.check_previous(folder/'test_001'),'Не найден файл model_six_axes.npz','родительская')
    failed(lambda:selector.check_previous(tmp/'missing'),'не существует')
    marker=folder/'INCOMPLETE.txt';marker.write_text('unfinished')
    failed(lambda:selector.check_previous(folder),'INCOMPLETE.txt');marker.unlink()
    model=folder/'model_six_axes.npz';orig=model.read_bytes();model.write_bytes(orig+b'changed')
    failed(lambda:selector.check_previous(folder),'SHA',str(folder));model.write_bytes(orig)
    manifest=folder/'input_manifest.json';orig=manifest.read_bytes();manifest.write_bytes(orig+b' ')
    failed(lambda:selector.check_previous(folder),'input_manifest.json','SHA');manifest.write_bytes(orig)
    old=folder/'input/train_001.json';orig=old.read_bytes();old.write_bytes(orig+b' ')
    failed(lambda:selector.check_previous(folder),'train_001.json','манифеста');old.write_bytes(orig)
    # Mock dialogs to test retry and the exact subprocess arguments; not a Windows GUI test.
    events=[]; selections=iter([str(folder/'input'),str(folder)])
    class Window:
        def withdraw(self):pass
        def attributes(self,*a):pass
        def destroy(self):events.append('destroy')
    dialogs=SimpleNamespace(askdirectory=lambda **kw:next(selections),
                            askopenfilenames=lambda **kw:[str(examples/'test-a.json')])
    boxes=SimpleNamespace(showinfo=lambda *a,**kw:None,
                          askretrycancel=lambda *a,**kw:events.append(('retry',a[1])) or True,
                          askyesno=lambda *a,**kw:events.append(('confirm',a[1])) or True,
                          askyesnocancel=lambda *a,**kw:False)
    tk=SimpleNamespace(Tk=Window,filedialog=dialogs,messagebox=boxes,
                       simpledialog=SimpleNamespace(askinteger=lambda *a,**kw:1))
    with patch.dict(sys.modules,{'tkinter':tk}), patch.object(selector,'invoke',lambda *args:events.append(('invoke',args)) or 0):
        assert selector.choose()==0
    assert any(e[0]=='retry' and 'родительская' in e[1] for e in events if isinstance(e,tuple))
    assert any(e[0]=='confirm' and str(folder) in e[1] for e in events if isinstance(e,tuple))
    args=[e[1] for e in events if isinstance(e,tuple) and e[0]=='invoke'][0]
    assert args[0]=='--new' and args[2:]==('--previous',str(folder),'--fresh',str(examples/'test-a.json'),'--hours',4)
    assert events[-1]=='destroy'
    for action,flag in ((2,'--resume'),(3,'--pause')):
        events=[];dialogs.askdirectory=lambda **kw:str(folder)
        tk.simpledialog.askinteger=lambda *a,**kw:action
        with patch.dict(sys.modules,{'tkinter':tk}),patch.object(selector,'invoke',lambda *args:events.append(('invoke',args)) or 0):
            assert selector.choose()==0
        assert ('invoke',(flag,str(folder))) in events
    # Actual wrapper delegates to unmodified series 59, with paths containing spaces.
    obj=json.loads((examples/'test-a.json').read_text(encoding='utf-8'))
    obj['keyframes'][0]['angles_deg'][0]+=1
    fresh=tmp/'fresh test.json';fresh.write_text(json.dumps(obj),encoding='utf-8')
    destination=tmp/'new study';assert selector.invoke('--new',destination,'--previous',folder,'--fresh',fresh,'--fixture-limit',2)==0
    assert (destination/'result/complete.json').is_file()
    assert selector.invoke('--resume',destination)==0
    assert {p.relative_to(folder):p.read_bytes() for p in folder.rglob('*') if p.is_file()}==before
print('Folder diagnosis checked exact path, correct parent hint, baseline integrity and read-only operation.')
