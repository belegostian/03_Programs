# Example of basic event probabilities
basic_event_probs = {
    'A': 0.01,
    'B': 0.02,
    'C': 0.03,
    # Add all basic events with their respective probabilities
}

p_host_failure = 0.001
p_link_failure = 0.001
p_switch_failure = 0.001

def calculate_port_overload_probability():
    
    return p_port_overload

def calculate_app_resource_crunched_probability():
    
    return p_app_resource_crunched

def calculate_app_connection_excessive_probability():
    
    return p_app_connection_excessive



# Define logic gates
def and_gate(*args):
    probability = 1
    for event_prob in args:
        probability *= event_prob
    return probability

def or_gate(*args):
    probability = 1
    for event_prob in args:
        probability *= (1 - event_prob)
    return 1 - probability

# Define middle event probabilities based on their logic gate and basic event inputs
# Placeholder names and logic are used here; these should be replaced with actual event names and logic
middle_event_probs = {
    'M1': or_gate(basic_event_probs['A'], basic_event_probs['B']),
    'M2': and_gate(basic_event_probs['C'], basic_event_probs['A']),
    # Define all middle events according to the FTA structure
}

# Top event probability calculation
# This should be constructed based on the actual FTA top event logic
top_event_probability = or_gate(
    middle_event_probs['M1'],
    middle_event_probs['M2'],
    # Include all relevant middle events and/or basic events
)

print(f"The probability of the top event is: {top_event_probability:.4f}")
