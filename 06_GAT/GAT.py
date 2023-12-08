import os
import re
import csv
import ast
import torch
import numpy as np
import networkx as nx
import torch.optim as optim
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATConv, global_mean_pool, global_max_pool, global_add_pool, MessagePassing
from torch_geometric.data import Data
from torch_geometric.utils import add_self_loops, degree
from torch_geometric.loader import DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import OneHotEncoder, MultiLabelBinarizer, StandardScaler
import matplotlib.pyplot as plt
# 輔助函式
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

def create_graph_from_csv(file_name):
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

def get_bandwidth(node, device_dict, computer_dict, switch_dict):
    if 'dev' in node:
        return device_dict[node]['bandwidth']
    elif 'comp' in node:
        return computer_dict[node]['bandwidth']
    else:
        return switch_dict[node]['bandwidth']

# 第一部分：資料前處理
base_folder = '03_scenario_generation\\experiment_0'

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

# 圖結構
pyg_graphs = []

scenario_folders = [d for d in os.listdir(base_folder) if os.path.isdir(os.path.join(base_folder, d)) and d.startswith('scenario')]
for scenario in scenario_folders:
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
    
    # 特徵輔助資料
    subscription_split_fields = {
        'path': ','
    }
    subscription_dict = csv_to_dict(os.path.join(file_path, 'subscription_paths.csv'), 'subscription', None, subscription_split_fields)

    network_graph = create_graph_from_csv(os.path.join(file_path, 'network_topo.csv'))
    
    # 邊特徵資料
    edge_dict = {}
    for i, edge in enumerate(network_graph.edges()):
        node1, node2 = edge
        
        # 邊特徵-類型
        app_node_candidate = node1 if 'app' in node1 else node2
        non_app_node = node2 if 'app' in node1 else node1
        edge_type = re.sub(r'\d+', '', app_node_candidate.split('_')[0]) + '_' + re.sub(r'\d+', '', non_app_node)
        
        # 邊特徵-頻寬
        if 'app' in node1 or 'app' in node2:
            bandwidth = 10000
            delay = 0
        else:
            nbd1 = get_bandwidth(node1, device_dict, computer_dict, switch_dict)
            nbd2 = get_bandwidth(node2, device_dict, computer_dict, switch_dict)
            bandwidth = min(nbd1, nbd2)
            
            # 邊特徵-延遲，交換器轉發延遲統一算在交換器到交換器/電腦的邊上
            delay = 0
            if ('sw' in node1 and 'comp' in node2) or ('sw' in node2 and 'comp' in node1):
                sw_node = node1 if 'sw' in node1 else node2
                delay = switch_dict[sw_node]['forward_delay']
            elif 'sw' in node1 and 'sw' in node2:
                delay = (switch_dict[node1]['forward_delay'] + switch_dict[node2]['forward_delay']) / 2
            
        edge_dict[i] = {'edge_type': edge_type, 'bandwidth': bandwidth, 'delay': delay}
    
    # 以單次訂閱為單位，進行資料前處理
    for sub in subscription_dict.values():
        #* 節點特徵前處理
        # 標註其參與訂閱的角色
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
        
        #* 邊特徵前處理
        # 邊特徵-類型
        paths = [(sub['path'][i], sub['path'][i + 1]) for i in range(len(sub['path']) - 1)]
        edge_view = network_graph.edges()
        
        matching_edges_order = []
        for path in paths:
            if path in edge_view or path[::-1] in edge_view:
                edge_order = next((i for i, edge in enumerate(edge_view) if edge == path or edge == path[::-1]), None)
                if edge_order is not None:
                    matching_edges_order.append(edge_order)
                    
        for i, edge in enumerate(edge_dict.values()):
            edge['role'] = 'path' if i in matching_edges_order else None
            
        edge_features = [v for k, v in edge_dict.items()]
            
        # 數值化非數值特徵
        single_label_columns = ['edge_type', 'role']
        ohe_features_dict = {col: [] for col in single_label_columns}
        for col in single_label_columns:
            encoded = ohe.fit_transform([[i[col]] for i in edge_features]).toarray()
            ohe_features_dict[col].extend(encoded)
            
        # 標準化數值特徵
        numerical_features = []
        numerical_features.extend(scaler.fit_transform([[node[key] for key in node if key not in single_label_columns] for node in edge_features]))
        
        # 特徵合併
        combined_edge_features = []
        for i in range(len(edge_features)):
            combined_row = []
            for col in single_label_columns:
                combined_row.extend(ohe_features_dict[col][i])
            combined_row.extend(numerical_features[i])
            combined_edge_features.append(combined_row)
        
        edge_features_tensor = torch.tensor(combined_edge_features, dtype=torch.float)
        
        #* 鄰接矩陣
        node_order = {node: idx for idx, node in enumerate(node_key_list)}
        adjacency_index = []
        for edge in edge_view:
            node1_idx = node_order.get(edge[0].split('_')[0])
            node2_idx = node_order.get(edge[1].split('_')[0])
            if node1_idx is not None and node2_idx is not None:
                adjacency_index.append((node1_idx, node2_idx))
                
        adjacency_index = torch.tensor(adjacency_index, dtype=torch.long).t().contiguous()
        
        #* 預測資料
        qos_score = float(sub['QoS Score'])
        qos_score_tensor = torch.tensor(qos_score, dtype=torch.float)
        
        #* 單筆資料
        data = Data(x=node_features_tensor, edge_index=adjacency_index, edge_attr=edge_features_tensor, y=qos_score_tensor)
        pyg_graphs.append(data)

