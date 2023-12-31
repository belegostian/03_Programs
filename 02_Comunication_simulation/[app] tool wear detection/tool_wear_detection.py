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
    'ActSpeed': ua.NodeId(20204),
    'ControlIdentifier1': ua.NodeId(20451),
    'ToolLife': ua.NodeId(20458),
}

polling_interval = 1 # seconds

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
                
                    act_speed = await client.get_node(Node_Dict['ActSpeed']).read_value()
                    _logger.info("ActSpeed: %s", act_speed)
                    
                    control_identifier = await client.get_node(Node_Dict['ControlIdentifier1']).read_value()
                    _logger.info("ControlIdentifier: %s", control_identifier)
                    
                    # TODO: 這邊有問題，讀取不到值
                    # tool_life = await client.get_node(Node_Dict['ToolLife']).read_value()
                    # _logger.info("ToolLife: %s", tool_life)
                    
                    elapsed = time.time() - start_time
                    sleep_time = max(polling_interval - elapsed, 0)
                    
                    await asyncio.sleep(sleep_time) # 大概還會誤差0.01秒
                
        except (OSError, asyncua.ua.uaerrors._base.UaError, asyncio.TimeoutError) as e:
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
    server_ips_env = os.getenv('TWD_SERVER_IPS')
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