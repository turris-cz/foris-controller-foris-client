Foris controller
================
An program/library which is act as a client of foris-controller.

Requirements
============

* python3

Installation
============

	``python3 setup.py install``

Usage
=====
Connect to foris-controller using unix-socket and perform `get` action on `about` module.


	foris-client -m about -a get unix-socket --path /tmp/foris-controller-socket


Connect to foris-controller using ubus dtto.

	foris-client -m about -a get -i data.json ubus --path /tmp/ubus.soc


Connect to foris-controller using mqtt dtto.

	foris-client -m about -a get -i data.json mqtt --host localhost --port 11883


Connect to foris-controller using mqtt remotely dtto.

	foris-client -m about -a get -i data.json mqtt --host localhost --port 11883 --tls-files ca.crt token.crt token.key --controller-id d89ef373059c