train_val_graphs, test_graphs = train_test_split(pyg_graphs, test_size=0.2, random_state=42)
train_graphs, val_graphs = train_test_split(train_val_graphs, test_size=0.25, random_state=42)

train_loader = DataLoader(train_graphs, batch_size=36, shuffle=True)
val_loader = DataLoader(val_graphs, batch_size=36, shuffle=False)
test_loader = DataLoader(test_graphs, batch_size=36, shuffle=False)

class OptimizedGATModel(torch.nn.Module):
    def __init__(self, num_node_features, num_classes):
        super(OptimizedGATModel, self).__init__()
        # Adjust the number of output features and heads in each layer
        self.conv1 = GATConv(num_node_features, 32, heads=4, dropout=0.3) # Example change
        self.conv2 = GATConv(32 * 4, 16, heads=2, concat=False, dropout=0.3) # Example change

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

# class EdgeFeatureGATLayer(nn.Module):
#     def __init__(self, in_features, edge_features, out_features, dropout, alpha, concat=True):
#         super(EdgeFeatureGATLayer, self).__init__()
#         self.dropout = dropout
#         self.in_features = in_features
#         self.edge_features = edge_features
#         self.out_features = out_features
#         self.alpha = alpha
#         self.concat = concat

#         # Adjust the size of W to match in_features and out_features
#         self.W = nn.Parameter(torch.zeros(size=(in_features, out_features)))
#         nn.init.xavier_uniform_(self.W.data, gain=1.414)
#         self.W_edge = nn.Parameter(torch.zeros(size=(edge_features, out_features)))
#         nn.init.xavier_uniform_(self.W_edge.data, gain=1.414)

#         # Attention mechanism
#         self.a = nn.Parameter(torch.zeros(size=(2 * out_features, 1)))
#         nn.init.xavier_uniform_(self.a.data, gain=1.414)
        
#         self.leakyrelu = nn.LeakyReLU(self.alpha)

#     def forward(self, input, edge_attr, edge_index):
#         # Apply linear transformation to node features
#         h = torch.mm(input, self.W)

#         # Apply transformation to edge features and aggregate to node level
#         edge_h = torch.mm(edge_attr, self.W_edge)
#         edge_h_sum = torch.zeros_like(h)
#         for i in range(edge_index.size(1)):
#             edge_h_sum[edge_index[0, i]] += edge_h[i]

#         # Combine node features and aggregated edge features
#         h_combined = h + edge_h_sum

#         # Attention mechanism
#         N = h_combined.size(0)
#         a_input = torch.cat([h_combined.repeat(1, N).view(N * N, -1), h_combined.repeat(N, 1)], dim=1).view(N, -1, 2 * self.out_features)
#         e = self.leakyrelu(torch.matmul(a_input, self.a).squeeze(2))

#         # Convert adjacency matrix to attention scores
#         adjacency = torch.zeros((N, N), device=input.device)
#         adjacency[edge_index[0], edge_index[1]] = 1
#         zero_vec = -9e15 * torch.ones_like(e)
#         attention = torch.where(adjacency > 0, e, zero_vec)
#         attention = F.softmax(attention, dim=1)
#         attention = F.dropout(attention, self.dropout, training=self.training)
#         h_prime = torch.matmul(attention, h_combined)

