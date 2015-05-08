# Copyright (c) 2014 Mirantis Inc.
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

import datetime

from radar.api.auth.token_storage import storage


class Token(object):
    def __init__(self, access_token, refresh_token, expires_in, user_id,
                 is_valid=True):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.expires_at = datetime.datetime.utcnow() + \
            datetime.timedelta(seconds=expires_in)
        self.user_id = user_id
        self.is_valid = is_valid


class AuthorizationCode(object):
    def __init__(self, code, user_id):
        self.code = code
        self.user_id = user_id


class MemoryTokenStorage(storage.StorageBase):

    def __init__(self):
        self.token_set = set([])
        self.auth_code_set = set([])

    def save_token(self, access_token, expires_in, refresh_token, user_id):
        token_info = Token(access_token=access_token,
                           expires_in=expires_in,
                           refresh_token=refresh_token,
                           user_id=user_id)

        self.token_set.add(token_info)

    def check_access_token(self, access_token):
        token_entry = None
        for token_info in self.token_set:
            if token_info.access_token == access_token:
                token_entry = token_info

        if not token_entry:
            return False

        now = datetime.datetime.utcnow()
        if now > token_entry.expires_at:
            token_entry.is_valid = False
            return False

        return True

    def get_access_token_info(self, access_token):
        for token_info in self.token_set:
            if token_info.access_token == access_token:
                return token_info
        return None

    def remove_token(self, token):
        pass

    def check_refresh_token(self, refresh_token):
        for token_info in self.token_set:
            if token_info.refresh_token == refresh_token:
                return True

        return False

    def get_refresh_token_info(self, refresh_token):
        for token_info in self.token_set:
            if token_info.refresh_token == refresh_token:
                return token_info

        return None

    def invalidate_refresh_token(self, refresh_token):
        token_entry = None
        for entry in self.token_set:
            if entry.refresh_token == refresh_token:
                token_entry = entry
                break

        self.token_set.remove(token_entry)

    def save_authorization_code(self, authorization_code, user_id):
        self.auth_code_set.add(AuthorizationCode(authorization_code, user_id))

    def check_authorization_code(self, code):
        code_entry = None
        for entry in self.auth_code_set:
            if entry.code["code"] == code:
                code_entry = entry
                break

        if not code_entry:
            return False

        return True

    def get_authorization_code_info(self, code):
        for entry in self.auth_code_set:
            if entry.code["code"] == code:
                return entry

        return None

    def invalidate_authorization_code(self, code):
        code_entry = None
        for entry in self.auth_code_set:
            if entry.code["code"] == code:
                code_entry = entry
                break

        self.auth_code_set.remove(code_entry)
