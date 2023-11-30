import subprocess
import csv
import os
import re
import glob
from pathlib import Path
import pandas as pd
import time

# Precompiled Regular Expressions
comp_pattern = re.compile(r'comp\d+')
env_var_pattern = re.compile(r'"([^"]+)":\s*"([^"]+)"')

# 第一部分: 確認所有scenario下每個computer對應的application, device
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

def find_line_with_key(lines, key):
    for line in lines:
        if key in line:
            return line.strip()
    return None

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

# 第二部分: 提取subprocess的變數，執行並得到一半的訓練資料
def write_headers(csv_file_path):
    headers = ['Scenario', 'Computer', 'Application', 'Device', 'Subscription Order', 'Weight', 'Session', 'Average RTT', 'Average Req Resp Delay', 'Average Reconnection Count', 'Average Error Packets Count']
    with open(csv_file_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        if csvfile.tell() == 0:  # File is empty, write headers
            writer.writerow(headers)

def process_scenario(folder, result_dicts, time_interval, output_file, start_index):
    subscription_file_path = Path(folder) / 'subscription_paths.csv'
    write_headers(output_file)

    container_file = Path(folder) / 'containernet_script.py'
    if container_file.exists():
        context_adding_containers = extract_context(container_file, 'Adding docker containers as hosts', '#')
        
        for comp, env_vars in result_dicts[Path(folder).name].items():
            # Find comp's IP
            client_ip_line = next((line for line in context_adding_containers if comp in line), None)
            client_ip = re.search(r'ip=\'(\d+\.\d+\.\d+\.\d+)\'', client_ip_line).group(1) if client_ip_line else None
            
            # Count IPs
            expected_session_count = sum(len(val.split(',')) for val in env_vars.values()) if env_vars else 0

            # Find .pcap file
            capture_file = next(Path(folder).glob(f'{comp}.pcap'), None)
            
            subprocess.run(['python', '01_PacketAnalyze\\opc_traffic_analyze2.py', client_ip, str(expected_session_count), str(capture_file), str(output_file), str(time_interval)])

            header = pd.read_csv(output_file, nrows=0)
            session_data = pd.read_csv(output_file, header=0, skiprows=range(1, start_index + 1), nrows=expected_session_count)
            
            if 'Session' in session_data.columns:
                for _, row in session_data.iterrows():
                    session = row['Session'] if 'Session' in row else None
                    if session:
                        device_ip = session.split('-')[1]
                        device, app, env_vars = find_device_and_app(context_adding_containers, device_ip, env_vars, comp)
                        app = app.split('_')[0].lower() if app else None
                        
                        if app:
                            applications_data = pd.read_csv('03_scenario_generation\\experiment_0\\applications.csv')
                            applications_data['initials'] = applications_data['name'].apply(lambda x: ''.join(word[0].lower() for word in x.split()))
                            app_row = applications_data[applications_data['initials'] == app]
                            if not app_row.empty:
                                app = app_row.iloc[0]['application']
                                
                        subscription_order, weight = find_subscription_order(subscription_file_path, device, f'{app}_{comp}')
                        start_index = update_data_training(output_file, Path(folder).name, comp, app, device, subscription_order, weight, start_index)
            else:
                # 待補
                pass
            
    return start_index

# 第三部分: 對應填寫剩下的另一半訓練資料
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

def main(base_path, time_interval, output_file):
    
    scenario_folders = glob.glob(os.path.join(base_path, f'*scenario*'))
    all_results = {Path(folder).name: process_scenario_folder(folder) for folder in scenario_folders}

    start_index=0
    for folder in scenario_folders:
        start_index = process_scenario(folder, all_results, time_interval, output_file, start_index)

if __name__ == "__main__":
    base_path = '03_scenario_generation\\experiment_0'
    time_interval = '10'
    output_file = '01_PacketAnalyze\\data_training.csv'
    
    main(base_path, time_interval, output_file)

# Parameters for the training data that will be calculated:
# average_rtt, average_req_resp_delay, average_reconnection_count, average_error_packets_count