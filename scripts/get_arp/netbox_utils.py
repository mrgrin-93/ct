# from typing import List, Dict, Any
from nornir.core.task import Task, Result
from ipaddress import IPv4Interface
from settings import EXCLUDED_PREFIXES
from utils import resolve_ptr, get_mac_vendor
from settings import CURRENT_TIME, NETBOX_URL, NETBOX_TOKEN
import pynetbox
import logging


nb = pynetbox.api(NETBOX_URL,
                  token=NETBOX_TOKEN)
nb.http_session.verify = False


def sync_host_with_netbox(task: Task) -> Result:
    logging.info(f"Syncing {task.host.name} with Netbox")
    if task.host["status"] == "deprecated":
        return Result(host=task.host, result="skipped")

    for vrf in task.host["summary"].keys():
        logging.info(f"Vrf {vrf}")
        nb_vrf = _get_or_create_vrf(vrf)
        logging.info(f"{nb_vrf}")

        for prefix in task.host["summary"][vrf]:
            if prefix in EXCLUDED_PREFIXES:
                logging.info(
                    f"{task.host.name} Skipping excluded prefix {prefix}")
                continue

            logging.info(f"Get or create prefix {prefix}")
            _get_or_create_prefix(prefix, nb_vrf.id if nb_vrf else "null")
            ips = list(nb.ipam.ip_addresses.filter(
                parent=prefix, vrf_id=nb_vrf.id if nb_vrf else "null"))

            # logging.info(f"{task.host["summary"][vrf][prefix]}")
            update_ips_in_prefix(task, ips, prefix, vrf)
            _create_missing_ips(task, prefix, ips, nb_vrf)

    logging.info(f"{task.host.name} synced successfully")
    return Result(host=task.host, result="synced")


def _get_or_create_vrf(name: str):
    vrf_filter = list(nb.ipam.vrfs.filter(name=name))
    if len(vrf_filter):
        return vrf_filter[0]
    return nb.ipam.vrfs.create(name=name) if name != "global" else None


def _get_or_create_prefix(prefix: str, vrf_id):
    try:
        nb_prefix = nb.ipam.prefixes.get(prefix=prefix, vrf_id=vrf_id)
        if vrf_id == "null":
            return nb_prefix if nb_prefix else nb.ipam.prefixes.create(prefix=prefix)
        else:
            return nb_prefix if nb_prefix else nb.ipam.prefixes.create(prefix=prefix, vrf={"id": vrf_id})
    except ValueError:
        matches = list(nb.ipam.prefixes.filter(prefix=prefix, vrf_id=vrf_id))
        if vrf_id == "null":
            return matches[0] if matches else nb.ipam.prefixes.create(prefix=prefix)
        else:
            return matches[0] if matches else nb.ipam.prefixes.create(prefix=prefix, vrf={"id": vrf_id})


def update_ips_in_prefix(task, ips: list, prefix: str, vrf: str):
    current_ips = task.host["summary"][vrf][prefix]
    ip_map = {ip.address.split("/")[0]: ip for ip in ips}

    for ip_str, ip_obj in ip_map.items():

        if ip_str in current_ips.keys():
            # logging.info(f"{ip_str}")
            try:
                _update_ip(ip_obj, current_ips[ip_str])
            except pynetbox.core.query.RequestError as e:
                logging.info(e)
        else:
            try:
                _mark_deprecated(ip_obj)
            except pynetbox.core.query.RequestError as e:
                logging.info(e)



def _create_missing_ips(task, prefix: str, ips: list, vrf):
    existing_ips = set(str(ip).split("/")[0] for ip in ips)
    if vrf:
        needed_ips = set(task.host["summary"][vrf.name][prefix].keys())
    else:
        needed_ips = set(task.host["summary"]["global"][prefix].keys())
    new_ips = needed_ips - existing_ips

    for ip in new_ips:
        _create_new_ip(task, ip, prefix, vrf)


def _update_ip(ip_obj, arp_entry):
    ip_obj.status = "active"
    ip_obj.custom_fields["MAC"] = arp_entry["link_layer_address"]
    ip_obj.custom_fields["Online"] = CURRENT_TIME
    ip_obj.custom_fields["MACVendor"] = get_mac_vendor(
        arp_entry["link_layer_address"])
    ip_obj.dns_name = resolve_ptr(ip_obj.address.split("/")[0])
    ip_obj.tags.append({"name": "Arp-Sync"})
    ip_obj.save()


def _mark_deprecated(ip_obj):
    if ip_obj.status["value"] == "active":
        logging.info(f"Setting deprecated {ip_obj.address}")
        ip_obj.status = "deprecated"
        ip_obj.tags.append({"name": "Arp-Sync"})
        ip_obj.save()


def _create_new_ip(task, ip: str, prefix: str, vrf):
    address = f"{ip}/{IPv4Interface(prefix).network.prefixlen}"
    if vrf:
        new_ip = nb.ipam.ip_addresses.create(address=address, vrf={"id": vrf.id})
        new_ip.custom_fields["MAC"] = task.host["summary"][vrf.name][prefix][ip]["link_layer_address"]
    else:
        new_ip = nb.ipam.ip_addresses.create(address=address)
        new_ip.custom_fields["MAC"] = task.host["summary"]["global"][prefix][ip]["link_layer_address"]
    new_ip.custom_fields["Online"] = CURRENT_TIME
    new_ip.custom_fields["MACVendor"] = get_mac_vendor(
        new_ip.custom_fields["MAC"])
    new_ip.dns_name = resolve_ptr(ip)
    new_ip.tags.append({"name": "Arp-Sync"})
    new_ip.save()
