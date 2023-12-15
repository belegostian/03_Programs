import os
import csv
import ast
import json
import random
from functools import partial
import networkx as nx
from deap import base, creator, tools, algorithms

import GAT # for objective function 1
import RPN # for objective function 2
import Individual

# 第一代個體生成
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

application_transformations = {
    'response_timeout': float,
    'cpu_usage (%)': float,
    'memory_usage (MiB)': float,
    'packet_sending (kB)': float,
    'packet_receiving (kB)': float
}
application_dict = csv_to_dict('03_scenario_generation\\experiment_0\\applications.csv', 'application', application_transformations)

computer_transformations = {
    'running_apps': ast.literal_eval,
    'cpu': float,
    'memory': int,
    'bandwidth': int,
    'group': lambda x: None if x == '' else int(x)
}
computer_dict = csv_to_dict('03_scenario_generation\\experiment_0\\computers.csv', 'computer', computer_transformations)

device_transformations = {
    'bandwidth': int,
    'group': int
}
device_dict = csv_to_dict('03_scenario_generation\\experiment_0\\devices.csv', 'device', device_transformations)

switch_transformations = {
    'bandwidth': int,
    'forward_delay': float
}
switch_dict = csv_to_dict('03_scenario_generation\\experiment_0\\switches.csv', 'switch', switch_transformations)

# individual = Individual.generate_individual(application_dict, computer_dict, device_dict, switch_dict)

# 定義目標方程式
subscription_split_fields = {
    'path': ','
}
subscription_dict = csv_to_dict('03_scenario_generation\\experiment_0\\subscriptions.csv', 'subscription', None, subscription_split_fields)

# gat_rate = GAT.graph_attention_network(individual)
# rpn_rate = RPN.risk_primary_number(individual)

# 設定 DEAP 模型參數
# Create types
creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0))  # Assuming minimization problems
creator.create("Individual", list, fitness=creator.FitnessMulti)

# Initialize toolbox
toolbox = base.Toolbox()

# Define how to create an individual and the population
toolbox.register("individual", tools.initIterate, creator.Individual, partial(Individual.generate_individual, application_dict, computer_dict, device_dict, switch_dict))
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

def custom_mutate(individual, indpb):
    # 前一部分的變異
    possible_values = list(switch_dict)
    for i in range(len(list(switch_dict) + list(device_dict) + list(computer_dict))):
        if random.random() < indpb:
            individual[i] = random.choice(possible_values)
    
    # 後一部分的變異
    possible_values = list(application_dict)
    for i in range(len(list(switch_dict) + list(device_dict) + list(computer_dict)), len(individual)):
        if random.random() < indpb:
            n = random.randint(1, len(possible_values))
            individual[i] = random.sample(possible_values, n)

    return (individual,)

# Genetic operators
toolbox.register("mate", tools.cxTwoPoint)
toolbox.register("mutate", custom_mutate, indpb=0.05)
toolbox.register("select", tools.selNSGA2)

def evaluate_individual(individual):
    fitness1 = GAT.graph_attention_network(application_dict, computer_dict, device_dict, switch_dict, subscription_dict, individual)
    fitness2 = RPN.risk_primary_number(application_dict, computer_dict, device_dict, switch_dict, subscription_dict, individual)
    
    return fitness1, fitness2

toolbox.register("evaluate", evaluate_individual)

population = toolbox.population(n=50)
generations = 10

for gen in range(generations):
    offspring = algorithms.varAnd(population, toolbox, cxpb=0.5, mutpb=0.2)
    fits = toolbox.map(toolbox.evaluate, offspring)
    for ind in offspring:
        fitness_values = toolbox.evaluate(ind)
        ind.fitness.values = fitness_values
    population = toolbox.select(offspring, k=len(population))

best_individuals = tools.selBest(population, k=3)  # Select the top 3 individuals
print("Best Individuals:")
for ind in best_individuals:
    print(ind, ind.fitness.values)

# Calculate and print statistics
fitness_values = [ind.fitness.values for ind in population]
mean_fitness = sum(f[0] for f in fitness_values) / len(population)
print("Mean fitness:", mean_fitness)


