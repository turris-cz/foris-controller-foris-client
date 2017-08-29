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

import pytest
import ubus

from foris_client.buses.ubus import UbusSender

from .fixtures import ubusd_test, ubusd_test2, ubus_controller, ubus_client, UBUS_PATH, UBUS_PATH2


def test_about(ubus_client):
    response = ubus_client.send("about", "get", None)
    assert "errors" not in response


def test_nonexisting_module(ubus_client):
    with pytest.raises(RuntimeError):
        ubus_client.send("non-existing", "get", None)


def test_nonexisting_action(ubus_client):
    with pytest.raises(RuntimeError):
        ubus_client.send("about", "non-existing", None)

def test_extra_data(ubus_client):
    response = ubus_client.send("about", "get", {"extra": "data"})
    assert "errors" in response


def test_reconnect(ubusd_test, ubusd_test2):
    import logging
    logging.basicConfig()
    logging.disable(logging.ERROR)
    sender1 = UbusSender(UBUS_PATH)
    assert ubus.get_socket_path() == UBUS_PATH
    assert ubus.get_connected()
    sender2 = UbusSender(UBUS_PATH2)
    assert ubus.get_socket_path() == UBUS_PATH2
    assert ubus.get_connected()
    sender1.disconnect()
    assert ubus.get_connected() is False
