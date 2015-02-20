"""
This is a simple tool to allow modifing the coeficient for analog-digital conversion
used in the evok's AnalogInput class. Use if your conversion does not match.

It converts the provided float to hex float and writes it to the specified memory.

See the evok.conf for adc coef starting address.

Make sure to restart the evok service.

Example: python set_adc_coef.py -c 5.56 -a 0x00
"""

#!/usr/bin/python
import smbus
import struct
import argparse
from time import sleep

parser = argparse.ArgumentParser()
parser.add_argument('-c', '--coef', help='Desired coeficient', required=True)
parser.add_argument('-a', '--address', help='Starting hex address of coeficient, e.g. 0xf0', required=True)
args = vars(parser.parse_args())

bus = smbus.SMBus(1)
DEVICE_ADDRESS = 0x50
addr = int(args['address'], 16)
hexstr = hex(struct.unpack('<I', struct.pack('<f', float(args['coef'])))[0])[2:]
for i in [0, 2, 4, 6]:
    bus.write_byte_data(DEVICE_ADDRESS, addr, int(hexstr[i:i + 2], 16))
    addr += 1
    sleep(0.05)