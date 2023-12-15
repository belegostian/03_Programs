import csv
import ast
import random
from functools import partial
from deap import base, creator, tools, algorithms
import matplotlib.pyplot as plt
from IPython.display import clear_output


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

# 定義目標方程式
subscription_split_fields = {
    'path': ','
}
subscription_dict = csv_to_dict('03_scenario_generation\\experiment_0\\subscriptions.csv', 'subscription', None, subscription_split_fields)

#* 設定 DEAP 模型參數
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
generations = 100

# Initialize lists to store fitness values for each generation
all_fitness = []

X_MIN, X_MAX = -5, 60
Y_MIN, Y_MAX = 0, 100

def dynamic_pareto_plot(all_fitness, ax, scat_current_gen, scat_previous_gens):
    # Update previous generations' points
    prev_gens_f1 = [f[0] for gen in all_fitness[:-1] for f in gen]
    prev_gens_f2 = [f[1] for gen in all_fitness[:-1] for f in gen]
    scat_previous_gens.set_data(prev_gens_f1, prev_gens_f2)

    # Update current generation's points
    current_gen = all_fitness[-1]
    current_gen_f1 = [f[0] for f in current_gen]
    current_gen_f2 = [f[1] for f in current_gen]
    scat_current_gen.set_data(current_gen_f1, current_gen_f2)

    # Check for points outside the defined bounds
    for x, y in zip(current_gen_f1, current_gen_f2):
        if x < X_MIN or x > X_MAX or y < Y_MIN or y > Y_MAX:
            print(f"Error point: ({x}, {y})")
            print()

    # Set fixed limits
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)

    plt.draw()
    plt.pause(0.1)  # Pause to update the plot

plt.ion()  # Turn on interactive mode
fig, ax = plt.subplots(figsize=(10, 6))
scat_current_gen, = ax.plot([], [], 'o', color='blue', label='Current Generation')
scat_previous_gens, = ax.plot([], [], 'o', color='gray', alpha=0.5, label='Previous Generations')
ax.set_xlim(X_MIN, X_MAX)
ax.set_ylim(Y_MIN, Y_MAX)
plt.xlabel("Fitness Objective 1")
plt.ylabel("Fitness Objective 2")
plt.grid(True)
plt.legend()
plt.show()

for gen in range(generations):
    offspring = algorithms.varAnd(population, toolbox, cxpb=0.5, mutpb=0.2)
    fits = toolbox.map(toolbox.evaluate, offspring)
    
    for ind in offspring:
        fitness_values = toolbox.evaluate(ind)
        ind.fitness.values = fitness_values
        
    population = toolbox.select(offspring, k=len(population))
    
    # Store fitness values of the current generation
    gen_fitness = [ind.fitness.values for ind in population]
    all_fitness.append(gen_fitness)

    # Update the dynamic plot
    dynamic_pareto_plot(all_fitness, ax, scat_current_gen, scat_previous_gens)
    print(f"Generation {gen} completed")

best_individuals = tools.selBest(population, k=3)  # Select the top 3 individuals
print("Best Individuals:")
for ind in best_individuals:
    print(ind, ind.fitness.values)

# Calculate and print statistics
fitness_values = [ind.fitness.values for ind in population]
QoS_mean_fitness = round(sum(f[0] for f in fitness_values) / len(population), 3)
RPN_mean_fitness = round(sum(f[1] for f in fitness_values) / len(population), 3)
print("Mean fitness:", QoS_mean_fitness, RPN_mean_fitness)

# wait for 
input("Press enter to exit ;)")