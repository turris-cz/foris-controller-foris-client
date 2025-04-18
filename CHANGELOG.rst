2.0.1 (2024-04-17)
------------------

* fix extras for test name

2.0.0 (2024-02-27)
------------------

* CI updates
* use hatchling as new build backend
* be compatible with paho-mqtt 2.X

1.0.5 (2023-07-13)
------------------

* CI updates
* using tox for tests
* publishing python packages to gitlab

1.0.4 (2021-07-21)
------------------

* move ubus socket path due to upstream change
* change URL from gitlab.labs.nic.cz to gitlab.nic.cz

1.0.3 (2019-12-05)
------------------

* fix - rewrite time.time() to time.monotonic()

1.0.2 (2019-06-05)
------------------

* mqtt: timeout fix + code cleanup

1.0.1 (2019-05-28)
------------------

* mqtt: keep background sending thread running

1.0 (2019-05-27)
----------------

* mqtt: replies are processed from another thread
* mqtt: should be more resilent through mqtt server restarts
* mqtt: should be able to process who requests in parallel (using send_internal and queue.Queue)

0.9.9 (2019-04-03)
------------------

* generate different exception for each api call
* mqtt: nicer client_id

0.9.8 (2019-02-14)
------------------

* mqtt: controller-id format fix

0.9.7 (2019-01-31)
------------------

* mqtt: can set path to credentials file
* controller_id format changed

0.9.6 (2019-01-30)
------------------

* fix foris-client binary for non-mqtt buses
* setup.py: make ubus and mqtt buses optional

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
