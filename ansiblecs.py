#!/usr/bin/env python3
# (C) CloudSigma AG
"""Python3 standalone inventory. Explicit migration to pycloudsigma source2.0.1."""
import os,sys,json,time,hashlib,stat,secrets,signal,argparse,fcntl
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlsplit
def supervised():
 import subprocess
 command=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--internal-worker']+sys.argv[1:]
 p=subprocess.Popen(command,stdin=sys.stdin,stdout=sys.stdout,stderr=sys.stderr,start_new_session=True)
 try:return p.wait(timeout=35)
 except subprocess.TimeoutExpired:
  os.killpg(p.pid,signal.SIGKILL);p.wait();print('inventory deadline',file=sys.stderr);return 1
if __name__=='__main__' and sys.argv[1:2]!=['--internal-worker']:sys.exit(supervised())
ENDPOINT='https://next.cloudsigma.com/api/2.0/'
# SDK resolved only from installed distribution in the interpreter environment.
# Refuse workspace config before SDK import; force empty OS null source.
if (Path(__file__).parent/'disabled-user-config').exists():raise SystemExit('inventory configuration refused')
os.environ['CLOUDSIGMA_CONFIG']='/dev/null'
import requests
from cloudsigma import resource,conf
if dict(conf.config):raise SystemExit("inventory configuration refused")
class Refusal(Exception):pass
def require(c):
 if not c:raise Refusal('inventory refused')
def pairs(items):
 d={}
 for k,v in items:require(k not in d);d[k]=v
 return d
def parse(raw):return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(Refusal('nonfinite')))
class Session(requests.Session):
 def __init__(self,email,underlying=None):super().__init__();self.trust_env=False;self.email=email;self.account=None;self.calls=0;self.underlying=underlying
 def send(self,q,**kw):
  u=urlsplit(q.url);profile=u.path=='/api/2.0/profile/'
  require(q.method=='GET' and u.scheme=='https' and u.netloc=='next.cloudsigma.com' and not u.fragment and not q.body and q.headers.get('Host','next.cloudsigma.com')=='next.cloudsigma.com');require(u.path in ['/api/2.0/profile/','/api/2.0/servers/detail/','/api/2.0/tags/'] and u.query==('' if profile else 'limit=100') and self.calls<3 and (profile or self.account is not None));self.calls+=1
  kw.update(allow_redirects=False,verify=True,proxies={},timeout=8,stream=True)
  r=self.underlying(q,kw) if self.underlying else super().send(q,**kw)
  try:
   if self.underlying:raw=r.content;require(len(raw)<=262144)
   else:raw=r.raw.read(262145,decode_content=True);require(len(raw)<=262144)
   require(r.status_code==200);v=parse(raw)
   if profile:require(type(v) is dict and v.get('email')==self.email and type(v.get('uuid')) is str and bool(v['uuid']));self.account=v['uuid']
   else:
    require(type(v) is dict and type(v.get('objects')) is list and len(v['objects'])<=100);m=v.get('meta');require(type(m) is dict and all(type(m.get(k)) is int for k in ['limit','offset','total_count']) and m['limit']==100 and m['offset']==0 and m['total_count']==len(v['objects']) and m.get('next') is None)
   r._content=raw;r._content_consumed=True;return r
  except Exception:self.account=None;raise
  finally:r.close()
def inventory(servers,tags):
 hosts={};ids={};groups={}
 for s in servers:
  require(type(s) is dict and type(s.get('status')) is str)
  if s['status']!='running':continue
  name=s.get('name');uid=s.get('uuid');require(type(name) is str and name and name not in hosts and name not in ['_meta','all','ungrouped'] and type(uid) is str and uid not in ids)
  ip=s['runtime']['nics'][0]['ip_v4']['uuid'];import ipaddress;require(type(ip) is str and ipaddress.ip_address(ip).version==4);hosts[name]={'ansible_ssh_host':ip};ids[uid]=name
 for t in tags:
  require(type(t) is dict and type(t.get('name')) is str and t['name'] and t['name'] not in groups and t['name'] not in hosts and t['name'] not in ['_meta','all','ungrouped'] and type(t.get('resources')) is list)
  names=[]
  for r in t['resources']:
   require(type(r) is dict and type(r.get('uuid')) is str and type(r.get('res_type')) is str)
   if r['res_type']=='servers' and r['uuid'] in ids:names.append(ids[r['uuid']])
  groups[t['name']]={'hosts':sorted(set(names))}
 return dict(groups,**{'_meta':{'hostvars':hosts},'all':{'hosts':sorted(hosts)}})
