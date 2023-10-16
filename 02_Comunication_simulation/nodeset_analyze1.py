from collections import defaultdict
import xml.etree.ElementTree as ET
import csv

FILE_PATH = 'SimpleCNC.xml'
NODE_TABLE = 'SimpleCNC.csv'
NODE_RELATION_TABLE = 'SimpleCNC_Relation.csv'
MERMAID_CODE = 'SimpleCNC_Mermaid.txt'

#* This script parses the XML file and extracts the following information for each element:

# Parse the XML file
tree = ET.parse(FILE_PATH)
root = tree.getroot()

# Helper function to extract NodeId number
def extract_nodeid(nodeid):
    return nodeid.split('=')[-1]

# Helper function to extract namespace and reference ID
def extract_namespace_reference(reference):
    parts = reference.split(';')
    if len(parts) == 1:  # No namespace specified, default to "1" #! default to "0"
        namespace = '0' 
        reference_id = parts[0].split('=')[-1]
    else:  # Namespace specified
        namespace = parts[0].split('=')[-1]
        reference_id = parts[1].split('=')[-1]
    return namespace, reference_id

# Helper function to extract references
def extract_references(references_element):
    references = {}
    for reference in references_element:
        namespace, reference_id = extract_namespace_reference(reference.text)
        if namespace in references:
            references[namespace].append(reference_id)
        else:
            references[namespace] = [reference_id]
    return references

# Prepare for CSV writing
csv_data = []
header = ["UA Type", "DisplayName", "NodeId", "References", "Description"]

# Iterate over all elements in the XML tree
for element in root.iter():
    if 'UAObjectType' in element.tag or 'UAVariable' in element.tag or 'UAObject' in element.tag:
        ua_type = element.tag.split('}')[-1]
        display_name = element.find('{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}DisplayName').text
        nodeid = extract_nodeid(element.attrib.get('NodeId', ''))
        description_element = element.find('{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}Description')
        description = description_element.text if description_element is not None else ''
        references_element = element.find('{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}References')
        references = extract_references(references_element) if references_element is not None else {}
        # Convert references dict to string
        references_str = '; '.join([f"{ns}:[{', '.join(ids)}]" for ns, ids in references.items()])
        csv_data.append([ua_type, display_name, nodeid, references_str, description])

# Write data to CSV file
with open(NODE_TABLE, 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(header)
    writer.writerows(csv_data)

#* This script parses the XML file and extracts the relationship between nodes.

# Step 1: Build a tree structure
tree = defaultdict(list)
node_names = {}

# Iterate over all elements in the XML tree
for element in root.iter():
    if 'UAObjectType' in element.tag or 'UAVariable' in element.tag or 'UAObject' in element.tag:
        nodeid = extract_nodeid(element.attrib.get('NodeId', ''))
        parent_nodeid = extract_nodeid(element.attrib.get('ParentNodeId', '')) if 'ParentNodeId' in element.attrib else None
        display_name = element.find('{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}DisplayName').text
        node_names[nodeid] = display_name  # Store node names for later use
        if parent_nodeid:
            tree[parent_nodeid].append(nodeid)  # Add child to parent in tree

# Step 2: Perform a depth-first traversal and record the paths
paths = []

def dfs(nodeid, path):
    # Record the path
    paths.append(path)
    # Visit all children
    for child_nodeid in tree[nodeid]:
        dfs(child_nodeid, path + [node_names[child_nodeid]])

# Start traversal from each root (a node without a parent)
for nodeid in node_names:
    # if nodeid not in tree:  # No children, skip
    #     continue
    if any(nodeid in children for children in tree.values()):  # This node is a child of another node, skip
        continue
    dfs(nodeid, [node_names[nodeid]])

# Step 3: Write paths to CSV file
with open(NODE_RELATION_TABLE, 'w', newline='') as file:
    writer = csv.writer(file)
    for path in paths:
        writer.writerow(path)

#* Generate Mermaid syntax

# Helper function to perform a depth-first traversal and generate Mermaid syntax
def dfs_mermaid(nodeid, indent):
    mermaid_syntax = '  ' * indent + node_names[nodeid] + '\n'
    for child_nodeid in tree[nodeid]:
        mermaid_syntax += dfs_mermaid(child_nodeid, indent + 1)
    return mermaid_syntax

mermaid_syntax = "mindmap\n"
for nodeid in node_names:
    if nodeid not in tree:  # No children, skip
        continue
    if any(nodeid in children for children in tree.values()):  # This node is a child of another node, skip
        continue
    mermaid_syntax += dfs_mermaid(nodeid, 1)

# Save the Mermaid syntax to a text file
with open(MERMAID_CODE, 'w') as file:
    file.write(mermaid_syntax)