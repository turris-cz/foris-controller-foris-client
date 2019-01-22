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

import itertools
import json
import os
import pytest
import subprocess
import time
import uuid


MQTT_HOST = "localhost"
MQTT_PORT = 11883
MQTT_ID = os.environ.get("TEST_CLIENT_ID", "%012x" % uuid.getnode())

SOCK_PATH = "/tmp/foris-client-test.soc"
NOTIFICATIONS_SOCK_PATH = "/tmp/foris-client-notifications-test.soc"
NOTIFICATIONS_OUTPUT_PATH = "/tmp/foris-client-notifications-test.out"
UBUS_PATH = "/tmp/ubus-foris-client-test.soc"
UBUS_PATH2 = "/tmp/ubus-foris-client-test2.soc"
LISTENER_LOG = "/tmp/foris-client-listener.txt"

EXTRA_MODULE_PATHS = [
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "test_modules", "echo")
]


def wait_for_mqtt_ready():
    from paho.mqtt import client as mqtt

    def on_connect(client, userdata, flags, rc):
        client.subscribe(f"foris-controller/{MQTT_ID}/notification/remote/action/advertize")

    def on_message(client, userdata, msg):
        try:
            if json.loads(msg.payload)["data"]["state"] in ["started", "running"]:
                client.loop_stop(True)
        except Exception:
            pass

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, 30)
    client.loop_start()
    client._thread.join(5)


def read_listener_output(old_data=None):
    while not os.path.exists(NOTIFICATIONS_OUTPUT_PATH):
        time.sleep(0.2)

    while True:
        with open(NOTIFICATIONS_OUTPUT_PATH) as f:
            data = f.readlines()
        last_data = [json.loads(e.strip().split(" ", 1)[1]) for e in data]
        if not old_data == last_data:
            break

    return last_data

@pytest.fixture(scope="session")
def mosquitto_test(request):

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull

    mosquitto_path = os.environ.get("MOSQUITTO_PATH", "/usr/sbin/mosquitto")
    mosquitto_instance = subprocess.Popen([mosquitto_path, "-v", "-p", str(MQTT_PORT)], **kwargs)
    yield mosquitto_instance
    mosquitto_instance.kill()


@pytest.fixture(scope="session")
def ubusd_test():
    try:
        os.unlink(UBUS_PATH)
    except:
        pass

    ubusd_instance = subprocess.Popen(["ubusd", "-A", "tests/ubus-acl", "-s", UBUS_PATH])
    time.sleep(0.1)
    yield ubusd_instance
    ubusd_instance.kill()
    try:
        os.unlink(UBUS_PATH)
    except:
        pass


@pytest.fixture(scope="session")
def ubusd_test2():
    try:
        os.unlink(UBUS_PATH2)
    except:
        pass

    ubusd_instance = subprocess.Popen(["ubusd", "-A", "tests/ubus-acl", "-s", UBUS_PATH2])
    time.sleep(0.1)
    yield ubusd_instance
    ubusd_instance.kill()
    try:
        os.unlink(UBUS_PATH2)
    except:
        pass


@pytest.fixture(scope="session")
def ubus_controller(request, ubusd_test):
    while not os.path.exists(UBUS_PATH):
        time.sleep(0.3)

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull

    extra_paths = list(itertools.chain.from_iterable(
        [("--extra-module-path", e) for e in EXTRA_MODULE_PATHS]))

    env_dict = dict(os.environ)
    env_dict['FC_UPDATER_MODULE'] = "foris_controller_testtools.svupdater"
    kwargs['env'] = env_dict

    process = subprocess.Popen(
        [
            "python", "-m", "foris_controller.controller", "-d", "-m", "about", "-m", "web",
            "-m", "echo", "-m", "maintain", "-m", "remote",
            "--backend", "mock"
        ] + extra_paths + ["ubus", "--path", UBUS_PATH],
        **kwargs
    )
    yield process

    process.kill()


@pytest.fixture(scope="session")
def mqtt_controller(request, mosquitto_test):

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull

    extra_paths = list(itertools.chain.from_iterable(
        [("--extra-module-path", e) for e in EXTRA_MODULE_PATHS]))

    env_dict = dict(os.environ)
    env_dict['FC_UPDATER_MODULE'] = "foris_controller_testtools.svupdater"
    kwargs['env'] = env_dict

    process = subprocess.Popen(
        [
            "python", "-m", "foris_controller.controller", "-d", "-m", "about", "-m", "web",
            "-m", "echo", "-m", "maintain", "-m", "remote",
            "--backend", "mock"
        ] + extra_paths + ["mqtt", "--host", MQTT_HOST, "--port", str(MQTT_PORT)],
        **kwargs
    )
    yield process

    process.kill()


@pytest.fixture(scope="session")
def unix_listener(request):
    try:
        os.unlink(NOTIFICATIONS_SOCK_PATH)
    except Exception:
        pass

    try:
        os.unlink(NOTIFICATIONS_OUTPUT_PATH)
    except Exception:
        pass

    try:
        os.unlink(LISTENER_LOG)
    except Exception:
        pass

    kwargs = {"preexec_fn": lambda: os.environ.update(PYTHONUNBUFFERED="1")}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull
    process = subprocess.Popen([
        "foris-listener", "-d", "-o", NOTIFICATIONS_OUTPUT_PATH, "-l", LISTENER_LOG,
        "unix-socket", "--path", NOTIFICATIONS_SOCK_PATH
    ], **kwargs)

    while True:
        if os.path.exists(LISTENER_LOG):
            with open(LISTENER_LOG) as f:
                if "Starting to listen" in f.read():
                    break
        time.sleep(0.3)

    yield process, read_listener_output

    try:
        os.unlink(LISTENER_LOG)
    except Exception:
        pass

    process.kill()


