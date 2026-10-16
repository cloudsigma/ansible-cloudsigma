"""Sequential cache recovery through the installed SDK and child transport."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CacheRecoveryTests(unittest.TestCase):
    def test_late_failures_preserve_then_recover(self):
        for failure in ('late-http503', 'late-timeout'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory(
                    dir=Path.home()) as directory:
                root = Path(directory)
                self.assertEqual(root.stat().st_mode & 0o777, 0o700)
                cache = root / 'cache'
                calls = 0

                def call(operation, mode, code, requests, decodes):
                    nonlocal calls
                    calls += 1
                    receipt = root / ('receipt-%d.json' % calls)
                    env = {'PATH': '/usr/bin:/bin', 'HOME': str(Path.home()),
                           'FIXTURE_MODE': mode, 'FIXTURE_RECEIPT': str(receipt),
                           'CLOUDSIGMA_CONFIG': '/dev/null'}
                    result = subprocess.run(
                        [sys.executable, '-I', '-B',
                         str(Path(__file__).with_name('child.py')),
                         '--cache-dir', str(cache), operation],
                        input=b'{"username":"fixture-user","password":"fixture-secret"}',
                        capture_output=True, env=env, timeout=10)
                    self.assertEqual(result.returncode, code, result.stderr)
                    self.assertNotIn(b'fixture-secret', result.stdout + result.stderr)
                    self.assertEqual(result.stderr, b'inventory refused\n' if code else b'')
                    if code:
                        self.assertEqual(result.stdout, b'')
                    record = json.loads(receipt.read_text())
                    self.assertTrue(record['sdk_members'])
                    self.assertEqual(len(record['requests']), requests)
                    self.assertEqual(len(record['decoded']), decodes)
                    if mode in ('changed', 'late-http503', 'late-timeout') and requests == 3:
                        server = record['decoded'][1]['value']['objects'][0]
                        self.assertEqual(server['name'], 'new-host')
                        self.assertEqual(server['runtime']['nics'][0]['ip_v4']['uuid'],
                                         '192.0.2.2')
                    return result

                def expected(name, address):
                    return {'g': {'hosts': [name]}, 'all': {'hosts': [name]},
                            '_meta': {'hostvars': {name: {'ansible_ssh_host': address}}}}

                self.assertEqual(call('--refreshdb', 'normal', 0, 3, 3).stdout, b'{}\n')
                files = list(cache.glob('*.json'))
                self.assertEqual(len(files), 1)
                file = files[0]
                before = file.read_bytes()
                self.assertEqual(json.loads(before)['inventory'], expected('host', '192.0.2.1'))
                call('--refreshdb', failure, 1, 3, 2)
                self.assertEqual(file.read_bytes(), before)
                self.assertFalse(list(cache.glob('.tmp-*')))
                result = call('--list', 'normal', 0, 1, 1)
                self.assertEqual(json.loads(result.stdout), expected('host', '192.0.2.1'))
                self.assertEqual(file.read_bytes(), before)
                self.assertEqual(call('--refreshdb', 'changed', 0, 3, 3).stdout, b'{}\n')
                after = file.read_bytes()
                self.assertNotEqual(after, before)
                self.assertEqual(json.loads(after)['inventory'], expected('new-host', '192.0.2.2'))
                result = call('--list', 'changed', 0, 1, 1)
                self.assertEqual(json.loads(result.stdout), expected('new-host', '192.0.2.2'))
                self.assertEqual(file.read_bytes(), after)
                self.assertFalse(list(cache.glob('.tmp-*')))
