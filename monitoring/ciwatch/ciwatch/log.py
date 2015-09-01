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

import logging
from logging import handlers
import os

from ciwatch.config import cfg


def setup_logger(name):

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s]"
                                      "  %(message)s")

    file_handler =\
        handlers.RotatingFileHandler(name,
                                     maxBytes=1048576,
                                     backupCount=2,)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)
    return logger


DATA_DIR =\
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/data'
if cfg.Data.data_dir:
    DATA_DIR = cfg.Data.data_dir

logger = setup_logger(DATA_DIR + '/ci-watch.log')
