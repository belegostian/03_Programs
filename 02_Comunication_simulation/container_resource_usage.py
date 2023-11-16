import subprocess
import time
import re

def parse_docker_stats(output):
    """Parse the docker stats output to extract CPU %, MEM USAGE, NET I/O."""
    stats = re.search(r'(\d+\.\d+)%\s+(\d+\.\d+)([a-zA-Z]+)\s+/\s+\d+\.\d+[a-zA-Z]+\s+\d+\.\d+%\s+(\d+\.\d+)([a-zA-Z]+)\s+/\s+(\d+)([a-zA-Z]+)', output)
    if stats:
        cpu_percent = float(stats.group(1))
        mem_usage = float(stats.group(2))
        mem_unit = stats.group(3)
        net_in = float(stats.group(4))
        net_in_unit = stats.group(5)
        net_out = float(stats.group(6))
        net_out_unit = stats.group(7)
        return cpu_percent, mem_usage, mem_unit, net_in, net_in_unit, net_out, net_out_unit
    else:
        raise ValueError("Could not parse docker stats output.")

# Initialize variables to store total values
total_cpu = 0
total_mem = 0
total_net_in = 0
total_net_out = 0

# Container ID
container_id = "4d52b05f5d59"

for _ in range(300):
    # Execute docker stats command
    result = subprocess.run(['docker', 'stats', '--no-stream', container_id], capture_output=True, text=True)
    output = result.stdout

    # Parse the output
    cpu, mem, mem_unit, net_in, net_in_unit, net_out, net_out_unit = parse_docker_stats(output)

    # Accumulate the values
    total_cpu += cpu
    total_mem += mem
    total_net_in += net_in
    total_net_out += net_out

    # Wait for 1 second
    time.sleep(1)

# Calculate the averages
average_cpu = round(total_cpu / 300, 3)
average_mem = round(total_mem / 300, 3)
average_net_in = round(total_net_in / 300, 3)
average_net_out = round(total_net_out / 300, 3)

print(f"Average CPU Usage: {average_cpu}%")
print(f"Average Memory Usage: {average_mem} {mem_unit}")
print(f"Average Network Input: {average_net_in} {net_in_unit}")
print(f"Average Network Output: {average_net_out} {net_out_unit}")
