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

from BaseHTTPServer import HTTPServer,BaseHTTPRequestHandler
import sys
import time
import os
import socket
import yaml
import datetime
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.sql import select, insert, update, delete
from sqlalchemy.sql import and_, or_, not_
from contextlib import contextmanager

DEBUG = False

class MoltenIronHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        response = self.parse(self.data_string)
        self.send_reply(response)

    def send_reply(self, response):
        if DEBUG:
            print "send_reply: response = %s" % (response,)
        # pop the status code off the response json and send it
        status_code = response.pop('status')
        self.send_response(status_code)
        self.send_header('Content-type','application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response))

    def parse(self,request_string):
        """
        Handle the request. Returns the response of the request
        """
        database = DataBase(conf)
        try:
            #Try to json-ify the request_string
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
        except Exception as e:
############database.rollback()
            response = {'status': 400, 'message': str(e)}

########database.commit()

        if DEBUG:
            print "parse: response = %s" % (response,)

        return response

class Nodes(declarative_base()):

    __tablename__ = 'Nodes'

    id            = Column(Integer, primary_key=True)
    name          = Column(String)
    ipmi_ip       = Column(String)
    ipmi_user     = Column(String)
    ipmi_password = Column(String)
    port_hwaddr   = Column(String)
    cpu_arch      = Column(String)
    cpus          = Column(Integer)
    ram_mb        = Column(Integer) # @TODO - why not just ram?
    disk_gb       = Column(Integer) # @TODO - why not just disk?
    status        = Column(String)
    provisioned   = Column(String)
    timestamp     = Column(Integer) #@TODO Long

    def map(self):
        # @TODO - don't hardcode
        return {"name":          self.name,
                "ipmi_ip":       self.ipmi_ip,
                "ipmi_user":     self.ipmi_user,
                "ipmi_password": self.ipmi_password,
                "port_hwaddr":   self.port_hwaddr,
                "cpu_arch":      self.cpu_arch,
                "cpus":          self.cpus,
                "ram_mb":        self.ram_mb,
                "disk_gb":       self.disk_gb,
                "status":        self.status,
                "provisioned":   self.provisioned,
                "timestamp":     self.timestamp}

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
        fmt = fmt.replace ('\n', ' ')

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

    # from sqlalchemy.dialects.mysql import INTEGER

    # @TODO INTEGER(unsigned=True)
    # @TODO NOT NULL
    # @TODO AUTO_INCREMENT
    id            = Column(Integer, primary_key=True)
    # @TODO INTEGER(unsigned=True)
    # @TODO NOT NULL
    node_id       = Column(Integer, ForeignKey("Nodes.id"))
    ip            = Column(String)

    def __repr__(self):

        fmt = """<Node(id='%d',
node_id='%d',
ip='%s' />"""
        fmt = fmt.replace ('\n', ' ')

        return fmt % (self.id,
                      self.node_id,
                      self.ip)

class DataBase():
    """
    This class may be used access the molten iron database.
    """

    def __init__(self, config):
        self.conf = config

        user     = self.conf["sqlUser"]
        passwd   = self.conf["sqlPass"]
        host     = "127.0.0.1"

        self.database = "MoltenIron"
        self.engine   = create_engine("mysql://%s:%s@%s/" % (user, passwd, host,), echo=DEBUG)

        self.element_info = [
            # The following are returned from the query call

            #field_name       length  special_fmt skip
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

    def close(self):
        self.engine.dispose ()

    def get_session(self):
        """
        Get a SQL academy session from the pool
        """
        Session = sessionmaker(bind=self.engine)
        session = Session()

        #@TODO - is there a better way to do this?
        session.execute ("USE %s;" % (self.database,))

        return session

    def get_connection(self):
        """
        Get a SQL academy connection from the pool
        """
        conn = self.engine.connect()

        #@TODO - is there a better way to do this?
        conn.execute ("USE %s;" % (self.database,))

        return conn

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            if DEBUG:
                print "Exception caught in session_scope: %s" % (e,)
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def connection_scope(self):
        """Provide a transactional scope around a series of operations."""
        conn = self.get_connection()
        try:
            yield conn
        except Exception as e:
            if DEBUG:
                print "Exception caught in connection_scope: %s" % (e,)
            raise
        finally:
            conn.close()

    def delete_db(self):
        conn = self.engine.connect()
        #@TODO - is there a better way to do this?
        conn.execute("DROP DATABASE IF EXISTS %s;" % (self.database,))
        conn.close()

    def create_db(self):
        conn = self.engine.connect()
        #@TODO - is there a better way to do this?
        conn.execute("CREATE DATABASE IF NOT EXISTS MoltenIron;")
        conn.execute("USE MoltenIron; CREATE TABLE IF NOT EXISTS Nodes ("
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
        conn.execute("USE MoltenIron; CREATE TABLE IF NOT EXISTS IPs ("
                     "id INT UNSIGNED NOT NULL AUTO_INCREMENT,"
                     "node_id INT UNSIGNED NOT NULL,"
                     "ip VARCHAR(50),"
                     "PRIMARY KEY (id),"
                     "FOREIGN KEY (node_id) REFERENCES Nodes(id)"
                     ");")
        conn.close()

    # @TODO this function is weird
    def requestBM(self, virtmachine, howMany):
        """
        Given the name of a requester and a number of nodes, attempt to
        increase the number of allocated nodes to that amount.

        Returns a list of IPs which are allocated to the requester
        separated by newlines.  This includes IPs which may have been
        previously allocated.

        If the requester already has virtual machines registered with molten
        iron, this function will not "re-allocate".  If a node currently has
        3 BM nodes and requests 5 BM nodes, an additional 2 nodes will be
        allocated.
        """

        allocatedIPs = self.getips(virtmachine)
        allocated    = len(allocatedIPs)
        howMany      = howMany - allocated
        if howMany <= 0:
            return "\n".join(allocatedIPs)

        session = self.get_session()
        count = session.query(Nodes).filter_by(status="ready").count()
        session.close()

        #@TODO - race condition
        if count >= howMany:
            return self.allocateBM(virtmachine, howMany)
        else:
            log(self.conf,
                "Error: %d nodes were requested, but %d are available" % (howMany, count, ))
            return {'status': 404, 'message': "Not enough available nodes found"}

    def allocateBM(self, owner_name, how_many):
        """
        Checkout machines from the database and return necessary info
        """

        try:
            with self.session_scope() as session, \
                 self.connection_scope() as conn:

                # Get a list of IDs for nodes that are free
                count = session.query(Nodes).filter_by(status="ready").count()

                # If we don't have enough nodes return an error
                if (count < how_many):
                    fmt = "Not enough available nodes found. Found %d, requested %d"
                    return {'status': 404, 'message': fmt % (count, how_many, )}

                nodes_allocated = {}

                for i in range(how_many):
                    first_ready = session.query(Nodes).filter_by(status="ready").first()

                    id = first_ready.id
                    # We have everything we need from node

                    log(self.conf,
                        "allocating node id: %d for %s" % (id, owner_name, ))

                    # Update the node to the in use state
                    stmt = update(Nodes)
                    stmt = stmt.where(Nodes.id==id)
                    stmt = stmt.values(status="dirty",
                                       provisioned=owner_name,
                                       timestamp=long(time.time()))

                    conn.execute(stmt)

                    # Refresh the data
                    session.close()
                    session          = self.get_session()
                    first_ready      = session.query(Nodes).filter_by(id=id).one()
                    first_ready_node = first_ready.map()

                    # Query the associated IP table
                    ips = session.query(IPs).filter_by(node_id=first_ready.id)

                    allocation_pool = []
                    for ip in ips:
                        allocation_pool.append(ip.ip)
                    first_ready_node['allocation_pool'] = ','.join(allocation_pool)

                    # Add the node to the nodes dict
                    nodes_allocated['node_%d' % (id, )] = first_ready_node

        except Exception as e:

            if DEBUG:
                print "Exception caught in deallocateBM: %s" % (e,)

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str (e)}

        return {'status': 200, 'nodes': nodes_allocated}

    def deallocateBM(self, id):
        """
        Given the ID of a node (or the IPMI IP), de-allocate that node.

        This changes the node status of that node from "used" to "dirty.  It
        also schedules that node for cleaning.
        """

        try:
            with self.session_scope() as session, \
                 self.connection_scope() as conn:

                query = session.query(Nodes.id, Nodes.ipmi_ip, Nodes.name)

                if type(id) == str and "." in id:
                    # If an ipmi_ip was passed
                    query = query.filter_by(ipmi_ip=id)
                else:
                    query = query.filter_by(id=id)

                node = query.one()

                log(self.conf,
                    "de-allocating node (%d, %s)" % (node.id, node.ipmi_ip,))

                stmt = update(Nodes)
                stmt = stmt.where(Nodes.id==node.id)
                stmt = stmt.values(status="dirty", provisioned="", timestamp=-1)

                conn.execute(stmt)

        except Exception as e:

            if DEBUG:
                print "Exception caught in deallocateBM: %s" % (e,)

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str (e)}

        return {'status': 200}

    def deallocateOwner(self, name):
        """
        Given the name of a BM owner, de-allocate all nodes in use by
        that owner.
        """

        try:
            with self.session_scope() as session:
                nodes = session.query(Nodes.id).filter_by(provisioned=name)
                for node in nodes:
                    self.deallocateBM(node.id)
        except Exception as e:
            if DEBUG:
                print "Exception caught in deallocateOwner: %s" % (e,)
            message = "Failed to deallocate node with ID %d" % (node.id,)
            return {'status': 400, 'message': message}

        return {'status': 200}

    def addBMNode(self, node):
        """
        Add a new node to molten iron.

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
                print "addBMNode: node = %s" % (node, )

            with self.session_scope() as session, \
                 self.connection_scope() as conn:

                # Check if it already exists
                count = session.query(Nodes).filter_by(name=node['name']).count()

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
                if node.has_key('status'):
                    stmt = stmt.values(status=node['status'])
                if node.has_key('provisioned'):
                    stmt = stmt.values(provisioned=node['provisioned'])
                if node.has_key('timestamp'):
                    stmt = stmt.values(timestamp=node['timestamp'])

                if DEBUG:
                    print stmt.compile().params

                conn.execute(stmt)

                # Refresh the data
                session.close()
                session = self.get_session()
                new_node = session.query(Nodes).filter_by(name=node['name']).one()

                # new_node is now a proper Node

                # Add IPs to database
                # Note: id is always 0 as it is an auto-incrementing field
                ips = node['allocation_pool'].split(',')
                for ip in ips:
                    stmt = insert(IPs)
                    stmt = stmt.values(node_id=new_node.id, ip=ip)

                    if DEBUG:
                        print stmt.compile().params

                    conn.execute(stmt)

        except Exception as e:

            if DEBUG:
                print "Exception caught in addBMNode: %s" % (e,)

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str (e)}

        return {'status': 200}

    def removeBMNode(self, ID, force):
        """
        Remove a node from molten iron

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
                    stmt = stmt.where(IPs.id==ip.id)
                    conn.execute(stmt)

                stmt = delete(Nodes)

                if force:
                    stmt = stmt.where(and_ (Nodes.id==query.id,
                                            Nodes.status!="used"))
                else:
                    stmt = stmt.where(Nodes.id==query.id)

                conn.execute(stmt)

        except Exception as e:

            if DEBUG:
                print "Exception caught in removeBMNode: %s" % (e,)

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str (e)}

        return {'status': 200}

    def cull(self, maxSeconds):
        """
        If any node has been in use for longer than maxSeconds, deallocate that
        node.

        Nodes that are deallocated in this way get their state set to "dirty".
        They are also scheduled for cleaning.
        """

        nodes_culled = {}

        try:
            with self.session_scope() as session:

                nodes = session.query(Nodes)

                for node in nodes:
                    if node.timestamp in ('', '-1'):
                        continue

                    # NOTE: time() can return fractional values. Ex: 1460560140.47
                    elapsedTime = time.time() - float (node.timestamp)
                    if float(elapsedTime) < float(maxSeconds):
                        continue

                    logstring = ("node %d has been allocated for too long."
                                % (node.id,))
                    log(self.conf, logstring)

                    if DEBUG:
                        print logstring

                    self.deallocateBM(node.id)

                    # Add the node to the nodes dict
                    nodes_culled['node_%d' % (node.id, )] = node.map()

        except Exception as e:

            if DEBUG:
                print "Exception caught in cull: %s" % (e,)

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str (e)}

        return {'status': 200, 'nodes': nodes_culled}

    # @TBD why ipmi_ip? This is already in the database.
    def doClean(self, ipmi_ip, node_id):
        """
        This function is used to clean a node.
        """

        try:
            with self.session_scope() as session, \
                 self.connection_scope() as conn:

                query = session.query(Nodes)
                query = query.filter_by(id=node_id)
                node  = query.one()

                if node.status in ('ready', ''):
                    return {'status': 400,
                            'message': 'The node at %d has status %s'
                                        % (node.id, node.status,)}

                logstring = "The node at %s has been cleaned." % (ipmi_ip,)
                log(self.conf, logstring)

                stmt = update(Nodes)
                stmt = stmt.where(Nodes.id==node_id)
                stmt = stmt.values(status="ready")

                conn.execute(stmt)

        except Exception as e:

            if DEBUG:
                print "Exception caught in doClean: %s" % (e,)

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str (e)}

        return {'status': 200}

    # @TODO shouldn't it be get_ips
    # @TODO shouldn't it return allocation_pool rather than ipmi_ip?
    def getips(self, ownerName):
        """
        Given the name of a node owner, return all IPs allocated to that node.

        IPs are returned as a string separated by the newline character.
        """

        ips = []

        try:
            with self.session_scope() as session:

                query = session.query(Nodes)
                nodes = query.filter_by(provisioned=ownerName)

                for node in nodes:
                    ips.append (node.ipmi_ip)

        except Exception as e:

            if DEBUG:
                print "Exception caught in getips: %s" % (e,)

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str (e)}

        return {'status': 200, 'ips': ips}

    # @TODO there are multiple results on owner
    def get_field(self, ownerName, field):
        """
        Given the name of a node and the name of a field, return the field.
        """

        if not hasattr (Nodes, field):
            return {'status': 400,
                    'message': 'field %s does not exist' % (field,)}

        field_values = []

        try:
            with self.session_scope() as session:

                query = session.query(Nodes)
                nodes = query.filter_by(provisioned=ownerName)

                if DEBUG:
                    print ("There are %d entries provisioned by %s"
                           % (nodes.count(), ownerName,))

                for node in nodes:
                    field_values.append(getattr(node, field))

        except Exception as e:

            if DEBUG:
                print "Exception caught in get_field: %s" % (e,)

            # Don't send the exception object as it is not json serializable!
            return {'status': 400, 'message': str (e)}

        return {'status': 200, 'field': field_values}

    def setup_status(self):
        """
        Setup the status formatting strings depending on skipped elements, lengths, and types.
        """

        self.result_separator = "+"
        for (_, length, _, skip) in self.element_info:
            if skip: continue
            self.result_separator += '-' * (1 + length + 1) + "+"

        self.description_line = "+"
        for (field, length, _, skip) in self.element_info:
            if skip: continue
            self.description_line += " " + field + ' ' * (length - len (field)) + " +"

        index = 0
        self.format_line = "|"
        for (_, length, special_fmt, skip) in self.element_info:
            if skip: continue
            if special_fmt is int:
                self.format_line += " {%d:<%d} |" % (index, length)
            elif special_fmt is str:
                self.format_line += " {%d:%d} |" % (index, length)
            elif special_fmt is float:
                self.format_line += " {%d:<%d.%d} |" % (index, length, length - 2)
            index += 1

    def status(self):
        """
        Return a table that details the state of each bare metal node.

        Currently this table is being created manually, there is probably a
        better way to be doing this.
        """
        results = self.query("SELECT * from Nodes;")

        result = ""

        result += self.result_separator + "\n"
        result += self.description_line + "\n"
        result += self.result_separator + "\n"

        for elements in results:

            timeString = ""
            try:
                if int(elements[5]) != -1:
                    elapsedTime = time.time() - int(elements[5])
                    hours = int(elapsedTime / 60 / 60)
                    minutes = int(elapsedTime / 60) % 60
                    seconds = int(elapsedTime) % 60
                    timeString = "{0:0>2}".format(str(hours)) + \
                        ":" + "{0:0>2}".format(str(minutes)) + ":" \
                        + "{0:0>2}".format(str(seconds))
            except Exception:
                pass
            elements = elements + (timeString, )

            new_elements  = []
            index         = 0
            for (_, _, _, skip) in self.element_info:
                if not skip:
                    new_elements.append (elements[index])
                index += 1

            result += self.format_line.format (*new_elements) + "\n"

        result += self.result_separator + "\n"

        return result


