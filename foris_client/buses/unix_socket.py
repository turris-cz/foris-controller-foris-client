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

import json
import logging
import socket
import struct

from .base import BaseSender

logger = logging.getLogger(__name__)


class UnixSocketSender(BaseSender):

    def _normalize_timeout(self, timeout):
        return None if not timeout else float(timeout) / 1000  # 0 makes non-blocking socket

    def connect(self, socket_path, default_timeout=0):
        """ connects to unix-socket

        :param socket_path: path to unix-socket
        :type socket_path: str
        :param default_timeout: default timeout for send operations (in ms)
        :type default_timeout: int
        """
        self.default_timeout = self._normalize_timeout(default_timeout)
        logger.debug("Trying to connect to '%s'." % socket_path)
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(socket_path)
        logger.debug(
            "Connected to '%s' (default_timeout=%d)." % (
                socket_path, 0 if not default_timeout else default_timeout
            )
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
        timeout = self._normalize_timeout(timeout)
        message = {
            "kind": "request",
            "module": module,
            "action": action,
        }

        if data is not None:
            message["data"] = data

        raw_message = json.dumps(message).encode("utf8")
        logger.debug("Sending message (len=%d): %s" % (len(raw_message), raw_message))
        length_bytes = struct.pack("I", len(raw_message))
        self.sock.sendall(length_bytes + raw_message)
        logger.debug("Message was send. Waiting for response.")

        received_length = struct.unpack("I", self.sock.recv(4))[0]
        logger.debug("Response length = %d." % received_length)
        self.sock.settimeout(timeout)
        received = self.sock.recv(received_length)
        logger.debug("Message received: %s" % received)

        return json.loads(received.decode("utf8")).get("data", {})

    def disconnect(self):
        logger.debug("Closing connection.")
        self.sock.close()
        logger.debug("Connection closed.")
