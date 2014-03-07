# ansible-cloudsigma

Ansible Dynamic Inventory Sources for CloudSigma.

## Installation

This script relies on the [pycloudsigma](https://github.com/cloudsigma/pycloudsigma). Install it by running:

    $ pip install -r requirements.txt

Next, you need to configure your credentials and data center location per the installation [instructions](https://github.com/cloudsigma/pycloudsigma#config-file).

## Usage

With pycloudsigma installed, you now need to build the database. To do this, run:

    $ ./ansiblecs.py --refreshdb

You can then verify the entry by running:

    $ ./ansiblecs.py --list

This should return a list of all running nodes, along with their IPs.

Finally, let's test this with ansible by running a ping against the server `ansible.local`:

    $ ansible -i ansiblecs.py -u cloudsigma ansible.local -m ping
    1.2.3.4 | success >> {
    "changed": false,
    "ping": "pong"
    }

Success! If that worked out, let's make this your default Ansible back-end. To do this, edit `/etc/ansible/ansible.cfg` (or create it if it doesn't exist). What you need to do is to change 'hostfile' such that it points to your script. A minimal `ansible.cfg` would look like this:

    [defaults]
    hostfile = /path/to/ansiblecs.py

This allows you to simply run:

    $ ansible -u cloudsigma ansible.local -m ping