def help():
    result = ("Usage:\n"
              "micli.py allocate owner_name number_of_nodes\n"
              "         release owner_name\n"
              "         free node_id(s)\n"
              "         add node_name ipmi_ip ipmi_user ipmi_password "
              "allocation_pool port_hwaddr cpu_arch cpus "
              "ram_mb disk_gb ...\n"
              "         get-field field_name owner_name\n"
              "         delete node_id\n"
              "         cull max_seconds")
    return result


#packet format:
#messageID`totalPackets`packetNum`message
def send(ip, port, message, messageID):
    """
    Send a string to a destination using a UDP packet. Long strings will
    be broken up and sent in several packets.

    Right now everything is plaintext (to speed up creation of prototype)
    Eventually it should probably be binary-ified

    Message syntax: messageID`totalPackets`packetNum`message
    """
    maxMessageSize = 200  # Is this the best size?
    delimiter = "`"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    messageChunks = []
    index = 0
    while index < len(message):
        if index + maxMessageSize <= len(message):
            messageChunks += [message[index:index + maxMessageSize]]
            index += maxMessageSize
        else:
            messageChunks += [message[index:]]
            index = len(message)
    for index, chunk in enumerate(messageChunks):
        newMessage = str(messageID) + delimiter \
            + str(len(messageChunks)) + delimiter \
            + str(index) + delimiter + chunk
        if DEBUG:
            print "sending\n", newMessage, "\nto", ip, ", port", port
        sock.sendto(newMessage, (ip, port))


