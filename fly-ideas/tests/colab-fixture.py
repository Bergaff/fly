import importlib.util
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys


def load(path):
    spec=importlib.util.spec_from_file_location('colab_impl',path);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m);return m


def main():
    repo=Path(__file__).resolve().parents[1];temp=Path(sys.argv[1]);source=temp/'source';source.mkdir()
    fixture=repo/'tests/shiu-lesions-fixture.py';prefix=fixture.read_text(encoding='utf8').split('# Маленький план для проверки транзакций')[0]
    saved=sys.argv;sys.argv=['fixture',str(source)];scope={'__file__':str(fixture),'__name__':'fixture_prefix'};exec(compile(prefix,str(fixture),'exec'),scope);sys.argv=saved
    lesion,top,base=scope['lesion'],scope['top'],scope['base'];mod=load(repo/'colab/fly_colab.py')
    mod.load_reference=lambda:(lesion,top,base)
    root=temp/'drive';inputs=root/'01_Исходные_файлы';inputs.mkdir(parents=True)
    shutil.copyfile(scope['conn'],inputs/mod.CONNECTION);shutil.copyfile(scope['comp'],inputs/mod.NEURONS)
    shutil.copytree(scope['folder'],inputs/'top200')
    # Топ выполнен в другой версии Python: его собственные версии сохраняются,
    # но сам рейтинг и суммы по всем 30 массивам проверяются независимо.
    summary_path=inputs/'top200'/'summary.json';checkpoint_path=inputs/'top200'/'checkpoint.json'
    summary=json.loads(summary_path.read_text(encoding='utf8'));checkpoint=json.loads(checkpoint_path.read_text(encoding='utf8'))
    summary['protocol']['python']='3.12.0';checkpoint['protocol']['python']='3.12.0'
    summary_path.write_text(json.dumps(summary),encoding='utf8');checkpoint_path.write_text(json.dumps(checkpoint),encoding='utf8')
    work=temp/'work';work.mkdir()
    _,_,_,data,meta,old=mod.prepare(root,work,True)
    assert old['python']=='3.12.0' and len(meta['candidates'])==200 and len(data['pre'])>0
    # Один настоящий контроль Brian2 на малой сети с тем же кодом 28.
    mod._BASE=base;mod._DATA=data;mod._LESION=lesion
    actual=mod.worker((100,'',0));assert len(actual)==3 and all(x>=0 for x in actual)
    # Проверяем конструкцию экспериментальной модели с NumPy на малой сети.
    # Это НЕ тест CUDA или GPU и не подтверждает их эквивалентность.
    import brian2 as b2, types
    old_set_device=b2.set_device;sys.modules['brian2cuda']=types.ModuleType('brian2cuda')
    b2.set_device=lambda *args,**kwargs:None;b2.prefs.codegen.target='numpy'
    try:
        gpu_structure=mod.gpu_trial(base,data,100,0,'',temp/'build-control');assert gpu_structure[:2]==actual[:2]
        target=meta['candidates'][0];reference=lesion.trial(base,data,100,0,target)
        gpu_structure=mod.gpu_trial(base,data,100,0,target,temp/'build-lesion');assert gpu_structure[:2]==reference[:2]
    finally: b2.set_device=old_set_device;sys.modules.pop('brian2cuda',None)
    # Результаты всех остальных повторов фиктивные: проверяем очередь, запись и resume.
    lesion.trial=lambda _b,_d,f,s,t:(f+s+len(t),s+len(t),0.01)
    prepared=(lesion,top,base,data,meta,old);mod.prepare=lambda *_:prepared;mod.available_bytes=lambda:10*1024**3
    run1=temp/'run1';run1.mkdir();mod.cpu_series(root,run1,2,2,3)
    folder=root/'02_CPU_полный_план'/'checkpoints';records,last=mod.checkpoint_list(folder);assert len(records)==3 and records[last]['rows']==3
    run2=temp/'run2';run2.mkdir();mod.cpu_series(root,run2,2,2,2)
    records,last=mod.checkpoint_list(folder);assert records[last]['rows']==5
    # Неопубликованная метка не меняет историю; повреждённая опубликованная блокирует продолжение.
    (folder/'checkpoint_unfinished.pending').write_text('partial',encoding='utf8')
    assert mod.checkpoint_list(folder)[1]==last
    (folder/'checkpoint_broken.json').write_text('{',encoding='utf8')
    try: mod.checkpoint_list(folder);raise AssertionError('повреждённая метка проигнорирована')
    except ValueError as e: assert 'повреждена' in str(e)
    (folder/'checkpoint_broken.json').unlink()
    view=load(repo/'experiments/templates/30_shiu_lesion_overview.py');view.reference=lambda:lesion
    view.CONNECTION_SHA=meta['connection_sha256'];view.NEURON_SHA=meta['neuron_sha256'];mod.load_overview=lambda:view
    export=temp/'export';export.mkdir();mod.export_latest(root,export)
    exported=list((root/'05_Экспорт_для_приложения').glob('*/lesions.sqlite3'));assert len(exported)==1 and len(view.read_checked(exported[0])[1])==5
    restore=temp/'restore';restore.mkdir();db=mod.restore_snapshot(folder,last,records[last],restore,lesion,meta)
    rows=db.execute('SELECT frequency,target,seed,left_count,right_count,wall_seconds,digest FROM trials').fetchall();assert len(rows)==5
    for f,t,s,l,r,w,digest in rows:
        assert l==f+s+len(t) and r==s+len(t) and digest==lesion.row_hash(f,t,s,l,r,w)
    # Другая версия Python или параметры не должны молча смешиваться.
    wrong=dict(meta,python='9.9.9');other=temp/'mismatch';other.mkdir()
    try: mod.restore_snapshot(folder,last,records[last],other,lesion,wrong);raise AssertionError('разные версии смешаны')
    except ValueError as e: assert 'другими' in str(e)
    # Две ветви истории не объединяются автоматически.
    branch=dict(records[last],id='checkpoint_fork',parent=records[last]['parent']);(folder/'checkpoint_fork.json').write_text(json.dumps(branch),encoding='utf8')
    try: mod.checkpoint_list(folder);raise AssertionError('ветви не обнаружены')
    except ValueError as e: assert 'ветки' in str(e)
    (folder/'checkpoint_fork.json').unlink()
    archive=folder/(last+'.sqlite.gz');saved_bytes=archive.read_bytes();archive.write_bytes(saved_bytes+b'x')
    corrupt=temp/'corrupt';corrupt.mkdir()
    try: mod.restore_snapshot(folder,last,records[last],corrupt,lesion,meta);raise AssertionError('повреждённый снимок принят')
    except ValueError as e: assert 'повреждён' in str(e)
    archive.write_bytes(saved_bytes);db.close()
    # Повреждение входного топа обнаруживается до создания базы.
    (inputs/'top200'/'counts_seed_00.npy').write_bytes(b'bad')
    bad=temp/'bad';bad.mkdir()
    # Восстанавливаем настоящую функцию подготовки после stub.
    mod=load(repo/'colab/fly_colab.py');mod.load_reference=lambda:(lesion,top,base)
    try: mod.prepare(root,bad,False);raise AssertionError('повреждённый топ принят')
    except ValueError as e: assert 'сумма' in str(e)
    print('Colab CPU: provenance, real Brian2, snapshots, resume, forks and corruption: ok')

if __name__=='__main__':main()
