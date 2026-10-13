import unittest,sys,io,json,tempfile,os,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent.parent));import ansiblecs as m
class Tests(unittest.TestCase):
 def invoke(self,root,op,mode='normal',auth=None):
  calls=[]
  def http(q,kw):
   import requests
   calls.append(q.url);self.assertEqual(q.method,'GET');self.assertTrue(kw['verify']);self.assertFalse(kw['allow_redirects']);self.assertEqual(kw['proxies'],{})
   if '/profile/' in q.url:v={'uuid':'fixture-account','email':'synthetic' if mode!='identity' else 'wrong'}
   else:
    objects=[{'uuid':'s','name':'host','status':'running','runtime':{'nics':[{'ip_v4':{'uuid':'192.0.2.1'}}]}}] if '/servers/' in q.url else [{'name':'group','resources':[{'uuid':'s','res_type':'servers'}]}]
    v={'objects':objects,'meta':{'limit':100,'offset':0,'total_count':len(objects)}}
    if mode=='pagination':v['meta']['next']='https://evil/'
    if mode=='schema':v['objects']=[{}]
   r=requests.Response();r.status_code=500 if mode=='error' else 200;r._content=json.dumps(v).encode();r.request=q;return r
  raw=json.dumps(auth if auth is not None else {'username':'synthetic','password':'synthetic-secret'}).encode();out=io.StringIO();err=io.StringIO()
  with patch.object(sys,'stdin',io.TextIOWrapper(io.BytesIO(raw))),patch.object(sys,'stdout',out),patch.object(sys,'stderr',err):code=m.main(['--cache-dir',str(root)]+op,http)
  self.assertNotIn('synthetic-secret',out.getvalue()+err.getvalue());return code,out.getvalue(),calls
 def test_populated_cli(self):
  with tempfile.TemporaryDirectory(dir=Path.home()) as t:
   root=Path(t)/'cache';code,out,calls=self.invoke(root,['--refreshdb']);self.assertEqual(code,0);self.assertEqual(len(calls),3)
   code,out,calls=self.invoke(root,['--list']);self.assertEqual(code,0);v=json.loads(out);self.assertEqual(v['group']['hosts'],['host']);self.assertEqual(v['_meta']['hostvars']['host']['ansible_ssh_host'],'192.0.2.1');self.assertEqual(len(calls),1)
   self.assertEqual(json.loads(self.invoke(root,['--host','host'])[1]),{'ansible_ssh_host':'192.0.2.1'});self.assertEqual(json.loads(self.invoke(root,['--host','unknown'])[1]),{})
   self.assertNotIn('synthetic-secret',next(root.glob('*.json')).read_text())
 def test_boundaries(self):
  for mode in ['identity','pagination','schema','error']:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory(dir=Path.home()) as t:
    root=Path(t)/'cache';code,out,calls=self.invoke(root,['--refreshdb'],mode);self.assertEqual(code,1);self.assertEqual(out,'');self.assertFalse(list(root.glob('*.json')));self.assertLessEqual(len(calls),3)
 def test_invalid_auth(self):
  with tempfile.TemporaryDirectory(dir=Path.home()) as t:
   root=Path(t)/'cache';code,_,calls=self.invoke(root,['--refreshdb'],auth={'username':'x'});self.assertEqual(code,1);self.assertEqual(calls,[]);self.assertFalse(root.exists())
 def test_cache_refusal(self):
  for mode in ['symlink','expiry','schema','binding','permissions']:
   with self.subTest(mode=mode),tempfile.TemporaryDirectory(dir=Path.home()) as t:
    root=Path(t)/'cache';self.assertEqual(self.invoke(root,['--refreshdb'])[0],0);f=next(root.glob('*.json'));v=json.loads(f.read_text())
    if mode=='symlink':f.unlink();f.symlink_to('/dev/null')
    elif mode=='permissions':f.chmod(0o644)
    else:
     if mode=='expiry':v['expires']=0
     if mode=='binding':v['binding']='other'
     if mode=='schema':v['inventory']['all']['hosts']=['unknown']
     f.write_text(json.dumps(v))
    self.assertEqual(self.invoke(root,['--list'])[0],1)
if __name__=='__main__':unittest.main()
