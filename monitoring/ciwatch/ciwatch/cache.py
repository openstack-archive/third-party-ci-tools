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

from functools import wraps

from flask import request
from werkzeug.contrib.cache import SimpleCache


cache = SimpleCache()


def cached(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = _get_cache_key()
        result = cache.get(key)
        if result is None:
            result = func(*args, **kwargs)
            cache.set(key, result, timeout=60)
        return result
    return wrapper


def _get_cache_key():
    args = request.args
    return request.path + str([(key, args[key]) for key in sorted(args)])
