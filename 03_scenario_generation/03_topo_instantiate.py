import os
import csv
import ast
import logging
import networkx as nx
from collections import defaultdict
from datetime import datetime

# 第一章，輔助函式
def csv_to_dict(file_path, key_field, transformations=None, split_fields=None):
    data_dict = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            key = row.pop(key_field)

            # Split specified fields
            if split_fields:
                for field, delimiter in split_fields.items():
                    if field in row:
                        row[field] = row[field].split(delimiter)

            # Apply transformations
            if transformations:
                for field, func in transformations.items():
                    if field in row:
                        row[field] = func(row[field])

            data_dict[key] = row
    return data_dict

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

def insert_docker_containers(container_dict, tag_version, base_ip, script_name_format, file_lines, insert_index, device_ip_mapping):
    current_group = None
    ip_base = base_ip

    for name, info in container_dict.items():
        if current_group != info['group']:
            current_group = info['group']
            ip_base = (ip_base // 10 + 1) * 10
            
        ip = f"10.0.0.{ip_base}"
        python_script = script_name_format(info).format(name.lower())
        docker_image = info['type'].lower()
        line = f"{name} = net.addDocker('{name}', ip='{ip}', dcmd='python {python_script}', dimage='{docker_image}:{tag_version}')\n"
        file_lines.insert(insert_index, line)
        
        device_ip_mapping[name] = ip
        insert_index += 1
        ip_base += 1
    return file_lines

# 補充 insert_docker_containers() 的輔助函式
def computer_script_name_format(computer_info, application_dict):
    running_apps = computer_info['running_apps']
    if len(running_apps) == 1:
        app_name = application_dict[running_apps[0]]['name'].lower().replace(" ", "_")
        return f"{app_name}.py"
    else:
        return "wrapper.py"

# 第二章，主函式
def main(file_path):
    # 資料讀取&準備
    device_transformations = {
        'bandwidth': int,
        'group': int
    }
    device_dict = csv_to_dict('experiment_0\\devices.csv', 'device', device_transformations)

    computer_transformations = {
        'running_apps': ast.literal_eval,
        'cpu': float,
        'memory': int,
        'bandwidth': int,
        'group': lambda x: None if x == '' else int(x)
    }
    computer_dict = csv_to_dict(os.path.join(file_path, 'computers.csv'), 'computer', computer_transformations)
    sorted_computer_dict = sorted(computer_dict.items(), key=lambda x: x[1]['group'] if x[1]['group'] is not None else 0)

    application_transformations = {
        'response_timeout': float,
        'cpu_usage (%)': float,
        'memory_usage (MiB)': float,
        'packet_sending (kB)': float,
        'packet_receiving (kB)': float
    }
    application_dict = csv_to_dict('experiment_0\\applications.csv', 'application', application_transformations)

    subscription_split_fields = {
        'path': ','
    }
    subscription_dict = csv_to_dict(os.path.join(file_path, 'subscription_paths.csv'), 'subscription', None, subscription_split_fields)

    switch_transformations = {
        'bandwidth': int,
        'forward_delay': float
    }
    switch_dict = csv_to_dict('experiment_0\switches.csv', 'switch', switch_transformations)

    network_graph = create_graph_from_csv('experiment_0\scenario_0\scenario_0.csv')

    #腳本撰寫
    with open('containernet_sample.py', 'r') as file:
        lines = file.readlines()

    # 建立 device-host
    insert_index = next(i for i, line in enumerate(lines) if "*** Adding docker containers as hosts" in line) + 1

    device_ip_mapping = {}
    lines = insert_docker_containers(device_dict, "ver2", 100, lambda info: f"{info['type'].lower()}.py", lines, insert_index, device_ip_mapping)

    # 建立 computer-host
    ip_base = 200
    initial_group = 0
    cpu_period_default = 100000
    default_tag = "11-15-22"

    for computer_name, computer_info in sorted_computer_dict:
        
        if computer_info['group'] != initial_group:
            ip_base = ((ip_base // 10) + 1) * 10
            initial_group = computer_info['group']

        ip = f"10.0.0.{ip_base}"
        python_script = computer_script_name_format(computer_info, application_dict)
        
        env_vars = {}
        if len(computer_info['running_apps']) == 0: # 沒有連線對象的電腦相對系統等於不存在
            ip_base += 1
            continue
        elif len(computer_info['running_apps']) == 1:
            docker_image = application_dict[computer_info['running_apps'][0]]['name'].lower().replace(" ", "_")
            tag_version = "ver2"
            
            env_key = ''.join([word[0].upper() for word in docker_image.split("_")]) + "_SERVER_IPS"
            subscription_key = f"{computer_info['running_apps'][0]}_{computer_name}"
            devices = [sub_info['device'] for sub, sub_info in subscription_dict.items() if sub_info['app'] == subscription_key]
            if devices:
                ips = [device_ip_mapping[dev] for dev in devices if dev in device_ip_mapping]
                env_vars[env_key] = ','.join(ips)
            else:
                env_vars[env_key] = ""    
            
        else:
            docker_image = '_'.join([''.join([word[0].lower() for word in application_dict[app]['name'].split()]) for app in computer_info['running_apps']])
            tag_version = default_tag
            
            app_count = 0
            for app in computer_info['running_apps']:
                env_key = docker_image.split("_")[app_count].upper() + "_SERVER_IPS"
                subscription_key = f"{app}_{computer_name}"
                devices = [sub_info['device'] for sub, sub_info in subscription_dict.items() if sub_info['app'] == subscription_key]
                if devices:
                    ips = [device_ip_mapping[dev] for dev in devices if dev in device_ip_mapping]
                    env_vars[env_key] = ','.join(ips)
                else:
                    env_vars[env_key] = ""    
                    
                app_count += 1

        memory_limit = f"{computer_info['memory']}m"
        memory_add_swap_limit = f"{computer_info['memory'] * 3}m"
        cpu_quota = int(computer_info['cpu'] * cpu_period_default)
        environment_str = ', '.join([f'"{k}": "{v}"' for k, v in env_vars.items()])
        environment_str = "{" + environment_str + "}"
        
        insert_line = f"{computer_name} = net.addDocker('{computer_name}', ip='{ip}', dcmd='python {python_script}', dimage='{docker_image}:{tag_version}', mem_limit='{memory_limit}', memswap_limit='{memory_add_swap_limit}', cpu_period={cpu_period_default}, cpu_quota={cpu_quota}, environment={environment_str})\n" # , environment={environment_str}
        lines.insert(insert_index, insert_line)
        insert_index += 1
        ip_base += 1

    # 建立 switch
    insert_index = next(i for i, line in enumerate(lines) if "*** Adding switches" in line) + 1
    for switch_name in switch_dict.keys():
        switch_line = f"{switch_name} = net.addSwitch('{switch_name}')\n"
        lines.insert(insert_index, switch_line)
        insert_index += 1

    # 建立 link
    insert_index = next(i for i, line in enumerate(lines) if "*** Creating links" in line) + 1
    for edge in network_graph.edges():
        if edge[0] in switch_dict and edge[1] in switch_dict:
            link_line = f"net.addLink({edge[0]}, {edge[1]}, cls=TCLink, use_htb=True)\n"
            lines.insert(insert_index, link_line)
            insert_index += 1

    for edge in network_graph.edges():
        switch, host = (edge if edge[0] in switch_dict else reversed(edge))
        if host in switch_dict or switch not in switch_dict:
            continue  # Skip if both are switches or neither is a switch

        switch_info = switch_dict[switch]
        delay = switch_info['forward_delay']
        
        switch_bandwidth = switch_info['bandwidth']
        host_bandwidth = (device_dict if host in device_dict else computer_dict).get(host, {}).get('bandwidth', 0)
        bandwidth = min(switch_bandwidth, host_bandwidth)

        link_line = f"net.addLink({host}, {switch}, cls=TCLink, bw={bandwidth}, delay='{delay}ms', use_htb=True)\n"
        lines.insert(insert_index, link_line)
        insert_index += 1

    with open(os.path.join(file_path, 'containernet_script.py'), 'w') as file:
        file.writelines(lines)

if __name__ == "__main__":
    scenario_num = 5
    
    for i in range(scenario_num):
        file_path = f'experiment_0\\scenario_{i}'
        main(file_path)
        
        print(f"Scenario {i} completed.")