import asyncio
import logging
import copy
import time
import numpy as np
import matplotlib.pyplot as plt
from asyncua import ua, Client

        
SERVER_URL = 'opc.tcp://localhost:4840'
SERVER_NAME = 'Test CNC Server'

_logger = logging.getLogger(__name__)

def initialize_plot():
    plt.ion() # Interactive mode on
    fig, ax = plt.subplots(2, 1)
    speed_line, = ax[0].plot([], [], label='Speed')
    torque_line, = ax[1].plot([], [], label='Torque')
    ax[0].set_xlabel('Time')
    ax[0].set_ylabel('Speed')
    ax[1].set_xlabel('Time')
    ax[1].set_ylabel('Torque')
    return ax, speed_line, torque_line

def update_plot(ax, speed_line, torque_line, time_values, speed_values, torque_values):
    if len(time_values) > 100:
        time_values = time_values[-100:]
        speed_values = speed_values[-100:]
        torque_values = torque_values[-100:]
    
    speed_line.set_xdata(time_values)
    speed_line.set_ydata(speed_values)
    torque_line.set_xdata(time_values)
    torque_line.set_ydata(torque_values)
    
    ax[0].relim(); ax[0].autoscale_view() # Rescale axes
    ax[1].relim(); ax[1].autoscale_view() # Rescale axes
    plt.draw()
    plt.pause(0.01) # Short pause to allow update
    
    return time_values, speed_values, torque_values # Return updated values
        
async def main():
    async with Client(url=SERVER_URL) as client:
        
        # 指定節點ID搜尋
        CmdSpeed = client.get_node(ua.NodeId(2019, 1))
        CmdTorque = client.get_node(ua.NodeId(2032, 1))
        
        ActSpeed = client.get_node(ua.NodeId(2005, 1))
        act_speed = copy.copy(await ActSpeed.read_value())
        ActTorque = client.get_node(ua.NodeId(2029, 1))
        act_torque = copy.copy(await ActTorque.read_value())
        ActPower = client.get_node(ua.NodeId(2026, 1))
        act_power = copy.copy(await ActPower.read_value())
        
        Voltage = client.get_node(ua.NodeId(2037, 1))
        voltage = copy.copy(await Voltage.read_value())
        Current = client.get_node(ua.NodeId(2039, 1))
        current = copy.copy(await Current.read_value())
        
        # 按階層搜尋
        # Voltage = await client.nodes.root.get_child(['0:Objects', '3:Machines', '1tCNC_spindle', '1:Voltage'])
        # Current = await client.nodes.root.get_child(['0:Objects', '3:Machines', '1tCNC_spindle', '1:Current'])
        
        # Initialize the plot
        ax, speed_line, torque_line = initialize_plot()
        time_values, speed_values, torque_values = [], [], []
        
        while True:
            start_time = time.time()
            
            # 網路負荷
            await CmdSpeed.write_value(8000.0) # 指定轉速
            await CmdTorque.write_value(90.0) # 指定轉矩
            
            ActSpeed = client.get_node(ua.NodeId(2005, 1))
            act_speed = copy.copy(await ActSpeed.read_value())
            ActTorque = client.get_node(ua.NodeId(2029, 1))
            act_torque = copy.copy(await ActTorque.read_value())
            ActPower = client.get_node(ua.NodeId(2026, 1))
            act_power = copy.copy(await ActPower.read_value())
            
            Voltage = client.get_node(ua.NodeId(2037, 1))
            voltage = copy.copy(await Voltage.read_value())
            Current = client.get_node(ua.NodeId(2039, 1))
            current = copy.copy(await Current.read_value())
            
            await asyncio.sleep(0.5) 
            
            _logger.info("\n實際轉速: %d rpm, 實際轉矩: %d Nm, 實際功率: %d W", act_speed, act_torque, act_power)
            _logger.info("電壓: %d V, 電流: %d I\n", voltage, current)
            
            mid_time = time.time()

            # CPU負荷
            time_values.append(start_time)
            speed_values.append(act_speed)
            torque_values.append(act_torque)
            
            time_values, speed_values, torque_values = update_plot(ax, speed_line, torque_line, time_values, speed_values, torque_values)
            
            size = int(100)
            iterations = int(50)
            for _ in range(iterations):
                a = np.random.rand(size, size)
                b = np.random.rand(size, size)
                np.dot(a, b)
                
            _logger.info("\n總耗時: %d ms, 網路請求耗時: %d ms, 計算耗時: %d ms", (time.time() - start_time)* 1000, (mid_time - start_time)* 1000, (time.time() - mid_time)* 1000)
            

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
