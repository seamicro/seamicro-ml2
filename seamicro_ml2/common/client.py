# Copyright (c) 2014 Red Hat Inc.
# All Rights Reserved.
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

from neutron.openstack.common import log
from oslo_utils import importutils
seamicroclient = importutils.try_import('seamicroclient')
if seamicroclient:
    from seamicroclient import client as seamicro_client
    from seamicroclient import exceptions as seamicro_client_exception

LOG = log.getLogger(__name__)


class SeaMicroRestClient(object):

    def get_client(self, **kwargs):
        """Creates the python-seamicro_client

        :param kwargs: A dict of keyword arguments to be passed to the method,
                   which should contain: 'username', 'password',
                   'auth_url', 'api_version' parameters.
        :returns: SeaMicro API client.
        """

        cl_kwargs = {'username': kwargs['username'],
                     'password': kwargs['password'],
                     'auth_url': kwargs['api_endpoint']}
        LOG.debug("****  %s", cl_kwargs)
        try:
            c = seamicro_client.Client(kwargs['api_version'], **cl_kwargs)
            LOG.debug("------- c %s ", c)
            return c
        except seamicro_client_exception.UnsupportedVersion as e:
            raise Exception(_(
                "Invalid 'seamicro_api_version' parameter. Reason: %s.") % e)
