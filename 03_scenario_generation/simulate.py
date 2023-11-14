#! /usr/bin/python

from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import setLogLevel

setLogLevel("info")

net = Containernet(controller=Controller)
net.addController("c0")

info('*** Adding docker containers as hosts\n')
# {HOST_NAME} = net.addDocker('{HOST_NAME}', ip = {IP}, dcmd = "python {PYTHON_SCRIPT}", dimage = "{DOCKER_IMAGE}:{TAG}", 
# environment = {"{KEY}:{VALUE}", "{KEY}:{VALUE}"...}, 
# mem_limit = {MEMORY_LIMIT}, memswap_limit = {MEMORY_ADD_SWAP_LIMIT}, cpu_quota = {CPU_QUOTA}, cpu_period = {CPU_PERIOD})

info ('*** Adding switches\n')
# {SWITCH_NAME} = net.addSwitch('{SWITCH_NAME}')

info ('*** Creating links\n')
# net.addLink({HOST_NAME}, {SWITCH_NAME}, cls=TCLink, bw={BANDWIDTH}, delay='{DELAY}ms', loss={LOSS}, max_queue_size={QUEUE_SIZE}, use_htb=True)
# net.addLink({SWITCH_NAME}, {SWITCH_NAME}, cls=TCLink, use_htb=True)

info ('*** Starting network\n')
net.start()
CLI(net)

info ('*** Stopping network')
net.stop()