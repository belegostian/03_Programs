from pyshark import LiveCapture
import time
import numpy as np

"""
已知未解問題：
1. OPC 的 header bytes 計算上會少 10 bytes
2. 封包抓取存入.pcap file的會少0.5秒 留在程式變數中傳遞的又在少0.5秒
3. 分析模組對大部分的手寫通訊應用有效 但抓一般網路封包時常失效
4. 重送分析模組的有效性仍待驗證
5. 閥值可以再調整

尚未完成部分:
1. 告警條件
2. 回饋機制
    
"""

def capture_packets(capture_interface, ip, port, capture_duration, output_file):
    # capture filter
    bpf_filter = f'host {ip} and tcp port {port}'

    # Initialize capture with the output_file parameter
    capture = LiveCapture(interface=capture_interface, bpf_filter=bpf_filter, output_file=output_file) #! only_summaries=True may be useful
    
    # Start capturing packets
    print("Capturing packets...")
    start_time = time.time()
    capture.sniff(timeout=capture_duration, packet_count=200) #! mostly 60~70 packets are captured
    packets = capture._packets
    capture.close()
    print(f"Capture duration: {time.time() - start_time} seconds \nCapture complete. Packets saved to {output_file}")
    
    return packets

def group_packets_info(packet_list, ip, port):
    grouped_packets = {}
    
    for packet in packet_list:
        src_ip = packet.ip.src
        src_port = packet[packet.transport_layer].srcport
        dst_ip = packet.ip.dst
        dst_port = packet[packet.transport_layer].dstport
        
        # classify packets by connect IP-Port
        if (src_ip, src_port) == (ip, port):
            key = (dst_ip, dst_port)
            direction = 'sending'
        else:
            key = (src_ip, src_port)
            direction = 'receiving'
            
        if key not in grouped_packets:
            grouped_packets[key] = []
        
        # extract packet info    
        timestamp = packet.sniff_time.timestamp()
        seq_num = int(packet.tcp.seq)
        ack_num = int(packet.tcp.ack)
        length = len(packet)
        
        if hasattr(packet.tcp, 'payload'): 
            data = packet.tcp.payload
            data = data.replace(':', '')
            try:
                data = bytes.fromhex(data).decode('ascii', errors='ignore')
            except ValueError:
                data = "Error decoding payload"
        else:
            data = None
        
        packet_info = {
            'timestamp': timestamp,
            'SEQ_num': seq_num,
            'ACK_num': ack_num,
            'direction': direction,
            'flags': get_tcp_flags(packet.tcp.flags),
            'length': length,
            'data': data
        }
        
        grouped_packets[key].append(packet_info)
        
    return grouped_packets

def get_tcp_flags(flag_hex):
    flag_bin = bin(int(flag_hex, 16))[2:].zfill(8)
    flags = ['CWR', 'ECE', 'URG', 'ACK', 'PSH', 'RST', 'SYN', 'FIN']
    return {flag: bool(int(flag_bin[bit])) for bit, flag in enumerate(reversed(flags))}

def remove_outliers(data_list):
    mean = np.mean(data_list)
    std_dev = np.std(data_list)
    upper_threshold = mean + 3 * std_dev
    lower_threshold = mean - 3 * std_dev
    
    filtered_list = [x for x in data_list if x <= upper_threshold and x >= lower_threshold]
    return filtered_list

def tcp_metrics(g_packets):
    metrics = {}
    for key, packets in g_packets.items():
        retransmit_count = 0
        psh_ack_delays = []
        
        known_seq_nums = set()
        highest_seq = {'sending': (-1, None), 'receiving': (-1, None)}
        seq_time_pairs = {'seq_num': None} # {seq_num: {'time': float(packet_time), 'seq': seq_num, 'payload': len(packet)-54}}
        
        for packet_info in packets:
            timestamp = packet_info['timestamp']
            seq_num = packet_info['SEQ_num']
            ack_num = packet_info['ACK_num']
            direction = packet_info['direction']
            flags = packet_info['flags']
            length = packet_info['length']
            
            # If this sequence number has been seen before and it's less than the highest sequence number seen for this connection, it's a retransmit
            if seq_num in known_seq_nums and seq_num < highest_seq[direction][0] and flags == highest_seq[direction][1]:
                retransmit_count += 1
            
            known_seq_nums.add(seq_num)
            if seq_num > highest_seq[direction][0]:
                highest_seq[direction] = (seq_num, flags)
            
            # If this is an ACK packet, calculate the PSH-ACK delay
            if flags['ACK']:
                
                if seq_num in seq_time_pairs:
                    if ack_num == seq_time_pairs[seq_num]['seq'] + seq_time_pairs[seq_num]['payload']:
                        psh_ack_delay = timestamp - seq_time_pairs[seq_num]['timestamp']
                        psh_ack_delays.append(psh_ack_delay)
                        
                        # this packet has been responded
                        seq_time_pairs.pop(seq_num, None)
                
                # If this is a pure ACK packet, it will not have an ACK packet later
                if sum(flags.values()) == 1:
                    break
            
            # else, the ACK num of the last packet will be the SEQ num of it's response packet
            seq_time_pairs[ack_num] = {'timestamp': timestamp, 'seq': seq_num, 'payload': length-44} # headers size (Ethernet, IP, TCP) = (14, 20, 20)
            
        psh_ack_delays = remove_outliers(psh_ack_delays)
        
        avg_psh_ack_delay = np.mean(psh_ack_delays) if psh_ack_delays else 0
        std_psh_ack_delay = np.std(psh_ack_delays) if psh_ack_delays else 0
        retransmit_rate = retransmit_count / len(packets)
        
        metrics[key] = {
            'avg_psh_ack_delay': avg_psh_ack_delay,
            'std_psh_ack_delay': std_psh_ack_delay,
            'retransmit_rate': retransmit_rate
        }
        
    return metrics

