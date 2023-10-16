import random
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt

#! switch_group -> group ，隨機度可以更高一些
device_list = {
    'Dev_1': {'bandwidth': 100, 'type': 'CNC', 'switch_group': 'Group_0'}, 
    'Dev_2': {'bandwidth': 100, 'type': 'RA', 'switch_group': 'Group_0'}, 
    'Dev_3': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_0'}, 
    'Dev_4': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_0'}, 
    'Dev_5': {'bandwidth': 100, 'type': 'CNC', 'switch_group': 'Group_1'}, 
    'Dev_6': {'bandwidth': 100, 'type': 'RA', 'switch_group': 'Group_1'}, 
    'Dev_7': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_1'}, 
    'Dev_8': {'bandwidth': 100, 'type': 'CNC', 'switch_group': 'Group_2'}, 
    'Dev_9': {'bandwidth': 100, 'type': 'RA', 'switch_group': 'Group_2'}, 
    'Dev_10': {'bandwidth': 100, 'type': 'AGV', 'switch_group': 'Group_2'}, 
    'Dev_11': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_2'}, 
    'Dev_12': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_2'}, 
    'Dev_13': {'bandwidth': 100, 'type': 'CNC', 'switch_group': 'Group_3'}, 
    'Dev_14': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_3'}, 
    'Dev_15': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_3'}, 
    'Dev_16': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_3'}, 
    'Dev_17': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_3'}, 
    'Dev_18': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_3'}, 
    'Dev_19': {'bandwidth': 100, 'type': 'CNC', 'switch_group': 'Group_4'}, 
    'Dev_20': {'bandwidth': 100, 'type': 'RA', 'switch_group': 'Group_4'}, 
    'Dev_21': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_4'},
    'Dev_22': {'bandwidth': 100, 'type': 'CNC', 'switch_group': 'Group_5'}, 
    'Dev_23': {'bandwidth': 100, 'type': 'RA', 'switch_group': 'Group_5'}, 
    'Dev_24': {'bandwidth': 100, 'type': 'AGV', 'switch_group': 'Group_5'}, 
    'Dev_25': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_5'}, 
    'Dev_26': {'bandwidth': 100, 'type': 'SR', 'switch_group': 'Group_5'}, 
    'Dev_27': {'bandwidth': 100, 'type': 'CNC', 'switch_group': 'Group_6'}}
application_list = {
    'App_0': {'response_timeout': 1000, 'computing_load': 200, 'bandwidth_load': 300, 'target_device_types': ['RA', 'SR']}, 
    'App_1': {'response_timeout': 100, 'computing_load': 800, 'bandwidth_load': 1800, 'target_device_types': ['AGV']}, 
    'App_2': {'response_timeout': 5, 'computing_load': 200, 'bandwidth_load': 30, 'target_device_types': ['CNC']}, 
    'App_3': {'response_timeout': 20, 'computing_load': 200, 'bandwidth_load': 30, 'target_device_types': ['CNC']}, 
    'App_4': {'response_timeout': 100, 'computing_load': 800, 'bandwidth_load': 300, 'target_device_types': ['CNC', 'SR']}, 
    'App_5': {'response_timeout': 1000, 'computing_load': 800, 'bandwidth_load': 30, 'target_device_types': ['RA']}
    }
#! switch_group -> group，之後可以做多對一的關係
server_list = {
    'Server_1': {'bandwidth': 1000, 'computing_power': 10000, 'switch_group': None, 'running_apps': []}, 
    'Server_2': {'bandwidth': 1000, 'computing_power': 1200, 'switch_group': None, 'running_apps': []}, 
    'Server_3': {'bandwidth': 1000, 'computing_power': 1200, 'switch_group': None, 'running_apps': []}, 
    'Server_4': {'bandwidth': 1000, 'computing_power': 1200, 'switch_group': None, 'running_apps': []}, 
    'Server_5': {'bandwidth': 1000, 'computing_power': 6000, 'switch_group': None, 'running_apps': []}, 
    'Server_6': {'bandwidth': 1000, 'computing_power': 6000, 'switch_group': None, 'running_apps': []}
    }   
