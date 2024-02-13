# REST EVOK API ([api-doc]())

The REST API provides a simple interface for sending and receiving data in a stateless, cacheable communications.
This protocol do not support multiple write in one request.
It is suitable for hand-make requests.

## Examples

For python examples you need installed 'requests' package.
You can install it with this command: `pip3 install requests`.

## Reading DI 1.01

### Python:
```python
import requests

def get_request(host: str, dev_type: str, circuit: str):
    url = f"http://{host}/rest/{dev_type}/{circuit}"
    return requests.get(url=url)

if __name__ == '__main__':
    ret = get_request(host='127.0.0.1', dev_type='input', circuit='1_01')
    print(ret.json())
```

### Curl:
```bash
curl --request GET --url 'http://127.0.0.1/rest/input/1_01/'
```

### Output:
```
{"dev": "input", "circuit": "1_01", "value": 0, "debounce": 50, "counter_modes": ["Enabled", "Disabled"], "counter_mode": "Enabled", "counter": 0, "mode": "Simple", "modes": ["Simple", "DirectSwitch"], "glob_dev_id": 2}
```


## Setting DO 1.01 to HIGH

### Python:
```python
import requests

def send_request(host: str, dev_type: str, circuit: str, value: bool):
    url = f"http://{host}/rest/{dev_type}/{circuit}"
    data = {'value': str(int(value))}
    return requests.post(url=url, data=data)

if __name__ == '__main__':
    ret = send_request(host='127.0.0.1', dev_type='output', circuit='1_01', value=True)
    print(ret.json())
```

### Curl:
```bash
curl --request POST --url 'http://127.0.0.1/rest/output/1_01/' --data 'value=1'
```

### Output:
```
{"success": true, "result": {"dev": "relay", "relay_type": "digital", "circuit": "1_01", "value": 1, "pending": false, "mode": "Simple", "modes": ["Simple", "PWM"], "glob_dev_id": 2, "pwm_freq": 4800.0, "pwm_duty": 0}}
```
