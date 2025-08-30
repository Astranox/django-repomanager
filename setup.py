#!/usr/bin/env python3

import subprocess
import sys

from setuptools import Command
from setuptools import setup

install_requires = [
    'Django>=2.1',
    'gnupg>=2.3',
]


class QualityCommand(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        checked = ['packagearchive', 'repomanager', 'setup.py', ]
        print('isort --check-only --diff -rc %s' % ' '.join(checked))
        status = subprocess.call(['isort', '--check-only', '--diff', '-rc', ] + checked)
        if status != 0:
            sys.exit(status)

        print('flake8 %s' % ' '.join(checked))
        status = subprocess.call(['flake8', ] + checked)
        if status != 0:
            sys.exit(status)

        print('python -Wd manage.py check')
        status = subprocess.call(['python', '-Wd', 'manage.py', 'check'])
        if status != 0:
            sys.exit(status)


setup(
    name='django-repomanager',
    version='0.2.1',
    description='',
    author='Mathias Ertl',
    author_email='mati@er.tl',
    url='https://github.com/Astranox/django-repomanager',
    packages=[
        'repomanager',
        'repomanager.management',
        'repomanager.management.commands',
        'repomanager.migrations',
    ],
    cmdclass={
        'code_quality': QualityCommand,
    },
    install_requires=install_requires,
    classifiers=[
        'Framework :: Django',
        'Framework :: Django :: 2.1',
        'Framework :: Django :: 2.2',
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)
