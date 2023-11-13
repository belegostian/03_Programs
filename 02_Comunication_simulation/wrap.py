import os
import shutil
import itertools
import subprocess
from datetime import datetime

# Function to extract initials from folder names
def get_initials(name):
    return ''.join([word[0] for word in name.split() if word.isalpha()])

# Create "[App] wrapped" folder
wrapped_folder = '[App] Wrapped Apps'
if not os.path.exists(wrapped_folder):
    os.makedirs(wrapped_folder)

# List Python scripts from "[App]" folders
python_files = {}
for root, dirs, files in os.walk('.'):
    if '[App]' in os.path.basename(root):
        python_files_in_dir = [os.path.join(root, file) for file in files if file.endswith('.py')]
        if python_files_in_dir:
            python_files[root] = python_files_in_dir

# Generate combinations and create subfolders
for num in range(2, len(python_files) + 1):
    for combo in itertools.combinations(python_files.items(), num):
        folder_names = [get_initials(os.path.basename(name)) for name, _ in combo]
        subfolder_name = '_'.join(folder_names)
        subfolder_path = os.path.join(wrapped_folder, subfolder_name)
        if not os.path.exists(subfolder_path):
            os.makedirs(subfolder_path)

        # Copy files to the new subfolder
        for _, files in combo:
            for file in files:
                shutil.copy(file, subfolder_path)

dockerfile_path = 'Dockerfile'
for subfolder in os.listdir(wrapped_folder):
    subfolder_path = os.path.join(wrapped_folder, subfolder)
    if os.path.isdir(subfolder_path):
        shutil.copy(dockerfile_path, subfolder_path)
        
        # 以下在Windows OS未經測試
        os.chdir(subfolder_path)
        
        subprocess.run(['pipreqs', '--force'])
        
        tag = datetime.now().strftime("%m-%d-%M-%S")
        image_name = f"{subfolder.lower()}:{tag}"
        subprocess.run(['docker', 'build', '--pull', '--rm', '-f', 'Dockerfile', '-t', image_name, '.'])
        
        os.chdir('../../')
        

print("Operation completed.")