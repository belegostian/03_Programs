import os
import re
import asyncio
import asyncua
import logging
import time
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

polling_interval = 10 # seconds

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
                    sleep_time = max(polling_interval - elapsed, 0) # 大概還會誤差0.01秒
                    
                    await asyncio.sleep(sleep_time) 
                
        except (OSError, asyncua.ua.uaerrors._base.UaError, asyncio.TimeoutError) as e:
            _logger.error(f"Connection failed: {e}")
            _logger.info("Attempting to reconnect in 5 seconds...")
            await asyncio.sleep(5) # 每5秒嘗試重新連線
        
        except Exception as e:
            _logger.exception("An unexpected error occurred: ", exc_info=e)
            break

async def main():
    # read env variables from file
    # with open('env_variables.env', 'r') as f:
    #     for line in f:
    #         key, value = line.strip().split('=', 1)
    #         os.environ[key] = value
    # server_ips = os.getenv('SERVER_IPS').split(',')
            
    # read env variables from docker runtime input
    server_ips_env = os.getenv('JS_SERVER_IPS')
    if server_ips_env:
        server_ips = server_ips_env.split(',')
    else:
        _logger.error('The SERVER_IPS environment variable is not set.')
        exit(1)
        
    # for testing
    # server_ips = ['127.0.0.1']
    
    ip_pattern = re.compile(r'^\d{1,3}(\.\d{1,3}){3}$')
    valid_ips = [ip for ip in server_ips if ip_pattern.match(ip)]
    if not valid_ips:
        print("No valid IPs found.")
        return    
    
    server_urls = [f"opc.tcp://{ip}:4840" for ip in server_ips]
    tasks = [server_task(url) for url in server_urls]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())