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
from molteniron import moltenirond

def compare_provisioned_nodes(lhs, rhs):
    lhs = lhs.copy()
    rhs = rhs.copy()
    rhs['provisioned'] = 'hamzy'
    del lhs['status']
    del lhs['timestamp']
    del rhs['status']
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
        "ipmi_password":   "16f6954d347c4de2",
        "port_hwaddr":     "28:5a:e7:e3:fe:75",
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
        "ipmi_password":   "3a23241cfa516699",
        "port_hwaddr":     "7d:0a:e5:b9:41:9b",
        "cpu_arch":        "ppc64el",
        "cpus":            20L,
        "ram_mb":          51000L,
        "disk_gb":         500L,
        "status":          "ready",
        "provisioned":     "",
        "timestamp":       "",
        "allocation_pool": "10.228.112.8,10.228.112.9"
    }
    node3 = {
        "name":            "pkvmci851",
        "ipmi_ip":         "10.228.118.129",
        "ipmi_user":       "user",
        "ipmi_password":   "4f7e47c57f27ec55",
        "port_hwaddr":     "5a:e8:11:e9:11:a2",
        "cpu_arch":        "ppc64el",
        "cpus":            20L,
        "ram_mb":          51000L,
        "disk_gb":         500L,
        "status":          "used",
        "provisioned":     "7a72eccd-3153-4d08-9848-c6d3b1f18f9f",
        "timestamp":       "1460489832",
        "allocation_pool": "10.228.112.12,10.228.112.13"
    }
    node4 = {
        "name":            "pkvmci853",
        "ipmi_ip":         "10.228.118.133",
        "ipmi_user":       "user",
        "ipmi_password":   "aeff165ded2c2f9f",
        "port_hwaddr":     "4d:18:82:dc:2c:d6",
        "cpu_arch":        "ppc64el",
        "cpus":            20L,
        "ram_mb":          51000L,
        "disk_gb":         500L,
        "status":          "used",
        "provisioned":     "6b8823ef-3e14-4811-98b9-32e27397540d",
        "timestamp":       "1460491566",
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

    ret = database.allocateBM("hamzy", 1)
    print ret
    assert ret['status'] == 200
    assert len(ret["nodes"]) == 1
    compare_provisioned_nodes (ret["nodes"]["node_1"], node1)

    session = database.get_session()
    n1 = session.query(moltenirond.Nodes).filter_by(name=node1["name"]).one()
    session.close()
    ret = database.deallocateBM(n1.id)
    print ret
    assert ret['status'] == 200

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

    ret = database.allocateBM("hamzy", 1)
    print ret
    assert ret['status'] == 200
    assert len(ret["nodes"]) == 1
    compare_provisioned_nodes (ret["nodes"]["node_1"], node1)

    session = database.get_session()
    n1 = session.query(moltenirond.Nodes).filter_by(name=node1["name"]).one()
    session.close()
    ret = database.deallocateBM(n1.ipmi_ip)
    print ret
    assert ret['status'] == 200

    database.close()
    del database
