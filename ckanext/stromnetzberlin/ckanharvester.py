#!/usr/bin/python
# -*- coding: utf8 -*-

from ckan.lib.helpers import json
from ckanext.harvest.harvesters.ckanharvester import CKANHarvester

import ConfigParser
import logging
import os


config = ConfigParser.RawConfigParser()
config_dir = os.path.dirname(os.path.abspath(__file__))
config.read(config_dir + '/config.ini')

logfile_path = config.get('Logger', 'logfile')
logfile_directory = os.path.dirname(logfile_path)
if logfile_directory and not os.path.exists(logfile_directory):
    os.makedirs(logfile_directory)

formatter = logging.Formatter(config.get('Logger', 'format'))
fh = logging.FileHandler(logfile_path)
fh.setFormatter(formatter)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(fh)


class GroupCKANHarvester(CKANHarvester):
    """An extended CKAN harvester that also imports remote groups, for that api version 1 is enforced"""

    api_version = 1
    """Enforce API version 1 for enabling group import"""

    def _set_config(self, config_str):
        """Enforce API version 1 for enabling group import"""
        if config_str:
            self.config = json.loads(config_str)
        else:
            self.config = {}
        self.api_version = 1
        self.config['api_version'] = '1'
        self.config['remote_groups'] = 'only_local'
        self.config['force_all'] = True


class StromnetzBerlinCKANHarvester(GroupCKANHarvester):
    def info(self):
        return {'name':        'stromnetz',
                'title':       'StromnetzBerlin Harvester',
                'description': 'A CKAN Harvester for StromnetzBerlin solving data'
                'compatibility problems.'}

    def amend_package(self, package):
        log.debug("Amending package '{name}'".format(name=package["name"]))
        package['groups'] = ['verentsorgung']
        
        # turn the date arrays into individual extras entries
        dates = package['extras']['dates']
        log.debug("dates: '{datestring}'".format(datestring=str(dates)))
        for date in package["extras"]["dates"]:
            if date["role"] == "veroeffentlicht":
                package["extras"]["date_released"] = date["date"]
            if date["role"] == "aktualisiert":
                package["extras"]["date_updated"] = date["date"]

    def import_stage(self, harvest_object):
        package_dict = json.loads(harvest_object.content)
        try:
            self.amend_package(package_dict)
        except ValueError, e:
            self._save_object_error(str(e), harvest_object)
            log.error('Stromnetz: ' + str(e))
            return
        harvest_object.content = json.dumps(package_dict)
        super(StromnetzBerlinCKANHarvester, self).import_stage(harvest_object)
