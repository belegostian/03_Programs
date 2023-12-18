import csv
import ast
import numpy
import random
import matplotlib.pyplot as plt
from functools import partial
from deap import algorithms, base, benchmarks, creator, tools
from deap.benchmarks.tools import diversity, convergence, hypervolume

import GAT
import RPN
import Individual

def csv_to_dict(file_path, key_field, transformations=None, split_fields=None):
    data_dict = {}
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            key = row.pop(key_field)

            if split_fields:
                for field, delimiter in split_fields.items():
                    if field in row:
                        row[field] = row[field].split(delimiter)

            if transformations:
                for field, func in transformations.items():
                    if field in row:
                        row[field] = func(row[field])

            data_dict[key] = row
    return data_dict

def init_plot():
    plt.ion()
    fig, ax = plt.subplots(figsize=(10, 6))
    scat_current_gen, = ax.plot([], [], 'o', color='blue', label='Current Generation', zorder=2)
    scat_previous_gens, = ax.plot([], [], 'o', color='gray', alpha=0.5, label='Previous Generations', zorder=1)
    scat_pareto_front, = ax.plot([], [], 'o', color='red', label='Pareto Front', zorder=3)
    ax.set_xlim(-5, 60)
    ax.set_ylim(0, 100)
    plt.xlabel("QoS Score")
    plt.ylabel("RPN Score")
    plt.grid(True)
    plt.legend()
    plt.show()
    return fig, ax, scat_current_gen, scat_previous_gens, scat_pareto_front

def dynamic_pareto_plot(all_fitness, pareto_front, ax, scat_current_gen, scat_previous_gens, scat_pareto_front):
    # Update previous generations' points
    prev_gens_f1 = [f[0] for gen in all_fitness[:-1] for f in gen]
    prev_gens_f2 = [f[1] for gen in all_fitness[:-1] for f in gen]
    scat_previous_gens.set_data(prev_gens_f1, prev_gens_f2)

    # Update current generation's points
    current_gen = all_fitness[-1]
    current_gen_f1 = [f[0] for f in current_gen]
    current_gen_f2 = [f[1] for f in current_gen]
    scat_current_gen.set_data(current_gen_f1, current_gen_f2)
    
    pareto_front_x = [f[0] for f in pareto_front]
    pareto_front_y = [f[1] for f in pareto_front]
    scat_pareto_front.set_data(pareto_front_x, pareto_front_y)

    # Check for points outside the defined bounds
    X_MIN, X_MAX = -5, 60
    Y_MIN, Y_MAX = 0, 100
    
    for x, y in zip(current_gen_f1, current_gen_f2):
        if x < X_MIN or x > X_MAX or y < Y_MIN or y > Y_MAX:
            print(f"Error point: ({x}, {y})")
            print()

    # Set fixed limits
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    
    plt.draw()
    plt.pause(0.1)  # Pause to update the plot

