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

from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import calendar
from datetime import datetime
import json
import os
import sys
import time
import traceback
import yaml
import argparse

from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.sql import insert, update, delete
from sqlalchemy.sql import and_
from sqlalchemy.types import TIMESTAMP
from sqlalchemy.schema import MetaData, Table

import sqlalchemy_utils
from sqlalchemy.exc import OperationalError

DEBUG = False

metadata = MetaData()


class JSON_encoder_with_DateTime(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat()

        return json.JSONEncoder.default(self, o)


# We need to turn BaseHTTPRequestHandler into a "new-style" class for
# Python 2.x
# NOTE: URL is over two lines :(
# http://stackoverflow.com/questions/1713038/super-fails-with-error-typeerror-
# argument-1-must-be-type-not-classobj
class OBaseHTTPRequestHandler(BaseHTTPRequestHandler, object):
    pass

# We need to pass in conf into MoltenIronHandler, so make a class factory
# to do that
# NOTE: URL is over two lines :(
# http://stackoverflow.com/questions/21631799/how-can-i-pass-parameters-to-a-
# requesthandler
def MakeMoltenIronHandlerWithConf(conf):
    class MoltenIronHandler(OBaseHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            # Note this *needs* to be done before call to super's class!
            self.conf = conf
            super(OBaseHTTPRequestHandler, self).__init__(*args, **kwargs)

        def do_POST(self):
            CL = 'Content-Length'
            self.data_string = self.rfile.read(int(self.headers[CL]))
            response = self.parse(self.data_string)
            self.send_reply(response)

        def send_reply(self, response):
            if DEBUG:
                print("send_reply: response = %s" % (response,))
            # get the status code off the response json and send it
            status_code = response['status']
            self.send_response(status_code)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response,
                                        cls=JSON_encoder_with_DateTime))

        def parse(self, request_string):
            """Handle the request. Returns the response of the request """
            try:
                database = DataBase(self.conf)
                # Try to json-ify the request_string
                request = json.loads(request_string)
                method = request.pop('method')
                if method == 'add':
                    response = database.addBMNode(request)
                elif method == 'allocate':
                    response = database.allocateBM(request['owner_name'],
                                                   request['number_of_nodes'])
                elif method == 'release':
                    response = database.deallocateOwner(request['owner_name'])
                elif method == 'get_field':
                    response = database.get_field(request['owner_name'],
                                                  request['field_name'])
                elif method == 'set_field':
                    response = database.set_field(request['id'],
                                                  request['key'],
                                                  request['value'])
                elif method == 'status':
                    response = database.status()
                elif method == 'delete_db':
                    response = database.delete_db()
                database.close()
                del database
            except Exception as e:
                response = {'status': 400, 'message': str(e)}

            if DEBUG:
                print("parse: response = %s" % (response,))

            return response

    return MoltenIronHandler


