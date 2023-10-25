import pyshark
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import numpy as np
import logging

SERVER_IP = '10.0.0.252'                                                # (string): 伺服器/主機IP
CAPTURE_FILE = 'Mininet_Traffic_Capture\Container_test_topo.pcapng'     # (string): 擷取封包檔案路徑
TIME_INTERVAL = 10                                                      # (int): 數據平均的時間間隔 -秒

def update_time_interval(packet, start_time, end_time):
    """_summary_
    
    輔助函式，用來更新 read_pcapng_file 時間區間
    """
    start_time = packet.sniff_time.timestamp()
    end_time = start_time + TIME_INTERVAL
    return start_time, end_time

def read_pcapng_file():
    """_summary_
    批次取得時間間隔內的封包物件

    Yields:
        [packet_object]: 時間間隔內的封包物件
    """
    with pyshark.FileCapture(CAPTURE_FILE, keep_packets=True) as cap:
        packet_list = []
        start_time, end_time = None, None
        for packet in cap:
            if start_time is None:
                start_time, end_time = update_time_interval(packet, start_time, end_time)

            packet_time = packet.sniff_time.timestamp()
            if packet_time <= end_time:
                if 'IP' in packet:
                    packet_list.append(packet)
            else:
                yield packet_list
                packet_list = [packet]
                start_time, end_time = update_time_interval(packet, start_time, end_time)

        if packet_list:
            yield packet_list

def classify_packets(packet_list):
    """_summary_
    依照 session/訂閱關係 做分類

    Args:
        packet_list [packet_object]: 時間間隔內的封包物件

    Returns:
        defaultdict(dict([packet_object])): 依照 session/訂閱關係 做分類的封包物件, 第一層key為client_ip, 第二層key為server_port
    """
    classified_packets = defaultdict(lambda: defaultdict(list)) # 結構為 {client_ip: {server_port: [packet1, packet2, ...], ...}, ...}
    classified_packets['background'] = []
    
    for packet in packet_list:
        try: # 其實這裡嘗試抓取封包的src_port, dst_port就預設了留下來的封包走TCP/UDP協定
            src_ip = packet.ip.src
            dst_ip = packet.ip.dst
            src_port = packet[packet.transport_layer].srcport
            dst_port = packet[packet.transport_layer].dstport
        except AttributeError: # 目前已知ARP,ICMP等控制封包會觸發，至於有沒有行為是unicast但不基於TCP/UDP的封包，還沒有遇到
            classified_packets['background'].append(packet)
            continue

        if src_ip == SERVER_IP or dst_ip == SERVER_IP:
            client_ip = dst_ip if src_ip == SERVER_IP else src_ip
            server_port = src_port if src_ip == SERVER_IP else dst_port
            classified_packets[client_ip][server_port].append(packet)
        else:
            classified_packets['background'].append(packet)

    return classified_packets

def unilateral_metrics(packet_list):
    """_summary_
    計算單向通訊指標: 平均單包吞吐量、平均總吞吐量、平均發送頻率

    Args:
        packet_list [packet_object]: 時間間隔內、同一個session的封包物件

    Returns:
        defaultdict(dict): 通訊指標*2 (請求/回應)
    """
    request_group = []
    response_group = []
    
    for packet in packet_list:
        src_ip = packet.ip.src
        dst_ip = packet.ip.dst

        if src_ip == SERVER_IP:
            response_group.append(packet)
        elif dst_ip == SERVER_IP:
            request_group.append(packet)
            
    def calculate(group):
        total_bytes = sum(int(packet.length) for packet in group)
        total_packets = len(group)
        
        avg_load = 0 if total_packets == 0 else round(total_bytes / total_packets, 2)
        avg_throughput = total_bytes / TIME_INTERVAL if TIME_INTERVAL else 0
        avg_frequency = total_packets / TIME_INTERVAL if TIME_INTERVAL else 0
        
        return avg_load, avg_throughput, avg_frequency
    
    req_avg_load, req_avg_throughput, req_avg_frequency = calculate(request_group)
    rep_avg_load, rep_avg_throughput, rep_avg_frequency = calculate(response_group)
    
    u_metrics = {
        'request': {'avg_load': req_avg_load, 'avg_throughput': req_avg_throughput, 'avg_frequency': req_avg_frequency},
        'response': {'avg_load': rep_avg_load, 'avg_throughput': rep_avg_throughput, 'avg_frequency': rep_avg_frequency}
    }
    
    return u_metrics

def main():
    
    # 讀取封包
    packet_lists = read_pcapng_file()
    
    
    for packet_list in packet_lists:
        
        # 讀取封包 -測試
        # logging.info(f'New Time Interval: Packets={len(packet_list)}')
        # for packet in packet_list:
        #     logging.debug(f'Packet Sniff Time: {packet.sniff_time}')
        #     logging.debug(f'Packet Length: {len(packet)} bytes')
        # logging.info('---')
        
        classified_packets = classify_packets(packet_list)
        
        # 分類封包 -測試        
        # for key, value in classified_packets.items():
        #     if key != 'background':
        #         for sub_key, sub_value in value.items():
        #             logging.info(f"For Client IP: {key}, Server Port: {sub_key}")
        #             for i, packet in enumerate(sub_value[:5]):
        #                 logging.info(f'{packet.ip.src}:{packet[packet.transport_layer].srcport} -> {packet.ip.dst}:{packet[packet.transport_layer].dstport}')
        #     logging.info('---')
        
        throughput_dict = defaultdict(dict)
        for key, value in classified_packets.items(): # key為client_ip, value為{server_port: [packet1, packet2, ...], ...}
            if key != 'background':
                for sub_key, sub_value in value.items(): # sub_key為server_port, sub_value為[packet1, packet2, ...]
                    u_metrics = unilateral_metrics(sub_value)
                    
                    if key not in throughput_dict:
                        throughput_dict[key] = {}
                        
                    throughput_dict[key][sub_key] = u_metrics
                    
                    # 計算單向通訊指標 -測試
                    # logging.info(f'Client IP: {key}, Server Port: {sub_key}')
                    # logging.info(f'Request: {u_metrics["request"]}')
                    # logging.info(f'Response: {u_metrics["response"]}')
                    # logging.info('---')
        
        
        
        
        

            
if __name__ == "__main__":
    
    # 方便觀察程式回饋
    logging.basicConfig(level=logging.INFO)    
    main() 