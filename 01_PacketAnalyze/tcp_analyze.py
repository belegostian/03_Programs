import pyshark
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import numpy as np

SOURCE_IP = '192.168.3.107'
CAPTURE_FILE = 'packets\HOMGE1.pcapng'
TIME_INTERVAL = 10

def read_pcapng_file(filename):
    cap = pyshark.FileCapture(filename, keep_packets=True)

    packet_list = []
    start_time = None
    for packet in cap:
        if start_time is None:
            start_time = packet.sniff_time.timestamp()
            end_time = start_time + 10  # 10 seconds later

        if packet.sniff_time.timestamp() <= end_time:
            packet_list.append(packet)
        else:
            yield packet_list

            packet_list = [packet]
            start_time = packet.sniff_time.timestamp()
            end_time = start_time + 10

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

def calculate_tcp_metrics(groups):
    tcp_metrics = {}

    for label, packets in groups.items():
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
                # This packet doesn't have a 'time_delta' field
                pass
                
            # PSH-ACK delay
            seq_num = int(packet.tcp.seq) # Assuming the seq is in packet.tcp.seq
            ack_num = int(packet.tcp.ack) # Assuming the ack is in packet.tcp.ack
            tcp_conversation_key = f"{packet.tcp.srcport}:{packet.tcp.dstport}"
            packet_time = packet.sniff_timestamp
            flags = get_tcp_flags(packet.tcp.flags)
            
            try:
                # If this sequence number has been seen before and it's less than the highest sequence number seen for this connection, it's a retransmit
                if seq_to_count[seq_num] > 0 and seq_num < highest_seq_seen.get(tcp_conversation_key, (0, {}))[0] \
                    and packet.tcp.flags == highest_seq_seen[tcp_conversation_key][1]:
                    total_retransmits += 1

                seq_to_count[seq_num] += 1
                
                if seq_num > highest_seq_seen.get(tcp_conversation_key, (0, {}))[0]:
                    highest_seq_seen[tcp_conversation_key] = (seq_num, packet.tcp.flags)                
                
                if flags['ACK']:
                    
                    # this is not a pure ACK packet
                    if any(flags[key] for key in flags if key != 'ACK'):
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
loop_counter = 0
tcp_proportions = []
proportions_no_psh_ack = []
retransmission_rates = []

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
        
# Create line plots for Average PSH-ACK Delay and Average Round Trip Time
plt.figure(figsize=(10, 6))

for label in set(label for _, label, _ in avg_round_trip_times):
    x_vals = [x for x, lbl, _ in avg_round_trip_times if lbl == label]
    y_vals = [y for _, lbl, y in avg_round_trip_times if lbl == label]
    plt.plot(x_vals, y_vals, marker='o', label=f'{label} - Avg Round Trip Time')

for label in set(label for _, label, _ in avg_psh_ack_delays):
    x_vals = [x for x, lbl, _ in avg_psh_ack_delays if lbl == label]
    y_vals = [y for _, lbl, y in avg_psh_ack_delays if lbl == label]
    plt.plot(x_vals, y_vals, marker='o', label=f'{label} - Avg PSH-ACK Delay')

plt.xlabel('Loop Cycle')
plt.ylabel('Time (seconds)')
plt.title('TCP Metrics by Loop Cycle and IP Address')
plt.legend()
plt.show()



labels = sorted(set(label for _, label, _ in tcp_proportions))

num_labels = len(labels)
num_cycles = loop_counter

index = np.arange(num_cycles)
bar_width = 0.15  # Smaller value for narrower bars
spacing = 0.2  # Additional spacing between groups

fig, ax = plt.subplots()

# We'll group the bars for each label in each cycle
for i, label in enumerate(labels):
    # tcp_proportion_vals = [val for _, lbl, val in tcp_proportions if lbl == label]
    # ax.bar(index + i*bar_width, tcp_proportion_vals, bar_width, label=f'{label} - TCP Proportion')

    proportion_no_psh_ack_vals = [val for _, lbl, val in proportions_no_psh_ack if lbl == label]
    ax.bar(index + (i+1)*bar_width, proportion_no_psh_ack_vals, bar_width, label=f'{label} - Proportion No PSH-ACK')

    retransmission_rate_vals = [val for _, lbl, val in retransmission_rates if lbl == label]
    ax.bar(index + (i+2)*bar_width, retransmission_rate_vals, bar_width, label=f'{label} - Retransmission Rate')

ax.set_xlabel('Loop Cycle')
ax.set_ylabel('Proportion')
ax.set_title('TCP Metrics by Loop Cycle and IP Address')
ax.legend()

plt.show()