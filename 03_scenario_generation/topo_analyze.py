import random
import logging
from collections import defaultdict
import networkx as nx
import matplotlib.pyplot as plt

G = nx.Graph()
G.add_nodes_from(['sw1', 'sw0', 'sw3', 'sw2', 'dev1', 'dev2', 'dev3', 'dev4', 'dev5', 'dev6', 'dev7', 'dev8', 'dev9', 'dev10', 'dev11', 'dev12', 'dev13', 'dev14', 'dev15', 'dev16', 'dev17', 'dev18', 'dev19', 'dev20', 'comp1', 'comp2',
'comp3', 'comp4', 'app1_comp1', 'app2_comp1', 'app1_comp2', 'app3_comp2', 'app2_comp2', 'app4_comp2', 'app3_comp3', 'app4_comp3', 'app2_comp4', 'app4_comp4'])
G.add_edges_from([('sw1', 'sw0'), ('sw1', 'sw3'), ('sw1', 'sw2'), ('sw1', 'dev1'), ('sw1', 'dev2'), ('sw1', 'dev3'), ('sw1', 'dev4'), ('sw1', 'dev5'), ('sw1', 'dev6'), ('sw1', 'comp3'), ('sw0', 'comp2'), ('sw3', 'dev13'), ('sw3', 'dev14'), ('sw3', 'dev15'), ('sw3', 'dev16'), ('sw3', 'dev17'), ('sw3', 'dev18'), ('sw3', 'dev19'), ('sw3', 'dev20'), ('sw2', 'dev7'), ('sw2', 'dev8'), ('sw2', 'dev9'), ('sw2', 'dev10'), ('sw2', 'dev11'), ('sw2', 'dev12'),
('sw2', 'comp1'), ('sw2', 'comp4'), ('comp1', 'app1_comp1'), ('comp1', 'app2_comp1'), ('comp2', 'app1_comp2'), ('comp2', 'app3_comp2'), ('comp2', 'app2_comp2'), ('comp2', 'app4_comp2'), ('comp3', 'app3_comp3'), ('comp3', 'app4_comp3'), ('comp4', 'app2_comp4'), ('comp4', 'app4_comp4')])

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
                logging.info(f"No path from {device} to {possible_app}")
                continue

            if shortest_path:
                app_on_comp = shortest_path[-1]
                properties["app"] = app_on_comp
                properties["path"] = shortest_path

    return subscription_dict


subscription_dict = shortest_path(G, subscription_dict)

