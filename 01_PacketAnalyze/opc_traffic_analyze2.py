import pyshark
from collections import defaultdict, Counter
import matplotlib.pyplot as plt
import numpy as np
import logging

SERVER_IP = '10.0.0.252'                                                # (string): 伺服器/主機IP
EXPECTED_SESSION_COUNT = 4                                                         # (int): 伺服器/主機同時處理的session數量
CAPTURE_FILE = 'Traffic_Capture (Mininet)\Container_test_topo.pcapng'     # (string): 擷取封包檔案路徑
TIME_INTERVAL = 1                                                     # (int): 數據平均的時間間隔 -秒

# PART 1: 依照時間間隔取得封包物件
def update_time_interval(packet, start_time, end_time):
    """輔助函式, 更新 read_pcapng_file 時間區間
    """
    start_time = packet.sniff_time.timestamp()
    end_time = start_time + TIME_INTERVAL
    return start_time, end_time

def read_pcapng_file():
    """批次取得時間間隔內的封包物件

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

# PART 2: 依照 session/訂閱關係 做分類
def initial_packet_grouping(packet_list):
    grouped_packets = {'background': []}
    
    for packet in packet_list:
        try: # 其實這裡嘗試抓取封包的src_port, dst_port就預設了留下來的封包走TCP/UDP協定
            src_ip = packet.ip.src
            dst_ip = packet.ip.dst
            src_port = packet[packet.transport_layer].srcport
            dst_port = packet[packet.transport_layer].dstport
        except AttributeError: # 目前已知ARP,ICMP等控制封包會觸發，至於有沒有行為是unicast但不基於TCP/UDP的封包，還沒有遇到
            grouped_packets['background'].append(packet)
            continue

        if src_ip == SERVER_IP or dst_ip == SERVER_IP:
            client_ip = dst_ip if src_ip == SERVER_IP else src_ip
            client_port = dst_port if src_ip == SERVER_IP else src_port
            group_key = f"{client_ip}-{client_port}"
            
            if group_key not in grouped_packets:
                grouped_packets[group_key] = []
                
            grouped_packets[group_key].append(packet)
        else:
            grouped_packets['background'].append(packet)
            
    return grouped_packets

def collect_grouped_packets_info(grouped_packets):
    """輔助函式, 紀錄每個session的起點、終點、SYN旗標

    Args:
        grouped_packets (_type_): _description_
    """
    grouped_packets_info = {}
    
    for group_ip_port, packets in grouped_packets.items():
        if group_ip_port == 'background':
            continue

        grouped_packets_info[group_ip_port] = {
            'First Packet Order': int(packets[0].number),
            'Last Packet Order': int(packets[-1].number),
            'SYN Flag': get_tcp_flags(packets[0].tcp.flags)['SYN'] # 有該旗標的封包，代表是新的正常session
        }
        
    return grouped_packets_info

def find_reconnect_sessions(sessions):
    """輔助函式, 找到可能是斷線重聯的兩段session, 將其記錄下來

    Args:
        sessions (_type_): _description_
        expected_session_count (_type_): _description_

    Returns:
        _type_: _description_
    """
    sorted_sessions = sorted(sessions.items(), key=lambda x: x[1]['Last Packet Order'])
    reconnect_pairs = {}
    total_session_count = len(sessions)
    
    for i, (session1, data1) in enumerate(sorted_sessions):
        if session1 not in sessions:
            continue

        min_gap = float('inf')
        reconnect_candidate = None

        for j, (session2, data2) in enumerate(sorted_sessions[i+1:]):
            if session2 not in sessions:
                continue

            if data2['First Packet Order'] > data1['Last Packet Order'] and data2['SYN Flag']: # 代表 data2 順序上是在 data1 之後，且是新的正常session
                gap = data2['First Packet Order'] - data1['Last Packet Order']
                
                if gap < min_gap:
                    min_gap = gap
                    reconnect_candidate = session2

        if reconnect_candidate:
            reconnect_pairs[session1] = reconnect_candidate
            del sessions[session1]
            del sessions[reconnect_candidate]
            
            total_session_count -= 1 # 更新剩餘session數量

        if total_session_count == EXPECTED_SESSION_COUNT: # 若剩餘session數量已符合預期，則不需要再繼續搜尋
            break

    return reconnect_pairs

def handle_reconnect_sessions(initial_packet_groups, reconnect_pairs):
    """輔助函式, 將斷線重聯的兩段session組合起來

    Args:
        initial_packet_groups (_type_): _description_
        reconnect_pairs (_type_): _description_
    """
    for old_key, new_key in reconnect_pairs.items():
            logging.info(f"Reconnect: {old_key} -> {new_key}")
            initial_packet_groups[old_key].extend(initial_packet_groups[new_key]) # 按順序組合兩個session的封包
            del initial_packet_groups[new_key]
            initial_packet_groups[new_key] = initial_packet_groups.pop(old_key) # 重新命名以保留新的session名稱

# PART 2-1: 依照分類結果追蹤sessions
def sort_sessions_by_length(initial_packet_groups, exclude_keywords):
    return sorted(
        [k for k in initial_packet_groups.keys() if all(ex not in k for ex in exclude_keywords)],
        key=lambda k: len(initial_packet_groups[k]),
        reverse=True
    )[:EXPECTED_SESSION_COUNT]

def initialize_session_tracking(packet_groups, session_track, sorted_group_keys, session_key_history):
    for i, session_name in enumerate(session_track.keys()):
            try:
                top_session_info = sorted_group_keys[i]
                session_track[session_name] = top_session_info
                packet_groups[f"{session_name}: {top_session_info}"] = packet_groups.pop(top_session_info)
                session_key_history[top_session_info] = session_name
            except IndexError: # 連線數比預期少，可能條件錯誤，也可能一開始就斷線了
                top_session_info = None
                
            logging.info(f"{session_name} assigned to {top_session_info}")

def update_session_tracking(initial_packet_groups, session_track, reconnect_pairs, sorted_group_keys, session_key_history):
    for session_name, old_key in session_track.items():
        if old_key in initial_packet_groups: # 這個session沒有變動
            initial_packet_groups[f"{session_name}: {old_key}"] = initial_packet_groups.pop(old_key)
            continue

        new_key = reconnect_pairs.get(old_key, None) 
        if new_key: # 這個session有變動，且有可能的對應reconnect session
            session_track[session_name] = new_key
            initial_packet_groups[f"{session_name}: {new_key}"] = initial_packet_groups.pop(new_key)
        else: # 這個session有變動，但沒有對應的reconnect session
            if session_track[session_name] != 'NONE':
                logging.info(f"Unable to track {session_name}: {old_key}") # 斷線宣告
            session_track[session_name] = 'NONE'
            
    if any(val == 'NONE' for val in session_track.values()): # 有session斷線
        remaining_keys = sorted_group_keys.copy()
        for session_name, val in session_track.items():
            if val == 'NONE':
                try: # 嘗試重新配對 (高風險)
                    for top_session_info in remaining_keys:
                        prev_assigned_session = session_key_history.get(top_session_info, None)
                        if prev_assigned_session and prev_assigned_session != session_name:
                            continue
                        
                        session_track[session_name] = top_session_info
                        initial_packet_groups[f"{session_name}: {top_session_info}"] = initial_packet_groups.pop(top_session_info)
                        session_key_history[top_session_info] = session_name
                        
                        logging.info(f"{session_name} re-assigned to {top_session_info}")
                        
                        remaining_keys.remove(top_session_info)
                        break
                    
                except StopIteration:
                    pass       

def session_tracking(initial_packet_groups, session_track, reconnect_pairs, session_key_history):
    """更新各session的狀態

    Args:
        initial_packet_groups (_type_): _description_
        session_track (_type_): _description_
        reconnect_pairs (_type_): _description_

    Returns:
        _type_: _description_
    """
    if all(val == 'NONE' for val in session_track.values()): # 首次執行
        sorted_group_keys = sort_sessions_by_length(initial_packet_groups, 'background')
        initialize_session_tracking(initial_packet_groups, session_track, sorted_group_keys, session_key_history)
        
        return initial_packet_groups
        
    else: # 非首次執行，確認session是否有變動
        sorted_group_keys = sort_sessions_by_length(initial_packet_groups, ['background', 'Session'])
        update_session_tracking(initial_packet_groups, session_track, reconnect_pairs, sorted_group_keys, session_key_history)
        
        return initial_packet_groups

def classify_packets(packet_list, session_track, session_key_history):
    """將封包分類成不同的session

    Args:
        packet_list (_type_): _description_
        session_track (_type_): _description_

    Returns:
        _type_: _description_
    """
    initial_packet_groups = initial_packet_grouping(packet_list)
    grouped_packets_info = collect_grouped_packets_info(initial_packet_groups)
    reconnect_pairs = {}
    
    if len(grouped_packets_info) > EXPECTED_SESSION_COUNT: # 有多餘的session，可能是異常，也可能是reconnect
        reconnect_pairs = find_reconnect_sessions(grouped_packets_info)
        handle_reconnect_sessions(initial_packet_groups, reconnect_pairs)
    
    sessions = session_tracking(initial_packet_groups, session_track, reconnect_pairs, session_key_history)
    
    return sessions

# PART 3: 計算通訊指標
def unilateral_metrics(packet_list):
    """計算單向通訊指標: 平均單包吞吐量、平均總吞吐量、平均發送頻率

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
    resp_avg_load, resp_avg_throughput, resp_avg_frequency = calculate(response_group)
    
    u_metrics = {
        'request': {'avg_load': req_avg_load, 'avg_throughput': req_avg_throughput, 'avg_frequency': req_avg_frequency},
        'response': {'avg_load': resp_avg_load, 'avg_throughput': resp_avg_throughput, 'avg_frequency': resp_avg_frequency}
    }
    
    return u_metrics

