import asyncio
import logging
import time
import numpy as np
import matplotlib.pyplot as plt
from asyncua import ua, Client

SERVER_URL = 'opc.tcp://localhost:4840'
SERVER_NAME = 'Test CNC Server'
_logger = logging.getLogger(__name__)

# Node IDs
CMD_SPEED_ID = ua.NodeId(2019, 1)
CMD_TORQUE_ID = ua.NodeId(2032, 1)
ACT_SPEED_ID = ua.NodeId(2005, 1)
ACT_TORQUE_ID = ua.NodeId(2029, 1)
ACT_POWER_ID = ua.NodeId(2026, 1)
VOLTAGE_ID = ua.NodeId(2037, 1)
CURRENT_ID = ua.NodeId(2039, 1)

def initialize_plot():
    plt.ion()
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
    ax[0].relim(); ax[0].autoscale_view()
    ax[1].relim(); ax[1].autoscale_view()
    plt.draw()
    plt.pause(0.01)
    return time_values, speed_values, torque_values

async def read_values(client, node_ids):
    return [await client.get_node(node_id).read_value() for node_id in node_ids]

async def main():
    async with Client(url=SERVER_URL) as client:
        ax, speed_line, torque_line = initialize_plot()
        time_values, speed_values, torque_values = [], [], []

        while True:
            
            # 網路負荷
            start_time = time.time()
            await client.get_node(CMD_SPEED_ID).write_value(8000.0)
            await client.get_node(CMD_TORQUE_ID).write_value(90.0)
            
            act_speed, act_torque, act_power, voltage, current = await read_values(client, [ACT_SPEED_ID, ACT_TORQUE_ID, ACT_POWER_ID, VOLTAGE_ID, CURRENT_ID])
            await asyncio.sleep(0.5)
            
            _logger.info("\n實際轉速: %d rpm, 實際轉矩: %d Nm, 實際功率: %d W", act_speed, act_torque, act_power)
            _logger.info("電壓: %d V, 電流: %d I\n", voltage, current)
            
            # CPU 負荷
            mid_time = time.time()

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