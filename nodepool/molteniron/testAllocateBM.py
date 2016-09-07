#!/usr/bin/env python

import sys
import yaml
from moltenirond import DataBase, TYPE_SQLITE_MEMORY

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
    path = sys.argv[0]
    dirs = path.split("/")
    newPath = "/".join(dirs[:-1]) + "/"

    fobj = open(newPath + "conf.yaml", "r")
    conf = yaml.load(fobj)

    node1 = {
        "name":            "pkvmci816",
        "ipmi_ip":         "10.228.219.134",
        "ipmi_user":       "user",
        "ipmi_password":   "e05cc5f061426e34",
        "port_hwaddr":     "f8:de:29:33:a4:ed",
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
        "ipmi_password":   "0614d63b6635ea3d",
        "port_hwaddr":     "4c:c5:da:28:2c:2d",
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
        "ipmi_password":   "928b056134e4d770",
        "port_hwaddr":     "53:76:c6:09:50:64",
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
        "ipmi_password":   "33f448a4fc176492",
        "port_hwaddr":     "85:e0:73:e9:fc:ca",
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
    database = DataBase(conf, TYPE_SQLITE_MEMORY)
    database.delete_db()
    database.close()
    del database

    database = DataBase(conf, TYPE_SQLITE_MEMORY)
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

    database.close()
    del database

    # 8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----
    database = DataBase(conf, TYPE_SQLITE_MEMORY)
    database.delete_db()
    database.close()
    del database

    database = DataBase(conf, TYPE_SQLITE_MEMORY)
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

    ret = database.allocateBM("hamzy", 2)
    print ret
    assert ret['status'] == 200
    assert len(ret["nodes"]) == 2
    compare_provisioned_nodes (ret["nodes"]["node_1"], node1)
    compare_provisioned_nodes (ret["nodes"]["node_2"], node2)

    database.close()
    del database

    # 8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----8<-----
    database = DataBase(conf, TYPE_SQLITE_MEMORY)
    database.delete_db()
    database.close()
    del database

    database = DataBase(conf, TYPE_SQLITE_MEMORY)
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

    ret = database.allocateBM("hamzy", 3)
    print ret
    assert ret == {'status':  404,
                   'message': ('Not enough available nodes found. '
                   'Found 2, requested 3')}

    database.close()
    del database
