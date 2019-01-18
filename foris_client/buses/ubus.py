#
# foris-client
# Copyright (C) 2019 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
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
import uuid
import json

from .base import BaseSender, BaseListener, ID

logger = logging.getLogger(__name__)


def _chunks(data, size):
    for i in range(0, len(data), size):
        yield data[i:i + size]


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

    def send(self, module: str, action: str, data: str, timeout=None, controller_id: str = ID):
        """ send request
        :param module: module which will be used
        :param action: action which will be called
        :param data: data for the request
        :param controller_id: ignored for ubus
        :returns: reply
        """
        timeout = self.default_timeout if timeout is None else timeout
        ubus_object = "foris-controller-%s" % module

        dumped_data = json.dumps(data if data else {})
        request_id = str(uuid.uuid4())

        logger.debug(
            "Sending calling method '%s' in object '%s': %s"
            % (action, ubus_object, dumped_data[:10000])
        )

        if len(dumped_data) > 512 * 1024:
            for data_part in _chunks(dumped_data, 512 * 1024):
                ubus.call(ubus_object, action, {
                    "payload": {"multipart_data": data_part},
                    "final": False, "multipart": True, "request_id": request_id
                })
            res = ubus.call(ubus_object, action, {
                "payload": {"multipart_data": ""},
                "final": True, "multipart": True, "request_id": request_id,
            })
        else:
            res = ubus.call(ubus_object, action, {
                "payload": {"data": data} if data is not None else {},
                "final": True, "multipart": False, "request_id": request_id
            })

        raw_response = "".join([e["data"] for e in res])
        logger.debug("Message received: %s", raw_response[:10000])

        response = json.loads(raw_response)

        # Raise exception on error
        self._raise_exception_on_error(response)

        return response.get("data", None)

    def disconnect(self):
        if ubus.get_connected():
            logger.debug("Disconnecting from ubus.")
            ubus.disconnect()
        else:
            logger.warning("Failed to disconnect from ubus (not connected)")


class UbusListener(BaseListener):
    def connect(self, socket_path, handler, module=None, timeout=0):
        """ connects to ubus and starts to listen

        :param socket_path: path to ubus socket
        :type socket_path: str
        :param handler: handler which will be called on obtained data and controller_id
        :type handler: callable
        :param timeout: how log is the listen period (in ms)
        :type timeout: int
        """
        self.disconnecting = False
        self.timeout = timeout
        self.module = module
        self.handler = handler

        self.connected_before = ubus.get_connected()
        if not self.connected_before:
            logger.debug("Connecting to ubus (%s)." % socket_path)
            ubus.connect(socket_path)

    def listen(self):
        logger.debug("Starting to listen.")

        def inner_handler(module, data):
            module_name = module[len("foris-controller-"):]
            msg = {
                "module": module_name,
                "kind": "notification",
                "action": data["action"],
            }
            msg_data = data.get("data", None)
            if msg_data:
                msg["data"] = msg_data
            logger.debug("Notification recieved %s." % msg)
            self.handler(msg, ID)

        listen_object = "foris-controller-%s" % (self.module if self.module else "*")
        logger.debug("Listening to '%s'." % listen_object)
        ubus.listen((listen_object, inner_handler))

        if self.timeout:
            ubus.loop(self.timeout)
        else:
            while True:
                ubus.loop(500)
                if self.disconnecting:
                    if self.connected_before:
                        logger.debug(
                            "Program was connected to ubus before listener started. "
                            "-> don't diconnect"
                        )
                    elif ubus.get_connected():
                        logger.debug("Disconnecting from ubus.")
                        ubus.disconnect()
                    else:
                        logger.warning("Failed to disconnect from ubus (not connected)")
                    logger.debug("Disconnected.")
                    break

    def disconnect(self):
        """ disconnects from ubus
        """
        logger.debug("Marked for disconnect.")
        self.disconnecting = True
