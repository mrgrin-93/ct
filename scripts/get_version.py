from nornir import InitNornir
from nornir.core.filter import F
from nornir_utils.plugins.functions import print_result
from nornir.core.task import Task, Result
from nornir_scrapli.tasks import send_command
from pprint import pprint
from nornir.core.exceptions import NornirSubTaskError
import asyncio
import motor.motor_asyncio

MONGO_DETAILS = "mongodb://my-mongo:27017"

client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)

host = InitNornir(config_file="/opt/ct/config.yaml")

async def updoad_devices():
    collection_name = client.acl['devices']
    await collection_name.delete_many({})
    await collection_name.insert_many(hosts)

def populate_host_version(task: Task):
    try:
        result = task.run(task=send_command, command="show version")
        task.host["version"] = result.scrapli_response.genie_parse_output()
        task.host["status"] = "active" 
    except NornirSubTaskError:
        task.host["status"] = "deprecated"

result = host.run(task=populate_host_version)

hosts = []

for i in host.inventory.hosts:
    if host.inventory.hosts[i]['status'] == "active":
        if host.inventory.hosts[i].platform == "ios":
            if (host.inventory.hosts[i]["version"]['version']).get('switch_num'):
                device = {'name':i,
                    'ip': host.inventory.hosts[i].hostname,
                    'version':  host.inventory.hosts[i]["version"]['version']['version'],
                    'location': host.inventory.hosts[i]['site'],
                    'is_alive': True,
                    'type': host.inventory.hosts[i]['role'],
                    'model': 'cisco',
                    'hardware': [
                            {'chassis': host.inventory.hosts[i]["version"]['version']['switch_num'][sw_num]['model_num'],
                            'serial_number': host.inventory.hosts[i]["version"]['version']['switch_num'][sw_num]['system_sn'],
                            'mac_address': host.inventory.hosts[i]["version"]['version']['switch_num'][sw_num]['mac_address']} for sw_num in (host.inventory.hosts[i]["version"]['version']['switch_num']).keys()
                            ]
                    }
            else:
                device = {'name':i,
                        'ip': host.inventory.hosts[i].hostname,
                        'version':  host.inventory.hosts[i]["version"]['version']['version'],
                        'location': host.inventory.hosts[i]['site'],
                        'is_alive': True,
                        'type': host.inventory.hosts[i]['role'],
                        'model': 'cisco',
                        'hardware': [
                                {'chassis': host.inventory.hosts[i]["version"]['version']['chassis'],
                                'serial_number': host.inventory.hosts[i]["version"]['version']['chassis_sn'],
                                'mac_address': ''}]
                    }
        if host.inventory.hosts[i].platform == "cisco_nxos":
            device = {'name':i,
                    'ip': host.inventory.hosts[i].hostname,
                    'version':  host.inventory.hosts[i]["version"]['platform']['software']['system_version'],
                    'location': host.inventory.hosts[i]['site'],
                    'is_alive': True,
                    'type': host.inventory.hosts[i]['role'],
                    'model': 'cisco_nexus',
                    'hardware': [
                            {'chassis': host.inventory.hosts[i]["version"]['platform']['hardware']['chassis'],
                            'serial_number': host.inventory.hosts[i]["version"]['platform']['hardware']['processor_board_id'],
                            'mac_address': ''}]
                    }
        hosts.append(device)

    elif host.inventory.hosts[i]['status'] == "deprecated":
        device = {'name':i,
                'ip': host.inventory.hosts[i].hostname,
                'version':  '',
                'location': host.inventory.hosts[i]['site'],
                'is_alive': False,
                'hardware': [
                    ]
            }
        hosts.append(device)

#pprint(hosts)

print(asyncio.run(updoad_devices()))