#! group_device_members -> devices，group_server_members -> servers
switch_list = {
    'Switch_1': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_1', 'Dev_2', 'Dev_3', 'Dev_4'], 'group_server_members': None}, 
    'Switch_2': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_5', 'Dev_6', 'Dev_7'], 'group_server_members': None}, 
    'Switch_3': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_8', 'Dev_9', 'Dev_10', 'Dev_11', 'Dev_12'], 'group_server_members': None}, 
    'Switch_4': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_13', 'Dev_14', 'Dev_15', 'Dev_16', 'Dev_17', 'Dev_18'], 'group_server_members': None}, 
    'Switch_5': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_19', 'Dev_20', 'Dev_21'], 'group_server_members': None}, 
    'Switch_6': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_22', 'Dev_23', 'Dev_24', 'Dev_25', 'Dev_26'], 'group_server_members': None}, 
    'Switch_7': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_27'], 'group_server_members': None}, 
    'Switch_8': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': None, 'group_server_members': None}
    }
#! cancel 'Group'
subscriptions = {
    'Subscription_1': {'Group': 'Group_0', 'Devices': ['Dev_1'], 'Application': 'App_2', 'Weight': 0.39},
    'Subscription_2': {'Group': 'Group_0', 'Devices': ['Dev_1'], 'Application': 'App_3', 'Weight': 0.56},
    'Subscription_3': {'Group': 'Group_0', 'Devices': ['Dev_4', 'Dev_1'], 'Application': 'App_4', 'Weight': 0.28},
    'Subscription_4': {'Group': 'Group_0', 'Devices': ['Dev_2'], 'Application': 'App_5', 'Weight': 0.78},
    'Subscription_5': {'Group': 'Group_1', 'Devices': ['Dev_6', 'Dev_7'], 'Application': 'App_0', 'Weight': 0.48},
    'Subscription_6': {'Group': 'Group_1', 'Devices': ['Dev_5'], 'Application': 'App_2', 'Weight': 0.91},
    'Subscription_7': {'Group': 'Group_1', 'Devices': ['Dev_5'], 'Application': 'App_3', 'Weight': 0.63},
    'Subscription_8': {'Group': 'Group_1', 'Devices': ['Dev_6'], 'Application': 'App_5', 'Weight': 0.68},
    'Subscription_9': {'Group': 'Group_2', 'Devices': ['Dev_9', 'Dev_12'], 'Application': 'App_0', 'Weight': 0.23},
    'Subscription_10': {'Group': 'Group_3', 'Devices': ['Dev_13'], 'Application': 'App_3', 'Weight': 0.11},
    'Subscription_11': {'Group': 'Group_3', 'Devices': ['Dev_15', 'Dev_13'], 'Application': 'App_4', 'Weight': 0.3},
    'Subscription_12': {'Group': 'Group_4', 'Devices': ['Dev_20', 'Dev_21'], 'Application': 'App_0', 'Weight': 0.79},
    'Subscription_13': {'Group': 'Group_4', 'Devices': ['Dev_19'], 'Application': 'App_2', 'Weight': 0.81},
    'Subscription_14': {'Group': 'Group_4', 'Devices': ['Dev_21', 'Dev_19'], 'Application': 'App_4', 'Weight': 0.14},
    'Subscription_15': {'Group': 'Group_4', 'Devices': ['Dev_20'], 'Application': 'App_5', 'Weight': 0.28},
    'Subscription_16': {'Group': 'Group_5', 'Devices': ['Dev_23', 'Dev_25'], 'Application': 'App_0', 'Weight': 0.17},
    'Subscription_17': {'Group': 'Group_5', 'Devices': ['Dev_24'], 'Application': 'App_1', 'Weight': 0.18},
    'Subscription_18': {'Group': 'Group_5', 'Devices': ['Dev_26', 'Dev_22'], 'Application': 'App_4', 'Weight': 0.49},
    'Subscription_19': {'Group': 'Group_5', 'Devices': ['Dev_23'], 'Application': 'App_5', 'Weight': 0.84}
    }

