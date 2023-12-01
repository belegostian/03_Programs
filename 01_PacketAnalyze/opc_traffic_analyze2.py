import csv
import logging
import pyshark
import matplotlib.pyplot as plt
from collections import defaultdict

#? 請在03_Programs資料夾下執行此程式
#? 這支程式在自動化流程中有大改，部分註解與測試集可能有錯誤

# PART 1: 依照時間間隔取得封包物件
def update_time_interval(packet, start_time, end_time):
    """輔助函式, 更新 read_pcapng_file 時間區間
    """
    start_time = packet.sniff_time.timestamp()
    end_time = start_time + time_interval
    return start_time, end_time

def read_pcapng_file(capture_file):
    """批次取得時間間隔內的封包物件

    Yields:
        [packet_object]: 時間間隔內的封包物件
    """
    with pyshark.FileCapture(capture_file, keep_packets=True) as cap:
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

# PART 2-1: 進行分類前置(蒐集、整理、重組)
def initial_packet_grouping(packet_list, client_ip):
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

        if src_ip == client_ip or dst_ip == client_ip:
            server_ip = dst_ip if src_ip == client_ip else src_ip
            server_port = dst_port if src_ip == client_ip else src_port
            client_port = src_port if src_ip == client_ip else dst_port
            group_key = f"{client_ip}:{client_port}-{server_ip}:{server_port}"
            
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

def find_reconnect_sessions(sessions, expected_session_count):
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
            
            session1_ip = '-'.join([part.split(':')[0] for part in session1.split('-')])
            session2_ip = '-'.join([part.split(':')[0] for part in session2.split('-')])
            if session1_ip == session2_ip: # 代表是同一對IP
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

        if total_session_count == expected_session_count: # 若剩餘session數量已符合預期，則不需要再繼續搜尋
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

# PART 2-2: 依照分類結果追蹤sessions
def sort_sessions_by_length(initial_packet_groups, exclude_keywords, expected_session_count):
    return sorted(
        [k for k in initial_packet_groups.keys() if all(ex not in k for ex in exclude_keywords)],
        key=lambda k: len(initial_packet_groups[k]),
        reverse=True
    )[:expected_session_count]

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

def session_tracking(initial_packet_groups, session_track, reconnect_pairs, session_key_history, expected_session_count):
    """更新各session的狀態

    Args:
        initial_packet_groups (_type_): _description_
        session_track (_type_): _description_
        reconnect_pairs (_type_): _description_

    Returns:
        _type_: _description_
    """
    if all(val == 'NONE' for val in session_track.values()): # 首次執行
        sorted_group_keys = sort_sessions_by_length(initial_packet_groups, 'background', expected_session_count)
        initialize_session_tracking(initial_packet_groups, session_track, sorted_group_keys, session_key_history)
        
        return initial_packet_groups
        
    else: # 非首次執行，確認session是否有變動
        sorted_group_keys = sort_sessions_by_length(initial_packet_groups, ['background', 'Session'], expected_session_count)
        update_session_tracking(initial_packet_groups, session_track, reconnect_pairs, sorted_group_keys, session_key_history)
        
        return initial_packet_groups

# PART 2: 依照 session/訂閱關係 做分類
def classify_packets(packet_list, client_ip, expected_session_count, session_track, session_key_history):
    """將封包分類成不同的session

    Args:
        packet_list (_type_): _description_
        session_track (_type_): _description_

    Returns:
        _type_: _description_
    """
    initial_packet_groups = initial_packet_grouping(packet_list, client_ip)
    grouped_packets_info = collect_grouped_packets_info(initial_packet_groups)
    reconnect_pairs = {}
    
    if len(grouped_packets_info) > expected_session_count: # 有多餘的session，可能是異常，也可能是reconnect
        reconnect_pairs = find_reconnect_sessions(grouped_packets_info, expected_session_count)
        handle_reconnect_sessions(initial_packet_groups, reconnect_pairs)
    
    sessions = session_tracking(initial_packet_groups, session_track, reconnect_pairs, session_key_history, expected_session_count)
    
    return sessions

# PART 3: 計算通訊指標
def unilateral_metrics(packet_list, client_ip):
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

        if src_ip == client_ip:
            response_group.append(packet)
        elif dst_ip == client_ip:
            request_group.append(packet)
            
    def calculate(group):
        total_bytes = sum(int(packet.length) for packet in group)
        total_packets = len(group)
        
        avg_load = 0 if total_packets == 0 else round(total_bytes / total_packets, 2)
        avg_throughput = total_bytes / time_interval if time_interval else 0
        avg_frequency = total_packets / time_interval if time_interval else 0
        
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

