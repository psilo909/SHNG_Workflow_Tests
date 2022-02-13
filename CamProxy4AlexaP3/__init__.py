#!/usr/bin/env python3
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
#  Copyright 2019 <AndreK>                <andre.kohler01@googlemail.com>
#########################################################################
#  This file is part of SmartHomeNG.   
#

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
import os
import sys
import time
from symbol import except_clause

from datetime import datetime
from builtins import Exception
from time import mktime
from datetime import timedelta





from lib.module import Modules
from lib.model.smartplugin import *
from lib.item import Items

from .camdevice import CamDevices, Cam

import logging
import uuid
import json

from .service import ThreadedServer
 

class CamProxy4AlexaP3(SmartPlugin):
    PLUGIN_VERSION = '1.0.0'
    ALLOW_MULTIINSTANCE = False
    
    
    def __init__(self, sh, video_buffer=524280, cert_path='', cert_path_key='', port=443):
        self.sh = sh
        self.logger = logging.getLogger(__name__)
        self.PATH_CERT = cert_path
        self.PATH_PRIVKEY = cert_path_key
        self.cams = CamDevices()
        self.ClientThreads = []
        self.service = ThreadedServer(self.logger, port, video_buffer, cert_path, cert_path_key,self.cams,self.ClientThreads)
        self.service.name = 'CamProxy4AlexaP3-Handler'
        # Status No. Todo
        # open    0. - make Threads stable
        # done    1. - Build a Class-Structure for Camera´s with traffic, last used, last client, active client
        # done    2. - Get all Camera-Devices - done by parse-item
        # done    3. - Parse Proxy-Url to real and back (Class Structur)
        # done    4. - Build Thread-Modell with Callback for Traffic and so on
        # open    5. - Give all the statistics to the WebInterface (not really a Problem)
        # open    6. - Inject real-Url in Client Request -> Hopefully it works
    
        
    
        # get the parameters for the plugin (as defined in metadata plugin.yaml):
        #   self.param1 = self.get_parameter_value('param1')

        # Initialization code goes here

        # On initialization error use:
        #   self._init_complete = False
        #   return

        if not self.init_webinterface():
            self._init_complete = False

        return


    def run(self):
        
        self.logger.info("Plugin '{}': start method called".format(self.get_fullname()))
        try:
            myFile = open(self.PATH_CERT,"r")
            myFile.close()
        except Exception as err:
            self.logger.error("Access Error to Cert-File {0}".format(self.PATH_CERT),' Error : ',err)
            self.alive= False
            exit(1)
        try:
            myFile = open(self.PATH_PRIVKEY,"r")
            myFile.close()
        except:
            self.logger.error("Access Error to Cert-Key-File {0}".format(self.PATH_PRIVKEY),' Error : ',err)
            self.alive= False
            exit(1)
        self.service.daemon = True
        self.service.start()
        self.alive = True
        while self.alive:
            if len(self.ClientThreads ) > 0:
                for t in self.ClientThreads:
                    if t.alive == False: 
                        self.CloseSockets(t)
                        try:            # Save Values
                            t.actCam.proxied_bytes +=t.proxied_bytes
                            self.logger.debug("ProxyCam4AlexaP3: saved proxied Bytes")
                        except Exception as err:
                            self.logger.debug("ProxyCam4AlexaP3: problem while saving proxied Bytes")
                        try:
                            Threadname = t.name
                            self.ClientThreads.remove(t)
                        except:
                            pass
                        
                        self.logger.debug("ProxyCam4AlexaP3: stopped Thread : %s " % Threadname)

            time.sleep(2)
        # Start the Service himself
        
        

    def stop(self):
        self.logger.debug("Plugin '{}': stop method called".format(self.get_fullname()))
        self.service.stop()
        self.alive = False
    
    def CloseSockets(self,thread):
        try:
            thread.mysocks.remove(thread.client)
            thread.mysocks.remove(thread.server)
        except:
            self.logger.debug("ProxyCam4AlexaP3: could not remove mysocks")
        try:
            thread.client.shutdown(socket.SHUT_RDWR)
            thread.client.close()
            self.logger.debug("ProxyCam4AlexaP3: Client socket closed")
        except Exception as errr:
            self.logger.debug("ProxyCam4AlexaP3: Client socket already close")
        try:
            thread.server.shutdown(socket.SHUT_RDWR)
            thread.server.close()
            self.logger.debug("ProxyCam4AlexaP3: Server socket closed")
        except Exception as errr:
            self.logger.debug("ProxyCam4AlexaP3: Server socket already close")

  

    def parse_item(self, item):
        """
        Default plugin parse_item method. Is called when the plugin is initialized.
        The plugin can, corresponding to its attribute keywords, decide what to do with
        the item in future, like adding it to an internal array for future reference
        :param item:    The item to process.
        :return:        If the plugin needs to be informed of an items change you should return a call back function
                        like the function update_item down below. An example when this is needed is the knx plugin
                        where parse_item returns the update_item function when the attribute knx_send is found.
                        This means that when the items value is about to be updated, the call back function is called
                        with the item, caller, source and dest as arguments and in case of the knx plugin the value
                        can be sent to the knx with a knx write function within the knx plugin.
        
        if self.has_iattr(item.conf, 'foo_itemtag'):
            self.logger.debug("Plugin '{}': parse item: {}".format(self.get_fullname(), item))
        """

           
        # add the needed Information to the Items, its hard to modify Items, but neccessary
        # add a attribute for each Stream if Proxy is defined
        # add a Camera for our own use for proxying it
        if 'alexa_csc_proxy_uri' in item.conf:
            # walk over all defined Streams
            i=1
            while i <= 3:
                myStream='alexa_proxy_url-{}'.format(i)
                if myStream in item.conf:
                    try:

                        cam_id = item.conf[myStream]
                        
                       
                        if not self.cams.exists(cam_id):
                            try:
                                self.cams.put( Cam(cam_id) )
                            except Exception as err:
                                print("Error:" ,err)
                        
                        cam = self.cams.get(cam_id)
                        # Now add the real URL to our Cam
                        
                        camera_uri = item.conf['alexa_csc_uri']
                        camera_uri = json.loads(camera_uri)
                        
                        try:
                            cam.real_Url=camera_uri['Stream{}'.format(i)]
                            myProxiedurl=item.conf['alexa_proxy_url-{}'.format(i)]
                            cam.proxied_Url = myProxiedurl
                        except Exception as err:
                            print(err)
                        
                        if 'alexa_description' in item.conf:
                            cam.name = item.conf['alexa_description']
                        
                        if not('alexa_description' in item.conf):
                            cam.name = item.conf['alexa_device']
                        
                        if 'alexa_auth_cred' in item.conf:
                            credentials = item.conf['alexa_auth_cred'].split(':')
                            cam.user = credentials[0]
                            cam.pwd = credentials[1]

                        self.logger.debug("CamProxy4AlexaP3: {}-added Camera-Streams = {}".format(item.id(), cam.real_Url))
                    except Exception as e:
                        self.logger.debug("CamProxy4AlexaP3: {}-wrong Stream Settings = {}".format(item.id(), ''))
                i +=1
            
            
    def parse_logic(self, logic):
        
        if 'xxx' in logic.conf:
            # self.function(logic['name'])
            pass

    def update_item(self, item, caller=None, source=None, dest=None):

        if item():
            if self.has_iattr(item.conf, 'foo_itemtag'):
                self.logger.debug(
                    "Plugin '{}': update_item ws called with item '{}' from caller '{}', source '{}' and dest '{}'".format(
                        self.get_fullname(), item, caller, source, dest))
            pass



    def init_webinterface(self):
        """"
        Initialize the web interface for this plugin

        This method is only needed if the plugin is implementing a web interface
        """
        try:
            self.mod_http = Modules.get_instance().get_module(
                'http')  # try/except to handle running in a core version that does not support modules
        except:
            self.mod_http = None
        if self.mod_http == None:
            self.logger.error("Plugin '{}': Not initializing the web interface".format(self.get_shortname()))
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


