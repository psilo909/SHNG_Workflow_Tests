#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2018- Serge Wagener                     serge@wagener.family
#########################################################################
#  This file is part of SmartHomeNG.
#
#  Sample plugin for new plugins to run with SmartHomeNG version 1.4 and
#  upwards.
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

from jinja2 import Environment, FileSystemLoader
import cherrypy
from lib.module import Modules
from lib.model.smartplugin import *
from lib.item import Items

import asyncio
import datetime
import os
import threading
import base64
import json
from random import randint
from time import sleep
import pyatv
from pyatv.const import Protocol

KNOWN_COMMANDS = ['rc_top_menu', 'rc_home', 'rc_home_hold', 'rc_menu', 'rc_select', 'rc_next', 'rc_previous', 'rc_play', 'rc_pause',
                    'rc_play_pause', 'rc_stop', 'rc_up', 'rc_down', 'rc_right', 'rc_left', 'rc_volume_up', 'rc_volume_down',
                    'rc_suspend', 'rc_wakeup', 'rc_skip_forward', 'rc_skip_backward', 'rc_set_position', 'rc_set_shuffle', 'rc_set_repear']

class AppleTV(SmartPlugin):
    """
    Main class of the Plugin. Does all plugin specific stuff and provides
    the update functions for the items
    """

    PLUGIN_VERSION = '1.6.1'

    def __init__(self, sh):
        """
        Initalizes the plugin.
        """
        # Call init code of parent class (SmartPlugin)
        super().__init__()

        # get the parameters for the plugin (as defined in metadata plugin.yaml):
        self._ip = self.get_parameter_value('ip')
        self._atv_scan_timeout = self.get_parameter_value('scan_timeout')

        self._atv_reconnect_timeout = 10
        # All devices
        self._atvs = None
        # Device used in this instance
        self._atv = None

        self._items = {}
        self._state = {}
        self._loop = asyncio.get_event_loop()
        self._push_listener_loop = None
        self._cycle = 5
        self._scheduler_running = False
        self._playstatus = None
        self._is_playing = False
        self._position = 0
        self._position_timestamp = datetime.datetime.now()
        self._credentials = None
        self._credentialsfile = None
        self._paired = False
        self.__push_listener_thread = None

        # Remote control and power control API
        self._atv_rc = None
        self._atv_pwc = None


        self.init_webinterface()
        return

    def run(self):
        """
        Run method for the plugin
        """
        self.logger.debug("Run method called")
        self.alive = True
        self._loop.run_until_complete(self.discover())
        self._loop.run_until_complete(self.connect())

    def stop(self):
        """
        Stop method for the plugin
        """
        self.logger.debug(
            "Plugin '{}': stop method called".format(self.get_fullname()))
        self._loop.stop()
        while self._loop.is_running():
            pass
        self._loop.run_until_complete(self.disconnect())
        self._loop.close()
        self.alive = False

    def parse_item(self, item):
        """
        Parse items into internal array on plugin startup
        """

        if self.has_iattr(item.conf, 'appletv'):
            self.logger.debug("parse item: {}".format(item.id()))
            _item = self.get_iattr_value(item.conf, 'appletv')
            # Add items to internal array
            if not _item in self._items:
                self._items[_item] = []
            self._items[_item].append(item)
            return self.update_item

    def parse_logic(self, logic):
        """
        Default plugin parse_logic method
        """
        if 'xxx' in logic.conf:
            # self.function(logic['name'])
            pass

    async def execute_rc(self, command):

        if (command in KNOWN_COMMANDS):
            command = command[3:]
            self.logger.info(
                "Sending remote command {} to Apple TV {}".format(command, self._atv.name))
            if hasattr(self._atv_rc, command):
                try:
                    result = await getattr(self._atv_rc, command)()
                except:
                    self.logger.error("Error launching coroutine {}".format(command))
            else:
                self.logger.error("Coroutine {} not found".format(command))
        else:
            self.logger.warning(
                "Unknown remote command {}, ignoring".format(command))
            return

    def update_item(self, item, caller=None, source=None, dest=None):
        """
        Item has been updated

        :param item: item to be updated towards the plugin
        :param caller: if given it represents the callers name
        :param source: if given it represents the source
        :param dest: if given it represents the dest
        """
        if self.alive and caller != self.get_shortname():
            if self.has_iattr(item.conf, 'appletv'):
                _value = self.get_iattr_value(item.conf,'appletv')
                self.logger.debug('Value: {}'.format(_value))
                if (_value == 'power'):
                    if item():
                        self._loop.create_task(self._atv_pwc.turn_on())
                    else:
                        self._loop.create_task(self._atv_pwc.turn_off())
                elif (_value == 'playing_position_percent'):
                    _position_percent = item()
                    if not 'playing_total_time' in self._state or not self._state['playing_total_time']:
                        _total_time = 0
                    else:
                        _total_time = self._state['playing_total_time']
                    _position = _total_time * _position_percent / 100
                    self.logger.debug("Setting position to {}% = {}/{}".format(_position_percent, _position, _total_time))
                    self._update_position(_position, False)
                    self._loop.create_task(self._atv_rc.set_position(_position))
                elif (_value == 'playing_shuffle'):
                    self.logger.debug('Setting shuffle to {}'.format(item()))
                    self._loop.create_task(self._atv_rc.set_shuffle(item()))
                    #self._update_items('playing_shuffle_text', pyatv.convert.shuffle_str(item()))
                elif (_value == 'playing_repeat'):
                    self.logger.debug('Setting repeat to {}'.format(item()))
                    self._loop.create_task(self._atv_rc.set_repeat(item()))
                elif (_value in KNOWN_COMMANDS):
                    item(False, self.get_shortname(), self._atv.name)
                    self._loop.create_task(self.execute_rc(_value))
                else:
                    self.logger.warning('Unknown command {}'.format(_value))

    def save_credentials(self):
        self.logger.debug('Saving credentials: {}'.format(self._credentials))
        self._credentialsfile = os.path.join(os.path.dirname(__file__), '{}.credentials'.format(self._atv.identifier))
        _credentials = open(self._credentialsfile, 'w')
        _credentials.write(self._credentials)
        _credentials.close()

    def load_credentials(self):
        self._paired = False
        self._credentialsfile = os.path.join(os.path.dirname(__file__), '{}.credentials'.format(self._atv.identifier))
        try:
            _credentials = open(self._credentialsfile, 'r')
            self._credentials = _credentials.read()
            _credentials.close()
            self.logger.debug('Stored credentials found')
            result = self._atv.set_credentials(self._atv.main_service().protocol, self._credentials)
            if result:
                self.logger.debug('Credentials successfully set')
                self._paired = True
            else:
                self.logger.warning('Error setting credentials, please re-pair !')
        except:
            self.logger.warning('No credentials found, you must pair this device !')
            return False
        return True

    async def discover(self):
        """
        Discovers Apple TV's on local mdns domain       
        """
        self.logger.debug("Discovering Apple TV's in your network for {} seconds...".format(
            int(self._atv_scan_timeout)))
        self._atvs = await pyatv.scan(self._loop, timeout=self._atv_scan_timeout)

        if not self._atvs:
            self.logger.warning("No Apple TV found")
        else:
            self.logger.info("Found {} Apple TV's:".format(len(self._atvs)))
            for _atv in self._atvs:
                _markup = '-'
                if str(_atv.address) == str(self._ip):
                    _markup = '*'
                    self._atv = _atv
                self.logger.info(" {} {}, IP: {}".format(_markup, _atv.name, _atv.address))

    async def connect(self):
        """
        Connects to this instance's Apple TV     
        """
        if not self._atv:
            if len(self._atvs) > 0:
                self.logger.debug("No device given in plugin.yaml or device not found, using first autodetected device")
                self._atv = self._atvs[0]
                self._ip = str(self._atv.address)
            else:
                return False
        if self._atv.name:
                self._update_items('name', self._atv.name)
        if self._ip:
            self._update_items('ip', self._ip)
        if self._atv.device_info.mac:
            self._update_items('mac', self._atv.device_info.mac)
        if self._atv.device_info.model:
            self._update_items('model', str(self._atv.device_info.model).replace('DeviceModel.',''))
        if self._atv.device_info.operating_system.TvOS:
            self._update_items('os', 'TvOS ' + self._atv.device_info.version)
        else:
            self._update_items('os', self._atv.device_info.version)
        self.load_credentials()
        self.logger.info("Connecting to '{0}' on ip '{1}'".format(self._atv.name, self._ip))
        self._device = await pyatv.connect(self._atv, self._loop)
        self._atv_rc = self._device.remote_control
        self._atv_pwc = self._device.power
        if self._atv_pwc.power_state == pyatv.const.PowerState.On:
            self._update_items('power', True)
        else:
            self._update_items('power', False)
        self._push_listener_thread = threading.Thread(
            target=self._push_listener_thread_worker, name='ATV listener')
        self._push_listener_thread.start()
        return True

    async def disconnect(self):
        """
        Stop listening to push updates and logout of this istances Apple TV     
        """
        self.logger.info("Disconnecting from '{0}'".format(self._atv.name))
        self._device.push_updater.stop()
        self._device.close()

    async def update_artwork(self):
        try:
            _artwork = await self._device.metadata.artwork() # width=512
            self.logger.debug("Artwork {}x{} type {}".format(_artwork.width, _artwork.height, _artwork.mimetype))
            self._update_items("artwork_width", _artwork.width)
            self._update_items("artwork_height", _artwork.height)
            self._update_items("artwork_mimetype", _artwork.mimetype)
            self._update_items("artwork_base64", base64.b64encode(_artwork.bytes).decode())
        except:
            pass

    def _update_items(self, attribute, value):
        #self.logger.debug('Updating {} with value {}'.format(attribute, value))
        self._state[attribute] = value
        if attribute in self._items:
            for _item in self._items[attribute]:
                _item(value, self.get_shortname())

    def _update_position(self, new_position, from_device):
        if not new_position:
            new_position = 0
        if not 'playing_total_time' in self._state or not self._state['playing_total_time']:
            self._update_items('playing_total_time', 0)
        if from_device:
            self._position = new_position
            self._position_timestamp = datetime.datetime.now()
        self._update_items('playing_position', new_position)
        if new_position > 0 and self._state['playing_total_time'] > 0:   
            self._update_items('playing_position_percent', int(round(new_position / self._state['playing_total_time'] * 100)))
        else:
            self._update_items('playing_position_percent', 0)

    def handle_async_exception(self, loop, context):
        self.logger.error('*** ASYNC EXCEPTIONM ***')
        self.logger.error('Context: {}'.format(context))
        raise

    def _push_listener_thread_worker(self):
        """
        Thread to run asyncio loop. This avoids blocking the main plugin thread
        """
        asyncio.set_event_loop(self._loop)
        self._loop.set_exception_handler(self.handle_async_exception)
        self._device.push_updater.listener = self
        self._device.push_updater.start()
        self._device.power.listener = self
        self._device.listener = self
        while self._loop.is_running():
            pass
        try:
            self.logger.debug("Loop running")
            _cycle = 0
            while True:
                self._loop.run_until_complete(asyncio.sleep(0.25))
                _cycle += 1
                if _cycle >= 2:
                    if self._state['playing_state'] == 3:
                        _time_passed = int(round((datetime.datetime.now() - self._position_timestamp).total_seconds()))
                        self._update_position(self._position + _time_passed, False)
                    _cycle = 0
        except:
            #self.logger.error('*** DEBUG ***')
            return

