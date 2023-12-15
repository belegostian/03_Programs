import os
import re
import ast
import csv
import networkx as nx
from collections import defaultdict

# Define logic gates
def and_gate(*args):
    probability = 1
    for event_prob in args:
        probability *= event_prob
    return probability

def or_gate(*args):
    probability = 1
    for event_prob in args:
        probability *= (1 - event_prob)
    return 1 - probability

def individual_to_graph(switch_dict, device_dict, computer_dict, individual):
    G = nx.Graph()
    
    # 前段
    nodes = list(switch_dict) + list(device_dict) + list(computer_dict)
    
    for node in nodes:
        G.add_node(node)
    
    for i in range(len(nodes)):
        if individual[i]:
            G.add_edge(individual[i], nodes[i])
            
    # 後段
    comps = list(computer_dict)
    for i in range(len(nodes), len(individual)):
        for app in individual[i]:
            node = f"{app}_{comps[i-len(nodes)]}"
            
            G.add_node(node)
            G.add_edge(comps[i-len(nodes)], node)
            
    return G, len(nodes)

def update_computer_dict(computer_dict, individual, first_range):
    # runnung apps
    for i in range(first_range, len(individual)):
        label = f'comp{i - first_range + 1}'
        computer_dict[label]['running_apps'] = individual[i]
            
    return computer_dict

def update_subscription_dict(G, subscription_dict):
    app_nodes = {node for node in G.nodes if node.startswith("app")}
    for sub, sub_info in subscription_dict.items():
        device = sub_info["device"]
        target_apps = {node for node in app_nodes if re.search(r'app' + sub_info["app"][-1], node)}
        try:
            shortest_path = min(
                (nx.shortest_path(G, source=device, target=app) for app in target_apps),
                key=len,
                default=None
            )
        except nx.NetworkXNoPath:
            return None
        if shortest_path:
            sub_info["app"] = shortest_path[-1]
            sub_info["path"] = shortest_path
    return subscription_dict

