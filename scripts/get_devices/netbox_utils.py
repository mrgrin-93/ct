from nornir.core.task import Task
import pynetbox
from ipaddress import IPv4Interface
import logging




nb = pynetbox.api("https://netbox.test",
                  token="your_netbox_token")
nb.http_session.verify = False

roles = {"edge": "Router",
        "access": "Access switch",
        "distribution": "Distribution switch",
        "core": "Core switch"}

def update_or_create_device(task: Task):

    if task.host["status"] == "deprecated":
        device = nb.dcim.devices.get(name = task.host.name)
        if device:
            device.status = "offline"
            device.save()
    else:
        device = nb.dcim.devices.get(name = task.host["version"]["version"]["hostname"])
        if device:
            logging.info(f"Update {device.name}")
            _udpate_device(task, device)
            _update_or_create_interfaces(task, device)
        else:
            logging.info(f"Create {task.host.name}")
            device = _create_device(task)
            _update_or_create_interfaces(task, device)


def _udpate_device(task: Task, device):
    if task.host.platform == "ios":
        if (task.host["version"]['version']).get('switch_num'):
            logging.info(f"{task.host.platform} and sw_num")
#            logging.info(f"{task.host.name} {task.host['version']['version']}")
            device.device_type = nb.dcim.device_types.get(part_number = task.host["version"]['version']['switch_num']["1"]['model_num']).id
            device.status = "active"
            device.role = {"name": roles[task.host["role"]]}
            device.serial = task.host["version"]['version']['switch_num']["1"]['system_sn']

        else:
            logging.info(f"{task.host.platform} and solo")
#            logging.info(f"{task.host.name} {task.host['version']['version']}")
            device.device_type = nb.dcim.device_types.get(part_number = task.host["version"]['version']['chassis'])
            device.status = "active"
            device.role = {"name": roles[task.host["role"]]}
            device.serial = task.host["version"]['version']['chassis_sn']

    if task.host.platform == "cisco_nxos":
        device.device_type = nb.dcim.device_types.get(part_number = task.host["version"]['platform']['hardware']['chassis'])
        device.status = "active"
        device.role = {"name": roles[task.host["role"]]}
        device.serial = task.host["version"]['platform']['hardware']['processor_board_id']
    device.save()


def _create_device(task: Task):
    logging.info(f"Create {task.host.name}")
    if task.host.platform == "ios":
        if (task.host["version"]['version']).get('switch_num'):
            new_device = nb.dcim.devices.create(name = task.host["version"]["version"]["hostname"],
                device_type = nb.dcim.device_types.get(part_number=task.host["version"]['version']['switch_num']["1"]['model_num']).id,
                role = {"name": roles[task.host["role"]]},
                status = "active", site = {"name": "Onboard"},
                serial = task.host["version"]['version']['switch_num']["1"]['system_sn'])

        else:
            new_device = nb.dcim.devices.create(name = task.host["version"]["version"]["hostname"],
                device_type = nb.dcim.device_types.get(part_number=task.host["version"]['version']['chassis']).id,
                role = {"name": roles[task.host["role"]]},
                status = "active", site = {"name": "Onboard"},
                serial = task.host["version"]['version']['chassis_sn'])

    if task.host.platform == "cisco_nxos":
        new_device = nb.dcim.devices.create(name = task.host["version"]["version"]["hostname"],
            device_type = nb.dcim.device_types.get(part_number=task.host["version"]['platform']['hardware']['chassis']).id,
            role = {"name": roles[task.host["role"]]},
            status = "active", site ={"name": "Onboard"},
            serial = task.host["version"]['platform']['hardware']['processor_board_id'])
    return new_device


def _update_or_create_interfaces(task: Task, device):
    logging.info(f"Updating interfaces for device {device.name}")
    for physical_interface in task.host["interfaces"].keys():
        interface = nb.dcim.interfaces.get(device_id = device.id, name = physical_interface)
        if interface and task.host["interfaces"][physical_interface]["oper_status"] == "up":
            interface  = _update_interface(task, interface, physical_interface)

        elif interface and task.host["interfaces"][physical_interface]["oper_status"] == "down":
            interface.enabled = task.host["interfaces"][physical_interface]["enabled"]
            interface.description = task.host["interfaces"][physical_interface].get("description", "")
            interface.type = _match_int_type(task, physical_interface)
            interface.save()

        else:
            interface = _create_interface(task, device, physical_interface)


        if task.host["ip_interfaces"][physical_interface].get("ipv4") and task.host["interfaces"][physical_interface]["oper_status"] == "up":
            _proceed_ips(task, physical_interface, interface, device)

    nb_interfaces = nb.dcim.interfaces.filter(device_id = device.id)
    for interface in nb_interfaces:
        if interface.name not in task.host["interfaces"].keys():
            interface.delete()



def _update_interface(task:Task, interface, physical_interface):
    interface.enabled = task.host["interfaces"][physical_interface]["enabled"]
    interface.description = task.host["interfaces"][physical_interface].get("description", "")
    interface.type = _match_int_type(task, physical_interface)
    if task.host["interfaces"][physical_interface].get("phys_address"):
