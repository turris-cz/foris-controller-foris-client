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

import logging
import uuid
import json
import threading
import time
import ssl
import queue
import re
import typing

from .base import BaseSender, BaseListener, ControllerMissing, prepare_controller_id

from paho.mqtt import client as mqtt
from typing import Optional


ANNOUNCER_PERIOD_REQUIRED = 5.0  # in seconds
CONNECT_TIMEOUT = 15  # in seconds
RETENTION_TIMEOUT = 30  # in seconds

logger = logging.getLogger(__name__)


def _normalize_timeout(timeout):
    return float(timeout or 0) / 1000


class ReplyListener(threading.Thread):
    def __init__(
        self,
        replies: typing.Dict[typing.Tuple[str, str], list],
        replies_lock: threading.Lock,
        controllers: typing.Dict[str, dict],
        controllers_lock: threading.Lock,
        host: str,
        port: int,
        client: mqtt.Client,
    ):
        self.host = host
        self.port = port
        self.client = client
        self.replies = replies
        self.replies_lock = replies_lock
        self.controllers: typing.Dict[str, dict] = controllers
        self.controllers_lock: threading.lock = controllers_lock
        super().__init__(group=None, target=None, name="foris-client-reply-listener", daemon=True)

    def run(self):
        logger.debug("Reply listener is starting.")

        def on_connect(client: mqtt.Client, userdata, flags, rc):
            logger.debug("Client connected.")
            client.subscribe("foris-controller/+/reply/+")
            client.subscribe("foris-controller/+/notification/remote/action/advertize")

        def on_subscribe(client, userdata, mid, granted_qos):
            logger.debug("Subscribed to %s.", mid)

        def on_disconnect(client, userdata, rc):
            logger.debug("Disconneted")

        def on_message(client, userdata, msg):
            logger.debug("Msg recieved for '%s' (msg=%s)", msg.topic, msg.payload)
            match = re.match(
                r"foris-controller/([^/]+)/notification/remote/action/advertize", msg.topic
            )
            if match:
                # recieved a messupdate controller list
                try:
                    data = json.loads(msg.payload)
                except ValueError:
                    logger.error("Advertisement not in JSON format.")
                    return
                with self.controllers_lock:
                    self.controllers[match.group(1)] = {
                        "last": time.time(),
                        "working_replies": data["data"].get("working_replies", []),
                    }
                    # clean older controller records
                    too_old = [
                        k
                        for k, v in self.controllers.items()
                        if v["last"] < time.time() - RETENTION_TIMEOUT
                    ]
                    for k in too_old:
                        del self.controllers[k]
                logger.debug("Msg for '%s' was processed", msg.topic)
                return
            match = re.match(r"foris-controller/([^/]+)/reply/([^/]+)", msg.topic)
            if match:
                controller_id, reply_id = match.groups()
                # Find message among replies
                with self.replies_lock:
                    record: typing.Optinal[
                        typing.Tuple[float, queue.Queue, bool]
                    ] = self.replies.get((controller_id, reply_id))

                    # clean older replies
                    too_old = [
                        k for k, v in self.replies.items() if v[0] < time.time() - RETENTION_TIMEOUT
                    ]
                    for k in too_old:
                        del self.replies[k]

                    if record:
                        _, output_queue, is_processed = record
                        if is_processed:
                            # message is already recieved and it is being processed
                            return
                        else:
                            # mark that the message is being processed
                            self.replies[(controller_id, reply_id)][2] = True

                    else:
                        logger.debug(
                            "Message id not found. "
                            "(probably it is expired or doesn't belong to this client)"
                        )
                        return
                # Parse and send queue the message
                try:
                    data = json.loads(msg.payload)
                except ValueError:
                    logger.error("Reply not in JSON format.")
                    return
                logger.debug("Sending response data '%s'", data)
                output_queue.put(data)
                logger.debug("Msg for '%s' was processed", msg.topic)
                return

            # this code should not be reached
            raise ValueError("Topic '%s' doesn't match", msg.topic)

        self.client.on_connect = on_connect
        self.client.on_subscribe = on_subscribe
        self.client.on_message = on_message
        self.client.on_disconnect = on_disconnect

        # start to connect
        self.client.connect(self.host, self.port, CONNECT_TIMEOUT)

        # Run in the loop till manually disconnected
        self.client.loop_forever()

        # try to unsubscribe gracefully
        self.client.unsubscribe("foris-controller/+/reply/+")
        self.client.unsubscribe("foris-controller/+/notification/remote/action/advertize")
        self.client.loop()


