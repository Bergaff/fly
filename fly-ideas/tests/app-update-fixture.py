import hashlib
import importlib.util
import io
import json
import os
import ssl
import sys
import types
import urllib.error
from unittest import mock
import subprocess
import shutil
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('app_update',ROOT/'electron/app-update.py')
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)


class TLSRequestTest(unittest.TestCase):
    def test_certifi_retry_keeps_verification_and_hostname(self):
        class Response:
            def __init__(self): self.buf=io.BytesIO(b'ok')
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def geturl(self): return 'https://api.github.com/test'
            def read(self,limit): return self.buf.read(limit)
        contexts=[]
        def open_url(req, timeout, context):
            contexts.append(context)
            if len(contexts)==1: raise urllib.error.URLError(ssl.SSLCertVerificationError('untrusted'))
            self.assertEqual(context.verify_mode,ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)
            return Response()
        cert_file=ssl.get_default_verify_paths().cafile
        if not cert_file: self.skipTest('test system has no CA file')
        with mock.patch.object(u.urllib.request,'urlopen',side_effect=open_url), mock.patch.dict(sys.modules,{'certifi':types.SimpleNamespace(where=lambda:cert_file)}):
            self.assertEqual(u.request('https://api.github.com/test',100),b'ok')
        self.assertEqual(len(contexts),2);self.assertIsNone(contexts[0])

    def test_certifi_retry_failure_is_not_ignored(self):
        cert_file=ssl.get_default_verify_paths().cafile
        if not cert_file: self.skipTest('test system has no CA file')
        failure=urllib.error.URLError(ssl.SSLCertVerificationError('untrusted'))
        with mock.patch.object(u.urllib.request,'urlopen',side_effect=failure) as func, mock.patch.dict(sys.modules,{'certifi':types.SimpleNamespace(where=lambda:cert_file)}):
            with self.assertRaises(urllib.error.URLError): u.request('https://api.github.com/test',100)
            self.assertEqual(func.call_count,2)

    def test_non_certificate_failure_never_retries(self):
        with mock.patch.object(u.urllib.request,'urlopen',side_effect=urllib.error.URLError('connection refused')) as func:
            with self.assertRaises(urllib.error.URLError): u.request('https://api.github.com/test',100)
            self.assertEqual(func.call_count,1)

class StreamingRequestTest(unittest.TestCase):
    def response(self, data, length=None):
        class Response:
            def __init__(self):
                self.buf=io.BytesIO(data)
                self.headers={} if length is None else {'Content-Length':str(length)}
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def geturl(self): return 'https://codeload.github.com/test'
            def read(self,n): return self.buf.read(n)
        return Response()
    def test_download_progress_known_and_unknown(self):
        for length in (70000,None):
            with self.subTest(length=length), mock.patch.object(u.urllib.request,'urlopen',return_value=self.response(b'x'*70000,length)), mock.patch.object(u,'emit_progress') as emit:
                self.assertEqual(len(u.request('https://codeload.github.com/test',100000,progress=True)),70000)
                self.assertEqual(emit.call_args_list[0].args,('archive',0,length,'bytes'))
                self.assertEqual(emit.call_args_list[-1].args,('archive',70000,length,'bytes'))
    def test_truncated_and_oversized_responses_fail(self):
        with mock.patch.object(u.urllib.request,'urlopen',return_value=self.response(b'abc',4)):
            with self.assertRaisesRegex(ValueError,'Неполная загрузка'): u.request('https://codeload.github.com/test',10,progress=True)
        for length in (None,5):
            with mock.patch.object(u.urllib.request,'urlopen',return_value=self.response(b'abcde',length)):
                with self.assertRaisesRegex(ValueError,'Слишком большой ответ'): u.request('https://codeload.github.com/test',4)