class Nodes(declarative_base()):

    __tablename__ = 'Nodes'

    # from sqlalchemy.dialects.mysql import INTEGER

    # CREATE TABLE `Nodes` (
    #        id INTEGER NOT NULL AUTO_INCREMENT, #@TODO UNSIGNED
    #        name VARCHAR(50),
    #        ipmi_ip VARCHAR(50),
    #        ipmi_user VARCHAR(50),
    #        ipmi_password VARCHAR(50),
    #        port_hwaddr VARCHAR(50),
    #        cpu_arch VARCHAR(50),
    #        cpus INTEGER,
    #        ram_mb INTEGER,
    #        disk_gb INTEGER,
    #        status VARCHAR(20),
    #        provisioned VARCHAR(50),
    #        timestamp TIMESTAMP NULL,
    #        PRIMARY KEY (id)
    # )

    id = Column('id', Integer, primary_key=True)
    name = Column('name', String(50))
    ipmi_ip = Column('ipmi_ip', String(50))
    ipmi_user = Column('ipmi_user', String(50))
    ipmi_password = Column('ipmi_password', String(50))
    port_hwaddr = Column('port_hwaddr', String(50))
    cpu_arch = Column('cpu_arch', String(50))
    cpus = Column('cpus', Integer)
    ram_mb = Column('ram_mb', Integer)
    disk_gb = Column('disk_gb', Integer)
    status = Column('status', String(20))
    provisioned = Column('provisioned', String(50))
    timestamp = Column('timestamp', TIMESTAMP)

    __table__ = Table(__tablename__,
                      metadata,
                      id,
                      name,
                      ipmi_ip,
                      ipmi_user,
                      ipmi_password,
                      port_hwaddr,
                      cpu_arch,
                      cpus,
                      ram_mb,
                      disk_gb,
                      status,
                      provisioned,
                      timestamp)

    def map(self):
        return {key: value for key, value
                in self.__dict__.items()
                if not key.startswith('_') and not callable(key)}

    def __repr__(self):
        fmt = """<Node(name='%s',
ipmi_ip='%s',
ipmi_user='%s',
ipmi_password='%s',
port='%s',
cpu_arch='%s',
cpus='%d',
ram='%d',
disk='%d',
status='%s',
provisioned='%s',
timestamp='%s'/>"""
        fmt = fmt.replace('\n', ' ')

        return fmt % (self.name,
                      self.ipmi_ip,
                      self.ipmi_user,
                      self.ipmi_password,
                      self.port_hwaddr,
                      self.cpu_arch,
                      self.cpus,
                      self.ram_mb,
                      self.disk_gb,
                      self.status,
                      self.provisioned,
                      self.timestamp)


class IPs(declarative_base()):

    __tablename__ = 'IPs'

    # CREATE TABLE `IPs` (
    #         id INTEGER NOT NULL AUTO_INCREMENT, #@TODO INTEGER(unsigned=True)
    #         node_id INTEGER, #@TODO UNSIGNED
    #         ip VARCHAR(50),
    #         PRIMARY KEY (id),
    #         FOREIGN KEY(node_id) REFERENCES `Nodes` (id)
    # )

    id = Column('id',
                Integer,
                primary_key=True)
    node_id = Column('node_id',
                     Integer,
                     ForeignKey("Nodes.id"))
    ip = Column('ip',
                String(50))

    __table__ = Table(__tablename__,
                      metadata,
                      id,
                      node_id,
                      ip)

    def __repr__(self):

        fmt = """<Node(id='%d',
node_id='%d',
ip='%s' />"""
        fmt = fmt.replace('\n', ' ')

        return fmt % (self.id,
                      self.node_id,
                      self.ip)

TYPE_MYSQL = 1
# Is there a mysql memory path?
TYPE_SQLITE = 3
TYPE_SQLITE_MEMORY = 4


