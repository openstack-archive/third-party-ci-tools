Very simple 3rd party CI dashboard tool
=======================================
It is two python scripts, one is a Flask app that serves up the UI and handles
REST calls. The other one monitors gerrit and records ci results in the database.


Requires:

* mongodb
* python-dev
* python-pip
* virtualenv


Setup the config files.. alter the path in config.py to match the location
of ci-scoreboard.conf. And update the ci-scoreboard.conf to have the right
values for your gerrit account, keyfile, and mongodb server.

To run the server first init things with:

  `./env.sh`

Then source the virtual environment:

   `source ./.venv/bin/activate`

And run the app with:

  `./scoreboard_ui.py runserver`
  `./scoreboard_gerrit_listener.py`

