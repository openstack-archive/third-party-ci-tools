# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import uuid

from oslo.config import cfg
from pecan import abort
from pecan import request
from pecan import response
from pecan import rest
from pecan.secure import secure
import wsmeext.pecan as wsme_pecan

from radar.api.auth import authorization_checks as checks
import radar.api.v1.wmodels as wmodels
import radar.db.api.access_tokens as token_api
import radar.db.api.users as user_api
from radar.openstack.common.gettextutils import _  # noqa
from radar.openstack.common import log


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class UserTokensController(rest.RestController):
    @secure(checks.authenticated)
    @wsme_pecan.wsexpose([wmodels.AccessToken], int, int, int, unicode,
                         unicode)
    def get_all(self, user_id, marker=None, limit=None, sort_field='id',
                sort_dir='asc'):
        """Returns all the access tokens for the provided user.

        :param user_id: The ID of the user.
        :param marker: The marker record at which to start the page.
        :param limit: The number of records to return.
        :param sort_field: The field on which to sort.
        :param sort_dir: The direction to sort.
        :return: A list of access tokens for the given user.
        """
        self._assert_can_access(user_id)

        # Boundary check on limit.
        if limit is None:
            limit = CONF.page_size_default
        limit = min(CONF.page_size_maximum, max(1, limit))

        # Resolve the marker record.
        marker_token = token_api.access_token_get(marker)

        tokens = token_api.access_token_get_all(marker=marker_token,
                                                limit=limit,
                                                user_id=user_id,
                                                filter_non_public=True,
                                                sort_field=sort_field,
                                                sort_dir=sort_dir)
        token_count = token_api.access_token_get_count(user_id=user_id)

        # Apply the query response headers.
        response.headers['X-Limit'] = str(limit)
        response.headers['X-Total'] = str(token_count)
        if marker_token:
            response.headers['X-Marker'] = str(marker_token.id)

        return [wmodels.AccessToken.from_db_model(t) for t in tokens]

    @secure(checks.authenticated)
    @wsme_pecan.wsexpose(wmodels.AccessToken, int, int)
    def get(self, user_id, access_token_id):
        """Returns a specific access token for the given user.

        :param user_id: The ID of the user.
        :param access_token_id: The ID of the access token.
        :return: The requested access token.
        """
        access_token = token_api.access_token_get(access_token_id)
        self._assert_can_access(user_id, access_token)

        if not access_token:
            abort(404)

        return wmodels.AccessToken.from_db_model(access_token)

    @secure(checks.authenticated)
    @wsme_pecan.wsexpose(wmodels.AccessToken, int, body=wmodels.AccessToken)
    def post(self, user_id, body):
        """Create a new access token for the given user.

        :param user_id: The user ID of the user.
        :param body: The access token.
        :return: The created access token.
        """
        self._assert_can_access(user_id, body)

        # Generate a random token if one was not provided.
        if not body.access_token:
            body.access_token = str(uuid.uuid4())

        # Token duplication check.
        dupes = token_api.access_token_get_all(access_token=body.access_token)
        if dupes:
            abort(409, _('This token already exists.'))

        token = token_api.access_token_create(body.as_dict())

        return wmodels.AccessToken.from_db_model(token)

    @secure(checks.authenticated)
    @wsme_pecan.wsexpose(wmodels.AccessToken, int, int,
                         body=wmodels.AccessToken)
    def put(self, user_id, access_token_id, body):
        """Update an access token for the given user.

        :param user_id: The user ID of the user.
        :param access_token_id: The ID of the access token.
        :param body: The access token.
        :return: The created access token.
        """
        target_token = token_api.access_token_get(access_token_id)

        self._assert_can_access(user_id, body)
        self._assert_can_access(user_id, target_token)

        if not target_token:
            abort(404)

        # We only allow updating the expiration date.
        target_token.expires_in = body.expires_in

        result_token = token_api.access_token_update(access_token_id,
                                                     target_token.as_dict())

        return wmodels.AccessToken.from_db_model(result_token)

    @secure(checks.authenticated)
    @wsme_pecan.wsexpose(wmodels.AccessToken, int, int)
    def delete(self, user_id, access_token_id):
        """Deletes an access token for the given user.

        :param user_id: The user ID of the user.
        :param access_token_id: The ID of the access token.
        :return: Empty body, or error response.
        """
        access_token = token_api.access_token_get(access_token_id)
        self._assert_can_access(user_id, access_token)

        if not access_token:
            abort(404)

        token_api.access_token_delete(access_token_id)

        response.status_code = 204

    def _assert_can_access(self, user_id, token_entity=None):
        current_user = user_api.user_get(request.current_user_id)

        if not user_id:
            abort(400)

        # The user must be logged in.
        if not current_user:
            abort(401)

        # If the impacted user is not the current user, the current user must
        # be an admin.
        if not current_user.is_superuser and current_user.id != user_id:
            abort(403)

        # The path-based impacted user and the user found in the entity must
        # be identical. No PUT /users/1/tokens { user_id: 2 }
        if token_entity and token_entity.user_id != user_id:
            abort(403)