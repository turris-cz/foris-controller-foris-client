#
# foris-client
# Copyright (C) 2018 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
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

import logging
import uuid
import json
import threading

from .base import BaseSender, BaseListener

from paho.mqtt import client as mqtt


logger = logging.getLogger(__name__)

ID = "%012x" % uuid.getnode()


def _normalize_timeout(timeout):
    return float(timeout or 0) / 1000


class MqttSender(BaseSender):

    def __init__(self, *args, **kwargs):
        self.lock = threading.Lock()
        super(MqttSender, self).__init__(*args, **kwargs)

    def connect(self, host, port):
        def on_connect(client, userdata, flags, rc):
            logger.debug("Connected to mqtt server.")

        def on_subscribe(client, userdata, mid, granted_qos):
            logger.debug("Subscribed to %d.", mid)
            msg = {"reply_topic": self.reply_topic}
            if self.data is not None:
                msg["data"] = self.data

            client.publish(self.publish_topic, json.dumps(msg))

        def on_message(client, userdata, msg):
            logger.debug("Msg recieved for '%s' (msg=%s", msg.topic, msg.payload)
            try:
                parsed = json.loads(msg.payload)
                self.result = parsed
                self.passed = True
            except ValueError:
                logger.error("Reply is not in JSON format.")
                return

            client.unsubscribe(self.reply_topic)
            client.loop_stop()

        def on_unsubscribe(client, userdata, mid):
            logger.debug("Unsubscribing from %d.", mid)

        def on_disconnect(client, userdata, rc):
            logger.debug("Sender Disconnected.")

        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.on_subscribe = on_subscribe
        self.client.on_message = on_message
        self.client.on_disconnect = on_disconnect

        self.client.connect(host, port, 30)

    def disconnect(self):
        logger.debug("Sender Disconnected.")
        self.client.disconnect()

    def send(self, module, action, data, timeout=None):
        timeout = _normalize_timeout(timeout)
        msg_id = uuid.uuid1()
        publish_topic = "foris-controller/%s/request/%s/action/%s" % (
            ID, module, action,
        )
        reply_topic = "foris-controller/%s/reply/%s" % (ID, msg_id,)
        with self.lock:
            self.reply_topic = reply_topic
            self.data = data
            self.publish_topic = publish_topic
            self.passed = False
            self.client.subscribe(reply_topic)
            self.client.loop_start()
            self.client._thread.join(30)
            self.client.loop_stop(True)

            if self.passed:
                result = self.result

            self.result = None
            self.reply_topic = None
            self.publish_topic = None
            self.data = None

            if not self.passed:
                raise RuntimeError("Timeout occured")

        # raise exception on error
        self._raise_exception_on_error(result)

        return result.get("data")


class MqttListener(BaseListener):
    def connect(self, host, port, handler, module=None, timeout=0):

        def on_disconnect(client, userdata, rc):
            logger.debug("Listener Disconnected.")

        def on_connect(client, userdata, flags, rc):
            listen_topic = "foris-controller/%s/notification/%s/action/+" % (
                ID, module if module else "+"
            )
            rc, mid = client.subscribe(listen_topic)
            if rc != 0:
                logger.error("Failed to subscribe to '%s'", listen_topic)
            logger.debug("Subscirbing to '%s' (mid=%d)", listen_topic, mid)
            self.connected = True

        def on_subscribe(client, userdata, mid, granted_qos):
            logger.debug("Subscirbed (mid=%d)", mid)

        def on_message(client, userdata, msg):
            logger.debug("Notification recieved (topic=%s, payload=%s)", msg.topic, msg.payload)
            try:
                parsed = json.loads(msg.payload)
            except Exception:
                logger.error("Wrong payload not in JSON format")
            handler(parsed)

        self.client = mqtt.Client()
        self.client.on_connect = on_connect
        self.client.on_subscribe = on_subscribe
        self.client.on_message = on_message
        self.client.on_disconnect = on_disconnect
        self.timeout = _normalize_timeout(timeout)
        self.connected = None
        self.client.connect(host, port, 30)

    def disconnect(self):
        logger.debug("Closing connection.")
        self.client.disconnect()

    def listen(self):
        while not self.connected:
            self.client.loop(0.2)

        logger.debug("Starting to listen.")
        self.client.loop(self.timeout)
        while not self.timeout:  # loop forever when timeout == 0.0
            self.client.loop(30.0)
        logger.debug("Listening stopped")