print(subscription_dict)
subscription_dict = {
    "sub1": { "devices": ["dev1"], "app": "app1_comp3", "weight": 0.2, "path": ["dev1", "sw1", "sw2", "comp3", "app1_comp3"]},
    "sub2": { "devices": ["dev2"], "app": "app1_comp3", "weight": 0.2, "path": ["dev2", "sw1", "sw2", "comp3", "app1_comp3"]},
    "sub3": { "devices": ["dev3"], "app": "app1_comp3", "weight": 0.2, "path": ["dev3", "sw1", "sw2", "comp3", "app1_comp3"]},
    "sub4": { "devices": ["dev4"], "app": "app1_comp3", "weight": 0.2, "path": ["dev4", "sw1", "sw2", "comp3", "app1_comp3"]},
    "sub5": { "devices": ["dev5"], "app": "app1_comp3", "weight": 0.4, "path": ["dev5", "sw1", "sw2", "comp3", "app1_comp3"]},
    "sub6": { "devices": ["dev6"], "app": "app1_comp3", "weight": 0.4, "path": ["dev6", "sw1", "sw2", "comp3", "app1_comp3"]},
    "sub7": { "devices": ["dev7"], "app": "app1_comp3", "weight": 0.2, "path": ["dev7", "sw2", "comp3", "app1_comp3"]},
    "sub8": { "devices": ["dev8"], "app": "app1_comp3", "weight": 0.2, "path": ["dev8", "sw2", "comp3", "app1_comp3"]},
    "sub9": { "devices": ["dev9"], "app": "app1_comp3", "weight": 0.2, "path": ["dev9", "sw2", "comp3", "app1_comp3"]},
    "sub10": { "devices": ["dev10"], "app": "app1_comp3", "weight": 0.2, "path": ["dev10", "sw2", "comp3", "app1_comp3"]},
    "sub11": { "devices": ["dev11"], "app": "app1_comp3", "weight": 0.4, "path": ["dev11", "sw2", "comp3", "app1_comp3"]},
    "sub12": { "devices": ["dev12"], "app": "app1_comp3", "weight": 0.4, "path": ["dev12", "sw2", "comp3", "app1_comp3"]},
    "sub13": { "devices": ["dev13"], "app": "app1_comp3", "weight": 0.2, "path": ["dev13", "sw3", "sw2", "comp3", "app1_comp3"]},
    "sub14": { "devices": ["dev14"], "app": "app1_comp3", "weight": 0.2, "path": ["dev14", "sw3", "sw2", "comp3", "app1_comp3"]},
    "sub15": { "devices": ["dev15"], "app": "app1_comp3", "weight": 0.2, "path": ["dev15", "sw3", "sw2", "comp3", "app1_comp3"]},
    "sub16": { "devices": ["dev16"], "app": "app1_comp3", "weight": 0.2, "path": ["dev16", "sw3", "sw2", "comp3", "app1_comp3"]},
    "sub17": { "devices": ["dev17"], "app": "app1_comp3", "weight": 0.4, "path": ["dev17", "sw3", "sw2", "comp3", "app1_comp3"]},
    "sub18": { "devices": ["dev18"], "app": "app1_comp3", "weight": 0.4, "path": ["dev18", "sw3", "sw2", "comp3", "app1_comp3"]},
    "sub19": { "devices": ["dev19"], "app": "app1_comp3", "weight": 0.4, "path": ["dev19", "sw3", "sw2", "comp3", "app1_comp3"]},
    "sub20": { "devices": ["dev20"], "app": "app1_comp3", "weight": 0.4, "path": ["dev20", "sw3", "sw2", "comp3", "app1_comp3"]},
    "sub21": { "devices": ["dev7"], "app": "app2_comp4", "weight": 0.3, "path": ["dev7", "sw2", "comp4", "app2_comp4"]},
    "sub22": { "devices": ["dev8"], "app": "app2_comp4", "weight": 0.3, "path": ["dev8", "sw2", "comp4", "app2_comp4"]},
    "sub23": { "devices": ["dev9"], "app": "app2_comp4", "weight": 0.3, "path": ["dev9", "sw2", "comp4", "app2_comp4"]},
    "sub24": { "devices": ["dev10"], "app": "app2_comp4", "weight": 0.3, "path": ["dev10", "sw2", "comp4", "app2_comp4"]},
    "sub25": { "devices": ["dev11"], "app": "app2_comp4", "weight": 0.5, "path": ["dev11", "sw2", "comp4", "app2_comp4"]},
    "sub26": { "devices": ["dev12"], "app": "app2_comp4", "weight": 0.5, "path": ["dev12", "sw2", "comp4", "app2_comp4"]},
    "sub27": { "devices": ["dev5"], "app": "app3_comp4", "weight": 0.8, "path": ["dev5", "sw1", "sw2", "comp4", "app3_comp4"]},
    "sub28": { "devices": ["dev6"], "app": "app3_comp4", "weight": 0.8, "path": ["dev6", "sw1", "sw2", "comp4", "app3_comp4"]},
    "sub29": { "devices": ["dev11"], "app": "app3_comp4", "weight": 0.8, "path": ["dev11", "sw2", "comp4", "app3_comp4"]},
    "sub30": { "devices": ["dev12"], "app": "app3_comp4", "weight": 0.8, "path": ["dev12", "sw2", "comp4", "app3_comp4"]},
    "sub31": { "devices": ["dev17"], "app": "app3_comp2", "weight": 0.8, "path": ["dev17", "sw3", "sw0", "comp2", "app3_comp2"]},
    "sub32": { "devices": ["dev18"], "app": "app3_comp2", "weight": 0.8, "path": ["dev18", "sw3", "sw0", "comp2", "app3_comp2"]},
    "sub33": { "devices": ["dev19"], "app": "app3_comp2", "weight": 0.8, "path": ["dev19", "sw3", "sw0", "comp2", "app3_comp2"]},
    "sub34": { "devices": ["dev20"], "app": "app3_comp2", "weight": 0.8, "path": ["dev20", "sw3", "sw0", "comp2", "app3_comp2"]},
    "sub35": { "devices": ["dev13"], "app": "app4_comp1", "weight": 0.9, "path": ["dev13", "sw3", "sw2", "comp1", "app4_comp1"]},
    "sub36": { "devices": ["dev14"], "app": "app4_comp1", "weight": 0.9, "path": ["dev14", "sw3", "sw2", "comp1", "app4_comp1"]}
}
