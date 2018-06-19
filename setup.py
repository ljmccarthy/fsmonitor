#!/usr/bin/env python

from distutils.core import setup
from platform import system

requires = []
if system == "Windows":
    requires = ["pypiwin32"]

setup(
    name="fsmonitor",
    version="0.1",
    description="Filesystem monitoring",
    long_description=open('README.rst').read(),
    long_description_content_type="text/x-rst",
    author="Luke McCarthy",
    author_email="luke@iogopro.co.uk",
    licence="MIT",
    url="http://github.com/shaurz/fsmonitor",
    install_requires=requires,
    packages=["fsmonitor"],
)
