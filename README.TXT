Requires following libraries :

------------ ADITIONAL MODULES ---------------
import ow
import pigpio
import tornado
import toro
import tornardorpc-unipi as tornadorpc
import jsonrpclib


------------ LOCAL MODULES ---------------
import apigpio
import unipig
import devices
import owclient
import extcontrols
import devents
import devices
import config


------------ STANDARD MODULES ---------------
import collections
import atexit
import base64
import fcntl
import os
import random
import re
import struct
import datetime
import time
import json
import multiprocessing
import ConfigParser


and functional i2c subsystem also requires running pigpiod (-s 10).

Use the provided etc/init.d/evok and etc/init.d/pigpiod scripts to start and stop the services.
