#!/usr/bin/python3
import os
import sys
from typing import List, Union

sys.path.append("/opt/unipi/os-configurator")
os_configurator = __import__("os-configurator")

OWFS_CONFIG_PATH = "/etc/owfs.conf"
OWFS_CONFIG_LINES = ["### CONFIGURED BY EVOK ###",
                     "server: i2c=/dev/i2c-1", "server: w1",
                     "##########################"]

BRAIN = "00"
E14DI14RO = "09"
E16DI14DI = "0A"
E16DI14RO = "08"
E14RO14RO = "07"
E8DI8DO = "01"
E4AI4AO4DI5RO = "13"
E4AI4AO6DI5RO = "0F"

UNIPI11 = "UNIPI11"
UNIPI11LITE = "UNIPI11LITE"


hw_data = {
    0x0103: [BRAIN],  # S103
    0x1103: [BRAIN],  # S103_E
    0x1203: [BRAIN],  # S103_I
    0x0203: [BRAIN, E8DI8DO],  # M103
    0x0303: [BRAIN, E16DI14RO],  # M203
    0x0403: [BRAIN, E16DI14DI],  # M303
    0x0503: [BRAIN, E4AI4AO4DI5RO],  # M523
    0x0603: [BRAIN, E16DI14RO, E16DI14RO],  # L203
    0x0703: [BRAIN, E14RO14RO, E14RO14RO],  # L403
    0x0803: [BRAIN, E4AI4AO4DI5RO, E16DI14RO],  # L523
    0x0903: [BRAIN, E4AI4AO4DI5RO, E4AI4AO4DI5RO],  # L533
    0x0a03: [BRAIN],  # S103_G
    0x0b03: [BRAIN, E14RO14RO],  # M403
    0x0c03: [BRAIN, E4AI4AO6DI5RO],  # M503
    # 0x0d03: [BRAIN],  # M603
    0x0e03: [BRAIN, E16DI14DI, E16DI14DI],  # L303
    0x0F03: [BRAIN, E4AI4AO6DI5RO, E14DI14RO],  # L503
    0x1003: [BRAIN, E4AI4AO6DI5RO, E4AI4AO6DI5RO],  # L513

    0x0107: [BRAIN],  # S107
    0x0707: [BRAIN],  # S117
    0x0a07: [BRAIN],  # S167
    0x0207: [E8DI8DO],  # S207
    0x0b07: [E8DI8DO],  # S227
    0x0307: [BRAIN, E16DI14RO],  # M207
    0x0407: [BRAIN, E4AI4AO4DI5RO],  # M527
    0x0507: [BRAIN, E16DI14RO, E16DI14RO],  # L207
    0x0607: [BRAIN, E4AI4AO4DI5RO, E16DI14RO],  # L527
    0x0807: [BRAIN, E16DI14RO],  # M267
    0x0907: [BRAIN, E4AI4AO4DI5RO],  # M567

    0x0001: [UNIPI11],  # UNIPI10
    0x0101: [UNIPI11],  # UNIPI11
    0x1101: [UNIPI11LITE],  # UNIPI11LITE
}


def configure_owfs():
    change = False
    required_lines = list(OWFS_CONFIG_LINES)
    lines = list()
    with open(OWFS_CONFIG_PATH, 'r') as f:
        while True:
            line = f.readline()
            if len(line) == 0:
                break
            line = line.replace('\n', '')
            if line in required_lines:
                required_lines.remove(line)
                if line == OWFS_CONFIG_LINES[0]:
                    return  # If have signature by evok, do nothing.
            if 'FAKE' in line and '#' != line.replace(' ', '')[0]:
                line = '#' + line
                change = True
            lines.append(line)

    if len(required_lines) > 0 or change:
        if len(required_lines) > 0:
            lines.append('\n')
            lines.extend(required_lines)
        with open(OWFS_CONFIG_PATH, 'w') as f:
            for line in lines:
                f.write(f"{line}\n")
        print("Configured OWFS")


def generate_config(boards: List[str], defaults: Union[None, dict] = None, has_ow: bool = False):
    defaults = defaults if defaults is not None else dict()
    port = defaults.get('port', 502)
    hostname = defaults.get('hostname', '127.0.0.1')
    names = defaults.get('names', [i for i in range(1, len(boards) + 1)])
    slave_ids = defaults.get('slave-ids', [i for i in range(1, len(boards) + 1)])

    ret = {
        'hw_tree': {
            'LOCAL_TCP': {
                'type': 'MODBUSTCP',
                'hostname': hostname,
                'port': port,
                'devices': {},
            }
        }
    }

    for i in range(len(boards)):
        ret['hw_tree']['LOCAL_TCP']['devices'][names[i]] = {
            'slave-id': slave_ids[i],
            'model': boards[i]
        }

    if has_ow:
        ret['hw_tree']['OWFS'] = {
            'type': 'OWBUS',
            'interval': 10,
            'scan_interval': 60
        }

    return ret


def yaml_dump(data: dict, stream, depth: int):
    pre = ''.join(['  ' for i in range(depth)])
    for key, value in data.items():
        if type(value) is dict:
            stream.write(f"{pre}{key}:\n")
            yaml_dump(value, stream, depth + 1)
        else:
            stream.write(f"{pre}{key}: {value}\n")


def run():
    try:
        product_data = os_configurator.get_product_info()
        platform_id = int(os_configurator.get_product_info().id)
        model_name = product_data.name
        boards: List[str] = hw_data.get(platform_id, [])
    except Exception as E:
        print(f"Device not recognized!  ({E})")
        exit(0)

    print(f"Detect device {model_name} ({hex(platform_id)}) with boards {boards}")

    is_unipi_one = True if platform_id in [0x0001, 0x0101, 0x1101] else False

    has_ow = False
    if (BRAIN in boards or is_unipi_one) and os.path.isfile(OWFS_CONFIG_PATH):
        has_ow = True
        configure_owfs()

    defaults = dict()

    if is_unipi_one:
        defaults['port'] = 503
        defaults['slave-ids'] = [0]

    autogen_conf = generate_config(boards, defaults=defaults, has_ow=has_ow)

    with open('/etc/evok/autogen.yaml', 'w') as f:
        yaml_dump(data=autogen_conf, stream=f, depth=0)


if __name__ == '__main__':
    run()
