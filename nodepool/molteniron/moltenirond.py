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

import MySQLdb
from BaseHTTPServer import HTTPServer,BaseHTTPRequestHandler
import sys
import time
import os
import socket
import yaml
import datetime
import json

#DEBUG = True
DEBUG = False

class MoltenIronHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        self.data_string = self.rfile.read(int(self.headers['Content-Length']))
        response = self.parse(self.data_string)
        self.send_reply(response)

    def send_reply(self, response):
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
                node = request
                response = database.addBMNode(node)
            elif method == 'allocate':
                response = database.allocateBM(request['owner_name'],
                                               request['number_of_nodes'])
            elif method == 'release':
                response = database.deallocateOwner(request['owner_name'])
            elif method == 'get_field':
                response = database.get_field(request['owner_name'],
                                              request['field_name'])
        except Exception as e:
            database.rollback()
            response = {'status': 400, 'message': str(e)}

        database.commit()
        return response

class DataBase():
    """
    This class may be used access the molten iron database.
    """

    def __init__(self, config):
        self.conf = config
        self.dbm = MySQLdb.connect(user=self.conf["sqlUser"],
                                   passwd=self.conf["sqlPass"])
        self.cursor = self.dbm.cursor()
        self.dbm.autocommit(False)
        self.cursor.execute("USE MoltenIron")

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

    def query(self, qry, *args):
        """
        Pass a query to the database.

        Note: if this query modifies the database, the modifications will
        not take effect until commit() is called

        query: the text of the query.  It may optionally formatting arguments
        such as "%s".

        *args: if the argument query contains any formatting arguments, include
        the values that should be substituted here.
        """
        if DEBUG:
            print qry
        self.cursor.execute(qry, args)
        result = self.cursor.fetchall()
        return result

    def commit(self):
        """
        Call this function to commit any previous queries that have been
        passed to this object.
        """
        if DEBUG:
            print "COMMIT"
        self.dbm.commit()

    def rollback(self):
        """
        Call this function to commit any previous queries that have been
        passed to this object.
        """
        if DEBUG:
            print "ROLLBACK"
        self.dbm.rollback()

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

        allocatedIPs = self.getips(virtmachine).split("\n")
        allocated = 0
        for ip in allocatedIPs:
            if ip != "":
                allocated += 1

        howMany = howMany - allocated
        if howMany <= 0:
            return "\n".join(allocatedIPs)

        # TODO(maurosr): Fix the disneyland of race conditions.
        result = self.query("SELECT * FROM Nodes WHERE status = 'ready'")
        if len(result) >= howMany:
            return self.allocateBM(virtmachine, howMany)
        else:
            logstring = (str(howMany) + " nodes were requested, but " +
                         str(len(result)) + " are available")
            log(self.conf, logstring)
            return "error: not enough nodes"

    def allocateBM(self, owner_name, how_many):
        """
        Checkout machines from the database and return necessary info
        """
        # Get a list of IDs for nodes that are free
        results = self.query("SELECT id FROM Nodes WHERE status = 'ready'")

        # If we don't have enough nodes return an error
        if (len(results) < how_many):
            response = {'status': 404, 'message': 'Not enough available nodes found'}
            return response

        nodes = {}
        for i in range(how_many):
            node_id = int(results[i][0])
            # Update the node to the in use state
            self.query("UPDATE Nodes SET status = 'used', provisioned = "
                       "%s, timestamp = %s WHERE id = %s",
                       owner_name, long(time.time()), node_id)

            # Get necessary info for response 
            data = self.query("SELECT id, ipmi_ip, port_hwaddr, ipmi_user, "
                              "ipmi_password, cpu_arch, cpus, ram_mb, disk_gb "
                              "FROM Nodes where id = %s",
                              node_id)
            # Create dict from SQL response
            node = {}
            node['id'] = data[0][0]
            node['ipmi_ip'] = data[0][1]
            node['port_hwaddr'] = data[0][2]
            node['ipmi_user'] = data[0][3]
            node['ipmi_password'] = data[0][4]
            node['cpu_arch'] = data[0][5]
            node['cpus'] = int(data[0][6])
            node['ram_mb'] = int(data[0][7])
            node['disk_gb'] = int(data[0][8])

            # Log that we're allocating the node
            logstring = ("allocating node id: " + str(data[0][0]) +
                         "for " + owner_name)
            log(self.conf, logstring)

            # Get the allocated IPs for the node and add them to the node's dict
            data = self.query("SELECT ip FROM IPs WHERE node_id = %(node_id)s"
                              % {'node_id' : node['id']} )
            allocation_pool = []
            for ip_row in data:
                allocation_pool.append(ip_row[0])
            node['allocation_pool'] = ','.join(allocation_pool)

            # Add the node to the nodes dict
            nodes['node_' + str(i)]=node

        response = {'status': 200, 'nodes': nodes}
        return response

    def deallocateBM(self, id):
        """
        Given the ID of a node (or the IPMI IP), de-allocate that node.

        This changes the node status of that node from "used" to "dirty.  It
        also schedules that node for cleaning.
        """
        node_id=id
        data = self.query("SELECT id, ipmi_ip, name FROM Nodes WHERE id=%s",
                          int(id))
        ipmi_ip = data[0][1]
        name = data[0][2]

        self.query("UPDATE Nodes SET status=\"ready\", provisioned="
                   "\"\", timestamp=-1 WHERE id=%s", int(node_id))

        logstring = "de-allocating node " + name + " (id: " + \
                    str(node_id) + ", ip: " + str(ipmi_ip) + ")"

        log(self.conf, logstring)

        response={'status':200}
        return response

    def deallocateOwner(self, name):
        """
        Given the name of a BM owner, de-allocate all nodes in use by
        that owner.
        """
        results = self.query("SELECT id FROM Nodes WHERE provisioned=%s",
                             name)
        for result in results:
            try:
                self.deallocateBM(result[0])
            except Exception as e:
                message = ("Failed to deallocate node with ID %(node_id)" %
                           {'node_id': result[0]})
                response = {'status':400,'message':message}
                return response
                
        response = {'status':200}
        return response

    def addBMNode(self, node):
        """
        Add a new node to molten iron.
        """

        #check if it already exists
        result = self.query("SELECT id FROM Nodes WHERE name=%s", node['node_name'])
        if len(result) != 0:
            status=400
            response = {'status':400, 'message': 'Node already exists'}
            return response

        logstring = "adding node %(node_name)s ipmi_ip: %(ipmi_ip)s" % node
        log(conf, logstring)

        # Add Node to database
        # Note: ID is always 0 as it is an auto-incrementing field
        insert_node_query=("INSERT INTO Nodes Values(0, '%(node_name)s', '%(ipmi_ip)s', "
                           "'%(ipmi_user)s', '%(ipmi_password)s', "
                           "'%(port_hwaddr)s', '%(cpu_arch)s', %(cpus)s, %(ram_mb)s,"
                           "%(disk_gb)s, 'ready', '', '')" % node)
        self.query(insert_node_query)

        node['id'] = self.cursor.lastrowid

        # Add IPs to database
        # Note: id is always 0 as it is an auto-incrementing field
        ips = node['allocation_pool'].split(',')
        for ip in ips:
            insert_ip_query=("INSERT INTO IPs Values(0, %(node_id)s, '%(ip)s')" %
                             {'node_id':node['id'], 'ip':ip})
            self.query(insert_ip_query)

        response = {'status':200}
        return response

    def removeBMNode(self, ID, force):
        """
        Remove a node from molten iron

        If force is False it will not remove nodes that are in use.  If force
        is True then it will always remove the node.
        """
        if(force):

            data = self.query("SELECT id, ipmi_ip, name FROM Nodes WHERE "
                              "id=%s", int(ID))
            logstring = ("deleting node " + data[0][2] + ", ipmi_ip: " +
                         str(data[0][1]) + ", node id: " + str(data[0][0]))
            log(conf, logstring)
            self.query("DELETE FROM Nodes WHERE id=%s", int(ID))

        else:
            data = self.query("SELECT id, ipmi_ip, name FROM Nodes WHERE "
                              "id=%s", int(ID))
            logstring = ("deleting node " + data[0][2] + ", ipmi_ip: " +
                         str(data[0][1]) + ", node id: " + str(data[0][0]))
            log(conf, logstring)
            self.query("DELETE FROM Nodes WHERE ID=%s and status != "
                       "\"used\"", int(ID))

    def cull(self, maxSeconds):
        """
        If any node has been in use for longer than maxSeconds, deallocate that
        node.

        Nodes that are deallocated in this way get their state set to "dirty".
        They are also scheduled for cleaning.
        """
        results = self.query("SELECT id, timestamp FROM Nodes")

        for result in results:
            currentTime = time.time()
            if result[1] not in ('', '-1'):
                elapsedTime = currentTime - int(result[1])
                if float(elapsedTime) >= float(maxSeconds):
                    logstring = ("node " + str(result[0]) + " has been"
                                 "allocated for too long.")
                    log(self.conf, logstring)
                    self.deallocateBM(result[0])

    def doClean(self, ipmi_ip, node_id):
        """
        This function is used to clean a node.
        """
        database = DataBase(self.conf)
        database.query("UPDATE Nodes SET status=\"ready\" WHERE id=%s",
                       node_id)
        database.commit()
        logstring = "The node at " + str(ipmi_ip) + " has been cleaned."
        log(self.conf, logstring)

    def getips(self, ownerName):
        """
        Given the name of a node owner, return all IPs allocated to that node.

        IPs are returned as a string separated by the newline character.
        """
        results = self.query("SELECT ipmi_ip FROM Nodes WHERE provisioned=%s",
                             ownerName)
        returnstr = ""
        for result in results:
            returnstr += result[0] + "\n"
        return returnstr

    def get_field(self, owner, field):
        """
        Given the name of a node and the name of a field, return the field.
        """
        query_str = ("SELECT %(field)s FROM Nodes WHERE provisioned='%(owner)s'"
                     % {'field':field, 'owner':owner})
        result = self.query(query_str)
        response = {'status':200, field:result[0][0]}
        return response

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
    moltenirond = HTTPServer((mi_addr, mi_port), handler)
    print 'Listening...'
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
