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
client1 = net.addDocker('client1', ip='10.0.0.249', dcmd="python client.py", dimage="opc_client:ver1")
client2 = net.addDocker('client2', ip='10.0.0.250', dcmd="python client.py", dimage="opc_client:ver1")
client3 = net.addDocker('client3', ip='10.0.0.251', dcmd="python client.py", dimage="opc_client:ver1", mem_limit="128m", memswap_limit="384m", cpu_period = 5000)
client4 = net.addDocker('client4', ip='10.0.0.251', dcmd="python client.py", dimage="opc_client:ver1", mem_limit="32m", memswap_limit="96m", cpu_period = 1000)
server = net.addDocker('server', ip='10.0.0.252', dcmd="python server.py", dimage="opc_server:ver1") # , ports=[4840], port_bindings={4840: 4840}

info('*** Setup network\n')
s1 = net.addSwitch('s1')
s2 = net.addSwitch('s2')

net.addLink(client1, s1)
net.addLink(client2, s1, cls=TCLink, delay='1ms', bw=1)
net.addLink(client3, s1)
net.addLink(client4, s1)
net.addLink(s1, s2)
net.addLink(s2, server)
net.start()

CLI(net)

net.stop()
