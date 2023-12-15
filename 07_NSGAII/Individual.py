import csv
import os
import json
import random
import networkx as nx
import matplotlib.pyplot as plt

def assign_computer_group(computer_dict, group_num):
    highest_cpu_server = max(computer_dict, key=lambda k: computer_dict[k]["cpu"])
    computer_dict[highest_cpu_server]["group"] = 0

    remaining_servers = [
        server for server in computer_dict if server != highest_cpu_server
    ]
    for server in remaining_servers:
        assigned_group = random.randint(1, group_num - 1)
        computer_dict[server]["group"] = assigned_group

    return computer_dict

def assign_apps_to_computer(computer_dict, application_dict):
    app_keys = list(application_dict.keys())
    computer_keys = list(computer_dict.keys())
    for comp in computer_dict:
        computer_dict[comp]["running_apps"] = []

    # 首輪分發
    for app in app_keys:
        assigned_computer = random.choice(computer_keys)
        computer_dict[assigned_computer]["running_apps"].append(app)

    # 二輪分發
    for app in app_keys:
        valid_computers = [
            comp
            for comp in computer_dict
            if app not in computer_dict[comp]["running_apps"]
        ]
        random.shuffle(valid_computers)
        num_additional_computers = random.randint(0, len(valid_computers) - 1)

        for assigned_computer in valid_computers[:num_additional_computers]:
            computer_dict[assigned_computer]["running_apps"].append(app)

    # 整理 running apps 的順序，因為會影響後續命名規則
    def extract_number(app_name):
        return int("".join(filter(str.isdigit, app_name)))

    for computer_keys in computer_dict:
        computer_dict[computer_keys]["running_apps"].sort(key=extract_number)

    return computer_dict

def generate_topology(switch_dict):
    switches = list(switch_dict.keys())
    G = nx.DiGraph()

    root = random.choice(switches)
    G.add_node(root)
    remaining_switches = set(switches)
    remaining_switches.remove(root)

    while remaining_switches:
        child = remaining_switches.pop()
        parent = random.choice(list(G.nodes))
        G.add_edge(parent, child)

    return G

def add_nodes_to_topology(G, dict):
    for label, properties in dict.items():
        G.add_node(label)
        group = properties["group"]
        switch_to_connect = f"sw{group}"
        G.add_edge(switch_to_connect, label)

    return G

def add_app_nodes_to_topology(G, application_dict, computer_dict):
    for computer, properties in computer_dict.items():
        for app in properties["running_apps"]:
            if app in application_dict:
                app_instance = f"{app}_{computer}"
                G.add_node(app_instance)
                G.add_edge(computer, app_instance)
        
    return G

def shortest_path(G, subscription_dict):
    app_nodes = {node for node in G.nodes if node.startswith("app")}
    for sub, properties in subscription_dict.items():
        device = properties["devices"][0]
        target_apps = {node for node in app_nodes if re.search(r'app' + properties["app"][-1], node)}
        shortest_path = min(
            (nx.shortest_path(G, source=device, target=app) for app in target_apps),
            key=len,
            default=None
        )
        if shortest_path:
            properties["app"] = shortest_path[-1]
            properties["path"] = shortest_path
        else:
            _logger.info(f"No path found for subscription {sub}")
    return subscription_dict

def generate_individual(application_dict, computer_dict, device_dict, switch_dict):

    # 生成拓樸
    updated_computer_dict = assign_computer_group(computer_dict, len(switch_dict))
    
    updated_computer_dict = assign_apps_to_computer(updated_computer_dict, application_dict)
    

    switch_to_topo = generate_topology(switch_dict)
    device_to_topo = add_nodes_to_topology(switch_to_topo, device_dict)
    computer_to_topo = add_nodes_to_topology(device_to_topo, updated_computer_dict)
    network_graph = add_app_nodes_to_topology(computer_to_topo, application_dict, updated_computer_dict)
    
    # 拓樸串列化
    keys = list(switch_dict) + list(device_dict) + list(updated_computer_dict)
    individual = []
    
    for key in keys:
        individual.append(list(network_graph.predecessors(key))[0]) if len(list(network_graph.predecessors(key))) == 1 else individual.append(None)
    
    for key in list(updated_computer_dict):
        individual.append(updated_computer_dict[key]["running_apps"])
    
    return individual