def assign_servers_to_switch_groups(server_list, switch_list):
    # Sort servers based on computing power in descending order
    sorted_servers = sorted(server_list.keys(), key=lambda x: server_list[x]['computing_power'], reverse=True)
    
    # Assign the server with the highest computing power to the switch group without group device members
    for switch in switch_list:
        if not switch_list[switch]['group_device_members']:
            server_list[sorted_servers[0]]['switch_group'] = switch
            switch_list[switch]['group_server_members'] = sorted_servers[0]
            break

    # Assign the remaining servers to switch groups
    server_index = 1
    for switch in switch_list:
        if not switch_list[switch]['group_server_members']:
            if server_index < len(sorted_servers):
                server_list[sorted_servers[server_index]]['switch_group'] = switch
                switch_list[switch]['group_server_members'] = sorted_servers[server_index]
                server_index += 1

    return server_list, switch_list
"""
# switch_list = {
#     'Switch_1': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_1', 'Dev_2', 'Dev_3', 'Dev_4'], 'group_server_members': 'Server_5'}, 
#     'Switch_2': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_5', 'Dev_6', 'Dev_7'], 'group_server_members': 'Server_6'}, 
#     'Switch_3': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_8', 'Dev_9', 'Dev_10', 'Dev_11', 'Dev_12'], 'group_server_members': 'Server_2'}, 
#     'Switch_4': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_13', 'Dev_14', 'Dev_15', 'Dev_16', 'Dev_17', 'Dev_18'], 'group_server_members': 'Server_3'}, 
#     'Switch_5': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_19', 'Dev_20', 'Dev_21'], 'group_server_members': 'Server_4'}, 
#     'Switch_6': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_22', 'Dev_23', 'Dev_24', 'Dev_25', 'Dev_26'], 'group_server_members': None}, 
#     'Switch_7': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_27'], 'group_server_members': None}, 
#     'Switch_8': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': None, 'group_server_members': 'Server_1'}
#     }
"""

def distribute_apps_to_servers(application_list, server_list):
    for server_data in server_list.values():
        server_data['remain_computing_power'] = server_data.pop('computing_power')
    
    # Part I
    for app_name, app_data in application_list.items():
        while True:
            server_name = random.choice(list(server_list.keys()))
            server_data = server_list[server_name]
            
            if server_data['remain_computing_power'] >= app_data['computing_load']:
                server_data['running_apps'].append(app_name)
                server_data['remain_computing_power'] -= app_data['computing_load']
                break

    # Part II
    for server_name, server_data in server_list.items():
        selection_prob = 0.8
        
        while selection_prob > 0:
            # Refreshing 'available_apps'
            available_apps = [app for app, app_data in application_list.items() if app not in server_data['running_apps'] and app_data['computing_load'] <= server_data['remain_computing_power']]
            
            if not available_apps:
                break
                
            selected_app = random.choice(available_apps)
            if random.random() < selection_prob:
                server_data['running_apps'].append(selected_app)
                server_data['remain_computing_power'] -= application_list[selected_app]['computing_load']
            
            # No need to remove the app from 'available_apps' as it is refreshed in each iteration
            selection_prob -= 0.1
    
    return server_list

"""
# server_list = {
#     'Server_1': {'bandwidth': 1000, 'switch_group': 'Switch_8', 'running_apps': ['App_3', 'App_5', 'App_4'], 'remain_computing_power': 8200}, 
#     'Server_2': {'bandwidth': 1000, 'switch_group': 'Switch_3', 'running_apps': ['App_0', 'App_5', 'App_3'], 'remain_computing_power': 0}, 
#     'Server_3': {'bandwidth': 1000, 'switch_group': 'Switch_4', 'running_apps': ['App_1', 'App_0', 'App_2'], 'remain_computing_power': 0}, 
#     'Server_4': {'bandwidth': 1000, 'switch_group': 'Switch_5', 'running_apps': ['App_2', 'App_4', 'App_3'], 'remain_computing_power': 0}, 
#     'Server_5': {'bandwidth': 1000, 'switch_group': 'Switch_1', 'running_apps': ['App_2'], 'remain_computing_power': 5800}, 
#     'Server_6': {'bandwidth': 1000, 'switch_group': 'Switch_2', 'running_apps': ['App_4', 'App_2', 'App_3'], 'remain_computing_power': 4800}}
"""

