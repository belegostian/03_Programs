import csv
import logging
import os
import re
from collections import defaultdict
import networkx as nx

_logger = logging.getLogger(__name__)

# 第一章，輔助型函式
def create_graph_from_csv(file_name):
    G = nx.Graph()

    with open(file_name, 'r') as file:
        reader = csv.reader(file)
        nodes_section = True
        for row in reader:
            if not row:
                nodes_section = False
                continue

            if nodes_section:
                if row[0] != 'Nodes':
                    G.add_node(row[0])
            else:
                if row[0] != 'Edges':
                    G.add_edge(row[0], row[1])

    return G

# 第二章，最短路徑分析函式
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

def load_subscriptions(file_name):
    subscription_dict = {}
    with open(file_name, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            sub = row['subscription']
            if sub not in subscription_dict:
                subscription_dict[sub] = {"devices": [], "app": row['app'], "weight": float(row['weight'])}
            subscription_dict[sub]['devices'].append(row['device'])
    return subscription_dict

def write_subscription_paths(subscription_dict, file_name):
    rows = []
    for sub, attrs in subscription_dict.items():
        path_str = ','.join(attrs['path'])
        for device in attrs['devices']:
            rows.append({
                "subscription": sub, 
                "device": device, 
                "app": attrs['app'], 
                "weight": attrs['weight'], 
                "path": path_str
            })
    with open(file_name, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=["subscription", "device", "app", "weight", "path"])
        writer.writeheader()
        writer.writerows(rows)

# 第三章，主程式
def main():
    base_folder = 'experiment_0'
    subscription_file = os.path.join(base_folder, 'subscriptions.csv')
    scenario_folders = [d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d)) and d.startswith('scenario')]
    
    for scenario in scenario_folders:
        graph_file = os.path.join(base_folder, scenario, f'{scenario}.csv')
        output_file = os.path.join(base_folder, scenario, 'subscription_paths.csv')
        
        if os.path.exists(graph_file):
            graph = create_graph_from_csv(graph_file)
            subscription_dict = load_subscriptions(subscription_file)
            updated_subscriptions = shortest_path(graph, subscription_dict)
            write_subscription_paths(updated_subscriptions, output_file)
            
            _logger.info(f"{scenario} completed")
        else:
            _logger.warning(f"Graph file not found for scenario {scenario}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()