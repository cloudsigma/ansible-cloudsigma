#!/usr/bin/env python
# (C) CloudSigma AG

DOCUMENTATION = '''
module: cloudsigma
short_description: A module to connect to your CloudSigma infrastructure.
author: Viktor Petersson <viktor@cloudsigma.com>
requirements:
    - pycloudsigma (`pip install cloudsigma`)
options:
    refreshdb:
        description:
            - Update the local server cache
        required: false
    list:
        description:
            - Dump a list of all hosts
        required: false
    host:
        description:
            - Placeholder. Will receive an empty string JSON object.
        required: false
'''

import cloudsigma
import json
import sys
import pickle

db_store = '/tmp/ansible-cloudsigma.db'


def refresh_db():
    ansible_db = {}
    running_uuid = []

    get_servers = cloudsigma.resource.Server()
    server_list = get_servers.list()
    get_tags = cloudsigma.resource.Tags()
    tag_list = get_tags.list()

    for server in server_list:
        if server['status'] == 'running':
            print 'Adding %s to inventory...' % server['name']

            name = server['name']
            ipv4 = server['runtime']['nics'][0]['ip_v4']['uuid']
            running_uuid.append(server['uuid'])
            ansible_db[name] = {'ansible_ssh_host': ipv4}

    for tag in tag_list:
        print 'Found tag %s' % tag['name']

        tag_name = tag['name']
        servers_tagged = []
        for server in tag['resources']:
            if (server['res_type'] == 'servers' and server['uuid'] in running_uuid):
                for s in server_list:
                    if s['uuid'] == server['uuid']:
                        print 'Found %s tagged with %s...' % (s['name'], tag['name'])
                        servers_tagged.append(s['name'])
            ansible_db[tag_name] = {'hosts': servers_tagged}

    pickle.dump(ansible_db, open(db_store, 'wb'))


def list_hosts():
    ansible_db = pickle.load(open(db_store, 'rb'))
    return ansible_db


def get_host():
    # An empty JSON dict is expected here.
    return {}


if len(sys.argv) >= 2:
    if sys.argv[1] == '--refreshdb':
        print('Refreshing host database...')
        refresh_db()
    elif sys.argv[1] == '--list':
        hosts = json.dumps(list_hosts(), indent=2)
        print(hosts)
    elif (sys.argv[1] == '--host' and len(sys.argv) == 3):
        # Can't use `json.dumps` since it won't return
        # anything in this case.
        print(get_host())
    else:
        print "Unknown variable."
else:
    print """
    Usage:
        --refreshdb         Refresh the database.
        --list              List all hosts.
        --host <hostname>   Details about a host. Return an empty JSON element.
    """