def generate_and_draw_topology(switch_list):
    # Initialize variables
    tree_topology = nx.Graph()
    remaining_switches = list(switch_list.keys())
    edge_nodes = []

    # Step 2: Select Root Node
    root_node = random.choice(remaining_switches)
    tree_topology.add_node(root_node)
    remaining_switches.remove(root_node)

    # Add root node to edge_nodes list
    edge_nodes.append(root_node)

    # Step 3-7: Loop until all switches are added to the tree
    while remaining_switches:
        # Step 4: Randomly pick an edge node
        parent_node = random.choice(edge_nodes)
        
        # Step 5: Randomly select one or several switches to add to the parent node
        num_children = random.randint(1, len(remaining_switches))
        children_nodes = random.sample(remaining_switches, num_children)
        
        # Step 6: Add children to the tree and update edge_nodes and remaining_switches
        for child in children_nodes:
            tree_topology.add_edge(parent_node, child)
            edge_nodes.append(child)
            remaining_switches.remove(child)

    # Step 8: Visualize the tree
    pos = nx.spring_layout(tree_topology, seed=42)  # positions for all nodes
    nx.draw(tree_topology, pos, with_labels=True, font_weight='bold')
    plt.title("Tree Topology of Switches")
    plt.show()
    
    return list(tree_topology.edges())

"""
# switch_list = {
#     'Switch_1': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_1', 'Dev_2', 'Dev_3', 'Dev_4'], 'group_server_members': 'Server_5'}, 
#     'Switch_2': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_5', 'Dev_6', 'Dev_7'], 'group_server_members': 'Server_6'}, 
#     'Switch_3': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_8', 'Dev_9', 'Dev_10', 'Dev_11', 'Dev_12'], 'group_server_members': 'Server_2'}, 
#     'Switch_4': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_13', 'Dev_14', 'Dev_15', 'Dev_16', 'Dev_17', 'Dev_18'], 'group_server_members': 'Server_3'}, 
#     'Switch_5': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_19', 'Dev_20', 'Dev_21'], 'group_server_members': 'Server_4'}, 
#     'Switch_6': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_22', 'Dev_23', 'Dev_24', 'Dev_25', 'Dev_26'], 'group_server_members': None}, 
#     'Switch_7': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': ['Dev_27'], 'group_server_members': None}, 
#     'Switch_8': {'bandwidth': 1000, 'forwarding_delay': 0.1, 'group_device_members': None, 'group_server_members': 'Server_1'}
#     }
"""

def find_shortest_paths(tree_topology, subscriptions, server_list, switch_list):
    """
    Finds the shortest path for each subscription in a network topology.
    
    Parameters:
        tree_topology (list of tuples): Network topology as list of edges.
        subscriptions (dict): Subscription details including devices and applications.
        server_list (dict): Server details including running applications.
        switch_list (dict): Switch details including connected devices.
        
    Returns:
        dict: Shortest path for each subscription.
    """
    
    # Build the Network Graph with Bandwidth
    G = nx.Graph()
    for edge in tree_topology:
        switch_1, switch_2 = edge
        bandwidth = min(switch_list[switch_1]['bandwidth'], switch_list[switch_2]['bandwidth'])
        G.add_edge(switch_1, switch_2, bandwidth=bandwidth)

    # Locate Devices and Servers
    def locate_entities(subscription):
        application = subscription['Application']
        devices = subscription['Devices']
        server_switches = set()
        for server, details in server_list.items():
            if application in details['running_apps']:
                server_switches.add(details['switch_group'])
        device_switches = set()
        for switch, details in switch_list.items():
            if details['group_device_members'] is None:
                continue
            if any(device in details['group_device_members'] for device in devices):
                device_switches.add(switch)
        return device_switches, server_switches

    # Find Shortest Path considering Bandwidth
    def find_shortest_path(device_switches, server_switches, weight):
        shortest_paths = {}
        for device_switch in device_switches:
            min_path = None
            min_length = float('inf')
            for server_switch in server_switches:
                try:
                    path = nx.shortest_path(G, source=device_switch, target=server_switch, weight='bandwidth')
                except nx.NetworkXNoPath:
                    continue
                path_has_enough_bandwidth = all(
                    G[u][v]['bandwidth'] >= weight for u, v in zip(path[:-1], path[1:])
                )
                if path_has_enough_bandwidth and len(path) < min_length:
                    min_length = len(path)
                    min_path = path
            shortest_paths[device_switch] = min_path
        return shortest_paths

    # Main logic
    result = {}
    for sub_name, sub_details in subscriptions.items():
        device_switches, server_switches = locate_entities(sub_details)
        weight = sub_details['Weight']
        if server_switches:  # Only proceed if a server_switch is found
            shortest_paths = find_shortest_path(device_switches, server_switches, weight)
            result[sub_name] = shortest_paths

    return result

