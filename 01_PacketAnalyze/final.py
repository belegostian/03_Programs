import pyshark
from collections import defaultdict, Counter
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
                if 'IP' in packet:
                    packet_list.append(packet)
            else:
                yield packet_list

                packet_list = [packet]
                start_time = packet.sniff_time.timestamp()
                end_time = start_time + TIME_INTERVAL

        if packet_list:
            yield packet_list
            
def filter_target_ips_packets(packets, ip_address):
    
    # classify by traffic behavior
    classified_packets = defaultdict(list)
    # group by connect-IP
    grouped_packets = defaultdict(list)

    for packet in packets:
        try:
            if packet.ip.src == ip_address or packet.ip.dst == ip_address:
                classified_packets['related'].append(packet)
                
                # Group by connection IPs                
                connection_ip = packet.ip.dst if packet.ip.src == ip_address else packet.ip.src
                grouped_packets[connection_ip].append(packet)
                
                # Determine sent or received packets
                if packet.ip.src == ip_address:
                    classified_packets['sent'].append(packet)
                elif packet.ip.dst == ip_address:
                    classified_packets['received'].append(packet)
            else:
                classified_packets['non_related'].append(packet)
                
        except AttributeError:
            #! Known condition: ARP packet
            classified_packets['non_related'].append(packet)
            

    return classified_packets, grouped_packets

def calculate_ip_basic_metrics(packet_list, throughput_dict, label, packet_count):
    total_bytes = sum(int(packet.length) for packet in packet_list)
    total_packets = len(packet_list)

    average_packet_size = round(total_bytes / total_packets, 2) if total_packets else 0
    throughput = total_bytes / TIME_INTERVAL
    
    throughput_dict[label][packet_count] = throughput

    return throughput, average_packet_size

def get_tcp_flags(flag_hex):
    # Convert hex to binary and pad with leading zeroes to 8 bits
    flag_bin = bin(int(flag_hex, 16))[2:].zfill(8)
    
    # Define flags according to their bit position
    flags = ['CWR', 'ECE', 'URG', 'ACK', 'PSH', 'RST', 'SYN', 'FIN']
    flag_dict = {flag: bool(int(flag_bin[bit])) for bit, flag in enumerate(reversed(flags))}

    return flag_dict

def calculate_tcp_metrics(grouped_packets):
    tcp_metrics = {}

    for label, packets in grouped_packets.items():
        tcp_packets = [packet for packet in packets if 'TCP' in packet]
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
                #! Known error if tcp_conversation_key haven't been stored in highest_seq_seen; moving 'if...(0, {}))[0]:' to front may help
                if seq_to_count[seq_num] > 0 and seq_num <= highest_seq_seen.get(tcp_conversation_key, (0, {}))[0] and flag_hex == highest_seq_seen[tcp_conversation_key][1]:
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


def plot_chart(data, chart_type, xlabel, ylabel, title, stacked=False):
    plt.figure(figsize=(10, 6))

    if chart_type == 'line':
        for label, values in data.items():
            plt.plot(values, marker='o', label=label)

    elif chart_type == 'bar':
        index = np.arange(len(next(iter(data.values())))) # gets the length of values list
        bar_width = 0.35

        if stacked:
            bottom = np.zeros(len(next(iter(data.values()))))
            for label, values in data.items():
                plt.bar(index, values, bar_width, bottom=bottom, label=label)
                bottom += np.array(values)
        else:
            for i, (label, values) in enumerate(data.items()):
                #! known error if IP count isn't the same in each loop
                plt.bar(index + i*bar_width, values, bar_width, label=label)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.show()

loop_counter = 0

max_count = sum(1 for _ in read_pcapng_file(CAPTURE_FILE))
throughput_dict = defaultdict(lambda: [0] * max_count)

# avg_round_trip_times = []
# avg_psh_ack_delays = []
tcp_proportions = []
proportions_no_psh_ack = []
retransmission_rates = []

