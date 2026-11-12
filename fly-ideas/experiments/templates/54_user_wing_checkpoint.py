#!/usr/bin/env python3
"""Transactional checkpoint primitives for the planned long user-wing study.

This module is NOT a runner. The caller must hold an exclusive OS run lock,
validate/freeze protocol and inputs, render/train, enforce resource and time
limits, orchestrate pause/evaluation, and provide a Windows interface.
"""
from __future__ import annotations
import hashlib
import io
import json
import math
import re
import sqlite3
import zipfile
from pathlib import Path
import numpy as np

DIM=576
MAX_SOURCE=32*1024*1024
MAX_TOTAL=64*1024*1024
DIGEST=re.compile(r'^[0-9a-f]{64}$')
NAME=re.compile(r'^[a-zA-Z0-9_.-]{1,96}$')
SHAPES={'sx':(DIM,), 'sx2':(DIM,), 'sy':(6,), 'sxy':(DIM,6), 'sxx':(DIM,DIM)}


def sha(data):return hashlib.sha256(data).hexdigest()
def canonical(obj):return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)

def empty_stats():
    return {'n':0, **{key:np.zeros(shape,dtype=np.float64) for key,shape in SHAPES.items()}}

def valid_stats(stats):
    if set(stats)!=set(SHAPES)|{'n'} or isinstance(stats['n'],(bool,np.bool_)) or not isinstance(stats['n'],(int,np.integer)) or not 0<=int(stats['n'])<2**63:
        raise ValueError('Некорректное число кадров в статистиках.')
    for key,shape in SHAPES.items():
        value=np.asarray(stats[key])
        if value.shape!=shape or value.dtype.kind!='f' or not np.isfinite(value).all():raise ValueError(f'Некорректные статистики {key}.')

def pack_stats(stats):
    valid_stats(stats);mem=io.BytesIO()
    np.savez_compressed(mem,n=np.array(stats['n'],dtype=np.int64),**{key:np.asarray(stats[key],dtype=np.float64) for key in SHAPES})
    return mem.getvalue()

def unpack_stats(blob,expected):
    if len(blob)>MAX_SOURCE or sha(blob)!=expected:raise ValueError('SHA статистик не совпадает или архив слишком велик.')
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if sum(item.file_size for item in z.infolist()) > MAX_TOTAL:raise ValueError('Распакованные статистики слишком велики.')
    with np.load(io.BytesIO(blob),allow_pickle=False) as z:
        if set(z.files)!=set(SHAPES)|{'n'} or z['n'].shape!=() or z['n'].dtype.kind not in 'iu':raise ValueError('Некорректный архив статистик.')
        result={'n':int(z['n']),**{key:np.array(z[key],copy=True) for key in SHAPES}}
    valid_stats(result);return result


