import random
import csv
import logging
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt

_logger = logging.getLogger(__name__)

def create_graph_from_csv(file_name):
    # Initialize an empty graph
    G = nx.Graph()

    # Read the CSV file
    with open(file_name, 'r') as file:
        reader = csv.reader(file)
        nodes_section = True  # Start with nodes section
        for row in reader:
            if not row:  # Empty row indicates switch from nodes to edges
                nodes_section = False
                continue

            if nodes_section:
                if row[0] != 'Nodes':  # Ignore header
                    G.add_node(row[0])
            else:
                if row[0] != 'Edges':  # Ignore header
                    G.add_edge(row[0], row[1])

    return G

def shortest_path(G, subscription_dict):
    for sub, properties in subscription_dict.items():
        device = properties["devices"][0]
        app = properties["app"]

        possible_apps = [
            node for node in G.nodes if node.startswith(f"app{app[-1]}")
        ]
        shortest_path = None
        for possible_app in possible_apps:
            try:
                path = nx.shortest_path(G, source=device, target=possible_app)
                if shortest_path is None or len(path) < len(shortest_path):
                    shortest_path = path
            except nx.NetworkXNoPath:
                _logger.info(f"No path from {device} to {possible_app}")
                continue

            if shortest_path:
                app_on_comp = shortest_path[-1]
                properties["app"] = app_on_comp
                properties["path"] = shortest_path

    return subscription_dict

def main():
    subscription_dict = {}
    with open('experiment_0\subscriptions.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            sub = row['subscription']
            if sub not in subscription_dict:
                subscription_dict[sub] = {"devices": [], "app": row['app'], "weight": float(row['weight'])}
            subscription_dict[sub]['devices'].append(row['device'])

    graph_structure_csv = 'experiment_0\scenario_0\scenario_0.csv'
    
    graph = create_graph_from_csv(graph_structure_csv)
    # print("Nodes:", graph.nodes())
    # print("Edges:", graph.edges())
    
    subscription_dict = shortest_path(graph, subscription_dict)
    # print(subscription_dict)
    # subscription_dict = {
    #     "sub1": { "devices": ["dev1"], "app": "app1_comp3", "weight": 0.2, "path": ["dev1", "sw1", "sw2", "comp3", "app1_comp3"]},
    #     "sub2": { "devices": ["dev2"], "app": "app1_comp3", "weight": 0.2, "path": ["dev2", "sw1", "sw2", "comp3", "app1_comp3"]},
    #     ...
    #     "sub36": { "devices": ["dev14"], "app": "app4_comp1", "weight": 0.9, "path": ["dev14", "sw3", "sw2", "comp1", "app4_comp1"]}
    # }
    
    rows = []
    for sub, attrs in subscription_dict.items():
        path_str = ','.join(attrs['path'])
        for device in attrs['devices']:
            row = {
                "subscription": sub, 
                "device": device, 
                "app": attrs['app'], 
                "weight": attrs['weight'], 
                "path": path_str
            }
            rows.append(row)

    csv_file = 'experiment_0\scenario_0\subscription_paths.csv'

    # Write the rows to a CSV file
    with open(csv_file, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["subscription", "device", "app", "weight", "path"])
        writer.writeheader()
        writer.writerows(rows)
    
    
if __name__ == "__main__":
    main()