#! /usr/bin/env python
################################################
# This is the stand alone version of Mantrack, #
# a tool from the AnimTrack package by J.W.    #
# Jolles. Do not distribute!                   #
################################################

from __future__ import print_function
from setuptools import setup
import sys

exec(open('mantrack/__version__.py').read())


DESCRIPTION = """
ManTrack: A standalone manual tracking package
"""
LONG_DESCRIPTION = """\
ManTrack is the standalone version of the manual tracking functionality
that is part of the (still private) AnimTrack package by J.W.Jolles.
"""

DISTNAME = 'mantrack'
MAINTAINER = 'Jolle Jolles'
MAINTAINER_EMAIL = 'j.w.jolles@gmail.com'
URL = 'http://jollejolles.com'
DOWNLOAD_URL = 'https://github.com/JolleJolles/mantrack'
LICENSE = 'Do not distribute'


def check_dependencies():
    install_requires = []

    # Make sure dependencies exist
    try:
        import future
    except ImportError:
        install_requires.append('future')
    try:
        import numpy
    except ImportError:
        install_requires.append('numpy')
    try:
        import pandas
    except ImportError:
        install_requires.append('pandas')
    try:
        import itertools
    except ImportError:
        install_requires.append('itertools')
    try:
        import animlab
    except ImportError:
        print("Package animlab is required. To install development version:")
        print("pip install git+https://github.com/JolleJolles/animlab.git")

    return install_requires


if __name__ == "__main__":

    install_requires = check_dependencies()

    setup(name=DISTNAME,
          author=MAINTAINER,
          author_email=MAINTAINER_EMAIL,
          maintainer=MAINTAINER,
          maintainer_email=MAINTAINER_EMAIL,
          description=DESCRIPTION,
          long_description=LONG_DESCRIPTION,
          url=URL,
          download_url=DOWNLOAD_URL,
          version=__version__,
          install_requires=install_requires,
          packages=['mantrack'],
          classifiers=[
                     'Intended Audience :: Science/Research',
                     'Programming Language :: Python :: 2.7',
                     'Programming Language :: Python :: 3',
                     'License :: OSI Approved :: Apache Software License',
                     'Topic :: Scientific/Engineering :: Visualization',
                     'Topic :: Scientific/Engineering :: Image Recognition',
                     'Topic :: Scientific/Engineering :: Information Analysis',
                     'Topic :: Multimedia :: Video'
                     'Operating System :: POSIX',
                     'Operating System :: Unix',
                     'Operating System :: MacOS'],
          )
