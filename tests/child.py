import sys as _sys
def _deny_network(event,args):
 if event.startswith('socket.'):
  raise PermissionError('offline child network denied')
_sys.addaudithook(_deny_network)
import sys,os,json,time,runpy,atexit,hashlib
from pathlib import Path
src=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(src));import ansiblecs as m
# Execute source __main__ intact; inject only underlying requests Session transport.
import requests
mode=os.environ['FIXTURE_MODE']
# Optional lifecycle receipts use the same pinned checkout identity as CI.
record={'requests':[], 'decoded':[]}
if 'FIXTURE_RECEIPT' in os.environ:
 import cloudsigma
 installed=Path(cloudsigma.__file__).parent
 sdk_source=src/'sdk-source'/'src'/'cloudsigma'
 def members(root):
  return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*.py')}
 expected=members(sdk_source);actual=members(installed)
 assert 'site-packages' in str(installed) and expected and actual==expected
 record['sdk_members']=actual
 original_json=requests.Response.json
 def decode(self,*a,**kw):
  value=original_json(self,*a,**kw)
  record['decoded'].append({'url':self.request.url,'value':value})
  return value
 requests.Response.json=decode
 def receipt():
  Path(os.environ['FIXTURE_RECEIPT']).write_text(json.dumps(record))
 atexit.register(receipt)
def send(self,q,**kw):
 if mode=='stall':time.sleep(60)
 if 'FIXTURE_RECEIPT' in os.environ:
  routes=['profile/','servers/detail/?limit=100','tags/?limit=100']
  assert q.url=='https://next.cloudsigma.com/api/2.0/'+routes[len(record['requests'])]
  assert q.method=='GET' and q.body is None
  assert kw['verify'] is True and kw['allow_redirects'] is False
  assert kw['proxies']=={} and kw['timeout']==8 and kw['stream'] is True
  assert q.headers['Authorization']=='Basic Zml4dHVyZS11c2VyOmZpeHR1cmUtc2VjcmV0'
  record['requests'].append(q.url)
 if '/tags/' in q.url and mode=='late-timeout':
  raise requests.exceptions.Timeout('fixture-secret synthetic timeout')
 if '/profile/' in q.url:v={'uuid':'fixture-account','email':'fixture-user'}
 else:
  objects=[{'uuid':'s','name':'host','status':'running','runtime':{'nics':[{'ip_v4':{'uuid':'192.0.2.1'}}]}}] if '/servers/' in q.url else [{'name':'g','resources':[{'uuid':'s','res_type':'servers'}]}]
  if mode in ('changed','late-http503','late-timeout') and '/servers/' in q.url:
   objects[0]['name']='new-host';objects[0]['runtime']['nics'][0]['ip_v4']['uuid']='192.0.2.2'
  if mode=='missing-nic' and '/servers/' in q.url:objects[0]['runtime']={}
  v={'objects':objects,'meta':{'limit':100,'offset':0,'total_count':len(objects)+(1 if mode=='incomplete' else 0)}}
 r=requests.Response();r.status_code=503 if mode=='late-http503' and '/tags/' in q.url else 200;r.request=q
 import io
 r.raw=io.BytesIO(json.dumps(v).encode())
 # raw.read receives decode_content from real fence.
 class Raw(io.BytesIO):
  def read(self,n=-1,**kw):return super().read(n)
 r.raw=Raw(json.dumps(v).encode());return r
requests.Session.send=send
sys.argv.insert(1,'--internal-worker')
runpy.run_path(str(src/'ansiblecs.py'),run_name='__main__')