# ------------------------------------------
#    Webinterface of the plugin
# ------------------------------------------

import cherrypy
from jinja2 import Environment, FileSystemLoader

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
        self.tplenv = self.init_template_environment()
        self.items = Items.get_instance()


    @cherrypy.expose
    def thread_list_json_html(self):
        """
        returns a list of Threads as json structure
        """
        
        thread_data = []
        for t in self.plugin.service.ClientThreads:
            if t.alive == True:
                try:
                    thread_dict = {
                                    'Thread' : t.name,
                                    'real_URL' : t.actCam.real_Url
                                  }
                    thread_data.append(thread_dict)
                except:
                    self.logger.error('Error while build Threadlist for WebInterface')
        if len(thread_data) ==0:
            thread_dict = {
                            'Thread' : 'No Active Thread',
                            'real_URL' : ''
                          }
            thread_data.append(thread_dict)
        return json.dumps(thread_data)
    
    
    @cherrypy.expose
    def thread_details_json_html(self, thread_name):
        """
        returns a detailed Informations for a camera-Thread
        """
        info_data = []
        if thread_name != 'No Active Thread' or thread_name == '': 
            for t in self.plugin.service.ClientThreads:
                if t.name != thread_name:
                    # not this Thread selected
                    continue
                else:
                    # found correct Thread
                    try:
                        actDateTime = datetime.now()
                        duration_sec = mktime(actDateTime.timetuple()) - mktime(t.last_Session_Start.timetuple())
                        Session_duration = str(timedelta(seconds=duration_sec))
                        
                        info_data = {
                            'Name' : t.name,
                            'Video-Buffer-Size': t.BUFF_SIZE_SERVER,
                            'proxied_bytes' : t.proxied_bytes,
                            'last_Session_Start' : t.last_Session_Start.strftime("%Y-%m-%d %H:%M:%S"),
                            'Session_duration' : Session_duration,
                            'server_url' : t.server_url,
                            'peer' : t.peer,
                            
                            #Cam - Infos
                            
                            'Cam-ID' : t.actCam.id,
                            'Cam-proxied_Url' : t.actCam.proxied_Url,
                            'Cam-real_Url' : t.actCam.real_Url,
                            'Cam-User' : t.actCam.user,
                            'Cam-Password' : t.actCam.pwd,
                            }
                        break
                    except Exception as err:
                        print("Error from Service :",err )
                        info_data = {
                                    'Error occured' : 'please try again'
                                    }
        else:
            info_data = {
                        'No Active Thread' : 'select a Thread on the left side'
                        }
            
        return json.dumps(info_data)
    
    
    @cherrypy.expose
    def index(self, reload=None):
        """
        Build index.html for cherrypy

        Render the template and return the html file to be delivered to the browser

        :return: contents of the template after beeing rendered
        """
        # Collect Cams without Proxy
        cam_tls_items = []
        # Collext all Cams
        for item in self.items.return_items():
            #if (self.plugin.has_iattr(item.conf, 'alexa_csc_proxy_uri')):
            #    cam_proxied_items.append(item)
            if ((self.plugin.has_iattr(item.conf, 'alexa_csc_uri')) and not (self.plugin.has_iattr(item.conf, 'alexa_csc_proxy_uri'))):
                cam_tls_items.append(item)
        
        # Collect proxied Cams
        cam_proxied_items = []
        myCams = self.plugin.cams.Cams
        for actCam in myCams:
            newEntry=dict()
            Cam2Add=self.plugin.cams.Cams.get(actCam)
            newEntry['name'] = Cam2Add.name
            newEntry['real_Url'] = Cam2Add.real_Url
            newEntry['proxied_Url'] = Cam2Add.proxied_Url
            newEntry['proxied_mb_Session'] = "%.1f" % 0.00
            newEntry['proxied_mb_total'] = "%.1f" % (Cam2Add.proxied_bytes / 1024.0 / 1024.0)
            newEntry['Sessions_total'] = Cam2Add.Sessions_total
            newEntry['last_Session_duration'] = Cam2Add.last_Session_duration
            
            if Cam2Add.last_Session != None:
                newEntry['last_Session'] = str(Cam2Add.last_Session.isoformat())
            else:
                newEntry['last_Session'] = 'never asked for'
            
            cam_proxied_items.append(newEntry)
        
        try:        
            myService = self.plugin.service
            myThreadCount=len(myService.ClientThreads)
            # SSL-Infos
            try:
                my_Ciphers = myService.cert_ciphers
                my_Ciphers = my_Ciphers.replace(":","<br>")
                my_Cert_Dict = myService.cert_dict
                if my_Cert_Dict != '':
                    cert_subject = dict(x[0] for x in my_Cert_Dict['subject'])
                    cert_issued_to = cert_subject['commonName']
                    cert_subject = dict(x[0] for x in my_Cert_Dict['issuer'])
                    cert_issued_by = cert_subject['commonName']
                    cert_notafter = my_Cert_Dict['notAfter']
                    cert_notBefore = my_Cert_Dict['notBefore']
            except Exception as err:
                print("Error from Service :",err )
                
        except Exception as err:
            print("Error from Service :",err )
        

        
        tmpl = self.tplenv.get_template('index.html')
        return tmpl.render(plugin_shortname=self.plugin.get_shortname(), plugin_version=self.plugin.get_version(),
                           plugin_info=self.plugin.get_info(), p=self.plugin,
                           proxied_Cams=str(len(cam_proxied_items)) ,
                           standard_Cams=str(len(cam_tls_items)),
                           items_proxied=sorted(cam_proxied_items, key=lambda k: str.lower(k['name'])),
                           item_tls=sorted(cam_tls_items, key=lambda k: str.lower(k['_path'])),
                           cert_issued_by=cert_issued_by, cert_issued_to=cert_issued_to ,
                           cert_notafter=cert_notafter ,cert_notBefore=cert_notBefore,my_Ciphers=my_Ciphers
                           )
        
                                   
