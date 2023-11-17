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
server1 = net.addDocker('server1', ip='10.0.0.200', dcmd="python cnc.py", dimage="cnc:ver2")
server2 = net.addDocker('server2', ip='10.0.0.201', dcmd="python cnc.py", dimage="cnc:ver2")
server3 = net.addDocker('server3', ip='10.0.0.202', dcmd="python cnc.py", dimage="cnc:ver2")
client = net.addDocker('client', ip='10.0.0.100', dcmd="python job_scheduling.py", dimage="job_scheduling:ver2", environment={"SERVER_IPS": "10.0.0.200,10.0.0.201,10.0.0.202"})

info('*** Setup network\n')
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')
s3 = net.addSwitch('s3')
s4 = net.addSwitch('s4')

net.addLink(client, s1)
net.addLink(server1, s2)
net.addLink(server2, s3)
net.addLink(server3, s4)
net.addLink(s1, s2)
net.addLink(s1, s3)
net.addLink(s1, s4)
net.start()

CLI(net)

net.stop()
