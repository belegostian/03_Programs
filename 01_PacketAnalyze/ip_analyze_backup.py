import pyshark
from collections import defaultdict
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
    related_packets = []
    non_related_packets = []
    sent_packets = []
    received_packets = []
    connection_groups = {}

    for packet in packet_list:
        # Checks if the packet is IP packet
        if 'IP' in packet:
            if packet.ip.src == ip_address or packet.ip.dst == ip_address:
                related_packets.append(packet)
                
                # Group by connection IPs
                connection_ip = packet.ip.dst if packet.ip.src == ip_address else packet.ip.src
                if connection_ip not in connection_groups:
                    connection_groups[connection_ip] = []
                connection_groups[connection_ip].append(packet)
                
                # Determine sent or received packets
                if packet.ip.src == ip_address:
                    sent_packets.append(packet)
                elif packet.ip.dst == ip_address:
                    received_packets.append(packet)
            else:
                non_related_packets.append(packet)

    return related_packets, non_related_packets, sent_packets, received_packets, connection_groups

def calculate_metrics(packet_list):
    total_bytes = 0
    total_packets = len(packet_list)

    for packet in packet_list:
        if 'IP' in packet:
            total_bytes += int(packet.length)

    if total_packets == 0:  # Avoid division by zero
        average_packet_size = 0
    else:
        average_packet_size = round(total_bytes / total_packets, 2)

    throughput = total_bytes / TIME_INTERVAL

    return throughput, average_packet_size

def accumulate_throughput(packets, throughput_dict, label, packet_count, max_count):
    throughput, average_packet_size = calculate_metrics(packets)
    if label not in throughput_dict:
        throughput_dict[label] = [0] * max_count
    throughput_dict[label][packet_count] = throughput
    return throughput_dict, throughput, average_packet_size



def plot_aggregated_throughput(throughput_dict):
    plt.figure(figsize=[10,6])
    bar_width = 0.35
    index = np.arange(len(throughput_dict['related']))
    plt.bar(index, throughput_dict['related'], bar_width, label='Related')
    plt.bar(index, throughput_dict['non_related'], bar_width, bottom=throughput_dict['related'], label='Non-related')
    plt.xlabel('Time intervals')
    plt.ylabel('Throughput (bytes/second)')
    plt.title('Total Throughput: Related vs Non-related')
    plt.legend()
    plt.show()

    plt.figure(figsize=[10,6])
    plt.bar(index, throughput_dict['sent'], bar_width, label='Sent')
    plt.bar(index, throughput_dict['received'], bar_width, bottom=throughput_dict['sent'], label='Received')
    plt.xlabel('Time intervals')
    plt.ylabel('Throughput (bytes/second)')
    plt.title('Total Throughput: Sent vs Received')
    plt.legend()
    plt.show()

def plot_top_ips(throughput_dict, top_n=5):
    # Identify top N IPs by total throughput
    ip_totals = {ip: sum(throughputs) for ip, throughputs in throughput_dict.items() if ip not in ['related', 'non_related', 'sent', 'received']}
    top_ips = sorted(ip_totals, key=ip_totals.get, reverse=True)[:top_n]

    # Plot
    plt.figure(figsize=[10,6])
    index = np.arange(len(throughput_dict['related']))
    bar_width = 0.35
    bottom = np.zeros(len(throughput_dict['related']))
    for ip in top_ips:
        plt.bar(index, throughput_dict[ip], bar_width, bottom=bottom, label=ip)
        bottom += np.array(throughput_dict[ip])

    plt.xlabel('Time intervals')
    plt.ylabel('Throughput (bytes/second)')
    plt.title(f'Total Throughput for Top {top_n} IPs')
    plt.legend()
    plt.show()


max_count = sum(1 for _ in read_pcapng_file(CAPTURE_FILE))
throughput_dict = {}
packet_count = 0

for packets in read_pcapng_file(CAPTURE_FILE):
    related, non_related, sent, received, groups = filter_packets(packets, SOURCE_IP)
    
    throughput_dict, throughput0, average_packet_size = accumulate_throughput(related, throughput_dict, 'related', packet_count, max_count)
    print(f"Related: \nThroughput: {throughput0} bytes/second; Average packet size: {average_packet_size} bytes; Transmit frequency: {len(related)/TIME_INTERVAL}")
    throughput_dict, throughput, average_packet_size = accumulate_throughput(non_related, throughput_dict, 'non_related', packet_count, max_count)
    print(f"Non-related: \nThroughput: {throughput} bytes/second; Average packet size: {average_packet_size} bytes; Transmit frequency: {len(non_related)/TIME_INTERVAL}")
    throughput_dict, throughput, average_packet_size = accumulate_throughput(sent, throughput_dict, 'sent', packet_count, max_count)
    print(f"Sent: \nThroughput: {throughput} bytes/second; Average packet size: {average_packet_size} bytes; Transmit frequency: {len(sent)/TIME_INTERVAL}")
    throughput_dict, throughput, average_packet_size = accumulate_throughput(received, throughput_dict, 'received', packet_count, max_count)
    print(f"Received: \nThroughput: {throughput} bytes/second; Average packet size: {average_packet_size} bytes; Transmit frequency: {len(received)/TIME_INTERVAL}")
    
    for ip, group_packets in groups.items():
        throughput_dict, throughput, average_packet_size = accumulate_throughput(group_packets, throughput_dict, ip, packet_count, max_count)
        print(f"Connection IP: {ip}; Proportion: {round(throughput/throughput0, 2)}")
    packet_count += 1
        
plot_aggregated_throughput(throughput_dict)
plot_top_ips(throughput_dict, top_n=5)