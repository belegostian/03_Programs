import os
import asyncio
import asyncua
import logging
import time
from asyncua import ua, Client

_logger = logging.getLogger(__name__)

# Node IDs
Node_Dict = {
    'ActStatus': ua.NodeId(20337),
    'ActMainProgramName': ua.NodeId(20324),
    'ActMFunctions': ua.NodeId(20325)
}

polling_interval = 60 # seconds

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
                    
                    actual_state = await client.get_node(Node_Dict['ActStatus']).read_value()
                    _logger.info("ActStatus: %s", actual_state)
                    
                    actual_program_name = await client.get_node(Node_Dict['ActMainProgramName']).read_value()
                    _logger.info("ActMainProgramName: %s", actual_program_name)
                    
                    actual_m_functions = await client.get_node(Node_Dict['ActMFunctions']).read_value()
                    _logger.info("ActMFunctions: %s", actual_m_functions)
                    
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
    # read env variables from file
    # with open('env_variables.env', 'r') as f:
    #     for line in f:
    #         key, value = line.strip().split('=', 1)
    #         os.environ[key] = value
    # server_ips = os.getenv('SERVER_IPS').split(',')
    
    # read env variables from docker runtime input
    server_ips_env = os.getenv('AWC_SERVER_IPS')
    if server_ips_env:
        server_ips = server_ips_env.split(',')
    else:
        _logger.error('The SERVER_IPS environment variable is not set.')
        exit(1)  # Exit if the environment variable is not set
    
    # for testing
    # server_ips = ['127.0.0.1']
    
    server_urls = [f"opc.tcp://{ip}:4840" for ip in server_ips]
    tasks = [server_task(url) for url in server_urls]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())