# Evok Bulk API

The Bulk API is designed to provide an efficient way for clients to update, create or delete large amounts of data. This protocol support multiple write in one request. It is suitable for automated requests thanks JSON protocol, which is better machine-processed.

## Examples

For python examples you need installed 'requests' package. You can install it with this command: `pip3 install requests`.

### Setting DOs to HIGH

```python title="Python"
import requests

payload = {"individual_assignments": []}

for circuit in ['1_01', '1_02', '1_03', '1_04']:
    cmd = {"device_type": "relay", "device_circuit": circuit, "assigned_values": {'value': 1}}
    payload['individual_assignments'].append(cmd)

url = 'http://127.0.0.1/bulk'
print(requests.post(url, json=payload).json())
```

```rs title="Output"
{'individual_assignments': [{'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_01', 'value': 0, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}, {'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_02', 'value': 0, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}, {'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_03', 'value': 0, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}, {'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_04', 'value': 0, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}]}
```

### Setting DOs to LOW

```python title="Python"
import requests

payload = {"individual_assignments": []}

for circuit in ['1_01', '1_02', '1_03', '1_04']:
    cmd = {"device_type": "relay", "device_circuit": circuit, "assigned_values": {'value': 0}}
    payload['individual_assignments'].append(cmd)

url = 'http://127.0.0.1/bulk'
print(requests.post(url, json=payload).json())
```

``` rs title="Output"
{'individual_assignments': [{'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_01', 'value': 1, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}, {'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_02', 'value': 1, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}, {'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_03', 'value': 1, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}, {'dev': 'relay', 'relay_type': 'digital', 'circuit': '1_04', 'value': 1, 'pending': False, 'mode': 'Simple', 'modes': ['Simple', 'PWM'], 'glob_dev_id': 2, 'pwm_freq': 4800.0, 'pwm_duty': 0}]}
```
