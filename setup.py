from distutils.core import setup
from os.path import exists
from platform import system

requires = []
if system == "Windows":
    requires = ["pypiwin32"]

setup(
    name = "fsmonitor",
    version = "0.1",
    description = "Filesystem monitoring",
    long_description=(open('README.rst').read() if exists('README.rst')
                      else ''),
    author = "Luke McCarthy",
    author_email = "luke@iogopro.co.uk",
    licence="MIT",
    url = "http://github.com/shaurz/fsmonitor",
    install_requires=requires,
    packages = ["fsmonitor"],
)
