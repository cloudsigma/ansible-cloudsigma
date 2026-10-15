import sys,os,unittest,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
# Restrict Python networking before SDK/test imports; subprocesses permitted only for inventory fixtures.
def deny(event,args):
 if event.startswith('socket.'):raise PermissionError('offline network denied')
sys.addaudithook(deny)
import socket
try:socket.socket()
except PermissionError:pass
else:raise RuntimeError('network guard failed')
os.environ['CLOUDSIGMA_CONFIG']='/dev/null'
import cloudsigma
assert 'site-packages' in cloudsigma.__file__, 'must test installed artifact'
sdk_source=ROOT/'sdk-source'/'src'/'cloudsigma'
installed=Path(cloudsigma.__file__).parent
expected={str(p.relative_to(sdk_source)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sdk_source.rglob('*.py')}
actual={str(p.relative_to(installed)):hashlib.sha256(p.read_bytes()).hexdigest() for p in installed.rglob('*.py')}
assert expected and actual==expected, 'whole installed SDK differs from pinned source'
print(json.dumps({'python':sys.version,'SDK':str(installed),'members':actual}))
os.environ['PATH']=str(Path(sys.executable).parent)+':/usr/bin:/bin'
os.environ['CLOUDSIGMA_CONFIG']='/dev/null'
sys.path.insert(0,str(ROOT))
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
r=unittest.TextTestRunner(verbosity=2).run(suite)
assert r.testsRun==13, 'unexpected test count'
sys.exit(not r.wasSuccessful())