class MqttSender(BaseSender):
    def __init__(self, *args, **kwargs):
        self.replies: typing.Dict[typing.Tuple[str, str], list] = {}
        self.replies_lock: threading.Lock = threading.Lock()
        self.controllers: typing.Dict[str, dict] = {}
        self.controllers_lock: threading.Lock = threading.Lock()
        self.client_lock: threading.Lock = threading.Lock()
        self.client_published_event: threading.Event = threading.Event()
        self.client: mqtt.Client

        self.mqtt_client_id = f"{uuid.uuid4()}-client-sender"
        self.mqtt_reply_client_id = f"{uuid.uuid4()}-client-reply-watcher"
        super(MqttSender, self).__init__(*args, **kwargs)

    def _prepare_client(self, client_id: str) -> mqtt.Client:
        client = mqtt.Client(client_id=client_id, clean_session=False)

        if self.tls_files:
            ca_path, cert_path, key_path = self.tls_files
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(cert_path, key_path)
            context.load_verify_locations(ca_path)
            context.verify_mode = ssl.CERT_REQUIRED
            # can't assume that server cert is issued to particular hostname/ipaddress
            context.check_hostname = False
            client.tls_set_context(context)

        if self.credentials:
            client.username_pw_set(*self.credentials)

        return client

    def connect(self, host, port, default_timeout=None, tls_files=[], credentials=None):
        self.default_timeout = _normalize_timeout(default_timeout)
        self.credentials = credentials
        self.tls_files = tls_files
        self.controller_id = None

        # prepare sender client
        def on_connect(client, userdata, flags, rc):
            logger.debug("Client sender connected to mqtt server.")

        def on_publish(client: mqtt.Client, userdata, mid):
            self.client_published_event.set()
            logger.debug("Client sender published a message (mid=%d).", mid)

        def on_disconnect(client, userdata, rc):
            logger.debug("Client sender Disconnected.")

        self.client: mqtt.Client = self._prepare_client(self.mqtt_client_id)
        self.client.on_connect = on_connect
        self.client.on_publish = on_publish
        self.client.on_disconnect = on_disconnect

        # prepare reply listener client
        self.reply_client = self._prepare_client(self.mqtt_reply_client_id)
        self.reply_worker = ReplyListener(
            replies=self.replies,
            replies_lock=self.replies_lock,
            controllers=self.controllers,
            controllers_lock=self.controllers_lock,
            host=host,
            port=port,
            client=self.reply_client,
        )
        self.reply_worker.start()
        logger.debug("Reply worker %s has started.", self.reply_worker)

        # sender start client thread
        self.client.connect(host, port, CONNECT_TIMEOUT)
        self.client.loop_start()
        logger.debug("Sending thread %s has started.", self.client._thread)

    def disconnect(self):
        self.client.disconnect()
        logger.debug("Sender Disconnected.")
        self.reply_client.disconnect()
        logger.debug("Reply client Disconnected.")

    def send_internal(
        self, msg_topic: str, msg_data: dict, reply_id: str, controller_id: str
    ) -> queue.Queue:
        """ Sends the message without waiting for the response
        """

        output: queue.Queue
        # only one message can be send at once
        with self.client_lock:
            logger.debug("Sending message for '%s'.", msg_topic)

            # preapre queue for the listener
            with self.replies_lock:
                if (controller_id, reply_id) in self.replies:
                    # already waiting for reply -> just update the time
                    logger.debug("Reusing reply_id %s", reply_id)
                    self.replies[(controller_id, reply_id)][0] = time.time()
                    output = self.replies[(controller_id, reply_id)][1]
                else:
                    # create new queue to wait
                    logger.debug("Using new reply_id '%s", reply_id)
                    output = queue.Queue(maxsize=1)
                    self.replies[(controller_id, reply_id)] = [time.time(), output, False]

            # clear published event
            self.client_published_event.clear()

            # start to perform
            raw_data = json.dumps(msg_data)
            self.client.publish(msg_topic, raw_data, qos=0)

            logger.debug("Sending msg for '%s'", msg_topic)

            if not self.client_published_event.wait(0.3):
                logger.debug("Failed to publish the message for '%s'. (retry)", msg_topic)
                if not self.client.publish(msg_topic, raw_data, qos=0):
                    logger.debug("Failed to publish the message for '%s'. (exception)", msg_topic)
                    # Msg can't reache thte controller
                    raise ControllerMissing(controller_id)

            logger.debug("Message for '%s' was sent", msg_topic)

        return output

    def send(
        self, module: str, action: str, data: dict, timeout=None, controller_id: str = None
    ) -> dict:
        """ Sends the message and waits for the response
        :param timeout: wait for X seconds for reply (0 => wait forever)
        """
        controller_id = prepare_controller_id(controller_id)

        timeout = self.default_timeout if timeout is None else _normalize_timeout(timeout)
        reply_id = str(uuid.uuid4())
        publish_topic: Optional[str] = "foris-controller/%s/request/%s/action/%s" % (
            controller_id,
            module,
            action,
        )

        msg = {"reply_msg_id": reply_id}
        if data is not None:
            msg["data"] = data

        output: queue.Queue

        def try_send():
            try:
                return self.send_internal(publish_topic, msg, reply_id, controller_id)
            except ConnectionError:
                # retry when fosquitto restarts
                logger.warning("Connection failed, trying to resend '%s'", publish_topic)
                try:
                    return self.send_internal(publish_topic, msg, reply_id, controller_id)
                except ConnectionError:
                    logger.error("Publishing into '%s' has failed.", publish_topic)
                    raise

        def check_controllers(try_to_resend: bool = False) -> typing.Optional[queue.Queue]:
            with self.controllers_lock:
                controller = self.controllers.get(controller_id)
                if not controller:
                    # controller hasn't appear yet
                    raise ControllerMissing(controller_id)
                if controller["last"] < time.time() - ANNOUNCER_PERIOD_REQUIRED:
                    # controller is not alive
                    raise ControllerMissing(controller_id)
                if try_to_resend and reply_id not in controller["working_replies"]:
                    # message is not being processed by the controller
                    logger.warning(
                        "Message hasn't reached controller trying to resend '%s'", publish_topic
                    )
                    return try_send()
                # otherwise controller is performing some long lasting task and hasn't replied yet

        output = try_send()

        def process_resp(resp: dict):
            self._raise_exception_on_error(resp)
            return resp.get("data")

        max_time: float = time.time() + timeout
        try:
            res = output.get(timeout=ANNOUNCER_PERIOD_REQUIRED)
            return process_resp(res)
        except queue.Empty:
            # Didn't finishend in time, try to check whether controller_id is processing the message
            output = check_controllers(True)

        # right now we are passed first ANNOUNCER_PERIOD_REQUIRED and waiting for the response
        while time.time() <= max_time:
            try:
                return process_resp(output.get(timeout=ANNOUNCER_PERIOD_REQUIRED))
            except queue.Empty:
                check_controllers()

    def __del__(self):
        """ Close all connections -> worker thread should eventually terminate"""
        self.disconnect()