class Cache:
 def __init__(self,root,account):
  root=Path(root).absolute();fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY)
  try:
   for i,part in enumerate(root.parts[1:]):
    require(part not in ['.','..'])
    if i==len(root.parts)-2:
     try:os.mkdir(part,0o700,dir_fd=fd)
     except FileExistsError:pass
    child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child;s=os.fstat(fd);require(s.st_uid in (0,os.getuid()) and not s.st_mode&0o022)
   require(s.st_uid==os.getuid() and not s.st_mode&0o077);self.fd=fd;self.binding=hashlib.sha256((ENDPOINT+'\0'+account).encode()).hexdigest();self.name=self.binding+'.json'
  except BaseException:os.close(fd);raise
 def close(self):os.close(self.fd)
 @contextmanager
 def locked(self,exclusive):
  fd=os.open(self.name+'.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600,dir_fd=self.fd)
  try:
   s=os.fstat(fd);require(stat.S_ISREG(s.st_mode) and s.st_uid==os.getuid() and not s.st_mode&0o077 and s.st_nlink==1)
   fcntl.flock(fd,fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH);yield
  finally:os.close(fd)
 def save(self,data):
  with self.locked(True):return self._save(data)
 def _save(self,data):
  raw=json.dumps({'version':1,'binding':self.binding,'expires':time.time()+300,'inventory':data}).encode();require(len(raw)<=262144);tmp='.tmp-'+secrets.token_hex(16);fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
  try:
   with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
   os.replace(tmp,self.name,src_dir_fd=self.fd,dst_dir_fd=self.fd);os.fsync(self.fd)
  finally:
   try:os.unlink(tmp,dir_fd=self.fd)
   except FileNotFoundError:pass
 def load(self):
  with self.locked(False):return self._load()
 def _load(self):
  fd=os.open(self.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.fd)
  try:
   s=os.fstat(fd);require(stat.S_ISREG(s.st_mode) and s.st_uid==os.getuid() and not s.st_mode&0o077 and s.st_nlink==1);raw=os.read(fd,262145);require(len(raw)<=262144);v=parse(raw);require(type(v) is dict and set(v)=={'version','binding','expires','inventory'} and type(v['version']) is int and v['version']==1 and v['binding']==self.binding and type(v['expires']) in (int,float) and time.time()<v['expires']<=time.time()+301);validate_inventory(v['inventory']);return v['inventory']
  finally:os.close(fd)
def validate_inventory(v):
 require(type(v) is dict and '_meta' in v and 'all' in v and type(v['_meta']) is dict and set(v['_meta'])=={'hostvars'});h=v['_meta']['hostvars'];require(type(h) is dict)
 import ipaddress
 def name(n):return type(n) is str and bool(n) and n not in ['_meta','all','ungrouped']
 for n,x in h.items():require(name(n) and type(x) is dict and set(x)=={'ansible_ssh_host'} and type(x['ansible_ssh_host']) is str);require(ipaddress.ip_address(x['ansible_ssh_host']).version==4)
 for k,x in v.items():
  if k=='_meta':continue
  require(k=='all' or (name(k) and k not in h));require(type(x) is dict and set(x)=={'hosts'} and type(x['hosts']) is list and all(type(n) is str and n in h for n in x['hosts']));require(x['hosts']==sorted(set(x['hosts'])))
 require(v['all']['hosts']==sorted(h))
def main(argv=None,underlying=None):
 parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True);g.add_argument('--list',action='store_true');g.add_argument('--host');g.add_argument('--refreshdb',action='store_true');parser.add_argument('--cache-dir',default=str(Path.home()/'.cache-cloudsigma-inventory'));args=parser.parse_args(argv)
 previous_handler=signal.getsignal(signal.SIGALRM);previous_alarm=signal.alarm(0);started=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(Refusal('deadline')));signal.alarm(30);cache=None;session=None
 try:
  raw=sys.stdin.buffer.read(8193);require(len(raw)<=8192);a=parse(raw);require(type(a) is dict and set(a)=={'username','password'} and all(type(a[k]) is str and a[k] for k in a) and len(a['username'])<=320 and len(a['password'])<=4096 and not any(c in a['username'] for c in ':\r\n\0') and not any(c in a['password'] for c in '\r\n\0'))
  session=Session(a['username'],underlying)
  def obj(cls):
   r=cls(api_endpoint=ENDPOINT,username=a['username'],password=a['password']);r.c._session=session;r.c.login_method='basic';r.c.request_log_level=None;return r
  obj(resource.Profile).get();cache=Cache(args.cache_dir,session.account)
  if args.refreshdb:
   # Serialize collection fetch and commit: no older in-flight refresh can overwrite newer.
   with cache.locked(True):
    data=inventory(obj(resource.Server).list_detail({'limit':100}),obj(resource.Tags).list({'limit':100}));validate_inventory(data);cache._save(data);print('{}')
  else:data=cache.load();print(json.dumps(data['_meta']['hostvars'].get(args.host,{}) if args.host else data))
  return 0
 except Exception:print('inventory refused',file=sys.stderr);return 1
 finally:
  if cache:cache.close()
  if session:session.close()
  signal.alarm(0);signal.signal(signal.SIGALRM,previous_handler)
  if previous_alarm:signal.alarm(max(1,previous_alarm-int(time.monotonic()-started)))
if __name__=='__main__':
 if sys.argv[1:2]==['--internal-worker']:del sys.argv[1];sys.exit(main())
 sys.exit(supervised())