def calculate_edge_priority(tree_topology, subscriptions, server_list, switch_list):
    """
    Calculates the priority (weight) of each edge in the network graph based on subscriptions.
    
    Parameters:
        tree_topology (list of tuples): Network topology as list of edges.
        subscriptions (dict): Subscription details including devices and applications.
        server_list (dict): Server details including running applications.
        switch_list (dict): Switch details including connected devices.
        
    Returns:
        dict: Priority (weight) for each edge.
    """
    # Initialize Edge Weights
    edge_weights = defaultdict(float)
    
    # Calculate Edge Weights
    result = find_shortest_paths(tree_topology, subscriptions, server_list, switch_list)
    for sub_name, sub_details in result.items():
        for path in sub_details.values():
            if path is None or len(path) < 2:
                continue
            sub_weight = subscriptions[sub_name]['Weight']
            for u, v in zip(path[:-1], path[1:]):
                edge_weights[(u, v)] += sub_weight
                edge_weights[(v, u)] += sub_weight  # The graph is undirected

    # Normalize Edge Weights
    for edge, weight in edge_weights.items():
        edge_weights[edge] = weight / 2

    return dict(edge_weights)


def calculate_edge_bandwidth(tree_topology, subscriptions, server_list, switch_list, application_list):
    """
    Calculates the bandwidth consumption of each edge in the network graph based on subscriptions and application details.
    
    Parameters:
        tree_topology (list of tuples): Network topology as list of edges.
        subscriptions (dict): Subscription details including devices and applications.
        server_list (dict): Server details including running applications.
        switch_list (dict): Switch details including connected devices.
        application_list (dict): Application details including bandwidth_load.
        
    Returns:
        dict: Bandwidth consumption for each edge.
    """
    # Initialize Edge Bandwidth Consumption
    edge_bandwidth_consumption = defaultdict(float)
    
    # Calculate Edge Bandwidth Consumption
    result = find_shortest_paths(tree_topology, subscriptions, server_list, switch_list)
    for sub_name, sub_details in result.items():
        for path in sub_details.values():
            if path is None or len(path) < 2:
                continue
            app_name = subscriptions[sub_name]['Application']
            app_bandwidth_load = application_list[app_name]['bandwidth_load']
            for u, v in zip(path[:-1], path[1:]):
                edge_bandwidth_consumption[(u, v)] += app_bandwidth_load
                edge_bandwidth_consumption[(v, u)] += app_bandwidth_load  # The graph is undirected
    
    # Normalize Bandwidth Consumption
    for edge, bandwidth in edge_bandwidth_consumption.items():
        edge_bandwidth_consumption[edge] = bandwidth / 2

    return dict(edge_bandwidth_consumption)

if __name__ == '__main__':
    server_list, switch_list = assign_servers_to_switch_groups(server_list, switch_list)
    print(switch_list)
    print()
    server_list = distribute_apps_to_servers(application_list, server_list)
    print(server_list)
    print()
    tree_topology = generate_and_draw_topology(switch_list)
    shortest_paths = find_shortest_paths(tree_topology, subscriptions, server_list, switch_list)
    print(shortest_paths)
    print()
    edge_priorities = calculate_edge_priority(tree_topology, subscriptions, server_list, switch_list)
    print(edge_priorities)
    print()
    edge_bandwidths = calculate_edge_bandwidth(tree_topology, subscriptions, server_list, switch_list, application_list)
    print(edge_bandwidths)
    print()