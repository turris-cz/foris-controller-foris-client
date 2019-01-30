#!/usr/bin/env python

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

import argparse
import logging
import json
import uuid
import typing
import re

from foris_client import __version__

logger = logging.getLogger("foris_client")


available_buses: typing.List[str] = ['unix-socket']


try:
    __import__("ubus")
    available_buses.append("ubus")
except ModuleNotFoundError:
    pass


try:
    __import__("paho.mqtt.client")
    available_buses.append("mqtt")
except ModuleNotFoundError:
    pass


def main():
    # Parse the command line options
    parser = argparse.ArgumentParser(prog="foris-client")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true", default=False)
    parser.add_argument('--version', action='version', version=__version__)

    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument(
        "-i", "--input", dest="input", default=None, type=str, metavar="INPUT_FILE",
        help="input data file in json format (when not present no data will be sent)."
    )
    input_group.add_argument(
        "-I", "--input-json", dest="json", default=None, type=str, metavar="INPUT_JSON",
        help="input data in json format (when not present no data will be sent)."
    )
    parser.add_argument(
        "-o", "--output", dest="output", default=None, type=str, metavar="OUTPUT_FILE",
        help="where to store output json data"
    )
    parser.add_argument(
        "-m", "--module", dest="module", help="module which will be used",
        required=True, type=str,
    )
    parser.add_argument(
        "-a", "--action", dest="action", help="action which will be performed",
        required=True, type=str
    )
    parser.add_argument(
        "-t", "--timeout", dest="timeout", help="timeout in ms (default=0 - wait forever)",
        type=int, default=0
    )

    subparsers = parser.add_subparsers(help="buses", dest="bus")
    subparsers.required = True

    unix_parser = subparsers.add_parser("unix-socket", help="use unix socket to send commands")
    unix_parser.add_argument("--path", dest="path", default='/tmp/foris-controller.soc')
    if "ubus" in available_buses:
        ubus_parser = subparsers.add_parser("ubus", help="use ubus to send commands")
        ubus_parser.add_argument("--path", dest="path", default='/var/run/ubus.sock')
    if "mqtt" in available_buses:
        mqtt_parser = subparsers.add_parser("mqtt", help="use mqtt to send commands")
        mqtt_parser.add_argument("--host", dest="host", default='localhost')
        mqtt_parser.add_argument("--port", dest="port", type=int, default=1883)
        mqtt_parser.add_argument(
            "--tls-files", nargs=3, default=[], metavar=("CA_CRT_FILE", "CRT_FILE", "KEY_FILE"),
            help="Set a paths to TLS files to access mqtt via encrypted connection."
        )
        mqtt_parser.add_argument(
            "--controller-id", type=lambda x: re.match(r"[a-zA-Z]{16}", x).group().upper(),
            help="sets which controller on the messages bus should be configured (8 bytes is hex)",
        )

    options = parser.parse_args()

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig()
    logger.debug("Version %s" % __version__)

    if options.bus == "ubus":
        from foris_client.buses.ubus import UbusSender
        logger.debug("Using ubus to send commands.")
        sender = UbusSender(options.path, options.timeout)

    elif options.bus == "unix-socket":
        from foris_client.buses.unix_socket import UnixSocketSender
        logger.debug("Using unix-socket to send commands.")
        sender = UnixSocketSender(options.path, options.timeout)

    elif options.bus == "mqtt":
        from foris_client.buses.mqtt import MqttSender
        logger.debug("Using mqtt to send commands.")
        sender = MqttSender(
            options.host, options.port, options.timeout,
            tls_files=options.tls_files,
        )

    data = None
    if options.input:
        with open(options.input) as f:
            data = json.load(f)

    if options.json:
        data = json.loads(options.json)

    kwargs = {"controller_id": options.controller_id} if options.bus == "mqtt" else {}
    response = sender.send(
        options.module, options.action, data, **kwargs)
    if not options.output:
        print(json.dumps(response))
    else:
        with open(options.output, "w") as f:
            json.dump(response, f)


if __name__ == "__main__":
    main()
