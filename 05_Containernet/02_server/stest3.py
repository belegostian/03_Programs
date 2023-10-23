import os.path
import asyncio
import logging
import numpy as np
from asyncua import ua, Server
from asyncua.common.instantiate_util import instantiate
from asyncua.common.xmlexporter import XmlExporter

SERVER_URL = 'opc.tcp://0.0.0.0:4840'
SERVER_NAME = 'Test CNC Server'

_logger = logging.getLogger(__name__)

# 自定義 CNC Server
class CNCServer:

    # server 初始化
    def __init__(self, endpoint, name, model_filepath):
        self.server = Server()
        
        self.server.set_endpoint(endpoint)
        self.server.set_server_name(name)
        self.server.set_security_policy(
            [
                ua.SecurityPolicyType.NoSecurity,
                ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
                ua.SecurityPolicyType.Basic256Sha256_Sign,
            ]
        )
        
        self.model_filepath = model_filepath

    async def create_spindle_object(self):
        
        # 繼承標準 node set 初始化新物件
        spindleType = await instantiate(
            await self.server.nodes.objects.get_child('3:Machines'), # Parent Object
            await self.server.nodes.base_object_type.get_child(['4:CncComponentType', '4:CncDriveType', '4:CncSpindleType']), # Type to Instantiate
            bname = '1:tCNC_spindle', # Browse Name
            dname = ua.LocalizedText('tCNC_spindle'), # Display Name
            idx = 1, # Namespace Index
            instantiate_optional = False)
        
        # 取得該物件
        spindle = await self.server.nodes.objects.get_child(['3:Machines', '1:tCNC_spindle'])

        # 創立物件之架構將繼承參考物件之架構，賦予初始值
        cnc_properties = {
            '4:CmdSpeed': 0.0,
            '4:CmdTorque': 0.0,
            '4:ActSpeed': 0.0,
            '4:ActTorque': 0.0,
            '4:ActPower': 0.0,
            '4:ActLoad': 0.0
        }
        for prop_name, value in cnc_properties.items():
            prop = await spindle.get_child(prop_name)
            await prop.write_value(value)
            
            # 設定可寫入
            if "Cmd" in prop_name:
                await prop.set_writable()
            
        # 自定義創立物件之架構，賦予初始值
        custom_properties = {
            '1:Voltage': 0.0,
            '1:Current': 0.0
        }
        for prop_name, value in custom_properties.items():
            await instantiate(
                spindle,
                await self.server.nodes.base_variable_type.get_child(['BaseDataVariableType', 'DataItemType', 'BaseAnalogType', 'AnalogItemType']),
                bname = prop_name,
                dname = ua.LocalizedText(prop_name.split(':')[1]),
                idx = 1,
                instantiate_optional = False
            )
            prop = await spindle.get_child(prop_name)
            await prop.write_value(value)
            
        # 賦予自定義資料
        # custom_properties = {
        #     '1:Voltage': [900, 920, 940, 960, 980, 1000, 1020, 1040, 1060, 1080],
        #     '1:Current': [1100, 1080, 1060, 1040, 1020, 1000, 980, 960, 940, 920]
        # }
        # for prop_name, value in custom_properties.items():
        #     prop = await spindle.add_object(1, prop_name.split(':')[1], ua.Variant(value, ua.VariantType.Double))
        #     await prop.add_variable(1, 'value', ua.Variant(value, ua.VariantType.Double))
        
        merge_properties = {**cnc_properties, **custom_properties}
        return spindle, list(merge_properties.keys())

    # server 初始化定義
    async def init(self):
        await self.server.init()
        
        # 引入參考的 node set
        await self.server.import_xml(os.path.join(self.model_filepath, "Opc.Ua.Di.NodeSet2.xml"))
        await self.server.import_xml(os.path.join(self.model_filepath, "Opc.Ua.Machinery.NodeSet2.xml"))
        await self.server.import_xml(os.path.join(self.model_filepath, 'Opc.Ua.CNC.NodeSet.xml'), strict_mode=False) #! strict_mode=False 還不完全確定功能
        
        # 建立 spindle 物件 (UA Object)
        spindle, property_names = await self.create_spindle_object()
        node_list = [spindle] + [await spindle.get_child(name) for name in property_names]

        # 輸出這個 Server 的 node set
        exporter = XmlExporter(self.server)
        await exporter.build_etree(node_list)
        await exporter.write_xml('custom_CNC.xml')

    async def __aenter__(self):
        await self.init()
        await self.server.start()
        return self.server

    async def __aexit__(self, exc_type, exc_val, exc_tb): #! 未定義條件
        await self.server.stop()

async def main():
    script_dir = os.path.dirname(__file__)
    
    # 以 Server 成立為條件，運行
    async with CNCServer(SERVER_URL, SERVER_NAME, script_dir) as server:
        
        await asyncio.sleep(10)
        _logger.info("\n------------暖機時間結束------------\n")
        
        spindle = await server.nodes.objects.get_child(['3:Machines', '1:tCNC_spindle'])
        CmdSpeed = await spindle.get_child('4:CmdSpeed')
        cmd_speed = await CmdSpeed.read_value()
        CmdTorque = await spindle.get_child('4:CmdTorque')
        cmd_torque = await CmdTorque.read_value()
        ActSpeed = await spindle.get_child('4:ActSpeed')
        act_speed = await ActSpeed.read_value()
        ActTorque = await spindle.get_child('4:ActTorque')
        act_torque = await ActTorque.read_value()
        ActPower = await spindle.get_child('4:ActPower')
        act_power = await ActPower.read_value()
        Voltage = await spindle.get_child('1:Voltage')
        voltage = await Voltage.read_value()
        Current = await spindle.get_child('1:Current')
        current = await Current.read_value()
        
        # 模擬設備資料
        while True:
            CmdSpeed = await spindle.get_child('4:CmdSpeed')
            cmd_speed = await CmdSpeed.read_value()
            CmdTorque = await spindle.get_child('4:CmdTorque')
            cmd_torque = await CmdTorque.read_value()            
            
            act_speed += (cmd_speed - act_speed) * np.random.normal(loc=0.1, scale=0.1)
            await ActSpeed.write_value(act_speed)
            act_torque += (cmd_torque - act_torque) * np.random.normal(loc=0.1, scale=0.1)
            await ActTorque.write_value(act_torque)
            act_power = act_speed * act_torque / 9.549 /1000  #! 常數，參考自網路
            await ActPower.write_value(act_power)
            _logger.info("\n實際轉速: %.2f rpm, 實際轉矩: %.2f Nm, 實際功率: %.2f KW", act_speed, act_torque, act_power)
            
            voltage += (20.0 - voltage) * np.random.normal(loc=0.1, scale=0.1) + np.random.normal(loc=0, scale=2.0)
            await Voltage.write_value(voltage)
            current += (5.0 - current) * np.random.normal(loc=0.1, scale=0.1) + np.random.normal(loc=0, scale=0.15)
            await Current.write_value(current)
            _logger.info("電壓: %.2f V, 電流: %.2f I\n", voltage, current)
            
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