# ------------------------------------------
#    Callbacks from AppleTV push listener
# ------------------------------------------

    def playstatus_update(self, updater, playstatus):
        """
        Callback for pyatv, is called on currently playing update
        """
        #self.logger.debug('playstatus_update: {}'.format(playstatus))
        self._loop.create_task(self.update_artwork())
        self._playstatus = playstatus
        try:
            _app = self._device.metadata.app
            self._update_items('playing_app_name', _app.name if _app.name else '---')
            self._update_items('playing_app_identifier', _app.identifier if _app.identifier else '---')
        except:
            pass
        self._update_items('playing_state', playstatus.device_state.value)
        self._update_items('playing_state_text', pyatv.convert.device_state_str(playstatus.device_state))
        self._update_items('playing_fingerprint', playstatus.hash)
        self._update_items('playing_genre', playstatus.genre if playstatus.genre else '---')
        self._update_items('playing_album', playstatus.album if playstatus.album else '---')
        self._update_items('playing_title', playstatus.title if playstatus.title else '---')
        self._update_items('playing_artist', playstatus.artist if playstatus.artist else '---')
        self._update_items('playing_type', playstatus.media_type.value)
        self._update_items('playing_type_text', pyatv.convert.media_type_str(playstatus.media_type))
        self._update_position(playstatus.position, True)
        self._update_items('playing_total_time', playstatus.total_time)
        if playstatus.position and playstatus.total_time:
            self._update_items('playing_position_percent', round(playstatus.position / playstatus.total_time * 100))
        else:
            self._update_items('playing_position_percent', 0)
        self._update_items('playing_repeat', playstatus.repeat.value)
        self._update_items('playing_repeat_text', pyatv.convert.repeat_str(playstatus.repeat))
        self._update_items('playing_shuffle', playstatus.shuffle.value)
        self._update_items('playing_shuffle_text', pyatv.convert.shuffle_str(playstatus.shuffle))

    def playstatus_error(self, updater, exception):
        """
        Callback for pyatv, is called on push update error
        """
        self.logger.warning("PushListener error, retrying in {0} seconds".format(
            self._atv_reconnect_timeout))
        updater.start(initial_delay=self._atv_reconnect_timeout)

    def powerstate_update(self, old_state, new_state):
        self.logger.debug('Power state changed from {0:s} to {1:s}'.format(old_state, new_state))
        if new_state == pyatv.const.PowerState.On:
            self._update_items('power', True)
        else:
            self._update_items('power', False)

    def connection_lost(self, exception):
        self.logger.warning("Lost connection:", str(exception))

    def connection_closed(self):
        self.logger.warning("Connection closed!")

