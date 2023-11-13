import psutil
import time

pid = 30572

# If the PID was found, monitor the CPU and RAM usage
if pid:
    process = psutil.Process(pid)

    while True:
        cpu_usage = process.cpu_percent(interval=1)
        ram_usage = process.memory_info().rss / 1024 / 1024  # Convert to MB
        print(f'CPU Usage: {cpu_usage}%')
        print(f'RAM Usage: {ram_usage} MB')
        time.sleep(1)
else:
    print(f"{pid} not found.")
