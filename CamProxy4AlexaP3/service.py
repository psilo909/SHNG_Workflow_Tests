# https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/steps-to-create-a-smart-home-skill
# https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/smart-home-skill-api-reference
import os
import sys
import socket
import threading
import ssl
import time
import select
import errno
from datetime import datetime
from builtins import Exception
from time import mktime
from datetime import timedelta




class ThreadedServer(threading.Thread):
    def __init__(self, logger,port, video_buffer,cert_path,cert_path_key, Cams, ClientThreads):
        threading.Thread.__init__(self)
        self.logger = logger
        self.host = '192.168.178.37'
        self.port = int(port)
        self.video_buffer = int(video_buffer)
        self.cert_path = cert_path
        self.cert_path_key = cert_path_key
        self.ClientThreads = ClientThreads
        self.sock = None
        self.running = False
        self.FirstRound = True
        self.Cams = Cams
        self.setName('CamProxy4AlexaP3')
        self.cert_dict = ssl._ssl._test_decode_cert(self.cert_path)    
        self.cert_ciphers = 'EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:'  
        self.cert_ciphers += 'AES256+EDH:ECDHE-RSA-AES256-GCM-SHA384:'
        self.cert_ciphers += 'ECDHE-RSA-AES256-SHA384:ECDHE-RSA-AES128-GCM-SHA256:'
        self.cert_ciphers += 'ECDHE-RSA-AES128-SHA256:DHE-RSA-AES256-GCM-SHA384'
            
    
    
    def stop(self):
        self.logger.info("ProxyCamAlexaP4: service stopping")
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        self.running= False
        
    def run(self):
        self.logger.info("ProxyCamAlexaP4: service starting")
        if self.FirstRound:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                #self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.bind(('', self.port))
                self.sock.listen(5)
                self.FirstRound=False
                self.running= True
                #================================
                # SSL-Settings
                #================================
                context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                # add Certificate to context
                context.load_cert_chain(self.cert_path, self.cert_path_key)  
                # add ciphers to context
                context.set_ciphers(self.cert_ciphers)
        aktThread = 0        
        while self.running:
            client, address = self.sock.accept()
            try:
                conn = context.wrap_socket(client, server_side=True)
            except Exception as err:
                self.logger.error("ProxyCam4AlexaP3: SSL-Error - {} ".format(err))
                pass

            client.settimeout(5)
 
            try:
                # Clean up old Threads
                for t in self.ClientThreads:
                    if t.alive == False:
                        try:
                            t.actCam.proxied_bytes +=t.proxied_bytes
                            self.ClientThreads.remove(t)
                        except:
                            pass
                        
                self.ClientThreads.append(listenProxy(conn,address,self.logger,self.Cams,self.video_buffer))
                aktThread +=1
                if aktThread > 99999:
                    aktThread = 1
                lastAdded = len(self.ClientThreads )-1
                NewThreadName ="CamThread-{0:06d}".format(aktThread)
                self.ClientThreads[lastAdded].name = NewThreadName

                self.logger.info("ProxyCam4AlexaP3: Added Thread %s" % NewThreadName)
                self.ClientThreads[lastAdded].daemon = True
                self.ClientThreads[lastAdded].start()

            except Exception as err:
                self.logger.info("ProxyCam4AlexaP3: NewThreadError - {}".format(err))
            
            self.logger.debug("ProxyCam4AlexaP3: new Thread added, total Threads:{} ".format(str(len(self.ClientThreads ))))

            
            