# ------------------------------------------
#    Methods to be used in logics
# ------------------------------------------

    def is_on(self):
        return self._state['power']

    def is_playing(self):
        if self._state['playing_state'] == pyatv.const.DeviceState.Playing.value:
            return True
        else:
            return False

    def pause(self):
        self._loop.create_task(self.execute_rc('rc_pause'))

    def play(self):
        self.logger.warning('Playing, sending command !!')
        self._loop.create_task(self.execute_rc('rc_play'))

# ------------------------------------------
#    Webinterface of the plugin
# ------------------------------------------

    def init_webinterface(self):
        """"
        Initialize the web interface for this plugin

        This method is only needed if the plugin is implementing a web interface
        """
        try:
            # try/except to handle running in a core version that does not support modules
            self.mod_http = Modules.get_instance().get_module('http')
        except:
            self.mod_http = None
        if self.mod_http == None:
            self.logger.error(
                "Plugin '{}': Not initializing the web interface".format(self.get_shortname()))
            return False

        import sys
        if not "SmartPluginWebIf" in list(sys.modules['lib.model.smartplugin'].__dict__):
            self.logger.warning(
                "Plugin '{}': Web interface needs SmartHomeNG v1.5 and up. Not initializing the web interface".format(self.get_shortname()))
            return False

        # set application configuration for cherrypy
        webif_dir = self.path_join(self.get_plugin_dir(), 'webif')
        config = {
            '/': {
                'tools.staticdir.root': webif_dir,
            },
            '/static': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': 'static'
            }
        }

        # Register the web interface as a cherrypy app
        self.mod_http.register_webif(WebInterface(webif_dir, self),
                                     self.get_shortname(),
                                     config,
                                     self.get_classname(), self.get_instance_name(),
                                     description='')

        return True

