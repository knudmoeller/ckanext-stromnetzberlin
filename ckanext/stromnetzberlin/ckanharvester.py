#!/usr/bin/python
# -*- coding: utf8 -*-

from ckan.lib.helpers import json
from ckanext.harvest.harvesters.ckanharvester import CKANHarvester

from dateutil.parser import parse

import ConfigParser
import logging
import os
import json


log = logging.getLogger(__name__)

class GroupCKANHarvester(CKANHarvester):
    """An extended CKAN harvester that imports from Stromnetz Berlin GmbHs
        CKAN and adjusts the metadata."""

    def _set_config(self, config_str):
        if config_str:
            self.config = json.loads(config_str)
        else:
            self.config = {}
        self.api_version = 1
        self.config['api_version'] = '1'
        self.config['default_extras'] = { 'berlin_source': 'harvest-stromnetzberlin'}
        self.config['default_groups'] = ["verentsorgung"]
        # we need to run validate_config to match the named default group above with
        # the actual group with this name
        config_str = json.dumps(self.config)
        config_str = self.validate_config(config_str)
        self.config = json.loads(config_str)


class StromnetzBerlinCKANHarvester(GroupCKANHarvester):

    geo_granularity_mapping = {
        u'GERMANFEDERATION': 'Deutschland' ,
        u'STATE': 'Berlin' ,
        u'CITY': 'Berlin' ,
        u'MUNICIPALITY': 'Bezirk' ,
        None: 'Keine' ,
    }

    geo_coverage_mapping = {
        u'Berlin': 'Berlin' ,
        None: 'Berlin' ,
    }

    data_formats = [ u'csv' , u'xls' , u'xlsx' , u'xml' ]

    def info(self):
        return {'name':        'stromnetz',
                'title':       'StromnetzBerlin Harvester',
                'description': 'A CKAN Harvester for StromnetzBerlin solving data'
                'compatibility problems.'}

    def amend_package(self, package):

        def unpack_extras(packed):
            unpacked = {}
            for extra in packed:
                value = unquote_value(extra['value'])
                unpacked[extra['key']] = value
            return unpacked

        def pack_extras(unpacked):
            packed = []
            for key, value in unpacked.items():
                packed.append( { "key": key, "value": value} )
            return packed

        def unquote_value(value):
            return value.strip("\"")

        log.debug("Amending package '{name}'".format(name=package["name"]))

        if len(package['resources']) < 1:
            log.debug("There are no resources, don't import this.")
            return "unchanged"

        packed = package['extras']
        extras = unpack_extras(packed)

        # turn the date arrays into individual extras entries
        # something weird here: the value I get back from extras['dates'] is sometimes a list (good),
        # sometimes a string (bad). So I use a hackish combination of eval and str that should work on both
        # cases and always give me back a list
        # dates = extras['dates']
        if 'dates' in extras:
            dates = eval(str(extras['dates']))
            log.debug("dates: '{datestring}'".format(datestring=str(dates)))
            released = filter(lambda x: x['role'] == 'veroeffentlicht', dates)
            updated = filter(lambda x: x['role'] == 'aktualisiert', dates)
            if len(released) > 0:
                extras["date_released"] = parse(released[0]["date"]).isoformat('T')
            if len(updated) > 0:
                extras["date_updated"] = parse(updated[0]["date"]).isoformat('T')
                
        # fix capitalization of temporal_granularity
        if 'temporal_granularity' in extras:
            log.debug('adjusting temporal_granularity')
            extras['temporal_granularity'] = extras['temporal_granularity'].title()

        if 'temporal_coverage_from' in extras:
            log.debug("adjusting temporal_coverage_from")
            extras['temporal_coverage_from'] = parse(extras['temporal_coverage_from']).isoformat('T')

        if 'temporal_coverage_to' in extras:
            log.debug("adjusting temporal_coverage_to")
            extras['temporal_coverage_to'] = parse(extras['temporal_coverage_to']).isoformat('T')

        log.debug('adjusting geographical_granularity')
        geographical_granularity_old = extras.get('geographical_granularity', None)
        geographical_granularity_new = self.geo_granularity_mapping.get(geographical_granularity_old, u'Keine')
        log.debug("replacing '{}' with '{}'".format(geographical_granularity_old, geographical_granularity_new))
        extras['geographical_granularity'] = geographical_granularity_new

        log.debug('adjusting geographical_coverage')
        geographical_coverage_old = extras.get('geographical_coverage', None)
        geographical_coverage_new = self.geo_coverage_mapping.get(geographical_coverage_old, u'Keine')
        log.debug("replacing '{}' with '{}'".format(geographical_coverage_old, geographical_coverage_new))
        extras['geographical_coverage'] = geographical_coverage_new

        if 'contacts' in extras:
            contacts = eval(str(extras['contacts']))
            maintainer = filter(lambda x: x['role'] == 'ansprechpartner', contacts)
            if len(maintainer) > 0:
                package['maintainer'] = maintainer[0]['name'].decode('unicode-escape')
                if 'email' in maintainer[0]:
                    package['maintainer_email'] = maintainer[0]['email']

        # fallback solution if no email given for Ansprechpartner
        if not package['maintainer_email']:
            package['maintainer_email'] = 'info@stromnetz-berlin.de'

        resource_formats = list(map(lambda x: x['format'], package['resources']))
        extras['berlin_type'] = 'datensatz'
        if len(resource_formats) > 0 and len(set(self.data_formats) & set(resource_formats)) == 0:
            log.debug("There are data resources, so this is a document.")

        package['type'] = "dataset"

        package['extras'] = pack_extras(extras)

        log.debug("Done amending package '{name}'".format(name=package["name"]))
        
        return True

    def import_stage(self, harvest_object):
        package_dict = json.loads(harvest_object.content)
        success = True
        try:
            success = self.amend_package(package_dict)
        except ValueError, e:
            self._save_object_error(str(e), harvest_object)
            log.error('Stromnetz: ' + str(e))
            return False

        if (success == "unchanged"):
            return success

        harvest_object.content = json.dumps(package_dict)
        harvest_object.current = True
        return super(StromnetzBerlinCKANHarvester, self).import_stage(harvest_object)
