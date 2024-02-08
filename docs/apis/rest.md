# REST EVOK API

Documentation in progress

## Examples

### Reading DI 1.01
Python:
```python
import requests

def get_request(host: str, dev_type: str, dev_id: str):
    url = f"http://{host}/rest/{dev_type}/{dev_id}"
    return requests.get(url=url)

if __name__ == '__main__':
    ret = get_request(host='127.0.0.1', dev_type='input', dev_id='1_01')
    print(ret.json())
```
Bash:
```bash
curl --request POST --url 'http://127.0.0.1/rest/input/1_01/'
```
### Setting DO 1.01 to HIGH
Python:
```python
import requests

def send_request(host: str, dev_type: str, dev_id: str, value: bool):
    url = f"http://{host}/rest/{dev_type}/{dev_id}"
    data = {'value': str(value)}
    return requests.post(url=url, data=data)

if __name__ == '__main__':
    ret = send_request(host='127.0.0.1', dev_type='output', dev_id='1_01', value=True)
    print(ret.json())
```
Bash:
```bash
curl --request POST --url 'http://127.0.0.1/rest/output/1_01/' --data 'value=1'
```
