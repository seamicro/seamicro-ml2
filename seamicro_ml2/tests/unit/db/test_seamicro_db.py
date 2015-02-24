# Copyright (c) 2013 OpenStack Foundation
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

import collections

from neutron import context
from neutron.tests.unit import testlib_api
from seamicro_ml2.db import models as seamicro_db


class SeaMicroDbTest(testlib_api.SqlTestCase):

    """Unit tests for SeaMicro mechanism driver's database."""

    SNWObj = collections.namedtuple('SNWObj', 'net_id vlan_id segment_id\
                                    tenant_id network_type')
    SPObj = collections.namedtuple('SPObj', 'port_id net_id vlan_id tenant_id')

    def _snw_test_obj(self, network_id, vlan_id, segment_id, tenant_id,
                      network_type="vlan"):
        """Return Network Test Object."""
        return self.SNWObj(unicode(network_id), unicode(vlan_id),
                           unicode(segment_id), unicode(tenant_id),
                           unicode(network_type))

    def _sp_test_obj(self, port_id, network_id, vlan_id, tenant_id):
        """Return Port Test Object."""
        return self.SPObj(unicode(port_id), unicode(network_id),
                          unicode(vlan_id), unicode(tenant_id))

    def _assert_network_match(self, snw, snw_obj):
        """Asserts that a network matches a network test obj."""
        self.assertEqual(snw.id, snw_obj.net_id)
        self.assertEqual(snw.vlan, snw_obj.vlan_id)
        self.assertEqual(snw.segment_id, snw_obj.segment_id)
        self.assertEqual(snw.network_type, snw_obj.network_type)
        self.assertEqual(snw.tenant_id, snw_obj.tenant_id)

    def _assert_port_match(self, sp, sp_obj):
        """Asserts that a port matches a port test obj."""
        self.assertEqual(sp.id, sp_obj.port_id)
        self.assertEqual(sp.network_id, sp_obj.net_id)
        self.assertEqual(sp.vlan_id, sp_obj.vlan_id)
        self.assertEqual(sp.tenant_id, sp_obj.tenant_id)

    def _add_network_to_db(self, snw):
        """Adds a network to the SeaMicro database."""
        ctx = context.get_admin_context()
        return seamicro_db.create_network(ctx, snw.net_id, snw.vlan_id,
                                          snw.segment_id, snw.network_type,
                                          snw.tenant_id)

    def _get_network(self, snw):
        """Get a network from SeaMicro databases."""
        ctx = context.get_admin_context()
        return seamicro_db.get_network(ctx, snw.net_id)

    def _remove_network_from_db(self, snw):
        """Remove network from SeaMicro databases."""
        ctx = context.get_admin_context()
        return seamicro_db.delete_network(ctx, snw.net_id)

    def _add_port_to_db(self, sp):
        """Add port to SeaMicro databases."""
        ctx = context.get_admin_context()
        return seamicro_db.create_port(ctx, sp.port_id, sp.net_id, sp.vlan_id,
                                       sp.tenant_id)

    def _get_port(self, sp):
        """Get port from SeaMicro databases."""
        ctx = context.get_admin_context()
        return seamicro_db.get_port(ctx, sp.port_id)

    def _remove_port_from_db(self, sp):
        """Remove port from SeaMicro databases."""
        ctx = context.get_admin_context()
        return seamicro_db.delete_port(ctx, sp.port_id)

    def test_network_add_remove(self):
        """Tests add and removal of network from the SeaMicro database."""
        snw11 = self._snw_test_obj(10, 100, 1001, 1000)
        snw = self._add_network_to_db(snw11)
        self._assert_network_match(snw, snw11)
        snw = self._remove_network_from_db(snw11)
        self._assert_network_match(snw, snw11)

    def test_network_remove_wrong_net_id(self):
        """Tests removal of wrong network from SeaMicro databases."""
        snw11 = self._snw_test_obj(10, 100, 1001, 1000)
        snw12 = self._snw_test_obj(11, 100, 1001, 1000)
        snw = self._add_network_to_db(snw11)
        self._assert_network_match(snw, snw11)
        snw = self._remove_network_from_db(snw12)
        self.assertEqual(snw, None)

    def test_network_get(self):
        """Tests get network from the Seamicro database."""
        snw11 = self._snw_test_obj(10, 100, 1001, 1000)
        snw = self._add_network_to_db(snw11)
        self._assert_network_match(snw, snw11)
        snw = self._get_network(snw11)
        self._assert_network_match(snw, snw11)

    def test_network_get_wrong_net_id(self):
        """Tests get wrong network from the Seamicro database."""
        snw11 = self._snw_test_obj(10, 100, 1001, 1000)
        snw12 = self._snw_test_obj(11, 100, 1001, 1000)
        snw = self._add_network_to_db(snw11)
        self._assert_network_match(snw, snw11)
        snw = self._get_network(snw12)
        self.assertEqual(snw, None)

    def test_port_add_remove(self):
        """Tests add and removal of port from the SeaMicro database."""
        sp11 = self._sp_test_obj(10, 10, 100, 1000)
        sp = self._add_port_to_db(sp11)
        self._assert_port_match(sp, sp11)
        sp = self._remove_port_from_db(sp11)
        self._assert_port_match(sp, sp11)

    def test_port_get(self):
        """Tests get port from the Seamicro database."""
        sp11 = self._sp_test_obj(10, 10, 100, 1000)
        sp = self._add_port_to_db(sp11)
        self._assert_port_match(sp, sp11)
        sp = self._get_port(sp11)
        self._assert_port_match(sp, sp11)

    def test_port_get_wrong_port_id(self):
        """Tests get wrong port from the Seamicro database."""
        sp11 = self._sp_test_obj(10, 10, 100, 1000)
        sp12 = self._sp_test_obj(11, 10, 100, 1000)
        sp = self._add_port_to_db(sp11)
        self._assert_port_match(sp, sp11)
        sp = self._get_port(sp12)
        self.assertEqual(sp, None)
