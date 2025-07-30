# from ipaddress import IPv4Address, IPv4Interface
from netaddr import EUI
from netaddr.core import NotRegisteredError
import dns.resolver
import dns.reversename
import logging
# from nornir_utils.plugins.functions.print_result import logging
# from typing import Optional

# mac_vendor_cache = {}

def resolve_ptr(ip: str) -> str:
    try:
        ptr_name = dns.reversename.from_address(ip)
        answer = dns.resolver.resolve(ptr_name, "PTR", raise_on_no_answer=False)
        return str(answer[0]) if answer else ""
    except dns.resolver.NXDOMAIN:
        return ""
    except dns.resolver.LifetimeTimeout:
        return ""


def get_mac_vendor(mac: str) -> str:
    # if mac in mac_vendor_cache:
    #     return mac_vendor_cache[mac]
    try:
        vendor = EUI(mac).oui.registration().org
    except NotRegisteredError:
#        logging.info(f"No such mac {mac} in db")
        vendor = "Unknown"
    # mac_vendor_cache[mac] = vendor
    return vendor
