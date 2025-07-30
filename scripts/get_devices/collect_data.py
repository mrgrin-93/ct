from nornir.core.task import Task, Result
from nornir_scrapli.tasks import send_command
from nornir.core.exceptions import NornirSubTaskError

import logging

def collect_device_info(task: Task) -> Result:

    try:
        result_version = task.run(task=send_command, command="show version", severity_level=logging.DEBUG)
        task.host["version"] = result_version.scrapli_response.genie_parse_output()

        result_ip_intf = task.run(task=send_command, command="show ip interface", severity_level=logging.DEBUG)
        ip_interfaces = result_ip_intf.scrapli_response.genie_parse_output()
        task.host["ip_interfaces"] = ip_interfaces

        result_intf = task.run(task=send_command, command="show interfaces", severity_level=logging.DEBUG)
        interfaces = result_intf.scrapli_response.genie_parse_output()
        task.host["interfaces"] = interfaces

        task.host["status"] = "active"

    except NornirSubTaskError as e:
        logging.error(f"{task.host.name} failed to collect data: {e}")
        task.host["status"] = "deprecated"
    except scrapli.exceptions.ScrapliAuthenticationFailed as e:
        logging.error(f"{task.host.name} failed to collect data: {e}")
        task.host["status"] = "deprecated"

#        return Result(host=task.host, result="failed")
#
#    return Result(host=task.host, result="success")
