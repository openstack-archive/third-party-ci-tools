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

import _mysql, MySQLdb, sys, os, yaml

def SQL(query):
    print os.popen("mysql -u root -p --execute=\"" + query + "\"").read()

def main():
    path = sys.argv[0]
    dirs = path.split("/")
    newPath = "/".join(dirs[:-1]) + "/"
    fobj = open(newPath + "conf.yaml", "r")
    conf = yaml.load(fobj)

    # Create the MoltenIron database
    SQL("CREATE DATABASE IF NOT EXISTS MoltenIron;")

    # Create the Nodes table
    SQL("USE MoltenIron; CREATE TABLE IF NOT EXISTS Nodes ("
        "id INT UNSIGNED NOT NULL AUTO_INCREMENT,"
        "name VARCHAR(50),"
        "ipmi_ip VARCHAR(50),"
        "ipmi_user VARCHAR(50),"
        "ipmi_password VARCHAR(50), "
        "port_hwaddr VARCHAR(50),"
        "cpu_arch VARCHAR(50),"
        "cpus INT,"
        "ram_mb INT,"
        "disk_gb INT,"
        "status VARCHAR(20),"
        "provisioned VARCHAR(50),"
        "timestamp LONG,"
        "PRIMARY KEY (id)"
        ");")

    # Create the IPs table
    SQL("USE MoltenIron; CREATE TABLE IF NOT EXISTS IPs ("
        "id INT UNSIGNED NOT NULL AUTO_INCREMENT,"
        "node_id INT UNSIGNED NOT NULL,"
        "ip VARCHAR(50),"
        "PRIMARY KEY (id),"
        "FOREIGN KEY (node_id) REFERENCES Nodes(id)"
        ");")

    # Create the SQL User
    SQL("CREATE USER '"+conf["sqlUser"]+"'@'localhost' IDENTIFIED BY '"+conf["sqlPass"]+"';")
    SQL("GRANT ALL ON MoltenIron.* TO '"+conf["sqlUser"]+"'@'localhost';")
    return 0

if __name__ == "__main__":
    main()