def resourceManager(conf):
    """
    This thread ensures that no node is held for longer than the maximum
    allowed time.
    """
    maxTime = conf["maxTime"]

    while True:
        database = DataBase(conf)
        database.cull(maxTime)
        database.commit()
        time.sleep(5)


def listener(conf):
    mi_addr = str(conf['serverIP'])
    mi_port = int(conf['mi_port'])
    handler = MoltenIronHandler
    print 'Listening... to %s:%d' % (mi_addr, mi_port,)
    moltenirond = HTTPServer((mi_addr, mi_port), handler)
    moltenirond.serve_forever()


def cleanup():
    """
    This function kills any running instances of molten iron.

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
    """
    Write a message to the log file.
    """
    cleanLogs(conf)
    logdir = conf["logdir"]
    now = datetime.datetime.today()

    fname = str(now.day) + "-" + str(now.month) \
        + "-" + str(now.year) + ".log"

    timestamp = "{0:0>2}".format(str(now.hour)) + ":" + \
        "{0:0>2}".format(str(now.minute)) \
        + ":" + "{0:0>2}".format(str(now.second))

    message = timestamp + "  " + message + "\n"

    #check if logdir exists, if not create it
    if not os.path.isdir(logdir):
        os.popen("mkdir " + logdir)

    fobj = open(logdir + "/" + fname, "a")
    fobj.write(message)
    fobj.close()


def cleanLogs(conf):
    """
    Find and delete log files that have been around for too long.
    """
    logdir = conf["logdir"]
    maxDays = conf["maxLogDays"]
    if not os.path.isdir(logdir):
        return
    now = datetime.datetime.today()
    logs = os.popen("ls " + logdir).read().split("\n")
    for log in logs:
        elements = log[:-1 * len(".log")].split("-")
        if len(elements) != 3:
            continue
        newDate = datetime.datetime(int(elements[2]), int(elements[1]),
                                    int(elements[0]))
        if (now - newDate).days > maxDays:
            os.popen("rm " + logdir + "/" + log)


if __name__ == "__main__":
    path = sys.argv[0]
    dirs = path.split("/")
    newPath = "/".join(dirs[:-1]) + "/"

    fobj = open(newPath + "conf.yaml", "r")
    conf = yaml.load(fobj)

    listener(conf)
