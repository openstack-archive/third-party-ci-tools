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

import os
import sys
import yaml


def SQL(query):
    print(os.popen("mysql -u root -p --execute=\"" + query + "\"").read())


def main():
    path = sys.argv[0]
    dirs = path.split("/")
    newPath = "/".join(dirs[:-1]) + "/"
    fobj = open(newPath + "conf.yaml", "r")
    conf = yaml.load(fobj)

    # Create the SQL User
    SQL("CREATE USER '"+conf["sqlUser"]+"'@'localhost' "
        "IDENTIFIED BY '"+conf["sqlPass"]+"';")
    SQL("GRANT ALL ON MoltenIron.* TO '"+conf["sqlUser"]+"'@'localhost';")
    return 0

if __name__ == "__main__":
    main()
