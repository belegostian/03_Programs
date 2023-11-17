import os.path
import asyncio
import logging
from asyncua import ua, Server
from asyncua.common.instantiate_util import instantiate
from asyncua.common.xmlexporter import XmlExporter

SERVER_URL = 'opc.tcp://0.0.0.0:4840'
SERVER_NAME = 'CNC Server'

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

    async def instantiate_objects(self):
        
        # 繼承標準node set初始化新物件，會返回包含該物件與子物件的list，[0]為該物件
        # https://reference.opcfoundation.org/CNC/v100/docs/6.1
        cnc_int = await instantiate(
            await self.server.nodes.objects.get_child('3:Machines'), # 父物件
            await self.server.nodes.base_object_type.get_child('4:CncInterfaceType'), # 物件類型 
            bname = '1:Cnc', # 物件瀏覽名稱
            )
        cnc = cnc_int[0]
        
        # 用以確認物件結構
        # structure_check = []
        # for i in range(len(cnc_interface)):
        #     structure_check.append((await cnc_interface[i].read_browse_name()).Name)
        
        # https://reference.opcfoundation.org/CNC/v100/docs/6.10
        alarm_int = await instantiate(
            cnc,
            await self.server.nodes.base_event_type.get_child(['ConditionType', 'AcknowledgeableConditionType', 'AlarmConditionType', 'DiscreteAlarmType', '4:CncAlarmType']),
            bname= '1:Alarm',
        )
        alarm = alarm_int[0]
        
        # reference https://reference.opcfoundation.org/Machinery/v103/docs/8.2
        nameplate = await cnc.add_object(nodeid=1, bname='1:Nameplate')
        await nameplate.add_property(nodeid=1, bname='Manufacturer', datatype=12, val="")
        await nameplate.add_property(nodeid=1, bname='DeviceClass', datatype=ua.String(), val="")
        await nameplate.add_property(nodeid=1, bname='SerialNumber', datatype=ua.String(), val="")
        await nameplate.add_property(nodeid=1, bname='InitialOperationDate', datatype=ua.String(), val="")
        
        # https://reference.opcfoundation.org/CNC/v100/docs/6.7
        driving = await cnc.add_object(nodeid=1, bname='1:Drive')
        await driving.add_property(nodeid=1, bname='ActLoad', datatype=ua.Double(), val=0)
        await driving.add_property(nodeid=1, bname='ActTorque', datatype=ua.Double(), val=0)
        await driving.add_property(nodeid=1, bname='CmdTorque', datatype=ua.Double(), val=0)
        await driving.add_property(nodeid=1, bname='ActOverride', datatype=ua.Double(), val=0)
        await driving.add_property(nodeid=1, bname='CmdOverride', datatype=ua.Double(), val=0)
                
        spindle_int = await instantiate(
            await cnc.get_child('4:CncSpindleList'),
            await self.server.nodes.base_object_type.get_child(['4:CncComponentType', '4:CncDriveType', '4:CncSpindleType']),
            bname = '1:Spindle',
        )
        spindle = spindle_int[0]
        
                # https://reference.opcfoundation.org/CNC/v100/docs/6.6
        channel_int = await instantiate(
            await cnc.get_child('4:CncChannelList'),
            await self.server.nodes.base_object_type.get_child(['4:CncComponentType', '4:CncChannelType']),
            bname = '1:Channel',
        )
        channel = channel_int[0]
        
        # https://reference.opcfoundation.org/MachineTool/v101/docs/8.4.3
        production_job_int = await instantiate(
            channel,
            await self.server.nodes.base_object_type.get_child(['6:ProductionJobType']),
            bname= '1:ProductionJob',
        )
        production_job = production_job_int[0]
        
        cutting_tools_int = await instantiate(
            cnc,
            await self.server.nodes.base_object_type.get_child(['6:EquipmentType', '6:Tools']),
            bname = '1:CuttingTools',
        )
        cutting_tools = cutting_tools_int[0]
        
        tool01_int = await instantiate(
            cutting_tools,
            await self.server.nodes.base_object_type.get_child(['6:BaseToolType', '6:ToolType']),
            bname = '1:Tool01',
        )
        tool01 = tool01_int[0]

        return cnc, alarm, nameplate, driving, channel, production_job, spindle, tool01

    # server 初始化定義
    async def init(self):
        await self.server.init()
        
        # 引入參考的 node set
        await self.server.import_xml(os.path.join(self.model_filepath, "Opc.Ua.Di.NodeSet2.xml"))
        await self.server.import_xml(os.path.join(self.model_filepath, "Opc.Ua.Machinery.NodeSet2.xml"))
        await self.server.import_xml(os.path.join(self.model_filepath, 'Opc.Ua.CNC.NodeSet.xml'), strict_mode=False)
        await self.server.import_xml(os.path.join(self.model_filepath, 'Opc.Ua.IA.NodeSet2.xml'))
        await self.server.import_xml(os.path.join(self.model_filepath, 'Opc.Ua.MachineTool.NodeSet2.xml'))
        
        # 建立 spindle 物件 (UA Object)
        cnc, alarm, nameplate, driving, channel, production_job, spindle, tool01 = await self.instantiate_objects() # 
        sub_nodes = []
        
        # 配合 app: Job Scheduling
        sub_nodes.append(await nameplate.get_child(['1:Manufacturer']))
        sub_nodes.append(await nameplate.get_child(['1:SerialNumber']))
        sub_nodes.append(await cnc.get_child('4:CncTypeName')) # 3: DeviceClass
        
        sub_nodes.append(await channel.get_child('4:ActStatus'))
        
        sub_nodes.append(await channel.get_child('4:ActMainProgramName'))
        sub_nodes.append(await production_job.get_child('6:RunsPlanned'))
        sub_nodes.append(await production_job.get_child('6:RunsCompleted'))
        
        sub_nodes.append(await alarm.get_child('4:AlarmIdentifier'))
        
        # 配合 app: automatic workpiece changing
        sub_nodes.append(await channel.get_child('4:ActMFunctions'))
        
        # 配合 app: Predictive Maintenance 
        sub_nodes.append(await driving.get_child('1:ActLoad'))
        sub_nodes.append(await driving.get_child('1:ActTorque'))
        sub_nodes.append(await driving.get_child('1:CmdTorque'))
        sub_nodes.append(await driving.get_child('1:ActOverride'))
        sub_nodes.append(await driving.get_child('1:CmdOverride'))
        
        sub_nodes.append(await nameplate.get_child(['1:InitialOperationDate']))
        
        # 配合 app: Tool Wear Detection
        sub_nodes.append(await spindle.get_child('4:ActSpeed'))
        
        sub_nodes.append(await tool01.get_child('6:ControlIdentifier1'))
        sub_nodes.append(await tool01.get_child('6:ToolLife'))
        
        # 確認ActStatus的EnumValue代表什麼
        # cnc_channel_status = await self.server.nodes.base_data_type.get_child(['Enumeration', '4:CncChannelStatus'])
        # enum = await cnc_channel_status.get_child('0:EnumValues')
        # enum_val_list = await enum.read_value()
        
        node_list = [cnc, alarm, nameplate, channel, production_job, driving, spindle, tool01] + [node for node in sub_nodes]

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
        _logger.info('Server started at %s', SERVER_URL)
        
        while(True):
            await asyncio.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
