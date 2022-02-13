# CamProxy4AlexaP3 - Version 1.0.0

## What the Plugin do :

The Plugin provides private Cameras in the local network for Amazon devices like Echo Show / Echo Spot / FireTV. The reqirements of Amazon for cameras are :

- encrypted Connection via TLSv1.2
- use an officiel certificate (not self signed)
- using Port 443

So it´s not possible to use private cameras (on local networks) without any cheats,
this plugin will fix this problem

## How it works:


## Change-Log

#### 2018.01.26 - lauch of Version 1.0.0

- Alpha Version for tests distributed



## Requirements

Nothing special needed, see Needed software

### Needed software

* running Plugin Alexa4P3
* SmartHomeNG >= 1.5.2
* Python >= 3.0
* for the WebInteface you need the http-module of SmartHomeNG
* SmartHomeSkill with Payload V3 in Amazon Developer Console
* working Lambda function in Amazon AWS
* running Nginx with guilty certificate (official not self signed)
* public URL via DYNDNS-Service
* reachable Port 443 (you have to move NGINX to another Port)
* Portforwarding on your router for Port 443 to your SmartHomeNG machine


## <span style="color:red">**!! Needed Access for the ProxyCam4AlexaP3 on Port 443 !!**</span>

<span style="color:red">**You have to give the Plugin access to Port 443. To do this you have to give Python permissions to bind privileged ports without root access.To setup this run the following command.It´s not allowed to Bind Symlinks. So after a update of the used Python version you have to do this again.(Python3 -> Symlink to python 3.5 after Update Python3 -> Symlink to python 3.6)**</span>

## <span style="color:red">**=================================================**</span>
<pre><code>sudo setcap CAP_NET_BIND_SERVICE=+eip /usr/bin/python3.5
</code></pre>
## <span style="color:red">**=================================================**</span>

## Supported Hardware

* all that is supported by SmartHomeNG

## Configuration

## plugin.yaml

The plugin has the following paramters in the plugin.yaml

```yaml
CamProxy4AlexaP3:
    class_name: CamProxy4AlexaP3
    class_path: plugins.camproxy4alexap3
    # port: 443 (optional)
    # video_buffer: 524280 (optional)
    # 262140 / 524280 / 1048560 try what fits to your cameras
    cert_path: '/etc/letsencrypt/live/<your.domain.net>/fullchain.pem'
    cert_path_key: '/etc/letsencrypt/live/<your.domain.net>/privkey.pem'
```

cert_path : File with your fullchain.pem for the URL where you want to reach your  proxied cameras

cert_path_key : File with your privkey.pem for the URL.

video_buffer : Size for the Videobuffer for streaming. Standard is 524280 bytes. My experience was :
- too small buffer, you have to wait a long time till the streamm starts
- too big buffer, the streams sometimes wait for the data

Please try out what value fits to your setup and Cam´s.

## items.yaml

No items or attributes have to be defined. On Startup the Plugin generates the needed attributes based on the attributes of the Alexpa4P3-Plugin.


In my point of view, no further description is needed

