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

import os
import pytest
import subprocess
import time


SOCK_PATH = "/tmp/foris-client-test.soc"
UBUS_PATH = "/tmp/ubus-foris-client-test.soc"
UBUS_PATH2 = "/tmp/ubus-foris-client-test2.soc"


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
    if request.config.getoption("--suppress-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull

    process = subprocess.Popen([
        "foris-controller", "-d", "--backend","mock", "ubus", "--path", UBUS_PATH
    ], **kwargs)
    yield process

    process.kill()


@pytest.fixture(scope="session")
def unix_controller(request):
    try:
        os.unlink(SOCK_PATH)
    except:
        pass

    kwargs = {}
    if request.config.getoption("--suppress-output"):
        devnull = open(os.devnull, 'wb')
        kwargs['stderr'] = devnull
        kwargs['stdout'] = devnull

    process = subprocess.Popen([
        "foris-controller", "-d", "--backend", "mock", "unix-socket", "--path", SOCK_PATH
    ], **kwargs)
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
