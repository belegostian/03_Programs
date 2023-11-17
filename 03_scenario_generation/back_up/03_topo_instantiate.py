import os
import csv
import ast
import json
import random
import logging
from collections import defaultdict
from datetime import datetime

# 第一章，輔助函式
# 適用於 device_dict, computer_dict, 但 application_dict要轉換的欄位太多，就沒有套用
def csv_to_dict(file_path, transformations=None):
    data_dict = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            key = row.pop('device' if 'device' in row else 'computer')
            if transformations:
                for field, func in transformations.items():
                    if field in row:
                        row[field] = func(row[field])
            data_dict[key] = row
    return data_dict

# 專用於 subscription_dict
def csv_to_dict_with_list_path(file_path):
    with open(file_path, mode='r') as file:
        csv_reader = csv.DictReader(file)
        data_dict = {}
        for row in csv_reader:
            row['path'] = row['path'].split(',')
            data_dict[row['subscription']] = row
    return data_dict

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
def computer_script_name_format(computer_info):
    running_apps = computer_info['running_apps']
    if len(running_apps) == 1:
        app_name = application_dict[running_apps[0]]['name'].lower().replace(" ", "_")
        return f"{app_name}.py"
    else:
        return "wrapper.py"

# 第一章第二段，資料讀取&準備
device_transformations = {
    'bandwidth': int,
    'group': int
}
device_dict = csv_to_dict('experiment_0\\devices.csv', device_transformations)

computer_transformations = {
    'running_apps': ast.literal_eval,
    'cpu': float,
    'memory': int,
    'bandwidth': int,
    'group': lambda x: None if x == '' else int(x)
}
computer_dict = csv_to_dict('experiment_0\scenario_0\computers.csv', computer_transformations)
sorted_computer_dict = sorted(computer_dict.items(), key=lambda x: x[1]['group'] if x[1]['group'] is not None else 0)

application_dict = {}
with open('experiment_0\\applications.csv', 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        app = row.pop('application')
        row['target_device'] = row['target_device'].split(', ')
        row['response_timeout'] = float(row['response_timeout'])
        row['cpu_usage (%)'] = float(row['cpu_usage (%)'])
        row['memory_usage (MiB)'] = float(row['memory_usage (MiB)'])
        row['packet_sending (kB)'] = float(row['packet_sending (kB)'])
        row['packet_receiving (kB)'] = float(row['packet_receiving (kB)'])
        application_dict[app] = row

subscription_dict = csv_to_dict_with_list_path('experiment_0\scenario_0\subscription_paths.csv')

# 第二章，腳本撰寫
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
    python_script = computer_script_name_format(computer_info)
    
    env_vars = {}
    if len(computer_info['running_apps']) == 0: # 沒有連線對象的電腦相對系統等於不存在
        ip_base += 1
        continue
    elif len(computer_info['running_apps']) == 1:
        docker_image = application_dict[computer_info['running_apps'][0]]['name'].lower().replace(" ", "_")
        tag_version = "ver1"
        
        env_key = ''.join([word[0].upper() for word in docker_image.split("_")]) + "_SERVER_IPS"
        subscription_key = f"{computer_info['running_apps'][0]}_{computer_name}"
        devices = [sub_info['device'] for sub, sub_info in subscription_dict.items() if sub_info['app'] == subscription_key]
        if devices:
            ips = [device_ip_mapping[dev] for dev in devices if dev in device_ip_mapping]
            env_vars[env_key] = ','.join(ips)
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
            app_count += 1

    memory_limit = f"{computer_info['memory']}m"
    memory_add_swap_limit = f"{computer_info['memory'] * 3}m"
    cpu_quota = int(computer_info['cpu'] * cpu_period_default)
    environment_str = ', '.join([f'"{k}": "{v}"' for k, v in env_vars.items()])
    environment_str = "{" + environment_str + "}"
    
    insert_line = f"{computer_name} = net.addDocker('{computer_name}', ip='{ip}', dcmd='python {python_script}', dimage='{docker_image}:{tag_version}', mem_limit='{memory_limit}', memswap_limit='{memory_add_swap_limit}', cpu_period='{cpu_period_default}', cpu_quota='{cpu_quota}', environment={environment_str})\n" # , environment={environment_str}
    lines.insert(insert_index, insert_line)
    insert_index += 1
    ip_base += 1
    
# Write the modified script
with open('containernet_sample_modified.py', 'w') as file:
    file.writelines(lines)
