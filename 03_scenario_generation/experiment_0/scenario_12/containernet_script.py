#! /usr/bin/python

from mininet.net import Containernet
from mininet.node import Controller
from mininet.cli import CLI
from mininet.link import TCLink
from mininet.log import info ,setLogLevel

setLogLevel("info")

net = Containernet(controller=Controller)
net.addController("c0")

info('*** Adding docker containers as hosts\n')
comp2 = net.addDocker('comp2', ip='10.0.0.200', dcmd='python wrapper.py', dimage='awc_js:11-15-22', mem_limit='256m', memswap_limit='768m', cpu_period=100000, cpu_quota=100000, environment={"AWC_SERVER_IPS": "10.0.0.120,10.0.0.121,10.0.0.122,10.0.0.123,10.0.0.124,10.0.0.125", "JS_SERVER_IPS": "10.0.0.120,10.0.0.121,10.0.0.122,10.0.0.123,10.0.0.124,10.0.0.125"})
comp1 = net.addDocker('comp1', ip='10.0.0.210', dcmd='python predictive_maintenance.py', dimage='predictive_maintenance:ver2', mem_limit='192m', memswap_limit='576m', cpu_period=100000, cpu_quota=75000, environment={"PM_SERVER_IPS": ""})
comp3 = net.addDocker('comp3', ip='10.0.0.220', dcmd='python wrapper.py', dimage='js_pm_twd:11-15-22', mem_limit='96m', memswap_limit='288m', cpu_period=100000, cpu_quota=37500, environment={"JS_SERVER_IPS": "10.0.0.110,10.0.0.111,10.0.0.112,10.0.0.113,10.0.0.114,10.0.0.115,10.0.0.130,10.0.0.131,10.0.0.132,10.0.0.133,10.0.0.134,10.0.0.135,10.0.0.136,10.0.0.137", "PM_SERVER_IPS": "10.0.0.130,10.0.0.131", "TWD_SERVER_IPS": "10.0.0.114,10.0.0.115,10.0.0.124,10.0.0.125,10.0.0.134,10.0.0.135,10.0.0.136,10.0.0.137"})
comp4 = net.addDocker('comp4', ip='10.0.0.221', dcmd='python automatic_workpiece_changing.py', dimage='automatic_workpiece_changing:ver2', mem_limit='96m', memswap_limit='288m', cpu_period=100000, cpu_quota=37500, environment={"AWC_SERVER_IPS": ""})
dev1 = net.addDocker('dev1', ip='10.0.0.110', dcmd='python cnc.py', dimage='cnc:ver2')
dev2 = net.addDocker('dev2', ip='10.0.0.111', dcmd='python cnc.py', dimage='cnc:ver2')
dev3 = net.addDocker('dev3', ip='10.0.0.112', dcmd='python cnc.py', dimage='cnc:ver2')
dev4 = net.addDocker('dev4', ip='10.0.0.113', dcmd='python cnc.py', dimage='cnc:ver2')
dev5 = net.addDocker('dev5', ip='10.0.0.114', dcmd='python cnc.py', dimage='cnc:ver2')
dev6 = net.addDocker('dev6', ip='10.0.0.115', dcmd='python cnc.py', dimage='cnc:ver2')
dev7 = net.addDocker('dev7', ip='10.0.0.120', dcmd='python cnc.py', dimage='cnc:ver2')
dev8 = net.addDocker('dev8', ip='10.0.0.121', dcmd='python cnc.py', dimage='cnc:ver2')
dev9 = net.addDocker('dev9', ip='10.0.0.122', dcmd='python cnc.py', dimage='cnc:ver2')
dev10 = net.addDocker('dev10', ip='10.0.0.123', dcmd='python cnc.py', dimage='cnc:ver2')
dev11 = net.addDocker('dev11', ip='10.0.0.124', dcmd='python cnc.py', dimage='cnc:ver2')
dev12 = net.addDocker('dev12', ip='10.0.0.125', dcmd='python cnc.py', dimage='cnc:ver2')
dev13 = net.addDocker('dev13', ip='10.0.0.130', dcmd='python cnc.py', dimage='cnc:ver2')
dev14 = net.addDocker('dev14', ip='10.0.0.131', dcmd='python cnc.py', dimage='cnc:ver2')
dev15 = net.addDocker('dev15', ip='10.0.0.132', dcmd='python cnc.py', dimage='cnc:ver2')
dev16 = net.addDocker('dev16', ip='10.0.0.133', dcmd='python cnc.py', dimage='cnc:ver2')
dev17 = net.addDocker('dev17', ip='10.0.0.134', dcmd='python cnc.py', dimage='cnc:ver2')
dev18 = net.addDocker('dev18', ip='10.0.0.135', dcmd='python cnc.py', dimage='cnc:ver2')
dev19 = net.addDocker('dev19', ip='10.0.0.136', dcmd='python cnc.py', dimage='cnc:ver2')
dev20 = net.addDocker('dev20', ip='10.0.0.137', dcmd='python cnc.py', dimage='cnc:ver2')
# {HOST_NAME} = net.addDocker('{HOST_NAME}', ip = {IP}, dcmd = "python {PYTHON_SCRIPT}", dimage = "{DOCKER_IMAGE}:{TAG}", 
# environment = {"{KEY}:{VALUE}", "{KEY}:{VALUE}"...}, 
# mem_limit = {MEMORY_LIMIT}, memswap_limit = {MEMORY_ADD_SWAP_LIMIT}, cpu_quota = {CPU_QUOTA}, cpu_period = {CPU_PERIOD})

info ('*** Adding switches\n')
sw0 = net.addSwitch('sw0')
sw1 = net.addSwitch('sw1')
sw2 = net.addSwitch('sw2')
sw3 = net.addSwitch('sw3')
# {SWITCH_NAME} = net.addSwitch('{SWITCH_NAME}')

info ('*** Creating links\n')
net.addLink(sw2, sw0, cls=TCLink, use_htb=True)
net.addLink(sw0, sw1, cls=TCLink, use_htb=True)
net.addLink(sw1, sw3, cls=TCLink, use_htb=True)
net.addLink(dev7, sw2, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev8, sw2, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev9, sw2, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev10, sw2, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev11, sw2, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
net.addLink(dev12, sw2, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
net.addLink(comp2, sw0, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
net.addLink(dev1, sw1, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev2, sw1, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev3, sw1, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev4, sw1, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev5, sw1, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
net.addLink(dev6, sw1, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
net.addLink(dev13, sw3, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev14, sw3, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev15, sw3, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev16, sw3, cls=TCLink, bw=100, delay='0.05ms', use_htb=True)
net.addLink(dev17, sw3, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
net.addLink(dev18, sw3, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
net.addLink(dev19, sw3, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
net.addLink(dev20, sw3, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
net.addLink(comp3, sw3, cls=TCLink, bw=1000, delay='0.05ms', use_htb=True)
# net.addLink({HOST_NAME}, {SWITCH_NAME}, cls=TCLink, bw={BANDWIDTH}, delay='{DELAY}ms', loss={LOSS}, max_queue_size={QUEUE_SIZE}, use_htb=True)
# net.addLink({SWITCH_NAME}, {SWITCH_NAME}, cls=TCLink, use_htb=True)

info ('*** Starting network\n')
net.start()
CLI(net)

info ('*** Stopping network')
net.stop()