#!/usr/bin/env python

from distutils.core import setup
from platform import system

requires = []
if system == "Windows":
    requires = ["pypiwin32"]

version = "0.1"

setup(
    name="fsmonitor",
    version=version,
    description="Filesystem monitoring",
    long_description=open('README.rst').read(),
    long_description_content_type="text/x-rst",
    author="Luke McCarthy",
    author_email="luke@iogopro.co.uk",
    licence="MIT",
    url="http://github.com/ljmccarthy/fsmonitor",
    download_url="https://pypi.org/project/fsmonitor/%s/" % version,
    project_urls={
        'Homepage': 'http://github.com/ljmccarthy/fsmonitor',
        'Download': 'https://pypi.org/project/fsmonitor/%s/' % version,
        'Issue tracker': 'http://github.com/ljmccarthy/fsmonitor/issues',
    },
    keywords=["filesystem", "monitor"],
    platforms="Any",
    install_requires=requires,
    packages=["fsmonitor"],
)
