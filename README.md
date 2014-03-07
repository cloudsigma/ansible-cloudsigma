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

Success! You can now install the inventory tracker in a more permanent fashion by creating a symlink inside `/etc/ansible`:

    $ ln -s /path/to/ansiblecs.py /etc/ansible/cloudsigma

This allows you to simply run:

    $ ansible -i cloudsigma -u cloudsigma ansible.local -m ping


