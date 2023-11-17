import subprocess

def run_all_scripts():
    print("Running all scripts concurrently")
    process = []
    process.append(subprocess.Popen(['python3', 'tool_wear_detection.py']))
    process.append(subprocess.Popen(['python3', 'automatic_workpiece_changing.py']))
    process.append(subprocess.Popen(['python3', 'job_scheduling.py']))
    
    for p in process:
        p.wait()
        
if __name__ == '__main__':
    run_all_scripts()