class NSGAII:
    def __init__(self, application_dict, computer_dict, device_dict, switch_dict, subscription_dict):
        self.application_dict = application_dict
        self.computer_dict = computer_dict
        self.device_dict = device_dict
        self.switch_dict = switch_dict
        self.subscription_dict = subscription_dict

        self.toolbox = base.Toolbox()
        self.create_types()
        self.init_toolbox()

    def create_types(self):
        creator.create("FitnessMulti", base.Fitness, weights=(1.0, -1.0))
        creator.create("Individual", list, fitness=creator.FitnessMulti)

    def init_toolbox(self):
        self.toolbox.register("generate", Individual.generate_individual, self.application_dict, self.computer_dict, self.device_dict, self.switch_dict)
        self.toolbox.register("individual", tools.initIterate, creator.Individual, self.toolbox.generate)
        self.toolbox.register("population", tools.initRepeat, list, self.toolbox.individual)

        self.toolbox.register("mate", tools.cxTwoPoint)
        self.toolbox.register("mutate", self.custom_mutate, indpb=0.1)
        self.toolbox.register("evaluate", self.evaluate_individual)
        self.toolbox.register("select", tools.selNSGA2)

    def custom_mutate(self, individual, indpb):
        gen_seg = len(list(self.switch_dict) + list(self.device_dict) + list(self.computer_dict))
        # 前一部分的變異
        possible_values = list(self.switch_dict)
        for i in range(gen_seg):
            if random.random() < indpb:
                individual[i] = random.choice(possible_values)
        
        # 後一部分的變異
        possible_values = list(self.application_dict)
        for i in range(gen_seg, len(individual)):
            if random.random() < indpb:
                n = random.randint(1, len(possible_values))
                individual[i] = random.sample(possible_values, n)
                
        return (individual,)
        
    def evaluate_individual(self, individual):
        fitness1 = GAT.graph_attention_network(self.application_dict, self.computer_dict, self.device_dict, self.switch_dict, self.subscription_dict, individual)
        fitness2 = RPN.risk_primary_number(self.application_dict, self.computer_dict, self.device_dict, self.switch_dict, self.subscription_dict, individual)
        return fitness1, fitness2
    
    def run(self, cxpb, mutpb, mu, ngen, seed=None):
        random.seed(seed)
        
        fig, ax, scat_current_gen, scat_previous_gens, scat_pareto_front = init_plot()
        all_fitness = []
        
        stats = tools.Statistics(lambda ind: ind.fitness.values)
        stats.register("avg", numpy.mean, axis=0)
        stats.register("std", numpy.std, axis=0)
        stats.register("min", numpy.min, axis=0)
        stats.register("max", numpy.max, axis=0)

        logbook = tools.Logbook()
        logbook.header = "gen", "evals", "std", "min", "avg", "max"

        pop = self.toolbox.population(n=mu)
        
        invalid_ind = [ind for ind in pop if not ind.fitness.valid]
        fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
        for ind, fit in zip(invalid_ind, fitnesses):
            ind.fitness.values = fit
            
        pop = self.toolbox.select(pop, len(pop))
        
        record = stats.compile(pop)
        logbook.record(gen=0, evals=len(invalid_ind), **record)
        print(logbook.stream)
        
        for gen in range(ngen):
            offspring = tools.selTournamentDCD(pop, len(pop))
            offspring = [self.toolbox.clone(ind) for ind in offspring]
            
            for ind1, ind2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < cxpb:
                    self.toolbox.mate(ind1, ind2)
                    
                self.toolbox.mutate(ind1)
                self.toolbox.mutate(ind2)
                del ind1.fitness.values, ind2.fitness.values
                
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = self.toolbox.map(self.toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
                
            pop = self.toolbox.select(pop + offspring, mu)
            record = stats.compile(pop)
            logbook.record(gen=gen, evals=len(invalid_ind), **record)
            print(logbook.stream)
            
            gen_fitness = [ind.fitness.values for ind in pop]
            all_fitness.append(gen_fitness)
            
            pareto_front = tools.sortNondominated(pop, len(pop), first_front_only=True)[0]
            pareto_front_fitness = [ind.fitness.values for ind in pareto_front]
            
            dynamic_pareto_plot(all_fitness, pareto_front_fitness, ax, scat_current_gen, scat_previous_gens, scat_pareto_front)
            
        print(f"Final population hypervolume is {hypervolume(pop, [30.0, 50.0])}")
        return pop, logbook

def main(seed=None):
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

    subscription_split_fields = {
        'path': ','
    }
    subscription_dict = csv_to_dict('03_scenario_generation\\experiment_0\\subscriptions.csv', 'subscription', None, subscription_split_fields)
    
    nsga2 = NSGAII(application_dict, computer_dict, device_dict, switch_dict, subscription_dict)
    nsga2.run(cxpb=0.8, mutpb=0.2, mu=40, ngen=40)

if __name__ == '__main__':
    main()