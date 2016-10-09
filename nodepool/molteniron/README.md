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

Running inside a Continuous Integration environment
---------------------------------------------------

During the creation of a job, add the following snippet of bash code:

```bash
# Setup MoltenIron and all necessary prerequisites.
# And then call the MI script to allocate a node.
(
  REPO_DIR=/opt/stack/new/third-party-ci-tools
  MI_CONF_DIR=/usr/local/etc/molteniron/
  MI_IP=10.1.2.3 # @TODO - Replace with your IP addr here!

  # Grab molteniron and install it
  git clone https://git.openstack.org/openstack/third-party-ci-tools ${REPO_DIR} || exit 1

  cd ${REPO_DIR}/nodepool/molteniron

  # @BUG Install prerequisite before running pip to install the requisites
  hash mysql_config || sudo apt install -y libmysqlclient-dev

  # Install the requisites for this package
  sudo pip install --upgrade --force-reinstall --requirement requirements.txt

  # Run the python package installation program
  sudo python setup.py install

  if [ -n "${MI_IP}" ]
  then
    # Set the molteniron server IP in the conf file
    sudo sed -i "s/127.0.0.1/${MI_IP}/g" ${MI_CONF_DIR}/conf.yaml
  fi

  export dsvm_uuid
  # NOTE: dsvm_uuid used in the following script, hence the -E
  sudo -E ${REPO_DIR}/nodepool/molteniron/utils/test_hook_configure_mi.sh
) || exit $?
```

and change the MI_IP environment variable to be your MoltenIron server!

During the destruction of a job, add the following snippet of bash code:

```bash
  DSVM_UUID="$(</etc/nodepool/uuid)"
  echo "Cleaning up resources associated with node: ${DSVM_UUID}"
  molteniron release ${DSVM_UUID}
```
