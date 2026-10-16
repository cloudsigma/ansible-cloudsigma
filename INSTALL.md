# Current public SDK source installation
Python 3.10/3.11/3.12. The SDK source is pinned to public commit `e59a412db46ae5de466e78d622140b0fd6bf93c3` (PR34 merged). Its metadata remains cloudsigma 3.0.0rc1; this is **not** a claim of a PyPI release. `requirements.txt` uses an immutable HTTPS source URL with an archive SHA256, not an unresolvable index version or mutable master.

From this repository, create a private virtual environment (substitute your supported Python minor):
```sh
python3.12 -m venv .venv
.venv/bin/python -m pip --isolated install --require-hashes -r ci/requirements-3.12.lock
.venv/bin/python -m pip --isolated install --no-deps --no-build-isolation -r requirements.txt
.venv/bin/python -m pip check
```
The first step retrieves hashlocked build/runtime dependencies; the second verifies the source archive hash and builds it with the locked build tools. Neither installs globally. For offline installation, retain the verified dependency wheels and built SDK wheel, record its SHA256, and install with `--no-index --no-deps`. Wheel hashes can vary with build timestamps; source identity is the immutable commit and archive checksum.

CI checks out the same full SDK commit, builds without isolation using its hashlocked tools, and verifies every installed SDK Python member against that checkout before running the finite suite. Local qualification in this update covers Python3.12 only; other runtimes require their CI execution.

Install ansiblecs.py executable and invoke with PATH=<venv>/bin:/usr/bin:/bin. Public supervisor retains sys.executable -I-B. Credentials are JSON username/password on protected stdin; do not put them in argv or environment. --refreshdb outputs{}, --list modern inventory _meta/all/groups, --host returns actual hostvars or{}. Five HTTP requests across all three commands because cache reads reauthenticate profile. Only NEXT endpoint in this scoped candidate; no broader deployment claim.

Private JSON cache replaces legacy shared /tmp pickle; no migration/read of that cache. Incomplete pages refuse; firstNIC IPv4 and running hosts only; collisions refuse. Credentials never cached; inventory data is intentionally private cached. See source for limits. No release, live replay or full API qualification implied.

Offline: with the exact installed SDK, run python -m unittest discover -s tests -v. Fixtures synthetic only.14 methods; production source unchanged from reviewed portable candidate.

The discovered late-failure regression runs the actual internal worker with installed SDK identity verified against `sdk-source`, using the existing child transport fixture. Both tags HTTP503 and Timeout follow a decoded changed server collection; old cache bytes must survive, then a later refresh must recover. This is sequential offline lifecycle coverage, not live or same-session retry acceptance. Use `python -I -B ci/run_offline.py` with the pinned SDK checkout present for the identity-checked finite suite. Test caches use fresh private directories under HOME; its ancestors must not be group/world-writable (the production guard is not relaxed).