class listenProxy(threading.Thread):
    def __init__(self, client, address,logger,cams,videoBuffer=524280):
        threading.Thread.__init__(self)
        self.logger = logger
        self.mysocks = []
        self.client = client
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.mysocks.append(client)
        self.mysocks.append(self.server)
        self.server_url = False
        self.alive = False
        self.serversend = 0
        self.BUFF_SIZE_SERVER=videoBuffer
        self.cams = cams
        self.proxied_bytes = 0
        self.peer = ''
        self.actCam = None
        self.last_Session_Start = datetime.now()

        
    def stop(self, txtInfo = ''):
        if txtInfo=='Server socket is dead':
            pass
        self.logger.debug("ProxyCam4AlexaP3: Cam Thread stopped")
        self.mysocks.remove(self.client)
        self.mysocks.remove(self.server)
        try:
            self.client.shutdown(socket.SHUT_RDWR)
            self.client.close()
        except Exception as err:
            self.logger.debug("ProxyCam4AlexaP3: Cam Thread cannot close client-socket - {}".format(err))
        try:
            self.server.shutdown(socket.SHUT_RDWR)
            self.server.close()
        except Exception as err:
            self.logger.debug("ProxyCam4AlexaP3: Cam Thread cannot close Server-socket-{}".format(err))
        self.logger.debug("ProxyCam4AlexaP3: Cam Thread stopped - %s" % txtInfo)
        self.actCam.proxied_bytes +=self.proxied_bytes
        try:
            self.actCam.last_Session_End = datetime.now()
            duration_sec = mktime(self.actCam.last_Session_End.timetuple()) - mktime(self.actCam.last_Session_Start.timetuple())
            self.actCam.last_Session_duration = str(timedelta(seconds=duration_sec))
        except:
            self.logger.debug("ProxyCam4AlexaP3: Problem during calculating duration-{}".format(err))
        self.alive = False
        #self.ClientThreads.remove(self)
        
        
        
    def run(self):
        BUFF_SIZE_CLIENT=4096
        BUFF_SIZE_SERVER=self.BUFF_SIZE_SERVER
        self.logger.info("ProxyCam4AlexaP3: Cam Thread startet")
        self.alive = True
        serverblock = b''
        clientblock = b''
        loopcount =0
        
        while self.alive:
            if loopcount==50:
                #self.logger.debug("ProxyCam4AlexaP3: Cam Thread running in loop-{}".format(self._name))
                loopcount=0
            else:
                loopcount +=1
            # check if all sockets are online
            if not self.issocketvalid(self.client):
                self.stop('Client socket is dead')
                continue        # loop
            if not self.server and self.server_url: # and not self.issocketvalid(self.server) ???? When has state 107 passed ??? 
                self.stop('Server socket is dead')
                continue        # loop
            readable, writable, exceptional = select.select(self.mysocks, [], [])
            #self.logger.debug("Got readable socket")
            for myActSock in readable:
                if myActSock == self.server:
                    try:
                        if self.server_url:
                            serverblock = b''
                            while True:
                                serverdata = self.server.recv(BUFF_SIZE_SERVER)
                                if serverdata:
                                    serverblock += serverdata
                                if len(serverdata) < BUFF_SIZE_SERVER:
                                    break
                        if serverblock:
                            # send data from Server to Client
                            self.client.send(serverblock)
                            #if len(serverblock)<10000:
                            #    self.logger.info("Server-sends:{}".format(serverblock.decode()))
                            if self.actCam != None:
                                try:
                                    self.proxied_bytes += len(serverblock)
                                except Exception as err:
                                    self.logger.info("Server-Block incosistnent")
                            '''
                            self.serversend += 1
                            if self.serversend == 3:
                                self.logger.info("ProxyCam4AlexaP3: Time for Stop - three times got Server-Request")
                                print ("Time for Stop three times got Server-Request")
                            # That means :
                            # Cam send -> Describe OK
                            # Cam send -> Setup
                            # Cam send -> Play OK
                            # Now everything should ready to stream to client
                            '''
                    except:
                        self.logger.info("ProxyCam4AlexaP3: Server disconnected right now not connected")
                        pass
                elif myActSock == self.client:
                    try:
                        
                        try:
                            self.peer = self.client.getpeername()[0]
                        except Exception as err:
                            self.logger.info("Problem by by getting Peer-Name")

                        clientblock = b''
                        while True:
                            clientdata = self.client.recv(BUFF_SIZE_CLIENT)
                            if clientdata:
                                clientblock += clientdata
                            if len(clientdata) < BUFF_SIZE_CLIENT:
                                break

                        
                        
                        if clientblock:
                            self.logger.debug("ProxyCam4AlexaP3: Client-Message-{}".format(str(clientblock.decode())))
                            if not self.server_url:
                                try:
                                    try:
                                        serverUrl, serverport,self.actCam =self.getUrl(clientblock.decode())
                                    except Exception as err:
                                        self.logger.debug("Error while parsing readl URL")
                                    if ('DESCRIBE' in clientblock.decode()):
                                        injectedUrl = self.InjectRealUrl(clientblock)

                                        #self.logger.debug("Client-Msg-org-{}".format(str(clientblock.decode())))                                        
                                        self.logger.debug("Client-Msg-new-{}".format(str(injectedUrl.decode())))
                                        clientblock = injectedUrl
                                        
                                    try:
                                        self.server.connect((serverUrl, int(serverport)))
                                        #self.server.settimeout(5)
                                        self.server_url = True
                                        self.logger.debug("ProxyCam4AlexaP3: connected to Server")
                                    except Exception as err:
                                        self.logger.debug("not able to connect to Server-{}".format(err))
                                except Exception as err:
                                    self.logger.debug("got no ServerUrl / ServerPort / ActualCam :{}".format(err))
                                   
                            # Send data to Server if connected
                                                        
                            try:
                                self.server.send(clientblock)
                            except Exception as err:
                                self.logger.debug("Error while server-send {}".format(err))

                                
                            if 'TEARDOWN' in clientblock.decode():
                                self.stop('TEARDOWN')
                            if 'PAUSE' in clientblock.decode():
                                self.stop('PAUSE')

                        else:
                            self.stop('Client-hang up')
                            continue        # loop
                            #self.logger.debug("ProxyCam4AlexaP3: Client-Message hang up")
                            #self.stop('Client-Message hang up')
                            #raise
                            #pass # error('Client disconnected')
                    except Exception as err:
                        self.logger.debug("ProxyCam4AlexaP3: Error in Client-Block-{}".format(err))
                        self.stop('Error in Client-Block')
                        pass
                        #return False

    def issocketvalid(self, socket_instance):
        """ Return True if this socket is connected. """
        if not socket_instance:
            return False

        try:
            socket_instance.getsockname()
        except socket.error as err:
            err_type = err.args[0]
            if err_type == errno.EBADF:  # 9: Bad file descriptor
                return False

        err_type = None
        try:
            socket_instance.getpeername()
        except socket.error as err:
            err_type = err.args[0]
        if err_type in [errno.EBADF, errno.ENOTCONN]:  # 9: Bad file descriptor.
            return False  # 107: Transport endpoint is not connected

        return True


    def getUrl(self, request):
        webserver = ''
        # parse the first line
        first_line = request.split('\n')[0]

        # get url
        url = first_line.split(' ')[1]
        http_pos = url.find("://")  # find pos of ://
        if (http_pos == -1):
            temp = url
        else:
            temp = url[(http_pos + 3):]  # get the rest of url
        myCam = self.cams.get(temp)
        myCam.last_Session_Start = datetime.now()
        myCam.last_Session = myCam.last_Session_Start
        myCam.Sessions_total += 1
        temp=myCam.real_Url
        
        port_pos = temp.find(":")  # find the port pos (if any)

        # find end of web server
        webserver_pos = temp.find("/")
        if webserver_pos == -1:
            webserver_pos = len(temp)

        webserver = ""
        port = -1
        if (port_pos == -1 or webserver_pos < port_pos):

            # default port
            port = 554
            webserver = temp[:webserver_pos]

        else:  # specific port
            port = int((temp[(port_pos + 1):])[:webserver_pos - port_pos - 1])
            webserver = temp[:port_pos]
        
        webserver = "{}".format(webserver)
        webserver = '192.168.178.9'
        port = 554
        self.logger.debug("got real Webserver-{}-".format(webserver))        
        return webserver, port, myCam

    def InjectRealUrl(self,orgRequest):
        readableRequest = orgRequest.decode()
        first_line = readableRequest.split('\n')[0]

        url = first_line.split(' ')[1]
        http_pos = url.find("://")  # find pos of ://
        if (http_pos == -1):
            temp = url
        else:
            temp = url[(http_pos + 3):]  # get the rest of url
        myCam = self.cams.get(temp)
        if myCam.user == '' and myCam.pwd == '':
            NewUrl = "rtsp://%s" % (myCam.real_Url)
        elif myCam.pwd == '':
            NewUrl = "rtsp://%s%s%s",myCam.user,"@",myCam.real_Url
        else:
            NewUrl = "rtsp://%s%s%s%s%s",myCam.user,":",myCam.pwd,"@",myCam.real_Url
        
        newStreamInfo = readableRequest.replace(url,NewUrl)
        try:
            myResponse = newStreamInfo.encode()#encoding='UTF-8',errors='strict')
        except Exception as err:
            self.logger.debug("Encoding Error :{}".format(err))            
        
        
        return myResponse