class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.app=Path(self.tmp.name)/'app';self.app.mkdir()
        self.config=self.app/'config.json';self.config.write_text('{}',encoding='utf8')
        self.files={'package.json':b'{"name":"test"}', 'package-lock.json':b'{"lockfileVersion":3}',
                    'src/App.tsx':b'new app', 'electron/main.cjs':b'new main', 'SETUP-PYTHON.bat':b'@echo off\nexit\n'}
        self.commit='a'*40
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w:gz') as t:
            for rel,data in self.files.items():
                if rel.endswith('.bat'): data=data.replace(b'\n',b'\r\n')
                item=tarfile.TarInfo('fly-commit/fly-ideas/'+rel);item.size=len(data);t.addfile(item,io.BytesIO(data))
            extra=tarfile.TarInfo('fly-commit/fly-ideas/workspace/data/protected.txt');extra.size=4;t.addfile(extra,io.BytesIO(b'evil'))
        self.archive=buf.getvalue()
        self.tree={'truncated':False,'tree':[{'path':'fly-ideas/'+rel,'type':'blob','mode':'100644','sha':u.blob_hash(data)} for rel,data in self.files.items()]}
        self.real_request=u.request
        u.request=lambda url,limit,progress=False: json.dumps({'sha':self.commit}).encode() if '/commits/' in url else json.dumps(self.tree).encode() if '/git/trees/' in url else self.archive
        (self.app/'electron').mkdir();(self.app/'electron/main.cjs').write_bytes(b'local edits')
        (self.app/'START.bat').write_bytes(b'custom launcher')
        (self.app/'workspace/data').mkdir(parents=True);(self.app/'workspace/data/protected.txt').write_bytes(b'user data')

    def tearDown(self): u.request=self.real_request;self.tmp.cleanup()
    def prepare(self,pid=99999999): return u.prepare(self.app,self.config,pid)
    def pending(self): return json.loads((self.app/'workspace/.app-updates/pending.json').read_text(encoding='utf8'))

    def test_conflict_stops_before_download_and_names_protected_folder(self):
        self.config.write_text(json.dumps({'dirs':{'data':str(self.app.resolve())}}),encoding='utf8')
        calls=[]
        existing=u.request
        def logged(url,limit,progress=False):
            calls.append(url)
            return existing(url,limit,progress=progress)
        u.request=logged
        with self.assertRaisesRegex(ValueError,'Защищённый путь') as exc:
            self.prepare()
        self.assertIn(str(self.app.resolve()),str(exc.exception))
        self.assertFalse(any('codeload' in url for url in calls))
        self.assertFalse((self.app/'workspace/.app-updates/pending.json').exists())
        self.assertEqual((self.app/'workspace/data/protected.txt').read_bytes(),b'user data')

    def test_update_and_backups(self):
        p=self.prepare();self.assertEqual(p['commit'],self.commit)
        self.assertEqual(u.apply(self.app),0)
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'new main')
        backup=next((self.app/'workspace/.app-updates').glob('backup-*'))
        self.assertEqual((backup/'electron/main.cjs').read_bytes(),b'local edits')
        self.assertEqual((self.app/'workspace/data/protected.txt').read_bytes(),b'user data')
        self.assertEqual((self.app/'START.bat').read_bytes(),b'custom launcher')
        self.assertEqual((self.app/'SETUP-PYTHON.bat').read_bytes(),b'@echo off\r\nexit\r\n')
        self.assertTrue((self.app/'workspace/.app-updates/npm-pending').exists())
        self.assertFalse((self.app/'workspace/.app-updates/pending.json').exists())

    def test_corrupt_download_or_active_process_does_not_write(self):
        self.prepare(os.getpid())
        with self.assertRaisesRegex(ValueError,'ещё работает'): u.apply(self.app)
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'local edits')
        m=self.pending();m['owner_pid']=99999999
        u.atomic_json(self.app/'workspace/.app-updates/pending.json',m)
        (self.app/'workspace/.app-updates'/m['stage']/'src/App.tsx').write_text('bad')
        with self.assertRaisesRegex(ValueError,'Повреждён файл'):u.apply(self.app)
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'local edits')

    def test_protected_folder_and_symlink(self):
        self.prepare();self.config.write_text(json.dumps({'dirs':{'data':str(self.app/'src')}}),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'пользовательскими данными'):u.apply(self.app)
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'local edits')
        self.config.write_text('{}',encoding='utf8')
        elsewhere=Path(self.tmp.name)/'elsewhere';elsewhere.mkdir()
        try: (self.app/'src').symlink_to(elsewhere,target_is_directory=True)
        except (OSError,NotImplementedError): self.skipTest('symlinks unavailable')
        with self.assertRaisesRegex(ValueError,'Ссылка'):u.apply(self.app)
        self.assertFalse((elsewhere/'App.tsx').exists())

    def test_data_inside_node_modules_blocks_npm(self):
        self.prepare();self.config.write_text(json.dumps({'dirs':{'data':str(self.app/'node_modules/userdata')}}),encoding='utf8')
        with self.assertRaisesRegex(ValueError,'node_modules'):u.apply(self.app)
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'local edits')
        self.assertFalse((self.app/'workspace/.app-updates/npm-pending').exists())

    def test_write_failure_restores_previous_files(self):
        self.prepare();real=u.os.replace
        def fail_once(src,dst):
            if str(dst).endswith('src/App.tsx') and not getattr(fail_once,'done',False):
                fail_once.done=True;raise OSError('interrupted write')
            return real(src,dst)
        u.os.replace=fail_once
        try:
            with self.assertRaisesRegex(OSError,'interrupted write'):u.apply(self.app)
        finally:u.os.replace=real
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'local edits')
        self.assertFalse((self.app/'package.json').exists())
        self.assertFalse((self.app/'workspace/.app-updates/journal.json').exists())
        self.assertEqual(u.apply(self.app),0)

    def test_incomplete_journal_recovers_before_retry(self):
        self.prepare();base=self.app/'workspace/.app-updates';backup=base/'backup-manual';(backup/'electron').mkdir(parents=True)
        (backup/'electron/main.cjs').write_bytes(b'local edits');(self.app/'electron/main.cjs').write_bytes(b'partial')
        u.atomic_json(base/'journal.json',{'app':str(self.app.resolve()),'config':str(self.config.resolve()),'backup':backup.name,
              'files':[{'rel':'electron/main.cjs','existed':True,'sha256':u.sha(b'local edits')}]})
        self.assertEqual(u.apply(self.app),1)
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'local edits')
        self.assertTrue((base/'pending.json').exists())
        self.assertEqual(u.apply(self.app),0)

    def test_start_helper_applies_staged_update(self):
        shutil.copyfile(ROOT/'electron/app-update.py',self.app/'electron/app-update.py')
        shutil.copyfile(ROOT/'electron/app-update-start.cjs',self.app/'electron/app-update-start.cjs')
        shutil.copyfile(ROOT/'electron/app-update-status.cjs',self.app/'electron/app-update-status.cjs')
        self.prepare()
        result=subprocess.run(['node',str(self.app/'electron/app-update-start.cjs')],capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'new main')
        self.assertEqual((self.app/'workspace/data/protected.txt').read_bytes(),b'user data')

    def test_start_helper_preserves_failure_details(self):
        shutil.copyfile(ROOT/'electron/app-update.py',self.app/'electron/app-update.py')
        shutil.copyfile(ROOT/'electron/app-update-start.cjs',self.app/'electron/app-update-start.cjs')
        shutil.copyfile(ROOT/'electron/app-update-status.cjs',self.app/'electron/app-update-status.cjs')
        self.prepare();m=self.pending()
        (self.app/'workspace/.app-updates'/m['stage']/'src/App.tsx').write_text('corrupt')
        result=subprocess.run(['node',str(self.app/'electron/app-update-start.cjs')],capture_output=True,text=True,timeout=30)
        self.assertNotEqual(result.returncode,0)
        status=json.loads((self.app/'workspace/.app-updates/update-status.json').read_text(encoding='utf8'))
        self.assertEqual(status['state'],'error')
        self.assertIn('Повреждён файл обновления',status['message'])
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'local edits')
        self.assertTrue((self.app/'workspace/.app-updates/pending.json').exists())

    def test_invalid_symlink_in_tree(self):
        self.tree['tree'][0]['mode']='120000'
        with self.assertRaisesRegex(ValueError,'Недопустимый объект'):self.prepare()
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'local edits')

    def test_invalid_git_blob_is_rejected(self):
        self.tree['tree'][0]['sha']='0'*40
        with self.assertRaisesRegex(ValueError,'Контрольная сумма Git'):self.prepare()
        self.assertEqual((self.app/'electron/main.cjs').read_bytes(),b'local edits')
        self.assertFalse((self.app/'workspace/.app-updates/pending.json').exists())

if __name__=='__main__':unittest.main()
