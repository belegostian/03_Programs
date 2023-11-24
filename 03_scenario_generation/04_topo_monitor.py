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
        return None

    link_pattern = r"net\.addLink\((\w+), (\w+), cls=TCLink, .*?\)"
    switch_link_count = {}
    comp_switch_port_pairs = {}

    for line in links_section.split('\n'):
        match = re.match(link_pattern, line)
        if match:
            host1, host2 = match.groups()

            # Check and update link counts for switches
            if 'sw' in host1:
                switch_link_count[host1] = switch_link_count.get(host1, 0) + 1
            if 'sw' in host2:
                switch_link_count[host2] = switch_link_count.get(host2, 0) + 1

            # Assign switch-port pair for comps
            if 'comp' in host1 or 'comp' in host2:
                comp = host1 if 'comp' in host1 else host2
                switch = host2 if 'comp' in host1 else host1
                port_number = switch_link_count[switch]
                comp_switch_port_pairs[comp] = f"{switch}-eth{port_number}"

    return comp_switch_port_pairs

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