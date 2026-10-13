import sys as _sys
def _deny_network(event,args):
 if event.startswith('socket.'):
  raise PermissionError('offline child network denied')
_sys.addaudithook(_deny_network)
import sys,os,json,time,runpy
from pathlib import Path
src=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(src));import ansiblecs as m
# Execute source __main__ intact; inject only underlying requests Session transport.
import requests
mode=os.environ['FIXTURE_MODE']
def send(self,q,**kw):
 if mode=='stall':time.sleep(60)
 if '/profile/' in q.url:v={'uuid':'fixture-account','email':'fixture-user'}
 else:
  objects=[{'uuid':'s','name':'host','status':'running','runtime':{'nics':[{'ip_v4':{'uuid':'192.0.2.1'}}]}}] if '/servers/' in q.url else [{'name':'g','resources':[{'uuid':'s','res_type':'servers'}]}]
  if mode=='missing-nic' and '/servers/' in q.url:objects[0]['runtime']={}
  v={'objects':objects,'meta':{'limit':100,'offset':0,'total_count':len(objects)+(1 if mode=='incomplete' else 0)}}
 r=requests.Response();r.status_code=200;r.request=q
 import io
 r.raw=io.BytesIO(json.dumps(v).encode())
 # raw.read receives decode_content from real fence.
 class Raw(io.BytesIO):
  def read(self,n=-1,**kw):return super().read(n)
 r.raw=Raw(json.dumps(v).encode());return r
requests.Session.send=send
sys.argv.insert(1,'--internal-worker')
runpy.run_path(str(src/'ansiblecs.py'),run_name='__main__')
