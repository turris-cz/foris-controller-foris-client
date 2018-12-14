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


import pytest
import random
import string

from foris_client.buses.mqtt import MqttSender
from foris_client.buses.base import ControllerError

from .fixtures import (
    mqtt_controller, mqtt_client, MQTT_HOST, mqtt_listener,
    mqtt_notify, mosquitto_test, MQTT_PORT,
)


def test_about(mosquitto_test, mqtt_listener, mqtt_controller, mqtt_client):
    response = mqtt_client.send("about", "get", None)
    assert "errors" not in response


def test_long_messages(mosquitto_test, mqtt_listener, mqtt_controller, mqtt_client):
    data = {
        "random_characters": "".join(
            random.choice(string.ascii_letters) for _ in range(1024 * 1024))
    }
    res = mqtt_client.send("echo", "echo", {"request_msg": data})
    assert res == {"reply_msg": data}


def test_nonexisting_module(mosquitto_test, mqtt_listener, mqtt_controller, mqtt_client):
    with pytest.raises(ControllerError):
        mqtt_client.send("non-existing", "get", None)


def test_nonexisting_action(mosquitto_test, mqtt_listener, mqtt_controller, mqtt_client):
    with pytest.raises(ControllerError):
        mqtt_client.send("about", "non-existing", None)


def test_extra_data(mosquitto_test, mqtt_listener, mqtt_controller, mqtt_client):
    with pytest.raises(ControllerError):
        mqtt_client.send("about", "get", {})


def test_timeout(mosquitto_test, mqtt_listener, mqtt_controller, mqtt_client):
    mqtt_client.send("about", "get", None, timeout=1000)
    sender = MqttSender(MQTT_HOST, MQTT_PORT)
    sender.send("about", "get", None)


def test_notifications_request(mosquitto_test, mqtt_listener, mqtt_controller, mqtt_client):
    _, read_listener_output = mqtt_listener
    old_data = read_listener_output()
    mqtt_client.send("web", "set_language", {"language": "cs"})
    last = read_listener_output(old_data)[-1]
    assert last == {
        u'action': u'set_language',
        u'data': {u'language': u'cs'},
        u'kind': u'notification',
        u'module': u'web'
     }


def test_notifications_cmd(mosquitto_test, mqtt_listener, mqtt_controller, mqtt_client, mqtt_notify):
    _, read_listener_output = mqtt_listener
    data = read_listener_output()
    mqtt_notify.notify("test_module", "test_action", {"test_data": "test"})
    data = read_listener_output(data)
    assert data[-1] == {
        u'action': u'test_action',
        u'data': {u'test_data': u'test'},
        u'kind': u'notification',
        u'module': u'test_module',
    }
    mqtt_notify.notify("maintain", "reboot_required")
    data = read_listener_output(data)
    assert data[-1] == {
        u'action': u'reboot_required',
        u'kind': u'notification',
        u'module': u'maintain'
    }
