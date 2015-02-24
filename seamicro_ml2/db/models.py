# Copyright 2014 Brocade Communications System, Inc.
# All rights reserved.
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


"""SeaMicro specific database schema/model."""
import sqlalchemy as sa

from neutron.db import model_base
from neutron.db import models_v2


class ML2_SeaMicroNetwork(model_base.BASEV2, models_v2.HasId,
                          models_v2.HasTenant):
    """Schema for SeaMicro network."""

    vlan = sa.Column(sa.String(10))
    segment_id = sa.Column(sa.String(36))
    network_type = sa.Column(sa.String(10))
    tenant_id = sa.Column(sa.String(36))


class ML2_SeaMicroPort(model_base.BASEV2, models_v2.HasId,
                       models_v2.HasTenant):
    """Schema for SeaMicro port."""
    network_id = sa.Column(sa.String(36),
                           nullable=False)
    vlan_id = sa.Column(sa.String(36))
    tenant_id = sa.Column(sa.String(36))


def create_network(context, net_id, vlan, segment_id, network_type, tenant_id):
    """Create a SeaMicro specific network."""

    # only network_type of vlan is supported
    session = context.session
    with session.begin(subtransactions=True):
        net = get_network(context, net_id, None)
        if not net:
            net = ML2_SeaMicroNetwork(id=net_id, vlan=vlan,
                                      segment_id=segment_id,
                                      network_type='vlan',
                                      tenant_id=tenant_id)
            session.add(net)
    return net


def delete_network(context, net_id):
    """Delete a SeaMicro specific network."""

    session = context.session
    with session.begin(subtransactions=True):
        net = get_network(context, net_id, None)
        if net:
            session.delete(net)
            return net


def get_network(context, net_id, fields=None):
    """Get SeaMicro specific network, with vlan extension."""

    session = context.session
    return session.query(ML2_SeaMicroNetwork).filter_by(id=net_id).first()


def get_networks(context, filters=None, fields=None):
    """Get all SeaMicro specific networks."""

    session = context.session
    return session.query(ML2_SeaMicroNetwork).all()


def create_port(context, port_id, network_id, vlan_id, tenant_id):
    """Create a SeaMicro specific port, has policy like vlan."""

    session = context.session
    with session.begin(subtransactions=True):
        port = get_port(context, port_id)
        if not port:
            port = ML2_SeaMicroPort(id=port_id,
                                    network_id=network_id,
                                    vlan_id=vlan_id,
                                    tenant_id=tenant_id)
            session.add(port)

    return port


def get_port(context, port_id):
    """get a SeaMicro specific port."""

    session = context.session
    return session.query(ML2_SeaMicroPort).filter_by(id=port_id).first()


def get_ports(context, network_id=None):
    """get a SeaMicro specific ports."""

    session = context.session
    return session.query(ML2_SeaMicroPort).filter_by(
        network_id=network_id).all()


def delete_port(context, port_id):
    """delete SeaMicro specific port."""

    session = context.session
    with session.begin(subtransactions=True):
        port = get_port(context, port_id)
        if port:
            session.delete(port)
            return port
