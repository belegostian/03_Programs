import re
import logging
import os
import glob
import subprocess
import time

# Setting up basic configuration for logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def extract_link_info(filename):
    try:
        with open(filename, 'r') as file:
            content = file.read()
    except FileNotFoundError:
        logging.error("File not found.")
        return None

    start_phrase = r"Creating links"
    end_phrase = r"Starting network"

    start_match = re.search(start_phrase, content)
    end_match = re.search(end_phrase, content)

    if not start_match or not end_match:
        logging.warning("Start or end phrase not found in file.")
        return None

    links_section = content[start_match.end():end_match.start()].strip()
    return links_section

def predict_comp_ports(filename):
    links_section = extract_link_info(filename)
    if links_section is None:
        return
    
    link_pattern = r"net\.addLink\((\w+), (\w+), cls=TCLink, .*?\)"
    switch_port_count = {}
    results = {}

    for line in links_section.split('\n'):
        match = re.match(link_pattern, line)
        if match:
            host, switch = match.groups()
            if 'comp' in host:
                switch_port_count[switch] = switch_port_count.get(switch, 1) + 1
                results[host] = f"{switch}-eth{switch_port_count[switch]}"
                
    return results

def run_tshark_commands(folder, switch_port_pairs):
    for comp, interface in switch_port_pairs.items():
        file_path = os.path.join(folder, f"tshark_{comp}.pcap")
        
        # 以下用於Linux
        cmd = f"sudo timeout 30 tshark -i {interface} -w {file_path}"
        logging.info(f"Running command: {cmd}")
        subprocess.run(cmd, shell=True)
        logging.info("Waiting for 30 seconds...")
        time.sleep(40)

def main():
    # Setting up basic configuration for logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Analyzing all containernet_script.py in the sub-folders
    base_path = 'experiment_0'
    scenario_folders = glob.glob(os.path.join(base_path, 'scenario_*'))
    analysis_results = {}

    for folder in scenario_folders:
        script_path = os.path.join(folder, 'containernet_script.py')
        analysis_results[folder] = predict_comp_ports(script_path)

    # Printing the final results
    for scenario, result in analysis_results.items():
        print(f"Results for {scenario}: {result}")
        
    for folder, switch_port_pairs in analysis_results.items():
        run_tshark_commands(folder, switch_port_pairs)

if __name__ == "__main__":
    main()




    
    
    

