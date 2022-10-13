#!/usr/bin/env python
from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()


setup(
    name='evok',
    version='2.4.18',
    description='',
    long_description=readme(),
    author='Tomas Knot',
    author_email='knot@unipi.technology',
    url='https://github.com/UniPiTechnology/evok',
    packages=[
        'evok',
	'tornadorpc_evok',
	'UnipiDali'
    ],
    classifiers=[
		'Development Status :: 5 - Production/Stable',
		'Environment :: Console',
		'Intended Audience :: Developers',
		'Programming Language :: Python :: 2'
    ],
    license='Apache License 2.0',
    keywords='evok unipi development',
)
