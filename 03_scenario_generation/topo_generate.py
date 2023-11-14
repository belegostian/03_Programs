import os
import csv
import random
import logging
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt

def assign_computer_group(computer_dict, group_num):
    # 機房
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

    return computer_dict

# print(computer_dict)
# computer_dict = {
#     'comp1': {'cpu': 0.8, 'memory': False, 'bandwidth': 1000, 'group': 2, 'running_apps': ['app1', 'app2']},
#     'comp2': {'cpu': 1, 'memory': False, 'bandwidth': 1000, 'group': 0, 'running_apps': ['app1', 'app3', 'app2', 'app4']},
#     'comp3': {'cpu': 0.4, 'memory': False, 'bandwidth': 1000, 'group': 1, 'running_apps': ['app3', 'app4']},
#     'comp4': {'cpu': 0.4, 'memory': False, 'bandwidth': 1000, 'group': 2, 'running_apps': ['app2', 'app4']}
#     }

def generate_topology(G, switch_dict, plot=False):
    switches = list(switch_dict.keys())

    root = random.choice(switches)
    G.add_node(root)
    remaining_switches = set(switches)
    remaining_switches.remove(root)

    while remaining_switches:
        child = remaining_switches.pop()
        parent = random.choice(list(G.nodes))
        G.add_edge(parent, child)

    if plot:
        nx.draw(G, with_labels=True, node_color="lightblue", node_size=2000)
        plt.title("Random Tree Topology of Switches")
        plt.show()

    return G

def add_nodes_to_topology(G, dict, plot=False):
    for label, properties in dict.items():
        G.add_node(label)
        group = properties["group"]

        switch_to_connect = f"sw{group}"

        if switch_to_connect in G.nodes:
            G.add_edge(label, switch_to_connect)
        else:
            print(
                f"Warning: {switch_to_connect} does not exist. Node {label} not connected."
            )

    if plot:
        nx.draw(G, with_labels=True, node_color="lightblue", node_size=2000)
        plt.title("Updated Network Topology")
        plt.show()

    return G

def add_app_nodes_to_topology(G, application_dict, computer_dict, plot=False, iteration=0):
    for computer, properties in computer_dict.items():
        for app in properties["running_apps"]:
            if app in application_dict:
                app_instance = f"{app}_{computer}"
                G.add_node(app_instance)
                G.add_edge(app_instance, computer)

    label_dict = {
        node: node.split("_")[0] if "app" in node else node for node in G.nodes()
    }
    node_categories = {}
    for node in G.nodes:
        if node.startswith("comp"):
            node_categories[node] = "comp"
        elif node.startswith("dev"):
            node_categories[node] = "dev"
        elif node.startswith("sw"):
            node_categories[node] = "sw"
        else:
            node_categories[node] = "app"
    color_map = {"comp": "lightblue", "dev": "teal", "sw": "cyan", "app": "turquoise"}
    node_colors = [color_map[node_categories.get(node, "default")] for node in G.nodes]

    if plot:        
        # pos = nx.spring_layout(G, k=0.5, iterations=25)
        plt.figure(figsize=(18, 12))
        nx.draw(
            G,
            # pos,
            labels=label_dict,
            with_labels=True,
            node_size=2000,
            node_color=node_colors,
            font_size=15
        )
        plt.title("Updated Network Topology with Applications")
        # plt.show()
        plt.savefig(f"scenario 1/scenario_{iteration}.png", format='PNG', dpi=300)

    return G

# print(app_to_topo.nodes)
# ['sw1', 'sw0', 'sw3', 'sw2', 'dev1', 'dev2', 'dev3', 'dev4', 'dev5', 'dev6', 'dev7', 'dev8', 'dev9', 'dev10', 'dev11', 'dev12', 'dev13', 'dev14', 'dev15', 'dev16', 'dev17', 'dev18', 'dev19', 'dev20', 'comp1', 'comp2',
# 'comp3', 'comp4', 'app1_comp1', 'app2_comp1', 'app1_comp2', 'app3_comp2', 'app2_comp2', 'app4_comp2', 'app3_comp3', 'app4_comp3', 'app2_comp4', 'app4_comp4']

# print(app_to_topo.edges)
# [('sw1', 'sw0'), ('sw1', 'sw3'), ('sw1', 'sw2'), ('sw1', 'dev1'), ('sw1', 'dev2'), ('sw1', 'dev3'), ('sw1', 'dev4'), ('sw1', 'dev5'), ('sw1', 'dev6'), ('sw1', 'comp3'), ('sw0', 'comp2'), ('sw3', 'dev13'), ('sw3', 'dev14'), ('sw3', 'dev15'), ('sw3', 'dev16'), ('sw3', 'dev17'), ('sw3', 'dev18'), ('sw3', 'dev19'), ('sw3', 'dev20'), ('sw2', 'dev7'), ('sw2', 'dev8'), ('sw2', 'dev9'), ('sw2', 'dev10'), ('sw2', 'dev11'), ('sw2', 'dev12'),
# ('sw2', 'comp1'), ('sw2', 'comp4'), ('comp1', 'app1_comp1'), ('comp1', 'app2_comp1'), ('comp2', 'app1_comp2'), ('comp2', 'app3_comp2'), ('comp2', 'app2_comp2'), ('comp2', 'app4_comp2'), ('comp3', 'app3_comp3'), ('comp3', 'app4_comp3'), ('comp4', 'app2_comp4'), ('comp4', 'app4_comp4')]

