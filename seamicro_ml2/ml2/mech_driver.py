# Copyright (c) 2013-2014 OpenStack Foundation
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

from neutron.i18n import _LE, _LI
from neutron.openstack.common import log

from seamicro_ml2.common import client as seamicro_client
from seamicro_ml2.db import models as seamicro_db

from oslo_utils import importutils

seamicroclient = importutils.try_import('seamicroclient')
if seamicroclient:
    from seamicroclient import exceptions as seamicro_client_exception

LOG = log.getLogger(__name__)


def _parse_switch_info(switch_ip, **kwargs):
    api_endpoint = 'http://' + switch_ip + '/v' + kwargs['api_version'] + '.0'
    switch_info = {'username': kwargs['username'],
                   'password': kwargs['password'],
                   'api_endpoint': api_endpoint,
                   'api_version': kwargs['api_version']}
    return switch_info


def _get_switch_info(switch_info, host_id):
    """Get the chassis IP and server ID the host_id belongs to."""
    for switch_ip in switch_info:
        if host_id in switch_info[switch_ip]:
            info = switch_info[switch_ip][host_id].split(",")
            return (switch_ip, info[0], info[1:])
    return (None, None, None)


class SeaMicroDriver(object):

    """SeaMicroPython Driver for Neutron.

    This code is the backend implementation for the SeaMicro ML2
    MechanismDriver for OpenStack Neutron.
    """

    def __init__(self, **switch):
        LOG.debug("Initializing SeaMicro ML2 driver")
        self.client = {}
        self._switch = switch
        for switch_ip in self._switch:
            switch_info = _parse_switch_info(switch_ip,
                                             **self._switch[switch_ip])
            c = seamicro_client.SeaMicroRestClient()
            self.client[switch_ip] = c.get_client(**switch_info)

    def create_network_precommit(self, mech_context):
        """Create Network in the mechanism specific database table."""

        LOG.debug("create_network_precommit: called")
        network = mech_context.current
        context = mech_context._plugin_context
        tenant_id = network['tenant_id']
        network_id = network['id']

        segments = mech_context.network_segments
        # currently supports only one segment per network
        segment = segments[0]

        network_type = segment['network_type']
        vlan_id = segment['segmentation_id']
        segment_id = segment['id']

        if network_type != 'vlan':
            raise Exception(
                _("SeaMicro Mechanism: failed to create network, "
                  "only network type vlan is supported"))

        try:
            seamicro_db.create_network(context, network_id, vlan_id,
                                       segment_id, network_type, tenant_id)
        except Exception:
            LOG.exception(
                _LE("SeaMicro Mechanism: failed to create network in db"))
            raise Exception(
                _("SeaMicro Mechanism: create_network_precommit failed"))

        LOG.info(_LI("create network (precommit): %(network_id)s "
                     "of network type = %(network_type)s "
                     "with vlan = %(vlan_id)s "
                     "for tenant %(tenant_id)s"),
                 {'network_id': network_id,
                  'network_type': network_type,
                  'vlan_id': vlan_id,
                  'tenant_id': tenant_id})

    def create_network_postcommit(self, mech_context):
        """Create Network as a segment on the switch."""

        LOG.debug("create_network_postcommit: called")
        network = mech_context.current
        # use network_id to get the network attributes
        # ONLY depend on our db for getting back network attributes
        # this is so we can replay postcommit from db
        context = mech_context._plugin_context

        network_id = network['id']
        try:
            network = seamicro_db.get_network(context, network_id)
        except Exception:
            LOG.exception(
                _LE("SeaMicro Mechanism: failed to get network %s from db"),
                network_id)
            raise Exception(
                _("SeaMicro Mechanism: failed to get network %s from db"),
                network_id)

        network_type = network['network_type']
        tenant_id = network['tenant_id']
        vlan_id = network['vlan']

        if not vlan_id:
            raise Exception(_("No vlan id provided"))

        for switch_ip in self._switch:
            try:
                system = self.client[switch_ip].system.list()
                system[0].add_segment(vlan_id)
            except seamicro_client_exception.ClientException as ex:
                LOG.exception(_LE("SeaMicro driver: failed in create network"
                                  " with the following error: %(error)s"),
                              {'error': ex.message})
                seamicro_db.delete_network(context, network_id)
                raise Exception(
                    _("Seamicro Mechanism: create_network_postcommmit failed"))

            LOG.info(_LI("created network (postcommit): %(network_id)s"
                         " of network type = %(network_type)s"
                         " with vlan = %(vlan_id)s"
                         " for tenant %(tenant_id)s"
                         " on switch %(switch_ip)s"),
                     {'network_id': network_id,
                      'network_type': network_type,
                      'vlan_id': vlan_id,
                      'tenant_id': tenant_id,
                      'switch_ip': switch_ip})

    def delete_network_precommit(self, mech_context):
        """Delete Network from the plugin specific database table."""

        LOG.debug("delete_network_precommit: called")
        network = mech_context.current
        network_id = network['id']
        vlan_id = network['provider:segmentation_id']
        tenant_id = network['tenant_id']

        context = mech_context._plugin_context

        try:
            seamicro_db.delete_network(context, network_id)
        except Exception:
            LOG.exception(
                _LE("SeaMicro Mechanism: failed to delete network in db"))
            raise Exception(
                _("SeaMicro Mechanism: delete_network_precommit failed"))

        LOG.info(_LI("delete network (precommit): %(network_id)s"
                     " with vlan = %(vlan_id)s"
                     " for tenant %(tenant_id)s"),
                 {'network_id': network_id,
                  'vlan_id': vlan_id,
                  'tenant_id': tenant_id})

    def delete_network_postcommit(self, mech_context):
        """Delete network which remove segment from the switch."""

        LOG.debug("delete_network_postcommit: called")
        network = mech_context.current
        network_id = network['id']
        vlan_id = network['provider:segmentation_id']
        tenant_id = network['tenant_id']

        for switch_ip in self._switch:
            try:
                system = self.client[switch_ip].system.list()
                system[0].remove_segment(vlan_id)
            except seamicro_client_exception.ClientException as ex:
                LOG.exception(_LE("SeaMicr driver: failed to delete network"
                                  " with the following error: %(error)s"),
                              {'error': ex.message})
                raise Exception(
                    _("Seamicro switch exception, delete_network_postcommit"
                      " failed"))

            LOG.info(_LI("delete network (postcommit): %(network_id)s"
                         " with vlan = %(vlan_id)s"
                         " for tenant %(tenant_id)s on switch %(switch_ip)s"),
                     {'network_id': network_id,
                      'vlan_id': vlan_id,
                      'tenant_id': tenant_id,
                      'switch_ip': switch_ip})

    def update_network_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        pass

    def update_network_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        pass

    def create_port_precommit(self, mech_context):
        """Create logical port on the chassis (db update)."""

        LOG.debug("create_port_precommit: called")

        port = mech_context.current
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']

        context = mech_context._plugin_context

        try:
            network = seamicro_db.get_network(context, network_id)
        except Exception:
            LOG.exception(
                _LE("SeaMicro Mechanism: failed to get network %s from db"),
                network_id)
            raise Exception(
                _("SeaMicro Mechanism: failed to get network %s from db"),
                network_id)

        vlan_id = network['vlan']

        try:
            seamicro_db.create_port(context, port_id, network_id,
                                    vlan_id, tenant_id)
        except Exception:
            LOG.exception(_LE("SeaMicro Mechanism: failed to create port"
                              " in db"))
            raise Exception(
                _("SeaMicro Mechanism: create_port_precommit failed"))

    def create_port_postcommit(self, mech_context):
        """Set all Nics of Server and Interface as Tagged-vlan."""

        LOG.debug("create_port_postcommit: called")
        port = mech_context.current
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        host_id = mech_context._binding.host
        context = mech_context._plugin_context
        try:
            network = seamicro_db.get_network(context, network_id)
        except Exception:
            LOG.exception(
                _LE("SeaMicro Mechanism: failed to get network %s from db"),
                network_id)
            raise Exception(
                _("SeaMicro Mechanism: failed to get network %s from db"),
                network_id)

        vlan_id = network['vlan']
        switch_ip, server_id, nics = _get_switch_info(self._switch, host_id)
        if switch_ip is not None and server_id is not None and nics is not None:
            try:
                interfaces = self.client[switch_ip].interfaces.list()
                for interface in interfaces:
                    interface.add_tagged_vlan(vlan_id)

                server = self.client[switch_ip].servers.get(server_id)
                if nics:
                    server.set_tagged_vlan(vlan_id, nics=nics)
                else:
                    server.set_tagged_vlan(vlan_id)
            except seamicro_client_exception.ClientException as ex:
                LOG.exception(
                    _LE("SeaMicro driver: failed to create port"
                        " with the following error: %(error)s"),
                    {'error': ex.message})
                seamicro_db.delete_port(context, port_id)
                raise Exception(
                    _("SeaMicro Mechanism: create_port_postcommit failed"))

            LOG.info(
                _LI("created port (postcommit): port_id=%(port_id)s"
                    " network_id=%(network_id)s tenant_id=%(tenant_id)s"
                    " switch_ip=%(switch_ip)s server_id=%(server_id)s"),
                {'port_id': port_id,
                 'network_id': network_id, 'tenant_id': tenant_id,
                 'switch_ip': switch_ip, 'server_id': server_id})

    def delete_port_precommit(self, mech_context):
        """Delete logical port on the switch (db update)."""

        LOG.debug("delete_port_precommit: called")
        port = mech_context.current
        port_id = port['id']

        context = mech_context._plugin_context

        try:
            seamicro_db.delete_port(context, port_id)
        except Exception:
            LOG.exception(_LE("SeaMicro Mechanism: failed to delete port"
                              " in db"))
            raise Exception(
                _("SeaMicro Mechanism: delete_port_precommit failed"))

    def delete_port_postcommit(self, mech_context):
        """UnSet Tagged-vlan of all Nics of Server and Interface."""

        LOG.debug("delete_port_postcommit: called")
        port = mech_context.current
        port_id = port['id']
        network_id = port['network_id']
        tenant_id = port['tenant_id']
        host_id = mech_context._binding.host
        context = mech_context._plugin_context

        try:
            network = seamicro_db.get_network(context, network_id)
        except Exception:
            LOG.exception(
                _LE("SeaMicro Mechanism: failed to get network %s from db"),
                network_id)
            raise Exception(
                _("SeaMicro Mechanism: failed to get network %s from db"),
                network_id)

        vlan_id = network['vlan']

        switch_ip, server_id, nics = _get_switch_info(self._switch, host_id)
        if switch_ip is not None and server_id is not None and nics is not None:
            try:
                interfaces = self.client[switch_ip].interfaces.list()
                for interface in interfaces:
                    interface.remove_tagged_vlan(vlan_id)

                server = self.client[switch_ip].servers.get(server_id)
                if nics:
                    server.unset_tagged_vlan(vlan_id, nics=nics)
                else:
                    server.unset_tagged_vlan(vlan_id)
            except seamicro_client_exception.ClientException as ex:
                LOG.exception(
                    _LE("SeaMicro driver: failed to delete port"
                        " with the following error: %(error)s"),
                    {'error': ex.message})
                raise Exception(
                    _("SeaMicro Mechanism: delete_port_postcommit failed"))

            LOG.info(
                _LI("delete port (postcommit): port_id=%(port_id)s"
                    " network_id=%(network_id)s tenant_id=%(tenant_id)s"
                    " switch_ip=%(switch_ip)s server_id=%(server_id)s"),
                {'port_id': port_id,
                 'network_id': network_id, 'tenant_id': tenant_id,
                 'switch_ip': switch_ip, 'server_id': server_id})

    def update_port_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug("update_port_precommit(self: called")

    def update_port_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug("update_port_postcommit: called")

    def create_subnet_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug("create_subnetwork_precommit: called")

    def create_subnet_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug("create_subnetwork_postcommit: called")

    def delete_subnet_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug("delete_subnetwork_precommit: called")

    def delete_subnet_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug("delete_subnetwork_postcommit: called")

    def update_subnet_precommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug("update_subnet_precommit(self: called")

    def update_subnet_postcommit(self, mech_context):
        """Noop now, it is left here for future."""
        LOG.debug("update_subnet_postcommit: called")
