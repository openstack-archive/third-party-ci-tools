# CI Watch

## Configuration

Configuration is stored in the `ci-watch.conf` file. Importantly, you can
specify a directory to store the `third-party-ci.log` file (data\_dir) as well
as the database to connect to. Look at `ci-watch.conf.sample` for an example.

Other settings should be self explanatory based on the provided configuration
file.

## Installation

From this folder, run the following commands.

```
pip install -r requirements.txt
# Note that this step requires the `ci-watch.conf` file.
pip install -e .
```

These instructions are for development and testing installations.

## Usage

At the moment, this package provides three commands.

`ci-watch-server`.
Launch a development server.

`ci-watch-stream-events`.
Stream events from Gerrit and append valid events to `third-party-ci.log`.

`ci-watch-populate-database`.
Add all entries from `third-party-ci.log` to the database.

## State of the project

This project is a work in progress and the code is pretty rough in some places.

## TODO

* Add tests.
* Use a different cache other than SimpleCache. It is not threadsafe. We
  should use something like redis instead.

These items are far from the only work needed for this project.


## Acknowledgements

This code was originally forked from John Griffith's sos-ci project. Some of it
can still be found in the code and configuration file.
