import os
import re
import csv
import time
import glob
import json
import logging
import subprocess
import pandas as pd
from pathlib import Path

# Precompiled Regular Expressions
comp_pattern = re.compile(r'comp\d+')
env_var_pattern = re.compile(r'"([^"]+)":\s*"([^"]+)"')

# PART1: 前置處理，取得拓墣中每個comp上運行的app與其連線的device
def extract_context(file_path, start_phrase, end_phrase):
    with open(file_path, 'r') as file:
        start_index = end_index = None
        for i, line in enumerate(file):
            if start_phrase in line:
                start_index = i
            elif end_phrase in line and start_index is not None:
                end_index = i
                break

        if start_index is not None and end_index is not None:
            file.seek(0)  # Reset file pointer to beginning
            return [line for i, line in enumerate(file) if start_index < i < end_index]

    return []

def parse_environment_variables(line):
    env_vars = {}
    match = re.search(r'environment=\{(.+?)\}\)', line)
    if match:
        env_var_str = match.group(1)
        vars = env_var_pattern.findall(env_var_str)
        for key, val in vars:
            env_vars[key] = val
    return env_vars

def process_scenario_folder(folder):
    container_file = os.path.join(folder, 'containernet_script.py')
    
    if os.path.exists(container_file):
        context_creating_links = extract_context(container_file, 'Creating links', '#')
        comps = [comp for line in context_creating_links for comp in comp_pattern.findall(line)]
        comp_dict = {comp: None for comp in comps}

        context_adding_containers = extract_context(container_file, 'Adding docker containers as hosts', '#')
        for line in context_adding_containers:
            comp_match = re.search(r'comp\d+', line)
            if comp_match:
                comp_name = comp_match.group()
                if comp_name in comp_dict:
                    env_vars = parse_environment_variables(line)
                    comp_dict[comp_name] = env_vars
    
        return comp_dict
    return {}

# PART2: 依序進行封包解析，並補上封包的拓樸條件
def initialize_training_data(csv_file_path):
    headers = ['Scenario', 'Computer', 'Application', 'Device', 'Subscription Order', 'Weight', 'Session', 'Average RTT', 'Average Req Resp Delay', 'Average Reconnection Count', 'Average Error Packets Count']
    with open(csv_file_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if csvfile.tell() == 0:  # File is empty, write headers
            writer.writerow(headers)

def count_ip_quota(env_vars):
    ip_quota = {}
    
    for key, value in env_vars.items():
        ips = value.split(',')
        for ip in ips:
            ip_quota[ip] = ip_quota.get(ip, 0) + 1
    
    return ip_quota

def find_device_and_app(context_adding_containers, device_ip, env_vars, comp):
    # Find the device
    device_line = next((line for line in context_adding_containers if line.strip().startswith('dev') and device_ip in line), None)
    device = re.search(r"dev(\d+)", device_line).group() if device_line else None
    
    # Find the application
    app = next((app for app, ips in env_vars.items() if device_ip in ips.split(',')), None)

    # Remove the device IP from the corresponding application in env_vars
    if app and device_ip in env_vars.get(app, ''):
        ips = env_vars[app].split(',')
        ips.remove(device_ip)
        env_vars[app] = ','.join(ips)
    
    return device, app, env_vars

def find_subscription_order(subscription_file, device, app_comp):
    with open(subscription_file, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if row[1] == device and row[2] == app_comp:
                return row[0], row[3]
    return None

def update_data_training(output_file, scenario, comp, app, device, subscription_order, weight, start_index):
    # Read the CSV file and store rows in a list
    with open(output_file, 'r', newline='') as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        headers = reader.fieldnames

    # Update the specific row
    if start_index < len(rows):
        rows[start_index].update({
            'Scenario': scenario,
            'Computer': comp,
            'Application': app,
            'Device': device,
            'Subscription Order': subscription_order,
            'Weight': weight
        })
        start_index += 1  # Increment the start_index for the next call

    # Write the updated rows back to the file
    with open(output_file, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
        
    time.sleep(0.1)

    return start_index

# 主程式
def main(folder, result_dicts, time_interval, output_file, start_index):
    subscription_file_path = Path(folder) / 'subscription_paths.csv'
    container_file = Path(folder) / 'containernet_script.py'
    
    # 初次創建data_training.csv
    initialize_training_data(output_file)
    
    if container_file.exists():
        # 取得該拓墣生成的hosts
        context_adding_containers = extract_context(container_file, 'Adding docker containers as hosts', '#')
        
        # 因為t-shark監控點在comp-sw的街線上，所以以comp為單位處理
        for comp, env_vars in result_dicts[Path(folder).name].items():
            capture_file = next(Path(folder).glob(f'{comp}.pcap'), None)
            
            client_ip_line = next((line for line in context_adding_containers if comp in line), None)
            client_ip = re.search(r'ip=\'(\d+\.\d+\.\d+\.\d+)\'', client_ip_line).group(1) if client_ip_line else None
            
            # 取得預估連線術語dev連線數配額
            expected_session_count = sum(len(val.split(',')) for val in env_vars.values()) if env_vars else 0
            ip_quota = count_ip_quota(env_vars)
            
            # 呼叫opc_traffic_analyze2.py，取得一半的訓練資料 (average_rtt, average_req_resp_delay, average_reconnection_count, average_error_packets_count)
            subprocess.run(['python', '01_PacketAnalyze\\opc_traffic_analyze2.py', client_ip, str(expected_session_count), json.dumps(ip_quota), str(capture_file), str(output_file), str(time_interval)])

            # 取得一半的訓練資料後，對應填寫剩下的另一半訓練資料
            session_data = pd.read_csv(output_file, header=0, skiprows=range(1, start_index + 1), nrows=expected_session_count)
            
            if 'Session' in session_data.columns:
                for _, row in session_data.iterrows():
                    session = row['Session'] if 'Session' in row else None
                    if session:
                        # 由於session的出現順序是隨機的，所以從該session的資訊反推app, device
                        device_ip = session.split('-')[1]
                        device, app, env_vars = find_device_and_app(context_adding_containers, device_ip, env_vars, comp)
                        app = app.split('_')[0].lower() if app else None
                        
                        if app:
                            applications_data = pd.read_csv('03_scenario_generation\\experiment_0\\applications.csv')
                            applications_data['initials'] = applications_data['name'].apply(lambda x: ''.join(word[0].lower() for word in x.split()))
                            app_row = applications_data[applications_data['initials'] == app]
                            if not app_row.empty:
                                app = app_row.iloc[0]['application']
                        
                        # 取得訂閱資訊
                        subscription_order, weight = find_subscription_order(subscription_file_path, device, f'{app}_{comp}')
                        
                        # 填寫剩下的另一半訓練資料
                        start_index = update_data_training(output_file, Path(folder).name, comp, app, device, subscription_order, weight, start_index)
            else:
                # 捕捉例外，目前無用
                pass
            
    return start_index

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    base_path = '03_scenario_generation\\experiment_0'
    time_interval = '10'
    output_file = '01_PacketAnalyze\\data_training.csv'
    start_index=0
    
    scenario_folders = glob.glob(os.path.join(base_path, f'*scenario*'))
    result_dicts = {Path(folder).name: process_scenario_folder(folder) for folder in scenario_folders}
    
    for folder in scenario_folders:
        start_index = main(folder, result_dicts, time_interval, output_file, start_index)