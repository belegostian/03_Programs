import os
import csv
import ast
import torch
import networkx as nx
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GATConv, global_mean_pool
from sklearn.preprocessing import OneHotEncoder, MultiLabelBinarizer, StandardScaler

#? 本模型不使用 edge attributes

def csv_to_dict(file_path, key_field, transformations=None, split_fields=None):
    data_dict = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            key = row.pop(key_field)

            # Split specified fields
            if split_fields:
                for field, delimiter in split_fields.items():
                    if field in row:
                        row[field] = row[field].split(delimiter)

            # Apply transformations
            if transformations:
                for field, func in transformations.items():
                    if field in row:
                        row[field] = func(row[field])

            data_dict[key] = row
    return data_dict

def csv_to_graph(file_name):
    G = nx.Graph()

    with open(file_name, 'r') as file:
        reader = csv.reader(file)
        nodes_section = True
        for row in reader:
            if not row:
                nodes_section = False
                continue

            if nodes_section:
                if row[0] != 'Nodes':
                    G.add_node(row[0])
            else:
                if row[0] != 'Edges':
                    G.add_edge(row[0], row[1])

    return G

def data_preprocess(base_folder = '03_scenario_generation\\experiment_0', scenario = 'scenario_0'):

    # 節點特徵(應用程序)
    application_transformations = {
        'response_timeout': float,
        'cpu_usage (%)': float,
        'memory_usage (MiB)': float,
        'packet_sending (kB)': float,
        'packet_receiving (kB)': float
    }
    application_dict = csv_to_dict(os.path.join(base_folder, 'applications.csv'), 'application', application_transformations)
    for app, app_info in application_dict.items():
            app_info['app_type'] = app_info.pop('name')

    # 節點特徵(生產設備)
    device_transformations = {
        'bandwidth': int,
        'group': int
    }
    device_dict = csv_to_dict(os.path.join(base_folder, 'devices.csv'), 'device', device_transformations)
    for dev, dev_info in device_dict.items():
            dev_info['dev_type'] = dev_info.pop('type')

    # 節點特徵(交換器)
    switch_transformations = {
        'bandwidth': int,
        'forward_delay': float
    }
    switch_dict = csv_to_dict(os.path.join(base_folder, 'switches.csv'), 'switch', switch_transformations)

    file_path = os.path.join(base_folder, scenario)

    # 節點特徵(計算設備)
    computer_transformations = {
        'running_apps': ast.literal_eval,
        'cpu': float,
        'memory': int,
        'bandwidth': int,
        'group': lambda x: None if x == '' else int(x)
    }
    computer_dict = csv_to_dict(os.path.join(file_path, 'computers.csv'), 'computer', computer_transformations)

    # 特徵輔助資料-1 (訂閱)
    subscription_split_fields = {
        'path': ','
    }
    subscription_dict = csv_to_dict(os.path.join(file_path, 'subscription_paths.csv'), 'subscription', None, subscription_split_fields)
    
    # 特徵輔助資料-2 (網路拓撲)
    network_graph = csv_to_graph(os.path.join(file_path, 'network_topo.csv'))

    # 資料集
    data = []
    
    for sub in subscription_dict.values():
        #* 節點特徵前處理-標註其參與訂閱的角色
        for app, app_info in application_dict.items():            
            app_info['role'] = 'subscribed' if sub['app'].split('_')[0] == app else None
            
        for comp, comp_info in computer_dict.items():
            comp_info['role'] = 'transfer' if sub['app'].split('_')[1] == comp else None
            
        for dev, dev_info in device_dict.items():
            dev_info['role'] = 'subscriber' if sub['device'] == dev else None
            
        for switch, switch_info in switch_dict.items():
            switch_info['role'] = 'transfer' if switch in sub['path'] else None
        
        application_list = [v for v in application_dict.values()]
        computer_list = [v for v in computer_dict.values()]
        device_list = [v for v in device_dict.values()]
        switch_list = [v for v in switch_dict.values()]
        node_key_list = list(application_dict.keys()) + list(computer_dict.keys()) + list(device_dict.keys()) + list(switch_dict.keys())
        
        # 特徵統一(補位)
        all_lists = application_list + computer_list + device_list + switch_list
        all_keys = sorted(set().union(*(item.keys() for item in all_lists)))
        
        node_features  = []
        single_label_columns = ['dev_type', 'app_type', 'role']
        multi_label_columns = ['running_apps', 'target_device']
        excluded_columns = single_label_columns + multi_label_columns
        
        for item in all_lists:
            new_dict = {key: None if key in single_label_columns else [] if key in multi_label_columns else 0 for key in all_keys}
            new_dict.update(item)
            node_features.append(new_dict)
        
        # 數值化非數值特徵
        ohe = OneHotEncoder()
        ohe_features_dict = {col: [] for col in single_label_columns}
        for col in single_label_columns:
            encoded = ohe.fit_transform([[i[col]] for i in node_features]).toarray()
            ohe_features_dict[col].extend(encoded)
            
        mlb = MultiLabelBinarizer()
        mlb_features_dict = {col: [] for col in multi_label_columns}
        for col in multi_label_columns:
            encoded = mlb.fit_transform([i[col] for i in node_features])
            mlb_features_dict[col].extend(encoded)

        # 標準化數值特徵
        scaler = StandardScaler()
        numerical_features = []
        numerical_features.extend(scaler.fit_transform([[node[key] for key in node if key not in excluded_columns] for node in node_features]))
        
        # 特徵合併
        combined_node_features = []
        for i in range(len(node_features)):
            combined_row = []
            for col in single_label_columns:
                combined_row.extend(ohe_features_dict[col][i])
            for col in multi_label_columns:
                combined_row.extend(mlb_features_dict[col][i])
            combined_row.extend(numerical_features[i])
            combined_node_features.append(combined_row)
            
        node_features_tensor = torch.tensor(combined_node_features, dtype=torch.float)
        
        #* 鄰接矩陣
        node_order = {node: idx for idx, node in enumerate(node_key_list)}
        adjacency_index = []
        for edge in network_graph.edges():
            node1_idx = node_order.get(edge[0].split('_')[0])
            node2_idx = node_order.get(edge[1].split('_')[0])
            if node1_idx is not None and node2_idx is not None:
                adjacency_index.append((node1_idx, node2_idx))
                
        adjacency_index = torch.tensor(adjacency_index, dtype=torch.long).t().contiguous()
        
        #* 預測資料
        qos_score = float(sub['QoS Score'])
        qos_score_tensor = torch.tensor(qos_score, dtype=torch.float)
        
        #* 單筆資料
        data.append(Data(x=node_features_tensor, edge_index=adjacency_index, y=qos_score_tensor))
        
    return data

