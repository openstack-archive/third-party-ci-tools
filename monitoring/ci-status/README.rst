CI Status Tool
==============

Used for a quick stats collection on Third Party CIs for various OpenStack
projects.

Example usage:
--------------

.. code-block:: bash

    $ ./ci-status.py -v -u datera-ci \\
            -k /home/user/.ssh/id_rsa \\
            -c "Datera CI" -a datera-dsvm-full -t 2 \\
            -j openstack/cinder \\
            --failures --number-of-reports --is-reporting \\
            --jenkins_disagreement

Output:
-------

.. code-block:: text

    Gerrit Query: ssh -i /home/user/.ssh/id_rsa -p 29418 dater
    a-ci@review.openstack.org "gerrit query --format=JSON --comments --current-
    patch-set project:openstack/cinder NOT age:2d  reviewer:Datera CI "

    ##### DATERA-DSVM-FULL #####

    ####### --number-of-reports arg result #######

    40 results in 2 days

    ###### --is-reporting arg result #######

    Review: 263026 --> 2016-07-07T17:02:15+00:00

    ###### --failures arg result #######

    20% failures

    ###### --jenkins-disagreement arg result #######

    0% -1 Jenkins && +1 CI
    20% +1 Jenkins && -1 CI

Minimal usage:
--------------

.. code-block:: bash

    $ ./ci-status.py -u datera-ci -k /home/user/.ssh/id_rsa \\
            -j openstack/cinder -c "Datera CI" -a datera-dsvm-full \\
            --is-reporting

Output:
-------

.. code-block:: text

    ##### DATERA-DSVM-FULL #####
    Review: 263026 --> 2016-07-07T17:02:15+00:00

Passthrough query usage:
------------------------

.. code-block:: bash

    $ ./ci-status.py -u datera-ci -k /home/user/.ssh/id_rsa \\
            -q "reviewer:{Some Body} -j openstack/cinder"

Output:
-------

    Will be a large dictionary

Config example:
---------------

.. code-block:: ini

    # In .gerritqueryrc file in your $HOME directory
    # (or passed in via config option)

    [DEFAULT]
    verbose=True
    host=review.openstack.org
    username=datera-ci
    port=29418
    query_project=openstack/cinder
    keyfile=/home/user/.ssh/id_rsa

    # I would not recommend putting any other flags into this config
    # file otherwise you could introduce silent errors
    # For example:

    # Adding these fields
    ci_account=datera-ci
    ci_runner_name=datera-dsvm-full

    # Then running this command
    # $ ./ci-status.py -c mellanox-ci --is-reporting

    # Would report a false negative for Datera. A CI
    # will show as non-reporting if you provide the
    # ci_account name of one CI and the ci_runner_name of
    # a different CI.  The tool has no way to tell that
    # these values do not belong together and will just
    # report that the CI has not posted within the specified
    # timeframe.

The "--all" flag:
-----------------

.. code-block:: bash

    # In order to use this flag, you must first run this command:
    $ ./ci-status.py --scrape-wiki --force -j openstack/your_project


    # It will fill your .gerritquerycache file with information about
    # the various CIs for your desired OpenStack project

    # Now you're free to run commands with the --all flag
    $ ./ci-status -j openstack/you_project --all --is-reporting


Python Requirements:
--------------------

* arrow
* lxml
* requests
* simplejson
* oslo.config>=3.12.0
