#
# foris-client
# Copyright (C) 2017 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
#

from __future__ import absolute_import

import logging
import ubus

from .base import BaseSender

logger = logging.getLogger(__name__)


class UbusSender(BaseSender):

    def connect(self, socket_path):
        if ubus.get_connected():
            connected_socket = ubus.get_socket_path()
            if socket_path == connected_socket:
                logger.info("Already connected to '%s'." % connected_socket)
                return
            else:
                logger.error(
                    "Connected to '%s'. Disconnecting to reconnect to '%s' " %
                    (connected_socket, socket_path)
                )
                self.disconnect()
        logger.debug("Trying to connect to ubus socket '%s'." % socket_path)
        ubus.connect(socket_path)
        logger.debug("Connected to ubus socket '%s'." % socket_path)

    def send(self, module, action, data):
        message = {
            "data": data if data else {}
        }
        ubus_object = "foris-controller-%s" % module
        logger.debug(
            "Sending calling method '%s' in object '%s': %s"
            % (action, ubus_object, message)
        )
        res = ubus.call(ubus_object, action, message)
        logger.debug("Message received: %s" % res)
        return res[0]["data"]

    def disconnect(self):
        if ubus.get_connected():
            logger.debug("Disconnection from ubus.")
            ubus.disconnect()
        else:
            logger.warning("Failed to disconnect from ubus (not connected)")
