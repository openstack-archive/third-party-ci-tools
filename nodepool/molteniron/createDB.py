#!/usr/bin/env python

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

