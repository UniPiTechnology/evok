# EVOK aliases

There is also the possibility of aliasing device names, to allow devices to be given permanent names.
There are several restrictions to aliases:

- Every alias needs to globally unique, not just within its own class.
- Aliases can only contain alphanumeric characters, underscores and dashes.
- This is to allow devices to address via the alias using the APIs
(i.e. setting an alias for a relay 1_01 to "bedroom_light" will allow it to be addressed both as /rest/relay/al_bedroom_light as well as /rest/relay/1_01)
- Invalid aliases will be rejected by the API, with the previous alias remaining.

The set aliases are initially stored only in the RAM.
After 5 minutes it is permanently saved to Flash.
The saving of all set aliases can be called up using the device '/run/alias'/

We recommended setting aliases with [evok-web](https://github.com/UniPiTechnology/evok-web).


# Examples

For python examples you need installed 'requests' package.
You can install it with this command: `pip3 install requests`.

## Setting alias DO 1_01 to my_relay

### Python:
```python
import requests

def set_alias(host: str, dev_type: str, circuit: str, value: str):
    url = f"http://{host}/rest/{dev_type}/{circuit}"
    data = {'alias': str(value)}
    return requests.post(url=url, data=data)

if __name__ == '__main__':
    ret = set_alias(host='127.0.0.1', dev_type='relay', circuit='1_01', value='my_relay')
    print(ret.json())
```

### Curl:
```bash
curl --request POST --url 'http://127.0.0.1/rest/relay/1_01/' --data 'alias=my_relay'
```

### Output:
```
{'success': True, 'result': {'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_01', 'value': 1, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0, 'alias': 'my_relay'}}
```

## Remove alias for DO 1_01

### Python:
```python
import requests

def set_alias(host: str, dev_type: str, circuit: str, value: str):
    url = f"http://{host}/rest/{dev_type}/{circuit}"
    data = {'alias': str(value)}
    return requests.post(url=url, data=data)

if __name__ == '__main__':
    ret = set_alias(host='127.0.0.1', dev_type='relay', circuit='1_01', value='')
    print(ret.json())
```

### Curl:
```bash
curl --request POST --url 'http://127.0.0.1/rest/relay/1_01/' --data 'alias='
```

### Output:
```
{'success': True, 'result': {'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_01', 'value': 1, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}}
```

## Force save alias to Flash

### Python:
```python
import requests

def save_aliases(host: str, value: bool):
    url = f"http://{host}/rest/run/alias"
    data = {'save': int(value)}
    return requests.post(url=url, data=data)

if __name__ == '__main__':
    ret = save_aliases(host='127.0.0.1', value=True)
    print(ret.json())
```

### Curl:
```bash
curl --request POST --url 'http://127.0.0.1/rest/run/alias/' --data 'save=1'
```

### Output:
```
{'success': True, 'result': {'dev': 'run', 'circuit': 'alias', 'save': False, 'aliases': {'my_relay': 'relay_1_01'}}}
```
