#! switch_group -> group ，隨機度可以更高一些


device_list = {
    'Dev_1': {'bandwidth': 100, 'type': 'CNC', 'switch_group': 'Group_0'}, 
    'Dev_2': {'bandwidth': 1000, 'type': 'RA', 'switch_group': 'Group_4'}, 
    'Dev_3': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_6'}, ...}
application_list = {
    'App_0': {'response_timeout': 1000, 'computing_load': 200, 'bandwidth_load': 300, 'target_device_types': ['RA', 'SR']}, 
    'App_1': {'response_timeout': 100, 'computing_load': 800, 'bandwidth_load': 1800, 'target_device_types': ['AGV']}, 
    'App_2': {'response_timeout': 5, 'computing_load': 200, 'bandwidth_load': 30, 'target_device_types': ['CNC']}, ...}
server_list = {
    'Server_1': {'bandwidth': 1000, 'computing_power': 10000, 'switch_group': None, 'running_apps': []}, 
    'Server_2': {'bandwidth': 1000, 'computing_power': 1200, 'switch_group': None, 'running_apps': []}, 
    'Server_3': {'bandwidth': 1000, 'computing_power': 1200, 'switch_group': None, 'running_apps': []}, ...}
switch_list = {
    'Switch_1': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_server_members': None, 'group_device_members': ['Dev_1', 'Dev_2', 'Dev_3', 'Dev_4']}, 
    'Switch_2': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_server_members': None, 'group_device_members': ['Dev_5', 'Dev_6', 'Dev_7']}, 
    'Switch_3': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_server_members': None, 'group_device_members': ['Dev_8', 'Dev_9', 'Dev_10', 'Dev_11', 'Dev_12']}, ...}
subscriptions = {
    'Subscription_1': {'Devices': ['Dev_1'], 'Application': 'App_2', 'Weight': 0.39},
    'Subscription_2': {'Devices': ['Dev_6'], 'Application': 'App_3', 'Weight': 0.56},
    'Subscription_3': {'Devices': ['Dev_4', 'Dev_1'], 'Application': 'App_4', 'Weight': 0.28}, ...}


server_list = {
    'Server_1': {'bandwidth': 1000, 'switch_group': 'Switch_8', 'running_apps': [...], 'remain_computing_power': 7000}, 
    'Server_2': {'bandwidth': 1000, 'switch_group': 'Switch_3', 'running_apps': [...], 'remain_computing_power': 0}, 
    'Server_3': {'bandwidth': 1000, 'switch_group': 'Switch_4', 'running_apps': [...], 'remain_computing_power': 0}, ...}
switch_list = {
    'Switch_1': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': [...], 'group_server_members': 'Server_5'}, 
    'Switch_2': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': [...], 'group_server_members': 'Server_6'}, 
    'Switch_3': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': [...], 'group_server_members': 'Server_2'}, ...}
subscription_paths = {
    'Subscription_1': ['Switch_1'],
    'Subscription_2': ['Switch_2', 'Switch_3', 'Switch_4'],
    'Subscription_3': ['Switch_6', 'Switch_7', 'Switch_5'], ...}

#! switch_group -> switch，之後可以做多對一的關係
server_list = {}   
#! group_device_members -> devices，group_server_members -> servers
switch_list = {}
#! cancel 'Group'
subscriptions = {}



{('Switch_5', 'Switch_1'): 0.9650000000000001, 
 ('Switch_1', 'Switch_5'): 0.9650000000000001, 
 ('Switch_5', 'Switch_4'): 0.315, 
 ('Switch_4', 'Switch_5'): 0.315, 
 ('Switch_6', 'Switch_5'): 0.84, 
 ('Switch_5', 'Switch_6'): 0.84}

{('Switch_5', 'Switch_1'): 45.0, 
 ('Switch_1', 'Switch_5'): 45.0, 
 ('Switch_5', 'Switch_4'): 300.0, 
 ('Switch_4', 'Switch_5'): 300.0, 
 ('Switch_6', 'Switch_5'): 1215.0, 
 ('Switch_5', 'Switch_6'): 1215.0}  