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


import uuid
import typing


def prepare_controller_id(controller_id: typing.Optional[str]):
    if controller_id is None:
        return f"{uuid.getnode():016X}"
    return controller_id


class ControllerError(Exception):
    def __init__(self, errors):
        res = ["Controller error(s) has occured:"]
        for error in errors:
            if "stacktrace" in error:
                res.append(error["stacktrace"])
            res.append(error["description"])
            res.append("\n")

        super(ControllerError, self).__init__("\n".join(res))
        self.errors = errors


def generate_controller_error(module, action):
    return type(f"ControllerError__{module}__{action}", (ControllerError,), {})


class ControllerMissing(Exception):
    def __init__(self, device_id):
        self.device_id = device_id
        super(ControllerMissing, self).__init__(f"Connection to controller {device_id} is lost.")


class BaseSender(object):
    def __init__(self, *args, **kwargs):
        self.connect(*args, **kwargs)

    def connect(self, *args, **kwargs):
        raise NotImplementedError()

    def send(self, module, action, data, timeout=None, controller_id=None):
        raise NotImplementedError()

    def disconnect(self):
        raise NotImplementedError()

    def _raise_exception_on_error(self, msg):
        if "errors" in msg:
            raise generate_controller_error(msg["module"], msg["action"])(msg["errors"])


class BaseListener(object):
    def __init__(self, *args, **kwargs):
        self.connect(*args, **kwargs)

    def listen(self):
        raise NotImplementedError()

    def connect(self, *args, **kwargs):
        raise NotImplementedError()

    def disconnect(self):
        raise NotImplementedError()
