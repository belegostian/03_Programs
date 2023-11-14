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

subscription_dict = {
    # Job Scheduling <- everyone
    "sub1": {"devices": ["dev1"], "app": "app1", "weight": 0.2},
    "sub2": {"devices": ["dev2"], "app": "app1", "weight": 0.2},
    "sub3": {"devices": ["dev3"], "app": "app1", "weight": 0.2},
    "sub4": {"devices": ["dev4"], "app": "app1", "weight": 0.2},
    "sub5": {"devices": ["dev5"], "app": "app1", "weight": 0.4},
    "sub6": {"devices": ["dev6"], "app": "app1", "weight": 0.4},
    "sub7": {"devices": ["dev7"], "app": "app1", "weight": 0.2},
    "sub8": {"devices": ["dev8"], "app": "app1", "weight": 0.2},
    "sub9": {"devices": ["dev9"], "app": "app1", "weight": 0.2},
    "sub10": {"devices": ["dev10"], "app": "app1", "weight": 0.2},
    "sub11": {"devices": ["dev11"], "app": "app1", "weight": 0.4},
    "sub12": {"devices": ["dev12"], "app": "app1", "weight": 0.4},
    "sub13": {"devices": ["dev13"], "app": "app1", "weight": 0.2},
    "sub14": {"devices": ["dev14"], "app": "app1", "weight": 0.2},
    "sub15": {"devices": ["dev15"], "app": "app1", "weight": 0.2},
    "sub16": {"devices": ["dev16"], "app": "app1", "weight": 0.2},
    "sub17": {"devices": ["dev17"], "app": "app1", "weight": 0.4},
    "sub18": {"devices": ["dev18"], "app": "app1", "weight": 0.4},
    "sub19": {"devices": ["dev19"], "app": "app1", "weight": 0.4},
    "sub20": {"devices": ["dev20"], "app": "app1", "weight": 0.4},
    # automatic workpiece changing <- group2
    "sub21": {"devices": ["dev7"], "app": "app2", "weight": 0.3},
    "sub22": {"devices": ["dev8"], "app": "app2", "weight": 0.3},
    "sub23": {"devices": ["dev9"], "app": "app2", "weight": 0.3},
    "sub24": {"devices": ["dev10"], "app": "app2", "weight": 0.3},
    "sub25": {"devices": ["dev11"], "app": "app2", "weight": 0.5},
    "sub26": {"devices": ["dev12"], "app": "app2", "weight": 0.5},
    # Tool Wear Detection <- all high-level CNC
    "sub27": {"devices": ["dev5"], "app": "app3", "weight": 0.8},
    "sub28": {"devices": ["dev6"], "app": "app3", "weight": 0.8},
    "sub29": {"devices": ["dev11"], "app": "app3", "weight": 0.8},
    "sub30": {"devices": ["dev12"], "app": "app3", "weight": 0.8},
    "sub31": {"devices": ["dev17"], "app": "app3", "weight": 0.8},
    "sub32": {"devices": ["dev18"], "app": "app3", "weight": 0.8},
    "sub33": {"devices": ["dev19"], "app": "app3", "weight": 0.8},
    "sub34": {"devices": ["dev20"], "app": "app3", "weight": 0.8},
    # Predictive Maintenance <- group3 + high-level CNC
    "sub35": {"devices": ["dev13"], "app": "app4", "weight": 0.9},
    "sub36": {"devices": ["dev14"], "app": "app4", "weight": 0.9},
}

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
    subscription_dict = {
        # Job Scheduling <- everyone
        "sub1": {"devices": ["dev1"], "app": "app1", "weight": 0.2},
        "sub2": {"devices": ["dev2"], "app": "app1", "weight": 0.2},
        "sub3": {"devices": ["dev3"], "app": "app1", "weight": 0.2},
        "sub4": {"devices": ["dev4"], "app": "app1", "weight": 0.2},
        "sub5": {"devices": ["dev5"], "app": "app1", "weight": 0.4},
        "sub6": {"devices": ["dev6"], "app": "app1", "weight": 0.4},
        "sub7": {"devices": ["dev7"], "app": "app1", "weight": 0.2},
        "sub8": {"devices": ["dev8"], "app": "app1", "weight": 0.2},
        "sub9": {"devices": ["dev9"], "app": "app1", "weight": 0.2},
        "sub10": {"devices": ["dev10"], "app": "app1", "weight": 0.2},
        "sub11": {"devices": ["dev11"], "app": "app1", "weight": 0.4},
        "sub12": {"devices": ["dev12"], "app": "app1", "weight": 0.4},
        "sub13": {"devices": ["dev13"], "app": "app1", "weight": 0.2},
        "sub14": {"devices": ["dev14"], "app": "app1", "weight": 0.2},
        "sub15": {"devices": ["dev15"], "app": "app1", "weight": 0.2},
        "sub16": {"devices": ["dev16"], "app": "app1", "weight": 0.2},
        "sub17": {"devices": ["dev17"], "app": "app1", "weight": 0.4},
        "sub18": {"devices": ["dev18"], "app": "app1", "weight": 0.4},
        "sub19": {"devices": ["dev19"], "app": "app1", "weight": 0.4},
        "sub20": {"devices": ["dev20"], "app": "app1", "weight": 0.4},
        # automatic workpiece changing <- group2
        "sub21": {"devices": ["dev7"], "app": "app2", "weight": 0.3},
        "sub22": {"devices": ["dev8"], "app": "app2", "weight": 0.3},
        "sub23": {"devices": ["dev9"], "app": "app2", "weight": 0.3},
        "sub24": {"devices": ["dev10"], "app": "app2", "weight": 0.3},
        "sub25": {"devices": ["dev11"], "app": "app2", "weight": 0.5},
        "sub26": {"devices": ["dev12"], "app": "app2", "weight": 0.5},
        # Tool Wear Detection <- all high-level CNC
        "sub27": {"devices": ["dev5"], "app": "app3", "weight": 0.8},
        "sub28": {"devices": ["dev6"], "app": "app3", "weight": 0.8},
        "sub29": {"devices": ["dev11"], "app": "app3", "weight": 0.8},
        "sub30": {"devices": ["dev12"], "app": "app3", "weight": 0.8},
        "sub31": {"devices": ["dev17"], "app": "app3", "weight": 0.8},
        "sub32": {"devices": ["dev18"], "app": "app3", "weight": 0.8},
        "sub33": {"devices": ["dev19"], "app": "app3", "weight": 0.8},
        "sub34": {"devices": ["dev20"], "app": "app3", "weight": 0.8},
        # Predictive Maintenance <- group3 + high-level CNC
        "sub35": {"devices": ["dev13"], "app": "app4", "weight": 0.9},
        "sub36": {"devices": ["dev14"], "app": "app4", "weight": 0.9},
    }

    file_name = 'experiment_0/scenario_0/scenario_0.csv'
    
    graph = create_graph_from_csv(file_name)
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
    
    
if __name__ == "__main__":
    main()