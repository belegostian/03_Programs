import csv
import json

# Your device dictionary
...

# # Convert the dictionary to a list of rows
# rows = []
# for device, attributes in device_dict.items():
#     row = {"device": device, **attributes}
#     rows.append(row)

# # File name for the CSV
# csv_file = 'devices.csv'

# # Write the rows to a CSV file
# with open(csv_file, 'w', newline='') as file:
#     writer = csv.DictWriter(file, fieldnames=["device", "type", "bandwidth", "group"])
#     writer.writeheader()
#     writer.writerows(rows)

# rows = []
# for app, attributes in application_dict.items():
#     row = {**attributes, "application": app}
#     row["target_device"] = ", ".join(row["target_device"])  # Convert list to string
#     rows.append(row)

# csv_file = "applications.csv"

# with open(csv_file, "w", newline="") as file:
#     writer = csv.DictWriter(
#         file,
#         fieldnames=[
#             "application",
#             "name",
#             "response_timeout",
#             "cpu_usage",
#             "memory_usage",
#             "packet_sending",
#             "packet_receiving",
#             "target_device",
#         ],
#     )
#     writer.writeheader()
#     writer.writerows(rows)

# rows = []
# for computer, attributes in computer_dict.items():
#     # Serialize the list to a string
#     attributes['running_apps'] = json.dumps(attributes['running_apps'])
#     row = {"computer": computer, **attributes}
#     rows.append(row)

# csv_file = 'computers.csv'

# with open(csv_file, 'w', newline='') as file:
#     writer = csv.DictWriter(file, fieldnames=["computer", "cpu", "memory", "bandwidth", "group", "running_apps"])
#     writer.writeheader()
#     writer.writerows(rows)

# rows = []
# for switch, attributes in switch_dict.items():
#     row = {"switch": switch, **attributes}
#     rows.append(row)

# csv_file = 'switches.csv'

# with open(csv_file, 'w', newline='') as file:
#     writer = csv.DictWriter(file, fieldnames=["switch", "bandwidth", "forward_delay"])
#     writer.writeheader()
#     writer.writerows(rows)

# rows = []
# for sub, attrs in subscription_dict.items():
#     for device in attrs['devices']:
#         row = {"subscription": sub, "device": device, **{k: v for k, v in attrs.items() if k != 'devices'}}
#         rows.append(row)

# csv_file = 'subscriptions.csv'

# with open(csv_file, 'w', newline='') as file:
#     writer = csv.DictWriter(file, fieldnames=["subscription", "device", "app", "weight"])
#     writer.writeheader()
#     writer.writerows(rows)