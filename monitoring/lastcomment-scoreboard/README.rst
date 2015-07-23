Last Comment
============

Last Comment is a small script to query OpenStack's gerrit REST API
and produce a report about the status of CI systems.

This can also be used as a CLI tool and used against any type of user (human or bot).

Design
-------

The html based report is a data file plus a static page.


lastcomment is powered by gerrit's REST API and doesn't use any datastore.
Although this means it cannot show results in real time, the data can be
refreshed as frequent as desired.

Dependencies
------------

`requests`

Help
-----

    ./lastcomment.py -h

Generate a Report
------------------


To generate a html report for third party CI accounts on http://localhost:8000/report:

    ./lastcomment.py -f ci.yaml -c 100 --json lastcomment.json
    python -m SimpleHTTPServer

Cloud-init
-----------

To run this on a cloud server using cloud-init and cron use the ``user-data.txt`` file.

Other Uses
----------

To see the last time the user 'Third Party CI'  commented anywhere

    ./lastcomment.py -n 'Third Party CI'

To print the last 30 comments by 'Third Party CI' on the repo openstack/cinder

    ./lastcomment.py -n 'Third Party CI' -m -p openstack/cinder


To print the last 30 votes by 'Third Party CI' on the repo openstack/cinder

    ./lastcomment.py -n 'Third Party CI' -v -p openstack/cinder

To print the contents of the last 30 reviews by 'John Smith'

    ./lastcomment.py -n 'John Smith'  -m

To specify a yaml file names.yaml containing projects and names to iterate through

    ./lastcomment.py -f names.yaml

To print statistics on third party CI accounts:

    ./lastcomment.py -c 100 -f ci.yaml -v

To generate a html report for cinder's third party CI accounts on http://localhost:8000/report:

    ./lastcomment.py -f ci.yaml -c 100 --json lastcomment.json
    python -m SimpleHTTPServer