class MqttListener(BaseListener):
    def __init__(self, *args, **kwargs):
        self.mqtt_client_id = f"{uuid.uuid4()}-client-listener"
        super().__init__(*args, **kwargs)

    def connect(
        self,
        host,
        port,
        handler,
        module=None,
        timeout=0,
        tls_files=[],
        controller_id="+",
        credentials=None,
    ):
        self.controller_id = controller_id
        self.tls_files = tls_files
        self.credentials = credentials

        def on_disconnect(client, userdata, rc):
            logger.debug("Listener Disconnected.")
            self.connected = False

        def on_connect(client, userdata, flags, rc):
            listen_topic = "foris-controller/%s/notification/%s/action/+" % (
                self.controller_id if self.controller_id else "+",
                module if module else "+",
            )
            rc, mid = client.subscribe(listen_topic, qos=0)
            if rc != 0:
                logger.error("Failed to subscribe to '%s'", listen_topic)
            logger.debug("Subscribing to '%s' (mid=%d)", listen_topic, mid)
            self.connected = True

        def on_subscribe(client, userdata, mid, granted_qos):
            logger.debug("Subscribed (mid=%d)", mid)

        def on_message(client, userdata, msg):
            logger.debug("Notification recieved (topic=%s, payload=%s)", msg.topic, msg.payload)
            try:
                parsed = json.loads(msg.payload)
            except Exception:
                logger.error("Wrong payload not in JSON format")
            controller_id, _, _ = re.match(
                "foris-controller/([^/]+)/notification/([^/]+)/action/([^/]+)$", msg.topic
            ).groups()
            handler(parsed, controller_id)

        self.client = mqtt.Client(client_id=self.mqtt_client_id, clean_session=False)

        if self.tls_files:
            ca_path, cert_path, key_path = self.tls_files
            context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
            context.load_cert_chain(cert_path, key_path)
            context.load_verify_locations(ca_path)
            context.verify_mode = ssl.CERT_REQUIRED
            # can't assume that server cert is issued to particular hostname/ipaddress
            context.check_hostname = False
            self.client.tls_set_context(context)

        self.client.on_connect = on_connect
        self.client.on_subscribe = on_subscribe
        self.client.on_message = on_message
        self.client.on_disconnect = on_disconnect
        self.timeout = _normalize_timeout(timeout)
        self.connected = None
        if self.credentials:
            self.client.username_pw_set(*self.credentials)
        self.client.connect(host, port, CONNECT_TIMEOUT)

    def disconnect(self):
        logger.debug("Closing connection.")
        self.client.disconnect()

    def listen(self):
        logger.debug("Starting to listen.")
        if self.timeout:
            self.client.loop_start()
            self.client._thread.join(self.timeout)
            self.client.loop_stop()
        else:
            self.client.loop_forever()
        logger.debug("Listening stopped")
