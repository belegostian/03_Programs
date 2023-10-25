from random import randint, shuffle, choice, choices, sample, random, uniform
from collections import defaultdict

# 1. Device List
# Key: device_order, Value: {'type': string, 'net_interface': int,  'fac_group': int}
device_list = {}

# 2. Server List
# Key: server_order, Value: {'cpu': int, 'ram': int, 'net_interface': int,  'fac_group': int, 'running_apps': [string]}
server_list = {}

# 3. Switch List
# Key: switch_order, Value: {'net_interface': int, 'forward_delay': double, 'fac_group': int}
switch_list = {}

# 4. Application List
# Key: app_order, Value: {'type': string, 'c_devices': [string], 'resp_timeout': double, 'cpu_cons': double, 'ram_cons': double, 'throughput': double}
application_list = {}


# 4. Subscription List
# Key: sub_order, Value: {'app_order': string, 'devices_order': [string], 'weight': double}
subscription_list = {}