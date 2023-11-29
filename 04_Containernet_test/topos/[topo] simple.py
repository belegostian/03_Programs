#!/usr/bin/python

from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info, setLogLevel

setLogLevel('info')

net = Containernet(controller=Controller)
net.addController('c0')

info('*** Adding server and client container\n')
app1 = net.addDocker('js_app', ip='10.0.0.251', dcmd="python tool_wear_detection.py", dimage="tool_wear_detection:ver1", environment={"TWD_SERVER_IPS": "10.0.0.252"})
dev1 = net.addDocker('cnc', ip='10.0.0.252', dcmd="python cnc.py", dimage="cnc:ver2")

info('*** Setup network\n')
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')

net.addLink(app1, s1)
net.addLink(s1, s2)
net.addLink(s2, dev1)
net.start()

CLI(net)

net.stop()
