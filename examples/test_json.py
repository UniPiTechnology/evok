import requests

host = '192.168.221.40'


def send_rest_request(host: str, dev_type: str, dev_id: str, value: int):
    url = f"http://{host}/json/{dev_type}/{dev_id}"
    data = {'value': str(value)}
    requests.post(url=url, data=data)


def get_rest_request(host: str, dev_type: str, dev_id: str):
    url = f"http://{host}/rest/{dev_type}/{dev_id}"
    return requests.get(url=url)


def main():
    ret = get_rest_request(host=host, dev_type='led', dev_id='1_01')
    print(ret.json())


if __name__ == '__main__':
    main()
