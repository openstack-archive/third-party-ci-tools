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
        "ipmi_password":   "e23af1e52896cf02",
        "port_hwaddr":     "5d:7e:05:dd:fe:65",
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
        "ipmi_password":   "57212373db56c76a",
        "port_hwaddr":     "7e:41:89:e1:28:03",
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
        "ipmi_password":   "c2f4b0bfa31fe9de",
        "port_hwaddr":     "4f:a7:48:59:6a:a7",
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
        "ipmi_password":   "f99d122fc129c1dd",
        "port_hwaddr":     "a2:0d:bc:ca:c5:a5",
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

    ret = database.doClean(1)
    print ret
    assert ret == {'status': 400, 'message': 'The node at 1 has status ready'}

    ret = database.doClean(2)
    print ret
    assert ret == {'status': 400, 'message': 'The node at 2 has status ready'}

    ret = database.doClean(3)
    print ret
    assert ret == {'status': 200}

    ret = database.doClean(4)
    print ret
    assert ret == {'status': 200}
