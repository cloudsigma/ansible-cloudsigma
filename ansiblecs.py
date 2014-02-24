#!/usr/bin/env python
'''
CloudSigma external inventory tracker for Ansible.
'''

import cloudsigma
import json
import sys
import pickle

db_store = '/tmp/ansible-cloudsigma.db'


def refresh_db():
    server = cloudsigma.resource.Server()
    server_list = server.list()
    server_db = {}

    for i in server_list:
        if i['status'] == 'running':
            name = i['name']
            ipv4 = i['runtime']['nics'][0]['ip_v4']['uuid']
            server_db[name] = {'ip': ipv4}

    pickle.dump(server_db, open(db_store, 'wb'))


def list_hosts():
    server_db = pickle.load(open(db_store, 'rb'))

    # Format the output to follow the expected input.
    def format_output():
        formatted = {}
        for i in server_db:
            formatted[i] = [server_db[i]['ip']]
        return formatted

    return format_output()


def get_host():
    # An empty JSON dict is expected here.
    return {}


if len(sys.argv) >= 2:
    if sys.argv[1] == '--refreshdb':
        print('Refreshing host database...')
        refresh_db()
    elif sys.argv[1] == '--list':
        hosts = json.dumps(list_hosts())
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