def get_tcp_flags(flag_hex):
    """輔助函式, 將TCP Flags轉換成dict
    """
    # Convert hex to binary and pad with leading zeroes to 8 bits
    flag_bin = bin(int(flag_hex, 16))[2:].zfill(8)
    
    # Define flags according to their bit position
    flags = ['FIN', 'SYN', 'RST', 'PSH', 'ACK', 'URG', 'ECE', 'CWR']
    flag_dict = {flag: bool(int(flag_bin[bit])) for bit, flag in enumerate(reversed(flags))}

    return flag_dict

def bilateral_metrics(packet_list, sub_key):
    """_summary_

    Args:
        packet_list [packet_object]: 時間間隔內、同一個session的封包物件
        sub_key (int): client的連線port, 用來區分不同的session, server-opc-app的連線port固定為4840

    Returns:
        defaultdict(dict): 通訊指標 & 異常封包列表
    """
    
    rtt_list = []
    req_resp_delay_list = []
    track_packets = {}
    session_indexes = {'max_req_seq': 0, 'max_resp_seq': 0, 'client_port': sub_key, 'opc_req_handle': None, 'holding_SYN_flag': False}
    h_messages = []
    e_messages = []
    
    for packet in packet_list:
        
        # 基本封包資訊
        order = packet.number
        timestamp = float(packet.sniff_timestamp)
        ip = packet.ip.src
        client_port = packet[packet.transport_layer].dstport if ip == SERVER_IP else packet[packet.transport_layer].srcport
        flags = get_tcp_flags(packet.tcp.flags)
        seq = int(packet.tcp.seq)
        ack = int(packet.tcp.ack)
        tcp_segment_len = int(packet.tcp.len)
        
        # 進階封包資訊
        try:
            rtt = float(packet.tcp.analysis_ack_rtt)
            rtt_list.append(rtt) # 紀錄rtt
        except AttributeError:
            pass
        try:
            opc_req_handle = packet.opcua.RequestHandle
        except AttributeError:
            opc_req_handle = None
        try:
            opc_message_type = packet.opcua.transport_type
            
            if opc_message_type == 'HEL': # 紀錄Hello封包 (即新的session開啟) #TODO: 考慮新增一項檢查機制，確認是否接上之前的SYN-SNY/ACK
                h_messages.append(order)
        except AttributeError:
            opc_message_type = None
            
        # 異常封包檢測
        if flags['RST']: # 重置請求
            e_messages.append(order)
            continue
        
        if session_indexes['client_port'] and client_port != session_indexes['client_port']: # 不屬於現行的session
            if flags['SYN']: # 可能是剛開啟的新session
                session_indexes['holding_SYN_flag'] = True
                e_messages.append(order) # 但是這裡先當作異常封包
                continue 
            else:
                e_messages.append(order)
                continue
        elif session_indexes['holding_SYN_flag'] and flags['SYN'] and flags['ACK']: # 確定是剛開啟的新session
            e_messages.pop() # 將上次加入的異常封包移除
            session_indexes['holding_SYN_flag'] = False
        
        if ip == SERVER_IP and seq <= session_indexes['max_resp_seq']: # 多種原因，高機率是某種retransmission
            e_messages.append(order)
            continue
        elif ip != SERVER_IP and seq <= session_indexes['max_req_seq']:
            e_messages.append(order)
            continue
        
        
        # 計算Request-Response延遲
        if flags['ACK']:
            if opc_req_handle: # 這是OPC封包
                if ack in track_packets and track_packets[ack]['opc_req_handle'] == opc_req_handle: # 這是有對應的回應封包
                    req_resp_delay_list.append(timestamp - track_packets[ack]['timestamp'])
                    track_packets.pop(ack, None)
                    
            if all(val == False for key, val in flags.items() if key != 'ACK'):
                continue # 這是個純ACK封包，不需要紀錄
            else:
                track_packets[seq + tcp_segment_len] = {'timestamp': timestamp, 'seq': seq, 'ack': ack, 'opc_req_handle': opc_req_handle} # 下一個對應的回應封包其ack值會相等此次封包req+tcp_segment_len
        
        # 更新session_indexes
        if ip == SERVER_IP: # 這是封回應封包
            session_indexes['max_resp_seq'] = seq
        else:
            session_indexes['max_req_seq'] = seq
        if opc_req_handle:
            session_indexes['opc_req_handle'] = opc_req_handle

    avg_rtt = round(sum(rtt_list)*1000 / len(rtt_list), 3) if rtt_list else 0 # 取毫秒
    avd_req_resp_delay = round(sum(req_resp_delay_list)*1000 / len(req_resp_delay_list), 3) if req_resp_delay_list else 0
    
    b_metrics = {'avg_rtt': avg_rtt, 'avd_req_resp_delay': avd_req_resp_delay, 'h_messages': h_messages, 'e_messages': e_messages}
    
    return b_metrics

