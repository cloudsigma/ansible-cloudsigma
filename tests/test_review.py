import unittest,subprocess,sys,tempfile,os,json,signal
from pathlib import Path
from unittest.mock import patch
import ansiblecs as m
class Tests(unittest.TestCase):
 def test_direct_cli_noauth(self):
  r=subprocess.run([str(Path(m.__file__).resolve()),'--list'],input=b'{}',capture_output=True,timeout=5);self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,b'');self.assertIn(b'inventory refused',r.stderr)
 def test_hostile_config(self):
  # Isolated copy so frozen/source directory config is never edited.
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'inventory.py';p.write_bytes(Path(m.__file__).read_bytes());p.chmod(0o755);(Path(t)/'disabled-user-config').write_text('request_log_level=DEBUG\nlogin_method=session')
   r=subprocess.run([str(p),'--list'],input=b'{"username":"synthetic","password":"secret-canary"}',capture_output=True,timeout=5);self.assertEqual(r.returncode,1);self.assertNotIn(b'secret-canary',r.stdout+r.stderr)
 def test_schema_invariants(self):
  good={'_meta':{'hostvars':{'h':{'ansible_ssh_host':'192.0.2.1'}}},'all':{'hosts':['h']}}
  for mode in ['integer','reserved','collision','duplicate','empty']:
   v=json.loads(json.dumps(good))
   if mode=='integer':v['_meta']['hostvars']['h']['ansible_ssh_host']=123
   if mode=='reserved':v['_meta']['hostvars']['all']=v['_meta']['hostvars'].pop('h')
   if mode=='collision':v['h']={'hosts':[]}
   if mode=='duplicate':v['g']={'hosts':['h','h']}
   if mode=='empty':v['']={'hosts':[]}
   with self.assertRaises(m.Refusal):m.validate_inventory(v)
 def test_watchdog_kill_reap(self):
  real=subprocess.Popen;children=[]
  def spawn(*a,**kw):
   child=real([sys.executable,'-c','import time;time.sleep(60)'],**kw);children.append(child);original=child.wait
   def wait(timeout=None):return original(timeout=.1 if timeout else None)
   child.wait=wait;return child
  with patch.object(subprocess,'Popen',side_effect=spawn):self.assertEqual(m.supervised(),1)
  self.assertIsNotNone(children[0].returncode)
