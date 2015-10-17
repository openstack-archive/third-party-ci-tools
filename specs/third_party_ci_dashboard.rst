::

  Copyright (c) 2015 Triniplex.

  This work is licensed under a Creative Commons Attribution 3.0
  Unported License.
  http://creativecommons.org/licenses/by/3.0/legalcode

===============================
CI Dashboard
===============================

https://storyboard.openstack.org/#!/story/2000013

The goal of this project is to create a dashboard for the
collection of statistics, monitoring, and usage information.

Problem Description
===================

Currently, there is no single, unified tool for the collection
and display of information which gives the developer the ability
to see how a system is performing against Jenkins. The creation
of a CI Dashboard was discussed at the Kilo Design
Summit [#kilo-third-party-items]_.

Proposed Change
===============

Implement a CI Dashboard system which would be used by operators
cross-project to determine the health of a third party system. The Third Party
CI Dashboard will collect statistics from Gerrit and generate reports which
can be used by distributed project teams as an indicator of the state
of a particular CI system, relative to other CI systems.

Initially, the Dashboard will be used to aggregate data for analysis, in order
to aide the developer in making a determination as to whether a CI system is
functioning as intended.

Alternatives
------------

None

Implementation
==============

The Dashboard will be modular in design in order to
maximize the re-usability and portability of the individual components.
The Dashboard will be composed of the following services:

#. The primary interface for the Dashboard will be a Pecan/WSME REST API
   service. The service will provide a single point through which
   operators may query the Dashboard data.

#. The API will be used by an AngularJS webclient, which may be built as
   a separate component to query the Dashboard data. A command line client
   (python-radar) will also allow the query and display of the data in
   textual form.

#. The data collected by the Dashboard will be stored in a MySQL database.
   The object relational mapper used for this will be SQLAlchemy, as
   this technology already has significant usage across OpenStack projects.

#. Data will be periodically collected from the Gerrit REST API by a
   python daemon.  The initial frequency for the data collection has been
   set at five (5) minutes.

Discussion of the process of evaluation and the methods which the Dashboard
will use to determine CI system health has begun on the third party mailing
list and community members should contribute their ideas to the
etherpad [#third-party-ci-dashboard-plan]_.


Assignee(s)
-----------

Primary assignee:
  - Steve Weston (steve.weston)

Work Items
----------

TBD

Repositories
------------

During the Kilo Design Summit the group discussed
review of the radar repository [#radar-repo]_.

Servers
-------

The server for the test environment is online and hosted at:
http://dashboard.triniplex.com [#third-party-ci-dashboard-server]_.

DNS Entries
-----------

TBD

Documentation
-------------

The documentation should be created as part of the third-party
manual.

Security
--------

None

Testing
-------

TBD

Dependencies
============

- This will require coordination from CI operators
  across all projects

References
==========

.. [#kilo-third-party-items] Session Kilo Design Summit
   https://etherpad.openstack.org/p/kilo-third-party-items
.. [#third-party-ci-dashboard-plan] CI Dashboard Planning
   https://etherpad.openstack.org/p/Third-Party-CI-Dashboard-InitialPlanning
.. [#ci-dashboard-repo] CI Dashboard Github Repository
   https://github.com/Triniplex/third-party-ci-dashboard.git
.. [#radar-repo] https://github.com/openstack/radar
.. [#third-party-ci-dashboard-server] http://dashboard.triniplex.com

