# Copyright (c) 2015 Tintri. All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref


Base = declarative_base()


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True)

    def __repr__(self):
        return "<Project(name='%s')>" % self.name


class PatchSet(Base):
    __tablename__ = "patch_sets"

    id = Column(Integer, primary_key=True)
    created = Column(DateTime)
    # ref = Column(String(64), unique=True)
    ref = Column(String(64))  # Why are there duplicate refs?
    # Verified only represents Jenkin's vote
    verified = Column(Boolean, nullable=True, default=None)

    commit_message = Column(String(4096))

    project_id = Column(Integer, ForeignKey('projects.id'))
    project = relationship("Project", backref=backref('patch_sets',
                                                      order_by=id))

    def __repr__(self):
        return "<PatchSet(created='%s', ref='%s')>" % (
            self.created, self.ref)


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True)
    result = Column(String(64))
    log_url = Column(String(1024), nullable=True, default=None)

    ci_server_id = Column(Integer, ForeignKey('ci_servers.id'))
    ci_server = relationship("CiServer", backref=backref('comments',
                                                         order_by=id))

    patch_set_id = Column(Integer, ForeignKey('patch_sets.id'))
    patch_set = relationship("PatchSet", backref=backref('comments',
                                                         order_by=id))

    def __repr__(self):
        return "<Comment(log_url='%s', result='%s')>" % (
            self.log_url, self.result)


class CiServer(Base):
    __tablename__ = "ci_servers"

    id = Column(Integer, primary_key=True)
    name = Column(String(128))

    # Official OpenStack CIs are trusted (e.g., Jenkins)
    trusted = Column(Boolean, default=False)

    ci_owner_id = Column(Integer, ForeignKey('ci_owners.id'))
    ci_owner = relationship('CiOwner', backref=backref('ci_servers',
                                                       order_by=id))

    def __repr__(self):
        return "<CiServer(name='%s')>" % self.name


class CiOwner(Base):
    __tablename__ = "ci_owners"

    id = Column(Integer, primary_key=True)
    name = Column(String(128), unique=True)

    def __repr__(self):
        return "<CiOwner(name='%s')>" % self.name
