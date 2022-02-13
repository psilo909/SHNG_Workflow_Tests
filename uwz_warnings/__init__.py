#!/usr/bin/env python3
#
#########################################################################
#  Copyright 2016 René Frieß                        rene.friess(a)gmail.com
#  Version 1.1.1
#########################################################################
#
#  This file is part of SmartHomeNG.
#
#  SmartHomeNG is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHomeNG is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHomeNG. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

import logging
import requests
import re
from lib.model.smartplugin import SmartPlugin

class UWZ(SmartPlugin):
    ALLOW_MULTIINSTANCE = False
    PLUGIN_VERSION = "1.3.1"
    _base_url = 'http://www.unwetterzentrale.de/uwz/getwarning_de.php?plz=%s&uwz=UWZ-%s&lang=%s'
    _warn_levels = {'gelb':1, 'orange':2, 'rot':3, 'violett':4}
    _warn_type = ['gewitter', 'glatteisregen', 'regen', 'schnee', 'sturm', 'temperatur', 'strassenglaette']

    def __init__(self, smarthome):
        """
        Initializes the plugin
        @param apikey: For accessing the free "Tankerkönig-Spritpreis-API" you need a personal
        api key. For your own key register to https://creativecommons.tankerkoenig.de
        """
        self.logger = logging.getLogger(__name__)
        self._sh = smarthome
        self._session = requests.Session()

    def run(self):
        self.alive = True

    def stop(self):
        self.alive = False

    def get_warnings(self, plz, country="DE", lang="de"):
        url = self._base_url % (str(plz), country.upper(), lang.lower())
        response = self._session.get(url)
        response.encoding = 'utf-8'
        content = response.text
        warnings = {}
        result = re.findall(r'<div style=\"float:left;display:block;width:117px;height:110px;padding-top:6px;\"><img src=\"..\/images\/icons\/(.*?)-(.*?).gif\" width=\"117\" height=\"104\"></div>', content)
        result_text = re.findall(r'<div style=\"font-size: 18px; margin-bottom: 10px;\">(.*?)</div>', content)
        i = 0
        for warning in result:
            if warning[0] not in self._warn_type:
                self.logger.error("New type %s" % warning[0])
            warning_level = self._warn_levels[warning[1]]
            if warning[0] in warnings:
                if warning_level > warnings[warning[0]]['level']:
                    warnings[warning[0]]['level'] = warning_level
                    warnings[warning[0]]['text'] = result_text[i]
            else:
                warnings[warning[0]] = {}
                warnings[warning[0]]['level'] = warning_level
                warnings[warning[0]]['text'] = result_text[i]
            i += 1
        return warnings
