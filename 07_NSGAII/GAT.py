import os
import csv
import ast
import re
import torch
import networkx as nx
import torch.nn.functional as F
from torch_geometric.data import Data
from torch_geometric.nn import GATConv, global_mean_pool
from sklearn.preprocessing import OneHotEncoder, MultiLabelBinarizer, StandardScaler

def individual_to_graph(switch_dict, device_dict, computer_dict, individual):
    G = nx.Graph()
    
    # 前段
    nodes = list(switch_dict) + list(device_dict) + list(computer_dict)
    
    for node in nodes:
        G.add_node(node)
    
    for i in range(len(nodes)):
        if individual[i]:
            G.add_edge(individual[i], nodes[i])
            
    # 後段
    comps = list(computer_dict)
    for i in range(len(nodes), len(individual)):
        for app in individual[i]:
            node = f"{app}_{comps[i-len(nodes)]}"
            
            G.add_node(node)
            G.add_edge(comps[i-len(nodes)], node)
            
    return G, len(nodes)

def update_computer_dict(computer_dict, individual, first_range):
    # runnung apps
    for i in range(first_range, len(individual)):
        label = f'comp{i - first_range + 1}'
        computer_dict[label]['running_apps'] = individual[i]
            
    return computer_dict

def update_subscription_dict(G, subscription_dict):
    app_nodes = {node for node in G.nodes if node.startswith("app")}
    for sub, sub_info in subscription_dict.items():
        device = sub_info["device"]
        target_apps = {node for node in app_nodes if re.search(r'app' + sub_info["app"][-1], node)}
        try:
            shortest_path = min(
                (nx.shortest_path(G, source=device, target=app) for app in target_apps),
                key=len,
                default=None
            )
        except nx.NetworkXNoPath:
            return None
        if shortest_path:
            sub_info["app"] = shortest_path[-1]
            sub_info["path"] = shortest_path
    return subscription_dict

def data_preprocess(application_dict, computer_dict, device_dict, switch_dict, subscription_dict, individual):

    # 特徵輔助資料-2 (網路拓撲)
    network_graph, first_range = individual_to_graph(switch_dict, device_dict, computer_dict, individual)
    computer_dict = update_computer_dict(computer_dict, individual, first_range)
    
    # 避免新一代拓樸變異後無法產生正確路徑
    if update_subscription_dict(network_graph, subscription_dict) is None:
        return None
    
    subscription_dict = update_subscription_dict(network_graph, subscription_dict)
    
    # 因為變數會被重複使用
    for app, app_info in application_dict.items():
        if isinstance(app_info, dict) and "name" in app_info:
            app_info['app_type'] = app_info.pop('name')
    

    for dev, dev_info in device_dict.items():
        if isinstance(dev_info, dict) and "type" in dev_info:
            dev_info['dev_type'] = dev_info.pop('type')

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
        multi_label_columns = ['target_device']
        dynamic_label_columns = ['running_apps']
        excluded_columns = single_label_columns + multi_label_columns + dynamic_label_columns
        
        for item in all_lists:
            new_dict = {key: None if key in single_label_columns else [] if key in multi_label_columns or key in dynamic_label_columns else 0 for key in all_keys}
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
            
        dynamic_features_dict = {col: [] for col in dynamic_label_columns}
        for col in dynamic_label_columns:
            
            encoded = []
            for i in range(len(node_features)):
                dynamic_app_list = [0] * len(application_dict.keys())
                
                for d_app in node_features[i][col]:
                    dynamic_app_list[int(d_app[-1]) - 1] = 1
                
                encoded.append(dynamic_app_list)
        
            dynamic_features_dict[col].extend(encoded)

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
            for col in dynamic_label_columns:
                combined_row.extend(dynamic_features_dict[col][i])    
            
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
        
        #* 單筆資料
        data.append(Data(x=node_features_tensor, edge_index=adjacency_index))
    
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

def graph_attention_network(application_dict, computer_dict, device_dict, switch_dict, subscription_dict, individual):
    num_node_features = 35
    num_classes = 1
    model = OptimizedGATModel(num_node_features, num_classes)

    model.load_state_dict(torch.load('06_GAT\model_state_dict.pth'))
    model.eval()

    if data_preprocess(application_dict, computer_dict, device_dict, switch_dict, subscription_dict, individual) is None:
        return -10
    
    data = data_preprocess(application_dict, computer_dict, device_dict, switch_dict, subscription_dict, individual)
    predict = []
    for i in range(len(data)):
        with torch.no_grad():
            predict.append(model(data[i]).item())
            
    # 加權重
    for pred, sub in zip (predict, subscription_dict.values()):
        pred = pred * float(sub['weight'])
        
    return round(sum(predict),8)