import requests
import json

host = '192.168.221.144'


def send_rest_request(host: str, dev_type: str, dev_id: str, value):
    url = f"http://{host}/json/{dev_type}/{dev_id}"
    data = {'value': value}
    return requests.post(url=url, data=json.dumps(data))


def get_rest_request(host: str, dev_type: str, dev_id: str):
    url = f"http://{host}/json/{dev_type}/{dev_id}"
    return requests.get(url=url)


def main():
    ret = send_rest_request(host=host, dev_type='led', dev_id='1_01', value='1')
    print(ret.json())


if __name__ == '__main__':
    main()
