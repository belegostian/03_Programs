import os.path
import asyncio
import logging
import random
from asyncua import ua, Server
from asyncua.common.instantiate_util import instantiate 
from asyncua.common.xmlexporter import XmlExporter

class CNCServer:
    def __init__(self, endpoint, name, model_filepath):
        self.server = Server()

        self.model_filepath = model_filepath
        self.server.set_server_name(name)
        self.server.set_endpoint(endpoint)

    async def init(self):
        await self.server.init()
        
        # import required node set files
        await self.server.import_xml(os.path.join(self.model_filepath, "UA\Opc.Ua.Di.NodeSet2.xml"))
        await self.server.import_xml(os.path.join(self.model_filepath, "Machinery\Opc.Ua.Machinery.NodeSet2.xml"))
        await self.server.import_xml(os.path.join(self.model_filepath, 'CNC\Opc.Ua.CNC.NodeSet.xml'), strict_mode=False) #! strict_mode=False 還不完全確定功能
        
        
        # custom object
        self.spindleType = await instantiate(
            await self.server.nodes.objects.get_child('3:Machines'), # Parent Object
            await self.server.nodes.base_object_type.get_child(['4:CncComponentType', '4:CncDriveType', '4:CncSpindleType']), # Type to Instantiate
            bname = '1:tCNC_spindle', # Browse Name
            dname = ua.LocalizedText('tCNC_spindle'), # Display Name
            idx = 1, # Namespace Index
            instantiate_optional = False)
        
        # custom object context
        spindle = await self.server.nodes.objects.get_child(['3:Machines', '1:tCNC_spindle'])
        
        cmd_speed = await spindle.get_child('4:CmdSpeed')
        await cmd_speed.write_value(201.9)
        act_speed = await spindle.get_child('4:ActSpeed')
        await act_speed.write_value(200.5)
        cmd_torque = await spindle.get_child('4:CmdTorque')
        await cmd_torque.write_value(203.2)
        act_torque = await spindle.get_child('4:ActTorque')
        await act_torque.write_value(202.9)
        act_load = await spindle.get_child('4:ActLoad')
        await act_load.write_value(202.3)
        act_power = await spindle.get_child('4:ActPower')
        await act_power.write_value(202.6)
        
        node_list = [spindle, cmd_speed, act_speed, cmd_torque, act_torque, act_load, act_power]

        exporter = XmlExporter(self.server)
        await exporter.build_etree(node_list)
        await exporter.write_xml('ua-export.xml')
        
    async def __aenter__(self):
        await self.init()
        await self.server.start()
        return self.server

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.server.stop()

async def main():
    script_dir = os.path.dirname(__file__)
    async with CNCServer(
        "opc.tcp://0.0.0.0:4840",
        "Test Server",
        script_dir,
    ) as server:
        
        while True:
            await asyncio.sleep(1)   
        
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())