def connect(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=rw',uri=True,timeout=30,isolation_level=None)
    db.execute('PRAGMA synchronous=FULL')
    db.execute('PRAGMA busy_timeout=30000')
    return db


def create(path,protocol,sources):
    """Create a new database only; leave existing paths untouched on failure.

    protocol and source bytes must already have been validated by the caller.
    Source IDs are labels, never filesystem paths; data remain within SQLite.
    """
    path=Path(path);protocol_text=canonical(protocol)
    if not isinstance(protocol,dict) or not sources or not isinstance(sources,dict):raise ValueError('Нужны протокол и исходные данные.')
    if len(protocol_text.encode())>1024*1024 or len(sources)>80:raise ValueError('Протокол или список исходных данных слишком велик.')
    total=0;items=[]
    for name,data in sorted(sources.items()):
        if not isinstance(name,str) or not NAME.fullmatch(name) or not isinstance(data,bytes) or len(data)>MAX_SOURCE:raise ValueError('Некорректный исходный файл или его имя.')
        total+=len(data);items.append((name,data,sha(data)))
    if total>MAX_TOTAL:raise ValueError('Исходные данные слишком велики.')
    if protocol.get('source_sha256')!={name:digest for name,_,digest in items}:
        raise ValueError('Контрольные суммы источников не закреплены в протоколе.')
    path.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation avoids replacing an existing DB, even under concurrent starts.
    with path.open('xb'):pass
    db=connect(path)
    try:
        db.execute('PRAGMA journal_mode=DELETE');db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        db.execute('CREATE TABLE sources (name TEXT PRIMARY KEY, payload BLOB NOT NULL, sha256 TEXT NOT NULL)')
        db.execute('CREATE TABLE state (id INTEGER PRIMARY KEY CHECK(id=1), next_id INTEGER NOT NULL, elapsed REAL NOT NULL, stats BLOB NOT NULL, stats_sha256 TEXT NOT NULL)')
        db.execute("CREATE TABLE candidates (id INTEGER PRIMARY KEY, status TEXT NOT NULL CHECK(status IN ('accepted','rejected')), frames INTEGER NOT NULL, spec TEXT NOT NULL, motion_sha256 TEXT NOT NULL, rgb_sha256 TEXT)")
        db.executemany('INSERT INTO metadata VALUES (?,?)',[('schema','wing-checkpoint-v1'),('protocol',protocol_text),('protocol_sha256',sha(protocol_text.encode('utf8')))])
        db.executemany('INSERT INTO sources VALUES (?,?,?)',items)
        blob=pack_stats(empty_stats());db.execute('INSERT INTO state VALUES (1,0,0,?,?)',(blob,sha(blob)))
        db.execute('COMMIT')
    except BaseException:
        if db.in_transaction:db.execute('ROLLBACK')
        raise
    finally:db.close()


def verify(db,expected_protocol):
    """Validate database and return committed state; caller owns transaction/lock."""
    if db.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError('SQLite не прошла quick_check.')
    meta=dict(db.execute('SELECT key,value FROM metadata').fetchall())
    if set(meta)!={'schema','protocol','protocol_sha256'} or meta['schema']!='wing-checkpoint-v1' or sha(meta['protocol'].encode('utf8'))!=meta['protocol_sha256']:
        raise ValueError('Повреждён протокол контрольной точки.')
    if meta['protocol']!=canonical(expected_protocol):raise ValueError('Протокол или версии отличаются: продолжение запрещено.')
    sources=db.execute('SELECT name,payload,sha256 FROM sources ORDER BY name').fetchall()
    if not sources or len(sources)>80 or sum(len(x[1]) for x in sources)>MAX_TOTAL:raise ValueError('Повреждены копии исходных данных.')
    for name,payload,digest in sources:
        if not NAME.fullmatch(name) or len(payload)>MAX_SOURCE or sha(payload)!=digest:raise ValueError('SHA копии исходных данных не совпадает.')
    if expected_protocol.get('source_sha256')!={name:digest for name,_,digest in sources}:raise ValueError('Контрольные суммы источников отличаются от протокола.')
    row=db.execute('SELECT next_id,elapsed,stats,stats_sha256 FROM state WHERE id=1').fetchone()
    if not row or db.execute('SELECT count(*) FROM state').fetchone()[0]!=1:raise ValueError('Повреждено состояние.')
    next_id,elapsed,blob,digest=row;stats=unpack_stats(blob,digest)
    count,lo,hi,frames=db.execute('SELECT COUNT(*),MIN(id),MAX(id),COALESCE(SUM(frames),0) FROM candidates').fetchone()
    if type(next_id)!=int or next_id<0 or count!=next_id or (count and (lo!=0 or hi!=next_id-1)) or frames!=stats['n'] or not math.isfinite(elapsed) or elapsed<0:
        raise ValueError('Контрольная точка не согласуется с журналом.')
    invalid=db.execute("SELECT COUNT(*) FROM candidates WHERE (status='rejected' AND (frames != 0 OR rgb_sha256 IS NOT NULL)) OR (status='accepted' AND (frames < 1 OR frames > 249 OR rgb_sha256 IS NULL))").fetchone()[0]
    if invalid:raise ValueError('Некорректные записи журнала кандидатов.')
    return {'next_id':next_id,'elapsed':elapsed,'stats':stats,'sources':{name:bytes(payload) for name,payload,_ in sources}}


def open_verified(path,expected_protocol):
    if not Path(path).is_file():raise ValueError('Нет базы контрольной точки.')
    db=connect(path)
    try:
        db.execute('BEGIN');state=verify(db,expected_protocol);db.execute('COMMIT');return state
    except BaseException:
        if db.in_transaction:db.execute('ROLLBACK')
        raise
    finally:db.close()


def commit_batch(path,protocol,expected_next,records,stats,elapsed):
    """Atomically commit contiguous candidates and their new cumulative stats.

    A stale expected_next is rejected; no two writers can commit the same IDs.
    The caller is responsible for the correctness of feature computations.
    """
    if type(expected_next)!=int or expected_next<0 or not records:raise ValueError('Пустая партия или неверный номер.')
    if not isinstance(elapsed,(int,float)) or isinstance(elapsed,bool) or not math.isfinite(elapsed):raise ValueError('Некорректное активное время.')
    values=[];frames=0
    for j,r in enumerate(records):
        if not isinstance(r,dict) or r.get('id')!=expected_next+j or r.get('status') not in ('accepted','rejected') or type(r.get('frames'))!=int:
            raise ValueError('Партия должна содержать последовательные номера и допустимый статус.')
        n=r['frames'];rgb=r.get('rgb_sha256');motion=r.get('motion_sha256')
        if not isinstance(motion,str) or not DIGEST.fullmatch(motion):raise ValueError('Некорректный SHA движения.')
        if r['status']=='accepted':
            if not 1<=n<=249 or not isinstance(rgb,str) or not DIGEST.fullmatch(rgb):raise ValueError('Некорректные кадры принятого движения.')
        elif n!=0 or rgb is not None:raise ValueError('Отклонённое движение не должно иметь кадры или RGB.')
        spec=canonical(r.get('spec'))
        if len(spec.encode('utf8'))>16384:raise ValueError('Слишком большая запись кандидата.')
        frames+=n;values.append((r['id'],r['status'],n,spec,motion,rgb))
    valid_stats(stats);blob=pack_stats(stats)
    db=connect(path)
    try:
        db.execute('BEGIN IMMEDIATE');state=verify(db,protocol)
        if state['next_id']!=expected_next:raise ValueError('Состояние изменилось: партия устарела и не сохранена.')
        if elapsed<state['elapsed'] or int(stats['n'])!=state['stats']['n']+frames:raise ValueError('Время или число кадров не согласуются с партией.')
        db.executemany('INSERT INTO candidates VALUES (?,?,?,?,?,?)',values)
        db.execute('UPDATE state SET next_id=?,elapsed=?,stats=?,stats_sha256=? WHERE id=1',(expected_next+len(values),float(elapsed),blob,sha(blob)))
        db.execute('COMMIT')
    except BaseException:
        if db.in_transaction:db.execute('ROLLBACK')
        raise
    finally:db.close()
