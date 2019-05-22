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
import os
import typing
import re

from foris_client import __version__
from foris_client.utils import read_passwd_file

logger = logging.getLogger("foris_listener")

LOGGER_MAX_LEN = 10000


available_buses: typing.List[str] = ["unix-socket"]


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
    parser = argparse.ArgumentParser(prog="foris-listener")
    parser.add_argument("-d", "--debug", dest="debug", action="store_true", default=False)
    parser.add_argument("--version", action="version", version=__version__)

    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        default=None,
        type=str,
        metavar="OUTPUT_FILE",
        help="where to store output json data",
    )
    parser.add_argument(
        "-m", "--module", dest="module", help="to listen", required=False, type=str, default=None
    )
    parser.add_argument(
        "-t",
        "--timeout",
        dest="timeout",
        help="timeout in ms (default=0 - listen forever)",
        type=int,
        default=0,
    )
    parser.add_argument(
        "-l",
        "--log-file",
        default=None,
        help="file where the logs will we appended",
        required=False,
    )

    subparsers = parser.add_subparsers(help="buses", dest="bus")
    subparsers.required = True

    unix_parser = subparsers.add_parser(
        "unix-socket", help="use unix socket to obtain notifications"
    )
    unix_parser.add_argument("--path", dest="path", default="/tmp/foris-controller.soc")
    if "ubus" in available_buses:
        ubus_parser = subparsers.add_parser("ubus", help="use ubus to obtain notificatins")
        ubus_parser.add_argument("--path", dest="path", default="/var/run/ubus.sock")
    if "mqtt" in available_buses:
        mqtt_parser = subparsers.add_parser("mqtt", help="use mqtt to obtain notificatins")
        mqtt_parser.add_argument("--host", dest="host", default="localhost")
        mqtt_parser.add_argument("--port", dest="port", type=int, default=1883)
        mqtt_parser.add_argument(
            "--tls-files",
            nargs=3,
            default=[],
            metavar=("CA_CRT_FILE", "CRT_FILE", "KEY_FILE"),
            help="Set a paths to TLS files to access mqtt via encrypted connection.",
        )
        mqtt_parser.add_argument(
            "--controller-id",
            type=lambda x: re.match(r"[0-9a-zA-Z]{16}", x).group().upper(),
            help="sets which controller on the messages bus should be configured (8 bytes is hex)",
        )
        mqtt_parser.add_argument(
            "--passwd-file",
            type=lambda x: read_passwd_file(x),
            help="path to passwd file (first record will be used to authenticate)",
            default=None,
        )

    options = parser.parse_args()

    logging_format = "%(levelname)s:%(name)s:%(message)." + str(LOGGER_MAX_LEN) + "s"
    if options.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(threadName)s: " + logging.BASIC_FORMAT)
    else:
        logging.basicConfig(format=logging_format)
    logger.debug("Version %s" % __version__)

    if options.log_file:
        logging_handler = logging.FileHandler(options.log_file)
        if options.debug:
            logging_handler.setLevel(logging.DEBUG)
        logging_handler.setFormatter(
            logging.Formatter("[%(created)f:%(process)d]" + logging.BASIC_FORMAT)
        )
        logging.getLogger().addHandler(logging_handler)

    if options.output:
        f = open(options.output, "w")
        f.flush()

        def print_to_file(data, controller_id):
            f.write(f"{controller_id} {json.dumps(data)}\n")
            f.flush()

        handler = print_to_file
    else:
        f = None

        def print_to_stdout(data, controller_id):
            print(f"{controller_id} {json.dumps(data)}")

        handler = print_to_stdout

    try:
        if options.bus == "ubus":
            from foris_client.buses.ubus import UbusListener

            logger.debug("Using ubus to listen for notifications.")
            listener = UbusListener(options.path, handler, options.module, options.timeout)

        elif options.bus == "unix-socket":
            from foris_client.buses.unix_socket import UnixSocketListener

            logger.debug("Using unix-socket to listen for notifications.")
            try:
                os.unlink(options.path)
            except OSError:
                pass
            listener = UnixSocketListener(options.path, handler, options.module, options.timeout)

        elif options.bus == "mqtt":
            from foris_client.buses.mqtt import MqttListener

            logger.debug("Using mqtt to listen for notifications.")
            listener = MqttListener(
                options.host,
                options.port,
                handler,
                options.module,
                options.timeout,
                tls_files=options.tls_files,
                controller_id=getattr(options, "controller_id", "+"),
                credentials=options.passwd_file,
            )

        listener.listen()
    finally:
        if f:
            f.close()


if __name__ == "__main__":
    main()
