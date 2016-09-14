MoltenIron overview
===================

MoltenIron maintains a pool of bare metal nodes.

Starting
--------

Before starting the server for the first time, the createDB.py
script must be run.

To start the server:
```bash
moltenirond-helper start
```

To stop the server:
```bash
moltenirond-helper stop
```

MoltenIron client
-----------------

Use the molteniron client (molteniron) to communicate with the server. For
usage information type:
```bash
molteniron -h
```

For usage of a specific command use:
```bash
molteniron [command] -h
```

MoltenIron commands
-------------------

command   | description
-------   | -----------
add       | Add a node
allocate  | Allocate a node
release   | Release a node
get_field | Get a specific field in a node
set_field | Set a specific field with a value in a node
status    | Return the status of every node
delete_db | Delete every database entry

Configuration of MoltenIron
---------------------------

Configuration of MoltenIron is specified in the file conf.yaml.

"B)" means that this configuration option is required for both the client and
the server.  "C)" means that it is required only for the client.  "S)" means
it is only required for the server.

usage | key        | description
----- | ---        | -----------
B)    | mi_port    | the port that the server uses to respond to commands.
C)    | serverIP   | The IP address of the server.  This is only used by
      |            | clients.
S)    | maxTime    | The maximum amount of time, in seconds, that a node
      |            | is allowed to be allocated to a particular BM node.
S)    | logdir     | The path to the directory where the logs should be
      |            | stored.
S)    | maxLogDays | The amount of time, in days, to keep old logs.
S)    | sqlUser    | The username to use for the MI server.  This user
      |            | will automatically be generated when createDB.py is run.
S)    | sqlPass    | The password of sqlUser

Running testcases
-----------------

The suite of testcases is checked by tox.  But, before you can run tox, you
need to change the local yaml configuration file to point to the log
directory.

```bash
(LOG=$(pwd)/testenv/log; sed -i -r -e 's,^(logdir: )(.*)$,\1'${LOG}',' conf.yaml; rm -rf testenv/; tox -e testenv)
```
