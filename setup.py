#!/usr/bin/env python3
from setuptools import setup

from ssmanager import __version__ as version

setup(name="ssmanager",
      version=version,
      description="The python module interact with server-mode shadowsocks.",
      author="Shell Chen",
      author_email="me@sorz.org",
      url="https://github.com/sorz/ssmanager/",
      packages=['ssmanager'])

