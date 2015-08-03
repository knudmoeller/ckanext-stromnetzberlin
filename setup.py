from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(
	name='ckanext-stromnetzberlin',
	version=version,
	description="This is a specific harvester for the stromnetzberlin portal.",
	long_description="""\
	""",
	classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	keywords='',
	author='Fraunhofer FOKUS',
	author_email='',
	url='https://github.com/fraunhoferfokus/ckanext-stromnetzberlin',
	license='AGPL',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.stromnetzberlin'],
	include_package_data=True,
	zip_safe=False,
	install_requires=[
		# -*- Extra requirements: -*-
	],
	entry_points=\
	"""
        [ckan.plugins]
	stromnetzberlin=ckanext.stromnetzberlin.ckanharvester:StromnetzBerlinCKANHarvester
	""",
)
