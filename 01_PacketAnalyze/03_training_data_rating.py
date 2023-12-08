import os
import glob
import pandas as pd
import re

def extract_number(subscription_order):
    match = re.search(r'\d+', subscription_order)
    return int(match.group()) if match else 0


base_path = '03_scenario_generation\\experiment_0'
scenario_folders = glob.glob(os.path.join(base_path, f'*scenario*'))

input_file = '01_PacketAnalyze\\data_training.csv'
data_training_df = pd.read_csv(input_file)

for folder in scenario_folders:
    filtered_df = data_training_df[data_training_df['Scenario'] == os.path.basename(folder)].copy()
    
    filtered_df['Subscription Order Numeric'] = filtered_df['Subscription Order'].apply(extract_number)
    sorted_df = filtered_df.sort_values(by='Subscription Order Numeric')
    qos_scores = sorted_df['QoS Score']
    
    subscription_file = os.path.join(folder, 'subscription_paths.csv')
    
    subscription_df = pd.read_csv(subscription_file)
    if len(subscription_df) == len(qos_scores):
        subscription_df['QoS Score'] = qos_scores.values
        subscription_df.to_csv(subscription_file, index=False)
    else:
        print(f"Row count mismatch in {subscription_file}. Skipping update.")