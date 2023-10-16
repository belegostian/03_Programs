import pyshark
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

SOURCE_IP = '192.168.3.107'
CAPTURE_FILE = 'packets\HOMGE1.pcapng'
TIME_INTERVAL = 10

def read_pcapng_file(filename):
    with pyshark.FileCapture(filename, keep_packets=True) as cap:
        packet_list = []
        start_time = None
        for packet in cap:
            if start_time is None:
                start_time = packet.sniff_time.timestamp()
                end_time = start_time + TIME_INTERVAL

            if packet.sniff_time.timestamp() <= end_time:
                packet_list.append(packet)
            else:
                yield packet_list

                packet_list = [packet]
                start_time = packet.sniff_time.timestamp()
                end_time = start_time + TIME_INTERVAL

        if packet_list:
            yield packet_list
    

def filter_packets(packet_list, ip_address):
    packets = defaultdict(list)
    connection_groups = defaultdict(list)

    for packet in packet_list:
        # Checks if the packet is IP packet
        if 'IP' in packet:
            if packet.ip.src == ip_address or packet.ip.dst == ip_address:
                packets['related'].append(packet)
                
                # Group by connection IPs                
                connection_ip = packet.ip.dst if packet.ip.src == ip_address else packet.ip.src
                connection_groups[connection_ip].append(packet)
                
                # Determine sent or received packets
                if packet.ip.src == ip_address:
                    packets['sent'].append(packet)
                elif packet.ip.dst == ip_address:
                    packets['received'].append(packet)
            else:
                packets['non_related'].append(packet)

    return packets, connection_groups

def get_tcp_flags(flag_hex):
    # Convert hex to binary and pad with leading zeroes to 8 bits
    flag_bin = bin(int(flag_hex, 16))[2:].zfill(8)
    
    # Define flags according to their bit position
    flags = ['CWR', 'ECE', 'URG', 'ACK', 'PSH', 'RST', 'SYN', 'FIN']

    # Create a dictionary indicating whether each flag is set or not
    flag_dict = {flag: bool(int(flag_bin[bit])) for bit, flag in enumerate(reversed(flags))}

    return flag_dict

#!--------------------------------------------------------
def calculate_tcp_metrics(groups):
    tcp_metrics = {}

    for label, packets in groups.items():
        tcp_packets = [packet for packet in packets if 'TCP' in packet]
        tcp_packets_len = len(tcp_packets)
        tcp_proportion = len(tcp_packets) / len(packets) if len(packets) else 0

        round_trip_times = []
        psh_ack_delays = []
        seq_to_time = {}
        seq_to_count = defaultdict(int)
        highest_seq_seen = {}  
        total_retransmits = 0
        
        for packet in tcp_packets:            
            
            # Wireshark RTT
            try:
                # Note: This assumes the 'time_delta' field is available and can be converted to float.
                round_trip_times.append(float(packet.tcp.time_delta))
            except AttributeError:
                pass
                
            # PSH-ACK delay            
            flag_hex = packet.tcp.flags
            flags = get_tcp_flags(flag_hex)
            
            seq_num = int(packet.tcp.seq) # Assuming the seq is in packet.tcp.seq
            ack_num = int(packet.tcp.ack)
            tcp_conversation_key = f"{packet.tcp.srcport}:{packet.tcp.dstport}"
            packet_time = packet.sniff_timestamp
            
            try:
                # If this sequence number has been seen before and it's less than the highest sequence number seen for this connection, it's a retransmit
                if seq_to_count[seq_num] > 0 and seq_num < highest_seq_seen.get(tcp_conversation_key, (0, {}))[0] and flag_hex == highest_seq_seen[tcp_conversation_key][1]:
                    total_retransmits += 1

                seq_to_count[seq_num] += 1
                
                if seq_num > highest_seq_seen.get(tcp_conversation_key, (0, {}))[0]:
                    highest_seq_seen[tcp_conversation_key] = (seq_num, flag_hex)                
                
                if flags['ACK']:
                    
                    # this is not a pure ACK packet
                    non_pure_ack_flag = [flags[key] for key in flags if key != 'ACK']
                    
                    
                    if any(non_pure_ack_flag):
                        # headers sizes (Ethernet, IP, TCP) = (14, 20, 20)
                        seq_to_time[ack_num] = {'time': float(packet_time), 'seq': seq_num, 'payload': len(packet)-54}
                    
                    if seq_num in seq_to_time:
                        if ack_num == seq_to_time[seq_num]['seq'] + seq_to_time[seq_num]['payload']:
                            psh_ack_delay = float(packet_time) - seq_to_time[seq_num]['time']
                            psh_ack_delays.append(psh_ack_delay)
                            seq_to_time.pop(seq_num, None)
                            
                seq_to_time[ack_num] = {'time': float(packet_time), 'seq': seq_num, 'payload': len(packet)-54}
                        
            except AttributeError:
                pass            
            
                        
        avg_round_trip_time = np.mean(round_trip_times) if round_trip_times else 0
        avg_psh_ack_delay = np.mean(psh_ack_delays) if psh_ack_delays else 0
        proportion_no_psh_ack = len(seq_to_time) / len(tcp_packets) if tcp_packets else 0
        retransmission_rate = total_retransmits / len(tcp_packets) if tcp_packets else 0

        tcp_metrics[label] = {'tcp_proportion': tcp_proportion, 
                              'avg_round_trip_time': avg_round_trip_time, 
                              'avg_psh_ack_delay': avg_psh_ack_delay, 
                              'proportion_no_psh_ack': proportion_no_psh_ack,
                              'retransmission_rate': retransmission_rate}

    return tcp_metrics


