#!/usr/bin/env python

#
# foris-client
# Copyright (C) 2017-2020 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
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

from setuptools import setup
from foris_client import __version__

DESCRIPTION = """
An program/library which is act as a client of foris-controller.
"""

setup(
    name='foris-client',
    version=__version__,
    author='CZ.NIC, z.s.p.o. (http://www.nic.cz/)',
    author_email='packaging@turris.cz',
    packages=[
        'foris_client',
        'foris_client.client',
        'foris_client.listener',
        'foris_client.buses',
    ],
    url='https://gitlab.nic.cz/turris/foris-controller/foris-client',
    license='COPYING',
    description=DESCRIPTION,
    long_description=open('README.rst').read(),
    setup_requires=[
        'pytest-runner',
    ],
    tests_require=[
        'pytest',
        'foris-controller',
        'ubus',
        'paho-mqtt',
    ],
    extras_require={
        'testsuite': [
            "foris-controller @ git+https://gitlab.nic.cz/turris/foris-controller/foris-controller.git#egg=foris-controller",
            "foris-controller-testtools @ git+https://gitlab.nic.cz/turris/foris-controller/foris-controller-testtools.git#egg=foris-controller-testtools",
        ],
        'ubus': ["ubus"],
        'mqtt': ["paho-mqtt"],
    },
    entry_points={
        "console_scripts": [
            "foris-client = foris_client.client.__main__:main",
            "foris-listener = foris_client.listener.__main__:main",
        ]
    },
    dependency_links=[
        "git+https://gitlab.nic.cz/turris/foris-controller/foris-controller.git#egg=foris-controller",
        "git+https://gitlab.nic.cz/turris/foris-controller/foris-controller-testtools.git#egg=foris-controller-testtools",
    ],
    zip_safe=False,
)