#         if self.concat:
#             return F.elu(h_prime)
#         else:
#             return h_prime

# class SimplifiedGATModel(torch.nn.Module):
#     def __init__(self, num_node_features, num_edge_features, num_classes):
#         super(SimplifiedGATModel, self).__init__()
#         self.conv1 = GATConv(num_node_features, 16, heads=4, dropout=0.3)  # Regular GATConv layer
#         self.edge_conv = EdgeFeatureGATLayer(in_features=64, edge_features=num_edge_features, out_features=16, dropout=0.3, alpha=0.2, concat=True)

#         self.fc = torch.nn.Linear(16, num_classes)

#     def forward(self, data):
#         x, edge_index, edge_attr, batch = data.x, data.edge_index, data.edge_attr, data.batch

#         # Node features processing
#         x = F.dropout(x, p=0.3, training=self.training)
#         x = F.elu(self.conv1(x, edge_index))

#         # Edge features processing (optional: only at specific layers)
#         x = self.edge_conv(x, edge_attr, edge_index)

#         x = global_mean_pool(x, batch)
#         x = self.fc(x)

#         return x

# Example Usage
num_node_features = train_graphs[0].num_node_features
num_edge_features = train_graphs[0].num_edge_features
num_classes = 1
model = OptimizedGATModel(num_node_features, num_classes)
# model = SimplifiedGATModel(num_node_features, num_edge_features, num_classes)

def train(model, train_loader, val_loader, num_epochs=100):
    model.train()
    criterion = torch.nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    train_losses, val_losses = [], []
    val_rmses, val_r2s = [], []

    for epoch in range(num_epochs):
        total_loss = 0
        for data in train_loader:
            optimizer.zero_grad()
            out = model(data)  # This should now be graph-level output

            # Ensure target tensor is correctly shaped
            target = data.y.view(-1, 1)
            if out.shape != target.shape:
                raise ValueError(f"Output shape {out.shape} and target shape {target.shape} do not match")

            loss = criterion(out, target)
            loss.backward()
            optimizer.step()

            total_loss += loss.item() * data.num_graphs

        avg_loss = total_loss / len(train_loader.dataset)
        train_losses.append(avg_loss)
        print()
        print(f'Epoch {epoch+1}/{num_epochs}, Loss: {avg_loss:.4f}')
        
        loss, rmse, r2 = validate(model, val_loader)
        val_losses.append(loss)
        val_rmses.append(rmse)
        val_r2s.append(r2)
        print(f'Validation Loss: {loss:.4f}')
        print()
        print(f'Root Mean Squared Error: {rmse:.4f}')
        print(f'R^2 Score: {r2:.4f}')
        print()
        print('----------------------------------------------')
        
    # Plotting training and validation loss
    plt.figure(figsize=(12, 5))
    plt.subplot(1, 2, 1)
    plt.plot(train_losses, label='Training Loss')
    plt.plot(val_losses, label='Validation Loss')
    plt.title('Training and Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('Loss')
    plt.legend()

    # Plotting RMSE and R^2
    plt.subplot(1, 2, 2)
    plt.plot(val_rmses, label='Validation RMSE')
    plt.plot(val_r2s, label='Validation R^2 Score')
    plt.title('Validation RMSE and R^2 Score')
    plt.xlabel('Epochs')
    plt.ylabel('Metric Value')
    plt.legend()

    plt.tight_layout()
    plt.show()

def validate(model, loader):
    model.eval()
    total_loss = 0
    preds, actuals = [], []

    with torch.no_grad():
        for data in loader:
            # Assuming 'data' has the attributes 'x', 'edge_index', and 'y'
            out = model(data)
            out = out.view(-1)
            loss = F.mse_loss(out, data.y)
            total_loss += loss.item()

            preds.append(out)
            actuals.append(data.y)

    # Concatenate all the predictions and actual values
    all_preds = torch.cat(preds, dim=0)
    all_actuals = torch.cat(actuals, dim=0)

    # Calculate RMSE
    rmse = mean_squared_error(all_actuals.cpu(), all_preds.cpu(), squared=False)

    # Calculate R^2 Score
    r2 = r2_score(all_actuals.cpu(), all_preds.cpu())

    return total_loss / len(loader), rmse, r2

model = OptimizedGATModel(num_node_features, num_classes)
# model = SimplifiedGATModel(num_node_features, num_edge_features, num_classes)
train(model, train_loader, val_loader, num_epochs=500)