def plot_metrics(plot_data, title, unit):
    plt.figure()
    
    cool_colors = ['blue', 'turquoise', 'teal', 'cyan', 'royalblue', 'dodgerblue', 'mediumslateblue', 'darkcyan']
    session_color_map = {}  # A dictionary to map session numbers to colors
    color_idx = 0
    
    # Sort the group names
    sorted_groups = sorted(plot_data.keys())
    
    for group in sorted_groups:
        duration_data = plot_data[group]
        x = list(duration_data.keys())
        y = [sum(values) / len(values) for values in duration_data.values()]  # Average if multiple values
        
        if "Session" in group:
            session_number = group.split(" ")[1]  # Extract session number
            
            # Assign a color if not already assigned
            if session_number not in session_color_map:
                session_color_map[session_number] = cool_colors[color_idx]
                color_idx = (color_idx + 1) % len(cool_colors)  # Loop back to the first color if needed
            
            plt.plot(x, y, label=group, linewidth=1.5, linestyle='-', marker='o', color=session_color_map[session_number])
        else:
            plt.plot(x, y, label=group, linewidth=1, linestyle='--', color='gray')
    
    plt.title(title)
    plt.xlabel('Capture Duration')
    plt.ylabel(unit)
    plt.legend()
    plt.show()

# 主程式
def main():
    
    capture_duration = 0 # 擷取封包的時間長度
    session_track ={f'Session {i+1}': 'NONE' for i in range(EXPECTED_SESSION_COUNT)}
    session_key_history = {}
    
    u_metrics_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict))) # 單向通訊指標
    b_metrics_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict))) # 雙向通訊指標
    
    request_data_load = defaultdict(lambda: defaultdict(list))
    request_data_throughput = defaultdict(lambda: defaultdict(list))
    request_data_frequency = defaultdict(lambda: defaultdict(list))
    
    response_data_load = defaultdict(lambda: defaultdict(list))
    response_data_throughput = defaultdict(lambda: defaultdict(list))
    response_data_frequency = defaultdict(lambda: defaultdict(list))
    
    average_rtt = defaultdict(lambda: defaultdict(list))
    average_req_resp_delay = defaultdict(lambda: defaultdict(list))
    reconnection_count = defaultdict(lambda: defaultdict(list))
    error_packets_count = defaultdict(lambda: defaultdict(list))
    
    # 批次讀取封包
    packet_lists = read_pcapng_file()
    for packet_list in packet_lists:
        
        capture_duration += TIME_INTERVAL
        logging.info('')
        logging.info(f'Processed Time Interval: {capture_duration} seconds')
        
        # 讀取封包 -測試
        # logging.info(f'New Time Interval: Packets={len(packet_list)}')
        # for packet in packet_list:
        #     logging.debug(f'Packet Sniff Time: {packet.sniff_time}')
        #     logging.debug(f'Packet Length: {len(packet)} bytes')
        # logging.info('---')
        
        # 分類封包
        classified_packets = classify_packets(packet_list, session_track, session_key_history)
        
        # 分類封包 -測試        
        # for key, value in classified_packets.items():
        #     if key != 'background':
        #         for sub_key, sub_value in value.items():
        #             logging.info(f"For Client IP: {key}, Client Port: {sub_key}")
        #             for i, packet in enumerate(sub_value[:5]):
        #                 logging.info(f'{packet.ip.src}:{packet[packet.transport_layer].srcport} -> {packet.ip.dst}:{packet[packet.transport_layer].dstport}')
        #     logging.info('---')
        
        # 計算通訊指標
        for key, value in classified_packets.items(): # key為client_ip-client_port, value為[packet1, packet2, ...]
            if key == 'background':
                continue
            
            u_metrics = unilateral_metrics(value)
            b_metrics = bilateral_metrics(value, key.split('-')[1])
            
            # 計算單向通訊指標 -測試
            # logging.info(f'Client IP: {key.split('-')[0]}, Client Port: {key.split('-')[1]}')
            # logging.info(f'Request: {u_metrics["request"]}')
            # logging.info(f'Response: {u_metrics["response"]}')
            # logging.info('---')
                    
            # 計算雙向通訊指標 -測試
            # logging.info(f'Client IP: {key.split('-')[0]}, Client Port: {key.split('-')[1]}')
            # logging.info(f'RTT: {b_metrics["avg_rtt"]}, Request-Response Delay: {b_metrics["avd_req_resp_delay"]}, Reconnection_count: {len(b_metrics["h_messages"])}, Error_count: {len(b_metrics["e_messages"])}')
            # logging.info('---')
            
            u_metrics_dict[capture_duration][key] = u_metrics
            b_metrics_dict[capture_duration][key] = b_metrics
            
            request_data_load[key][capture_duration].append(u_metrics['request']['avg_load'])   
            request_data_throughput[key][capture_duration].append(u_metrics['request']['avg_throughput'])
            request_data_frequency[key][capture_duration].append(u_metrics['request']['avg_frequency'])
                    
            response_data_load[key][capture_duration].append(u_metrics['response']['avg_load'])
            response_data_throughput[key][capture_duration].append(u_metrics['response']['avg_throughput'])
            response_data_frequency[key][capture_duration].append(u_metrics['response']['avg_frequency'])
                    
            average_rtt[key][capture_duration].append(b_metrics['avg_rtt'])
            average_req_resp_delay[key][capture_duration].append(b_metrics['avd_req_resp_delay'])
            reconnection_count[key][capture_duration].append(len(b_metrics['h_messages']))
            error_packets_count[key][capture_duration].append(len(b_metrics['e_messages']))   
            
    plot_metrics(request_data_load, 'Request Average Load', 'bytes/s')
    plot_metrics(request_data_throughput, 'Request Average Throughput', 'bytes/s')
    plot_metrics(request_data_frequency, 'Request Average Frequency', 'packets/s')
    
    plot_metrics(response_data_load, 'Response Average Load', 'bytes/s')
    plot_metrics(response_data_throughput, 'Response Average Throughput', 'bytes/s')
    plot_metrics(response_data_frequency, 'Response Average Frequency', 'packets/s')
    
    plot_metrics(average_rtt, 'Average RTT', 'ms')
    plot_metrics(average_req_resp_delay, 'Average Request-Response Delay', 'ms')
    plot_metrics(reconnection_count, 'Reconnection Count', 'packets')
    plot_metrics(error_packets_count, 'Error Packets Count', 'packets')
    
if __name__ == "__main__":
    
    # 方便觀察程式回饋
    logging.basicConfig(level=logging.INFO)    
    main() 
    pause = input("Press any key to exit...")