0.9.5 (2019-01-21)
------------------

* mqtt: more resilent message handling
* mqtt: request reply protocol changed
* foris-client script fix

0.9.4 (2019-01-20)
------------------

* handle advertizements as notifications (remote.advertize)
* controller_id added to sending and listening api
* python2 is no longer supported

0.9.3 (2019-01-16)
------------------

* foris-listener,foris-client: add support for tls encrypted connections
* mqtt: handle situation when the controller is disconnected
* mqtt: handle reconnects

0.9.2 (2018-12-27)
------------------

* mqtt: MqttSender will keep the connection persistent
* mqtt: timeout fixes

0.9.1 (2018-12-21)
------------------

* setup.py quick fix
* small test updates

0.9 (2018-12-21)
----------------

* mqtt bus support implemented
* PEP508 dependencies

0.8 (2018-08-14)
----------------

* using entry points for scripts
* CI - test on both python2 and python3 images
* --version argument adn print version into debug console

0.7 (2018-06-19)
----------------

* reflect foris-schema api update
* unix-socket: timeout fixes
* ubus: message format updates

0.6 (2018-03-05)
----------------

* notification witout data fix

0.5 (2017-12-13)
----------------

* ability to pass json as cmdline added (`-I` parameter) added
* long message handling

0.4 (2017-10-20)
----------------

* support for notifications added
* some other fixes

0.3 (2017-09-06)
----------------

* raise an exception when an error message is recieved
* timeout option added

0.2.1 (2017-08-31)
------------------

* fix debug message prints in ubus

0.2 (2017-08-28)
----------------

* smoother ubus reconnect

0.1 (2017-08-11)
----------------

* initial version
