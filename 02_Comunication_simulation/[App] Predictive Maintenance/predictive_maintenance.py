import os
import asyncio
import asyncua
import logging
import time
from asyncua import ua, Client

_logger = logging.getLogger(__name__)

# Node IDs
Node_Dict = {
    'ActLoad': ua.NodeId(2007),
    'ActTorque': ua.NodeId(2008),
    'CmdTorque': ua.NodeId(2009),
    'ActOverride': ua.NodeId(2010),
    'CmdOverride': ua.NodeId(2011),
    'InitialOperationDate': ua.NodeId(2005),
    'AlarmIdentifier': ua.NodeId(20011)
}

polling_interval = 0.1 # seconds

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
                
                    actual_load = await client.get_node(Node_Dict['ActLoad']).read_value()
                    _logger.info("ActLoad: %s", actual_load)
                    
                    actual_torque = await client.get_node(Node_Dict['ActTorque']).read_value()
                    _logger.info("ActTorque: %s", actual_torque)
                    
                    command_torque = await client.get_node(Node_Dict['CmdTorque']).read_value()
                    _logger.info("CmdTorque: %s", command_torque)
                    
                    actual_override = await client.get_node(Node_Dict['ActOverride']).read_value()
                    _logger.info("ActOverride: %s", actual_override)
                    
                    command_override = await client.get_node(Node_Dict['CmdOverride']).read_value()
                    _logger.info("CmdOverride: %s", command_override)
                    
                    initial_operation_date = await client.get_node(Node_Dict['InitialOperationDate']).read_value()
                    _logger.info("InitialOperationDate: %s", initial_operation_date)
                    
                    alarm_identifier = await client.get_node(Node_Dict['AlarmIdentifier']).read_value()
                    _logger.info("AlarmIdentifier: %s", alarm_identifier)
                    
                    elapsed = time.time() - start_time
                    sleep_time = max(polling_interval - elapsed, 0)
                    
                    await asyncio.sleep(sleep_time) # 大概還會誤差0.01秒
                
        except (OSError, asyncua.ua.uaerrors._base.UaError) as e:
            _logger.error(f"Connection failed: {e}")
            _logger.info("Attempting to reconnect in 5 seconds...")
            await asyncio.sleep(5)
        
        except Exception as e:
            _logger.exception("An unexpected error occurred: ", exc_info=e)
            break

async def main():            
    # read env variables from docker runtime input
    server_ips_env = os.getenv('PM_SERVER_IPS')
    if server_ips_env:
        server_ips = server_ips_env.split(',')
    else:
        _logger.error('The SERVER_IPS environment variable is not set.')
        exit(1)  # Exit if the environment variable is not set
    
    server_urls = [f"opc.tcp://{ip}:4840" for ip in server_ips]
    tasks = [server_task(url) for url in server_urls]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())