from nornir import InitNornir
from nornir.core.task import Task
from nornir_utils.plugins.functions import print_result
from nornir.core.filter import F
import logging

from collect_data import collect_device_info
from netbox_utils import update_or_create_device

import urllib3

# Инициализация Nornir
nr = InitNornir(
    config_file="/opt/ct/config.yaml",
    logging={"enabled": False, "log_file": "/opt/ct/nornir.log"}
)

# Подавление предупреждений SSL

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s %(threadName)s %(levelname)s: %(message)s',
    level=logging.INFO,
)

def run_task(task: Task) -> None:
    collect_device_info(task)
    update_or_create_device(task)


if __name__ == "__main__":
#    hosts = nr.filter(F(groups__contains="rmt"))
#    hosts = nr.filter(name = "dcx4500x")
#    result = hosts.run(task = run_task)
    result = nr.run(task = run_task)
    print_result(result)