#        logging.info(f"mac is {task.host["interfaces"][physical_interface].get("phys_address")}")
        try:
            mac  = nb.dcim.mac_addresses.get(mac_address=task.host["interfaces"][physical_interface]["phys_address"],
                assigned_object_id=interface.id)
        except ValueError:
            mac = list(nb.dcim.mac_addresses.filter(mac_address=task.host["interfaces"][physical_interface]["phys_address"],
                assigned_object_id=interface.id))[0]
        if not mac:
            nb.dcim.mac_addresses.create(mac_address=task.host["interfaces"][physical_interface]["phys_address"],
            assigned_object_id = interface.id,
            assigned_object_type = "dcim.interface")
        else:
            mac.assigned_object_id = interface.id
            mac.assigned_object_type = "dcim.interface"
            mac.save()
    if task.host["ip_interfaces"][physical_interface].get("vrf"):
        try:
            interface.vrf = {"name": task.host["ip_interfaces"][physical_interface].get("vrf")}
            interface.save()
        except pynetbox.core.query.RequestError:
            logging.info(f"Create VRF {task.host['ip_interfaces'][physical_interface]['vrf']}")
            nb.ipam.vrfs.create(name = task.host["ip_interfaces"][physical_interface]["vrf"])
            interface.vrf = {"name": task.host["ip_interfaces"][physical_interface].get("vrf")}
            interface.save()
    return interface



def _create_interface(task, device, physical_interface):
    interface = nb.dcim.interfaces.create(device = device.id, name = physical_interface, type = _match_int_type(task, physical_interface))
    _update_interface(task, interface, physical_interface)
    return interface


def _proceed_ips(task: Task, physical_interface, interface, device):
    for ip in task.host["ip_interfaces"][physical_interface].get("ipv4").keys():
        if  ip == "ipcp_negotiated":
            continue
        logging.info(f"{device.name} Processing IP address {ip}")
        try:
            if task.host["ip_interfaces"][physical_interface].get("vrf"):
                vrf_id = nb.ipam.vrfs.get(name = task.host["ip_interfaces"][physical_interface].get("vrf")).id
                nb_ip = nb.ipam.ip_addresses.get(address = ip, vrf_id = vrf_id)
            else:
                nb_ip = nb.ipam.ip_addresses.get(address = ip, vrf_id = "null")
        except pynetbox.core.query.RequestError as e:
            logging.info(e)
        if nb_ip:
            nb_ip.assigned_object_type = "dcim.interface"
            nb_ip.assigned_object_id = interface.id
            nb_ip.save()
        else:
            if task.host["ip_interfaces"][physical_interface].get("vrf"):
                vrf_id = nb.ipam.vrfs.get(name = task.host["ip_interfaces"][physical_interface].get("vrf")).id
#                try:
                _get_or_create_prefix(IPv4Interface(ip).network.with_prefixlen, vrf_id)
                nb_ip = nb.ipam.ip_addresses.create(vrf={"id": vrf_id}, address = ip, assigned_object_id = interface.id, assigned_object_type = "dcim.interface")
#                except pynetbox.core.query.RequestError:
#                    nb.ipam.ip_addresses.delete([nb.ipam.ip_addresses.get(address = ip).id])
#                    nb_ip = nb.ipam.ip_addresses.create(vrf_id = vrf_id, address = ip, assigned_object_id = interface.id, assigned_object_type = "dcim.interface")
            else:
                nb_ip = nb.ipam.ip_addresses.create(address = ip, assigned_object_id = interface.id, assigned_object_type = "dcim.interface")
        if ip.split('/')[0] == task.host.hostname:
            logging.info(f"{task.host.hostname} is primary, nb {ip}, id = {nb_ip.id}")
            device.primary_ip4 = nb_ip.id
            logging.info(f"{dict(device)}")
            device.save()
        logging.info(f"IP address {nb_ip} processed")


def _get_or_create_prefix(prefix, vrf_id):
    try:
        nb_prefix = nb.ipam.prefixes.get(prefix=prefix, vrf_id=vrf_id)
        return nb_prefix if nb_prefix else nb.ipam.prefixes.create(prefix=prefix, vrf={"id": vrf_id})
    except ValueError:
        matches = list(nb.ipam.prefixes.filter(prefix=prefix, vrf_id=vrf_id))
        return matches[0] if matches else nb.ipam.prefixes.create(prefix=prefix, vrf={"id": vrf_id})


def _match_int_type(task: Task, int: str) -> str:
    if 'Vlan' in int:
            int_type = 'virtual'
    elif 'Tunnel' in int:
        int_type = 'virtual'
    elif 'Port' in int:
        int_type = 'lag'
    elif 'TwentyFive' in int:
        int_type = '25gbase-x-sfp28'
    elif 'TenGigabit' in int:
        int_type = '10gbase-t'
    elif 'Gigabit' in int:
        int_type = '1000base-t'
    else:
        int_type = 'other'
    return int_type
