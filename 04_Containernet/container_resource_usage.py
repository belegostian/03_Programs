import subprocess
import time

def parse_docker_stats(output):
    """Parse the docker stats output to extract CPU %, MEM USAGE, NET I/O."""
    # Split the output into lines and use the second line (index 1)
    lines = output.split('\n')
    stats_line = lines[1]

    # Split the line by spaces and filter out empty strings and slashes
    stats = [stat for stat in stats_line.split(' ') if stat and stat != '/']

    # Extract the required metrics
    cpu_percent = stats[2]  # CPU %
    mem_usage = stats[3]  # MEM USAGE
    net_i = stats[6]  # NET I
    net_o = stats[7]  # NET O
    return cpu_percent, mem_usage, net_i, net_o

# Initialize variables to store total values
total_cpu = 0
total_mem_usage = 0
total_net_i = 0
total_net_o = 0

# Container ID
container_id = "6d96a8d93af4"

for _ in range(300):
    # Execute docker stats command
    result = subprocess.run(['sudo', 'docker', 'stats', '--no-stream', container_id], capture_output=True, text=True)
    output = result.stdout

    # Parse the output
    cpu, mem_usage, net_i, net_o = parse_docker_stats(output)

    # Convert CPU percentage to a float and accumulate
    total_cpu += float(cpu.strip('%'))

    # Convert memory usage to a float (assuming MiB for simplicity)
    mem_value, mem_unit = mem_usage[:-3], mem_usage[-3:]
    total_mem_usage += float(mem_value)

    # Split network I/O and convert to float (assuming kB for simplicity)
    total_net_i += float(net_i[:-2])
    total_net_o += float(net_o[:-2])

    # Wait for 1 second
    time.sleep(1)

# Calculate the averages
average_cpu = total_cpu / 300
average_mem_usage = total_mem_usage / 300
average_net_i = total_net_i / 300
average_net_o = total_net_o / 300

print()
print(f"Average CPU Usage: {average_cpu}%")
print(f"Average Memory Usage: {average_mem_usage} MiB")  # Assuming MiB
print(f"Average Network Input: {average_net_i} kB")  # Assuming kB
print(f"Average Network Output: {average_net_o} kB")  # Assuming kB
