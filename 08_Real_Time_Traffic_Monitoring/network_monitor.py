import time
from collections import defaultdict

import numpy as np
import pyshark

def capture_packets(target_ip, target_port, capture_time=5, interface='Wi-Fi', output_file='C:/Users/IAN/Dropbox/NTU/02_研究/03_programs/03_CommunicationMonitoring/captured.pcapng'):
    capture = pyshark.LiveCapture(interface, display_filter=f"ip.addr == {target_ip} && tcp.port == {target_port}") # , output_file=output_file)
    start_time = time.time()
    return [(packet, time.time() - start_time) for packet in capture.sniff_continuously(packet_count=200) if time.time() - start_time <= capture_time]

def filter_and_group_packets(all_packets):
    interval_packets = defaultdict(list)
    for packet, elapsed_time in all_packets:
        interval_packets[int(elapsed_time)].append(packet)

    interval_ip_port_packets = {}
    for interval, packets in interval_packets.items():
        ip_port_packets = defaultdict(list)
        for packet in packets:
            src_ip_port = (packet.ip.src, packet[packet.transport_layer].srcport)
            dest_ip_port = (packet.ip.dst, packet[packet.transport_layer].dstport)
            ip_port_key = frozenset([src_ip_port, dest_ip_port])
            ip_port_packets[ip_port_key].append(packet)
        interval_ip_port_packets[interval] = ip_port_packets
    return interval_ip_port_packets

def get_tcp_flags(flag_hex):
    flag_bin = bin(int(flag_hex, 16))[2:].zfill(8)
    flags = ['CWR', 'ECE', 'URG', 'ACK', 'PSH', 'RST', 'SYN', 'FIN']
    return {flag: bool(int(flag_bin[bit])) for bit, flag in enumerate(reversed(flags))}

def calculate_tcp_metrics(groups):
    tcp_metrics = {}
    for label, packets in groups.items():
        tcp_packets = [packet for packet in packets if 'TCP' in packet]

        psh_ack_delays = []
        seq_to_time = {}
        seq_to_count = defaultdict(int)
        highest_seq_seen = {}  
        total_retransmits = 0
        
        for packet in tcp_packets:
                
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
                        if ack_num == seq_to_time[seq_num]['seq'] + seq_to_time[seq_num]['payload'] + 10: #! +10
                            psh_ack_delay = float(packet_time) - seq_to_time[seq_num]['time']
                            psh_ack_delays.append(psh_ack_delay)
                            seq_to_time.pop(seq_num, None)
                            
                seq_to_time[ack_num] = {'time': float(packet_time), 'seq': seq_num, 'payload': len(packet)-54}
                        
            except AttributeError:
                pass
                        
        # Remove 2 smallest and 2 largest values
        psh_ack_delays = sorted(psh_ack_delays)
        if len(psh_ack_delays) >= 4:
            psh_ack_delays = psh_ack_delays[2:-2]
        
        avg_psh_ack_delay = np.mean(psh_ack_delays) if psh_ack_delays else 0
        std_psh_ack_delay = np.std(psh_ack_delays) if psh_ack_delays else 0
        retransmission_rate = total_retransmits / len(tcp_packets) if tcp_packets else 0

        tcp_metrics[label] = {'Average PSH-ACK delay': avg_psh_ack_delay,
                              'Standard Deviation of PSH-ACK delay': std_psh_ack_delay,
                              'Retransmission rate': retransmission_rate}
    return tcp_metrics

if __name__ == "__main__":
    last_ten_metrics = []
    
    while True:
        all_packets = capture_packets("192.168.50.85", "443", capture_time=2)
        interval_ip_port_packets = filter_and_group_packets(all_packets)
        
        all_metrics = {}
        for interval, ip_port_packets in interval_ip_port_packets.items():
            metrics = calculate_tcp_metrics(ip_port_packets)
            all_metrics[interval] = metrics

        # Add the newest metrics to the last_ten_metrics list
        last_ten_metrics.append(all_metrics)

        # Trim last_ten_metrics to keep only the last 10 elements
        if len(last_ten_metrics) > 10:
            last_ten_metrics.pop(0)

        # If enough metrics are available, check for alarms
        if len(last_ten_metrics) >= 10:
            psh_ack_delays = [metrics.get(interval, {}).get(ip_port_pair, {}).get('Average PSH-ACK delay', 0)
                              for metrics in last_ten_metrics[:-1]
                              for interval, ip_port_group in metrics.items()
                              for ip_port_pair in ip_port_group]
            std_of_last_9 = np.std(psh_ack_delays) if psh_ack_delays else 0
            print("\n\n")
            print(std_of_last_9)
            
            last_metric = last_ten_metrics[-1]
            print(last_metric)
            second_last_metric = last_ten_metrics[-2]
            
            # Assuming you'd like to check the same interval and ip_port_pair
            for interval in last_metric.keys():
                for ip_port_pair in last_metric[interval].keys():
                    last_value = last_metric[interval][ip_port_pair].get('Average PSH-ACK delay', 0)
                    second_last_value = second_last_metric.get(interval, {}).get(ip_port_pair, {}).get('Average PSH-ACK delay', 0)
                    if abs(last_value - second_last_value) > std_of_last_9:
                        print("Alarm")