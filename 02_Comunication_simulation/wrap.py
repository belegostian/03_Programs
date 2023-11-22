import os
import shutil
import itertools
import subprocess
from datetime import datetime

# Function to extract initials from folder names
def get_initials(name):
    return ''.join([word[0] for word in name.split() if word.isalpha()])

def modify_dockerfile(subfolder_path, python_scripts):
    dockerfile_path = os.path.join(subfolder_path, 'Dockerfile')
    with open(dockerfile_path, 'r') as file:
        dockerfile_content = file.readlines()

    # Find the line to replace
    replacement_index = next(i for i, line in enumerate(dockerfile_content) if 'COPY' in line and '.' in line)

    # Generate new COPY commands
    new_copy_commands = [f"COPY ./{os.path.basename(script)} /app/{os.path.basename(script)}\n" for script in python_scripts]
    new_copy_commands.append("COPY ./wrapper.py /app/wrapper.py\n")
    new_copy_commands.append("COPY ./requirements.txt /app/requirements.txt\n")

    # Replace the line
    dockerfile_content[replacement_index:replacement_index + 1] = new_copy_commands

    # Write back to Dockerfile
    with open(dockerfile_path, 'w') as file:
        file.writelines(dockerfile_content)

def modify_wrapper_py(subfolder_path, python_scripts):
    wrapper_path = os.path.join(subfolder_path, 'wrapper.py')
    with open(wrapper_path, 'r') as file:
        wrapper_content = file.readlines()

    # Find the line to insert new commands
    insert_index = next(i for i, line in enumerate(wrapper_content) if 'process = []' in line) + 1

    # Generate new process.append() commands
    new_process_commands = [f"    process.append(subprocess.Popen(['python3', '{os.path.basename(script)}']))\n" for script in python_scripts]

    # Insert the new lines
    wrapper_content[insert_index:insert_index] = new_process_commands

    # Write back to wrapper.py
    with open(wrapper_path, 'w') as file:
        file.writelines(wrapper_content)

# Create "[app] wrapped" folder
wrapped_folder = '[app] wrapped apps'
if not os.path.exists(wrapped_folder):
    os.makedirs(wrapped_folder)

# List Python scripts from "[app]" folders
python_files = {}
for root, dirs, files in os.walk('.'):
    if '[app]' in os.path.basename(root):
        python_files_in_dir = [os.path.join(root, file) for file in files if file.endswith('.py')]
        if python_files_in_dir:
            python_files[root] = python_files_in_dir
            
        # 以下在Windows OS未經測試
        os.chdir(root)

        # Format image_name: remove '[app]', strip spaces, and replace spaces with underscores
        dir_name = os.path.basename(root)
        image_name = dir_name.replace('[app]', '').strip().replace(' ', '_')
        tag = 'ver2'
        image_name = f"{image_name.lower()}:{tag}"

        subprocess.run(['sudo', 'docker', 'build', '--pull', '--rm', '-f', 'Dockerfile', '-t', image_name, '.'])
        os.chdir('..')

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
wrapper_path = 'wrapper.py'

for subfolder in os.listdir(wrapped_folder):
    subfolder_path = os.path.join(wrapped_folder, subfolder)
    if os.path.isdir(subfolder_path):
        shutil.copy(wrapper_path, subfolder_path)
        shutil.copy(dockerfile_path, subfolder_path)
        
        # List of python scripts in the current subfolder
        python_scripts_in_subfolder = [f for f in os.listdir(subfolder_path) if f.endswith('.py') and f != 'wrapper.py']
        
        modify_wrapper_py(subfolder_path, python_scripts_in_subfolder)
        modify_dockerfile(subfolder_path, python_scripts_in_subfolder)
        
        # 以下在Windows OS未經測試
        os.chdir(subfolder_path)
        
        subprocess.run(['pipreqs', '--force'])
        
        tag = datetime.now().strftime("%m-%d-%H")
        image_name = f"{subfolder.lower()}:{tag}"
        
        subprocess.run(['sudo', 'docker', 'build', '--pull', '--rm', '-f', 'Dockerfile', '-t', image_name, '.'])
        os.chdir('../../')

print("Operation completed.")
