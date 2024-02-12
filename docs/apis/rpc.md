# RPC EVOK API ([api-doc]())

The RPC (Remote Procedure Call) API is used for invoking procedures, functions or methods across a network.
It is suitable for automated request.

# Examples

For python examples you need installed 'requests' package.
You can install it with this command: `pip3 install requests`.

## Reading DI 1.01

### Python:
```python
import requests

payload = {
    "method": "input_get",
    "params": ["1_01"],
    "jsonrpc": "2.0",
    "id": 0,
}

url = 'http://127.0.0.1/rpc'
response = requests.post(url, json=payload).json()
print(response)
```

### Output:
```
{'jsonrpc': '2.0', 'id': 0, 'result': [0, 50]}
```


## Setting DO 1.01 to HIGH

### Python:
```python
import requests

payload = {
    "method": "relay_set",
    "params": ["1_01", '1'],
    "jsonrpc": "2.0",
    "id": 0,
}

url = 'http://127.0.0.1/rpc'
response = requests.post(url, json=payload).json()
print(response)
```

### Output:
```
{'jsonrpc': '2.0', 'id': 0, 'result': 1}
```
