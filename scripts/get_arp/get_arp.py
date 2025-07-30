
# from turtledemo.chaos import h
from nornir import InitNornir
from nornir.core.task import Task
from nornir.core.filter import F
from nornir_utils.plugins.functions import print_result
import logging

from collect_arp import collect_arp_data
from netbox_utils import sync_host_with_netbox

import urllib3

# from pprint import pprint

# Инициализация Nornir
nr = InitNornir(
    config_file="/opt/ct/config.yaml",
    logging={"log_file": "/opt/ct/nornir.log"}
)

# Подавление предупреждений SSL

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s %(threadName)s %(levelname)s: %(message)s',
    level=logging.INFO,
)

# Основная задача


def run_task(task: Task) -> None:
    collect_arp_data(task)
    sync_host_with_netbox(task)


result = nr.run(task=run_task)

# Вывод результата
print_result(result)