def risk_primary_number(application_dict, computer_dict, device_dict, switch_dict, subscription_dict, individual):
    network_graph, first_range = individual_to_graph(switch_dict, device_dict, computer_dict, individual)
    computer_dict = update_computer_dict(computer_dict, individual, first_range)
    
    # 避免新一代拓樸變異後無法產生正確路徑
    if update_subscription_dict(network_graph, subscription_dict) is None:
        return 10
    
    subscription_dict = update_subscription_dict(network_graph, subscription_dict)

    app_resource_crunched = defaultdict(float)
    RPN = defaultdict(float)
    for sub_key, sub_info in subscription_dict.items():
        basic_event_probs = {
            'single_host_fail': [0.0005, 0.0005], # 生產設備、計算設備
            'single_link_fail': [0.0001],
            'single_switch_fail': [0.0005],
            'single_port_overload': [],
            'app_resource_crunched': app_resource_crunched,
            'unexpected_app_behavior': 0.0003
        }

        event_probs = defaultdict(lambda: defaultdict(float))
        
        sub_path = sub_info['path']
        
        basic_event_probs['single_link_fail'] = basic_event_probs['single_link_fail'] * (len(sub_path)-2)
        basic_event_probs['single_switch_fail'] = basic_event_probs['single_switch_fail'] * (len(sub_path)-3)
        
        # single_port_overload:
        for i in range(len(sub_path)-2):
            # 1. 求出端口頻寬
            if 'dev' in sub_path[i]:
                bw1 = device_dict[sub_path[i]]['bandwidth']
            elif 'sw' in sub_path[i]:
                bw1 = switch_dict[sub_path[i]]['bandwidth']
            else:
                bw1 = computer_dict[sub_path[i]]['bandwidth']
                
            if 'dev' in sub_path[i+1]:
                bw2 = device_dict[sub_path[i+1]]['bandwidth']
            elif 'sw' in sub_path[i+1]:
                bw2 = switch_dict[sub_path[i+1]]['bandwidth']
            else:
                bw2 = computer_dict[sub_path[i+1]]['bandwidth']
                
            bandwidth = min(bw1, bw2)
            
            # 2. 求出端口流量
            matching_sub_dicts = []
            
            for key, info in subscription_dict.items():
                for j in range(len(info['path']) - 1):
                    if (info['path'][j] == sub_path[i] and info['path'][j + 1] == sub_path[i + 1]) or (info['path'][j] == sub_path[i + 1] and info['path'][j + 1] == sub_path[i]):
                        matching_sub_dicts.append(key)
            
            throughput = 0            
            for sub in matching_sub_dicts:
                throughput += (application_dict[subscription_dict[sub]['app'].split('_')[0]]['packet_sending (kB)'] + application_dict[subscription_dict[sub]['app'].split('_')[0]]['packet_receiving (kB)'])
            
            # 3. 端口頻寬/端口流量； 2.25以上為 0.0001, 1.5~2.25為 0.001, 1.25~1.5為 0.01, 1.0~1.25為 0.1
            if bandwidth / throughput * 1000 >= 2.25:
                basic_event_probs['single_port_overload'].append(0.0001)
            elif bandwidth / throughput * 1000 >= 1.5:
                basic_event_probs['single_port_overload'].append(0.001)
            elif bandwidth / throughput * 1000 >= 1.25:
                basic_event_probs['single_port_overload'].append(0.01)
            elif bandwidth / throughput * 1000 >= 1.0:
                basic_event_probs['single_port_overload'].append(0.1)
            else:
                basic_event_probs['single_port_overload'].append(1)
        
        # app_resource_crunched:
        comp = sub_info['app'].split('_')[1]
        if comp not in app_resource_crunched:
            apps_in_comp = defaultdict(int)
            
            for key, info in subscription_dict.items():
                if info['app'].split('_')[1] == comp:
                    apps_in_comp[info['app'].split('_')[0]] += 1
            
            comp_cpu = computer_dict[comp]['cpu']
            comp_mem = computer_dict[comp]['memory']
            
            app_cpu = 0
            app_mem = 0
            for app, num in apps_in_comp.items():
                app_cpu += application_dict[app]['cpu_usage (%)'] * (1 + num*0.05) # PS. 假設APP負荷隨連線數增加而增加 (0.05倍)
                app_mem += application_dict[app]['memory_usage (MiB)'] * (1 + num*0.02)
                
            crunch_factor = min(comp_cpu * 100 / app_cpu, comp_mem / app_mem)
                
            if crunch_factor >= 2.25:
                app_resource_crunched[comp] = 0.0001
            elif crunch_factor >= 1.5:
                app_resource_crunched[comp] = 0.001
            elif crunch_factor >= 1.25:
                app_resource_crunched[comp] = 0.01
            elif crunch_factor >= 1.0:
                app_resource_crunched[comp] = 0.1
            else:
                app_resource_crunched[comp] = 1
        
        basic_event_probs['app_resource_crunched'] = app_resource_crunched[comp]
        
        event_probs['host_fail'] = or_gate(*basic_event_probs['single_host_fail'])
        event_probs['link_fail'] = or_gate(*basic_event_probs['single_link_fail'])
        event_probs['switch_fail'] = or_gate(*basic_event_probs['single_switch_fail'])
        event_probs['port_overload'] = or_gate(*basic_event_probs['single_port_overload'])
        event_probs['link_down'] = or_gate(event_probs['host_fail'], event_probs['link_fail'], event_probs['switch_fail'])
        event_probs['time_out'] = or_gate(event_probs['port_overload'], basic_event_probs['app_resource_crunched'])
        event_probs['connection_fail'] = or_gate(event_probs['link_down'], event_probs['time_out'])
        event_probs['subscription_fail'] = or_gate(event_probs['connection_fail'], basic_event_probs['unexpected_app_behavior'])
        
        RPN[sub_key] = event_probs['subscription_fail'] * float(sub_info['weight'])
    
    return sum(RPN.values()) * 1000