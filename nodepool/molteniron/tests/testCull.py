#!/usr/bin/env python

# Copyright (c) 2016 IBM Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
import yaml
import argparse
import time
from molteniron import moltenirond

def compare_culled_nodes(lhs, rhs):
    lhs = lhs.copy()
    rhs = rhs.copy()
    del rhs['allocation_pool']
    # timestamp can be converted on the server
    del lhs['timestamp']
    del rhs['timestamp']
    del lhs['id']
    assert lhs == rhs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Molteniron command line tool")
    parser.add_argument("-c",
                        "--conf-dir",
                        action="store",
                        type=str,
                        dest="conf_dir",
                        help="The directory where configuration is stored")

    args = parser.parse_args(sys.argv[1:])

    if args.conf_dir:
        if not os.path.isdir (args.conf_dir):
            msg = "Error: %s is not a valid directory" % (args.conf_dir, )
            print >> sys.stderr, msg
            sys.exit(1)

        yaml_file = os.path.realpath("%s/conf.yaml" % (args.conf_dir, ))
    else:
        yaml_file = "/usr/local/etc/molteniron/conf.yaml"

    with open(yaml_file, "r") as fobj:
        conf = yaml.load(fobj)

    node1 = {
        "name":            "pkvmci816",
        "ipmi_ip":         "10.228.219.134",
        "ipmi_user":       "user",
        "ipmi_password":   "34118fd3509621ba",
        "port_hwaddr":     "ff:2c:e1:cc:8e:7c",
        "cpu_arch":        "ppc64el",
        "cpus":            20L,
        "ram_mb":          51000L,
        "disk_gb":         500L,
        "status":          "ready",
        "provisioned":     "",
        "timestamp":       "",
        "allocation_pool": "10.228.112.10,10.228.112.11"
    }
    node2 = {
        "name":            "pkvmci818",
        "ipmi_ip":         "10.228.219.133",
        "ipmi_user":       "user",
        "ipmi_password":   "fa2125690a95b43c",
        "port_hwaddr":     "f6:58:13:02:64:59",
        "cpu_arch":        "ppc64el",
        "cpus":            20L,
        "ram_mb":          51000L,
        "disk_gb":         500L,
        "status":          "ready",
        "provisioned":     "",
        "timestamp":       "-1",
        "allocation_pool": "10.228.112.8,10.228.112.9"
    }
    node3 = {
        "name":            "pkvmci851",
        "ipmi_ip":         "10.228.118.129",
        "ipmi_user":       "user",
        "ipmi_password":   "3aee014d56425a6c",
        "port_hwaddr":     "6e:d4:a5:ae:13:55",
        "cpu_arch":        "ppc64el",
        "cpus":            20L,
        "ram_mb":          51000L,
        "disk_gb":         500L,
        "status":          "used",
        "provisioned":     "7a72eccd-3153-4d08-9848-c6d3b1f18f9f",
        # NOTE: time() can return fractional values. Ex: 1460560140.47
        "timestamp":       str (time.time() - 1000.0),
        "allocation_pool": "10.228.112.12,10.228.112.13"
    }
    node4 = {
        "name":            "pkvmci853",
        "ipmi_ip":         "10.228.118.133",
        "ipmi_user":       "user",
        "ipmi_password":   "254dd9fb34ddcac7",
        "port_hwaddr":     "a0:c9:22:23:22:9d",
        "cpu_arch":        "ppc64el",
        "cpus":            20L,
        "ram_mb":          51000L,
        "disk_gb":         500L,
        "status":          "used",
        "provisioned":     "6b8823ef-3e14-4811-98b9-32e27397540d",
        "timestamp":       str (time.time() - 2000.0),
        "allocation_pool": "10.228.112.14,10.228.112.15"
    }

    # 8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----
    database = moltenirond.DataBase(conf, moltenirond.TYPE_SQLITE_MEMORY)
    ret = database.addBMNode (node1)
    print ret
    assert ret == {'status': 200}
    ret = database.addBMNode (node2)
    print ret
    assert ret == {'status': 200}
    ret = database.addBMNode (node3)
    print ret
    assert ret == {'status': 200}
    ret = database.addBMNode (node4)
    print ret
    assert ret == {'status': 200}

    ret = database.cull (1000)
    print ret
    assert ret['status'] == 200
    assert len(ret['nodes']) == 2

    compare_culled_nodes (ret['nodes']['node_3'], node3)
    compare_culled_nodes (ret['nodes']['node_4'], node4)

    database.close()
    del database

    # 8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----
    database = moltenirond.DataBase(conf, moltenirond.TYPE_SQLITE_MEMORY)
    database.delete_db()
    database.close()
    del database

    database = moltenirond.DataBase(conf, moltenirond.TYPE_SQLITE_MEMORY)
    ret = database.addBMNode (node1)
    print ret
    assert ret == {'status': 200}
    ret = database.addBMNode (node2)
    print ret
    assert ret == {'status': 200}
    ret = database.addBMNode (node3)
    print ret
    assert ret == {'status': 200}
    ret = database.addBMNode (node4)
    print ret
    assert ret == {'status': 200}

    ret = database.cull (2000)
    print ret
    assert ret['status'] == 200
    assert len(ret['nodes']) == 1

    compare_culled_nodes (ret['nodes']['node_4'], node4)

    database.close()
    del database

    # 8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----
    database = moltenirond.DataBase(conf, moltenirond.TYPE_SQLITE_MEMORY)
    database.delete_db()
    database.close()
    del database

    database = moltenirond.DataBase(conf, moltenirond.TYPE_SQLITE_MEMORY)
    ret = database.addBMNode (node1)
    print ret
    assert ret == {'status': 200}
    ret = database.addBMNode (node2)
    print ret
    assert ret == {'status': 200}
    ret = database.addBMNode (node3)
    print ret
    assert ret == {'status': 200}
    ret = database.addBMNode (node4)
    print ret
    assert ret == {'status': 200}

    ret = database.cull (3000)
    print ret
    assert ret['status'] == 200
    assert len(ret['nodes']) == 0

    database.close()
    del database
