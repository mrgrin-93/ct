from nornir.core.task import Task, Result
from nornir_scrapli.tasks import send_command
from nornir.core.exceptions import NornirSubTaskError
from ipaddress import IPv4Interface, IPv4Address
import logging
# from typing import Dict, Any

def collect_arp_data(task: Task) -> Result:
    logging.info(f"Starting collection on {task.host.name}")
    task.host["summary"] = {}
    task.host["status"] = "active"

    try:
        result_vrf = task.run(task=send_command, command="show ip vrf", severity_level=logging.DEBUG)
        task.host["vrf"] = result_vrf.scrapli_response.genie_parse_output()

        result_arp_global = task.run(task=send_command, command="show ip arp", severity_level=logging.DEBUG)
        task.host["arp"] = {"global": result_arp_global.scrapli_response.genie_parse_output()}

        try:
            for vrf in task.host["vrf"]["vrf"].keys():
                result_arp_vrf = task.run(task=send_command, command=f"show ip arp vrf {vrf}", severity_level=logging.DEBUG)
                task.host["arp"][vrf] = result_arp_vrf.scrapli_response.genie_parse_output()
        except TypeError:
            logging.info(f"{task.host.name} have no VRF")

        result_intf = task.run(task=send_command, command="show ip interface", severity_level=logging.DEBUG)
        interfaces = result_intf.scrapli_response.genie_parse_output()
        task.host["interfaces"] = interfaces

        # Build summary
        task.host["summary"] = {}
        for arp_vrf in task.host["arp"]:
            if isinstance(task.host["arp"][arp_vrf],list):
                continue
            task.host["summary"][arp_vrf] = {}
            for intf in task.host["arp"][arp_vrf]["interfaces"]:
                if intf not in interfaces or 'ipv4' not in interfaces[intf]:
                    continue
                for prefix in interfaces[intf]['ipv4']:
                    network = IPv4Interface(prefix).network
                    task.host["summary"][arp_vrf][str(network.with_prefixlen)] = {}
                    neighbors = task.host["arp"][arp_vrf]["interfaces"][intf]["ipv4"]["neighbors"]
                    for ip in neighbors:
                        if IPv4Address(ip) in network:
                            task.host["summary"][arp_vrf][str(network)][ip] = neighbors[ip]

        task.host["arp"].clear()
        task.host["interfaces"].clear()
        task.host["vrf"].clear()

    except NornirSubTaskError as e:
        logging.error(f"{task.host.name} failed to collect data: {e}")
        task.host["status"] = "deprecated"
        return Result(host=task.host, result="failed")

    return Result(host=task.host, result="success")