def create_directory(directory_name):
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)

def write_to_csv(file_name, nodes, edges):
    with open(file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Nodes'])
        writer.writerows([[node] for node in nodes])
        writer.writerow([])
        writer.writerow(['Edges'])
        writer.writerows(edges)

def main(G, iteration):
    device_dict = {
        "dev1": {"type": "CNC", "bandwidth": 100, "group": 1},
        "dev2": {"type": "CNC", "bandwidth": 100, "group": 1},
        "dev3": {"type": "CNC", "bandwidth": 100, "group": 1},
        "dev4": {"type": "CNC", "bandwidth": 100, "group": 1},
        "dev5": {"type": "CNC", "bandwidth": 1000, "group": 1},
        "dev6": {"type": "CNC", "bandwidth": 1000, "group": 1},
        "dev7": {"type": "CNC", "bandwidth": 100, "group": 2},
        "dev8": {"type": "CNC", "bandwidth": 100, "group": 2},
        "dev9": {"type": "CNC", "bandwidth": 100, "group": 2},
        "dev10": {"type": "CNC", "bandwidth": 100, "group": 2},
        "dev11": {"type": "CNC", "bandwidth": 1000, "group": 2},
        "dev12": {"type": "CNC", "bandwidth": 1000, "group": 2},
        "dev13": {"type": "CNC", "bandwidth": 100, "group": 3},
        "dev14": {"type": "CNC", "bandwidth": 100, "group": 3},
        "dev15": {"type": "CNC", "bandwidth": 100, "group": 3},
        "dev16": {"type": "CNC", "bandwidth": 100, "group": 3},
        "dev17": {"type": "CNC", "bandwidth": 1000, "group": 3},
        "dev18": {"type": "CNC", "bandwidth": 1000, "group": 3},
        "dev19": {"type": "CNC", "bandwidth": 1000, "group": 3},
        "dev20": {"type": "CNC", "bandwidth": 1000, "group": 3},
    }
    application_dict = {
        "app1": {
            "name": "Job Scheduling",
            "response_timeout": False,
            "cpu_usage": False,
            "memory_usage": False,
            "packet_sending": False,
            "packet_receiving": "app1",
            "target_device": ["CNC"],
        },
        "app2": {
            "name": "automatic workpiece changing",
            "response_timeout": False,
            "cpu_usage": False,
            "memory_usage": False,
            "packet_sending": False,
            "packet_receiving": "app2",
            "target_device": ["CNC"],
        },
        "app3": {
            "name": "Tool Wear Detection",
            "response_timeout": False,
            "cpu_usage": False,
            "memory_usage": False,
            "packet_sending": False,
            "packet_receiving": "app3",
            "target_device": ["CNC"],
        },
        "app4": {
            "name": "Predictive Maintenance",
            "response_timeout": False,
            "cpu_usage": False,
            "memory_usage": False,
            "packet_sending": False,
            "packet_receiving": "app4",
            "target_device": ["CNC"],
        },
    }
    computer_dict = {
        "comp1": {
            "cpu": 0.8,
            "memory": False,
            "bandwidth": 1000,
            "group": None,
            "running_apps": [],
        },
        "comp2": {
            "cpu": 1,
            "memory": False,
            "bandwidth": 1000,
            "group": None,
            "running_apps": [],
        },
        "comp3": {
            "cpu": 0.4,
            "memory": False,
            "bandwidth": 1000,
            "group": None,
            "running_apps": [],
        },
        "comp4": {
            "cpu": 0.4,
            "memory": False,
            "bandwidth": 1000,
            "group": None,
            "running_apps": [],
        },
    }
    switch_dict = {
        "sw0": {"bandwidth": 1000, "forward_delay": False},
        "sw1": {"bandwidth": 1000, "forward_delay": False},
        "sw2": {"bandwidth": 1000, "forward_delay": False},
        "sw3": {"bandwidth": 1000, "forward_delay": False},
    }
    
    computer_dict = assign_computer_group(computer_dict, len(switch_dict))
    computer_dict = assign_apps_to_computer(computer_dict, application_dict)
    
    switch_to_topo = generate_topology(G, switch_dict)
    device_to_topo = add_nodes_to_topology(switch_to_topo, device_dict)
    computer_to_topo = add_nodes_to_topology(device_to_topo, computer_dict)
    # app_to_topo = add_app_nodes_to_topology(computer_to_topo, application_dict, computer_dict, plot=True)
    app_to_topo = add_app_nodes_to_topology(computer_to_topo, application_dict, computer_dict, plot=True, iteration=iteration)
    
    csv_filename = f'scenario 1/scenario_{iteration}.csv'
    write_to_csv(csv_filename, app_to_topo.nodes, app_to_topo.edges)

if __name__ == "__main__":
    n = 5
    G = nx.Graph()
    create_directory('scenario 1')
    
    for i in range(n):
        G.clear()
        main(G, i)
    pause = input("Press any key to exit...")