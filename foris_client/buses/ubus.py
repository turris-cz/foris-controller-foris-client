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

    def connect(self, socket_path, default_timeout=0):
        """ connects to ubus

        :param socket_path: path to ubus socket
        :type socket_path: str
        :param default_timeout: default timeout for send operations (in ms)
        :type default_timeout: int
        """
        self.default_timeout = default_timeout

        if ubus.get_connected():
            connected_socket = ubus.get_socket_path()
            if socket_path == connected_socket:
                logger.info("Already connected to '%s'." % connected_socket)
                logger.debug("Default timeout set to %d." % default_timeout)
                return
            else:
                logger.error(
                    "Connected to '%s'. Disconnecting to reconnect to '%s' " %
                    (connected_socket, socket_path)
                )
                self.disconnect()
        logger.debug("Trying to connect to ubus socket '%s'." % socket_path)
        ubus.connect(socket_path)
        logger.debug(
            "Connected to ubus socket '%s' (default_timeout=%d)."
            % (socket_path, default_timeout)
        )

    def send(self, module, action, data, timeout=None):
        """ send request

        :param module: module which will be used
        :type module: str
        :param action: action which will be called
        :type action: str
        :param data: data for the request
        :type data: dict
        :param timeout: timeout for the request in ms (0=wait forever)
        :returns: reply
        """
        timeout = self.default_timeout if timeout is None else timeout

        message = {
            "data": data if data else {}
        }
        ubus_object = "foris-controller-%s" % module
        logger.debug(
            "Sending calling method '%s' in object '%s': %s"
            % (action, ubus_object, message)
        )
        res = ubus.call(ubus_object, action, message, timeout=timeout)
        logger.debug("Message received: %s" % res)
        return res[0]["data"]

    def disconnect(self):
        if ubus.get_connected():
            logger.debug("Disconnection from ubus.")
            ubus.disconnect()
        else:
            logger.warning("Failed to disconnect from ubus (not connected)")
