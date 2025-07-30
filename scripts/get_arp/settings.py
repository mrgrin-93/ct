import os
from datetime import datetime
# Путь к конфигу Nornir
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.yaml")

# Netbox
NETBOX_URL = "https://netbox.test"
NETBOX_TOKEN = "your-netbox-token"

# Исключённые префиксы
EXCLUDED_PREFIXES = [
    "10.10.10.0/24", "10.10.10.0/25", "10.10.0.0/26", "10.100.100.0/29",
]

# Текущее время для отметок
CURRENT_TIME = datetime.now().strftime("%Y-%m-%d %H:%M")