class DataBase():
    """This class may be used access the molten iron database.  """

    def __init__(self,
                 config,
                 db_type=TYPE_MYSQL):
        self.conf = config

        self.user = self.conf["sqlUser"]
        self.passwd = self.conf["sqlPass"]
        self.host = "127.0.0.1"
        self.database = "MoltenIron"
        self.db_type = db_type

        engine = None
        try:
            # Does the database exist?
            engine = self.create_engine()
            c = engine.connect()
            c.close()
        except OperationalError:
            sqlalchemy_utils.create_database(engine.url)
            engine = self.create_engine()
            c = engine.connect()
            c.close()
        self.engine = engine

        self.create_metadata()

        self.element_info = [
            # The following are returned from the query call

            # field_name       length  special_fmt skip
            ("id",                 4, int,        False),
            ("name",               6, str,        False),
            ("ipmi_ip",            9, str,        False),
            ("ipmi_user",         11, str,        False),
            ("ipmi_password",     15, str,        False),
            ("port_hwaddr",       19, str,        False),
            ("cpu_arch",          10, str,        False),
            ("cpus",               6, int,        False),
            ("ram_mb",             8, int,        False),
            ("disk_gb",            9, int,        False),
            ("status",             8, str,        False),
            ("provisioned",       13, str,        False),
            # We add timeString
            ("time",              14, float,      False),
        ]
        self.setup_status()

    def create_engine(self):
        engine = None

        if self.db_type == TYPE_MYSQL:
            engine = create_engine("mysql://%s:%s@%s/%s"
                                   % (self.user,
                                      self.passwd,
                                      self.host,
                                      self.database, ),
                                   echo=DEBUG)
        elif self.db_type == TYPE_SQLITE_MEMORY:
            engine = create_engine('sqlite:///:memory:',
                                   echo=DEBUG)
        elif self.db_type == TYPE_SQLITE:
            engine = create_engine("sqlite://%s:%s@%s/%s"
                                   % (self.user,
                                      self.passwd,
                                      self.host,
                                      self.database, ),
                                   echo=DEBUG)

        return engine

    def close(self):
        if DEBUG:
            print("close: Calling engine.dispose()")
        self.engine.dispose()
        if DEBUG:
            print("close: Finished")

    def get_session(self):
        """Get a SQL academy session from the pool """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        return session

    def get_connection(self):
        """Get a SQL academy connection from the pool """
        conn = self.engine.connect()

        return conn

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations. """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            if DEBUG:
                print("Exception caught in session_scope: %s %s"
                      % (e, traceback.format_exc(4), ))
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def connection_scope(self):
        """Provide a transactional scope around a series of operations. """
        conn = self.get_connection()
        try:
            yield conn
        except Exception as e:
            if DEBUG:
                print("Exception caught in connection_scope: %s" % (e,))
            raise
        finally:
            conn.close()

    def delete_db(self):
        # Instead of:
        #   IPs.__table__.drop(self.engine, checkfirst=True)
        #   Nodes.__table__.drop(self.engine, checkfirst=True)
        metadata.drop_all(self.engine, checkfirst=True)

        return {'status': 200}

    def create_metadata(self):
        # Instead of:
        #   Nodes.__table__.create(self.engine, checkfirst=True)
        #   IPs.__table__.create(self.engine, checkfirst=True)
        if DEBUG:
            print("create_metadata: Calling metadata.create_all")
        metadata.create_all(self.engine, checkfirst=True)
        if DEBUG:
            print("create_metadata: Finished")

    def to_timestamp(self, ts):
        timestamp = None
        if self.db_type == TYPE_MYSQL:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S", ts)
        elif self.db_type in (TYPE_SQLITE, TYPE_SQLITE_MEMORY):
            c = calendar.timegm(ts)
            timestamp = datetime.fromtimestamp(c)
        return timestamp

    def from_timestamp(self, timestamp):
        ts = None
        if self.db_type == TYPE_MYSQL:
            ts = time.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        elif self.db_type == TYPE_SQLITE:
            ts = timestamp.timetuple()
        return ts

    def allocateBM(self, owner_name, how_many):
        """Checkout machines from the database and return necessary info """

        try:
            with self.session_scope() as session, \
                     self.connection_scope() as conn:

                # Get a list of IDs for nodes that are free
                count = session.query(Nodes).filter_by(status="ready").count()

                # If we don't have enough nodes return an error
                if (count < how_many):
                    fmt = "Not enough available nodes found."
                    fmt += " Found %d, requested %d"
                    return {'status': 404,
                            'message': fmt % (count, how_many, )}

                nodes_allocated = {}

                for i in range(how_many):
                    first_ready = session.query(Nodes)
                    first_ready = first_ready.filter_by(status="ready")
                    first_ready = first_ready.first()

                    id = first_ready.id
                    # We have everything we need from node

                    log(self.conf,
                        "allocating node id: %d for %s" % (id, owner_name, ))

                    timestamp = self.to_timestamp(time.gmtime())

                    # Update the node to the in use state
                    stmt = update(Nodes)
                    stmt = stmt.where(Nodes.id == id)
                    stmt = stmt.values(status="dirty",
                                       provisioned=owner_name,
                                       timestamp=timestamp)
                    conn.execute(stmt)

                    # Refresh the data
                    session.close()
                    session = self.get_session()

                    first_ready = session.query(Nodes).filter_by(id=id).one()

                    first_ready_node = first_ready.map()

                    # Query the associated IP table
                    ips = session.query(IPs).filter_by(node_id=first_ready.id)

                    allocation_pool = []
                    for ip in ips:
                        allocation_pool.append(ip.ip)
                    first_ready_node['allocation_pool'] \
                        = ','.join(allocation_pool)

                    # Add the node to the nodes dict
                    nodes_allocated['node_%d' % (id, )] = first_ready_node

        except Exception as e:

            if DEBUG:
                print("Exception caught in deallocateBM: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200, 'nodes': nodes_allocated}

    def deallocateBM(self, id):
        """Given the ID of a node (or the IPMI IP), de-allocate that node.

        This changes the node status of that node from "used" to "ready."
        """

        try:
            with self.session_scope() as session, \
                 self.connection_scope() as conn:

                query = session.query(Nodes.id, Nodes.ipmi_ip, Nodes.name)

                if (type(id) == str or type(id) == unicode) and ("." in id):
                    # If an ipmi_ip was passed
                    query = query.filter_by(ipmi_ip=id)
                else:
                    query = query.filter_by(id=id)

                node = query.one()

                log(self.conf,
                    "de-allocating node (%d, %s)" % (node.id, node.ipmi_ip,))

                stmt = update(Nodes)
                stmt = stmt.where(Nodes.id == node.id)
                stmt = stmt.values(status="ready",
                                   provisioned="",
                                   timestamp=None)

                conn.execute(stmt)

        except Exception as e:

            if DEBUG:
                print("Exception caught in deallocateBM: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200}

    def deallocateOwner(self, owner_name):
        """Deallocate all nodes in use by a given BM owner.  """

        try:
            with self.session_scope() as session:
                nodes = session.query(Nodes.id)
                nodes = nodes.filter_by(provisioned=owner_name)

                if nodes.count() == 0:
                    message = "No nodes are owned by %s" % (owner_name,)

                    return {'status': 400, 'message': message}

                for node in nodes:
                    self.deallocateBM(node.id)
        except Exception as e:
            if DEBUG:
                print("Exception caught in deallocateOwner: %s" % (e,))
            message = "Failed to deallocate node with ID %d" % (node.id,)
            return {'status': 400, 'message': message}

        return {'status': 200}

    def addBMNode(self, node):
        """Add a new node to molten iron.

        ex:
        node = {u'name': u'test',
                u'ipmi_user': u'user',
                u'port_hwaddr': u'de:ad:be:ef:00:01',
                u'disk_gb': 32,
                u'cpu_arch': u'ppc64el',
                u'ram_mb': 2048,
                u'cpus': 8,
                u'allocation_pool': u'0.0.0.1,0.0.0.2',
                u'ipmi_password': u'password',
                u'ipmi_ip': u'0.0.0.0'}
        """

        try:
            if DEBUG:
                print("addBMNode: node = %s" % (node, ))

            with self.session_scope() as session, \
                    self.connection_scope() as conn:

                # Check if it already exists
                query = session.query(Nodes)
                query = query.filter_by(name=node['name'])
                count = query.count()

                if count == 1:
                    return {'status': 400, 'message': "Node already exists"}

                log(self.conf,
                    "adding node %(name)s ipmi_ip: %(ipmi_ip)s" % node)

                # Add Node to database
                # Note: ID is always 0 as it is an auto-incrementing field
                stmt = insert(Nodes)
                stmt = stmt.values(name=node['name'])
                stmt = stmt.values(ipmi_ip=node['ipmi_ip'])
                stmt = stmt.values(ipmi_user=node['ipmi_user'])
                stmt = stmt.values(ipmi_password=node['ipmi_password'])
                stmt = stmt.values(port_hwaddr=node['port_hwaddr'])
                stmt = stmt.values(cpu_arch=node['cpu_arch'])
                stmt = stmt.values(cpus=node['cpus'])
                stmt = stmt.values(ram_mb=node['ram_mb'])
                stmt = stmt.values(disk_gb=node['disk_gb'])
                stmt = stmt.values(status='ready')
                if 'status' in node:
                    stmt = stmt.values(status=node['status'])
                if 'provisioned' in node:
                    stmt = stmt.values(provisioned=node['provisioned'])
                if 'timestamp' in node:
                    timestamp_str = node['timestamp']
                    if DEBUG:
                        print("timestamp_str = %s" % (timestamp_str, ))
                    if len(timestamp_str) != 0 and timestamp_str != "-1":
                        ts = time.gmtime(float(timestamp_str))
                        timestamp = self.to_timestamp(ts)
                        if DEBUG:
                            print("timestamp = %s" % (timestamp, ))
                        stmt = stmt.values(timestamp=timestamp)
                if DEBUG:
                    print(stmt.compile().params)

                conn.execute(stmt)

                # Refresh the data
                session.close()
                session = self.get_session()

                query = session.query(Nodes).filter_by(name=node['name'])
                new_node = query.one()

                # new_node is now a proper Node with an id

                # Add IPs to database
                # Note: id is always 0 as it is an auto-incrementing field
                ips = node['allocation_pool'].split(',')
                for ip in ips:
                    stmt = insert(IPs)
                    stmt = stmt.values(node_id=new_node.id, ip=ip)

                    if DEBUG:
                        print(stmt.compile().params)

                    conn.execute(stmt)

        except Exception as e:

            if DEBUG:
                print("Exception caught in addBMNode: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200}

    def removeBMNode(self, ID, force):
        """Remove a node from molten iron

        If force is False it will not remove nodes that are in use.  If force
        is True then it will always remove the node.
        """

        try:
            with self.session_scope() as session, \
                 self.connection_scope() as conn:

                query = session.query(Nodes.id, Nodes.ipmi_ip, Nodes.name)
                query = query.filter_by(id=int(ID))
                query = query.one()

                log(self.conf,
                    ("deleting node (id=%d, ipmi_ip=%s, name=%s"
                     % (query.id, query.ipmi_ip, query.name,)))

                ips = session.query(IPs).filter_by(node_id=int(ID))
                for ip in ips:
                    stmt = delete(IPs)
                    stmt = stmt.where(IPs.id == ip.id)
                    conn.execute(stmt)

                stmt = delete(Nodes)

                if force:
                    stmt = stmt.where(and_(Nodes.id == query.id,
                                           Nodes.status != "used"))
                else:
                    stmt = stmt.where(Nodes.id == query.id)

                conn.execute(stmt)

        except Exception as e:

            if DEBUG:
                print("Exception caught in removeBMNode: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200}

    def cull(self, maxSeconds):
        """If any node has been in use for longer than maxSeconds, deallocate
        that node.

        Nodes that are deallocated in this way get their state set to "dirty".
        They are also scheduled for cleaning.
        """

        if DEBUG:
            print("cull: maxSeconds = %s" % (maxSeconds, ))

        nodes_culled = {}

        try:
            with self.session_scope() as session:

                nodes = session.query(Nodes)

                if DEBUG:
                    print("There are %d nodes" % (nodes.count(), ))

                for node in nodes:

                    if DEBUG:
                        print(node)

                    if node.timestamp in ('', '-1', None):
                        continue

                    currentTime = self.to_timestamp(time.gmtime())
                    elapsedTime = currentTime - node.timestamp
                    if DEBUG:
                        print("currentTime         = %s"
                              % (currentTime, ))
                        print("node.timestamp      = %s"
                              % (node.timestamp, ))
                        print("elapsedTime         = %s"
                              % (elapsedTime, ))
                        print("elapsedTime.seconds = %s"
                              % (elapsedTime.seconds, ))

                    if elapsedTime.seconds < int(maxSeconds):
                        continue

                    logstring = ("node %d has been allocated for too long."
                                 % (node.id,))
                    log(self.conf, logstring)

                    if DEBUG:
                        print(logstring)

                    self.deallocateBM(node.id)

                    # Add the node to the nodes dict
                    nodes_culled['node_%d' % (node.id, )] = node.map()

        except Exception as e:

            if DEBUG:
                print("Exception caught in cull: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200, 'nodes': nodes_culled}

    def doClean(self, node_id):
        """This function is used to clean a node. """

        try:
            with self.session_scope() as session, \
                 self.connection_scope() as conn:

                query = session.query(Nodes)
                query = query.filter_by(id=node_id)
                node = query.one()

                if node.status in ('ready', ''):
                    return {'status': 400,
                            'message': 'The node at %d has status %s'
                            % (node.id, node.status,)}

                logstring = "The node at %s has been cleaned." % \
                            (node.ipmi_ip,)
                log(self.conf, logstring)

                stmt = update(Nodes)
                stmt = stmt.where(Nodes.id == node_id)
                stmt = stmt.values(status="ready")

                conn.execute(stmt)

        except Exception as e:

            if DEBUG:
                print("Exception caught in doClean: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200}

    # @TODO shouldn't it return allocation_pool rather than ipmi_ip?
    def get_ips(self, owner_name):
        """Return all IPs allocated to a given node owner

        IPs are returned as a list of strings
        """

        ips = []

        try:
            with self.session_scope() as session:

                query = session.query(Nodes)
                nodes = query.filter_by(provisioned=owner_name)

                for node in nodes:
                    ips.append(node.ipmi_ip)

        except Exception as e:

            if DEBUG:
                print("Exception caught in get_ips: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200, 'ips': ips}

    def get_field(self, owner_name, field):
        """Return entries list with id, field for a given owner, field.  """

        if not hasattr(Nodes, field):
            return {'status': 400,
                    'message': 'field %s does not exist' % (field,)}

        results = []

        try:
            with self.session_scope() as session:

                query = session.query(Nodes)
                nodes = query.filter_by(provisioned=owner_name)

                if DEBUG:
                    print("There are %d entries provisioned by %s"
                          % (nodes.count(), owner_name,))

                if nodes.count() == 0:
                    return {'status': 404,
                            'message': '%s does not own any nodes'
                                       % owner_name}

                for node in nodes:
                    result = {'id': node.id}
                    result['field'] = getattr(node, field)

                    results.append(result)

        except Exception as e:

            if DEBUG:
                print("Exception caught in get_field: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200, 'result': results}

    def set_field(self, id, key, value):
        """Given an identifying id, set specified key to the passed value. """

        if not hasattr(Nodes, key):
            return {'status': 400,
                    'message': 'field %s does not exist' % (key,)}

        try:
            with self.session_scope() as session, \
                 self.connection_scope() as conn:

                query = session.query(Nodes)
                nodes = query.filter_by(id=id)

                if nodes.count() == 0:
                    return {'status': 404,
                            'message': 'Node with id of %s does not exist!'
                                       % id}

                nodes.one()

                kv = {key: value}

                stmt = update(Nodes)
                stmt = stmt.where(Nodes.id == id)
                stmt = stmt.values(**kv)

                conn.execute(stmt)

        except Exception as e:

            if DEBUG:
                print("Exception caught in set_field: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200}

    def setup_status(self):
        """Setup the status formatting strings depending on skipped elements,
        lengths, and types.
        """

        self.result_separator = "+"
        for (_, length, _, skip) in self.element_info:
            if skip:
                continue
            self.result_separator += '-' * (1 + length + 1) + "+"

        self.description_line = "+"
        for (field, length, _, skip) in self.element_info:
            if skip:
                continue
            self.description_line += (" " +
                                      field +
                                      ' ' * (length - len(field)) +
                                      " +")

        index = 0
        self.format_line = "|"
        for (_, length, special_fmt, skip) in self.element_info:
            if skip:
                continue
            if special_fmt is int:
                self.format_line += " {%d:<%d} |" % (index, length)
            elif special_fmt is str:
                self.format_line += " {%d:%d} |" % (index, length)
            elif special_fmt is float:
                self.format_line += " {%d:<%d.%d} |" \
                                    % (index, length, length - 2)
            index += 1

    def status(self):
        """Return a table that details the state of each bare metal node.

        Currently this table is being created manually, there is probably a
        better way to be doing this.
        """

        result = ""

        try:
            with self.session_scope() as session:

                query = session.query(Nodes)

                result += self.result_separator + "\n"
                result += self.description_line + "\n"
                result += self.result_separator + "\n"

                for node in query:

                    timeString = ""
                    try:
                        if node.timestamp is not None:
                            elapsedTime = datetime.utcnow() - node.timestamp
                            timeString = str(elapsedTime)
                    except Exception:
                        pass

                    elements = (node.id,
                                node.name,
                                node.ipmi_ip,
                                node.ipmi_user,
                                node.ipmi_password,
                                node.port_hwaddr,
                                node.cpu_arch,
                                node.cpus,
                                node.ram_mb,
                                node.disk_gb,
                                node.status,
                                node.provisioned,
                                timeString)

                    new_elements = []
                    index = 0
                    for (_, _, _, skip) in self.element_info:
                        if not skip:
                            new_elements.append(elements[index])
                        index += 1

                    result += self.format_line.format(*new_elements) + "\n"

                result += self.result_separator + "\n"

        except Exception as e:

            if DEBUG:
                print("Exception caught in status: %s" % (e,))

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str(e)}

        return {'status': 200, 'result': result}


def listener(conf):
    mi_addr = str(conf['serverIP'])
    mi_port = int(conf['mi_port'])
    handler_class = MakeMoltenIronHandlerWithConf(conf)
    print('Listening... to %s:%d' % (mi_addr, mi_port,))
    moltenirond = HTTPServer((mi_addr, mi_port), handler_class)
    moltenirond.serve_forever()


def cleanup():
    """This function kills any running instances of molten iron.

    This should be called when starting a new instance of molten iron.
    """
    ps = os.popen("ps aux | grep python | grep moltenIronD.py").read()
    processes = ps.split("\n")
    pids = []
    for process in processes:
        if "grep" in process:
            continue
        words = process.split(" ")
        actual = []
        for word in words:
            if word != "":
                actual += [word]
        words = actual
        if len(words) > 1:
            pids += [words[1]]
    myPID = os.getpid()

    for pid in pids:
        if int(pid) == int(myPID):
            continue
        os.system("kill -9 " + pid)


def log(conf, message):
    """Write a message to the log file. """
    cleanLogs(conf)
    logdir = conf["logdir"]
    now = datetime.today()

    fname = str(now.day) + "-" + str(now.month) \
        + "-" + str(now.year) + ".log"

    timestamp = "{0:0>2}".format(str(now.hour)) + ":" + \
        "{0:0>2}".format(str(now.minute)) \
        + ":" + "{0:0>2}".format(str(now.second))

    message = timestamp + "  " + message + "\n"

    # check if logdir exists, if not create it
    if not os.path.isdir(logdir):
        os.popen("mkdir " + logdir)

    fobj = open(logdir + "/" + fname, "a")
    fobj.write(message)
    fobj.close()


def cleanLogs(conf):
    """Find and delete log files that have been around for too long. """
    logdir = conf["logdir"]
    maxDays = conf["maxLogDays"]
    if not os.path.isdir(logdir):
        return
    now = datetime.today()
    logs = os.popen("ls " + logdir).read().split("\n")
    for log in logs:
        elements = log[:-1 * len(".log")].split("-")
        if len(elements) != 3:
            continue
        newDate = datetime(int(elements[2]),
                           int(elements[1]),
                           int(elements[0]))
        if (now - newDate).days > maxDays:
            os.popen("rm " + logdir + "/" + log)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Molteniron daemon")
    parser.add_argument("-c",
                        "--conf-dir",
                        action="store",
                        type=str,
                        dest="conf_dir",
                        help="The directory where configuration is stored")

    args = parser.parse_args ()

    if args.conf_dir:
        if not os.path.isdir (args.conf_dir):
            msg = "Error: %s is not a valid directory" % (args.conf_dir, )
            print >> sys.stderr, msg
            sys.exit(1)

        yaml_file = os.path.realpath("%s/conf.yaml" % (args.conf_dir, ))
    else:
        yaml_file = "/usr/local/etc/molteniron/conf.yaml"

    with open(yaml_file, "r") as fobj:
        conf = yaml.load(fobj)

        listener(conf)