def bilateral_metrics(packet_list, client_ip):
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
    session_indexes = {'max_req_seq': 0, 'max_resp_seq': 0, 'client_port': None, 'opc_req_handle': None, 'holding_SYN_flag': False}
    h_messages = []
    e_messages = []
    
    for packet in packet_list:
        
        # 基本封包資訊
        order = packet.number
        timestamp = float(packet.sniff_timestamp)
        
        src_ip = packet.ip.src
        dst_ip = packet.ip.dst
        src_port = packet[packet.transport_layer].srcport
        dst_port = packet[packet.transport_layer].dstport
        
        server_ip = dst_ip if src_ip == client_ip else src_ip
        server_port = dst_port if src_ip == client_ip else src_port
        client_port = src_port if src_ip == client_ip else dst_port            
        
        ip = packet.ip.src
        client_port = packet[packet.transport_layer].srcport if ip == client_ip else packet[packet.transport_layer].dstport
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
        
        if ip == server_ip and seq <= session_indexes['max_resp_seq']: # 多種原因，高機率是某種retransmission
            e_messages.append(order)
            continue
        elif ip != server_ip and seq <= session_indexes['max_req_seq']:
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
        if ip == server_ip: # 這是封回應封包
            session_indexes['max_resp_seq'] = seq
        else:
            session_indexes['max_req_seq'] = seq
        if opc_req_handle:
            session_indexes['opc_req_handle'] = opc_req_handle

    avg_rtt = round(sum(rtt_list)*1000 / len(rtt_list), 3) if rtt_list else 0 # 取毫秒
    avd_req_resp_delay = round(sum(req_resp_delay_list)*1000 / len(req_resp_delay_list), 3) if req_resp_delay_list else 0
    
    b_metrics = {'avg_rtt': avg_rtt, 'avd_req_resp_delay': avd_req_resp_delay, 'h_messages': h_messages, 'e_messages': e_messages}
    
    return b_metrics

# PART 4-1 指標分組前處理
def transform_keys(original_dict):
    new_dict = {}
    
    for key in original_dict:
        
        if 'Session' not in key:
                continue
        
        session_part, ip_part = key.split(': ', 1)
        parts = ip_part.split('-')
        ip_addresses = [part.split(':')[0] for part in parts]
        new_key = session_part + ': ' + '-'.join(ip_addresses)
        new_dict[new_key] = original_dict[key]
        
    return new_dict

def align_sessions(old_dict, new_dict):
    record = {k.split(': ')[1]: k.split(': ')[0] for k in old_dict.keys()}
    aligned_dict = {}
    
    for new_key, value in new_dict.items():
        session, ip_pair = new_key.split(': ')
        if ip_pair in record:
            aligned_key = f"{record[ip_pair]}: {ip_pair}"
            del record[ip_pair]
        else:
            aligned_key = new_key
        aligned_dict[aligned_key] = value
        
    return aligned_dict

# PART 4 指標分組儲存
def process_and_save_data(average_rtt, average_req_resp_delay, reconnection_count, error_packets_count, output_file):
    # Helper function to calculate the average of a list
    def process_data(data_dict):
        processed_data = defaultdict(float)
        for outer_key, inner_dict in data_dict.items():
            if "Session" in outer_key:
                total = sum(inner_dict.values())
                count = len(inner_dict)
                processed_data[outer_key] = total / count if count > 0 else 0
        return processed_data

    # Process the defaultdict structures
    processed_average_rtt = process_data(average_rtt)
    processed_average_req_resp_delay = process_data(average_req_resp_delay)
    processed_reconnection_count = process_data(reconnection_count)
    processed_error_packets_count = process_data(error_packets_count)
    
    with open(output_file, mode='r', newline='') as file:
        reader = csv.reader(file)
        existing_headers = next(reader, None)

    # Write processed data to CSV
    with open(output_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=existing_headers)
        
        # Append each session's data
        for session in processed_average_rtt.keys():
            writer.writerow({
                'Session': session,
                'Average RTT': round(processed_average_rtt[session], 4),
                'Average Req Resp Delay': round(processed_average_req_resp_delay[session], 4),
                'Average Reconnection Count': round(processed_reconnection_count[session], 4),
                'Average Error Packets Count': round(processed_error_packets_count[session], 4)
            })

