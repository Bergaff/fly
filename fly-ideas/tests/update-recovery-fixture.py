import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('recover',ROOT/'electron/update-recovery.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.app=Path(self.tmp.name)/'app';self.app.mkdir()
        (self.app/'electron').mkdir();shutil.copyfile(ROOT/'electron/app-update.py',self.app/'electron/app-update.py')
        (self.app/'START.bat').write_text('unchanged')
        self.base=self.app/'workspace/.app-updates';self.base.mkdir(parents=True)
        (self.app/'workspace/user.csv').write_bytes(b'precious')
        self.cfg=self.app/'config.json'
        self.cfg.write_text(json.dumps({'dirs':{'data':str(self.app)},'apiKey':'THIS_MUST_NOT_BE_REPORTED'}),encoding='utf8')
        self.stage='stage-'+'a'*40+'-'+'b'*32
        (self.base/self.stage).mkdir()
        (self.base/self.stage/'staged.txt').write_bytes(b'download')
        self.pending=self.base/'pending.json'
        self.pending.write_text(json.dumps({'version':1,'branch':'arena/01a0b34a-fly','app':str(self.app.resolve()),'config':str(self.cfg.resolve()),'commit':'a'*40,'stage':self.stage,'owner_pid':99999999,'files':{'.gitattributes':'c'*64}}),encoding='utf8')
    def tearDown(self):self.tmp.cleanup()
    def test_diagnose_and_pause_preserving_all_user_files(self):
        info=r.inspect(self.app)
        self.assertIn('dirs.data: '+str(self.app.resolve()),info[-2])
        self.assertNotIn('THIS_MUST_NOT_BE_REPORTED',info[-2])
        p=self.pending.read_bytes();cfg=self.cfg.read_bytes()
        self.assertIsNone(r.pause_update(info,False));self.assertTrue(self.pending.exists())
        paused=r.pause_update(info,True)
        self.assertFalse(self.pending.exists());self.assertEqual(paused.read_bytes(),p)
        self.assertEqual(self.cfg.read_bytes(),cfg);self.assertEqual((self.app/'workspace/user.csv').read_bytes(),b'precious')
        self.assertEqual((self.base/self.stage/'staged.txt').read_bytes(),b'download')
        self.assertEqual((self.app/'START.bat').read_text(),'unchanged')
    def test_never_pause_if_journal_or_live_owner(self):
        (self.base/'journal.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'journal.json'):r.inspect(self.app)
        (self.base/'journal.json').unlink()
        m=json.loads(self.pending.read_text());m['owner_pid']=os.getpid();self.pending.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'ещё работает'):r.inspect(self.app)
        self.assertTrue(self.pending.exists())
    def test_races_refuse_without_renaming(self):
        info=r.inspect(self.app);self.cfg.write_text('{}')
        with self.assertRaisesRegex(ValueError,'изменились'):r.pause_update(info,True)
        self.assertTrue(self.pending.exists())
        self.cfg.write_text(json.dumps({'dirs':{'data':str(self.app)}}))
        info=r.inspect(self.app);self.pending.write_text(self.pending.read_text()+' ')
        with self.assertRaisesRegex(ValueError,'изменились'):r.pause_update(info,True)
        info=r.inspect(self.app);(self.base/'journal.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'изменилось'):r.pause_update(info,True)
        self.assertTrue(self.pending.exists())
    def test_diagnostic_fields_and_nonconflicting_paths(self):
        for config,name in [({'projectDirs':{'test':{'code':str(self.app)} }},'projectDirs.test.code'),({'dataFiles':{'input':str(self.app/'.gitattributes')}},'dataFiles.input'),({'syncFolder':str(self.app.parent)},'syncFolder')]:
            self.cfg.write_text(json.dumps(config));info=r.inspect(self.app)
            self.assertIn(name,info[-2]);self.assertTrue(info[-1])
        self.cfg.write_text('{}');info=r.inspect(self.app)
        self.assertFalse(info[-1])
        with self.assertRaisesRegex(ValueError,'не найдено'):r.pause_update(info,True)
        self.assertTrue(self.pending.exists())
    @unittest.skipIf(os.name=='nt','symlink creation may require privileges')
    def test_links_and_broken_journal_refused(self):
        (self.base/'journal.json').symlink_to(self.base/'missing')
        with self.assertRaisesRegex(ValueError,'journal'):r.inspect(self.app)
        (self.base/'journal.json').unlink()
        self.pending.rename(self.base/'other.json');self.pending.symlink_to(self.base/'other.json')
        with self.assertRaisesRegex(ValueError,'Ссылка'):r.inspect(self.app)
        self.assertTrue((self.base/'other.json').exists())
    def test_cli_confirmation_preserves_snapshot(self):
        import subprocess,sys
        result=subprocess.run([sys.executable,str(ROOT/'electron/update-recovery.py'),str(self.app)],input='1\n',text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertFalse(self.pending.exists());self.assertEqual(len(list(self.base.glob('pending-paused-*.json'))),1)
        self.assertTrue((self.base/self.stage/'staged.txt').exists())

    def test_packaged_bat_embeds_exact_source(self):
        text=(ROOT/'experiments/PAUSE-FAILED-UPDATE.bat').read_text(encoding='utf8')
        marker='#<FLY_RECOVERY_PY>\n'
        self.assertEqual(text.split(marker,1)[1],(ROOT/'electron/update-recovery.py').read_text(encoding='utf8'))

if __name__=='__main__':unittest.main()
