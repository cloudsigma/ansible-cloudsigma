import sys,unittest,tempfile,json,subprocess,os,time,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;SRC=P.parent;sys.path.insert(0,str(SRC));import ansiblecs as m
SERVER={'uuid':'s','name':'host','status':'running','runtime':{'nics':[{'ip_v4':{'uuid':'192.0.2.1'}}]}}
class Tests(unittest.TestCase):
 def test_collisions(self):
  cases=[([SERVER,SERVER],[]),([SERVER],[{'name':'host','resources':[]}])]
  for n in ['_meta','all','ungrouped']:
   cases.extend([([dict(SERVER,name=n)],[]),([SERVER],[{'name':n,'resources':[]}])])
  cases.append(([SERVER],[{'name':'g','resources':[]},{'name':'g','resources':[]}]))
  for servers,tags in cases:
   with self.subTest(servers=bool(servers),tags=bool(tags)),self.assertRaises(m.Refusal):m.inventory(servers,tags)
 def test_empty_groups_and_missing_nic(self):
  self.assertEqual(m.inventory([],[{'name':'empty','resources':[]}])['empty'],{'hosts':[]})
  for runtime in [{},{'nics':[]},{'nics':[{}]},{'nics':[{'ip_v4':None}]},{'nics':[{'ip_v4':{'uuid':'::1'}}]}]:
   with self.assertRaises((m.Refusal,KeyError,IndexError,TypeError,ValueError)):m.inventory([dict(SERVER,runtime=runtime)],[])
  self.assertEqual(m.inventory([dict(SERVER,status='stopped',runtime={})],[])['all']['hosts'],[])
 def test_atomic_concurrency(self):
  import concurrent.futures
  with tempfile.TemporaryDirectory(dir=Path.home()) as t:
   root=Path(t)/'cache';c=m.Cache(root,'synthetic');data=m.inventory([SERVER],[]);c.save(data);c.close()
   def worker(i):
    c=m.Cache(root,'synthetic')
    try:
     for _ in range(30):
      if i%2:c.save(data)
      else:self.assertEqual(c.load(),data)
    finally:c.close()
   with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(worker,range(6)))
   self.assertFalse(list(root.glob('.tmp-*')))
 def test_cli_and_preservation(self):
  child=P/'child.py'
  with tempfile.TemporaryDirectory(dir=Path.home()) as t:
   root=Path(t)/'cache'
   def call(op,mode='normal'):
    env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'FIXTURE_MODE':mode}
    r=subprocess.run([sys.executable,'-I','-B',str(child),'--cache-dir',str(root)]+op,input=b'{"username":"fixture-user","password":"fixture-secret"}',capture_output=True,env=env,timeout=5)
    self.assertNotIn(b'fixture-secret',r.stdout+r.stderr);self.assertNotIn(b'fixture-user',r.stdout+r.stderr);return r
   self.assertEqual(call(['--refreshdb']).returncode,0);f=next(root.glob('*.json'));before=f.read_bytes()
   for mode in ['incomplete','missing-nic']:
    r=call(['--refreshdb'],mode);self.assertEqual(r.returncode,1);self.assertEqual(r.stdout,b'');self.assertEqual(f.read_bytes(),before)
   self.assertEqual(json.loads(call(['--list']).stdout)['g']['hosts'],['host'])
   self.assertEqual(json.loads(call(['--host','host']).stdout),{'ansible_ssh_host':'192.0.2.1'})
   self.assertEqual(json.loads(call(['--host','absent']).stdout),{})
 def test_whole_entry_deadline(self):
  with tempfile.TemporaryDirectory(dir=Path.home()) as t:
   start=time.monotonic();r=subprocess.run([sys.executable,'-I','-B',str(P/'child.py'),'--refreshdb','--cache-dir',str(Path(t)/'cache')],input=b'{"username":"fixture-user","password":"fixture-secret"}',capture_output=True,env={'PATH':'/usr/bin:/bin','HOME':str(Path.home()),'FIXTURE_MODE':'stall'},timeout=35)
   elapsed=time.monotonic()-start;self.assertEqual(r.returncode,1);self.assertGreaterEqual(elapsed,29);self.assertLess(elapsed,34);self.assertEqual(r.stdout,b'');self.assertNotIn(b'fixture-secret',r.stderr)
if __name__=='__main__':unittest.main(verbosity=2)
