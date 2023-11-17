from random import randint, shuffle, choice, choices, sample, random, uniform
from collections import defaultdict

# 1. Device List
# Key: Device Name, Value: {'bandwidth': Bandwidth, 'type': Type, 'switch_group': Switch Group} #! switch_group -> group 就好
device_list = {}

# 2. Server List
# Key: Server Name, Value: {'bandwidth': Bandwidth, 'computing_power': Computing Power, 'switch_group': Switch Group, 'running_apps': [List of Running Apps]}
server_list = {}

# 3. Switch List
# Key: Switch Name, Value: {'bandwidth': Bandwidth, 'forwarding_rate': Forwarding Rate, 'group_device_members': [List of Device Members], 'group_server_members': [List of Server Members]}
switch_list = {}

# 4. Application List
# Key: Application Name, Value: {'response_timeout': Response Timeout, 'computing_load': Computing Load, 'bandwidth_load': Bandwidth Load}
application_list = {}

def generate_regular_key_devices():
    global device_list  # Use the global device_list
    device_list.clear()  # Clear any existing data
    
    # Generate total number of devices (between 10 and 30)
    total_devices = randint(10, 30)
    
    # Generate number of CNC machines (at least 1, up to total_devices/2 to leave room for other types)
    num_cnc = randint(1, total_devices // 2)
    
    # Generate number of other types based on CNC
    num_ra = randint(int(0.5 * num_cnc), int(1 * num_cnc))
    num_sr = randint(int(1 * num_cnc), int(3 * num_cnc))
    num_agv = randint(int(0.3 * num_cnc), int(0.5 * num_cnc))
    
    # Generate groups
    device_counter = 1  # Start from 1 for regular keys like Dev_1, Dev_2,...
    group_counter = 0  # To keep track of group number
    
    while device_counter <= total_devices:
        group_size = randint(2, 6)  # Size of each group
        num_cnc_in_group = 1  # At least one CNC in each group
        
        # Try to fulfill the group size, but don't exceed the total number of devices
        group_size = min(group_size, total_devices - device_counter + 1)  # +1 because device_counter starts from 1
        
        # Try to fulfill the group size with CNCs, but don't exceed the total number of CNCs
        num_cnc_in_group = min(num_cnc_in_group, num_cnc)
        
        # Number of other devices in the group
        num_ra_in_group = min(randint(0, num_cnc_in_group), num_ra)
        num_agv_in_group = min(randint(0, num_cnc_in_group), num_agv)
        num_sr_in_group = min(group_size - num_cnc_in_group - num_ra_in_group - num_agv_in_group, num_sr)
        
        # Update remaining device counts
        num_cnc -= num_cnc_in_group
        num_ra -= num_ra_in_group
        num_agv -= num_agv_in_group
        num_sr -= num_sr_in_group
        
        # Create group
        group_name = f"Group_{group_counter}"
        for i in range(num_cnc_in_group):
            device_list[f"Dev_{device_counter}"] = {'bandwidth': 100, 'type': 'CNC', 'switch_group': group_name}
            device_counter += 1
        for i in range(num_ra_in_group):
            device_list[f"Dev_{device_counter}"] = {'bandwidth': 100, 'type': 'RA', 'switch_group': group_name}
            device_counter += 1
        for i in range(num_agv_in_group):
            device_list[f"Dev_{device_counter}"] = {'bandwidth': 100, 'type': 'AGV', 'switch_group': group_name}
            device_counter += 1
        for i in range(num_sr_in_group):
            device_list[f"Dev_{device_counter}"] = {'bandwidth': 100, 'type': 'SR', 'switch_group': group_name}
            device_counter += 1
        
        # Increment group counter
        group_counter += 1

def generate_initial_applications():
    global application_list  # Use the global application_list
    application_list.clear()  # Clear any existing data

    # Generate total number of applications (between 3 and 8)
    total_apps = randint(6, 9)

    # Define possible attributes
    timeout_thresholds = [5, 20, 100, 1000]  # in ms
    computing_loads = [200, 400, 800]
    bandwidth_loads = [30, 300, 1800]  # in Kbps
    target_device_types = [
        ['CNC'], 
        ['CNC', 'SR'], 
        ['RA', 'SR'], 
        ['CNC', 'RA'], 
        ['RA'], 
        ['RA', 'AGV'], 
        ['AGV']
    ]

    # Make sure each timeout threshold appears at least once
    selected_timeouts = sample(timeout_thresholds, len(timeout_thresholds))
    while len(selected_timeouts) < total_apps:
        selected_timeouts.append(choices(timeout_thresholds, [1, 1, 1, 2])[0])
    
    for i in range(total_apps):
        timeout = selected_timeouts[i]
        
        # Higher probability for greater computing_loads with smaller timeouts
        computing_load = choices(computing_loads, [2, 1, 1] if timeout <= 20 else [1, 1, 2])[0]
        
        # Higher probability for greater bandwidth_loads with greater computing_loads
        bandwidth_load = choices(bandwidth_loads, [1, 1, 2] if computing_load >= 400 else [2, 1, 1])[0]
        
        # Higher probability for certain target_device_types with smaller timeouts
        target_types = choices(target_device_types, [2, 2, 1, 1, 1, 1, 1] if timeout <= 20 else [1, 1, 1, 1, 1, 1, 1])[0]

        # Add to application_list
        application_list[f"App_{i}"] = {
            'response_timeout': timeout,
            'computing_load': computing_load,
            'bandwidth_load': bandwidth_load,
            'target_device_types': target_types
        }

def generate_initial_servers():
    global server_list  # Use the global server_list
    server_list.clear()  # Clear any existing data

    # Calculate total number of servers based on number of devices and number of groups
    total_devices = len(device_list)
    total_groups = len(set([device['switch_group'] for device in device_list.values()]))
    total_servers = randint(int(0.2 * total_devices), int(0.4 * total_devices))
    total_servers = min(total_servers, total_groups)
    
    # Define possible computing powers
    computing_powers = [1200, 6000, 10000]

    # The server with 10000 computing power is unique
    num_high_power = 1 if total_servers > 1 else 0

    # Remaining servers are mainly low power
    num_low_power = int((total_servers - num_high_power) * 0.75)
    num_medium_power = total_servers - num_high_power - num_low_power

    server_counter = 1  # Start from 1 for regular keys like Server_1, Server_2,...
    for i in range(num_high_power):
        server_list[f"Server_{server_counter}"] = {'bandwidth': 1000, 'computing_power': 10000, 'switch_group': None, 'running_apps': None}
        server_counter += 1
    for i in range(num_low_power):
        server_list[f"Server_{server_counter}"] = {'bandwidth': 1000, 'computing_power': 1200, 'switch_group': None, 'running_apps': None}
        server_counter += 1
    for i in range(num_medium_power):
        server_list[f"Server_{server_counter}"] = {'bandwidth': 1000, 'computing_power': 6000, 'switch_group': None, 'running_apps': None}
        server_counter += 1

def generate_initial_switches():
    global switch_list  # Use the global switch_list
    switch_list.clear()  # Clear any existing data

    # Calculate total number of switches based on number of groups
    total_groups = len(set([device['switch_group'] for device in device_list.values()]))
    total_switches = total_groups + 1  # +1 for the independent switch

    # Initialize a defaultdict to hold devices for each group
    group_device_members = defaultdict(list)

    # Populate group_device_members from device_list
    for dev_key, dev_val in device_list.items():
        group_device_members[dev_val['switch_group']].append(dev_key)

    # Add switches
    switch_counter = 1  # Start from 1 for regular keys like Switch_1, Switch_2,...
    for group, devices in group_device_members.items():
        switch_list[f"Switch_{switch_counter}"] = {
            'bandwidth': 1000,
            'forwarding_delay': 0.1,
            'group_device_members': devices,
            'group_server_members': None
        }
        switch_counter += 1

    # Add an independent switch
    switch_list[f"Switch_{switch_counter}"] = {
        'bandwidth': 1000,
        'forwarding_delay': 0.1,
        'group_device_members': None,
        'group_server_members': None
    }

#! 未考慮設備配對問題 Ex.某群組內SR1可能與CNC1一起訂閱某個應用，但又同時與CNC2一起訂閱另一個應用
#! 每個群組無法訂閱同個應用多次
#! 
def generate_grouped_device_app_subscriptions():
    # Local variable to store subscriptions
    grouped_device_app_subscriptions = {}
    subscription_counter = 1  # To enumerate the subscription relationships
    
    # Group devices by their switch_group
    grouped_devices = defaultdict(list)
    for dev_key, dev_val in device_list.items():
        grouped_devices[dev_val['switch_group']].append(dev_key)
    
    # Identify eligible applications for each group
    for group, device_keys in grouped_devices.items():
        device_types_set = set(device_list[dev_key]['type'] for dev_key in device_keys)
        for app_name, app_val in application_list.items():
            target_types_set = set(app_val.get('target_device_types', []))
            
            # Check if this group's devices are eligible for this application
            if target_types_set.issubset(device_types_set):
                
                # With a probability of 0.6, subscribe the devices to the application
                if random() <= 0.6:
                    # Assign a random subscription weight between 0.1 and 1
                    weight = round(uniform(0.1, 1), 2)
                    
                    # Get unique devices for each type
                    subscribed_devices = []
                    available_device_keys = device_keys.copy()
                    for target_type in target_types_set:
                        type_devices = [dev_key for dev_key in available_device_keys if device_list[dev_key]['type'] == target_type]
                        if type_devices:
                            subscribed_device = choice(type_devices)
                            subscribed_devices.append(subscribed_device)
                            available_device_keys.remove(subscribed_device)
                    
                    if subscribed_devices:
                        grouped_device_app_subscriptions[f"Subscription_{subscription_counter}"] = {
                            'Group': group,
                            'Devices': subscribed_devices,
                            'Application': app_name,
                            'Weight': weight
                        }
                        subscription_counter += 1
                    
    return grouped_device_app_subscriptions

if __name__ == "__main__":
    generate_regular_key_devices()
    generate_initial_applications()
    generate_initial_servers()
    generate_initial_switches()
    subscriptions = generate_grouped_device_app_subscriptions()
    
    print()
    print(device_list)
    print()
    print(application_list)
    print()
    print(server_list)
    print()
    print(switch_list)
    print()
    print(subscriptions)
    print()
    