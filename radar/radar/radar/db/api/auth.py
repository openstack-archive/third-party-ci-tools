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

from radar.db.api import base as api_base
from radar.db import models


def authorization_code_get(code):
    query = api_base.model_query(models.AuthorizationCode,
                                 api_base.get_session())
    return query.filter_by(code=code).first()


def authorization_code_save(values):
    return api_base.entity_create(models.AuthorizationCode, values)


def authorization_code_delete(code):
    del_code = authorization_code_get(code)

    if del_code:
        api_base.entity_hard_delete(models.AuthorizationCode, del_code.id)


def access_token_get(access_token):
    query = api_base.model_query(models.AccessToken, api_base.get_session())
    return query.filter_by(access_token=access_token).first()


def access_token_save(values):
    return api_base.entity_create(models.AccessToken, values)


def access_token_delete(access_token):
    del_token = access_token_get(access_token)

    if del_token:
        api_base.entity_hard_delete(models.AccessToken, del_token.id)


def refresh_token_get(refresh_token):
    query = api_base.model_query(models.RefreshToken, api_base.get_session())
    return query.filter_by(refresh_token=refresh_token).first()


def refresh_token_save(values):
    return api_base.entity_create(models.RefreshToken, values)


def refresh_token_delete(refresh_token):
    del_token = refresh_token_get(refresh_token)

    if del_token:
        api_base.entity_hard_delete(models.RefreshToken, del_token.id)