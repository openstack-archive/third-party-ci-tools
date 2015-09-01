#!/usr/bin/env python

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

from os.path import join, dirname

from setuptools import setup

import ciwatch


setup(
    name='ci-watch',
    version=ciwatch.__version__,
    long_description=open(join(dirname(__file__), 'README.md')).read(),
    entry_points={
        'console_scripts': [
            'ci-watch-server = ciwatch:main',
            'ci-watch-populate-database = ciwatch.populate:main',
            'ci-watch-stream-events = ciwatch.events:main',
            ],
        },
    install_requires=[
        "flask",
        "sqlalchemy",
        "iniparse",
        "paramiko",
    ]
)
