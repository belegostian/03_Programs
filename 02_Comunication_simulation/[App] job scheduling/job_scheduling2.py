import argparse
import asyncio
import asyncua
import logging
import time
import numpy as np
import matplotlib.pyplot as plt
from asyncua import ua, Client

_logger = logging.getLogger(__name__)

# Node IDs
Node_Dict = {
    'Manufacturer': ua.NodeId(2002, 1),
    'SerialNumber': ua.NodeId(2004, 1),
    'CncTypeName': ua.NodeId(20005),
    'ActStatus': ua.NodeId(20337),
    'ActMainProgramName': ua.NodeId(20324),
    'RunsPlanned': ua.NodeId(20442),
    'RunsCompleted': ua.NodeId(20441),
    'AlarmIdentifier': ua.NodeId(20011),
}

async def read_values(client, node_ids):
    return [await client.get_node(node_id).read_value() for node_id in node_ids]

async def main(server_urls):
    tasks = [server_task(url) for url in server_urls]
    await asyncio.gather(*tasks)
    
async def server_task(url):
    while True:
        try:
            async with Client(url=url) as client:
                _logger.info(f"Connected to Server at {url}")
                
                while True:
            
                    start_time = time.time()
                
                    manufacturer = await client.get_node(Node_Dict['Manufacturer']).read_value()
                    _logger.info("Manufacturer: %s", manufacturer)
                    
                    serial_number = await client.get_node(Node_Dict['SerialNumber']).read_value()
                    _logger.info("Serial Number: %s", serial_number)
                    
                    cnc_type_name = await client.get_node(Node_Dict['CncTypeName']).read_value()
                    _logger.info("CNC Type Name: %s", cnc_type_name)
                    
                    actual_status = await client.get_node(Node_Dict['ActStatus']).read_value()
                    _logger.info("Actual Status: %s", actual_status)
                    
                    actual_main_program_name = await client.get_node(Node_Dict['ActMainProgramName']).read_value()
                    _logger.info("Actual Main Program Name: %s", actual_main_program_name)
                    
                    runs_planned = await client.get_node(Node_Dict['RunsPlanned']).read_value()
                    _logger.info("Runs Planned: %s", runs_planned)
                    
                    runs_completed = await client.get_node(Node_Dict['RunsCompleted']).read_value()
                    _logger.info("Runs Completed: %s", runs_completed)
                    
                    alarm_identifier = await client.get_node(Node_Dict['AlarmIdentifier']).read_value()
                    _logger.info("Alarm Identifier: %s", alarm_identifier)
                    
                    elapsed = time.time() - start_time
                    sleep_time = max(1 - elapsed, 0)
                    
                    await asyncio.sleep(sleep_time) # 大概還會誤差0.01秒
                
        except (OSError, asyncua.ua.uaerrors._base.UaError) as e:
            _logger.error(f"Connection failed: {e}")
            _logger.info("Attempting to reconnect in 5 seconds...")
            await asyncio.sleep(5)
        
        except Exception as e:
            _logger.exception("An unexpected error occurred: ", exc_info=e)
            break  # Exit the loop for unexpected errors

async def main(server_ips):
    server_urls = [f"opc.tcp://{ip}:4840" for ip in server_ips]
    tasks = [server_task(url) for url in server_urls]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Connect to multiple OPC UA servers using IP addresses.')
    parser.add_argument('ips', nargs='+', help='List of server IP addresses to connect to.')
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())