@pytest.fixture(scope="session")
def mqtt_listener(request, mosquitto_test):
    try:
        os.unlink(LISTENER_LOG)
    except Exception:
        pass

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull
    args = [
        "python", "-m", "foris_client.listener", "-d",
        "-o", NOTIFICATIONS_OUTPUT_PATH, "-l", LISTENER_LOG,
        "mqtt", "--host", MQTT_HOST, "--port", str(MQTT_PORT),
    ]
    process = subprocess.Popen(args, **kwargs)

    while True:
        if os.path.exists(LISTENER_LOG):
            with open(LISTENER_LOG) as f:
                if "Starting to listen" in f.read():
                    break
        time.sleep(0.3)

    yield process, read_listener_output

    try:
        os.unlink(LISTENER_LOG)
    except Exception:
        pass

    process.kill()


@pytest.fixture(scope="session")
def unix_controller(request):
    try:
        os.unlink(SOCK_PATH)
    except Exception:
        pass

    kwargs = {}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull

    env_dict = dict(os.environ)
    env_dict['FC_UPDATER_MODULE'] = "foris_controller_testtools.svupdater"
    kwargs['env'] = env_dict

    extra_paths = list(itertools.chain.from_iterable(
        [("--extra-module-path", e) for e in EXTRA_MODULE_PATHS]))

    process = subprocess.Popen(
        [
            "python", "-m", "foris_controller.controller", "-d", "-m", "remote",
            "-m", "about", "-m", "web", "-m", "echo", "-m", "maintain",
            "--backend", "mock",
        ] + extra_paths + [
            "unix-socket", "--path", SOCK_PATH, "--notifications-path", NOTIFICATIONS_SOCK_PATH
        ],
        **kwargs
    )
    yield process
    process.kill()


@pytest.fixture(scope="function")
def ubus_client(ubusd_test, ubus_controller):
    from foris_client.buses.ubus import UbusSender
    wait_process = subprocess.Popen(
        ["ubus", "wait_for", "foris-controller-about", "-s", UBUS_PATH])
    wait_process.wait()

    sender = UbusSender(UBUS_PATH)
    yield sender
    sender.disconnect()


@pytest.fixture(scope="function")
def unix_socket_client(unix_controller):
    from foris_client.buses.unix_socket import UnixSocketSender
    while not os.path.exists(SOCK_PATH):
        time.sleep(0.3)
    sender = UnixSocketSender(SOCK_PATH)
    yield sender
    sender.disconnect()


@pytest.fixture(scope="function")
def mqtt_client(mosquitto_test, mqtt_controller):
    # wait for started notification or wait for 5 seconds
    wait_for_mqtt_ready()

    from foris_client.buses.mqtt import MqttSender
    sender = MqttSender(MQTT_HOST, MQTT_PORT)
    yield sender
    sender.disconnect()


@pytest.fixture(scope="session")
def ubus_listener(request):
    try:
        os.unlink(NOTIFICATIONS_OUTPUT_PATH)
    except Exception:
        pass

    try:
        os.unlink(LISTENER_LOG)
    except Exception:
        pass

    kwargs = {"preexec_fn": lambda: os.environ.update(PYTHONUNBUFFERED="1")}
    if not request.config.getoption("--debug-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull
    process = subprocess.Popen([
        "foris-listener", "-d", "-o", NOTIFICATIONS_OUTPUT_PATH, "-l", LISTENER_LOG,
        "ubus", "--path", UBUS_PATH
    ], **kwargs)

    while True:
        if os.path.exists(LISTENER_LOG):
            with open(LISTENER_LOG) as f:
                if "Listening to 'foris-controller-*'" in f.read():
                    break
        time.sleep(0.3)

    try:
        os.unlink(LISTENER_LOG)
    except Exception:
        pass

    yield process, read_listener_output
    process.kill()


@pytest.fixture(scope="function")
def unix_notify(unix_listener):
    from foris_controller.buses.unix_socket import UnixSocketNotificationSender
    while not os.path.exists(NOTIFICATIONS_SOCK_PATH):
        time.sleep(0.2)
    sender = UnixSocketNotificationSender(NOTIFICATIONS_SOCK_PATH)
    yield sender
    sender.disconnect()


@pytest.fixture(scope="function")
def ubus_notify(ubus_listener):
    from foris_controller.buses.ubus import UbusNotificationSender
    while not os.path.exists(UBUS_PATH):
        time.sleep(0.2)
    sender = UbusNotificationSender(UBUS_PATH)
    yield sender
    sender.disconnect()


@pytest.fixture(scope="function")
def mqtt_notify(mqtt_listener):
    from foris_controller.buses.mqtt import MqttNotificationSender

    wait_for_mqtt_ready()

    sender = MqttNotificationSender(MQTT_HOST, MQTT_PORT)
    yield sender
    sender.disconnect()