# tcp_metrics stores data in a single loop; tcp_metrics_dict stores data of a full file
tcp_metrics_dict = {
    'avg_round_trip_times': {'data': [], 'plot_type': 'line'},
    'avg_psh_ack_delays': {'data': [], 'plot_type': 'line'},
    'tcp_proportions': {'data': [], 'plot_type': 'bar'},
    'proportions_no_psh_ack': {'data': [], 'plot_type': 'bar'},
    'retransmission_rates': {'data': [], 'plot_type': 'bar'}
}

for packets in read_pcapng_file(CAPTURE_FILE):
    classified_packets, grouped_packets = filter_target_ips_packets(packets, SOURCE_IP)
    tcp_metrics = calculate_tcp_metrics(grouped_packets)
    
    # basic IP packets analyze
    for label, packet_list in classified_packets.items():
        throughput, average_packet_size = calculate_ip_basic_metrics(packet_list, throughput_dict, label, loop_counter)
        #? print(f"{label.capitalize()}: \nThroughput: {throughput} bytes/second; Average packet size: {average_packet_size} bytes; Transmit frequency: {len(packet_list)/TIME_INTERVAL}")
        
        if label == 'related':
            related_throughput = throughput
            for ip, packet_list in grouped_packets.items():
                throughput, average_packet_size = calculate_ip_basic_metrics(packet_list, throughput_dict, ip, loop_counter)
                #? print(f"Connection IP: {ip}; Proportion: {round(throughput/related_throughput, 2)}")
    
    # TCP packets analyze
    for label, metrics in tcp_metrics.items():
        print(f"\n{label.capitalize()}:")
        
        if metrics['tcp_proportion'] > 0:            
            tcp_metrics_dict['tcp_proportions']['data'].append((loop_counter, label, metrics['tcp_proportion']))
            tcp_metrics_dict['avg_round_trip_times']['data'].append((loop_counter, label, metrics['avg_round_trip_time']))
            tcp_metrics_dict['avg_psh_ack_delays']['data'].append((loop_counter, label, metrics['avg_psh_ack_delay']))
            tcp_metrics_dict['proportions_no_psh_ack']['data'].append((loop_counter, label, metrics['proportion_no_psh_ack']))
            tcp_metrics_dict['retransmission_rates']['data'].append((loop_counter, label, metrics['retransmission_rate']))
            
            print(f"TCP Proportion: {metrics['tcp_proportion'] * 100:.4f}%")
            print(f"Average Round Trip Time: {metrics['avg_round_trip_time']:.4f} seconds")
            print(f"Average PSH-ACK Delay: {metrics['avg_psh_ack_delay']:.4f} seconds")
            print(f"Proportion of TCP packets without PSH-ACK delay: {metrics['proportion_no_psh_ack'] * 100:.4f}%")
            print(f"Retransmission Rate: {metrics['retransmission_rate'] * 100:.4f}%")
            
            
                
    loop_counter += 1
    print("------------------------------------------------------------------------------------------------\n")
    
# For classified throughput
plot_chart({label: throughput_dict[label] for label in ['related', 'non_related']}, 'bar', 'Time intervals', 'Throughput (bytes/second)', 'Total Throughput: Related vs Non-related', True)
plot_chart({label: throughput_dict[label] for label in ['sent', 'received']}, 'bar', 'Time intervals', 'Throughput (bytes/second)', 'Total Throughput: Sent vs Received', True)

# For top connection IPs throughput
ip_totals = {ip: sum(throughputs) for ip, throughputs in throughput_dict.items() if ip not in ['related', 'non_related', 'sent', 'received']}
top_ips = sorted(ip_totals, key=ip_totals.get, reverse=True)[:5]
top_ips_dict = {ip: throughput_dict[ip] for ip in top_ips}
plot_chart(top_ips_dict, 'bar', 'Time intervals', 'Throughput (bytes/second)', 'Total Throughput for Top 5 IPs', True)

# For TCP Metrics
processed_data = {}
for key, values in tcp_metrics_dict.items():
    data = values['data']
    chart_type = values['plot_type']
    processed_data[key] = {}
    labels = set([item[1] for item in data])
    for label in labels:
        processed_data[key][label] = [item[2] for item in data if item[1] == label]
for key, data in processed_data.items():
    chart_type = tcp_metrics_dict[key]['plot_type']
    plot_chart(data, chart_type, "Loop Count", "Value", key, stacked=False)