# PART 5 繪製圖表
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
def main(client_ip, expected_session_count, capture_file, output_file, time_interval):
    
    capture_duration = 0 # 擷取封包的時間長度
    session_track ={f'Session {i+1}': 'NONE' for i in range(expected_session_count)}
    session_key_history = {}
    
    u_metrics_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict))) # 單向通訊指標
    b_metrics_dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict))) # 雙向通訊指標
    
    request_data_load = defaultdict(lambda: defaultdict(float))
    request_data_throughput = defaultdict(lambda: defaultdict(float))
    request_data_frequency = defaultdict(lambda: defaultdict(float))
    
    response_data_load = defaultdict(lambda: defaultdict(float))
    response_data_throughput = defaultdict(lambda: defaultdict(float))
    response_data_frequency = defaultdict(lambda: defaultdict(float))
    
    average_rtt = defaultdict(lambda: defaultdict(float))
    average_req_resp_delay = defaultdict(lambda: defaultdict(float))
    reconnection_count = defaultdict(lambda: defaultdict(float))
    error_packets_count = defaultdict(lambda: defaultdict(float))
    
    # 批次讀取封包
    packet_lists = read_pcapng_file(capture_file)
    history_classified_packets = {}
    for packet_list in packet_lists:
        
        logging.info(f'Processed Time Interval: {capture_duration} seconds')
        
        # 讀取封包 -測試
        # logging.info(f'New Time Interval: Packets={len(packet_list)}')
        # for packet in packet_list:
        #     logging.debug(f'Packet Sniff Time: {packet.sniff_time}')
        #     logging.debug(f'Packet Length: {len(packet)} bytes')
        # logging.info('---')
        
        # 分類封包
        classified_packets = classify_packets(packet_list, client_ip, expected_session_count, session_track, session_key_history)
        classified_packets = transform_keys(classified_packets)
        classified_packets = align_sessions(history_classified_packets, classified_packets)
        history_classified_packets = classified_packets
        
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
            
            u_metrics = unilateral_metrics(value, client_ip)
            b_metrics = bilateral_metrics(value, (key.split(': ')[1]).split(':')[0])
            
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
            
            request_data_load[key][capture_duration] = u_metrics['request']['avg_load']
            request_data_throughput[key][capture_duration]= u_metrics['request']['avg_throughput']
            request_data_frequency[key][capture_duration]= u_metrics['request']['avg_frequency']
                    
            response_data_load[key][capture_duration] = u_metrics['response']['avg_load']
            response_data_throughput[key][capture_duration] = u_metrics['response']['avg_throughput']
            response_data_frequency[key][capture_duration] = u_metrics['response']['avg_frequency']
                    
            average_rtt[key][capture_duration] = b_metrics['avg_rtt']
            average_req_resp_delay[key][capture_duration] = b_metrics['avd_req_resp_delay']
            reconnection_count[key][capture_duration] = len(b_metrics['h_messages'])
            error_packets_count[key][capture_duration] = len(b_metrics['e_messages'])
        
        capture_duration += time_interval
        logging.info('')
        
    # 繪製圖表        
    # plot_metrics(request_data_load, 'Request Average Load', 'bytes/s')
    # plot_metrics(request_data_throughput, 'Request Average Throughput', 'bytes/s')
    # plot_metrics(request_data_frequency, 'Request Average Frequency', 'packets/s')
    
    # plot_metrics(response_data_load, 'Response Average Load', 'bytes/s')
    # plot_metrics(response_data_throughput, 'Response Average Throughput', 'bytes/s')
    # plot_metrics(response_data_frequency, 'Response Average Frequency', 'packets/s')
    
    # plot_metrics(average_rtt, 'Average RTT', 'ms')
    # plot_metrics(average_req_resp_delay, 'Average Request-Response Delay', 'ms')
    # plot_metrics(reconnection_count, 'Reconnection Count', 'packets')
    # plot_metrics(error_packets_count, 'Error Packets Count', 'packets')
    
    process_and_save_data(average_rtt, average_req_resp_delay, reconnection_count, error_packets_count, output_file)
    
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # 自動化流程
    # client_ip = sys.argv[1]  # 伺服器/主機IP
    # expected_session_count = sys.argv[2] # 伺服器/主機同時處理的session數量
    # capture_file = sys.argv[3] # 擷取封包檔案路徑
    # output_file = sys.argv[4] # 輸出csv檔案路徑
    # time_interval = int(sys.argv[5]) # 數據平均的時間間隔 -秒
    # 
    # main(client_ip, int(expected_session_count), capture_file, output_file, time_interval)
    
    # 測試組-1
    # client_ip = '10.0.0.210'
    # expected_session_count = '2'
    # capture_file = '03_scenario_generation\\experiment_0\\scenario_1\\comp1.pcap'
    # output_file = '01_PacketAnalyze\\data_training.csv'
    # time_interval = 10
    # 
    # main(client_ip, int(expected_session_count), capture_file, output_file, time_interval)
    
    # 測試組-2
    client_ips = '10.0.0.220,10.0.0.230'.split(',')
    expected_session_counts = '14,14'.split(',')
    capture_files = '03_scenario_generation\\experiment_0\\scenario_1\\comp3.pcap,03_scenario_generation\\experiment_0\\scenario_0\\comp4.pcap'.split(',')
    output_file = '01_PacketAnalyze\\data_training.csv'
    time_interval = 10
    
    for client_ip, expected_session_count, capture_file in zip(client_ips, expected_session_counts, capture_files):
        main(client_ip, int(expected_session_count), capture_file, output_file, time_interval)
        
    