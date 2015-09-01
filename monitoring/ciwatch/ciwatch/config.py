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

import os

from iniparse import INIConfig

_fdir = os.path.dirname(os.path.realpath(__file__))
_conf_dir = os.path.dirname(_fdir)
cfg = INIConfig(open(_conf_dir + '/ci-watch.conf'))


def get_projects():
    projects = []
    for name in cfg.misc.projects.split(','):
        projects.append(name)
    return projects
