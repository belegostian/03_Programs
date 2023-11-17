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
client = net.addDocker('client', ip='10.0.0.251', dcmd="python wrapper.py", dimage="awc_pm:11-13-31-01", environment={"AWC_SERVER_IPS": "10.0.0.252", "PM_SERVER_IPS": "10.0.0.252"})
server = net.addDocker('server', ip='10.0.0.252', dcmd="python cnc.py", dimage="cnc:ver2")

info('*** Setup network\n')
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')

net.addLink(client, s1)
net.addLink(s1, s2)
net.addLink(s2, server)
net.start()

CLI(net)

net.stop()