class WebInterface(SmartPluginWebIf):

    def __init__(self, webif_dir, plugin):
        """
        Initialization of instance of class WebInterface

        :param webif_dir: directory where the webinterface of the plugin resides
        :param plugin: instance of the plugin
        :type webif_dir: str
        :type plugin: object
        """
        self.logger = logging.getLogger(__name__)
        self.webif_dir = webif_dir
        self.plugin = plugin
        self.items = Items.get_instance()
        self.tplenv = self.init_template_environment()
        self.pinentry = False

    @cherrypy.expose
    def index(self, reload=None):
        """
        Build index.html for cherrypy

        Render the template and return the html file to be delivered to the browser

        :return: contents of the template after beeing rendered 
        """
        # get list of items with the attribute knx_dpt
        plgitems = []
        _instance = self.plugin.get_instance_name()
        if _instance:
            _keyword = 'appletv@{}'.format(_instance)
        else:
            _keyword = 'appletv'
        for item in self.items.return_items():
            if _keyword in item.conf:
                plgitems.append(item)
        tmpl = self.tplenv.get_template('index.html')
        return tmpl.render(p=self.plugin, items=sorted(plgitems, key=lambda k: str.lower(k['_path'])), pinentry=self.pinentry)

    @cherrypy.expose
    def get_data_html(self, dataSet=None):
        """
        Return data to update the webpage

        For the standard update mechanism of the web interface, the dataSet to return the data for is None

        :param dataSet: Dataset for which the data should be returned (standard: None)
        :return: dict with the data needed to update the web page.
        """
        if dataSet is None:
            data = {}
            data['state'] = self.plugin._state
            # return it as json the the web page
            try:
                return json.dumps(data)
            except Exception as e:
                self.logger.error("get_data_html exception: {}".format(e))
                #self.logger.debug(data)
        return {}

    @cherrypy.expose
    def button_pressed(self, button=None, pin=None):
        if button == "discover":
            self.logger.debug('Discover button pressed')
            self.plugin._loop.create_task(self.plugin.discover())
        elif button == "start_authorization":
            self.logger.debug('Start authentication')
            self.pinentry = True

            _protocol = self.plugin._atv.main_service().protocol
            _task = self.plugin._loop.create_task(
                pyatv.pair(self.plugin._atv, _protocol, self.plugin._loop)
            )
            while not _task.done():
                sleep(0.1)
            self._pairing = _task.result()
            if self._pairing.device_provides_pin:
                self._pin = None
                self.logger.info('Device provides pin')
            else:
                self._pin = randint(1111,9999)
                self.logger.info('SHNG must provide pin: {}'.format(self._pin))
                
            self.plugin._loop.create_task(self._pairing.begin())

        elif button == "finish_authorization":
            self.logger.debug('Finish authentication')
            self.pinentry = False
            self._pairing.pin(pin)
            _task = self.plugin._loop.create_task(self._pairing.finish())
            while not _task.done():
                sleep(0.1)
            if self._pairing.has_paired:
                self.logger.info('Pairing successfull !')
                self.plugin._credentials = self._pairing.service.credentials
                self.plugin.save_credentials()
            else:
                self.logger.error('Unable to pair, wrong Pin ?')
            self.plugin._loop.create_task(self._pairing.close())
        else:
            self.logger.warning(
                "Unknown button pressed in webif: {}".format(button))
        raise cherrypy.HTTPRedirect('index')