class OptimizedGATModel(torch.nn.Module):
    def __init__(self, num_node_features, num_classes):
        super(OptimizedGATModel, self).__init__()
        
        self.conv1 = GATConv(num_node_features, 64, heads=6, dropout=0.4)
        self.conv2 = GATConv(64 * 6, 16, heads=3, concat=False, dropout=0.4)

        self.fc = torch.nn.Linear(16, num_classes)  # Linear layer to adjust the output dimension

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch

        # Reduced dropout and changed activation function
        x = F.dropout(x, p=0.3, training=self.training)
        x = F.relu(self.conv1(x, edge_index))  # Changed to ReLU

        x = F.dropout(x, p=0.3, training=self.training)
        x = self.conv2(x, edge_index)

        x = global_mean_pool(x, batch)  # Pooling node features to graph-level
        x = self.fc(x)  # Final linear layer

        return x

def graph_attention_network(individual):
    num_node_features = 35
    num_classes = 1
    model = OptimizedGATModel(num_node_features, num_classes)

    model.load_state_dict(torch.load('06_GAT\model_state_dict.pth'))
    model.eval()

    data = data_preprocess(individual)
    for i in range(len(data)):
        with torch.no_grad():
            pred = model(data[i])
            # print(round(pred.item(),8))
            
    return round(pred.item(),8)