avg_round_trip_times = []
avg_psh_ack_delays = []
tcp_proportions = []
proportions_no_psh_ack = []
retransmission_rates = []
loop_counter = 0

for packets in read_pcapng_file(CAPTURE_FILE):
    grouped_packets, groups = filter_packets(packets, SOURCE_IP)
    tcp_metrics = calculate_tcp_metrics(groups)

    for label, metrics in tcp_metrics.items():
        print(f"\n{label.capitalize()}:")
        if metrics['tcp_proportion'] > 0:            
            tcp_proportions.append((loop_counter, label, metrics['tcp_proportion']))
            print(f"TCP Proportion: {metrics['tcp_proportion'] * 100:.4f}%")
            avg_round_trip_times.append((loop_counter, label, metrics['avg_round_trip_time']))
            print(f"Average Round Trip Time: {metrics['avg_round_trip_time']:.4f} seconds")
            avg_psh_ack_delays.append((loop_counter, label, metrics['avg_psh_ack_delay']))
            print(f"Average PSH-ACK Delay: {metrics['avg_psh_ack_delay']:.4f} seconds")
            proportions_no_psh_ack.append((loop_counter, label, metrics['proportion_no_psh_ack']))
            print(f"Proportion of TCP packets without PSH-ACK delay: {metrics['proportion_no_psh_ack'] * 100:.4f}%")
            retransmission_rates.append((loop_counter, label, metrics['retransmission_rate']))
            print(f"Retransmission Rate: {metrics['retransmission_rate'] * 100:.4f}%")
    loop_counter += 1         
    print("------------------------------------------------------------------------------------------------")
        
# Create a dictionary to store the metrics
metrics_data = {
    'avg_round_trip_times': {'data': avg_round_trip_times, 'plot_type': 'line'},
    'avg_psh_ack_delays': {'data': avg_psh_ack_delays, 'plot_type': 'line'},
    'tcp_proportions': {'data': tcp_proportions, 'plot_type': 'bar'},
    'proportions_no_psh_ack': {'data': proportions_no_psh_ack, 'plot_type': 'bar'},
    'retransmission_rates': {'data': retransmission_rates, 'plot_type': 'bar'}
}


def plot_data(metric_name, data, xlabel, ylabel, title, plot_type='line'):
    plt.figure(figsize=(10, 6))
    labels = set(label for _, label, _ in data)
    
    if plot_type == 'line':
        for label in labels:
            x_vals = [x for x, lbl, _ in data if lbl == label]
            y_vals = [y for _, lbl, y in data if lbl == label]
            plt.plot(x_vals, y_vals, marker='o', label=f'{label} - {metric_name}')
    elif plot_type == 'bar':
        num_labels = len(labels)
        num_cycles = loop_counter
        index = np.arange(num_cycles)
        bar_width = 0.15
        for i, label in enumerate(labels):
            bar_vals = [val for _, lbl, val in data if lbl == label]
            plt.bar(index + i*bar_width, bar_vals, bar_width, label=f'{label} - {metric_name}')
    
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.show()

# Plotting the data
for metric_name, metric in metrics_data.items():
    plot_data(metric_name, metric['data'], 'Loop Cycle', 'Time (seconds)', 'TCP Metrics by Loop Cycle and IP Address', metric['plot_type'])