if __name__ == '__main__':
    # Configure capture settings
    capture_interface = 'Adapter for loopback traffic capture'
    ip = '127.0.0.1'
    port = '4840'
    capture_duration = 5 #! file stored packets are missing 0.5 sec; returned packets are missing 1 sec
    output_file = 'OPC_captured_packets.pcap'
    
    # for Wi-Fi / 乙太網路 traffic
    # capture_interface = '乙太網路'
    # ip = '192.168.1.188'
    # capture_interface = 'Wi-Fi'
    # ip = '192.168.50.85'
    # port = '443'
    # capture_duration = 20
    # output_file = 'WiFi_captured_packets.pcap'
    
    metrics_history = []
    
    while True:
        # Capture packets
        c_packets = capture_packets(capture_interface, ip, port, capture_duration, output_file)
        
        # Group & extract packet's data
        g_packets = group_packets_info(c_packets, ip, port)
        
        # Calculate TCP metrics
        metrics = tcp_metrics(g_packets)
        
        # Append the latest metrics and ensure the history only contains the latest 6 records
        metrics_history.append(metrics)
        if len(metrics_history) > 6:
            metrics_history.pop(0)
            
        # Evaluate the metrics history for warnings and alarms
        if len(metrics_history) >= 2:  # Ensure there are at least two records to compare
            latest_metrics = metrics_history[-1]
            first_metrics = metrics_history[0]

            for key in latest_metrics.keys():
                mean_diff = latest_metrics[key]['avg_psh_ack_delay'] - metrics_history[-2][key]['avg_psh_ack_delay']
                std_diff = metrics_history[-2][key]['std_psh_ack_delay']

                if mean_diff > std_diff:
                    print(f"Warning for {key}: PSH-ACK delay increased by more than 1 sigma")

                if len(metrics_history) >= 5 and latest_metrics[key]['avg_psh_ack_delay'] - first_metrics[key]['avg_psh_ack_delay'] > 2 * std_diff:
                    print(f"Warning for {key}: Latest PSH-ACK delay increased by more than 2 sigma compared to the 1st record")

                if mean_diff > 2 * std_diff:
                    print(f"Alarm for {key}: PSH-ACK delay increased by more than 2 sigma")

                if len(metrics_history) >= 5 and latest_metrics[key]['avg_psh_ack_delay'] - first_metrics[key]['avg_psh_ack_delay'] > 3 * std_diff:
                    print(f"Alarm for {key}: Latest PSH-ACK delay increased by more than 3 sigma compared to the 1st record")
    
        # for key, packets in g_packets.items():
        #     print(f"Connected IP-Port: {key}")
        #     print("-" * 40)
            
        #     for i, packet_info in enumerate(packets):
        #         print(f"Packet {i+1}:")
        #         print(f"\tTimestamp: {packet_info['timestamp']}")
        #         print(f"\tPSH Number: {packet_info['SEQ_num']}")
        #         print(f"\tACK Number: {packet_info['ACK_num']}")
        #         print(f"\tPacket Length: {packet_info['length']}")
        #         print(f"\tData: {packet_info['data']}")
            
        #     print("=" * 40)

        for key, metric in metrics.items():
            print(f"Connected IP-Port: {key}")
            print("-" * 40)
            print(f"Average PSH-ACK delay: {metric['avg_psh_ack_delay']} sec")
            print(f"Standard Deviation of PSH-ACK delay: {metric['std_psh_ack_delay']} sec")
            print(f"Retransmission rate: {metric['retransmit_rate']} %")
            print("=" * 40)