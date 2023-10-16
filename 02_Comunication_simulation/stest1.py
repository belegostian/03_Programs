
#* Part1: Defiine nodeset of representational devices
class DeviceModel:
    def __init__(self, name, data_form):
        self.name = name
        self.data_form = data_form

class CNC(DeviceModel):
    def __init__(self, name):
        super().__init__(name, 'CNC Data Form')
        # Specific attributes for CNC
        self.spindle_speed = None
        self.feed_rate = None
        self.tool_position = None

class Robot(DeviceModel):
    def __init__(self, name):
        super().__init__(name, 'Robot Data Form')
        # Specific attributes for Robot
        self.arm_positions = None
        self.gripper_state = None
        self.motion_speed = None

class Sensor(DeviceModel):
    def __init__(self, name):
        super().__init__(name, 'Sensor Data Form')
        # Specific attributes for Sensor
        self.sensor_reading = None
        self.status = None

#* Part2: generate persudo data
import itertools
import random

class DataGenerator:
    def __init__(self, data=None, lower_limit=None, upper_limit=None):
        self.data = data if data is not None else []
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit
        self.data_iter = itertools.cycle(self.data) if self.data else None

    def sequential_data(self):
        if self.data_iter is None:
            raise ValueError('Data is not set for sequential generation')
        return next(self.data_iter)

    def random_data(self):
        if self.lower_limit is None or self.upper_limit is None:
            raise ValueError('Upper and lower limit not set for random generation')
        return random.uniform(self.lower_limit, self.upper_limit)

# Sequential data generation
seq_generator = DataGenerator(data=[1, 2, 3, 4, 5])
print(seq_generator.sequential_data())  # prints: 1
print(seq_generator.sequential_data())  # prints: 2
print(seq_generator.sequential_data())  # prints: 3
# and so on...

# Random data generation
rand_generator = DataGenerator(lower_limit=0, upper_limit=100)
print(rand_generator.random_data())  # prints a random number between 0 and 100

#* Part3: set up OPC server
from opcua import ua, uamethod, Server, Client

class OPCUAServerWrapper:
    def __init__(self, url):
        self.server = Server()
        self.server.set_endpoint(url)
        self.server.init()

    def init_node(self, device_model):
        root = self.server.get_root_node()
        objects = self.server.get_objects_node()
        
        # Initializing node for each attribute in device_model
        for attribute in vars(device_model):
            objects.add_variable('ns=2;s=' + device_model.name + '.' + attribute, attribute, getattr(device_model, attribute))
        
    def get_node(self, node_id):
        return self.server.get_node(node_id)
    
    def set_node(self, node_id, value):
        node = self.get_node(node_id)
        node.set_value(value)

class OPCUAClientWrapper:
    def __init__(self, url):
        self.client = Client(url)
        self.client.connect()

    def init_node(self, device_model):
        root = self.client.get_root_node()
        
        # Initializing node for each attribute in device_model
        for attribute in vars(device_model):
            var = root.get_child(['0:Objects', '2:' + device_model.name, '2:' + attribute])
            setattr(self, attribute, var)

    def get_node(self, node_id):
        return self.client.get_node(node_id)
    
    def set_node(self, node_id, value):
        node = self.get_node(node_id)
        node.set_value(value)

# Initialize server and client with the same device model
device_model = CNC('Device1')
server = OPCUAServerWrapper("opc.tcp://localhost:4840")
client = OPCUAClientWrapper("opc.tcp://localhost:4840")

# Initialize nodes
server.init_node(device_model)
client.init_node(device_model)

# Set and get node values
server.set_node('ns=2;s=Device1.spindle_speed', 1000)
print(client.get_node('ns=2;s=Device1.spindle_speed').get_value())  # prints: 1000


#* Part4: Send and receive data
import time
import threading

class CommunicationController:
    def __init__(self, device_model, data_generator, opcua_server, opcua_client, 
                 sending_frequency, cycle_size, cycle_duration, cycle_interval, polling_frequency):
        self.device_model = device_model
        self.data_generator = data_generator
        self.opcua_server = opcua_server
        self.opcua_client = opcua_client
        self.sending_frequency = sending_frequency
        self.cycle_size = cycle_size
        self.cycle_duration = cycle_duration
        self.cycle_interval = cycle_interval
        self.polling_frequency = polling_frequency

    def connect(self):
        self.opcua_server.server.start()
        self.opcua_client.client.connect()

    def disconnect(self):
        self.opcua_server.server.stop()
        self.opcua_client.client.disconnect()

    def start_sending(self):
        # Start a new thread to send data
        threading.Thread(target=self._send_data).start()

    def start_receiving(self):
        # Start a new thread to receive data
        threading.Thread(target=self._receive_data).start()

    def _send_data(self):
        while True:
            for _ in range(self.cycle_size):
                # Send data for each attribute in device model
                for attribute in vars(self.device_model):
                    value = self.data_generator.sequential_data()
                    self.opcua_server.set_node('ns=2;s=' + self.device_model.name + '.' + attribute, value)
                    time.sleep(1 / self.sending_frequency)
                time.sleep(self.cycle_duration)
            time.sleep(self.cycle_interval)

    def _receive_data(self):
        while True:
            # Receive data for each attribute in device model
            for attribute in vars(self.device_model):
                value = self.opcua_client.get_node('ns=2;s=' + self.device_model.name + '.' + attribute).get_value()
                print(f'Received data: {value}')
            time.sleep(1 / self.polling_frequency)

# Initialize device model, data generator, server, client
device_model = CNC('Device1')
data_generator = DataGenerator(data=[1, 2, 3, 4, 5])
server = OPCUAServerWrapper("opc.tcp://localhost:4840")
client = OPCUAClientWrapper("opc.tcp://localhost:4840")
server.init_node(device_model)
client.init_node(device_model)

# Initialize communication controller
comm_controller = CommunicationController(device_model, data_generator, server, client, 
                                          sending_frequency=10, cycle_size=100, cycle_duration=10, 
                                          cycle_interval=1, polling_frequency=10)

# Connect server and client
comm_controller.connect()

# Start sending and receiving data
comm_controller.start_sending()
comm_controller.start_receiving()

# Disconnect server and client when done
# comm_controller.disconnect()
