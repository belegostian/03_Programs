import csv
import os
import json
import random
import networkx as nx
import matplotlib.pyplot as plt

#! TOFO
"""
    1. 統一路徑
"""

#? 請在03_Programs資料夾下執行此程式

# 第一章: 輔助型函式
def read_csv_as_dict(filename, key_column, processing_func=None):
    result_dict = {}
    try:
        with open(filename, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                key = row.pop(key_column)
                if processing_func:
                    row = processing_func(row)
                result_dict[key] = row
    except IOError as e:
        print(f"Error reading file {filename}: {e}")

    return result_dict

def write_dict_to_csv(filename, dict_data, headers):
    try:
        with open(filename, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for key, data in dict_data.items():
                data_with_key = {headers[0]: key, **data}
                writer.writerow(data_with_key)
    except IOError as e:
        print(f"Error writing file {filename}: {e}")

def process_device_row(row):
    row["bandwidth"] = int(row["bandwidth"])
    row["group"] = int(row["group"])

    return row

def process_application_row(row):
    row["response_timeout"] = float(row["response_timeout"])
    row["cpu_usage (%)"] = float(row["cpu_usage (%)"])
    row["memory_usage (MiB)"] = float(row["memory_usage (MiB)"])
    row["packet_sending (kB)"] = float(row["packet_sending (kB)"])
    row["packet_receiving (kB)"] = float(row["packet_receiving (kB)"])
    row["target_device"] = row["target_device"].split(", ")

    return row

def process_computer_row(row):
    row["running_apps"] = json.loads(row["running_apps"])
    row["cpu"] = float(row["cpu"])
    row["memory"] = int(row["memory"])
    row["bandwidth"] = int(row["bandwidth"])
    row["group"] = None if row["group"] == "" else int(row["group"])

    return row

def process_switch_row(row):
    row["bandwidth"] = int(row["bandwidth"])
    row["forward_delay"] = float(row["forward_delay"])

    return row

def create_directory(directory_name):
    if not os.path.exists(directory_name):
        os.makedirs(directory_name)


# 第二章: 生成拓樸函式
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
        G.add_edge(label, switch_to_connect)
            
    if plot:
        nx.draw(G, with_labels=True, node_color="lightblue", node_size=2000)
        plt.title("Node-Updated Network Topology")
        plt.show()

    return G

def add_app_nodes_to_topology(G, application_dict, computer_dict, show_plot=False, iteration=0):
    for computer, properties in computer_dict.items():
        for app in properties["running_apps"]:
            if app in application_dict:
                app_instance = f"{app}_{computer}"
                G.add_node(app_instance)
                G.add_edge(app_instance, computer)

    # 實驗比對用圖，細節會比較多
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
    
    plt.figure(figsize=(18, 12))
    nx.draw(
        G,
        labels=label_dict,
        with_labels=True,
        node_size=2000,
        node_color=node_colors,
        font_size=15
    )
    plt.title("Updated Network Topology with Applications")
    plt.savefig(f"03_scenario_generation\\experiment_0\\scenario_{iteration}\\network_topo.png", format='PNG', dpi=300)

    if show_plot:        
        plt.show()
        
    return G
        
# 第三章: 主函式
def main(G, iteration):
    # 讀取資料
    device_dict = read_csv_as_dict('03_scenario_generation\\experiment_0\\devices.csv', 'device', process_device_row)
    application_dict = read_csv_as_dict('03_scenario_generation\\experiment_0\\applications.csv', 'application', process_application_row)
    computer_dict = read_csv_as_dict('03_scenario_generation\\experiment_0\\computers.csv', 'computer', process_computer_row)
    switch_dict = read_csv_as_dict('03_scenario_generation\\experiment_0\\switches.csv', 'switch', process_switch_row)
    
    # 生成拓樸
    computer_dict = assign_computer_group(computer_dict, len(switch_dict))
    computer_dict = assign_apps_to_computer(computer_dict, application_dict)
    
    switch_to_topo = generate_topology(G, switch_dict)
    device_to_topo = add_nodes_to_topology(switch_to_topo, device_dict)
    computer_to_topo = add_nodes_to_topology(device_to_topo, computer_dict)
    app_to_topo = add_app_nodes_to_topology(computer_to_topo, application_dict, computer_dict, show_plot=False, iteration=iteration)
    
    # 更新 CSV-1
    update_comp_csv_file = f'03_scenario_generation\\experiment_0\\scenario_{iteration}\\computers.csv'
    headers = ["computer", "cpu", "memory", "bandwidth", "group", "running_apps"]
    write_dict_to_csv(update_comp_csv_file, computer_dict, headers)
    
    # 更新 CSV-2
    topo_csv_file = f'03_scenario_generation\\experiment_0\\scenario_{iteration}\\network_topo.csv'
    with open(topo_csv_file, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Nodes'])
        writer.writerows([[node] for node in app_to_topo.nodes])
        writer.writerow([])
        writer.writerow(['Edges'])
        writer.writerows(app_to_topo.edges)
        
if __name__ == "__main__":
    scenario_num = 20
    G = nx.Graph()
    create_directory('03_scenario_generation\\experiment_0')
    
    for i in range(scenario_num):
        create_directory(f'03_scenario_generation\\experiment_0\\scenario_{i}')
        G.clear()
        main(G, i)
        
        print(f"Scenario {i} completed.")