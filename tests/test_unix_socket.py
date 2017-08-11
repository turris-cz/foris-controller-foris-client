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


from .fixtures import unix_controller, unix_socket_client


def test_about(unix_socket_client):
    response = unix_socket_client.send("about", "get", None)
    assert "errors" not in response


def test_nonexisting_module(unix_socket_client):
    response = unix_socket_client.send("non-existing", "get", None)
    assert "errors" in response


def test_nonexisting_action(unix_socket_client):
    response = unix_socket_client.send("about", "non-existing", None)
    assert "errors" in response

def test_extra_data(unix_socket_client):
    response = unix_socket_client.send("about", "get", {})
    assert "errors" in response
