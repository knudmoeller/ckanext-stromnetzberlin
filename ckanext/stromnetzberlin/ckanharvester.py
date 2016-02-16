#!/usr/bin/python
# -*- coding: utf8 -*-

from ckan.lib.helpers import json
from ckanext.harvest.harvesters.ckanharvester import CKANHarvester

from dateutil.parser import parse

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
    """An extended CKAN harvester that imports from Stromnetz Berlin GmbHs
        CKAN and adjusts the metadata."""

    def _set_config(self, config_str):
        if config_str:
            self.config = json.loads(config_str)
        else:
            self.config = {}
        # self.api_version = 1
        # self.config['api_version'] = '1'
        # self.config['remote_groups'] = 'only_local'
        # self.config['force_all'] = True


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
        # something weird here: the value I get back from package['extras']['dates'] is sometimes a list (good),
        # sometimes a string (bad). So I use a hackish combination of eval and str that should work on both
        # cases and always give me back a list
        # dates = package['extras']['dates']
        if 'dates' in package['extras']:
            dates = eval(str(package['extras']['dates']))
            log.debug("dates: '{datestring}'".format(datestring=str(dates)))
            released = filter(lambda x: x['role'] == 'veroeffentlicht', dates)
            updated = filter(lambda x: x['role'] == 'aktualisiert', dates)
            if len(released) > 0:
                package["extras"]["date_released"] = parse(released[0]["date"]).isoformat('T')
            if len(updated) > 0:
                package["extras"]["date_updated"] = parse(updated[0]["date"]).isoformat('T')
                
        if 'temporal_coverage_from' in package['extras']:
            log.debug("adjusting temporal_coverage_from")
            package['extras']['temporal_coverage_from'] = parse(package['extras']['temporal_coverage_from']).isoformat('T')

        if 'temporal_coverage_to' in package['extras']:
            log.debug("adjusting temporal_coverage_to")
            package['extras']['temporal_coverage_to'] = parse(package['extras']['temporal_coverage_to']).isoformat('T')

        if 'contacts' in package['extras']:
            contacts = eval(str(package['extras']['contacts']))
            maintainer = filter(lambda x: x['role'] == 'ansprechpartner', contacts)
            if len(maintainer) > 0:
                package['maintainer'] = maintainer[0]['name']
                if 'email' in maintainer[0]:
                    package['maintainer_email'] = maintainer[0]['email']

        # fall back solution if no email given for Ansprechpartner
        if not package['maintainer_email']:
            package['maintainer_email'] = 'info@stromnetz-berlin.de'

        # "datensatz" and "dokument" are deprecated for newer versions of CKAN,
        # but keep information in extras
        if package['type'] == "datensatz":
            package['extras']['berlin_type'] = "datensatz"
        if package['type'] == "dokument":
            package['extras']['berlin_type'] = "dokument"

        package['type'] = "dataset"

        # add source information
        package['extras']['berlin_source'] = "harvest-stromnetzberlin"


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
