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

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ciwatch import models
from ciwatch.config import cfg, get_projects


engine = create_engine(cfg.database.connection)
Session = sessionmaker()
Session.configure(bind=engine)
models.Base.metadata.create_all(engine)
session = Session()


def create_projects():
    for name in get_projects():
        get_or_create(models.Project,
                      commit_=False,
                      name=name)
    session.commit()


def update_or_create_comment(commit_=True, **kwargs):
    comment = session.query(models.Comment).filter_by(
        ci_server_id=kwargs['ci_server_id'],
        patch_set_id=kwargs['patch_set_id']).scalar()
    if comment is not None:
        for key, value in kwargs.iteritems():
            setattr(comment, key, value)
    else:
        session.add(models.Comment(**kwargs))
    if commit_:
        session.commit()


def get_or_create(model, commit_=True, **kwargs):
    result = session.query(model).filter_by(**kwargs).first()
    if not result:
        result = model(**kwargs)
        session.add(result)
        if commit_:
            session.commit()
    return result
