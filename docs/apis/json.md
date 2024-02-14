# JSON EVOK API ([api-doc]())

The JSON API provides a simple interface for sending and receiving data in a stateless, cacheable communications.
This protocol do not support multiple write in one request.
It is suitable for automated requests thanks JSON protocol, which is better machine-processed.

# Examples

For python examples you need installed 'requests' package.
You can install it with this command: `pip3 install requests`.

## Reading DI 1.01

### Python:
```python
import requests

def get_request(host: str, dev_type: str, circuit: str):
    url = f"http://{host}/json/{dev_type}/{circuit}"
    return requests.get(url=url)

if __name__ == '__main__':
    ret = get_request(host='127.0.0.1', dev_type='input', circuit='1_01')
    print(ret.json())
```

### Curl:
```bash
curl --request GET --url 'http://127.0.0.1/json/input/1_01/'
```

### Output:
```
{"dev": "input", "circuit": "1_01", "value": 0, "debounce": 50, "counter_modes": ["Enabled", "Disabled"], "counter_mode": "Enabled", "counter": 0, "mode": "Simple", "modes": ["Simple", "DirectSwitch"], "glob_dev_id": 2}
```


## Setting DO 1.01 to HIGH

### Python:
```python
import requests, json

def send_request(host: str, dev_type: str, circuit: str, value: bool):
    url = f"http://{host}/json/{dev_type}/{circuit}"
    data = {'value': str(int(value))}
    return requests.post(url=url, data=json.dumps(data))

if __name__ == '__main__':
    ret = send_request(host='127.0.0.1', dev_type='relay', circuit='1_01', value=True)
    print(ret.json())
```

### Curl:
```bash
curl --request POST --url 'http://127.0.0.1/json/relay/1_01/' --data '{"value": 1}'
```

### Output:
```
{'success': True, 'result': {'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_01', 'value': 0, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}}
```
