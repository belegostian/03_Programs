import subprocess

def run_all_scripts():
    print("Running all scripts concurrently")
    process = []
    process.append(subprocess.Popen(['python3', 'clientA.py']))
    process.append(subprocess.Popen(['python3', 'clientB.py']))
    
    for p in process:
        p.wait()
        
if __name__ == '__main__':
    run_all_scripts()