from typing import Tuple, Dict

from .schemas import *

schemas: Dict[str, Tuple[dict, dict]] = {
    'input': (di_post_inp_schema, di_post_inp_example),
    'output': (relay_post_inp_schema, relay_post_inp_example),
    'register': (register_post_inp_schema, register_post_inp_example),
    'ai': (ai_post_inp_schema, ai_post_inp_example),
    'ao': (ao_post_inp_schema, ao_post_inp_example),
    'led': (led_post_inp_schema, led_post_inp_example),
    'watchdog': (wd_post_inp_schema, wd_post_inp_example),
    '1wdevice': (owire_post_inp_schema, owire_post_inp_example),
    'owbus': (owbus_post_inp_schema, owbus_post_inp_example),
}
schemas['di'] = schemas['input']
schemas['do'] = schemas['output']
schemas['relay'] = schemas['output']
schemas['analoginput'] = schemas['ai']
schemas['analogoutput'] = schemas['ao']
schemas['wd'] = schemas['watchdog']
schemas['temp'] = schemas['1wdevice']
schemas['sensor'] = schemas['1wdevice']
